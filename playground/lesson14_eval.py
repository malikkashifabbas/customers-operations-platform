"""Lesson 14: does the supervisor route to the right specialists, and do parallel answers come back as ONE reply? (PASS/FAIL)"""

import sys
import time
import uuid

import django_setup  # noqa: F401  (must run before any Django model import)
from django.db.models import Count, Sum
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.customers.models import Customer
from core.models import Tenant
from lesson12_eval import normalize

ALI = "+923001234567"


def run(graph, tenant, customer, question, routes, contains=(), language=None, thread=None) -> tuple[bool, float]:
    config = {"configurable": {"thread_id": thread or uuid.uuid4().hex}}
    before = len(graph.get_state(config).values.get("messages", []))
    started = time.perf_counter()
    state = graph.invoke({"messages": [HumanMessage(question)]}, config, context=SupportContext(tenant=tenant, customer=customer))
    seconds = time.perf_counter() - started
    turn = state["messages"][before + 1 :]
    finals = [m for m in turn if isinstance(m, AIMessage) and not m.tool_calls]
    reply = finals[-1].content if finals else ""
    tools = [c["name"] for m in turn if isinstance(m, AIMessage) for c in m.tool_calls]
    problems = []
    if set(state.get("routes", [])) != set(routes):
        problems.append(f"routes={state.get('routes')}, expected {sorted(routes)}")
    if len(finals) != 1:
        problems.append(f"{len(finals)} visible replies this turn, expected 1 (compose must remove the specialist drafts)")
    if language and state.get("language") != language:
        problems.append(f"language={state.get('language')}, expected {language}")
    problems += [f"missing text {s!r}" for s in contains if s.lower() not in normalize(reply)]
    print(f"\n{'PASS' if not problems else 'FAIL'}  {customer.full_name}: {question}")
    print(f"      routes={state.get('routes')} tools={tools or 'none'} language={state.get('language')} | {seconds:.1f}s")
    print(f"      reply: {reply}")
    for problem in problems:
        print(f"      !! {problem}")
    return not problems, seconds


if __name__ == "__main__":
    graph = build_graph(checkpointer=InMemorySaver())
    demo = Tenant.objects.get(slug="demo-company")
    ali, sara = Customer.objects.get(tenant=demo, phone=ALI), Customer.objects.get(tenant=demo, email="sara@example.com")
    big = Customer.objects.filter(tenant=demo).annotate(n=Count("orders")).order_by("-n").first()
    big_paid = str(big.orders.filter(status="paid").aggregate(total=Sum("amount"))["total"])
    follow_up = uuid.uuid4().hex

    results = [
        run(graph, demo, ali, "give me all my orders", {"billing"}, contains=["ORD-1001", "ORD-1003"]),
        run(graph, demo, ali, "what email do you have for me?", {"account"}, contains=["ali@example.com"]),
        run(graph, demo, ali, "what is your return policy?", {"knowledge"}, contains=["30"]),
        run(graph, demo, big, "what is my phone number and how much have I spent on paid orders?", {"account", "billing"},
            contains=[big.phone, big_paid]),
        run(graph, demo, sara, "mera email kya hai aur mere kitne orders hain?", {"account", "billing"},
            contains=["sara@example.com", "2"], language="roman_urdu"),
        run(graph, demo, ali, "tell me about ORD-1002", {"billing"}, contains=["declined"], thread=follow_up),
        run(graph, demo, ali, "and what is my email?", {"account"}, contains=["ali@example.com"], thread=follow_up),
    ]
    passed = sum(ok for ok, _ in results)
    timings = [seconds for _, seconds in results]
    print(f"\n===== {passed}/{len(results)} passed | avg {sum(timings) / len(timings):.1f}s | max {max(timings):.1f}s =====")
    sys.exit(0 if passed == len(results) else 1)
