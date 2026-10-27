"""Support agent: input guard -> ReAct loop over read-only tools -> output guard; a blocked question goes to a fixed refusal."""

import logging
from pathlib import Path

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from agents.core.prompts import load_prompt
from infra.llm.gateway import get_chat_model

from . import guards
from .context import SupportContext
from .state import SupportState
from .tools import TOOLS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v3.md"


def guard_input(state: SupportState, runtime: Runtime[SupportContext]) -> dict:
    context = runtime.context
    message = str(state["messages"][-1].content)
    previous_language = state.get("language", "english")
    reset = {"output_flags": []}
    if guards.mentions_other_person(message, context.customer):
        return {**reset, "blocked_reason": "other_customer", "language": previous_language}
    try:
        verdict = guards.classify_input(
            message,
            company_name=context.tenant.name,
            customer_name=context.customer.full_name,
            previous_language=previous_language,
        )
    except Exception:
        # Fail open: the tools still only see this customer's data, so a guard outage must not stop support.
        logger.warning("input guard failed, letting the message through", exc_info=True)
        return {**reset, "blocked_reason": None, "language": previous_language}
    blocked = None if verdict.decision == "allowed" else verdict.decision
    return {**reset, "blocked_reason": blocked, "language": verdict.language}


def route_after_input(state: SupportState) -> str:
    return "refuse" if state.get("blocked_reason") else "agent"


def refuse(state: SupportState) -> dict:
    text = guards.REFUSALS[state["blocked_reason"]][state.get("language", "english")]
    return {"messages": [AIMessage(text)]}


def agent(state: SupportState, runtime: Runtime[SupportContext]) -> dict:
    prompt = load_prompt(
        SYSTEM_PROMPT,
        company_name=runtime.context.tenant.name,
        reply_language=guards.REPLY_LANGUAGE[state.get("language", "english")],
    )
    llm = get_chat_model().bind_tools(TOOLS)
    response = llm.invoke([SystemMessage(prompt), *state["messages"]])
    return {"messages": [response]}


def guard_output(state: SupportState) -> dict:
    reply = state["messages"][-1]
    flags = guards.check_output(str(reply.content), state["messages"])
    if not flags:
        return {"output_flags": []}
    logger.warning("output guard replaced a reply: %s", flags)
    safe = guards.SAFE_FALLBACK[state.get("language", "english")]
    # Same id, so add_messages replaces the bad reply instead of appending a second one.
    return {"messages": [AIMessage(safe, id=reply.id)], "output_flags": flags}


def build_graph(checkpointer=None):
    builder = StateGraph(SupportState, context_schema=SupportContext)
    builder.add_node("guard_input", guard_input)
    builder.add_node("refuse", refuse)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_node("guard_output", guard_output)

    builder.add_edge(START, "guard_input")
    builder.add_conditional_edges("guard_input", route_after_input, {"agent": "agent", "refuse": "refuse"})
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "guard_output"})
    builder.add_edge("tools", "agent")
    builder.add_edge("guard_output", END)
    builder.add_edge("refuse", END)
    return builder.compile(checkpointer=checkpointer)
