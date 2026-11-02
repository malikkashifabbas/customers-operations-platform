"""Staff routes: see which tickets wait for a refund approval and approve or reject them (the worker then resumes the agent)."""

from uuid import UUID

from ninja import Router

from apps.accounts.auth import StaffJWT
from infra.observability.tracing import trace_span

from . import selectors, services
from .schemas import ApprovalIn, StaffTicketOut

router = Router(tags=["staff"], auth=StaffJWT())


@router.get("/", response=list[StaffTicketOut])
def list_waiting_approval(request):
    return selectors.list_tickets_waiting_approval(tenant=request.auth.tenant)


@router.post("/{public_id}/decision", response={202: StaffTicketOut})
def decide(request, public_id: UUID, payload: ApprovalIn):
    ticket = selectors.get_ticket_for_staff(tenant=request.auth.tenant, public_id=public_id)
    # A new trace, not the ticket's first one: staff may decide hours later, and session_id links both in one Thread.
    with trace_span(
        "POST /staff/tickets/decision",
        metadata={"tenant": request.auth.tenant.slug, "session_id": f"ticket-{public_id}", "ticket_public_id": str(public_id)},
    ):
        ticket = services.decide_approval(ticket=ticket, approved=payload.approved, note=payload.note, reviewer=request.auth.reviewer)
    return 202, ticket
