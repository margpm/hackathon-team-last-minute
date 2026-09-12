from __future__ import annotations

import json
import logging
import os
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

    try:
        response = await (completion_fn or litellm.acompletion)(
            model=model or settings.active_model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "contextproof_result",
                    "strict": True,
                    "schema": schema,
                },
            },
            temperature=0,
            max_tokens=1600,
        )
        result = ContextProofResult.model_validate_json(_response_content(response))
        return validate_source_integrity(result, context.posts)
    except ContextProofModelError:
        raise
    except (ValidationError, SourceIntegrityError, json.JSONDecodeError) as error:
        raise ContextProofModelError(
            "OPENAI_INVALID_OUTPUT",
            "OpenAI output failed the ContextProof integrity check.",
        ) from error
    except Exception as error:
        logger.error("OpenAI ContextProof analysis failed: %s", type(error).__name__)
        raise ContextProofModelError(
            "OPENAI_REQUEST_FAILED",
            "OpenAI analysis failed before any result was produced.",
        ) from error
