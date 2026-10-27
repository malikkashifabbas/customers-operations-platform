"""Remember processed event ids so a re-delivered Kafka event has no second effect."""

from . import keys
from .client import get_redis

DONE_TTL_SECONDS = 7 * 24 * 3600


def is_done(event_id: str) -> bool:
    return bool(get_redis().exists(keys.event_done(event_id)))


def mark_done(event_id: str) -> None:
    get_redis().set(keys.event_done(event_id), 1, ex=DONE_TTL_SECONDS)
