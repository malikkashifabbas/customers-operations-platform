"""Qdrant, a dedicated vector database: one collection, a dense (meaning) and a sparse (BM25 words) vector per chunk.

Postgres stays the source of truth; this is a search copy that sync code can always rebuild from it.
"""

from functools import lru_cache

from qdrant_client import QdrantClient, models

from config.env import env
from infra.llm.embeddings import EMBEDDING_DIMENSIONS

COLLECTION = "knowledge_chunks"
DENSE = "dense"
SPARSE = "bm25"


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    if not env.qdrant_url:
        raise RuntimeError("QDRANT_URL is not set")
    return QdrantClient(url=env.qdrant_url, timeout=10)


def enabled() -> bool:
    return bool(env.qdrant_url)


def ensure_collection() -> None:
    if client().collection_exists(COLLECTION):
        return
    client().create_collection(
        COLLECTION,
        vectors_config={DENSE: models.VectorParams(size=EMBEDDING_DIMENSIONS, distance=models.Distance.COSINE)},
        # IDF here turns plain word counts into BM25: rare words weigh more, as in a search engine.
        sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    # is_tenant: Qdrant stores each company's points together, so a filtered search stays fast with many companies.
    client().create_payload_index(COLLECTION, "tenant", models.KeywordIndexParams(type="keyword", is_tenant=True))
    client().create_payload_index(COLLECTION, "document", models.KeywordIndexParams(type="keyword"))


def _match(key: str, value: str) -> models.FieldCondition:
    return models.FieldCondition(key=key, match=models.MatchValue(value=value))


def replace_document(*, document: str, points: list[models.PointStruct]) -> None:
    """Delete the document's old points, then write the new ones (chunks get new ids on every re-index)."""
    ensure_collection()
    delete_document(document=document)
    if points:
        client().upsert(COLLECTION, points=points, wait=True)


def delete_document(*, document: str) -> None:
    ensure_collection()
    client().delete(COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(must=[_match("document", document)])), wait=True)


def search(*, tenant: str, vector, using: str, limit: int) -> list[models.ScoredPoint]:
    """One search, always inside one company: the tenant filter is applied by Qdrant, not after it."""
    return client().query_points(
        COLLECTION, query=vector, using=using, query_filter=models.Filter(must=[_match("tenant", tenant)]), limit=limit, with_payload=True
    ).points


def count(*, tenant: str | None = None) -> int:
    query_filter = models.Filter(must=[_match("tenant", tenant)]) if tenant else None
    return client().count(COLLECTION, count_filter=query_filter, exact=True).count
