"""Support agent: input guard -> ReAct loop over tools -> output guard (one rewrite, then fallback); a blocked question goes to a fixed refusal."""

import logging
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, RemoveMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from agents.core.prompts import load_prompt
from infra.llm.gateway import get_chat_model

from . import guards
from .context import SupportContext
from .state import GuardUsage, SupportState
from .tools import ALL_TOOLS, tools_for

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v4.md"
MAX_OUTPUT_RETRIES = 1

REFUND_RULE = {
    "chat": "you cannot refund in this chat. If the customer wants a refund, tell them to open a support ticket, where a staff member can approve it.",
    "ticket": (
        "only through request_refund, and only when the customer clearly asks to refund a specific order. "
        "A staff member must approve it. Never say a refund is done unless the tool result says refund_status is done; "
        "if it was rejected, tell the customer and include the staff note if there is one."
    ),
}


def _capabilities(tools: list) -> str:
    return "\n".join(f"- {tool.name}: {tool.description.split('. ')[0].rstrip('.')}." for tool in tools)


def _usage_plus(state: SupportState, message: BaseMessage) -> GuardUsage:
    usage = state.get("guard_usage") or {"llm_calls": 0, "tokens": 0}
    tokens = (getattr(message, "usage_metadata", None) or {}).get("total_tokens", 0)
    return {"llm_calls": usage["llm_calls"] + 1, "tokens": usage["tokens"] + tokens}


def guard_input(state: SupportState, runtime: Runtime[SupportContext]) -> dict:
    context = runtime.context
    message = str(state["messages"][-1].content)
    previous_language = state.get("language", "english")
    reset = {"output_flags": [], "guard_feedback": None, "output_retries": 0, "guard_usage": {"llm_calls": 0, "tokens": 0}}
    if guards.mentions_other_person(message, context.customer):
        return {**reset, "blocked_reason": "other_customer", "language": previous_language}
    try:
        verdict, tokens = guards.classify_input(
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
    usage = {"llm_calls": 1, "tokens": tokens}
    return {**reset, "blocked_reason": blocked, "language": verdict.language, "guard_usage": usage}


def route_after_input(state: SupportState) -> str:
    return "refuse" if state.get("blocked_reason") else "agent"


def refuse(state: SupportState) -> dict:
    text = guards.REFUSALS[state["blocked_reason"]][state.get("language", "english")]
    return {"messages": [AIMessage(text)]}


def agent(state: SupportState, runtime: Runtime[SupportContext]) -> dict:
    context = runtime.context
    tools = tools_for(context)
    prompt = load_prompt(
        SYSTEM_PROMPT,
        company_name=context.tenant.name,
        capabilities=_capabilities(tools),
        refund_rule=REFUND_RULE[context.channel],
        reply_language=guards.REPLY_LANGUAGE[state.get("language", "english")],
    )
    if state.get("guard_feedback"):
        prompt += f"\n\nYour previous reply was rejected by a safety check. Write it again and {state['guard_feedback']}."
    llm = get_chat_model().bind_tools(tools)
    response = llm.invoke([SystemMessage(prompt), *state["messages"]])
    return {"messages": [response]}


def guard_output(state: SupportState) -> dict:
    reply = state["messages"][-1]
    flags = guards.check_output(str(reply.content), state["messages"])
    if not flags:
        return {"guard_feedback": None}
    all_flags = [*state.get("output_flags", []), *flags]
    usage = _usage_plus(state, reply)
    retries = state.get("output_retries", 0)
    if retries < MAX_OUTPUT_RETRIES:
        logger.info("output guard rejected a draft, asking for a rewrite: %s", flags)
        # RemoveMessage deletes the bad draft from history, so the rewrite does not see (or repeat) it.
        return {
            "messages": [RemoveMessage(id=reply.id)],
            "guard_feedback": guards.feedback_for(flags),
            "output_retries": retries + 1,
            "output_flags": all_flags,
            "guard_usage": usage,
        }
    logger.warning("output guard replaced a reply after %s rewrite(s): %s", retries, flags)
    safe = guards.SAFE_FALLBACK[state.get("language", "english")]
    # Same id, so add_messages replaces the bad reply instead of appending a second one.
    return {"messages": [AIMessage(safe, id=reply.id)], "guard_feedback": None, "output_flags": all_flags, "guard_usage": usage}


def route_after_output(state: SupportState) -> str:
    return "agent" if state.get("guard_feedback") else END


def build_graph(checkpointer=None):
    builder = StateGraph(SupportState, context_schema=SupportContext)
    builder.add_node("guard_input", guard_input)
    builder.add_node("refuse", refuse)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(ALL_TOOLS))
    builder.add_node("guard_output", guard_output)

    builder.add_edge(START, "guard_input")
    builder.add_conditional_edges("guard_input", route_after_input, {"agent": "agent", "refuse": "refuse"})
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "guard_output"})
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges("guard_output", route_after_output, {"agent": "agent", END: END})
    builder.add_edge("refuse", END)
    return builder.compile(checkpointer=checkpointer)
