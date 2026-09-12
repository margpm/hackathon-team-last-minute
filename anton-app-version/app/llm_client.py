from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Awaitable, Callable
from typing import Any

import litellm
from pydantic import ValidationError

from app.config import settings
from app.contextproof import (
    ContextProofResult,
    PublicContext,
    SourceIntegrityError,
    validate_source_integrity,
)
from app.logger import log_event

logger = logging.getLogger(__name__)

# Set API keys for litellm so it can route to any provider
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.gemini_api_key:
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key


class ContextProofModelError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


CompletionFunction = Callable[..., Awaitable[Any]]

SEARCH_QUERY_SYSTEM_INSTRUCTION = (
    "You prepare search queries for live public social-media retrieval. "
    "Read the user's original request. Output only a comma-separated list "
    "of 1 to 3 concise search queries optimized for Bluesky or Threads. "
    "Preserve the user's key entities and intent. Do not answer the request, "
    "explain your choices, number the queries, or add any other text."
)


def _log_model_error(stage: str, error: Exception) -> None:
    log_event(
        logger,
        "llm.error",
        level=logging.ERROR,
        stage=stage,
        error_type=type(error).__name__,
        error_code=getattr(error, "code", None),
        message=str(error),
    )


def _response_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise ContextProofModelError(
            "OPENAI_INVALID_RESPONSE",
            "OpenAI returned no structured analysis.",
        ) from error

    if not isinstance(content, str) or not content.strip():
        raise ContextProofModelError(
            "OPENAI_INVALID_RESPONSE",
            "OpenAI returned no structured analysis.",
        )
    return content


def _parse_search_queries(content: str) -> list[str]:
    candidates = re.split(r"[,;\n]+", content)
    queries: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", candidate)
        cleaned = " ".join(cleaned.strip(" \t\r\n\"'").split())
        normalized = cleaned.casefold()
        if len(cleaned) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        queries.append(cleaned[:100])
        if len(queries) == 3:
            break

    if not queries:
        raise ContextProofModelError(
            "OPENAI_INVALID_QUERY_OUTPUT",
            "OpenAI returned no usable social search queries.",
        )
    return queries


async def generate_search_queries(
    question: str,
    completion_fn: CompletionFunction | None = None,
    model: str | None = None,
) -> list[str]:
    clean_question = question.strip()
    if len(clean_question) < 3 or len(clean_question) > 300:
        raise ValueError("Question must contain between 3 and 300 characters.")
    if completion_fn is None and not settings.openai_api_key:
        raise ContextProofModelError(
            "OPENAI_NOT_CONFIGURED",
            "OPENAI_API_KEY is required for live ContextProof analysis.",
        )

    selected_model = model or settings.active_model
    messages = [
        {"role": "system", "content": SEARCH_QUERY_SYSTEM_INSTRUCTION},
        {"role": "user", "content": clean_question},
    ]
    request = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 80,
    }
    log_event(
        logger,
        "llm.request",
        stage="query_generation",
        **request,
    )

    try:
        response = await (completion_fn or litellm.acompletion)(**request)
        content = _response_content(response)
        log_event(
            logger,
            "llm.response",
            stage="query_generation",
            model=selected_model,
            content=content,
        )
        return _parse_search_queries(content)
    except ContextProofModelError as error:
        _log_model_error("query_generation", error)
        raise
    except Exception as error:
        _log_model_error("query_generation", error)
        raise ContextProofModelError(
            "OPENAI_QUERY_REQUEST_FAILED",
            "OpenAI search-query generation failed before retrieval.",
        ) from error


async def analyze_context(
    context: PublicContext,
    completion_fn: CompletionFunction | None = None,
    model: str | None = None,
) -> ContextProofResult:
    if completion_fn is None and not settings.openai_api_key:
        raise ContextProofModelError(
            "OPENAI_NOT_CONFIGURED",
            "OPENAI_API_KEY is required for live ContextProof analysis.",
        )

    selected_model = model or settings.active_model
    schema = ContextProofResult.model_json_schema()
    messages = [
        {
            "role": "system",
            "content": (
                "You are ContextProof. Analyze only the observed Bluesky posts in "
                "the supplied JSON. A SUPPORTED SIGNAL is not objective truth: it "
                "requires at least two relevant observed posts that materially support "
                "the same point. A CONFLICT requires materially incompatible observed "
                "positions and at least two post IDs. UNKNOWN means the available "
                "evidence does not establish the answer. Never manufacture consensus, "
                "facts, authors, URLs, timestamps, or post IDs. Reference only supplied "
                "post IDs. Return exactly one bounded, reversible best next action that "
                "requires human approval. Its evidence_post_ids must cite observed posts "
                "when evidence supports it, or be empty when the action is to collect "
                "more evidence. Keep every field concise."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(context.model_dump(), ensure_ascii=False),
        },
    ]

    request = {
        "model": selected_model,
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "contextproof_result",
                "strict": True,
                "schema": schema,
            },
        },
        "temperature": 0,
        "max_tokens": 1600,
    }
    log_event(logger, "llm.request", stage="synthesis", **request)

    try:
        response = await (completion_fn or litellm.acompletion)(**request)
        content = _response_content(response)
        log_event(
            logger,
            "llm.response",
            stage="synthesis",
            model=selected_model,
            content=content,
        )
        result = ContextProofResult.model_validate_json(content)
        return validate_source_integrity(result, context.posts)
    except ContextProofModelError as error:
        _log_model_error("synthesis", error)
        raise
    except (ValidationError, SourceIntegrityError, json.JSONDecodeError) as error:
        _log_model_error("synthesis", error)
        raise ContextProofModelError(
            "OPENAI_INVALID_OUTPUT",
            "OpenAI output failed the ContextProof integrity check.",
        ) from error
    except Exception as error:
        _log_model_error("synthesis", error)
        raise ContextProofModelError(
            "OPENAI_REQUEST_FAILED",
            "OpenAI analysis failed before any result was produced.",
        ) from error
