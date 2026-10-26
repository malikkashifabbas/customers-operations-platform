"""Chat with the real support agent (database tools) as one logged-in customer.

    uv run python playground/chat_support.py                                   Ali Khan @ Demo Company, memory in RAM
    uv run python playground/chat_support.py --customer sara@example.com       log in as another customer
    uv run python playground/chat_support.py --tenant nimbustech               same phone, other company
    uv run python playground/chat_support.py --thread orders-1                 memory in Postgres (survives restarts)

Commands: 'new' = fresh conversation, 'state' = saved memory, 'exit' = quit.
"""

import argparse
import time
import uuid
from contextlib import nullcontext

import django_setup  # noqa: F401  (must run before any Django model import)
from django.db.models import Q
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.core.checkpointers import postgres_checkpointer
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph
from apps.customers.models import Customer
from core.models import Tenant


def print_turn(messages: list, seconds: float) -> None:
    llm_calls = tokens = 0
    for message in messages:
        if isinstance(message, AIMessage):
            llm_calls += 1
            tokens += (message.usage_metadata or {}).get("total_tokens", 0)
            for call in message.tool_calls:
                print(f"  [tool call]   {call['name']}({call['args']})")
            if message.content:
                print(f"\nAgent: {message.content}")
        elif isinstance(message, ToolMessage):
            preview = message.content if len(message.content) <= 160 else message.content[:160] + "..."
            print(f"  [tool result] {preview}")
    print(f"  ({seconds:.1f}s | {llm_calls} LLM calls | {tokens} tokens)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the OpsPilot support agent as a logged-in customer.")
    parser.add_argument("--tenant", default="demo-company", help="tenant slug (demo-company or nimbustech)")
    parser.add_argument("--customer", default="+923001234567", help="customer phone or email")
    parser.add_argument("--thread", help="conversation name; when given, memory is stored in Postgres")
    args = parser.parse_args()

    tenant = Tenant.objects.get(slug=args.tenant)
    customer = Customer.objects.get(Q(phone=args.customer) | Q(email=args.customer), tenant=tenant)
    context = SupportContext(tenant=tenant, customer=customer)
    order_count = customer.orders.count()

    store = postgres_checkpointer() if args.thread else nullcontext(InMemorySaver())
    with store as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        name = args.thread or f"temp-{uuid.uuid4().hex[:8]}"
        thread_id = f"{tenant.public_id}:{customer.public_id}:{name}"  # tenant + customer inside the id

        print("OpsPilot support agent - 'new' = fresh chat, 'state' = saved memory, 'exit' = quit")
        print(f"Logged in as: {customer.full_name} ({customer.phone}) @ {tenant.name} | {order_count} orders in DB")
        print(f"Memory: {'Postgres' if args.thread else 'RAM'} | thread: ...:{name}")

        while True:
            try:
                text = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"exit", "quit"}:
                break
            config = {"configurable": {"thread_id": thread_id}}
            if text.lower() == "new":
                thread_id = f"{tenant.public_id}:{customer.public_id}:{name}-{uuid.uuid4().hex[:6]}"
                print("(new conversation)")
                continue
            if text.lower() == "state":
                saved = graph.get_state(config).values.get("messages", [])
                print(f"  saved messages: {len(saved)} | checkpoints: {len(list(graph.get_state_history(config)))}")
                continue

            before = len(graph.get_state(config).values.get("messages", []))
            started = time.perf_counter()
            try:
                result = graph.invoke({"messages": [HumanMessage(text)]}, config, context=context)
            except Exception as exc:  # rate limits or network errors should not kill the chat
                print(f"\n[error] {type(exc).__name__}: {exc}")
                continue
            print_turn(result["messages"][before + 1 :], time.perf_counter() - started)

    print("\nBye!")


if __name__ == "__main__":
    main()
