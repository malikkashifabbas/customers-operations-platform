"""Turn graph.stream(stream_mode=STREAM_MODES, subgraphs=True) output into simple (event, data) pairs for SSE or Redis Streams."""

from collections.abc import Iterable, Iterator

from langchain_core.messages import AIMessage, AIMessageChunk, RemoveMessage, ToolMessage

STREAM_MODES = ["messages", "updates"]
# Nodes whose LLM text is the reply; other LLM nodes (guard, supervisor, grader, query writer) must never reach the customer.
ANSWER_NODES = {"agent", "generate_answer"}


def agent_events(stream: Iterable) -> Iterator[tuple[str, dict]]:
    multi_domain = False  # several specialists stream at once -> their tokens would interleave, so only compose streams
    for item in stream:
        # subgraphs=True yields (namespace, mode, data); without it, (mode, data) from the top graph only.
        namespace, mode, data = item if len(item) == 3 else ((), *item)
        if mode == "messages":
            chunk, metadata = data
            node = metadata.get("langgraph_node")
            if isinstance(chunk, AIMessageChunk) and chunk.content and ((node in ANSWER_NODES and not multi_domain) or node == "compose"):
                yield "token", {"text": chunk.content}
        elif mode == "updates":
            if namespace:
                continue  # a step inside a specialist; the parent's specialist update already carries its new messages
            for node, update in data.items():
                if node == "__interrupt__":
                    continue  # a tuple of Interrupt objects, not a dict; the caller reads it from graph.get_state()
                if node in ("guard_input", "triage") and (update or {}).get("blocked_reason"):
                    yield "guardrail", {"blocked_reason": update["blocked_reason"]}
                if node in ("supervisor", "triage") and (update or {}).get("routes"):
                    multi_domain = len(update["routes"]) > 1
                    yield "routing", {"domains": update["routes"]}
                for msg in (update or {}).get("messages", []):
                    if node == "refuse":
                        yield "token", {"text": msg.content}  # fixed text, no LLM, so it arrives in one piece
                    elif node == "guard_output" and isinstance(msg, RemoveMessage):
                        yield "reset", {}  # draft rejected: client clears the bubble, the rewrite's tokens follow
                    elif node == "guard_output":
                        yield "replace", {"text": msg.content}  # tokens already shown were unsafe: client swaps them
                    elif isinstance(msg, AIMessage) and msg.response_metadata.get("domain") and not msg.usage_metadata:
                        if not multi_domain:
                            yield "token", {"text": msg.content}  # a specialist's fixed text (no LLM, so no tokens were streamed)
                    elif isinstance(msg, AIMessage):
                        for call in msg.tool_calls:
                            yield "tool_call", {"name": call["name"], "args": call["args"]}
                    elif isinstance(msg, ToolMessage):
                        yield "tool_result", {"name": msg.name, "content": msg.content[:500]}
