"""Lesson 13: refund approvals with interrupt() — pause, show the request, resume with a staff decision (PASS/FAIL)."""

import json
import sys
import uuid

import django_setup  # noqa: F401  (must run before any Django model import)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from core.models import Tenant

ALI = "+923001234567"


def ticket_question(body: str) -> dict:
    return {"messages": [HumanMessage(f"Support ticket subject: Refund\n\n{body}")]}


def last_reply(state: dict) -> str:
    return next((m.content for m in reversed(state["messages"]) if isinstance(m, AIMessage) and m.content), "")


def tool_names(state: dict) -> list[str]:
    return [c["name"] for m in state["messages"] if isinstance(m, AIMessage) for c in m.tool_calls]


def refund_results(state: dict) -> list[dict]:
    return [json.loads(m.content) for m in state["messages"] if isinstance(m, ToolMessage) and m.name == "request_refund" and m.content.startswith("{")]


def report(name: str, problems: list[str], reply: str) -> bool:
    print(f"\n{'PASS' if not problems else 'FAIL'}  {name}")
    print(f"      reply: {reply}")
    for problem in problems:
        print(f"      !! {problem}")
    return not problems


def main() -> int:
    graph = build_graph(checkpointer=InMemorySaver())
    demo = Tenant.objects.get(slug="demo-company")
    ali = Customer.objects.get(tenant=demo, phone=ALI)
    ticket_ctx = SupportContext(tenant=demo, customer=ali, channel="ticket")
    order = Order.objects.get(tenant=demo, customer=ali, order_number="ORD-1001")
    Order.objects.filter(pk=order.pk).update(status=OrderStatus.PAID)  # start every run from a paid order
    results = []

    # A: failed order -> the tool refuses before interrupt(), so no human is bothered.
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    state = graph.invoke(ticket_question("Please refund ORD-1002."), config, context=ticket_ctx)
    problems = ["paused, but a failed order must not reach staff"] if graph.get_state(config).interrupts else []
    results.append(report("A ticket: refund a FAILED order (no pause)", problems, last_reply(state)))

    # B: paid order -> pause; staff reject -> order stays paid.
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    graph.invoke(ticket_question("Please refund ORD-1001, I was charged twice."), config, context=ticket_ctx)
    interrupts = graph.get_state(config).interrupts
    print(f"\n      paused with: {interrupts[0].value if interrupts else None}")
    problems = [] if interrupts and interrupts[0].value.get("order_number") == "ORD-1001" else ["did not pause for ORD-1001"]
    decision = {"approved": False, "note": "We found only one charge on your card.", "reviewer": "eval"}
    state = graph.invoke(Command(resume=decision), config, context=ticket_ctx)
    order.refresh_from_db()
    if order.status != OrderStatus.PAID:
        problems.append(f"order is {order.status} after a rejection")
    if not any(r.get("refund_status") == "rejected" for r in refund_results(state)):
        problems.append("tool result does not say rejected")
    results.append(report("B ticket: refund PAID order -> staff REJECT", problems, last_reply(state)))

    # C: paid order -> pause; staff approve -> order refunded (then put back for the next run).
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    graph.invoke(ticket_question("Please refund ORD-1001, I was charged twice."), config, context=ticket_ctx)
    problems = [] if graph.get_state(config).interrupts else ["did not pause"]
    state = graph.invoke(Command(resume={"approved": True, "note": "", "reviewer": "eval"}), config, context=ticket_ctx)
    order.refresh_from_db()
    if order.status != OrderStatus.REFUNDED:
        problems.append(f"order is {order.status} after approval")
    if state.get("output_flags") and not state.get("output_retries"):
        problems.append(f"output guard flagged the true refund reply: {state['output_flags']}")
    results.append(report("C ticket: refund PAID order -> staff APPROVE", problems, last_reply(state)))
    Order.objects.filter(pk=order.pk).update(status=OrderStatus.PAID)

    # D: chat cannot wait for staff, so it has no refund tool at all.
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    state = graph.invoke({"messages": [HumanMessage("please refund ORD-1001")]}, config, context=SupportContext(tenant=demo, customer=ali))
    problems = ["chat called request_refund"] if "request_refund" in tool_names(state) else []
    if graph.get_state(config).interrupts:
        problems.append("chat paused")
    if "ticket" not in last_reply(state).lower():
        problems.append("reply does not point to a support ticket")
    results.append(report("D chat: refund request -> tells customer to open a ticket", problems, last_reply(state)))

    passed = sum(results)
    print(f"\n===== {passed}/{len(results)} passed =====")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
