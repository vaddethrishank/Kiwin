import time
from typing import Optional
from fastapi import HTTPException
from app.core.redis_client import get_redis, redis_available
import logging

logger = logging.getLogger(__name__)

# Lua script for atomic Token Bucket rate limiting
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = 1

local bucket = redis.call("HMGET", key, "tokens", "last_update")
local tokens = tonumber(bucket[1])
local last_update = tonumber(bucket[2])

if not tokens then
    tokens = capacity
    last_update = now
else
    local time_passed = math.max(0, now - last_update)
    local refill = time_passed * refill_rate
    tokens = math.min(capacity, tokens + refill)
    last_update = now
end

if tokens >= requested then
    tokens = tokens - requested
    redis.call("HMSET", key, "tokens", tokens, "last_update", last_update)
    -- Expire the key if idle for twice the time it takes to fully refill
    local expire_time = math.ceil(capacity / refill_rate) * 2
    redis.call("EXPIRE", key, expire_time)
    return 1 -- allowed
else
    redis.call("HMSET", key, "tokens", tokens, "last_update", last_update)
    return 0 -- rejected
end
"""

_script_sha: Optional[str] = None

async def check_rate_limit(identifier: str, capacity: int = 10, refill_rate: float = 0.2):
    """
    Checks if the given identifier is within the rate limit.
    Raises HTTPException(429) if the limit is exceeded.
    
    Args:
        identifier: The unique key to rate limit on (e.g., "ratelimit:ip:192.168.1.1" or "ratelimit:session:1234")
        capacity: Maximum burst of requests allowed.
        refill_rate: Tokens added per second. (e.g., 0.2 = 1 token every 5 seconds)
    """
    if not await redis_available():
        # If Redis is down, we silently bypass rate limiting so the app stays up.
        return

    r = get_redis()
    if not r:
        return
        
    global _script_sha
    try:
        if _script_sha is None:
            _script_sha = await r.script_load(TOKEN_BUCKET_SCRIPT)
            
        now = time.time()
        
        # Run the Lua script atomically
        allowed = await r.evalsha(
            _script_sha, 
            1, # number of keys
            identifier, 
            capacity, 
            refill_rate, 
            now
        )
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise HTTPException(
                status_code=429, 
                detail="Too many requests. Please slow down."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # If there's a redis error (e.g., script flush), clear sha and allow request
        logger.error(f"[RateLimit] Error: {e}")
        _script_sha = None
