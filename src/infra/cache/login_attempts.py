"""Lock a login after repeated failures, the policy's 5 attempts and 30 minutes. Redis keys hold a hash, never a phone number."""

import hashlib

from core.limits import LOGIN_LOCK_SECONDS, LOGIN_MAX_FAILURES

from . import keys
from .client import get_redis


def _key(attempt: str) -> str:
    return keys.login_failures(hashlib.sha256(attempt.encode()).hexdigest())


def is_locked(attempt: str, max_failures: int = LOGIN_MAX_FAILURES) -> bool:
    return int(get_redis().get(_key(attempt)) or 0) >= max_failures


def record_failure(attempt: str, lock_seconds: int = LOGIN_LOCK_SECONDS) -> None:
    key = _key(attempt)
    pipe = get_redis().pipeline()
    pipe.incr(key)
    pipe.expire(key, lock_seconds)
    pipe.execute()


def clear(attempt: str) -> None:
    get_redis().delete(_key(attempt))
