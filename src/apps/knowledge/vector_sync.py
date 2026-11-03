"""Copy a document's chunks from Postgres to Qdrant. Safe to run any number of times: the result is always Postgres's state."""

from qdrant_client import models

from infra.llm.embeddings import embed_sparse_texts
from infra.vectorstore import qdrant

from .models import KnowledgeChunk, KnowledgeDocument


def sync_document(*, document_public_id: str) -> int:
    """Return how many points the document has in Qdrant now (0 when it was deleted from Postgres)."""
    document = KnowledgeDocument.objects.select_related("tenant").filter(public_id=document_public_id).first()
    if document is None:
        qdrant.delete_document(document=document_public_id)
        return 0
    chunks = list(KnowledgeChunk.objects.filter(document=document).order_by("position"))
    sparse = embed_sparse_texts([chunk.text for chunk in chunks])
    points = [
        models.PointStruct(
            id=str(chunk.public_id),
            vector={qdrant.DENSE: [float(x) for x in chunk.embedding], qdrant.SPARSE: models.SparseVector(indices=indices, values=values)},
            payload={
                "tenant": str(document.tenant.public_id),
                "document": str(document.public_id),
                "title": document.title,
                "version": document.version,
                "section": chunk.section,
                "text": chunk.text,
            },
        )
        for chunk, (indices, values) in zip(chunks, sparse, strict=True)
    ]
    qdrant.replace_document(document=str(document.public_id), points=points)
    return len(points)
