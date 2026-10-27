"""Run the support agent for one customer message, either all at once or as a stream of SSE events.

Chat memory lives in Redis with a TTL (temporary); tickets keep theirs in Postgres.
"""

import logging
import time
import uuid
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage

from agents.core.checkpointers import get_redis_checkpointer
from agents.core.streaming import STREAM_MODES, agent_events
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph
from core.limits import CHAT_MESSAGES_PER_MINUTE, CONVERSATION_LOCK_SECONDS
from core.sse import sse
from infra.cache import locks, ratelimit

from .auth import CustomerPrincipal
from .exceptions import AssistantUnavailable, ConversationBusy, RateLimited

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_redis_checkpointer())


def _thread_id(principal: CustomerPrincipal, conversation_id: str) -> str:
    # Tenant and customer are part of the id, so nobody can open another customer's conversation.
    return f"{principal.tenant.public_id}:{principal.customer.public_id}:{conversation_id}"


def _prepare(principal: CustomerPrincipal, conversation_id: str | None):
    if not ratelimit.allow(
        scope="chat", subject=str(principal.customer.public_id), limit=CHAT_MESSAGES_PER_MINUTE, window_seconds=60
    ):
        raise RateLimited()
    conversation_id = conversation_id or uuid.uuid4().hex
    thread_id = _thread_id(principal, conversation_id)
    config = {"configurable": {"thread_id": thread_id}}
    context = SupportContext(tenant=principal.tenant, customer=principal.customer)
    return conversation_id, thread_id, config, context


def run_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> dict:
    graph = get_graph()
    conversation_id, thread_id, config, context = _prepare(principal, conversation_id)
    with locks.redis_lock(f"thread:{thread_id}", CONVERSATION_LOCK_SECONDS) as acquired:
        if not acquired:
            raise ConversationBusy()
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


def stream_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> Iterator[str]:
    # Checks run here, before the response starts, so a busy/limited request still gets a normal 409/429 JSON error.
    conversation_id, thread_id, config, context = _prepare(principal, conversation_id)
    lock_name = f"thread:{thread_id}"
    token = locks.acquire(lock_name, CONVERSATION_LOCK_SECONDS)
    if token is None:
        raise ConversationBusy()
    return _stream_events(message, conversation_id, config, context, lock_name, token)


def _stream_events(message, conversation_id, config, context, lock_name, token) -> Iterator[str]:
    started = time.perf_counter()
    try:
        yield sse("start", {"conversation_id": conversation_id})
        stream = get_graph().stream({"messages": [HumanMessage(message)]}, config, context=context, stream_mode=STREAM_MODES)
        for event, data in agent_events(stream):
            yield sse(event, data)
        yield sse("done", {"conversation_id": conversation_id, "latency_ms": int((time.perf_counter() - started) * 1000)})
    except Exception:
        logger.exception("support agent stream failed")
        yield sse("error", {"code": AssistantUnavailable.code, "message": AssistantUnavailable.message})
    finally:
        locks.release(lock_name, token)
