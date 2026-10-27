"""Server-Sent Events formatting: optional 'id:', then 'event:' and 'data:', then a blank line."""

import json


def sse(event: str, data: dict, event_id: str | None = None) -> str:
    # With an id, a reconnecting browser sends it back as Last-Event-ID so the server can resume after it.
    id_line = f"id: {event_id}\n" if event_id else ""
    return f"{id_line}event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def retry(milliseconds: int) -> str:
    return f"retry: {milliseconds}\n\n"


def heartbeat() -> str:
    # A comment line: clients ignore it, but proxies and load balancers see traffic and keep the connection open.
    return ": keep-alive\n\n"
