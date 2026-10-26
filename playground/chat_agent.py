"""Chat with the Lesson 7B agent in the terminal.

    uv run python playground/chat_agent.py                 memory in RAM (gone when you exit)
    uv run python playground/chat_agent.py --thread ali-1  memory in Postgres (survives restarts)

Commands: 'new' = fresh conversation (new thread), 'state' = what is saved, 'exit' = quit.
"""

import argparse
import sys
import uuid
from contextlib import nullcontext
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lesson07b_tool_agent import FAKE_ACCOUNTS, FAKE_ORDERS, build_graph  # noqa: E402

from agents.core.checkpointers import postgres_checkpointer  # noqa: E402


def print_new_messages(messages: list) -> None:
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                print(f"  [tool call]   {call['name']}({call['args']})")
        elif isinstance(message, ToolMessage):
            print(f"  [tool result] {message.content}")
        elif isinstance(message, AIMessage):
            print(f"\nAgent: {message.content}")


def thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def saved_messages(graph, thread_id: str) -> list:
    return graph.get_state(thread_config(thread_id)).values.get("messages", [])


def print_state(graph, thread_id: str) -> None:
    messages = saved_messages(graph, thread_id)
    checkpoints = list(graph.get_state_history(thread_config(thread_id)))
    print(f"  thread: {thread_id} | saved messages: {len(messages)} | checkpoints (photos): {len(checkpoints)}")
    for message in messages:
        text = message.content or f"<tool call: {', '.join(c['name'] for c in message.tool_calls)}>"
        print(f"    {type(message).__name__:<12} {text[:90]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the OpsPilot support agent.")
    parser.add_argument("--thread", help="conversation id; when given, memory is stored in Postgres")
    args = parser.parse_args()

    store = postgres_checkpointer() if args.thread else nullcontext(InMemorySaver())
    with store as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        thread_id = args.thread or f"temp-{uuid.uuid4().hex[:8]}"
        where = "Postgres (survives restart)" if args.thread else "RAM (lost when you exit)"

        print("OpsPilot support agent - 'new' = fresh chat, 'state' = saved memory, 'exit' = quit")
        print(f"Test data -> orders: {', '.join(FAKE_ORDERS)} | accounts: {', '.join(FAKE_ACCOUNTS)}")
        print(f"Memory: {where} | thread: {thread_id}")
        previous = saved_messages(graph, thread_id)
        if previous:
            print(f"(continuing an old conversation: {len(previous)} saved messages)")

        while True:
            try:
                text = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"exit", "quit"}:
                break
            if text.lower() == "new":
                thread_id = f"{args.thread or 'temp'}-{uuid.uuid4().hex[:8]}"
                print(f"(new conversation, thread: {thread_id})")
                continue
            if text.lower() == "state":
                print_state(graph, thread_id)
                continue

            before = len(saved_messages(graph, thread_id))
            try:
                result = graph.invoke({"messages": [HumanMessage(text)]}, thread_config(thread_id))
            except Exception as exc:  # rate limits or network errors should not kill the chat
                print(f"\n[error] {type(exc).__name__}: {exc}")
                continue
            print_new_messages(result["messages"][before + 1 :])

    print("\nBye!")


if __name__ == "__main__":
    main()
