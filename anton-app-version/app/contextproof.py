from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.logger import log_event


logger = logging.getLogger(__name__)


def _log_pipeline_error(stage: str, error: Exception) -> None:
    log_event(
        logger,
        "pipeline.error",
        level=logging.ERROR,
        stage=stage,
        error_type=type(error).__name__,
        error_code=getattr(error, "code", None),
        message=str(error),
    )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PublicPost(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)
    url: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    source: Literal["bluesky"]


class PublicContext(StrictModel):
    query: str = Field(min_length=3, max_length=300)
    search_queries: list[str] = Field(default_factory=list, max_length=3)
    posts: list[PublicPost]


class SupportedSignal(StrictModel):
    claim: str = Field(min_length=1)
    supporting_post_ids: list[str]
    reason: str = Field(min_length=1)


class Conflict(StrictModel):
    topic: str = Field(min_length=1)
    position_a: str = Field(min_length=1)
    position_b: str = Field(min_length=1)
    supporting_post_ids: list[str]


class Unknown(StrictModel):
    question: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RecommendedAction(StrictModel):
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_post_ids: list[str]


class ContextProofResult(StrictModel):
    supported_signals: list[SupportedSignal]
    conflicts: list[Conflict]
    unknowns: list[Unknown]
    recommended_action: RecommendedAction


class ContextProofRun(StrictModel):
    context: PublicContext
    analysis: ContextProofResult
    evidence: list[PublicPost]


class SourceIntegrityError(ValueError):
    pass


def _assert_references(
    ids: list[str],
    known_ids: set[str],
    field_name: str,
    minimum: int,
) -> None:
    if len(ids) < minimum:
        raise SourceIntegrityError(
            f"{field_name} must reference at least {minimum} observed post IDs."
        )

    if len(ids) != len(set(ids)):
        raise SourceIntegrityError(f"{field_name} contains duplicate post IDs.")

    unknown_ids = [post_id for post_id in ids if post_id not in known_ids]
    if unknown_ids:
        raise SourceIntegrityError(
            f"{field_name} references an unobserved post ID: {unknown_ids[0]}"
        )


def validate_source_integrity(
    result: ContextProofResult,
    posts: list[PublicPost],
) -> ContextProofResult:
    known_ids = {post.id for post in posts}

    for index, signal in enumerate(result.supported_signals):
        _assert_references(
            signal.supporting_post_ids,
            known_ids,
            f"supported_signals[{index}]",
            minimum=2,
        )

    for index, conflict in enumerate(result.conflicts):
        _assert_references(
            conflict.supporting_post_ids,
            known_ids,
            f"conflicts[{index}]",
            minimum=2,
        )

    _assert_references(
        result.recommended_action.evidence_post_ids,
        known_ids,
        "recommended_action",
        minimum=0,
    )
    return result


def select_evidence(
    context: PublicContext,
    result: ContextProofResult,
    maximum: int = 5,
) -> list[PublicPost]:
    ordered_ids: list[str] = []

    def add(post_ids: list[str]) -> None:
        for post_id in post_ids:
            if post_id not in ordered_ids:
                ordered_ids.append(post_id)

    add(result.recommended_action.evidence_post_ids)
    for signal in result.supported_signals:
        add(signal.supporting_post_ids)
    for conflict in result.conflicts:
        add(conflict.supporting_post_ids)

    # UNKNOWN can be caused by weak evidence, so retain observed links even when
    # the model correctly cites no post as support for an action.
    if len(ordered_ids) < 2:
        add([post.id for post in context.posts])

    posts_by_id = {post.id: post for post in context.posts}
    return [posts_by_id[post_id] for post_id in ordered_ids[:maximum]]


GenerateQueriesFunction = Callable[[str], Awaitable[list[str]]]
SearchFunction = Callable[[str, list[str]], Awaitable[PublicContext]]
AnalyzeFunction = Callable[[PublicContext], Awaitable[ContextProofResult]]


async def run_contextproof(
    question: str,
    generate_queries_fn: GenerateQueriesFunction | None = None,
    search_fn: SearchFunction | None = None,
    analyze_fn: AnalyzeFunction | None = None,
) -> ContextProofRun:
    clean_question = question.strip()
    if len(clean_question) < 3 or len(clean_question) > 300:
        raise ValueError("Question must contain between 3 and 300 characters.")

    log_event(logger, "pipeline.started", question=clean_question)
    if generate_queries_fn is None:
        from app.llm_client import generate_search_queries

        generate_queries_fn = generate_search_queries
    if search_fn is None:
        from app.bluesky_client import search_posts

        search_fn = search_posts
    if analyze_fn is None:
        from app.llm_client import analyze_context

        analyze_fn = analyze_context

    try:
        search_queries = await generate_queries_fn(clean_question)
    except Exception as error:
        _log_pipeline_error("query_generation", error)
        raise
    if not 1 <= len(search_queries) <= 3:
        raise ValueError("Query generation must return between 1 and 3 queries.")
    log_event(
        logger,
        "pipeline.search_queries_ready",
        search_queries=search_queries,
    )

    try:
        context = await search_fn(clean_question, search_queries)
    except Exception as error:
        _log_pipeline_error("social_retrieval", error)
        raise
    log_event(
        logger,
        "pipeline.retrieval_complete",
        search_queries=context.search_queries,
        post_count=len(context.posts),
    )
    try:
        result = await analyze_fn(context)
        validate_source_integrity(result, context.posts)
    except Exception as error:
        _log_pipeline_error("synthesis", error)
        raise

    log_event(
        logger,
        "pipeline.synthesis_complete",
        supported_signal_count=len(result.supported_signals),
        conflict_count=len(result.conflicts),
        unknown_count=len(result.unknowns),
        recommended_action=result.recommended_action.title,
    )

    run = ContextProofRun(
        context=context,
        analysis=result,
        evidence=select_evidence(context, result),
    )
    log_event(logger, "pipeline.completed", evidence_count=len(run.evidence))
    return run
