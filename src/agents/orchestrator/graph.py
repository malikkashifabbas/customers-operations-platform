"""Multi-agent support graph: input guard -> supervisor -> domain specialists in parallel (Send) -> compose -> output guard.

Guards, refusal and the output-guard rewrite rules are reused from agents/domains/support/graph.py.
"""

from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Send

from agents.core.domain import DomainSpec
from agents.core.prompts import load_prompt
from agents.core.react_subgraph import DomainState
from agents.domains.support import graph as support
from agents.domains.support.context import SupportContext
from agents.domains.support.guards import REPLY_LANGUAGE
from agents.domains.support.state import GuardUsage, SupportState
from agents.registry import DOMAINS
from infra.llm.gateway import get_chat_model

from .supervisor import supervisor

COMPOSE_PROMPT = Path(__file__).parent / "prompts" / "compose.v1.md"
NO_USAGE: GuardUsage = {"llm_calls": 0, "tokens": 0}


class OrchestratorState(SupportState):
    routes: list[str]
    routing_usage: GuardUsage  # supervisor + specialist drafts that compose merged away (not visible in messages)


def _add_usage(usage: GuardUsage, messages: list[BaseMessage]) -> GuardUsage:
    # Only LLM replies carry usage_metadata; a fixed-text reply (knowledge) is not an LLM call.
    llm_replies = [m for m in messages if isinstance(m, AIMessage) and m.usage_metadata]
    tokens = sum(m.usage_metadata.get("total_tokens", 0) for m in llm_replies)
    return {"llm_calls": usage["llm_calls"] + len(llm_replies), "tokens": usage["tokens"] + tokens}


def _this_turn(messages: list[BaseMessage]) -> list[BaseMessage]:
    last_human = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    return messages[last_human:]


def guard_input(state: OrchestratorState, runtime: Runtime[SupportContext]) -> dict:
    # A refused turn skips the supervisor, so routing fields are reset here or the last turn's values would leak.
    return {**support.guard_input(state, runtime), "routes": [], "routing_usage": NO_USAGE}


def specialist(spec: DomainSpec):
    """Wrap a domain subgraph as a node that returns only the NEW messages, tagged with the domain name."""
    subgraph = spec.build()

    def run(state: DomainState, runtime: Runtime[SupportContext]) -> dict:
        result = subgraph.invoke(state, context=runtime.context)
        new = result["messages"][len(state["messages"]) :]
        if new and isinstance(new[-1], AIMessage) and not new[-1].tool_calls:
            new[-1].response_metadata["domain"] = spec.name
        return {"messages": new}

    return run


def route_to_domains(state: OrchestratorState) -> list[Send]:
    payload = {"messages": state["messages"], "language": state.get("language", "english")}
    return [Send(name, payload) for name in state["routes"]]


def compose(state: OrchestratorState, runtime: Runtime[SupportContext]) -> dict:
    turn = _this_turn(state["messages"])
    drafts = [m for m in turn if isinstance(m, AIMessage) and m.response_metadata.get("domain") and not m.tool_calls]
    rewriting = bool(state.get("guard_feedback"))
    if len(drafts) == 1 and not rewriting:
        return {}  # one specialist answered: its reply is already the final reply, no extra LLM call

    question = str(turn[0].content)
    facts = "\n".join(f"- {m.name}: {m.content}" for m in turn if isinstance(m, ToolMessage))
    # "billing specialist:" and not "[billing]": square brackets are reserved for real [source] citations.
    answers = "\n".join(f"{m.response_metadata['domain']} specialist: {m.content}" for m in drafts)
    prompt = load_prompt(
        COMPOSE_PROMPT, company_name=runtime.context.tenant.name, reply_language=REPLY_LANGUAGE[state.get("language", "english")]
    )
    if rewriting:
        prompt += f"\n\nThe previous reply was rejected by a safety check. Write it again and {state['guard_feedback']}."
    material = f"Customer message:\n{question}\n\nTool results:\n{facts or '(none)'}\n\nSpecialist answers:\n{answers or '(none)'}"
    reply = get_chat_model().invoke([SystemMessage(prompt), HumanMessage(material)])
    usage = _add_usage(state.get("routing_usage") or NO_USAGE, drafts)
    return {"messages": [*[RemoveMessage(id=m.id) for m in drafts], reply], "routing_usage": usage, "guard_feedback": None}


def route_after_output(state: OrchestratorState) -> str:
    return "compose" if state.get("guard_feedback") else END


def build_graph(checkpointer=None):
    builder = StateGraph(OrchestratorState, context_schema=SupportContext)
    builder.add_node("guard_input", guard_input)
    builder.add_node("refuse", support.refuse)
    builder.add_node("supervisor", supervisor)
    for name, spec in DOMAINS.items():
        builder.add_node(name, specialist(spec), input_schema=DomainState)
        builder.add_edge(name, "compose")
    builder.add_node("compose", compose)
    builder.add_node("guard_output", support.guard_output)

    builder.add_edge(START, "guard_input")
    builder.add_conditional_edges("guard_input", support.route_after_input, {"agent": "supervisor", "refuse": "refuse"})
    builder.add_conditional_edges("supervisor", route_to_domains, list(DOMAINS))
    builder.add_edge("compose", "guard_output")
    builder.add_conditional_edges("guard_output", route_after_output, {"compose": "compose", END: END})
    builder.add_edge("refuse", END)
    return builder.compile(checkpointer=checkpointer)
