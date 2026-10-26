"""Lesson 7B: a ReAct agent - the LLM decides when to call tools, ToolNode runs them, then it answers."""

import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # playground runs outside Django
from infra.llm.gateway import get_chat_model  # noqa: E402

AGENT_PROMPT = (
    "You are OpsPilot's support agent. Use the tools to look up facts before answering. "
    "Never invent order or account details. Reply to the customer in two or three short sentences."
)

FAKE_ORDERS = {"ORD-1001": "paid on 20 Oct 2026, amount $49", "ORD-1002": "unpaid, payment failed (card declined)"}
FAKE_ACCOUNTS = {"ali@example.com": "locked after 5 failed logins", "sara@example.com": "active"}


@tool
def get_order_status(order_id: str) -> str:
    """Look up the payment status of an order by its id, for example ORD-1001."""
    return FAKE_ORDERS.get(order_id.upper(), "No order found with that id.")


@tool
def get_account_status(email: str) -> str:
    """Check whether a customer's account is active or locked, by the customer's email."""
    return FAKE_ACCOUNTS.get(email.lower(), "No account found with that email.")


TOOLS = [get_order_status, get_account_status]


def agent(state: MessagesState) -> dict:
    llm = get_chat_model().bind_tools(TOOLS)
    response = llm.invoke([SystemMessage(AGENT_PROMPT), *state["messages"]])
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    print(graph.get_graph().draw_mermaid())

    questions = [
        "I paid for order ORD-1002 but it still shows unpaid. Why?",
        "I can't log in. My email is ali@example.com, and can you also check order ORD-1001?",
        "What are your office hours?",
    ]
    for question in questions:
        print("\n" + "#" * 80)
        result = graph.invoke({"messages": [HumanMessage(question)]})
        for message in result["messages"]:
            message.pretty_print()
