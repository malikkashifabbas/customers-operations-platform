"""Load test: the same synthetic vectors in pgvector and Qdrant, searched inside one company at a time.

load: builds `bench_chunks` (Postgres table, raw SQL, no migration) and two Qdrant collections; the real knowledge tables are never touched.
run:  recall@10 against an exact numpy search, latency and QPS per store setting, split by company size.
drop: removes all of it.
"""

import json
import statistics
import threading
import time

import numpy as np
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from pgvector.psycopg import register_vector
from qdrant_client import QdrantClient, models

from apps.knowledge.models import KnowledgeChunk
from config.env import env
from infra.llm.embeddings import EMBEDDING_DIMENSIONS

TABLE = "bench_chunks"
QDRANT_SHARED = "bench_chunks"  # same setup as 19A: one graph for everyone + tenant index
QDRANT_PER_TENANT = "bench_chunks_per_tenant"  # Qdrant's multitenancy setup: no global graph, one per company
TENANTS = 50
TOPICS = 2000
TOPICS_PER_TENANT = 40
SEED = 19
K = 10
# Share of all rows per tenant: one big company, then medium, then many small ones (like real customers).
SHARES = [0.20] + [0.04] * 9 + [0.015] * 20 + [0.007] * 20
GROUPS = {"big (20%)": [0], "medium (4%)": list(range(1, 10)), "small (0.7%)": list(range(30, 50))}


def _tenant(index: int) -> str:
    return f"t{index:02d}"


def _normalize(vectors: np.ndarray) -> np.ndarray:
    return (vectors / np.linalg.norm(vectors, axis=1, keepdims=True)).astype(np.float32)


def _topics(rng: np.random.Generator) -> np.ndarray:
    # Random vectors would be a wrong test (real text clusters), so topics are mixes of our real policy embeddings.
    base = _normalize(np.array([np.asarray(e, dtype=np.float32) for e in KnowledgeChunk.objects.values_list("embedding", flat=True)]))
    if len(base) < 2:
        raise CommandError("seed_knowledge first: topics are built from the real chunk embeddings")
    first, second = rng.integers(0, len(base), TOPICS), rng.integers(0, len(base), TOPICS)
    mix = rng.uniform(0.3, 0.7, (TOPICS, 1)).astype(np.float32)
    noise = rng.normal(0, 0.025, (TOPICS, EMBEDDING_DIMENSIONS)).astype(np.float32)
    return _normalize(mix * base[first] + (1 - mix) * base[second] + noise)


def _dataset(total: int):
    """Same seed, same data: `run` rebuilds the vectors in memory for the exact search instead of reading them back."""
    rng = np.random.default_rng(SEED)
    topics = _topics(rng)
    counts = [round(share * total) for share in SHARES]
    tenant_topics = [rng.choice(TOPICS, TOPICS_PER_TENANT, replace=False) for _ in range(TENANTS)]
    vectors, tenants = [], []
    for index, count in enumerate(counts):
        picked = topics[rng.choice(tenant_topics[index], count)]
        vectors.append(_normalize(picked + rng.normal(0, 0.018, picked.shape).astype(np.float32)))
        tenants.append(np.full(count, index, dtype=np.int32))
    return topics, tenant_topics, np.concatenate(vectors), np.concatenate(tenants), rng


def _qdrant() -> QdrantClient:
    if not env.qdrant_url:
        raise CommandError("QDRANT_URL is not set")
    return QdrantClient(url=env.qdrant_url, timeout=120)


def _tenant_filter(tenant: str) -> models.Filter:
    return models.Filter(must=[models.FieldCondition(key="tenant", match=models.MatchValue(value=tenant))])


class Command(BaseCommand):
    help = "Load test pgvector vs Qdrant on synthetic vectors: load | run | drop"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["load", "run", "drop"])
        parser.add_argument("--total", type=int, default=200_000)
        parser.add_argument("--queries", type=int, default=100, help="queries per company-size group")
        parser.add_argument("--threads", type=int, default=8)
        parser.add_argument("--out", help="also write the results as JSON here")

    def handle(self, *args, **options):
        getattr(self, f"_{options['action']}")(options)

    def _say(self, text: str) -> None:
        self.stdout.write(text)
        self.stdout.flush()

    # ---------- load ----------

    def _load(self, options):
        started = time.perf_counter()
        _, _, vectors, tenants, _ = _dataset(options["total"])
        self._say(f"generated {len(vectors):,} vectors for {TENANTS} tenants in {time.perf_counter() - started:.1f}s")
        self._load_postgres(vectors, tenants)
        for name, hnsw in ((QDRANT_SHARED, None), (QDRANT_PER_TENANT, models.HnswConfigDiff(m=0, payload_m=16))):
            self._load_qdrant(name, hnsw, vectors, tenants)

    def _load_postgres(self, vectors, tenants):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE}")
            cursor.execute(f"CREATE TABLE {TABLE} (id bigint PRIMARY KEY, tenant_id int NOT NULL, embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL)")
        register_vector(connection.connection)
        started = time.perf_counter()
        with connection.cursor() as cursor, cursor.copy(f"COPY {TABLE} (id, tenant_id, embedding) FROM STDIN WITH (FORMAT BINARY)") as copy:
            copy.set_types(["int8", "int4", "vector"])
            for row_id, (tenant, vector) in enumerate(zip(tenants.tolist(), vectors)):
                copy.write_row((row_id, tenant, vector))
        self._say(f"postgres: copied rows in {time.perf_counter() - started:.1f}s")
        with connection.cursor() as cursor:
            # Same indexes as knowledge_chunk: a btree on tenant and HNSW m=16, ef_construction=64.
            cursor.execute(f"CREATE INDEX {TABLE}_tenant_idx ON {TABLE} (tenant_id)")
            cursor.execute("SET maintenance_work_mem = '1GB'")
            cursor.execute("SET max_parallel_maintenance_workers = 0")  # parallel build needs more /dev/shm than Docker's 64 MB
            started = time.perf_counter()
            cursor.execute(f"CREATE INDEX {TABLE}_hnsw ON {TABLE} USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")
            self._say(f"postgres: HNSW index built in {time.perf_counter() - started:.1f}s")
            cursor.execute(f"ANALYZE {TABLE}")
            cursor.execute("RESET maintenance_work_mem")
            cursor.execute("RESET max_parallel_maintenance_workers")

    def _load_qdrant(self, name, hnsw, vectors, tenants):
        client = _qdrant()
        if client.collection_exists(name):
            client.delete_collection(name)
        client.create_collection(
            name, vectors_config=models.VectorParams(size=EMBEDDING_DIMENSIONS, distance=models.Distance.COSINE), hnsw_config=hnsw
        )
        # The tenant index must exist before the points arrive, so the graph is built with it.
        client.create_payload_index(name, "tenant", models.KeywordIndexParams(type="keyword", is_tenant=True))
        started = time.perf_counter()
        client.upload_collection(
            name, vectors=vectors, payload=({"tenant": _tenant(t)} for t in tenants.tolist()), ids=range(len(vectors)), batch_size=1000
        )
        uploaded = time.perf_counter() - started
        greens = 0
        while greens < 3:  # status can read green for a moment before the optimizer starts building the graph
            time.sleep(2)
            info = client.get_collection(name)
            greens = greens + 1 if info.status == models.CollectionStatus.GREEN else 0
        self._say(f"qdrant {name}: uploaded in {uploaded:.1f}s, indexed after {time.perf_counter() - started:.1f}s ({info.points_count:,} points)")

    # ---------- run ----------

    def _run(self, options):
        topics, tenant_topics, vectors, tenants, rng = _dataset(options["total"])
        queries = []
        for group, members in GROUPS.items():
            for _ in range(options["queries"]):
                tenant = int(rng.choice(members))
                query = topics[rng.choice(tenant_topics[tenant])] + rng.normal(0, 0.018, EMBEDDING_DIMENSIONS).astype(np.float32)
                queries.append((group, tenant, _normalize(query[None, :])[0]))
        truth = []
        for _, tenant, query in queries:
            ids = np.flatnonzero(tenants == tenant)
            truth.append(set(ids[np.argsort(-(vectors[ids] @ query))[:K]].tolist()))
        self._say(f"{len(queries)} queries, exact top {K} from numpy as the right answer\n")
        self._plans(queries)
        results_floor = self._floor()

        variants = {
            "pgvector A: today (ef_search 40)": self._pg_search({"hnsw.ef_search": "40", "hnsw.iterative_scan": "off"}),
            "pgvector B: iterative_scan strict": self._pg_search({"hnsw.ef_search": "100", "hnsw.iterative_scan": "strict_order"}),
            "pgvector C: exact (no HNSW)": self._pg_search({"enable_indexscan": "off"}),
            "qdrant A: 19A setup": self._qdrant_search(QDRANT_SHARED),
            "qdrant B: graph per company": self._qdrant_search(QDRANT_PER_TENANT),
        }
        results = {"floor_ms": results_floor, "total": len(vectors), "tenants": TENANTS, "queries_per_group": options["queries"], "threads": options["threads"], "variants": {}}
        for name, search in variants.items():
            for _, tenant, query in queries[:30]:
                search(tenant, query)  # warm caches so the first variant is not punished
            rows = {group: {"recall": [], "short": 0, "ms": []} for group in GROUPS}
            for (group, tenant, query), right in zip(queries, truth):
                started = time.perf_counter()
                found = search(tenant, query)
                rows[group]["ms"].append((time.perf_counter() - started) * 1000)
                rows[group]["recall"].append(len(right & set(found)) / K)
                rows[group]["short"] += len(found) < K
            qps = self._qps(search, queries, options["threads"])
            results["variants"][name] = {"qps": qps, "groups": {}}
            self._say(f"{name}   (QPS with {options['threads']} threads: {qps:.0f})")
            for group, row in rows.items():
                summary = {
                    "recall": statistics.mean(row["recall"]),
                    "short_answers": row["short"],
                    "p50_ms": statistics.median(row["ms"]),
                    "p95_ms": float(np.percentile(row["ms"], 95)),
                }
                results["variants"][name]["groups"][group] = summary
                self._say(
                    f"   {group:13} recall@10 {summary['recall']:.3f} | fewer than 10: {row['short']:3} | "
                    f"p50 {summary['p50_ms']:6.1f} ms | p95 {summary['p95_ms']:6.1f} ms"
                )
        results["sizes"] = self._sizes()
        self._say(f"\nsizes: {results['sizes']}")
        if options["out"]:
            with open(options["out"], "w", encoding="utf-8") as handle:
                json.dump(results, handle, indent=2)

    def _pg_search(self, settings: dict):
        local = threading.local()
        full = {"hnsw.ef_search": "40", "hnsw.iterative_scan": "off", "enable_indexscan": "on"} | settings

        def search(tenant, query):
            with connection.cursor() as cursor:
                # Settings once per connection, so each timed search is one round trip, like one Qdrant request.
                if getattr(local, "applied", None) != id(connection.connection):
                    cursor.execute("SELECT " + ", ".join(["set_config(%s, %s, false)"] * len(full)), [v for pair in full.items() for v in pair])
                    local.applied = id(connection.connection)
                cursor.execute(f"SELECT id FROM {TABLE} WHERE tenant_id = %s ORDER BY embedding <=> %s::vector LIMIT {K}", [tenant, query.tolist()])
                return [row[0] for row in cursor.fetchall()]

        return search

    def _qdrant_search(self, name: str):
        local = threading.local()

        def search(tenant, query):
            if not hasattr(local, "client"):
                local.client = _qdrant()
            points = local.client.query_points(name, query=query.tolist(), query_filter=_tenant_filter(_tenant(tenant)), limit=K, with_payload=False).points
            return [point.id for point in points]

        return search

    def _qps(self, search, queries, threads: int) -> float:
        chunks = [queries[index::threads] for index in range(threads)]

        def worker(part):
            try:
                for _, tenant, query in part:
                    search(tenant, query)
            finally:
                connection.close()  # each thread gets its own Django connection; close it, or Postgres keeps it open

        pool = [threading.Thread(target=worker, args=(part,)) for part in chunks]
        started = time.perf_counter()
        for thread in pool:
            thread.start()
        for thread in pool:
            thread.join()
        return len(queries) / (time.perf_counter() - started)

    def _floor(self) -> dict:
        """An empty round trip to each store: the part of every latency that is the network, not the search."""
        client = _qdrant()
        timings = {"postgres": [], "qdrant": []}
        with connection.cursor() as cursor:
            for _ in range(50):
                started = time.perf_counter()
                cursor.execute("SELECT 1")
                cursor.fetchall()
                timings["postgres"].append((time.perf_counter() - started) * 1000)
                started = time.perf_counter()
                client.collection_exists(QDRANT_SHARED)
                timings["qdrant"].append((time.perf_counter() - started) * 1000)
        floor = {store: statistics.median(values) for store, values in timings.items()}
        self._say(f"empty round trip: postgres {floor['postgres']:.1f} ms, qdrant {floor['qdrant']:.1f} ms\n")
        return floor

    def _plans(self, queries):
        """Which index Postgres picks today for each company size: HNSW, or the tenant btree (exact)."""
        seen = set()
        with connection.cursor() as cursor:
            for group, tenant, query in queries:
                if group in seen:
                    continue
                seen.add(group)
                cursor.execute(f"EXPLAIN SELECT id FROM {TABLE} WHERE tenant_id = %s ORDER BY embedding <=> %s::vector LIMIT {K}", [tenant, query.tolist()])
                plan = " ".join(row[0] for row in cursor.fetchall())
                picked = "HNSW" if f"{TABLE}_hnsw" in plan else "tenant btree, exact sort" if f"{TABLE}_tenant_idx" in plan else "full scan"
                self._say(f"postgres plan for {group:13}: {picked}")
        self._say("")

    def _sizes(self) -> dict:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT pg_size_pretty(pg_relation_size('{TABLE}')), pg_size_pretty(pg_relation_size('{TABLE}_hnsw'))")
            table, index = cursor.fetchone()
        sizes = {"postgres_table": table, "postgres_hnsw": index}
        client = _qdrant()
        for name in (QDRANT_SHARED, QDRANT_PER_TENANT):
            info = client.get_collection(name)
            sizes[name] = f"{info.points_count:,} points, {info.indexed_vectors_count:,} in HNSW"
        return sizes

    # ---------- drop ----------

    def _drop(self, options):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE}")
        client = _qdrant()
        for name in (QDRANT_SHARED, QDRANT_PER_TENANT):
            if client.collection_exists(name):
                client.delete_collection(name)
        self._say("bench data removed from Postgres and Qdrant")
