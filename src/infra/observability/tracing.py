"""LLM tracing to self-hosted Langfuse (its SDK exports over OpenTelemetry). Off unless LANGFUSE_ENABLED=true.

Callers only ever use trace_config() and flush(); nothing else in the code knows Langfuse exists.
"""

import re
from functools import lru_cache
from typing import Any

from config.env import env

PHONE_RE = re.compile(r"\+?\d[\d\s-]{8,}\d")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CNIC_RE = re.compile(r"\b\d{5}-\d{7}-\d\b")


def mask(data: Any, **kwargs) -> Any:
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
def _client():
    if not env.langfuse_enabled:
        return None
    from langfuse import Langfuse  # imported lazily so the app does not need Langfuse installed or running when off

    # Keys are passed in, not read from os.environ: pydantic-settings loads .env into Env, not into the process env.
    return Langfuse(
        public_key=env.langfuse_public_key,
        secret_key=env.langfuse_secret_key.get_secret_value(),
        host=env.langfuse_host,
        mask=mask,
    )


def trace_config(
    config: dict, *, session_id: str, user_id: str, tenant: str, channel: str, tags: list[str] | None = None
) -> dict:
    """Return the LangGraph config with the Langfuse callback and labels added (unchanged when tracing is off)."""
    if _client() is None:
        return config
    from langfuse.langchain import CallbackHandler

    metadata = {
        **config.get("metadata", {}),
        # langfuse_* keys are read by the callback: one session per conversation or ticket, one user per customer.
        "langfuse_session_id": session_id,
        "langfuse_user_id": user_id,
        "langfuse_tags": [f"channel:{channel}", f"tenant:{tenant}", *(tags or [])],
        "tenant": tenant,
        "channel": channel,
    }
    return {**config, "callbacks": [*config.get("callbacks", []), CallbackHandler()], "metadata": metadata}


def langfuse_client():
    """The Langfuse client for datasets and experiments (evals, benchmarks), or None when tracing is off."""
    return _client()


def flush() -> None:
    """Short scripts must call this before exiting; long-running processes send traces in the background."""
    client = _client()
    if client is not None:
        client.flush()
