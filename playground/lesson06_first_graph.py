"""Lesson 6: first LangGraph graph - state, nodes, edges, a conditional edge and a reducer (no LLM yet)."""

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class TicketState(TypedDict):
    ticket_text: str
    category: str
    priority: str
    reply: str
    steps: Annotated[list[str], operator.add]


def classify(state: TicketState) -> dict:
    text = state["ticket_text"].lower()
    if any(word in text for word in ("refund", "invoice", "payment", "charged")):
        category = "billing"
    elif any(word in text for word in ("error", "crash", "bug", "login")):
        category = "tech"
    else:
        category = "general"
    return {"category": category, "steps": [f"classify -> {category}"]}


def set_priority(state: TicketState) -> dict:
    urgent = any(word in state["ticket_text"].lower() for word in ("urgent", "asap", "immediately"))
    priority = "high" if urgent else "normal"
    return {"priority": priority, "steps": [f"set_priority -> {priority}"]}


def route_by_category(state: TicketState) -> Literal["billing", "tech", "general"]:
    return state["category"]


def billing_reply(state: TicketState) -> dict:
    reply = "Our billing team will check your invoice and refund any extra charge."
    return {"reply": reply, "steps": ["billing_reply"]}


def tech_reply(state: TicketState) -> dict:
    reply = "Our technical team is looking into the error you reported."
    return {"reply": reply, "steps": ["tech_reply"]}


def general_reply(state: TicketState) -> dict:
    reply = "Thanks for reaching out, a support agent will get back to you soon."
    return {"reply": reply, "steps": ["general_reply"]}


def build_graph():
    builder = StateGraph(TicketState)

    builder.add_node("classify", classify)
    builder.add_node("set_priority", set_priority)
    builder.add_node("billing_reply", billing_reply)
    builder.add_node("tech_reply", tech_reply)
    builder.add_node("general_reply", general_reply)

    builder.add_edge(START, "classify")
    builder.add_edge("classify", "set_priority")
    builder.add_conditional_edges(
        "set_priority",
        route_by_category,
        {"billing": "billing_reply", "tech": "tech_reply", "general": "general_reply"},
    )
    builder.add_edge("billing_reply", END)
    builder.add_edge("tech_reply", END)
    builder.add_edge("general_reply", END)

    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()

    print("===== Mermaid diagram =====")
    print(graph.get_graph().draw_mermaid())

    print("===== invoke: final state =====")
    result = graph.invoke({"ticket_text": "I was charged twice, please refund ASAP"})
    for key, value in result.items():
        print(f"{key}: {value}")

    print("===== stream: update after every node =====")
    for update in graph.stream({"ticket_text": "The app shows an error on login"}, stream_mode="updates"):
        print(update)
