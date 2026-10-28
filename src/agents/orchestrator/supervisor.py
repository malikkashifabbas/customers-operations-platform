"""Supervisor node: an LLM classifier that picks which domain specialists get the latest message (it never answers)."""

import logging
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from agents.core.prompts import load_prompt
from agents.domains.support.context import SupportContext
from agents.registry import DOMAINS
from config.env import env
from infra.llm.gateway import get_chat_model

logger = logging.getLogger(__name__)

SUPERVISOR_PROMPT = Path(__file__).parent / "prompts" / "supervisor.v1.md"
FALLBACK_ROUTES = ["billing", "account"]
TRANSCRIPT_MESSAGES = 6


class Route(BaseModel):
    domains: list[str] = Field(description=f"Specialists to call, one or more of: {', '.join(DOMAINS)}.")


def _transcript(messages: list) -> str:
    """Last few customer/assistant lines only; tool calls and results would just cost tokens here."""
    lines = []
    for message in messages[-TRANSCRIPT_MESSAGES * 3 :]:
        if isinstance(message, HumanMessage):
            lines.append(f"Customer: {message.content}")
        elif isinstance(message, AIMessage) and message.content and not message.tool_calls:
            lines.append(f"Assistant: {message.content}")
    return "\n".join(lines[-TRANSCRIPT_MESSAGES:])


def supervisor(state: dict, runtime: Runtime[SupportContext]) -> dict:
    prompt = load_prompt(
        SUPERVISOR_PROMPT,
        company_name=runtime.context.tenant.name,
        domains="\n".join(f"- {name}: {spec.description}" for name, spec in DOMAINS.items()),
    )
    usage = {"llm_calls": 0, "tokens": 0}
    try:
        llm = get_chat_model(model=env.llm_guard_model).with_structured_output(Route, include_raw=True)
        result = llm.invoke([SystemMessage(prompt), HumanMessage(_transcript(state["messages"]))])
        usage = {"llm_calls": 1, "tokens": (result["raw"].usage_metadata or {}).get("total_tokens", 0)}
        # Keep known names only, in order, without duplicates: the LLM may return "Billing" or invent a domain.
        routes = list(dict.fromkeys(d.strip().lower() for d in (result["parsed"].domains if result["parsed"] else [])))
        routes = [d for d in routes if d in DOMAINS]
    except Exception:
        logger.warning("supervisor failed, using fallback routes", exc_info=True)
        routes = []
    if not routes:
        routes = FALLBACK_ROUTES
    return {"routes": routes, "routing_usage": usage}
