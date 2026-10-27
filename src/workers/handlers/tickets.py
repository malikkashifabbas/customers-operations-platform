"""What the agent worker does with one tickets.created event: run the support agent and save its reply."""

import logging
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage

from agents.core.checkpointers import get_pool_checkpointer
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import build_graph
from apps.tickets import selectors, services
from apps.tickets.models import TicketStatus
from infra.eventbus.events import TicketCreatedV1

logger = logging.getLogger(__name__)


class PermanentEventError(Exception):
    """Retrying will never help (e.g. the ticket does not exist): send the event straight to the DLQ."""


@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_pool_checkpointer())


def handle_ticket_created(event: TicketCreatedV1) -> str:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is None:
        raise PermanentEventError(f"ticket {event.ticket_public_id} not found for tenant {event.tenant_public_id}")
    if ticket.status != TicketStatus.OPEN:
        return f"skipped: ticket already {ticket.status}"  # second idempotency guard, independent of Redis

    config = {"configurable": {"thread_id": f"{ticket.tenant.public_id}:{ticket.customer.public_id}:ticket-{ticket.public_id}"}}
    context = SupportContext(tenant=ticket.tenant, customer=ticket.customer)
    question = f"Support ticket subject: {ticket.subject}\n\n{ticket.body}"
    result = get_graph().invoke({"messages": [HumanMessage(question)]}, config, context=context)

    reply = next((m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content), "")
    services.mark_ticket_answered(ticket=ticket, reply=reply)
    return f"answered ({len(reply)} chars)"


def mark_failed(event: TicketCreatedV1) -> None:
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
    if ticket is not None and ticket.status == TicketStatus.OPEN:
        services.mark_ticket_failed(ticket=ticket)
