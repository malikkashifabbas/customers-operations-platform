"""Run the support agent for one customer message, either all at once or as a stream of SSE events.

Chat memory lives in Redis with a TTL (temporary); tickets keep theirs in Postgres.
"""

import logging
import time
import uuid
from collections.abc import Iterator
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command, Interrupt

from agents.core.checkpointers import get_redis_checkpointer
from agents.core.streaming import STREAM_MODES, agent_events
from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.accounts.auth import CustomerPrincipal
from core.limits import CHAT_MESSAGES_PER_MINUTE, CONVERSATION_LOCK_SECONDS
from core.sse import sse
from infra.cache import locks, ratelimit
from infra.observability.tracing import trace_config

from .exceptions import AssistantUnavailable, ConfirmationPending, ConversationBusy, NothingToConfirm, RateLimited

logger = logging.getLogger(__name__)
RESUME_ATTEMPTS = 3

# Fixed text, no LLM: the customer must see exactly what will happen, and it must say nothing has happened yet.
CONFIRM_REPLY = {
    "ticket_confirmation": {
        "english": "I am ready to open this support ticket: \"{subject}\". Please confirm or cancel. Nothing has been created yet.",
        "roman_urdu": "Main ye support ticket kholne ke liye tayyar hoon: \"{subject}\". Barah-e-karam confirm ya cancel karein. Abhi kuch nahi bana.",
        "urdu": "میں یہ سپورٹ ٹکٹ کھولنے کے لیے تیار ہوں: \"{subject}\"۔ براہ کرم تصدیق یا منسوخ کریں۔ ابھی کچھ نہیں بنا۔",
    },
    "name_change": {
        "english": "I am ready to change your name from \"{old_name}\" to \"{new_name}\". Please confirm or cancel. Nothing has changed yet.",
        "roman_urdu": "Main aap ka naam \"{old_name}\" se \"{new_name}\" karne ke liye tayyar hoon. Barah-e-karam confirm ya cancel karein. Abhi kuch nahi badla.",
        "urdu": "میں آپ کا نام \"{old_name}\" سے \"{new_name}\" کرنے کے لیے تیار ہوں۔ براہ کرم تصدیق یا منسوخ کریں۔ ابھی کچھ نہیں بدلا۔",
    },
    "email_change": {
        "english": "I am ready to send a confirmation link to {new_email}. Your email changes from {old_email} only when that link is opened. Please confirm or cancel. Nothing has changed yet.",
        "roman_urdu": "Main {new_email} par confirmation link bhejne ke liye tayyar hoon. Aap ka email {old_email} se tabhi badlega jab wo link khola jaye. Barah-e-karam confirm ya cancel karein. Abhi kuch nahi badla.",
        "urdu": "میں {new_email} پر تصدیقی لنک بھیجنے کے لیے تیار ہوں۔ آپ کا ای میل {old_email} سے تبھی بدلے گا جب وہ لنک کھولا جائے۔ براہ کرم تصدیق یا منسوخ کریں۔ ابھی کچھ نہیں بدلا۔",
    },
}


@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_redis_checkpointer())


def _thread_id(principal: CustomerPrincipal, conversation_id: str) -> str:
    # Tenant and customer are part of the id, so nobody can open another customer's conversation.
    return f"{principal.tenant.public_id}:{principal.customer.public_id}:{conversation_id}"


def _pending(graph, config: dict) -> Interrupt | None:
    interrupts = graph.get_state(config).interrupts
    return interrupts[0] if interrupts else None


def _confirm_reply(pending: Interrupt, language: str) -> str:
    return CONFIRM_REPLY[pending.value["type"]][language].format(**pending.value)


def _resume(graph, config: dict, context: SupportContext, answer: dict) -> dict:
    interrupts = graph.get_state(config).interrupts
    if len(interrupts) == 1:
        return graph.invoke(Command(resume=answer), config, context=context)
    # Several pauses need the interrupt id, so the customer answers one at a time; the next one comes back to them.
    target = interrupts[0].id
    # RedisSaver often loses an id-keyed resume on the first try (measured 29 of 30); a rerun is safe, write tools act once per call.
    for _ in range(RESUME_ATTEMPTS):
        result = graph.invoke(Command(resume={target: answer}), config, context=context)
        if target not in {interrupt.id for interrupt in graph.get_state(config).interrupts}:
            break
    return result


def _prepare(principal: CustomerPrincipal, conversation_id: str | None, tags: list[str] | None = None):
    if not ratelimit.allow(
        scope="chat", subject=str(principal.customer.public_id), limit=CHAT_MESSAGES_PER_MINUTE, window_seconds=60
    ):
        raise RateLimited()
    conversation_id = conversation_id or uuid.uuid4().hex
    thread_id = _thread_id(principal, conversation_id)
    config = trace_config(
        {"configurable": {"thread_id": thread_id}},
        session_id=conversation_id,
        user_id=str(principal.customer.public_id),
        tenant=principal.tenant.slug,
        channel="chat",
        tags=tags,
    )
    context = SupportContext(tenant=principal.tenant, customer=principal.customer)
    return conversation_id, thread_id, config, context


def run_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> dict:
    graph = get_graph()
    conversation_id, thread_id, config, context = _prepare(principal, conversation_id)
    with locks.redis_lock(f"thread:{thread_id}", CONVERSATION_LOCK_SECONDS) as acquired:
        if not acquired:
            raise ConversationBusy()
        if _pending(graph, config):
            raise ConfirmationPending()
        first_new = len(graph.get_state(config).values.get("messages", [])) + 1
        started = time.perf_counter()
        try:
            result = graph.invoke({"messages": [HumanMessage(message)]}, config, context=context)
        except Exception as exc:
            logger.exception("support agent failed")
            raise AssistantUnavailable() from exc
        return _response(graph, config, conversation_id, result, first_new, started)


def confirm_chat(*, principal: CustomerPrincipal, conversation_id: str, approved: bool) -> dict:
    """The customer's yes or no comes from this API and code, never from the LLM, so no message can fake an approval."""
    graph = get_graph()
    conversation_id, thread_id, config, context = _prepare(principal, conversation_id, tags=["resume"])
    with locks.redis_lock(f"thread:{thread_id}", CONVERSATION_LOCK_SECONDS) as acquired:
        if not acquired:
            raise ConversationBusy()
        pending = _pending(graph, config)
        if pending is None:
            raise NothingToConfirm()
        first_new = len(graph.get_state(config).values.get("messages", []))
        started = time.perf_counter()
        try:
            result = _resume(graph, config, context, {"approved": approved})
        except Exception as exc:
            logger.exception("support agent failed on resume")
            raise AssistantUnavailable() from exc
        return _response(graph, config, conversation_id, result, first_new, started)


def _response(graph, config: dict, conversation_id: str, result: dict, first_new: int, started: float) -> dict:
    new_ai = [m for m in result["messages"][first_new:] if isinstance(m, AIMessage)]
    # Guards, supervisor and merged/rejected drafts are not in the message list, so they report their own usage.
    hidden = [result.get("guard_usage") or {}, result.get("routing_usage") or {}]
    hidden_usage = {key: sum(usage.get(key, 0) for usage in hidden) for key in ("llm_calls", "tokens")}
    pending = _pending(graph, config)
    return {
        "conversation_id": conversation_id,
        "reply": _confirm_reply(pending, result.get("language", "english")) if pending else (new_ai[-1].content if new_ai else ""),
        "status": "confirmation_required" if pending else "answered",
        "pending_action": pending.value if pending else None,
        "tool_calls": [{"name": c["name"], "args": c["args"]} for m in new_ai for c in m.tool_calls],
        "llm_calls": len([m for m in new_ai if m.usage_metadata]) + hidden_usage["llm_calls"],
        "tokens": sum((m.usage_metadata or {}).get("total_tokens", 0) for m in new_ai) + hidden_usage["tokens"],
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "blocked_reason": result.get("blocked_reason"),
        "output_flags": result.get("output_flags", []),
        "output_retries": result.get("output_retries", 0),
        "routes": result.get("routes", []),
    }


def stream_chat(*, principal: CustomerPrincipal, message: str, conversation_id: str | None) -> Iterator[str]:
    # Checks run here, before the response starts, so a busy/limited request still gets a normal 409/429 JSON error.
    conversation_id, thread_id, config, context = _prepare(principal, conversation_id)
    lock_name = f"thread:{thread_id}"
    token = locks.acquire(lock_name, CONVERSATION_LOCK_SECONDS)
    if token is None:
        raise ConversationBusy()
    if _pending(get_graph(), config):
        locks.release(lock_name, token)
        raise ConfirmationPending()
    return _stream_events(message, conversation_id, config, context, lock_name, token)


def _stream_events(message, conversation_id, config, context, lock_name, token) -> Iterator[str]:
    started = time.perf_counter()
    try:
        yield sse("start", {"conversation_id": conversation_id})
        # subgraphs=True: specialists run inside nodes, and their tokens only reach this stream with it.
        stream = get_graph().stream(
            {"messages": [HumanMessage(message)]}, config, context=context, stream_mode=STREAM_MODES, subgraphs=True
        )
        for event, data in agent_events(stream):
            yield sse(event, data)
        state = get_graph().get_state(config)
        if state.interrupts:
            pending = state.interrupts[0]
            language = state.values.get("language", "english")
            yield sse("confirmation_required", {"pending_action": pending.value, "reply": _confirm_reply(pending, language)})
        yield sse("done", {"conversation_id": conversation_id, "latency_ms": int((time.perf_counter() - started) * 1000)})
    except Exception:
        logger.exception("support agent stream failed")
        yield sse("error", {"code": AssistantUnavailable.code, "message": AssistantUnavailable.message})
    finally:
        locks.release(lock_name, token)
