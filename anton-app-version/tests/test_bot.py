import unittest

from app.bluesky_client import LiveSourceError
from app.bot import ApprovalStore, approval_markup, format_contextproof, format_failure
from app.contextproof import (
    ContextProofResult,
    ContextProofRun,
    PublicContext,
    PublicPost,
    RecommendedAction,
    SupportedSignal,
)


def demo_run() -> ContextProofRun:
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
    context = PublicContext(query="AI agents problems", posts=posts)
    analysis = ContextProofResult(
        supported_signals=[
            SupportedSignal(
                claim="Verification is a repeated concern.",
                supporting_post_ids=[post.id for post in posts],
                reason="Two observed posts support the point.",
            )
        ],
        conflicts=[],
        unknowns=[],
        recommended_action=RecommendedAction(
            title="Build one visible approval gate.",
            reason="It tests the repeated concern.",
            evidence_post_ids=[post.id for post in posts],
        ),
    )
    return ContextProofRun(context=context, analysis=analysis, evidence=posts)


class TelegramPresentationTests(unittest.TestCase):
    def test_response_contains_required_sections_and_real_links(self):
        text = format_contextproof(demo_run())

        self.assertIn("Observed: 2 live Bluesky posts", text)
        self.assertIn("SUPPORTED SIGNAL", text)
        self.assertIn("CONFLICT", text)
        self.assertIn("UNKNOWN", text)
        self.assertIn("BEST NEXT ACTION", text)
        self.assertIn("https://bsky.app/profile/", text)
        self.assertLessEqual(len(text), 3900)

    def test_approval_is_owner_bound_one_time_and_exact(self):
        store = ApprovalStore(ttl_seconds=10)
        token = store.create("Build one visible approval gate.", user_id=7, now=100)

        self.assertIsNone(store.consume(token, user_id=8, now=101))
        approval = store.consume(token, user_id=7, now=101)
        self.assertEqual(approval.action, "Build one visible approval gate.")
        self.assertIsNone(store.consume(token, user_id=7, now=102))

    def test_inline_button_uses_bounded_callback_data(self):
        markup = approval_markup("bounded-token")
        button = markup.inline_keyboard[0][0]

        self.assertEqual(button.text, "APPROVE")
        self.assertEqual(button.callback_data, "approve:bounded-token")
        self.assertLessEqual(len(button.callback_data), 64)

    def test_live_source_failure_is_explicit_and_has_no_fake_success(self):
        text = format_failure(
            LiveSourceError("BLUESKY_HTTP_ERROR", "Bluesky returned HTTP 503.")
        )

        self.assertIn("LIVE_SOURCE_ERROR", text)
        self.assertIn("No analysis was generated", text)
        self.assertNotIn("SUPPORTED SIGNAL\n-", text)
