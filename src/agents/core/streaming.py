"""Turn graph.stream(stream_mode=STREAM_MODES) output into simple (event, data) pairs for SSE or Pub/Sub."""

from collections.abc import Iterable, Iterator

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

STREAM_MODES = ["messages", "updates"]


def agent_events(stream: Iterable) -> Iterator[tuple[str, dict]]:
    for mode, data in stream:
        if mode == "messages":
            chunk, metadata = data
            if metadata.get("langgraph_node") == "agent" and isinstance(chunk, AIMessageChunk) and chunk.content:
                yield "token", {"text": chunk.content}
        elif mode == "updates":
            for node, update in data.items():
                if node == "guard_input" and (update or {}).get("blocked_reason"):
                    yield "guardrail", {"blocked_reason": update["blocked_reason"]}
                for msg in (update or {}).get("messages", []):
                    if node == "refuse":
                        yield "token", {"text": msg.content}  # fixed text, no LLM, so it arrives in one piece
                    elif node == "guard_output":
                        yield "replace", {"text": msg.content}  # tokens already shown were unsafe: client swaps them
                    elif isinstance(msg, AIMessage):
                        for call in msg.tool_calls:
                            yield "tool_call", {"name": call["name"], "args": call["args"]}
                    elif isinstance(msg, ToolMessage):
                        yield "tool_result", {"name": msg.name, "content": msg.content[:500]}
