"""HTTP routes for customers: thin, they only call selectors and services."""

from uuid import UUID

from ninja import Router
from ninja.pagination import paginate

from core.tenancy import TenantHeader

from . import selectors, services
from .schemas import CustomerIn, CustomerOut

router = Router(tags=["customers"], auth=TenantHeader())


@router.get("/", response=list[CustomerOut])
@paginate
def list_customers(request):
    return selectors.list_customers(tenant=request.auth)


@router.post("/", response={201: CustomerOut})
def create_customer(request, payload: CustomerIn):
    customer = services.create_customer(
        tenant=request.auth,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email or "",
    )
    return 201, customer


@router.get("/{public_id}", response=CustomerOut)
def get_customer(request, public_id: UUID):
    return selectors.get_customer(tenant=request.auth, public_id=public_id)
