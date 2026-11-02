"""Lock a login after repeated failures, the policy's 5 attempts and 30 minutes. Redis keys hold a hash, never a phone number."""

import hashlib

from core.limits import LOGIN_LOCK_SECONDS, LOGIN_MAX_FAILURES

from . import keys
from .client import get_redis


def _key(attempt: str) -> str:
    return keys.login_failures(hashlib.sha256(attempt.encode()).hexdigest())


def is_locked(attempt: str) -> bool:
    return int(get_redis().get(_key(attempt)) or 0) >= LOGIN_MAX_FAILURES


def record_failure(attempt: str) -> None:
    key = _key(attempt)
    pipe = get_redis().pipeline()
    pipe.incr(key)
    pipe.expire(key, LOGIN_LOCK_SECONDS)
    pipe.execute()


def clear(attempt: str) -> None:
    get_redis().delete(_key(attempt))
