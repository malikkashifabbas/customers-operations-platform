"""HTTP routes for tickets: create returns 202 at once, the agent worker answers later."""

from uuid import UUID

from ninja import Router

from apps.chat.api import CUSTOMER_HEADER_DOCS
from apps.chat.auth import CustomerHeaders

from . import selectors, services
from .schemas import TicketIn, TicketOut

router = Router(tags=["tickets"], auth=CustomerHeaders())


@router.post("/", response={202: TicketOut}, openapi_extra=CUSTOMER_HEADER_DOCS)
def create_ticket(request, payload: TicketIn):
    ticket = services.create_ticket(
        tenant=request.auth.tenant, customer=request.auth.customer, subject=payload.subject, body=payload.body
    )
    return 202, ticket


@router.get("/{public_id}", response=TicketOut, openapi_extra=CUSTOMER_HEADER_DOCS)
def get_ticket(request, public_id: UUID):
    return selectors.get_ticket_for_customer(tenant=request.auth.tenant, customer=request.auth.customer, public_id=public_id)
