"""Read-side queries for the knowledge base; every search is filtered by tenant.

Hybrid search: vector search finds the same meaning in other words, keyword (full-text) search finds exact terms
like "email", "COD" or "restocking fee" that a small embedding model misses. Reciprocal Rank Fusion merges the two.
"""

import re

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection, transaction
from pgvector.django import CosineDistance

from config.env import env
from core.models import Tenant

from .models import KnowledgeChunk

CANDIDATES = 10
RRF_K = 60  # standard RRF constant: damps the gap between rank 1 and rank 2 so neither search dominates


def search_chunks(*, tenant: Tenant, query_embedding: list[float], limit: int = 4) -> list[KnowledgeChunk]:
    """Nearest chunks by cosine distance (0 = same meaning, 2 = opposite), only from this tenant's documents."""
    with transaction.atomic():
        _tune_hnsw()
        return list(
            KnowledgeChunk.objects.filter(tenant=tenant)
            .select_related("document")
            .annotate(distance=CosineDistance("embedding", query_embedding))
            .order_by("distance")[:limit]
        )


def _tune_hnsw() -> None:
    # is_local=true: the settings end with this transaction, so the pooled connection keeps Postgres defaults.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('hnsw.iterative_scan', %s, true), set_config('hnsw.ef_search', %s, true)",
            [env.pgvector_iterative_scan, str(env.pgvector_ef_search)],
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
    ranks: dict[int, dict[str, int]] = {}
    for source, results in (("meaning", by_meaning), ("words", by_words)):
        for rank, chunk in enumerate(results, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + rank)
            chunks.setdefault(chunk.id, chunk)
            ranks.setdefault(chunk.id, {})[source] = rank
    best = sorted(scores, key=scores.get, reverse=True)[:limit]
    # RRF sinks a chunk only one search finds ("deliver" and "delivery" stem differently), so the closest meaning gets an extra place.
    if by_meaning and by_meaning[0].id not in best:
        best.append(by_meaning[0].id)
    for chunk_id in best:
        # Rank per search ({"meaning": 1, "words": 3}): callers can tell how sure the search is.
        chunks[chunk_id].ranks = ranks[chunk_id]
    return [chunks[chunk_id] for chunk_id in best]
