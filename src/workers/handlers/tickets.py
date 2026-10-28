"""What the agent worker does with ticket events: run the support agent, stream progress, save its reply.

tickets.created starts the agent; if it pauses for a refund approval (interrupt), tickets.approval_decided resumes it.
"""

import logging
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from agents.core.checkpointers import get_pool_checkpointer
from agents.core.streaming import STREAM_MODES, agent_events
from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.tickets import selectors, services
from apps.tickets.models import Ticket, TicketStatus
from core.limits import TICKET_LOCK_SECONDS
from infra.cache import keys, streams
from infra.cache.locks import redis_lock
from infra.eventbus.events import TicketApprovalDecidedV1, TicketCreatedV1

logger = logging.getLogger(__name__)

# Fixed text (no LLM) shown while staff decide; the agent writes the real answer after the decision.
WAITING_REPLY = {
    "english": "Your refund request for {order_number} ({amount}) has been sent to our staff for approval. We will update this ticket once they decide.",
    "roman_urdu": "Aap ki {order_number} ({amount}) ki refund request staff ki approval ke liye bhej di gayi hai. Faisla hote hi is ticket par jawab aa jayega.",
    "urdu": "آپ کی {order_number} ({amount}) کی ریفنڈ درخواست اسٹاف کی منظوری کے لیے بھیج دی گئی ہے۔ فیصلہ ہوتے ہی اس ٹکٹ پر جواب آ جائے گا۔",
}


class PermanentEventError(Exception):
    """Retrying will never help (e.g. the ticket does not exist): send the event straight to the DLQ."""


@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_pool_checkpointer())


def _publish(ticket: Ticket, event: str, data: dict) -> None:
    streams.append(keys.ticket_events(str(ticket.public_id)), event, data)


def handle_ticket_created(event: TicketCreatedV1) -> str:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is None:
        raise PermanentEventError(f"ticket {event.ticket_public_id} not found for tenant {event.tenant_public_id}")
    if ticket.status != TicketStatus.OPEN:
        return f"skipped: ticket already {ticket.status}"  # second idempotency guard, independent of Redis

    with redis_lock(f"ticket:{ticket.public_id}", TICKET_LOCK_SECONDS) as acquired:
        if not acquired:
            return "skipped: another worker is answering this ticket"
        question = f"Support ticket subject: {ticket.subject}\n\n{ticket.body}"
        return _run(ticket, {"messages": [HumanMessage(question)]})


def handle_approval_decided(event: TicketApprovalDecidedV1) -> str:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is None:
        raise PermanentEventError(f"ticket {event.ticket_public_id} not found for tenant {event.tenant_public_id}")
    if ticket.status != TicketStatus.WAITING_APPROVAL or ticket.approval_decision is None:
        return f"skipped: ticket is {ticket.status}, nothing to resume"

    with redis_lock(f"ticket:{ticket.public_id}", TICKET_LOCK_SECONDS) as acquired:
        if not acquired:
            return "skipped: another worker is working on this ticket"
        _publish(ticket, "approval_decided", {"approved": ticket.approval_decision["approved"]})
        # Command(resume=...) continues the paused run: interrupt() inside request_refund returns this decision.
        return _run(ticket, Command(resume=ticket.approval_decision))


def _run(ticket: Ticket, graph_input) -> str:
    """Run (or resume) the agent for this ticket, stream its events, then save either the answer or the approval request."""
    _publish(ticket, "processing", {})
    config = {"configurable": {"thread_id": f"{ticket.tenant.public_id}:{ticket.customer.public_id}:ticket-{ticket.public_id}"}}
    context = SupportContext(tenant=ticket.tenant, customer=ticket.customer, channel="ticket")
    graph = get_graph()
    # subgraphs=True: specialists run inside nodes, and their tokens only reach this stream with it.
    stream = graph.stream(graph_input, config, context=context, stream_mode=STREAM_MODES, subgraphs=True)
    for name, data in agent_events(stream):
        _publish(ticket, name, data)

    state = graph.get_state(config)
    if state.interrupts:
        request = state.interrupts[0].value
        reply = WAITING_REPLY[state.values.get("language", "english")].format(**request)
        services.mark_ticket_waiting_approval(ticket=ticket, request=request, reply=reply)
        _publish(ticket, "approval_required", {**request, "reply": reply})
        return f"waiting for staff approval ({request['order_number']})"

    reply = next((m.content for m in reversed(state.values["messages"]) if isinstance(m, AIMessage) and m.content), "")
    services.mark_ticket_answered(ticket=ticket, reply=reply)
    _publish(ticket, "answered", {"reply": reply})  # after the DB commit, so a GET right after sees the same answer
    return f"answered ({len(reply)} chars)"


def mark_failed(event: TicketCreatedV1 | TicketApprovalDecidedV1) -> None:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is not None and ticket.status in (TicketStatus.OPEN, TicketStatus.WAITING_APPROVAL):
        services.mark_ticket_failed(ticket=ticket)
        _publish(ticket, "failed", {"reply": ""})
