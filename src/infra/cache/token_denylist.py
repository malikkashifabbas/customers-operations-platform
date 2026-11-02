"""Logged-out tokens: a JWT cannot be recalled, so its id waits here until it would have expired anyway."""

from . import keys
from .client import get_redis


def revoke(jti: str, seconds: int) -> None:
    if seconds > 0:
        get_redis().set(keys.revoked_token(jti), "1", ex=seconds)


def is_revoked(jti: str) -> bool:
    return bool(get_redis().exists(keys.revoked_token(jti)))
