"""A tenant is one client company; every tenant-scoped row points at one."""

from django.db import models

from .base import BaseModel


class Tenant(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    # Companies have different rules: one may require a CNIC photo, so the agent edits a profile only where allowed.
    agent_can_edit_profile = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
