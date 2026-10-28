"""A searchable piece of a document (one section, or part of a long one) with its embedding vector."""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models
from pgvector.django import HnswIndex, VectorField

from core.models import TenantScopedModel
from infra.llm.embeddings import EMBEDDING_DIMENSIONS


class KnowledgeChunk(TenantScopedModel):
    # tenant is repeated from the document so the vector search filters one table, without a join.
    document = models.ForeignKey("knowledge.KnowledgeDocument", on_delete=models.CASCADE, related_name="chunks")
    section = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "document"], name="knowledge_chunk_tenant_doc_idx"),
            GinIndex(SearchVector("text", config="english"), name="knowledge_chunk_text_fts"),
            HnswIndex(
                name="knowledge_chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} › {self.section}"
