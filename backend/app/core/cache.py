"""
Hot-feed caching via Redis (Phase 4 resilience, 2026-07-16 plan).

Only the anonymous default feed is cached (no user_context/exclude_ids —
personalized pages are unique per caller and would just thrash). The cache
is strictly best-effort: any Redis failure degrades to a live DB read, and
a warm entry keeps the feed serving through a short database outage.
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

FEED_CACHE_KEY = "bloom:feed:anonymous:v1"
FEED_CACHE_TTL_SECONDS = 60

_client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
    return _client


async def get_cached_feed() -> dict[str, Any] | None:
    """Fetch the cached anonymous feed; None on miss or Redis failure."""
    try:
        raw = await _get_client().get(FEED_CACHE_KEY)
        if raw is None:
            return None
        cached = json.loads(raw)
        return cached if isinstance(cached, dict) else None
    except Exception as e:
        logger.debug(f"Feed cache read skipped: {e}")
        return None


async def set_cached_feed(response: dict[str, Any]) -> None:
    """Store the anonymous feed response; failures are non-fatal."""
    try:
        await _get_client().set(
            FEED_CACHE_KEY, json.dumps(response), ex=FEED_CACHE_TTL_SECONDS
        )
    except Exception as e:
        logger.debug(f"Feed cache write skipped: {e}")
