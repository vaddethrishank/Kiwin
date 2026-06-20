"""
semantic_cache.py
─────────────────
Redis-backed semantic cache for LLM responses.

How it works
────────────
  SET  → store {embedding (JSON), answer} under  semcache:{agent_id}:{uuid}
  GET  → scan all semcache:{agent_id}:* keys, compute cosine similarity
         between the incoming query embedding and each stored embedding.
         If similarity ≥ threshold → return the cached answer (cache HIT).

This requires ONLY plain Redis (no Redis Stack / RediSearch module).
The cosine similarity is computed locally in Python using numpy — fast
and zero extra dependencies beyond what LangChain already pulls in.

Key schema
──────────
  semcache:{agent_id}:{uuid4}
    embedding  = JSON list[float] (768-dim Gemini embedding)
    answer     = str (full LLM response)
    question   = str (original question, for debugging)

TTL: configurable via settings.REDIS_CACHE_TTL (default 3600 s = 1 hour)
"""

import json
import logging
import uuid
from typing import List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.redis_client import get_redis, redis_available

logger = logging.getLogger(__name__)

_KEY_PREFIX = "semcache"


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _cache_key(agent_id: str, entry_id: str) -> str:
    return f"{_KEY_PREFIX}:{agent_id}:{entry_id}"


def _scan_pattern(agent_id: str) -> str:
    return f"{_KEY_PREFIX}:{agent_id}:*"


# ── Public API ────────────────────────────────────────────────────────────────

async def get_cached_response(
    agent_id: str,
    query_embedding: List[float],
) -> Optional[str]:
    """
    Look up a semantically similar cached response.

    Returns the cached LLM answer string if a match is found,
    or None on a cache miss.
    """
    if not await redis_available():
        return None

    r = get_redis()
    threshold = settings.REDIS_SEMANTIC_CACHE_THRESHOLD

    try:
        # Scan all cache entries for this agent
        pattern = _scan_pattern(agent_id)
        keys = []
        async for key in r.scan_iter(match=pattern, count=100):
            keys.append(key)

        if not keys:
            return None

        best_score = 0.0
        best_answer: Optional[str] = None

        # Batch-fetch all entries (pipeline for speed)
        pipe = r.pipeline()
        for key in keys:
            pipe.hgetall(key)
        entries = await pipe.execute()

        for entry in entries:
            if not entry or "embedding" not in entry or "answer" not in entry:
                continue
            try:
                cached_vec = json.loads(entry["embedding"])
                score = _cosine_similarity(query_embedding, cached_vec)
                if score > best_score:
                    best_score = score
                    best_answer = entry["answer"]
            except Exception:
                continue

        if best_score >= threshold and best_answer is not None:
            logger.info(
                "[SemanticCache] HIT (agent=%s, similarity=%.4f)", agent_id, best_score
            )
            return best_answer

        logger.debug(
            "[SemanticCache] MISS (agent=%s, best_similarity=%.4f)", agent_id, best_score
        )
        return None

    except Exception as exc:
        logger.warning("[SemanticCache] get error: %s", exc)
        return None


async def set_cached_response(
    agent_id: str,
    question: str,
    query_embedding: List[float],
    answer: str,
) -> None:
    """
    Store an LLM answer in the semantic cache with a TTL.
    Fire-and-forget — errors are logged but not raised.
    """
    if not await redis_available():
        return

    r = get_redis()
    ttl = settings.REDIS_CACHE_TTL

    try:
        entry_id = str(uuid.uuid4())
        key = _cache_key(agent_id, entry_id)

        await r.hset(key, mapping={
            "embedding": json.dumps(query_embedding),
            "answer": answer,
            "question": question[:500],  # store truncated question for debugging
        })
        await r.expire(key, ttl)

        logger.debug(
            "[SemanticCache] Stored (agent=%s, key=%s, ttl=%ds)", agent_id, key, ttl
        )
    except Exception as exc:
        logger.warning("[SemanticCache] set error: %s", exc)


async def invalidate_agent_cache(agent_id: str) -> int:
    """
    Delete all semantic cache entries for an agent.
    Useful when agent knowledge base changes (new file uploaded).
    Returns the number of deleted keys.
    """
    if not await redis_available():
        return 0

    r = get_redis()
    deleted = 0
    try:
        pattern = _scan_pattern(agent_id)
        async for key in r.scan_iter(match=pattern):
            await r.delete(key)
            deleted += 1
        logger.info("[SemanticCache] Invalidated %d entries for agent %s", deleted, agent_id)
    except Exception as exc:
        logger.warning("[SemanticCache] invalidate error: %s", exc)
    return deleted
