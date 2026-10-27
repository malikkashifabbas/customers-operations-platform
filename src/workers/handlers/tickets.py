"""What the agent worker does with one tickets.created event: run the support agent, stream progress, save its reply."""

import logging
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage

from agents.core.checkpointers import get_pool_checkpointer
from agents.core.streaming import STREAM_MODES, agent_events
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph
from apps.tickets import selectors, services
from apps.tickets.models import Ticket, TicketStatus
from core.limits import TICKET_LOCK_SECONDS
from infra.cache import keys, streams
from infra.cache.locks import redis_lock
from infra.eventbus.events import TicketCreatedV1

logger = logging.getLogger(__name__)


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
        _publish(ticket, "processing", {})

        config = {"configurable": {"thread_id": f"{ticket.tenant.public_id}:{ticket.customer.public_id}:ticket-{ticket.public_id}"}}
        context = SupportContext(tenant=ticket.tenant, customer=ticket.customer)
        question = f"Support ticket subject: {ticket.subject}\n\n{ticket.body}"
        graph = get_graph()
        stream = graph.stream({"messages": [HumanMessage(question)]}, config, context=context, stream_mode=STREAM_MODES)
        for name, data in agent_events(stream):
            _publish(ticket, name, data)

        messages = graph.get_state(config).values["messages"]
        reply = next((m.content for m in reversed(messages) if isinstance(m, AIMessage) and m.content), "")
        services.mark_ticket_answered(ticket=ticket, reply=reply)
        _publish(ticket, "answered", {"reply": reply})  # after the DB commit, so a GET right after sees the same answer
    return f"answered ({len(reply)} chars)"


def mark_failed(event: TicketCreatedV1) -> None:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is not None and ticket.status == TicketStatus.OPEN:
        services.mark_ticket_failed(ticket=ticket)
        _publish(ticket, "failed", {"reply": ""})
