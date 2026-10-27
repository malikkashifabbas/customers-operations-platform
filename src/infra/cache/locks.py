"""Redis lock: only one holder at a time, auto-expires if the holder crashes, released only by its owner."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from . import keys
from .client import get_redis

# Delete the key only if it still holds OUR token; otherwise we could release a lock someone else took after ours expired.
_RELEASE_SCRIPT = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"


def acquire(name: str, ttl_seconds: int = 60) -> str | None:
    token = uuid.uuid4().hex
    acquired = get_redis().set(keys.lock(name), token, nx=True, ex=ttl_seconds)
    return token if acquired else None


def release(name: str, token: str) -> None:
    get_redis().eval(_RELEASE_SCRIPT, 1, keys.lock(name), token)


@contextmanager
def redis_lock(name: str, ttl_seconds: int = 60) -> Iterator[bool]:
    token = acquire(name, ttl_seconds)
    try:
        yield token is not None
    finally:
        if token is not None:
            release(name, token)
