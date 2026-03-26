"""Token bucket rate limiting via Redis."""

import time

import redis.asyncio as aioredis
import structlog

from api.config import settings
from api.services.cache import get_redis

logger = structlog.get_logger()

# Lua script for atomic token bucket check+decrement
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local window = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, now .. '-' .. math.random())
    redis.call('EXPIRE', key, window)
    return 1
else
    return 0
end
"""


async def check_rate_limit(api_key: str, tier: str = "free") -> bool:
    """Return True if the request is within rate limits, False otherwise.

    Args:
        api_key: The API key making the request.
        tier: "free" or "pro" — determines daily limit.

    Returns:
        True if allowed, False if rate limit exceeded.
    """
    limit = settings.free_tier_daily_limit if tier == "free" else settings.pro_tier_daily_limit
    window = 86_400  # 24 hours in seconds
    now = int(time.time())
    key = f"ratelimit:{api_key}"

    redis = get_redis()
    result = await redis.eval(_RATE_LIMIT_SCRIPT, 1, key, limit, now, window)  # type: ignore[arg-type]
    allowed = bool(result)
    if not allowed:
        logger.warning("rate_limit.exceeded", api_key=api_key[:8] + "...", tier=tier)
    return allowed
