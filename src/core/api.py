"""Public company lookup: the login page knows only the slug in its URL and needs the tenant's public id."""

from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from .models import Tenant

router = Router(tags=["tenants"])


class TenantPublicOut(Schema):
    public_id: UUID
    name: str
    slug: str


# By slug only, never a list: nobody can enumerate which companies use OpsPilot.
@router.get("/{slug}", response=TenantPublicOut, auth=None)
def get_tenant(request, slug: str):
    return get_object_or_404(Tenant, slug=slug, is_active=True)
