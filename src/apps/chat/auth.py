"""Resolve tenant + customer from headers (temporary until JWT); the customer must belong to that tenant.

X-Tenant-Public-Id   = core_tenant.public_id
X-Customer-Public-Id = customers_customer.public_id
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from ninja.security import APIKeyHeader

from apps.customers.models import Customer
from core.models import Tenant

TENANT_HEADER = "X-Tenant-Public-Id"
CUSTOMER_HEADER = "X-Customer-Public-Id"


@dataclass(frozen=True)
class CustomerPrincipal:
    tenant: Tenant
    customer: Customer


class CustomerHeaders(APIKeyHeader):
    param_name = TENANT_HEADER

    def authenticate(self, request, key: str | None) -> CustomerPrincipal | None:
        tenant_public_id = key
        customer_public_id = request.headers.get(CUSTOMER_HEADER)
        if not tenant_public_id or not customer_public_id:
            return None
        try:
            tenant = Tenant.objects.get(public_id=tenant_public_id, is_active=True)
            customer = Customer.objects.get(public_id=customer_public_id, tenant=tenant)
        except (Tenant.DoesNotExist, Customer.DoesNotExist, ValidationError):
            return None
        return CustomerPrincipal(tenant=tenant, customer=customer)
