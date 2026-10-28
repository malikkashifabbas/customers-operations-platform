"""Lesson 15: raw search results (no LLM) for both tenants — vector-only vs hybrid; each company must only hit its own text."""

import django_setup  # noqa: F401  (must run before any Django model import)

from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument
from apps.knowledge.selectors import hybrid_search_chunks, search_chunks
from core.models import Tenant
from infra.llm.embeddings import embed_query

QUESTIONS = [
    "how many days do I have to return an item",
    "cash on delivery refund how long",
    "COD order ka refund kitne din mein milta hai",
    "support hours on Saturday and phone number",
    "opened laptop return restocking fee",
    "support email address",
]

if __name__ == "__main__":
    for tenant in Tenant.objects.filter(slug__in=["demo-company", "nimbustech"]).order_by("slug"):
        docs = KnowledgeDocument.objects.filter(tenant=tenant).count()
        chunks = KnowledgeChunk.objects.filter(tenant=tenant).count()
        print(f"\n######## {tenant.name}: {docs} documents, {chunks} chunks")
        for question in QUESTIONS:
            vector = embed_query(question)
            print(f"\nQ: {question}")
            for chunk in search_chunks(tenant=tenant, query_embedding=vector, limit=3):
                assert chunk.tenant_id == tenant.id, "tenant leak"
                print(f"   vector {chunk.distance:.3f}  {chunk.document.title} › {chunk.section}")
            for chunk in hybrid_search_chunks(tenant=tenant, query=question, query_embedding=vector, limit=3):
                assert chunk.tenant_id == tenant.id, "tenant leak"
                print(f"   hybrid        {chunk.document.title} › {chunk.section}")
