"""Lesson 8A: a checkpointer gives the agent memory per thread_id - send only the new message each turn."""

import sys
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lesson07b_tool_agent import build_graph  # noqa: E402


def ask(graph, thread_id: str, text: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"messages": [HumanMessage(text)]}, config)
    print(f"[{thread_id}] You:   {text}")
    print(f"[{thread_id}] Agent: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    graph = build_graph(checkpointer=InMemorySaver())

    ask(graph, "ali-1", "Hi, my email is ali@example.com")
    ask(graph, "ali-1", "Why can't I log in?")
    ask(graph, "sara-1", "Why can't I log in?")

    state = graph.get_state({"configurable": {"thread_id": "ali-1"}})
    print("ali-1 messages saved:", len(state.values["messages"]))
    print("ali-1 next node:", state.next)
    history = list(graph.get_state_history({"configurable": {"thread_id": "ali-1"}}))
    print("ali-1 checkpoints (photos):", len(history))
