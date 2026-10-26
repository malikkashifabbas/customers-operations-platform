"""Lesson 7A: the classify node uses an LLM with structured output instead of keywords."""

import sys
from pathlib import Path
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # playground runs outside Django
from infra.llm.gateway import get_chat_model  # noqa: E402

CLASSIFY_PROMPT = (
    "You triage customer support tickets for a SaaS company. "
    "Pick the category and priority that best fit the ticket."
)


class Classification(BaseModel):
    category: Literal["billing", "tech", "general"] = Field(
        description="billing = payments, invoices, refunds; tech = errors, login, account access; general = anything else"
    )
    priority: Literal["high", "normal"] = Field(description="high only if the customer is blocked or says it is urgent")
    reason: str = Field(description="One short sentence explaining the choice")


class TicketState(TypedDict):
    ticket_text: str
    category: str
    priority: str
    reason: str
    reply: str


def classify(state: TicketState) -> dict:
    llm = get_chat_model().with_structured_output(Classification)
    result = llm.invoke([SystemMessage(CLASSIFY_PROMPT), HumanMessage(state["ticket_text"])])
    return {"category": result.category, "priority": result.priority, "reason": result.reason}


def route_by_category(state: TicketState) -> Literal["billing", "tech", "general"]:
    return state["category"]


def billing_reply(state: TicketState) -> dict:
    return {"reply": "Our billing team will check your invoice and refund any extra charge."}


def tech_reply(state: TicketState) -> dict:
    return {"reply": "Our technical team is looking into the problem you reported."}


def general_reply(state: TicketState) -> dict:
    return {"reply": "Thanks for reaching out, a support agent will get back to you soon."}


def build_graph():
    builder = StateGraph(TicketState)
    builder.add_node("classify", classify)
    builder.add_node("billing_reply", billing_reply)
    builder.add_node("tech_reply", tech_reply)
    builder.add_node("general_reply", general_reply)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_by_category,
        {"billing": "billing_reply", "tech": "tech_reply", "general": "general_reply"},
    )
    builder.add_edge("billing_reply", END)
    builder.add_edge("tech_reply", END)
    builder.add_edge("general_reply", END)
    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    tickets = [
        "My account is locked, urgent!",
        "I was charged twice for my subscription this month",
        "Do you have a dark mode in the dashboard?",
    ]
    for ticket in tickets:
        result = graph.invoke({"ticket_text": ticket})
        print(f"\nTICKET:   {ticket}")
        print(f"category: {result['category']} | priority: {result['priority']}")
        print(f"reason:   {result['reason']}")
        print(f"reply:    {result['reply']}")
