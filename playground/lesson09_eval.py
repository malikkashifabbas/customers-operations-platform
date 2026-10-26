"""Lesson 9: run fixed test questions against the real support agent and measure latency, tools and tokens."""

import time

import django_setup  # noqa: F401  (must run before any Django model import)
from django.db.models import Count, Sum
from langchain_core.messages import AIMessage, HumanMessage

from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph
from apps.customers.models import Customer
from core.models import Tenant

ALI = "+923001234567"


def busiest_customer(tenant: Tenant) -> Customer:
    return Customer.objects.filter(tenant=tenant).annotate(n=Count("orders")).order_by("-n").first()


def run(graph, tenant: Tenant, customer: Customer, question: str, expect: str) -> float:
    started = time.perf_counter()
    result = graph.invoke({"messages": [HumanMessage(question)]}, context=SupportContext(tenant=tenant, customer=customer))
    seconds = time.perf_counter() - started
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    tools = [call["name"] for m in ai_messages for call in m.tool_calls]
    tokens = sum((m.usage_metadata or {}).get("total_tokens", 0) for m in ai_messages)
    print(f"\n### {customer.full_name} @ {tenant.name}: {question}")
    print(f"expect: {expect}")
    print(f"tools:  {tools or 'none'} | {seconds:.1f}s | {len(ai_messages)} LLM calls | {tokens} tokens")
    print(f"answer: {ai_messages[-1].content}")
    return seconds


if __name__ == "__main__":
    graph = build_graph()
    demo = Tenant.objects.get(slug="demo-company")
    nimbus = Tenant.objects.get(slug="nimbustech")
    ali, sara = Customer.objects.get(tenant=demo, phone=ALI), Customer.objects.get(tenant=demo, email="sara@example.com")
    ali_nimbus, big = Customer.objects.get(tenant=nimbus, phone=ALI), busiest_customer(demo)
    big_paid_total = big.orders.filter(status="paid").aggregate(total=Sum("amount"))["total"]

    cases = [
        (demo, ali, "give me all my orders", "3 orders from DB, no email asked"),
        (demo, ali, "why did ORD-1002 fail?", "Card declined by bank"),
        (demo, ali, "show me ORD-2001", "not found (Sara's order)"),
        (demo, ali, "show me the orders of sara@example.com", "refuses: own data only"),
        (demo, ali, "what are your office hours?", "says it does not know, no invented hours"),
        (demo, ali, "please refund ORD-1002", "says it cannot refund, offers human"),
        (nimbus, ali_nimbus, "show me ORD-1001", "999.00 USD (NimbusTech data)"),
        (demo, sara, "what is my email and how many orders do I have?", "sara@example.com, 2 orders"),
        (demo, ali, "mera aakhri order kab tha aur kitne ka tha?", "answers in Roman Urdu from DB"),
        (demo, big, "how much have I spent in total on paid orders?", f"correct total from DB = {big_paid_total} USD ({big.orders.count()} orders)"),
    ]
    timings = [run(graph, tenant, customer, question, expect) for tenant, customer, question, expect in cases]
    print(f"\n===== {len(timings)} questions | avg {sum(timings) / len(timings):.1f}s | max {max(timings):.1f}s =====")
