"""What the worker does when documents change: copy them to Qdrant (Postgres stays the source of truth)."""

from apps.knowledge.vector_sync import sync_document
from infra.eventbus.events import KnowledgeChunksChangedV1
from infra.vectorstore import qdrant


def handle_chunks_changed(event: KnowledgeChunksChangedV1) -> str:
    if not qdrant.enabled():
        return "skipped: QDRANT_URL is not set"
    points = sync_document(document_public_id=event.document_public_id)
    return f"document {event.document_public_id[:8]}: {points} points in Qdrant"
