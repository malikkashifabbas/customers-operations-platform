"""Support agent: a ReAct loop over read-only tools that only see the logged-in customer's data."""

from pathlib import Path

from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from agents.core.prompts import load_prompt
from infra.llm.gateway import get_chat_model

from .context import SupportContext
from .tools import TOOLS

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v2.md"


def agent(state: MessagesState, runtime: Runtime[SupportContext]) -> dict:
    prompt = load_prompt(SYSTEM_PROMPT, company_name=runtime.context.tenant.name)
    llm = get_chat_model().bind_tools(TOOLS)
    response = llm.invoke([SystemMessage(prompt), *state["messages"]])
    return {"messages": [response]}


def build_graph(checkpointer=None):
    builder = StateGraph(MessagesState, context_schema=SupportContext)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer)
