"""Redis Streams: an append-only log with ids. Unlike Pub/Sub, a late listener can replay from the start or resume after an id."""

import json

from .client import get_redis

STREAM_MAXLEN = 1000  # keep roughly the last 1000 entries per stream
STREAM_TTL_SECONDS = 3600  # the whole stream disappears an hour after its last write


def append(stream: str, event: str, data: dict) -> str:
    pipe = get_redis().pipeline()
    pipe.xadd(stream, {"event": event, "data": json.dumps(data, ensure_ascii=False)}, maxlen=STREAM_MAXLEN, approximate=True)
    pipe.expire(stream, STREAM_TTL_SECONDS)
    entry_id, _ = pipe.execute()
    return entry_id


def exists(stream: str) -> bool:
    return bool(get_redis().exists(stream))


def read_after(stream: str, after_id: str, block_ms: int) -> list[tuple[str, str, dict]]:
    """Entries newer than after_id ('0' = from the start); waits up to block_ms for new ones."""
    result = get_redis().xread({stream: after_id}, count=100, block=block_ms)
    return [
        (entry_id, fields["event"], json.loads(fields["data"]))
        for _name, entries in (result or [])
        for entry_id, fields in entries
    ]
