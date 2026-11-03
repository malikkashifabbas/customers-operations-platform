# pgvector vs Qdrant: load test report (Lesson 19B)

**Question from the senior:** "pgvector is for small projects; big projects use a dedicated vector database." Is that true for OpsPilot?

**Short answer (measured, 3 Nov 2026):** at 200,000 vectors and 50 companies, **default pgvector was not good enough**: it silently returned fewer than 10 results for medium-sized companies. **Tuned pgvector** (two settings) and **Qdrant** both found the right results (recall ≈ 1.000) at similar speed. The scale where pgvector really runs out is above what we tested; the deciding factors are the filter problem and operations, not raw speed.

## Setup

| | |
|---|---|
| Data | 200,000 synthetic vectors, 384 dimensions (the size of our real embeddings), cosine distance |
| Companies | 50, uneven like real customers: 1 big (20% of rows), 9 medium (4% each), 20 at 1.5%, 20 small (0.7%) |
| How vectors were made | Mixes of our 84 real policy embeddings plus noise: real text clusters by topic, so purely random vectors would be a misleading test |
| Queries | 300: 100 per size group (big, medium, small), always filtered to one company, top 10 |
| Right answer | Exact search in numpy over that company's vectors; **recall@10** = share of the true top 10 the store returned |
| Postgres | `pgvector/pgvector:0.8.7-pg17`, HNSW `m=16, ef_construction=64` (same as `knowledge_chunk`), btree on tenant |
| Qdrant | `qdrant/qdrant:v1.19.2`, HNSW `m=16, ef_construct=100`, tenant keyword index with `is_tenant=True` |
| Machine | Laptop, Windows 11, Docker Desktop VM with 8 CPUs and 7.7 GB RAM, one node, everything on localhost |
| Code | `uv run src/manage.py vector_bench load / run / drop` (`src/devtools/management/commands/vector_bench.py`) |

## The problem this test was built to find

Every search is inside one company. pgvector's HNSW index first takes the `ef_search` (default 40) nearest vectors **from all companies**, and only then applies `WHERE tenant_id = ...`. A company with 4% of the rows keeps about 1–2 of those 40, so a request for 10 results gets fewer, with no error.

Postgres picked these plans on its own:

| Company size | Plan Postgres chose |
|---|---|
| big (20%) | HNSW |
| medium (4%) | HNSW |
| small (0.7%) | btree on tenant, then exact sort (always correct, small enough to be fast) |

So the medium companies are the dangerous middle: too big for the exact plan, too small for the HNSW candidate list.

## Results

Latency is p50 measured from Python, so it includes the network round trip. An empty round trip cost **1.6 ms** to Postgres, **12 ms** to Qdrant over REST/HTTP and **3.4 ms** to Qdrant over gRPC (Windows + Docker Desktop; HTTP overhead is high here).

| Setting | big recall | medium recall | small recall | Results < 10 (of 300) | p50 big / medium / small | QPS, 8 threads |
|---|---|---|---|---|---|---|
| **pgvector A: today's defaults** (`ef_search 40`, no iterative scan) | 0.947 | **0.869** | 1.000 | **10** | 14 / 45 / 7 ms | 236 |
| pgvector B: `iterative_scan strict_order`, `ef_search 100` | 0.983 | 0.891 | 1.000 | 0 | 9 / 8 / 7 ms | 269 |
| **pgvector B2: `strict_order`, `ef_search 200`** | 0.999 | **1.000** | 1.000 | 0 | 9 / 14 / 7 ms | 209 |
| pgvector `relaxed_order`, `ef_search 200` | 0.999 | 1.000 | 1.000 | 0 | 9 / 12 / 7 ms | — |
| pgvector C: exact, no HNSW | 1.000 | 1.000 | 1.000 | 0 | 76 / 14 / 7 ms | 68 |
| Qdrant A (19A setup), REST | 1.000 | 1.000 | 1.000 | 0 | 13 / 20 / 15 ms | 103 |
| **Qdrant A, gRPC** | 1.000 | 1.000 | 1.000 | 0 | 7 / 8 / 7 ms | 262 |
| Qdrant B (graph per company: `m=0`, `payload_m=16`), REST | 1.000 | 1.000 | 1.000 | 0 | 17 / 17 / 24 ms | 135 |
| Qdrant B, gRPC | 1.000 | 1.000 | 1.000 | 0 | 6 / 8 / 7 ms | 206 |

**Load and size**

| | pgvector | Qdrant A | Qdrant B |
|---|---|---|---|
| Load | COPY 7 s + HNSW build 139 s (one worker, `maintenance_work_mem 1GB`) | upload + index 112 s | upload + index 101 s |
| Disk | table 313 MB + HNSW 391 MB | 395 MB | 390 MB |
| Container RAM after the test | 922 MB (includes our other data) | 671 MB (both collections) | |

## What this means

1. **Default pgvector is wrong for multi-tenant search at this size**, not because it is slow but because it silently drops results for medium companies. That would show up as the assistant saying "I couldn't find that policy" while the policy exists.
2. **Two settings fix it.** `hnsw.iterative_scan = strict_order` keeps scanning the index until enough rows pass the tenant filter, and `hnsw.ef_search = 200` makes each step wide enough. Recall went to 1.000 for every group, and p50 stayed 7–14 ms. This is now on in OpsPilot (`PGVECTOR_ITERATIVE_SCAN`, `PGVECTOR_EF_SEARCH`, set per search transaction only).
3. **Qdrant got recall 1.000 with zero tuning**, because its filter is applied inside the graph walk and `is_tenant` keeps each company's points together. Over gRPC it was as fast as tuned pgvector. Over REST on this laptop it was slower only because of the HTTP round trip.
4. **Speed is not the deciding factor at 200k.** Both stores answer in under 15 ms (p50). The differences are:

| | pgvector (tuned) | Qdrant |
|---|---|---|
| Correct filtered results | Needs the two settings, and someone has to know about them | Correct by default |
| Consistency | Same transaction as the data: no sync, no stale copy | A copy: needs the outbox → Kafka → worker sync (Lesson 19A), a rebuild command and monitoring |
| Operations | One database to back up, secure and monitor | One more service: backups, upgrades, memory, alerts |
| Keyword search | Postgres full-text (English stemmer) | BM25 sparse vectors (19A: 22/22 vs pgvector 21/22 on our policies) |
| Scaling past one machine | Hard: vertical scaling, read replicas, partitioning | Built-in sharding and replication |

## Recommendation

- **Now (84 chunks, 2 companies) and up to a few hundred thousand chunks:** pgvector with the iterative scan settings is enough and simpler. Keep it as the default.
- **Keep Qdrant ready behind `VECTOR_STORE`** (Lesson 19A): it is already synced and tested, so switching is a setting, not a project.
- **Switch to Qdrant when one of these becomes true:** several million vectors or an index that no longer fits in Postgres memory; many tenants of very different sizes where tuning `ef_search` per case becomes guesswork; vector search load that starts slowing down normal Postgres queries; or a need for sharding/replication of search alone.
- If we use Qdrant in production, use **gRPC** from the API, and the per-company graph (Qdrant B) once there are many companies.

## Limits of this test

- One laptop, Docker Desktop on Windows, one node, no other load. A Linux server would have a much smaller network round trip, especially for Qdrant's HTTP API.
- Postgres ran with its container default `shared_buffers = 128MB`; production would give it more memory.
- Synthetic vectors built from real embeddings, 300 queries; real policy questions were compared separately in 19A (22 questions).
- 200,000 vectors is "medium" scale. The test does not show what happens at 10 or 100 million.

## How to run it again

```bash
uv run src/manage.py vector_bench load            # about 5 minutes on the laptop
uv run src/manage.py vector_bench run --out bench.json
uv run src/manage.py vector_bench drop            # removes the test table and collections
```
