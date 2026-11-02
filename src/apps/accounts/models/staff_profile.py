"""A staff login: Django's User holds the username and password, this row says which company the person works for."""

from django.conf import settings
from django.db import models

from core.models import TenantScopedModel


class StaffProfile(TenantScopedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staff_profile")

    def __str__(self) -> str:
        return f"{self.user.get_username()} @ {self.tenant_id}"
