"""One policy document of one tenant (e.g. "returns-and-refunds"); its text lives in KnowledgeChunk rows."""

from django.db import models

from core.models import TenantScopedModel


class KnowledgeDocument(TenantScopedModel):
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=200, blank=True)
    # sha256 of the source text: re-seeding skips documents whose text did not change (embedding is slow).
    content_hash = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "slug"], name="knowledge_unique_slug_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.title
