import json
import unittest
from types import SimpleNamespace

from app.contextproof import PublicContext, PublicPost
from app.llm_client import (
    ContextProofModelError,
    analyze_context,
    generate_search_queries,
)


def context() -> PublicContext:
    posts = [
        PublicPost(
            id=f"at://did:plc:user{number}/app.bsky.feed.post/post-{number}",
            text=f"Observed statement {number}",
            author=f"@user{number}.example",
            url=f"https://bsky.app/profile/did:plc:user{number}/post/post-{number}",
            created_at="2026-09-12T10:00:00Z",
            source="bluesky",
        )
        for number in (1, 2)
    ]
    return PublicContext(query="AI agents problems", posts=posts)


def valid_payload(source_context: PublicContext) -> dict:
    ids = [post.id for post in source_context.posts]
    return {
        "supported_signals": [
            {
                "claim": "Verification is a repeated concern.",
                "supporting_post_ids": ids,
                "reason": "Two observed posts support the point.",
            }
        ],
        "conflicts": [],
        "unknowns": [],
        "recommended_action": {
            "title": "Build one approval-gated verification step.",
            "reason": "It directly tests the repeated concern.",
            "evidence_post_ids": ids,
        },
    }


def response(payload: dict):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(payload)),
            )
        ]
    )


def text_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


class SearchQueryGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generates_bounded_queries_and_logs_full_exchange(self):
        question = "What blocks teams from trusting AI agents in production?"
        model_reply = "AI agent trust, production verification, human approval"
        observed = None

        async def completion_fn(**kwargs):
            nonlocal observed
            observed = kwargs
            return text_response(model_reply)

        with self.assertLogs("app.llm_client", level="INFO") as captured:
            queries = await generate_search_queries(
                question,
                completion_fn=completion_fn,
                model="gpt-4o-mini",
            )

        self.assertEqual(
            queries,
            ["AI agent trust", "production verification", "human approval"],
        )
        self.assertEqual(observed["model"], "gpt-4o-mini")
        self.assertEqual(observed["temperature"], 0)

        audit_log = "\n".join(captured.output)
        self.assertIn("llm.request", audit_log)
        self.assertIn("query_generation", audit_log)
        self.assertIn(question, audit_log)
        self.assertIn("Output only", audit_log)
        self.assertIn("llm.response", audit_log)
        self.assertIn(model_reply, audit_log)


class OpenAIStructuredOutputTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_strict_structured_output_and_validates_ids(self):
        source_context = context()
        observed = None

        async def completion_fn(**kwargs):
            nonlocal observed
            observed = kwargs
            return response(valid_payload(source_context))

        with self.assertLogs("app.llm_client", level="INFO") as captured:
            result = await analyze_context(
                source_context,
                completion_fn=completion_fn,
                model="gpt-4o-mini",
            )

        self.assertEqual(observed["model"], "gpt-4o-mini")
        self.assertEqual(observed["response_format"]["type"], "json_schema")
        self.assertTrue(observed["response_format"]["json_schema"]["strict"])
        self.assertEqual(len(result.supported_signals), 1)

        audit_log = "\n".join(captured.output)
        self.assertIn("llm.request", audit_log)
        self.assertIn("synthesis", audit_log)
        self.assertIn(source_context.posts[0].text, audit_log)
        self.assertIn("llm.response", audit_log)
        self.assertIn("Verification is a repeated concern.", audit_log)

    async def test_fails_closed_when_model_invents_a_source_id(self):
        source_context = context()
        payload = valid_payload(source_context)
        payload["recommended_action"]["evidence_post_ids"] = ["invented-id"]

        async def completion_fn(**_kwargs):
            return response(payload)

        with self.assertRaisesRegex(ContextProofModelError, "integrity check"):
            await analyze_context(source_context, completion_fn=completion_fn)

    async def test_fails_closed_when_openai_request_fails(self):
        async def completion_fn(**_kwargs):
            raise RuntimeError("upstream unavailable")

        with self.assertRaisesRegex(ContextProofModelError, "before any result"):
            await analyze_context(context(), completion_fn=completion_fn)
