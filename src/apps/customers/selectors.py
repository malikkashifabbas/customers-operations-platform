"""Read-side queries for customers; every query is filtered by tenant."""

from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from core.models import Tenant

from .models import Customer


def list_customers(*, tenant: Tenant) -> QuerySet[Customer]:
    return Customer.objects.filter(tenant=tenant).order_by("-created_at")


def get_customer(*, tenant: Tenant, public_id: UUID) -> Customer:
    return get_object_or_404(Customer, tenant=tenant, public_id=public_id)
