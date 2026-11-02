"""HTTP routes for customers: thin, they only call selectors and services."""

from uuid import UUID

from ninja import Router
from ninja.pagination import paginate

from apps.accounts import services as account_services
from apps.accounts.auth import StaffJWT
from apps.accounts.schemas import ResetPasswordIn

from . import selectors, services
from .schemas import CustomerIn, CustomerOut

# Staff only: this list holds every customer's name, phone and email.
router = Router(tags=["customers"], auth=StaffJWT())


@router.get("/", response=list[CustomerOut])
@paginate
def list_customers(request):
    return selectors.list_customers(tenant=request.auth.tenant)


@router.post("/", response={201: CustomerOut})
def create_customer(request, payload: CustomerIn):
    details = {"tenant": request.auth.tenant, "full_name": payload.full_name, "phone": payload.phone, "email": payload.email or ""}
    if payload.password:
        return 201, account_services.register_customer(**details, password=payload.password)
    return 201, services.create_customer(**details)


@router.get("/{public_id}", response=CustomerOut)
def get_customer(request, public_id: UUID):
    return selectors.get_customer(tenant=request.auth.tenant, public_id=public_id)


@router.post("/{public_id}/password", response={204: None})
def reset_password(request, public_id: UUID, payload: ResetPasswordIn):
    customer = selectors.get_customer(tenant=request.auth.tenant, public_id=public_id)
    account_services.reset_customer_password(customer=customer, new_password=payload.new_password)
    return 204, None
