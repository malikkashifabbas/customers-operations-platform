"""Live ticket updates for the SSE endpoint, read from the ticket's Redis Stream (replayable, resumable)."""

import re
import time
from collections.abc import Iterator

from core.limits import SSE_HEARTBEAT_SECONDS, SSE_RETRY_MILLISECONDS, TICKET_STREAM_TIMEOUT_SECONDS
from core.sse import heartbeat, retry, sse
from infra.cache import keys, streams

from .models import Ticket, TicketStatus

FINAL_EVENTS = {"answered", "failed"}
_STREAM_ID = re.compile(r"^\d+-\d+$")


def resume_from(last_event_id: str | None) -> str:
    """Start after the browser's Last-Event-ID if it is a valid stream id, otherwise replay from the beginning."""
    return last_event_id if last_event_id and _STREAM_ID.match(last_event_id) else "0"


def ticket_events(ticket: Ticket, after_id: str = "0") -> Iterator[str]:
    stream = keys.ticket_events(str(ticket.public_id))
    yield retry(SSE_RETRY_MILLISECONDS)
    ticket.refresh_from_db(fields=["status", "reply"])
    yield sse("status", {"status": ticket.status})

    # Old ticket whose stream already expired: the database is the only record, so answer from it.
    if ticket.status != TicketStatus.OPEN and not streams.exists(stream):
        yield sse(ticket.status, {"reply": ticket.reply})
        return

    deadline = time.monotonic() + TICKET_STREAM_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        entries = streams.read_after(stream, after_id, block_ms=SSE_HEARTBEAT_SECONDS * 1000)
        if not entries:
            yield heartbeat()
            continue
        for entry_id, event, data in entries:
            after_id = entry_id
            yield sse(event, data, event_id=entry_id)
            if event in FINAL_EVENTS:
                return
    yield sse("timeout", {"message": "No update yet; reconnect or fetch the ticket again later."})
