"""Write-side rules for tickets. Every state change and its event are saved in ONE transaction (outbox pattern)."""

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from core.models import Tenant
from core.limits import TICKET_FOLLOW_UPS_MAX, TICKET_MESSAGES_PER_MINUTE
from infra.cache import ratelimit
from infra.eventbus.events import TicketAnsweredV1, TicketApprovalDecidedV1, TicketCreatedV1, TicketMessageAddedV1
from infra.eventbus.outbox import publish_event
from infra.eventbus.topics import TICKETS_ANSWERED, TICKETS_APPROVAL_DECIDED, TICKETS_CREATED, TICKETS_MESSAGE_ADDED

from ..exceptions import ApprovalNotPending, FollowUpLimitReached, TicketBusy, TicketRateLimited, TicketWaitingApproval
from ..models import MessageAuthor, Ticket, TicketMessage, TicketStatus


def create_ticket(*, tenant: Tenant, customer: Customer, subject: str, body: str) -> Ticket:
    with transaction.atomic():
        ticket = Ticket.objects.create(tenant=tenant, customer=customer, subject=subject.strip(), body=body.strip())
        TicketMessage.objects.create(tenant=tenant, ticket=ticket, author=MessageAuthor.CUSTOMER, body=ticket.body)
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
        _add_reply(ticket, reply)
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
    TicketMessage.objects.create(tenant=ticket.tenant, ticket=ticket, author=MessageAuthor.ASSISTANT, body=reply)
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


def add_follow_up(*, ticket: Ticket, body: str) -> TicketMessage:
    """The customer writes again on an answered (or failed) ticket: message + reopen + event in ONE transaction."""
    if not ratelimit.allow(scope="ticket-message", subject=str(ticket.customer.public_id), limit=TICKET_MESSAGES_PER_MINUTE, window_seconds=60):
        raise TicketRateLimited()
    with transaction.atomic():
        # Row lock: two quick replies must not both see "answered" and start two agent runs.
        locked = Ticket.objects.select_for_update().select_related("tenant").get(pk=ticket.pk)
        if locked.status == TicketStatus.OPEN:
            raise TicketBusy()
        if locked.status == TicketStatus.WAITING_APPROVAL:
            raise TicketWaitingApproval()
        if locked.messages.filter(author=MessageAuthor.CUSTOMER).count() > TICKET_FOLLOW_UPS_MAX:
            raise FollowUpLimitReached()
        message = TicketMessage.objects.create(tenant=locked.tenant, ticket=locked, author=MessageAuthor.CUSTOMER, body=body.strip())
        locked.status = TicketStatus.OPEN
        locked.save(update_fields=["status", "updated_at"])
        publish_event(
            topic=TICKETS_MESSAGE_ADDED,
            key=str(locked.public_id),
            event=TicketMessageAddedV1(
                tenant_public_id=str(locked.tenant.public_id), ticket_public_id=str(locked.public_id), message_public_id=str(message.public_id)
            ),
        )
    return message


def _add_reply(ticket: Ticket, reply: str) -> None:
    now = timezone.now()
    ticket.messages.filter(author=MessageAuthor.CUSTOMER, answered_at__isnull=True).update(answered_at=now)
    TicketMessage.objects.create(tenant=ticket.tenant, ticket=ticket, author=MessageAuthor.ASSISTANT, body=reply)

