"""Write-side rules for tickets. Every state change and its event are saved in ONE transaction (outbox pattern)."""

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from core.models import Tenant
from infra.eventbus.events import TicketAnsweredV1, TicketApprovalDecidedV1, TicketCreatedV1
from infra.eventbus.outbox import publish_event
from infra.eventbus.topics import TICKETS_ANSWERED, TICKETS_APPROVAL_DECIDED, TICKETS_CREATED

from ..exceptions import ApprovalNotPending
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


def mark_ticket_waiting_approval(*, ticket: Ticket, request: dict, reply: str) -> Ticket:
    ticket.status = TicketStatus.WAITING_APPROVAL
    ticket.approval_request = request
    ticket.approval_decision = None
    ticket.reply = reply
    ticket.save(update_fields=["status", "approval_request", "approval_decision", "reply", "updated_at"])
    return ticket


def decide_approval(*, ticket: Ticket, approved: bool, note: str, reviewer: str) -> Ticket:
    """Save the staff decision and an event in ONE transaction; the agent worker resumes the paused graph from that event."""
    with transaction.atomic():
        locked = Ticket.objects.select_for_update().get(pk=ticket.pk)
        if locked.status != TicketStatus.WAITING_APPROVAL or locked.approval_decision is not None:
            raise ApprovalNotPending()
        locked.approval_decision = {
            "approved": approved,
            "note": note.strip(),
            "reviewer": reviewer.strip(),
            "decided_at": timezone.now().isoformat(),
        }
        locked.save(update_fields=["approval_decision", "updated_at"])
        publish_event(
            topic=TICKETS_APPROVAL_DECIDED,
            key=str(locked.public_id),
            event=TicketApprovalDecidedV1(tenant_public_id=str(locked.tenant.public_id), ticket_public_id=str(locked.public_id)),
        )
    return locked
