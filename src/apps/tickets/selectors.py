"""Read-side queries for tickets; always filtered by tenant (and by customer for customer-facing reads)."""

from uuid import UUID

from django.shortcuts import get_object_or_404

from apps.customers.models import Customer
from core.models import Tenant

from .models import Ticket


def get_ticket_for_customer(*, tenant: Tenant, customer: Customer, public_id: UUID) -> Ticket:
    return get_object_or_404(Ticket, tenant=tenant, customer=customer, public_id=public_id)


def get_ticket_for_event(*, tenant_public_id: str, ticket_public_id: str) -> Ticket | None:
    # The event carries both ids; matching on both means a forged event cannot reach another tenant's ticket.
    return (
        Ticket.objects.select_related("tenant", "customer")
        .filter(tenant__public_id=tenant_public_id, public_id=ticket_public_id)
        .first()
    )
