"""Triage node: the input guard and the supervisor in ONE structured LLM call (Lesson 16B, -1 LLM call per message).

Lesson 16A measured guard + supervisor at a third of all tokens; both read the same message, so one call can do both.
The free regex check (another customer's email or phone) still runs first and needs no LLM at all.
"""

import logging
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from agents.core.prompts import load_prompt
from agents.domains.support import guards
from agents.domains.support.context import SupportContext
from agents.domains.support.state import Language
from agents.registry import DOMAINS
from config.env import env
from infra.llm.gateway import get_chat_model

from .supervisor import FALLBACK_ROUTES

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = Path(__file__).parent / "prompts" / "triage.v1.md"
NO_USAGE = {"llm_calls": 0, "tokens": 0}
TRANSCRIPT_MESSAGES = 6


class TriageVerdict(BaseModel):
    decision: Literal["allowed", "other_customer", "prompt_injection", "off_topic"] = Field(description="What kind of message this is.")
    language: Language = Field(description="Language of the customer's latest message.")
    domains: list[str] = Field(description=f"Specialists for an allowed message, from: {', '.join(DOMAINS)}. Empty otherwise.")


def _transcript(messages: list) -> str:
    lines = [
        f"{'Customer' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and m.content and not m.tool_calls)
    ]
    return "\n".join(lines[-TRANSCRIPT_MESSAGES:])


def triage(state: dict, runtime: Runtime[SupportContext]) -> dict:
    context = runtime.context
    message = str(state["messages"][-1].content)
    previous_language = state.get("language", "english")
    # Same per-turn resets as guard_input + supervisor, so nothing from the previous message leaks into this one.
    reset = {"output_flags": [], "guard_feedback": None, "output_retries": 0, "routing_usage": NO_USAGE}
    if guards.mentions_other_person(message, context.customer):
        return {**reset, "blocked_reason": "other_customer", "language": previous_language, "routes": [], "guard_usage": NO_USAGE}

    prompt = load_prompt(
        TRIAGE_PROMPT,
        company_name=context.tenant.name,
        customer_name=context.customer.full_name,
        previous_language=previous_language,
        domains="\n".join(f"- {name}: {spec.description}" for name, spec in DOMAINS.items()),
    )
    request = f"Conversation so far:\n{_transcript(state['messages'][:-1]) or '(none)'}\n\nLatest customer message: {message}"
    try:
        llm = get_chat_model(model=env.llm_guard_model).with_structured_output(TriageVerdict, include_raw=True)
        result = llm.invoke([SystemMessage(prompt), HumanMessage(request)])
        if result["parsed"] is None:
            raise ValueError(f"triage returned no verdict: {result['parsing_error']}")
        verdict: TriageVerdict = result["parsed"]
        tokens = (result["raw"].usage_metadata or {}).get("total_tokens", 0)
    except Exception:
        # Fail open, as before: data access is still limited to this customer by the tools themselves.
        logger.warning("triage failed, letting the message through with fallback routes", exc_info=True)
        return {**reset, "blocked_reason": None, "language": previous_language, "routes": FALLBACK_ROUTES, "guard_usage": NO_USAGE}

    blocked = None if verdict.decision == "allowed" else verdict.decision
    routes = [d for d in dict.fromkeys(name.strip().lower() for name in verdict.domains) if d in DOMAINS]
    return {
        **reset,
        "blocked_reason": blocked,
        "language": verdict.language,
        "routes": [] if blocked else (routes or FALLBACK_ROUTES),
        "guard_usage": {"llm_calls": 1, "tokens": tokens},
    }
