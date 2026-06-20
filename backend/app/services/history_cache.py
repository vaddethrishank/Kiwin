"""
history_cache.py
────────────────
Redis-backed chat history cache with Postgres write-through.

Architecture
────────────
  • Active session history is stored in a Redis LIST (fast LRANGE reads).
  • On first access (cold start), we hydrate from Postgres automatically.
  • Every new message is appended to Redis AND written through to Postgres
    (non-blocking, as a background task).
  • If Redis is unavailable, we fall back to Postgres reads silently.

Key schema
──────────
  history:{agent_id}:{user_id}
    A Redis LIST of JSON strings: [{"role": "user"|"assistant", "content": "..."}]
    Maximum 50 entries (LTRIM applied on every RPUSH).
    TTL: 24 hours (reset on every access).

Public API
──────────
  get_history(agent_id, user_id, db, is_public)  → list[dict]
  append_messages(agent_id, user_id, pairs)       → None  (fire-and-forget)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.redis_client import get_redis, redis_available

logger = logging.getLogger(__name__)

_KEY_PREFIX = "history"
_MAX_MESSAGES = 50
_TTL_SECONDS = 86_400          # 24 hours
_FETCH_LIMIT = 10              # messages fetched for the LLM context window


def _history_key(agent_id: str, user_id: str) -> str:
    return f"{_KEY_PREFIX}:{agent_id}:{user_id}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_valid_uuid(val: str) -> bool:
    import uuid
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _fetch_postgres_history(db, agent_id: str, user_id: str, is_public: bool, limit: int):
    """Sync Postgres query — call via asyncio.to_thread."""
    query = db.table("messages").select("role, content").eq("agent_id", agent_id)
    if not is_public and _is_valid_uuid(user_id):
        query = query.eq("user_id", user_id)
    else:
        query = query.eq("session_id", user_id)
    return query.order("created_at", desc=True).limit(limit).execute()


def _fetch_postgres_history_50(db, agent_id: str, user_id: str, is_public: bool):
    return _fetch_postgres_history(db, agent_id, user_id, is_public, limit=50)


# ── Public API ────────────────────────────────────────────────────────────────

async def get_history_for_llm(
    agent_id: str,
    user_id: str,
    db,
    is_public: bool = False,
) -> List[Dict[str, str]]:
    """
    Return the last N messages for the LLM context window.
    Redis-first; falls back to Postgres on miss.
    Returns chronological order (oldest first).
    """
    import asyncio

    key = _history_key(agent_id, user_id)

    if await redis_available():
        r = get_redis()
        try:
            # LRANGE returns the list left-to-right (oldest → newest)
            raw = await r.lrange(key, -_FETCH_LIMIT, -1)
            if raw:
                await r.expire(key, _TTL_SECONDS)   # refresh TTL on access
                messages = [json.loads(m) for m in raw]
                logger.debug("[HistoryCache] HIT (key=%s, msgs=%d)", key, len(messages))
                return messages
        except Exception as exc:
            logger.warning("[HistoryCache] read error: %s", exc)

    # Cache miss — fetch from Postgres
    logger.debug("[HistoryCache] MISS — fetching from Postgres (key=%s)", key)
    try:
        import asyncio
        res = await asyncio.to_thread(_fetch_postgres_history, db, agent_id, user_id, is_public, _FETCH_LIMIT)
        if res.data:
            msgs = [{"role": m["role"], "content": m["content"]} for m in reversed(res.data)]
            # Populate Redis for next time (fire-and-forget)
            if await redis_available():
                asyncio.create_task(_hydrate_redis(key, msgs))
            return msgs
    except Exception as exc:
        logger.warning("[HistoryCache] Postgres fallback error: %s", exc)

    return []


async def get_history_for_ui(
    agent_id: str,
    user_id: str,
    db,
    is_public: bool = False,
) -> List[Dict[str, str]]:
    """
    Return the last 50 messages for the chat UI display.
    Redis-first; falls back to Postgres on miss.
    """
    import asyncio

    key = _history_key(agent_id, user_id)

    if await redis_available():
        r = get_redis()
        try:
            raw = await r.lrange(key, -50, -1)
            if raw:
                await r.expire(key, _TTL_SECONDS)
                messages = [json.loads(m) for m in raw]
                logger.debug("[HistoryCache] UI HIT (key=%s, msgs=%d)", key, len(messages))
                return messages
        except Exception as exc:
            logger.warning("[HistoryCache] UI read error: %s", exc)

    # Postgres fallback
    try:
        res = await asyncio.to_thread(_fetch_postgres_history_50, db, agent_id, user_id, is_public)
        if res.data:
            return [{"role": m["role"], "content": m["content"]} for m in reversed(res.data)]
    except Exception as exc:
        logger.warning("[HistoryCache] UI Postgres fallback error: %s", exc)

    return []


async def append_messages(
    agent_id: str,
    user_id: str,
    messages: List[Dict[str, str]],
) -> None:
    """
    Append one or more messages to the Redis history list.
    Trims to MAX_MESSAGES and refreshes TTL.
    Fire-and-forget — errors are logged, not raised.
    """
    if not await redis_available():
        return

    r = get_redis()
    key = _history_key(agent_id, user_id)

    try:
        pipe = r.pipeline()
        for msg in messages:
            pipe.rpush(key, json.dumps({"role": msg["role"], "content": msg["content"]}))
        pipe.ltrim(key, -_MAX_MESSAGES, -1)    # keep only the last MAX_MESSAGES
        pipe.expire(key, _TTL_SECONDS)
        await pipe.execute()
        logger.debug("[HistoryCache] Appended %d messages to %s", len(messages), key)
    except Exception as exc:
        logger.warning("[HistoryCache] append error: %s", exc)


async def _hydrate_redis(key: str, messages: List[Dict[str, str]]) -> None:
    """Populate Redis from a list of messages fetched from Postgres."""
    r = get_redis()
    if not r:
        return
    try:
        pipe = r.pipeline()
        pipe.delete(key)
        for msg in messages:
            pipe.rpush(key, json.dumps({"role": msg["role"], "content": msg["content"]}))
        pipe.ltrim(key, -_MAX_MESSAGES, -1)
        pipe.expire(key, _TTL_SECONDS)
        await pipe.execute()
        logger.debug("[HistoryCache] Hydrated Redis key %s with %d messages", key, len(messages))
    except Exception as exc:
        logger.warning("[HistoryCache] hydrate error: %s", exc)
