"""Redis caching layer for wallet profiles and feature vectors."""

import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from api.config import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the shared Redis client (lazy init)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_profile_cache(address: str, chain: str) -> dict | None:
    """Fetch cached wallet profile. Returns None on cache miss."""
    key = f"profile:{chain}:{address}"
    raw = await get_redis().get(key)
    if raw is None:
        return None
    logger.debug("cache.hit", key=key)
    return json.loads(raw)


async def set_profile_cache(address: str, chain: str, data: dict) -> None:
    """Store wallet profile in Redis with TTL."""
    key = f"profile:{chain}:{address}"
    await get_redis().setex(key, settings.profile_cache_ttl, json.dumps(data))
    logger.debug("cache.set", key=key, ttl=settings.profile_cache_ttl)


async def get_feature_cache(address: str, chain: str) -> dict | None:
    """Fetch cached feature vector."""
    key = f"features:{chain}:{address}"
    raw = await get_redis().get(key)
    return json.loads(raw) if raw else None


async def set_feature_cache(address: str, chain: str, features: dict) -> None:
    """Store feature vector in Redis with TTL."""
    key = f"features:{chain}:{address}"
    await get_redis().setex(key, settings.feature_cache_ttl, json.dumps(features))
