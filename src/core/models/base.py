"""Abstract base models every OpsPilot table builds on."""

import uuid

from django.db import models


class BaseModel(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedModel(BaseModel):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="+")

    class Meta:
        abstract = True
