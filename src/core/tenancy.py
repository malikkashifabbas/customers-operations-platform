"""Resolve the current tenant from the X-Tenant-ID header (temporary until JWT auth)."""

from django.core.exceptions import ValidationError
from ninja.security import APIKeyHeader

from core.models import Tenant


class TenantHeader(APIKeyHeader):
    param_name = "X-Tenant-ID"

    def authenticate(self, request, key: str | None) -> Tenant | None:
        if not key:
            return None
        try:
            return Tenant.objects.get(public_id=key, is_active=True)
        except (Tenant.DoesNotExist, ValidationError):
            return None
