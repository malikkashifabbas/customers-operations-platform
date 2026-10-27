"""Fixed-window rate limit: count hits per subject per window; the counter key expires by itself."""

import time

from . import keys
from .client import get_redis


def allow(*, scope: str, subject: str, limit: int, window_seconds: int) -> bool:
    window = int(time.time() // window_seconds)
    key = keys.rate(scope, subject, window)
    pipe = get_redis().pipeline()
    pipe.incr(key)  # atomic: concurrent requests each get their own number
    pipe.expire(key, window_seconds, nx=True)
    count, _ = pipe.execute()
    return count <= limit
