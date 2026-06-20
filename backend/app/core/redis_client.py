"""
redis_client.py
───────────────
Async Redis client singleton with graceful degradation.

If REDIS_URL is not set, or the Redis server is unreachable, every
operation silently returns None / False — the app continues working
normally using Postgres as the fallback.

Usage:
    from app.core.redis_client import redis, redis_available

    if await redis_available():
        await redis.set("key", "value")
"""

import asyncio
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Singleton client ───────────────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None
_redis_ok: Optional[bool] = None          # cached health-check result


def _make_client() -> Optional[aioredis.Redis]:
    """Create the Redis client from the configured URL, or return None."""
    url = settings.REDIS_URL
    if not url:
        return None
    try:
        client = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=False,
        )
        return client
    except Exception as exc:
        logger.warning("[Redis] Could not create client: %s", exc)
        return None


def get_redis() -> Optional[aioredis.Redis]:
    """Return the (lazily-created) Redis client, or None if not configured."""
    global _redis_client
    if _redis_client is None:
        _redis_client = _make_client()
    return _redis_client


async def redis_available() -> bool:
    """
    Return True if Redis is reachable.
    Result is cached for the lifetime of the process after the first check.
    """
    global _redis_ok
    if _redis_ok is not None:
        return _redis_ok

    client = get_redis()
    if client is None:
        _redis_ok = False
        logger.info("[Redis] REDIS_URL not set — caching disabled.")
        return False

    try:
        await client.ping()
        _redis_ok = True
        logger.info("[Redis] Connected successfully.")
    except Exception as exc:
        _redis_ok = False
        logger.warning("[Redis] Unreachable — falling back to Postgres. Error: %s", exc)

    return _redis_ok


# Convenience alias so other modules can do:
#   from app.core.redis_client import redis
redis = get_redis
