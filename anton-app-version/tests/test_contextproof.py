import unittest

from app.contextproof import (
    Conflict,
    ContextProofResult,
    PublicContext,
    PublicPost,
    RecommendedAction,
    SourceIntegrityError,
    SupportedSignal,
    Unknown,
    run_contextproof,
    validate_source_integrity,
)


def post(number: int) -> PublicPost:
    return PublicPost(
        id=f"at://did:plc:user{number}/app.bsky.feed.post/post-{number}",
        text=f"Observed public statement {number}",
        author=f"@user{number}.example",
        url=f"https://bsky.app/profile/did:plc:user{number}/post/post-{number}",
        created_at="2026-09-12T10:00:00Z",
        source="bluesky",
    )


class ContextProofAcceptanceTests(unittest.TestCase):
    def test_normal_signal_requires_multiple_observed_posts(self):
        posts = [post(1), post(2)]
        result = ContextProofResult(
            supported_signals=[
                SupportedSignal(
                    claim="Reliability is a repeated AI-agent concern.",
                    supporting_post_ids=[posts[0].id, posts[1].id],
                    reason="Two observed posts independently describe reliability failures.",
                )
            ],
            conflicts=[],
            unknowns=[],
            recommended_action=RecommendedAction(
                title="Prototype a visible agent verification checkpoint.",
                reason="Repeated observed concerns point to verification as the bounded test.",
                evidence_post_ids=[posts[0].id, posts[1].id],
            ),
        )

        validated = validate_source_integrity(result, posts)

        self.assertEqual(len(validated.supported_signals), 1)
        self.assertEqual(len(validated.recommended_action.evidence_post_ids), 2)

    def test_conflict_preserves_materially_incompatible_positions(self):
        posts = [post(1), post(2)]
        result = ContextProofResult(
            supported_signals=[],
            conflicts=[
                Conflict(
                    topic="How much autonomy AI agents should receive.",
                    position_a="Agents should execute end to end.",
                    position_b="Agents should stop for human approval.",
                    supporting_post_ids=[posts[0].id, posts[1].id],
                )
            ],
            unknowns=[],
            recommended_action=RecommendedAction(
                title="Test one approval-gated agent workflow.",
                reason="A bounded test resolves the observed autonomy disagreement.",
                evidence_post_ids=[posts[0].id, posts[1].id],
            ),
        )

        self.assertEqual(len(validate_source_integrity(result, posts).conflicts), 1)

    def test_insufficient_evidence_returns_unknown_and_one_action(self):
        result = ContextProofResult(
            supported_signals=[],
            conflicts=[],
            unknowns=[
                Unknown(
                    question="Which problem is largest?",
                    reason="The available posts do not establish comparative prevalence.",
                )
            ],
            recommended_action=RecommendedAction(
                title="Collect a larger focused sample before choosing a build.",
                reason="The observed context is insufficient for a product decision.",
                evidence_post_ids=[],
            ),
        )

        validated = validate_source_integrity(result, [])

        self.assertEqual(len(validated.unknowns), 1)
        self.assertEqual(validated.recommended_action.evidence_post_ids, [])

    def test_source_integrity_rejects_invented_ids(self):
        posts = [post(1), post(2)]
        result = ContextProofResult(
            supported_signals=[
                SupportedSignal(
                    claim="A claim",
                    supporting_post_ids=[posts[0].id, "invented-id"],
                    reason="A reason",
                )
            ],
            conflicts=[],
            unknowns=[],
            recommended_action=RecommendedAction(
                title="A bounded action",
                reason="A reason",
                evidence_post_ids=[posts[0].id],
            ),
        )

        with self.assertRaisesRegex(SourceIntegrityError, "unobserved post ID"):
            validate_source_integrity(result, posts)


class ContextProofPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_integrated_pipeline_returns_traceable_evidence(self):
        context = PublicContext(query="AI agents problems", posts=[post(1), post(2)])
        result = ContextProofResult(
            supported_signals=[
                SupportedSignal(
                    claim="Verification is repeatedly requested.",
                    supporting_post_ids=[context.posts[0].id, context.posts[1].id],
                    reason="Both observed posts support the point.",
                )
            ],
            conflicts=[],
            unknowns=[],
            recommended_action=RecommendedAction(
                title="Build one visible verification gate.",
                reason="It addresses the repeated observed signal.",
                evidence_post_ids=[context.posts[0].id, context.posts[1].id],
            ),
        )

        async def search_fn(_question):
            return context

        async def analyze_fn(_context):
            return result

        run = await run_contextproof(
            context.query,
            search_fn=search_fn,
            analyze_fn=analyze_fn,
        )

        self.assertEqual([item.id for item in run.evidence], [
            context.posts[0].id,
            context.posts[1].id,
        ])
