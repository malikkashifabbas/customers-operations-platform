"""Lesson 15: RAG eval over the tricky policy documents — right numbers, no other company's numbers, a citation (PASS/FAIL)."""

import sys
import time
import uuid

import django_setup  # noqa: F401  (must run before any Django model import)
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.customers.models import Customer
from core.models import Tenant
from lesson12_eval import normalize

ALI = "+923001234567"


def run(graph, tenant, customer, question, contains=(), not_contains=(), language=None, needs_citation=True):
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    started = time.perf_counter()
    state = graph.invoke({"messages": [HumanMessage(question)]}, config, context=SupportContext(tenant=tenant, customer=customer))
    seconds = time.perf_counter() - started
    turn = state["messages"][1:]
    reply = next((m.content for m in reversed(turn) if isinstance(m, AIMessage) and m.content and not m.tool_calls), "")
    queries = [c["args"].get("query") for m in turn if isinstance(m, AIMessage) for c in m.tool_calls if c["name"] == "search_policies"]
    text = normalize(reply)
    problems = []
    if "knowledge" not in state.get("routes", []):
        problems.append(f"routes={state.get('routes')}, knowledge expected")
    problems += [f"missing {s!r}" for s in contains if normalize(s) not in text]
    problems += [f"forbidden {s!r} (other company / invented)" for s in not_contains if normalize(s) in text]
    if needs_citation and "[" not in reply:
        problems.append("no [source] citation")
    if language and state.get("language") != language:
        problems.append(f"language={state.get('language')}, expected {language}")
    print(f"\n{'PASS' if not problems else 'FAIL'}  {tenant.name}: {question}")
    print(f"      searches={queries} flags={state.get('output_flags') or 'none'} | {seconds:.1f}s")
    print(f"      reply: {reply}")
    for problem in problems:
        print(f"      !! {problem}")
    return not problems, seconds


if __name__ == "__main__":
    graph = build_graph(checkpointer=InMemorySaver())
    demo, nimbus = Tenant.objects.get(slug="demo-company"), Tenant.objects.get(slug="nimbustech")
    ali, ali_n = Customer.objects.get(tenant=demo, phone=ALI), Customer.objects.get(tenant=nimbus, phone=ALI)

    cases = [
        # Demo Company
        (demo, ali, "How many days do I have to return an item?", ["30"], ["14 days"]),
        (demo, ali, "My order was delivered on 25 August 2026. Can I still return it today?", ["45"], []),
        (demo, ali, "Can I get a refund for a dress marked Final Sale?", ["exchange", "7"], []),
        (demo, ali, "I paid cash on delivery and returned an item. How do I get my money back and how long does it take?", ["bank", "10"], []),
        (demo, ali, "My earrings arrived broken yesterday. Can I return them?", ["48"], []),
        (demo, ali, "Is there a limit for cash on delivery orders?", ["200"], []),
        (demo, ali, "What are your support hours during Ramadan?", ["10", "4"], []),
        (demo, ali, "How much does express delivery cost and by what time must I order?", ["9.99", "2"], ["14.99"]),
        (demo, ali, "What is your support email address?", ["support@demo-company.example"], ["help@nimbustech"]),
        (demo, ali, "Can you deliver my order to Dubai?", ["pakistan"], []),
        (demo, ali, "COD order ka refund kitne din mein milta hai?", ["10"], [], "roman_urdu"),
        (demo, ali, "Do you offer gift wrapping?", ["support team"], [], None, False),
        # NimbusTech
        (nimbus, ali_n, "How many days do I have to return an item?", ["14"], ["30 days"]),
        (nimbus, ali_n, "Do you offer cash on delivery?", [], ["200"]),
        (nimbus, ali_n, "I opened my laptop box and want to return it. Is there a fee?", ["15", "restocking"], []),  # model may write "15 %"
        (nimbus, ali_n, "Can I return a phone I already set up with my SIM?", ["7"], []),
        (nimbus, ali_n, "Is there a fee for a 6 month installment plan?", ["2.5"], []),
        (nimbus, ali_n, "Can I call your phone support on Saturday?", [], ["9:00"]),
        (nimbus, ali_n, "laptop ki warranty kitni hai?", ["1", "6"], [], "roman_urdu"),
    ]
    results = [run(graph, *case) for case in cases]
    passed = sum(ok for ok, _ in results)
    timings = [seconds for _, seconds in results]
    print(f"\n===== {passed}/{len(results)} passed | avg {sum(timings) / len(timings):.1f}s | max {max(timings):.1f}s =====")
    sys.exit(0 if passed == len(results) else 1)
