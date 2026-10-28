"""Read-side queries for the knowledge base; every search is filtered by tenant.

Hybrid search: vector search finds the same meaning in other words, keyword (full-text) search finds exact terms
like "email", "COD" or "restocking fee" that a small embedding model misses. Reciprocal Rank Fusion merges the two.
"""

import re

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from pgvector.django import CosineDistance

from core.models import Tenant

from .models import KnowledgeChunk

CANDIDATES = 10
RRF_K = 60  # standard RRF constant: damps the gap between rank 1 and rank 2 so neither search dominates


def search_chunks(*, tenant: Tenant, query_embedding: list[float], limit: int = 4) -> list[KnowledgeChunk]:
    """Nearest chunks by cosine distance (0 = same meaning, 2 = opposite), only from this tenant's documents."""
    return list(
        KnowledgeChunk.objects.filter(tenant=tenant)
        .select_related("document")
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:limit]
    )


def keyword_search_chunks(*, tenant: Tenant, query: str, limit: int = CANDIDATES) -> list[KnowledgeChunk]:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", query) if len(w) > 1]
    if not words:
        return []
    # OR of the words (not AND): "support email address" must still match a chunk that never says "address".
    search_query = SearchQuery(words[0], config="english")
    for word in words[1:]:
        search_query |= SearchQuery(word, config="english")
    vector = SearchVector("text", config="english")  # same expression as the GIN index, so Postgres can use it
    return list(
        KnowledgeChunk.objects.filter(tenant=tenant)
        .select_related("document")
        .annotate(search=vector, rank=SearchRank(vector, search_query))
        .filter(search=search_query)
        .order_by("-rank")[:limit]
    )


def hybrid_search_chunks(*, tenant: Tenant, query: str, query_embedding: list[float], limit: int = 5) -> list[KnowledgeChunk]:
    by_meaning = search_chunks(tenant=tenant, query_embedding=query_embedding, limit=CANDIDATES)
    by_words = keyword_search_chunks(tenant=tenant, query=query)
    scores: dict[int, float] = {}
    chunks: dict[int, KnowledgeChunk] = {}
    for results in (by_meaning, by_words):
        for rank, chunk in enumerate(results, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + rank)
            chunks.setdefault(chunk.id, chunk)
    best = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [chunks[chunk_id] for chunk_id in best]
