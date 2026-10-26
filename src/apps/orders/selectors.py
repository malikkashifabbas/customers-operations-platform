"""Read-side queries for orders; every query is filtered by tenant AND customer."""

from django.db.models import QuerySet

from apps.customers.models import Customer
from core.models import Tenant

from .models import Order


def list_orders_for_customer(*, tenant: Tenant, customer: Customer, limit: int = 50) -> QuerySet[Order]:
    return Order.objects.filter(tenant=tenant, customer=customer).order_by("-created_at")[:limit]


def get_order_for_customer(*, tenant: Tenant, customer: Customer, order_number: str) -> Order | None:
    return Order.objects.filter(tenant=tenant, customer=customer, order_number__iexact=order_number.strip()).first()
