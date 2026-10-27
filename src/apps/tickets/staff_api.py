"""Staff routes: see which tickets wait for a refund approval and approve or reject them (the worker then resumes the agent)."""

from uuid import UUID

from ninja import Router

from core.staff import StaffHeaders
from core.tenancy import TenantHeader

from . import selectors, services
from .schemas import ApprovalIn, StaffTicketOut

router = Router(tags=["staff"], auth=StaffHeaders())

# Ninja auth can document only one header, so the tenant header is added to the docs by hand.
TENANT_HEADER_DOCS = {
    "parameters": [
        {
            "in": "header",
            "name": TenantHeader.param_name,
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
            "description": "core_tenant.public_id of the staff member's company",
        }
    ]
}


@router.get("/", response=list[StaffTicketOut], openapi_extra=TENANT_HEADER_DOCS)
def list_waiting_approval(request):
    return selectors.list_tickets_waiting_approval(tenant=request.auth.tenant)


@router.post("/{public_id}/decision", response={202: StaffTicketOut}, openapi_extra=TENANT_HEADER_DOCS)
def decide(request, public_id: UUID, payload: ApprovalIn):
    ticket = selectors.get_ticket_for_staff(tenant=request.auth.tenant, public_id=public_id)
    ticket = services.decide_approval(ticket=ticket, approved=payload.approved, note=payload.note, reviewer=payload.reviewer)
    return 202, ticket
