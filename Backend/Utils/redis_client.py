import os
import redis.asyncio as aioredis

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        username = os.getenv("REDIS_USER") or None
        password = os.getenv("REDIS_PASSWORD") or None
        _redis = aioredis.Redis(
            host=host,
            port=port,
            username=username,
            password=password,
            decode_responses=False,
        )
    return _redis


async def close_redis():
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
