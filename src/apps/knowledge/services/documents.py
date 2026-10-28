"""Write-side rules for the knowledge base: (re)index one document, or remove documents that no longer exist."""

import hashlib

from django.db import transaction

from core.models import Tenant
from infra.llm.embeddings import embed_texts

from ..chunking import parse_markdown
from ..models import KnowledgeChunk, KnowledgeDocument


def ingest_document(*, tenant: Tenant, slug: str, markdown: str) -> tuple[KnowledgeDocument, str]:
    """Return the document and what happened: "created", "updated" or "unchanged"."""
    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    existing = KnowledgeDocument.objects.filter(tenant=tenant, slug=slug).first()
    if existing and existing.content_hash == content_hash and existing.chunks.exists():
        return existing, "unchanged"

    parsed = parse_markdown(markdown)
    # Embed before opening the transaction: it takes seconds and must not hold database locks meanwhile.
    vectors = embed_texts([chunk.text for chunk in parsed.chunks])

    with transaction.atomic():
        document, created = KnowledgeDocument.objects.update_or_create(
            tenant=tenant,
            slug=slug,
            defaults={"title": parsed.title, "version": parsed.version, "content_hash": content_hash},
        )
        document.chunks.all().delete()
        KnowledgeChunk.objects.bulk_create(
            KnowledgeChunk(tenant=tenant, document=document, section=chunk.section, position=index, text=chunk.text, embedding=vector)
            for index, (chunk, vector) in enumerate(zip(parsed.chunks, vectors, strict=True))
        )
    return document, "created" if created else "updated"


def remove_documents_except(*, tenant: Tenant, keep_slugs: set[str]) -> int:
    deleted, _ = KnowledgeDocument.objects.filter(tenant=tenant).exclude(slug__in=keep_slugs).delete()
    return deleted
