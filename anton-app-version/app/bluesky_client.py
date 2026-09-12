from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from app.config import settings
from app.contextproof import PublicContext, PublicPost


logger = logging.getLogger(__name__)

GENERIC_WORDS = {
    "about",
    "and",
    "are",
    "biggest",
    "build",
    "for",
    "have",
    "is",
    "next",
    "people",
    "should",
    "the",
    "today",
    "what",
    "with",
}


class LiveSourceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _query_terms(query: str) -> set[str]:
    return {
        token[:-1] if token.endswith("s") and len(token) > 4 else token
        for token in re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        if len(token) >= 3 and token not in GENERIC_WORDS
    }


def build_search_query(question: str) -> str:
    tokens = re.findall(r"\w+", question.lower(), flags=re.UNICODE)
    if (
        "ai" in tokens
        and "problem" in tokens
        and "build" in tokens
        and any(token.startswith("agent") for token in tokens)
    ):
        return "AI agents problems"

    useful = [
        token
        for token in tokens
        if len(token) >= 3 and token not in GENERIC_WORDS
    ]
    return " ".join(useful[:8]) or question.strip()


def _public_post_url(uri: str) -> str | None:
    parts = uri.split("/")
    if (
        len(parts) != 5
        or parts[0] != "at:"
        or parts[1] != ""
        or parts[3] != "app.bsky.feed.post"
        or not parts[2]
        or not parts[4]
    ):
        return None
    return f"https://bsky.app/profile/{parts[2]}/post/{parts[4]}"


def normalize_posts(
    payload: dict[str, Any],
    query: str,
    limit: int,
) -> list[PublicPost]:
    raw_posts = payload.get("posts")
    if not isinstance(raw_posts, list):
        raise LiveSourceError(
            "BLUESKY_INVALID_RESPONSE",
            "Bluesky returned an invalid search response.",
        )

    terms = _query_terms(query)
    seen_ids: set[str] = set()
    seen_text: set[tuple[str, str]] = set()
    normalized: list[PublicPost] = []

    for raw_post in raw_posts:
        if not isinstance(raw_post, dict):
            continue
        record = raw_post.get("record")
        author = raw_post.get("author")
        if not isinstance(record, dict) or not isinstance(author, dict):
            continue

        post_id = _clean_text(raw_post.get("uri"))
        text = _clean_text(record.get("text"))
        did = _clean_text(author.get("did"))
        handle = _clean_text(author.get("handle"))
        created_at = _clean_text(record.get("createdAt") or raw_post.get("indexedAt"))
        url = _public_post_url(post_id)

        if not all((post_id, text, did, created_at, url)):
            continue
        if terms and not terms.intersection(_query_terms(text)):
            continue

        signature = (did, text.casefold())
        if post_id in seen_ids or signature in seen_text:
            continue

        seen_ids.add(post_id)
        seen_text.add(signature)
        normalized.append(
            PublicPost(
                id=post_id,
                text=text,
                author=f"@{handle}" if handle else did,
                url=url,
                created_at=created_at,
                source="bluesky",
            )
        )
        if len(normalized) >= limit:
            break

    return normalized


RequestFunction = Callable[[dict[str, str]], Awaitable[dict[str, Any]]]


async def _request_search(params: dict[str, str]) -> dict[str, Any]:
    timeout = aiohttp.ClientTimeout(total=settings.bluesky_timeout_seconds)
    headers = {
        "Accept": "application/json",
        "User-Agent": "ContextProof/1.0",
    }
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(settings.bluesky_search_url, params=params) as response:
                if response.status != 200:
                    raise LiveSourceError(
                        "BLUESKY_HTTP_ERROR",
                        f"Bluesky live search returned HTTP {response.status}.",
                    )
                try:
                    payload = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as error:
                    raise LiveSourceError(
                        "BLUESKY_INVALID_RESPONSE",
                        "Bluesky returned non-JSON search data.",
                    ) from error
    except LiveSourceError:
        raise
    except (aiohttp.ClientError, TimeoutError) as error:
        raise LiveSourceError(
            "BLUESKY_REQUEST_FAILED",
            "Bluesky live search could not be reached.",
        ) from error

    if not isinstance(payload, dict):
        raise LiveSourceError(
            "BLUESKY_INVALID_RESPONSE",
            "Bluesky returned an invalid search response.",
        )
    return payload


async def search_posts(
    query: str,
    search_queries: list[str] | None = None,
    request_fn: RequestFunction | None = None,
) -> PublicContext:
    clean_query = query.strip()
    if len(clean_query) < 3 or len(clean_query) > 300:
        raise ValueError("Question must contain between 3 and 300 characters.")

    limit = min(max(settings.bluesky_result_limit, 1), 40)
    candidates = search_queries or [build_search_query(clean_query)]
    queries: list[str] = []
    seen_queries: set[str] = set()
    for candidate in candidates:
        candidate = _clean_text(candidate)[:100]
        normalized = candidate.casefold()
        if len(candidate) < 2 or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        queries.append(candidate)
        if len(queries) == 3:
            break
    if not queries:
        raise ValueError("At least one usable social search query is required.")

    async def retrieve(search_query: str) -> list[PublicPost]:
        params = {
            "q": search_query,
            "limit": str(limit),
            "sort": "top",
            "lang": settings.bluesky_language,
        }
        payload = await (request_fn or _request_search)(params)
        return normalize_posts(payload, search_query, limit)

    batches: list[list[PublicPost] | Exception] = []
    for search_query in queries:
        try:
            batches.append(await retrieve(search_query))
        except Exception as error:
            batches.append(error)

    failures = [item for item in batches if isinstance(item, Exception)]
    successful_batches = [item for item in batches if isinstance(item, list)]
    if not successful_batches and failures:
        raise failures[0]

    for search_query, batch in zip(queries, batches, strict=True):
        if isinstance(batch, Exception):
            logger.warning(
                "Bluesky query failed query=%r error=%s",
                search_query,
                type(batch).__name__,
            )

    posts: list[PublicPost] = []
    seen_ids: set[str] = set()
    seen_content: set[tuple[str, str]] = set()
    for batch in successful_batches:
        for post in batch:
            signature = (post.author.casefold(), post.text.casefold())
            if post.id in seen_ids or signature in seen_content:
                continue
            seen_ids.add(post.id)
            seen_content.add(signature)
            posts.append(post)
            if len(posts) == limit:
                break
        if len(posts) == limit:
            break

    logger.info(
        "Bluesky retrieval completed queries=%d posts=%d",
        len(queries),
        len(posts),
    )
    return PublicContext(
        query=clean_query,
        search_queries=queries,
        posts=posts,
    )


async def publish_to_bluesky(text: str) -> str:
    """Publish through the collaborator-provided authenticated stretch path."""
    if not settings.bluesky_handle or not settings.bluesky_app_password:
        raise ValueError("Bluesky handle or app password not configured.")

    from atproto import AsyncClient

    logger.info("Authenticating to Bluesky for an approved publish action.")
    client = AsyncClient()
    try:
        await client.login(settings.bluesky_handle, settings.bluesky_app_password)
        post = await client.send_post(text)
        logger.info("Approved Bluesky post published with URI %s.", post.uri)
        return post.uri
    except Exception as error:
        logger.error("Approved Bluesky publish failed: %s", type(error).__name__)
        raise
