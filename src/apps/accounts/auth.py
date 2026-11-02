"""Who is calling: read the Bearer token and load that customer or staff member fresh from the database.

The agent's tools use the customer returned here, so identity comes from a signed token, never from a header or the LLM.
"""

import hmac
from dataclasses import dataclass, field

from ninja.security import HttpBearer

from apps.customers.models import Customer
from core.models import Tenant

from . import tokens
from .models import StaffProfile


@dataclass(frozen=True)
class CustomerPrincipal:
    tenant: Tenant
    customer: Customer
    claims: dict = field(default_factory=dict, compare=False, repr=False)


@dataclass(frozen=True)
class StaffPrincipal:
    tenant: Tenant
    staff: StaffProfile
    claims: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def reviewer(self) -> str:
        return self.staff.user.get_username()


def _same_password(claims: dict, password_hash: str) -> bool:
    return hmac.compare_digest(str(claims.get("pwd", "")), tokens.password_fingerprint(password_hash))


def principal_from_claims(claims: dict) -> CustomerPrincipal | StaffPrincipal | None:
    tenant_public_id = claims.get("tenant_public_id")
    if claims.get("role") == tokens.ROLE_CUSTOMER:
        customer = (
            Customer.objects.select_related("tenant")
            .filter(public_id=claims.get("customer_public_id"), tenant__public_id=tenant_public_id, tenant__is_active=True)
            .first()
        )
        if customer and _same_password(claims, customer.password):
            return CustomerPrincipal(tenant=customer.tenant, customer=customer, claims=claims)
        return None
    if claims.get("role") == tokens.ROLE_STAFF:
        staff = (
            StaffProfile.objects.select_related("tenant", "user")
            .filter(public_id=claims.get("staff_public_id"), tenant__public_id=tenant_public_id, tenant__is_active=True, user__is_active=True)
            .first()
        )
        if staff and _same_password(claims, staff.user.password):
            return StaffPrincipal(tenant=staff.tenant, staff=staff, claims=claims)
        return None
    return None


class CustomerJWT(HttpBearer):
    def authenticate(self, request, token: str) -> CustomerPrincipal | None:
        claims = tokens.read(token, tokens.ACCESS)
        principal = principal_from_claims(claims) if claims else None
        return principal if isinstance(principal, CustomerPrincipal) else None


class StaffJWT(HttpBearer):
    def authenticate(self, request, token: str) -> StaffPrincipal | None:
        claims = tokens.read(token, tokens.ACCESS)
        principal = principal_from_claims(claims) if claims else None
        return principal if isinstance(principal, StaffPrincipal) else None
