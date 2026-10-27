"""Staff auth for the approval API: tenant header + shared X-Staff-Key (temporary until JWT with roles)."""

import hmac
from dataclasses import dataclass

from ninja.security import APIKeyHeader

from config.env import env
from core.models import Tenant
from core.tenancy import TenantHeader

STAFF_HEADER = "X-Staff-Key"


@dataclass(frozen=True)
class StaffPrincipal:
    tenant: Tenant


class StaffHeaders(APIKeyHeader):
    param_name = STAFF_HEADER

    def authenticate(self, request, key: str | None) -> StaffPrincipal | None:
        if env.staff_api_key is None or not key:
            return None
        # compare_digest takes the same time for every wrong key, so the key cannot be guessed by timing.
        if not hmac.compare_digest(key, env.staff_api_key.get_secret_value()):
            return None
        tenant = TenantHeader().authenticate(request, request.headers.get(TenantHeader.param_name))
        return StaffPrincipal(tenant=tenant) if tenant else None
