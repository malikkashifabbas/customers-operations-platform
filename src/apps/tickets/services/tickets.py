"""Write-side rules for tickets. Every state change and its event are saved in ONE transaction (outbox pattern)."""

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from core.models import Tenant
from infra.eventbus.events import TicketAnsweredV1, TicketCreatedV1
from infra.eventbus.outbox import publish_event
from infra.eventbus.topics import TICKETS_ANSWERED, TICKETS_CREATED

from ..models import Ticket, TicketStatus


def create_ticket(*, tenant: Tenant, customer: Customer, subject: str, body: str) -> Ticket:
    with transaction.atomic():
        ticket = Ticket.objects.create(tenant=tenant, customer=customer, subject=subject.strip(), body=body.strip())
        publish_event(
            topic=TICKETS_CREATED,
            key=str(ticket.public_id),
            event=TicketCreatedV1(tenant_public_id=str(tenant.public_id), ticket_public_id=str(ticket.public_id)),
        )
    return ticket


def mark_ticket_answered(*, ticket: Ticket, reply: str) -> Ticket:
    with transaction.atomic():
        ticket.status = TicketStatus.ANSWERED
        ticket.reply = reply
        ticket.answered_at = timezone.now()
        ticket.save(update_fields=["status", "reply", "answered_at", "updated_at"])
        publish_event(
            topic=TICKETS_ANSWERED,
            key=str(ticket.public_id),
            event=TicketAnsweredV1(tenant_public_id=str(ticket.tenant.public_id), ticket_public_id=str(ticket.public_id)),
        )
    return ticket


def mark_ticket_failed(*, ticket: Ticket) -> Ticket:
    ticket.status = TicketStatus.FAILED
    ticket.save(update_fields=["status", "updated_at"])
    return ticket
