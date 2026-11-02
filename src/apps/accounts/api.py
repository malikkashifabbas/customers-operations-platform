"""HTTP routes for login: customers and staff get signed tokens here, and every other API then requires one."""

from ninja import Router

from core.limits import LOGINS_PER_MINUTE_PER_IP
from infra.cache import ratelimit

from . import services, tokens
from .auth import CustomerJWT, CustomerPrincipal, StaffJWT
from .exceptions import LoginLocked
from .schemas import (
    AccessTokenOut,
    ChangePasswordIn,
    CustomerLoginIn,
    CustomerSignupIn,
    LogoutIn,
    MeOut,
    RefreshIn,
    StaffLoginIn,
    TokensOut,
)

router = Router(tags=["auth"])


def _limit_by_ip(request) -> None:
    # Account locks stop guessing one password; this stops one machine trying many phones.
    if not ratelimit.allow(scope="login", subject=request.META.get("REMOTE_ADDR", ""), limit=LOGINS_PER_MINUTE_PER_IP, window_seconds=60):
        raise LoginLocked()


@router.post("/customer/signup", response={201: TokensOut})
def customer_signup(request, payload: CustomerSignupIn):
    _limit_by_ip(request)
    return 201, services.sign_up_customer(
        tenant_public_id=payload.tenant_public_id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email or "",
        password=payload.password,
    )


@router.post("/customer/login", response=TokensOut)
def customer_login(request, payload: CustomerLoginIn):
    _limit_by_ip(request)
    return services.login_customer(tenant_public_id=payload.tenant_public_id, phone=payload.phone, password=payload.password)


@router.post("/staff/login", response=TokensOut)
def staff_login(request, payload: StaffLoginIn):
    _limit_by_ip(request)
    return services.login_staff(username=payload.username, password=payload.password)


@router.post("/refresh", response=AccessTokenOut)
def refresh(request, payload: RefreshIn):
    return services.refresh_access(refresh_token=payload.refresh_token)


@router.post("/password", response=TokensOut, auth=[CustomerJWT(), StaffJWT()])
def change_password(request, payload: ChangePasswordIn):
    return services.change_password(principal=request.auth, current_password=payload.current_password, new_password=payload.new_password)


@router.post("/logout", response={204: None}, auth=[CustomerJWT(), StaffJWT()])
def logout(request, payload: LogoutIn):
    services.log_out(principal=request.auth, refresh_token=payload.refresh_token)
    return 204, None


@router.get("/me", response=MeOut, auth=[CustomerJWT(), StaffJWT()])
def me(request):
    principal = request.auth
    if isinstance(principal, CustomerPrincipal):
        customer = principal.customer
        return {
            "role": tokens.ROLE_CUSTOMER,
            "name": customer.full_name,
            "tenant_public_id": principal.tenant.public_id,
            "customer_public_id": customer.public_id,
        }
    return {
        "role": tokens.ROLE_STAFF,
        "name": principal.reviewer,
        "tenant_public_id": principal.tenant.public_id,
        "staff_public_id": principal.staff.public_id,
    }
