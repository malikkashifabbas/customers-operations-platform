"""LLM tracing to LangSmith (cloud). Off unless LANGSMITH_TRACING=true.

Callers only ever use trace_config(), flush() and langsmith_client(); nothing else in the code knows LangSmith exists.
"""

import os
import re
from functools import lru_cache
from typing import Any

from config.env import env

PHONE_RE = re.compile(r"\+?\d[\d\s-]{8,}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CNIC_RE = re.compile(r"\b\d{5}-\d{7}-\d\b")


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


def flush() -> None:
    """Short scripts must call this before exiting; long-running processes send traces in the background."""
    if langsmith_client() is not None:
        from langchain_core.tracers.langchain import wait_for_all_tracers

        wait_for_all_tracers()
