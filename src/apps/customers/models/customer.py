"""A customer belongs to exactly one tenant; phone is the identity inside that tenant."""

from django.db import models

from core.models import TenantScopedModel


class Customer(TenantScopedModel):
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "phone"], name="customers_unique_phone_per_tenant"),
        ]
        indexes = [
            models.Index(fields=["tenant", "-created_at"], name="customers_tenant_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"
