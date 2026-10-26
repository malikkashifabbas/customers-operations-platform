"""Run the support agent for one customer message, either all at once or as a stream of SSE events."""

import json
import logging
import time
import uuid
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from agents.core.checkpointers import get_pool_checkpointer
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph

from .auth import CustomerPrincipal
from .exceptions import AssistantUnavailable

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_pool_checkpointer())


def _thread_id(principal: CustomerPrincipal, conversation_id: str) -> str:
    # Tenant and customer are part of the id, so nobody can open another customer's conversation.
    return f"{principal.tenant.public_id}:{principal.customer.public_id}:{conversation_id}"


def _prepare(principal: CustomerPrincipal, conversation_id: str | None):
    conversation_id = conversation_id or uuid.uuid4().hex
    config = {"configurable": {"thread_id": _thread_id(principal, conversation_id)}}
    context = SupportContext(tenant=principal.tenant, customer=principal.customer)
    return conversation_id, config, context


def run_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> dict:
    graph = get_graph()
    conversation_id, config, context = _prepare(principal, conversation_id)
    before = len(graph.get_state(config).values.get("messages", []))
    started = time.perf_counter()
    try:
        result = graph.invoke({"messages": [HumanMessage(message)]}, config, context=context)
    except Exception as exc:
        logger.exception("support agent failed")
        raise AssistantUnavailable() from exc

    new_ai = [m for m in result["messages"][before + 1 :] if isinstance(m, AIMessage)]
    return {
        "conversation_id": conversation_id,
        "reply": new_ai[-1].content if new_ai else "",
        "tool_calls": [{"name": c["name"], "args": c["args"]} for m in new_ai for c in m.tool_calls],
        "llm_calls": len(new_ai),
        "tokens": sum((m.usage_metadata or {}).get("total_tokens", 0) for m in new_ai),
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> Iterator[str]:
    graph = get_graph()
    conversation_id, config, context = _prepare(principal, conversation_id)
    started = time.perf_counter()
    yield _sse("start", {"conversation_id": conversation_id})
    try:
        for mode, data in graph.stream(
            {"messages": [HumanMessage(message)]}, config, context=context, stream_mode=["messages", "updates"]
        ):
            if mode == "messages":
                chunk, metadata = data
                if metadata.get("langgraph_node") == "agent" and isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield _sse("token", {"text": chunk.content})
            elif mode == "updates":
                for update in data.values():
                    for msg in (update or {}).get("messages", []):
                        if isinstance(msg, AIMessage):
                            for call in msg.tool_calls:
                                yield _sse("tool_call", {"name": call["name"], "args": call["args"]})
                        elif isinstance(msg, ToolMessage):
                            yield _sse("tool_result", {"name": msg.name, "content": msg.content[:500]})
    except Exception:
        logger.exception("support agent stream failed")
        yield _sse("error", {"code": AssistantUnavailable.code, "message": AssistantUnavailable.message})
        return
    yield _sse("done", {"conversation_id": conversation_id, "latency_ms": int((time.perf_counter() - started) * 1000)})
