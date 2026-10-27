"""One shared Redis client (it keeps its own connection pool)."""

from functools import lru_cache

import redis

from config.env import env


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(env.redis_url, decode_responses=True)
