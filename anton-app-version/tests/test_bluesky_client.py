import unittest

from app.bluesky_client import (
    LiveSourceError,
    build_search_query,
    normalize_posts,
    search_posts,
)


def raw_post(
    rkey: str,
    text: str,
    did: str = "did:plc:alice",
    handle: str = "alice.example",
) -> dict:
    return {
        "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
        "author": {"did": did, "handle": handle},
        "record": {
            "text": text,
            "createdAt": "2026-09-12T10:00:00Z",
        },
        "indexedAt": "2026-09-12T10:00:01Z",
    }


class BlueskyNormalizationTests(unittest.TestCase):
    def test_demo_question_maps_to_one_focused_public_search(self):
        query = build_search_query(
            "What is the biggest problem people have with AI agents today, "
            "and what should we build next?"
        )

        self.assertEqual(query, "AI agents problems")

    def test_normalizes_real_identity_permalink_and_deduplicates(self):
        first = raw_post("post-one", "AI agent reliability is the main problem.")
        payload = {
            "posts": [
                first,
                first,
                raw_post(
                    "post-two",
                    "AI agents need clearer human approval boundaries.",
                    did="did:plc:bob",
                    handle="bob.example",
                ),
                raw_post("irrelevant", "My garden is ready for autumn."),
            ]
        }

        posts = normalize_posts(payload, "AI agents reliability", limit=30)

        self.assertEqual([post.id for post in posts], [
            "at://did:plc:alice/app.bsky.feed.post/post-one",
            "at://did:plc:bob/app.bsky.feed.post/post-two",
        ])
        self.assertEqual(posts[0].author, "@alice.example")
        self.assertEqual(
            posts[0].url,
            "https://bsky.app/profile/did:plc:alice/post/post-one",
        )
        self.assertEqual(posts[0].source, "bluesky")

    def test_rejects_payload_without_posts(self):
        with self.assertRaisesRegex(LiveSourceError, "invalid search response"):
            normalize_posts({"unexpected": []}, "AI agents", limit=30)


class BlueskySearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_searches_all_generated_queries_and_deduplicates_results(self):
        observed_queries = []
        shared = raw_post(
            "shared",
            "AI agent trust improves when human approval is visible.",
        )

        async def request_fn(params):
            observed_queries.append(params["q"])
            if params["q"] == "AI agent trust":
                return {
                    "posts": [
                        shared,
                        raw_post(
                            "trust",
                            "AI agent trust depends on production verification.",
                            did="did:plc:bob",
                            handle="bob.example",
                        ),
                    ]
                }
            return {
                "posts": [
                    shared,
                    raw_post(
                        "approval",
                        "Human approval should gate consequential agent actions.",
                        did="did:plc:carol",
                        handle="carol.example",
                    ),
                ]
            }

        context = await search_posts(
            "What blocks teams from trusting AI agents in production?",
            search_queries=["AI agent trust", "human approval"],
            request_fn=request_fn,
        )

        self.assertEqual(observed_queries, ["AI agent trust", "human approval"])
        self.assertEqual(
            context.query,
            "What blocks teams from trusting AI agents in production?",
        )
        self.assertEqual(context.search_queries, ["AI agent trust", "human approval"])
        self.assertEqual(len(context.posts), 3)
        self.assertEqual(len({post.id for post in context.posts}), 3)

    async def test_search_uses_public_query_and_demo_safe_limit(self):
        observed_params = None

        async def request_fn(params):
            nonlocal observed_params
            observed_params = params
            return {"posts": [raw_post("post-one", "AI agents fail without context.")]}

        context = await search_posts("AI agents problems", request_fn=request_fn)

        self.assertEqual(context.query, "AI agents problems")
        self.assertEqual(len(context.posts), 1)
        self.assertEqual(observed_params["q"], "agents problems")
        self.assertEqual(observed_params["sort"], "top")
        self.assertGreaterEqual(int(observed_params["limit"]), 20)
        self.assertLessEqual(int(observed_params["limit"]), 40)

    async def test_live_source_error_is_not_replaced_with_fake_data(self):
        async def request_fn(_params):
            raise LiveSourceError("BLUESKY_HTTP_ERROR", "Bluesky returned HTTP 503.")

        with self.assertRaisesRegex(LiveSourceError, "HTTP 503"):
            await search_posts("AI agents problems", request_fn=request_fn)
