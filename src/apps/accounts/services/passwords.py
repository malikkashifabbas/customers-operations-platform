"""Sign up, change or reset a password, log out. A changed password ends every old token through its fingerprint."""

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.customers.models import Customer
from apps.customers.services import create_customer
from core.models import Tenant
from infra.cache import login_attempts

from .. import tokens
from ..auth import CustomerPrincipal, StaffPrincipal
from ..exceptions import InvalidCredentials, LoginLocked, UnknownTenant, WeakPassword
from .login import token_pair


def _check_strength(password: str) -> None:
    try:
        validate_password(password)
    except ValidationError as exc:
        raise WeakPassword(" ".join(exc.messages)) from exc


def _save_customer_password(customer: Customer, password: str) -> None:
    customer.password = make_password(password)
    customer.save(update_fields=["password", "updated_at"])


def register_customer(*, tenant: Tenant, full_name: str, phone: str, email: str, password: str) -> Customer:
    _check_strength(password)
    with transaction.atomic():
        # An existing phone is refused even without a password: otherwise anyone could claim that customer's orders.
        customer = create_customer(tenant=tenant, full_name=full_name, phone=phone, email=email)
        _save_customer_password(customer, password)
    return customer


def sign_up_customer(*, tenant_public_id, full_name: str, phone: str, email: str, password: str) -> dict:
    tenant = Tenant.objects.filter(public_id=tenant_public_id, is_active=True).first()
    if tenant is None:
        raise UnknownTenant()
    customer = register_customer(tenant=tenant, full_name=full_name, phone=phone, email=email, password=password)
    return token_pair(CustomerPrincipal(tenant=tenant, customer=customer))


def change_password(*, principal: CustomerPrincipal | StaffPrincipal, current_password: str, new_password: str) -> dict:
    is_customer = isinstance(principal, CustomerPrincipal)
    attempt = f"password:{principal.claims['sub']}"
    if login_attempts.is_locked(attempt):
        raise LoginLocked()
    stored = principal.customer.password if is_customer else principal.staff.user.password
    if not check_password(current_password, stored):
        login_attempts.record_failure(attempt)
        raise InvalidCredentials()
    _check_strength(new_password)
    login_attempts.clear(attempt)
    if is_customer:
        _save_customer_password(principal.customer, new_password)
    else:
        principal.staff.user.set_password(new_password)
        principal.staff.user.save(update_fields=["password"])
    return token_pair(principal)


def reset_customer_password(*, customer: Customer, new_password: str) -> None:
    """Staff help a customer who forgot their password until SMS or email reset exists; old sessions end."""
    _check_strength(new_password)
    _save_customer_password(customer, new_password)
    login_attempts.clear(f"customer:{customer.tenant.public_id}:{customer.phone}")


def log_out(*, principal: CustomerPrincipal | StaffPrincipal, refresh_token: str | None) -> None:
    tokens.revoke(principal.claims)
    refresh_claims = tokens.read(refresh_token, tokens.REFRESH) if refresh_token else None
    # Only this user's own refresh token: a token from someone else's session is left alone.
    if refresh_claims and refresh_claims.get("sub") == principal.claims["sub"]:
        tokens.revoke(refresh_claims)
