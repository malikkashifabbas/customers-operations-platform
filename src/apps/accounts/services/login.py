"""Check login details and hand out tokens. Every failure looks the same, so the API never reveals which phones exist."""

from uuid import UUID

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password

from apps.customers.models import Customer
from apps.customers.utils import normalize_phone
from infra.cache import login_attempts

from .. import tokens
from ..auth import CustomerPrincipal, StaffPrincipal, principal_from_claims
from ..exceptions import InvalidCredentials, InvalidToken, LoginLocked
from ..models import StaffProfile


def _customer_claims(customer: Customer) -> dict:
    return {
        "sub": str(customer.public_id),
        "role": tokens.ROLE_CUSTOMER,
        "tenant_public_id": str(customer.tenant.public_id),
        "customer_public_id": str(customer.public_id),
        "pwd": tokens.password_fingerprint(customer.password),
    }


def _staff_claims(staff: StaffProfile) -> dict:
    return {
        "sub": str(staff.public_id),
        "role": tokens.ROLE_STAFF,
        "tenant_public_id": str(staff.tenant.public_id),
        "staff_public_id": str(staff.public_id),
        "pwd": tokens.password_fingerprint(staff.user.password),
    }


def token_pair(principal: CustomerPrincipal | StaffPrincipal) -> dict:
    claims = _customer_claims(principal.customer) if isinstance(principal, CustomerPrincipal) else _staff_claims(principal.staff)
    return _token_pair(claims)


def _token_pair(claims: dict) -> dict:
    return {
        "access_token": tokens.mint(claims, tokens.ACCESS),
        "refresh_token": tokens.mint(claims, tokens.REFRESH),
        "token_type": "bearer",
        "expires_in": tokens.ACCESS_TOKEN_SECONDS,
    }


def login_customer(*, tenant_public_id: UUID, phone: str, password: str) -> dict:
    phone = normalize_phone(phone)
    attempt = f"customer:{tenant_public_id}:{phone}"
    if login_attempts.is_locked(attempt):
        raise LoginLocked()
    customer = (
        Customer.objects.select_related("tenant")
        .filter(tenant__public_id=tenant_public_id, tenant__is_active=True, phone=phone)
        .first()
    )
    if customer is None or not customer.password:
        make_password(password)  # same work as a real check, so response time does not reveal which phones exist
    elif check_password(password, customer.password):
        login_attempts.clear(attempt)
        return _token_pair(_customer_claims(customer))
    login_attempts.record_failure(attempt)
    raise InvalidCredentials()


def login_staff(*, username: str, password: str) -> dict:
    attempt = f"staff:{username}"
    if login_attempts.is_locked(attempt):
        raise LoginLocked()
    user = authenticate(username=username, password=password)
    staff = StaffProfile.objects.select_related("tenant").filter(user=user, tenant__is_active=True).first() if user else None
    if staff is None:
        login_attempts.record_failure(attempt)
        raise InvalidCredentials()
    login_attempts.clear(attempt)
    return _token_pair(_staff_claims(staff))


def refresh_access(*, refresh_token: str) -> dict:
    claims = tokens.read(refresh_token, tokens.REFRESH)
    principal = principal_from_claims(claims) if claims else None
    if isinstance(principal, CustomerPrincipal):
        fresh = _customer_claims(principal.customer)
    elif isinstance(principal, StaffPrincipal):
        fresh = _staff_claims(principal.staff)
    else:
        raise InvalidToken()
    return {"access_token": tokens.mint(fresh, tokens.ACCESS), "token_type": "bearer", "expires_in": tokens.ACCESS_TOKEN_SECONDS}
