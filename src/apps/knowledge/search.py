"""One door for policy search: VECTOR_STORE picks pgvector or Qdrant, and callers get the same shape back from both."""

from dataclasses import dataclass, field

from qdrant_client import models

from config.env import env
from core.models import Tenant
from infra.llm.embeddings import embed_sparse_query
from infra.vectorstore import qdrant

from .selectors import CANDIDATES, RRF_K, hybrid_search_chunks


@dataclass
class HitDocument:
    title: str
    version: str


@dataclass
class Hit:
    """The fields search_policies reads from a KnowledgeChunk, so a Qdrant result looks like one."""

    section: str
    text: str
    document: HitDocument
    ranks: dict[str, int] = field(default_factory=dict)


def _qdrant_search(*, tenant: Tenant, query: str, query_embedding: list[float], limit: int) -> list[Hit]:
    tenant_id = str(tenant.public_id)
    indices, values = embed_sparse_query(query)
    by_meaning = qdrant.search(tenant=tenant_id, vector=query_embedding, using=qdrant.DENSE, limit=CANDIDATES)
    by_words = qdrant.search(tenant=tenant_id, vector=models.SparseVector(indices=indices, values=values), using=qdrant.SPARSE, limit=CANDIDATES)
    # The same Reciprocal Rank Fusion and extra place as the pgvector path, so only the store differs in a comparison.
    scores: dict[str, float] = {}
    points: dict[str, models.ScoredPoint] = {}
    ranks: dict[str, dict[str, int]] = {}
    for source, results in (("meaning", by_meaning), ("words", by_words)):
        for rank, point in enumerate(results, start=1):
            key = str(point.id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank)
            points.setdefault(key, point)
            ranks.setdefault(key, {})[source] = rank
    best = sorted(scores, key=scores.get, reverse=True)[:limit]
    if by_meaning and str(by_meaning[0].id) not in best:
        best.append(str(by_meaning[0].id))
    hits = []
    for key in best:
        payload = points[key].payload
        hits.append(Hit(section=payload["section"], text=payload["text"], document=HitDocument(payload["title"], payload["version"]), ranks=ranks[key]))
    return hits


def search_knowledge(*, tenant: Tenant, query: str, query_embedding: list[float], limit: int) -> list:
    if env.vector_store == "qdrant":
        return _qdrant_search(tenant=tenant, query=query, query_embedding=query_embedding, limit=limit)
    return hybrid_search_chunks(tenant=tenant, query=query, query_embedding=query_embedding, limit=limit)
