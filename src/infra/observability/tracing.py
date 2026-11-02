"""LLM tracing to LangSmith (cloud). Off unless LANGSMITH_TRACING=true.

Callers only ever use trace_config(), flush(), langsmith_client() and the span helpers; nothing else in the code knows LangSmith exists.

Lesson 16C: one ticket is one trace across processes. The API span's headers travel outbox -> relay -> Kafka -> worker.
"""

import logging
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any

from config.env import env

PHONE_RE = re.compile(r"\+?\d[\d\s-]{8,}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CNIC_RE = re.compile(r"\b\d{5}-\d{7}-\d\b")
logger = logging.getLogger(__name__)


def mask(data: Any) -> Any:
    """Hide personal data before it leaves the process: traces keep the shape of the text, not the person."""
    if isinstance(data, str):
        return PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", CNIC_RE.sub("[cnic]", data)))
    if isinstance(data, dict):
        return {key: mask(value) for key, value in data.items()}
    if isinstance(data, list | tuple):
        return [mask(value) for value in data]
    if hasattr(data, "model_dump"):
        # LangChain messages (HumanMessage, AIMessage...) are pydantic objects, not dicts: mask their fields too.
        return mask(data.model_dump())
    return data


@lru_cache(maxsize=1)
def langsmith_client():
    """The LangSmith client (also used for datasets and experiments), or None when tracing is off."""
    if not env.langsmith_tracing or env.langsmith_api_key is None:
        return None
    from langsmith import Client  # imported lazily so the app does not touch LangSmith when tracing is off

    # pydantic-settings reads .env into Env, not os.environ; LangChain runs started by evaluate() look in os.environ.
    os.environ.setdefault("LANGSMITH_API_KEY", env.langsmith_api_key.get_secret_value())
    os.environ.setdefault("LANGSMITH_ENDPOINT", env.langsmith_endpoint)
    hide = mask if env.langsmith_mask_pii else None
    return Client(
        api_url=env.langsmith_endpoint,
        api_key=env.langsmith_api_key.get_secret_value(),
        hide_inputs=hide,
        hide_outputs=hide,
    )


def trace_config(
    config: dict, *, session_id: str, user_id: str, tenant: str, channel: str, tags: list[str] | None = None
) -> dict:
    """Return the LangGraph config with the LangSmith tracer and labels added (unchanged when tracing is off)."""
    client = langsmith_client()
    if client is None:
        return config
    from langchain_core.tracers.langchain import LangChainTracer

    return {
        **config,
        "run_name": f"support-{channel}",
        "callbacks": [*config.get("callbacks", []), LangChainTracer(project_name=env.langsmith_project, client=client)],
        "tags": [*config.get("tags", []), f"channel:{channel}", f"tenant:{tenant}", *(tags or [])],
        # LangSmith "Threads" group runs by session_id; LangGraph also adds the checkpointer thread_id by itself.
        "metadata": {**config.get("metadata", {}), "session_id": session_id, "user_id": user_id, "tenant": tenant, "channel": channel},
    }


def _parent_run(headers: Mapping | None, client, **kwargs):
    """The remote parent run, or None: a bad or missing header starts a new trace and must never stop the work."""
    if not headers:
        return None
    from langsmith import RunTree

    try:
        return RunTree.from_headers(dict(headers), client=client, project_name=env.langsmith_project, **kwargs)
    except Exception:
        logger.warning("ignoring bad trace headers", exc_info=True)
        return None


@contextmanager
def trace_span(name: str, *, parent: Mapping | None = None, metadata: dict | None = None) -> Iterator[None]:
    """One named step of the trace; LLM runs and events published inside it become its children."""
    client = langsmith_client()
    if client is None:
        yield
        return
    from langsmith import run_helpers

    # tracing_context: the .env flag never reaches os.environ, so LangSmith must be told it is on.
    with run_helpers.tracing_context(enabled=True, client=client, project_name=env.langsmith_project):
        with run_helpers.trace(
            name, client=client, project_name=env.langsmith_project, parent=_parent_run(parent, client), metadata=metadata
        ):
            yield


def label_span(**metadata: str) -> None:
    """Add labels to the current span, for values only known after it started (the new ticket's id)."""
    if langsmith_client() is None:
        return
    from langsmith import run_helpers

    run = run_helpers.get_current_run_tree()
    if run is not None:
        run.add_metadata(metadata)


def current_trace_headers() -> dict[str, str]:
    """Headers that let another process continue the current span's trace; empty when there is no span."""
    if langsmith_client() is None:
        return {}
    from langsmith import run_helpers

    run = run_helpers.get_current_run_tree()
    return run.to_headers() if run is not None else {}


def record_span(name: str, *, parent: Mapping | None, start_time: datetime, metadata: dict | None = None) -> None:
    """A finished step measured from the outside (time spent waiting in a queue); needs a parent to attach to."""
    client = langsmith_client()
    # A remote parent's start time is a placeholder (now), and LangSmith moves a child that starts before its parent up to it.
    remote_parent = _parent_run(parent, client, start_time=start_time) if client is not None else None
    if remote_parent is None:
        return
    try:
        run = remote_parent.create_child(name=name, run_type="chain", start_time=start_time, extra={"metadata": metadata or {}})
        run.end()
        run.post()
    except Exception:
        logger.warning("could not record span %s", name, exc_info=True)


def flush() -> None:
    """Short scripts must call this before exiting; long-running processes send traces in the background."""
    if langsmith_client() is not None:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
