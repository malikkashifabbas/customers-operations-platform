"""A generic ReAct subgraph (agent <-> tools): each domain only supplies its tools and its prompt."""

from collections.abc import Callable

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from infra.llm.gateway import get_chat_model


class DomainState(MessagesState):
    language: str


def build_react_subgraph(
    *,
    all_tools: list,
    tools_for: Callable[[object], list],
    prompt_for: Callable[[DomainState, object, list], str],
    context_schema: type,
):
    """tools_for(context) picks what the LLM may call now; ToolNode gets all_tools so it can run any of them."""

    def agent(state: DomainState, runtime: Runtime) -> dict:
        tools = tools_for(runtime.context)
        llm = get_chat_model().bind_tools(tools) if tools else get_chat_model()
        response = llm.invoke([SystemMessage(prompt_for(state, runtime.context, tools)), *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(DomainState, context_schema=context_schema)
    builder.add_node("agent", agent)
    builder.add_edge(START, "agent")
    if all_tools:
        builder.add_node("tools", ToolNode(all_tools))
        builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        builder.add_edge("tools", "agent")
    else:
        builder.add_edge("agent", END)
    # No checkpointer here: a subgraph uses its parent's, under its own namespace (e.g. "billing:<task id>").
    return builder.compile()
