"""Resolve tenant + customer from headers (temporary until JWT); the customer must belong to that tenant."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from ninja.security import APIKeyHeader

from apps.customers.models import Customer
from core.models import Tenant

CUSTOMER_HEADER = "X-Customer-ID"


@dataclass(frozen=True)
class CustomerPrincipal:
    tenant: Tenant
    customer: Customer


class CustomerHeaders(APIKeyHeader):
    param_name = "X-Tenant-ID"

    def authenticate(self, request, key: str | None) -> CustomerPrincipal | None:
        customer_id = request.headers.get(CUSTOMER_HEADER)
        if not key or not customer_id:
            return None
        try:
            tenant = Tenant.objects.get(public_id=key, is_active=True)
            customer = Customer.objects.get(public_id=customer_id, tenant=tenant)
        except (Tenant.DoesNotExist, Customer.DoesNotExist, ValidationError):
            return None
        return CustomerPrincipal(tenant=tenant, customer=customer)
