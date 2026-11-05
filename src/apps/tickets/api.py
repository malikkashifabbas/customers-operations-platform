"""HTTP routes for tickets: create returns 202 at once, the agent worker answers later."""

from uuid import UUID

from django.http import StreamingHttpResponse
from ninja import Router

from apps.accounts.auth import CustomerJWT
from infra.observability.tracing import label_span, trace_span

from . import selectors, services
from .schemas import TicketIn, TicketOut
from .streams import resume_from, ticket_events

router = Router(tags=["tickets"], auth=CustomerJWT())


@router.post("/", response={202: TicketOut})
def create_ticket(request, payload: TicketIn):
    with trace_span("POST /tickets", metadata={"tenant": request.auth.tenant.slug}):
        ticket = services.create_ticket(
            tenant=request.auth.tenant, customer=request.auth.customer, subject=payload.subject, body=payload.body
        )
        label_span(session_id=f"ticket-{ticket.public_id}", ticket_public_id=str(ticket.public_id))
    return 202, ticket


@router.get("/", response=list[TicketOut])
def list_tickets(request):
    return selectors.list_tickets_for_customer(tenant=request.auth.tenant, customer=request.auth.customer)


@router.get("/{public_id}", response=TicketOut)
def get_ticket(request, public_id: UUID):
    return selectors.get_ticket_for_customer(tenant=request.auth.tenant, customer=request.auth.customer, public_id=public_id)


@router.get("/{public_id}/stream")
def stream_ticket(request, public_id: UUID):
    ticket = selectors.get_ticket_for_customer(tenant=request.auth.tenant, customer=request.auth.customer, public_id=public_id)
    after_id = resume_from(request.headers.get("Last-Event-ID"))
    response = StreamingHttpResponse(ticket_events(ticket, after_id), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
