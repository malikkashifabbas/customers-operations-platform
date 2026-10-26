"""Chat with the Lesson 7B agent in the terminal. Commands: 'new' starts a fresh conversation, 'exit' quits."""

import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lesson07b_tool_agent import FAKE_ACCOUNTS, FAKE_ORDERS, build_graph  # noqa: E402


def print_new_messages(messages: list) -> None:
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                print(f"  [tool call]   {call['name']}({call['args']})")
        elif isinstance(message, ToolMessage):
            print(f"  [tool result] {message.content}")
        elif isinstance(message, AIMessage):
            print(f"\nAgent: {message.content}")


def main() -> None:
    graph = build_graph()
    history: list = []
    print("OpsPilot support agent - type your question.  'new' = fresh chat, 'exit' = quit")
    print(f"Test data -> orders: {', '.join(FAKE_ORDERS)} | accounts: {', '.join(FAKE_ACCOUNTS)}")

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
            history = []
            print("(new conversation started)")
            continue

        try:
            result = graph.invoke({"messages": [*history, HumanMessage(text)]})
        except Exception as exc:  # rate limits or network errors should not kill the chat
            print(f"\n[error] {type(exc).__name__}: {exc}")
            continue

        # Everything after the history and the new question is what the agent produced this turn.
        print_new_messages(result["messages"][len(history) + 1 :])
        history = result["messages"]

    print("\nBye!")


if __name__ == "__main__":
    main()
