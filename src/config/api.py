"""Main API: every app's router is mounted here, one line each."""

from ninja import NinjaAPI

from apps.customers.api import router as customers_router
from core.exceptions import DomainError

api = NinjaAPI(title="OpsPilot API", version="0.1.0")

api.add_router("/customers/", customers_router)


@api.exception_handler(DomainError)
def handle_domain_error(request, exc: DomainError):
    return api.create_response(request, {"code": exc.code, "message": exc.message}, status=exc.status_code)
