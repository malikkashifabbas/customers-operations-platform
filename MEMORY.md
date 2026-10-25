# OpsPilot — Project Memory

> **Har nayi chat / naya developer / naya AI: kaam shuru karne se pehle ye file poori parho.**
> Ye project ki permanent history hai — kya bana, kyun bana, kahan hai, aur agla qadam kya hai.
> **Har lesson mukammal hone par is file ko update karna lazmi hai** (neeche "Lesson log" aur "Current state").

**Last updated:** 25 Oct 2026 — after Lesson 5 (customers app + first API), commit `7a92e22` pushed.

---

## 1. Project kya hai

**OpsPilot** (GitHub naam: *customers-operations-platform*) — event-driven, multi-agent **customer operations platform**: customer ke tickets/messages Kafka events ban kar aate hain, LangGraph AI agents unhein samajhte hain, Django ORM tools se data check karte hain, knowledge base (RAG) se jawab dhoondte hain, risky kaam (refund waghera) se pehle insaan se approval lete hain, aur result Kafka par wapas bhejte hain.

- **Maqsad:** Malik Kashif Abbas ka **learning project** — company (Metis International / Hypernim) ka stack seekhna: Python, Django, PostgreSQL, **LangGraph** (main), LangChain, **Kafka** (Hypernim ki services Kafka par chalti hain), **Redis** (temporary memory).
- **Repo:** https://github.com/malikkashifabbas/customers-operations-platform (public, branch `main`)
- **Local path:** `E:\data all\web journey\django-learning\opspilot`

## 2. Working agreement (lazmi)

1. **Learning mode:** har lesson pehle **Roman English / Roman Urdu** mein, line by line samjhao (har abbreviation ka poora naam). User aksar kehta hai "aap khud kar do" — tab steps khud karo aur **report** do. Admin password jaisi cheezein user khud type karta hai.
2. **`docs/learnings.md`:** har nayi seekhi hui cheez "Learning N" ban kar wahan jati hai (kya, kyun, kaise check karein).
3. **`MEMORY.md` (ye file):** har lesson ke baad update — Lesson log + Current state + Next steps.
4. **Commit/push sirf user ke kehne par.** Push user ke Terminal panel se (sandbox ke paas git credentials nahi). Commit author: `Malik Kashif Abbas <malikkashifabbas28@gmail.com>` (repo-local git config).
5. **Public repo:** har push se pehle passwords/secrets scan karo. `.env` gitignored hai — kabhi commit nahi. Docs mein asli password kabhi mat likho.
6. Code comments: **ek line** max, sirf "kyun" — code ko dohrao mat.

## 3. Stack aur faisle (ADR-style)

| Faisla | Kya chuna | Kyun |
|---|---|---|
| Architecture | **Modular monolith** + alag worker processes | Ek codebase, saaf module deewarein; baad mein service nikalna aasan |
| Package manager | **uv** (Python 3.12) | Tez; `uv.lock` se sab ke same versions |
| Web | **Django 5.2 LTS** | Lambi support |
| REST API | **Django Ninja + Pydantic** (DRF nahi) | Async built-in; Pydantic API + settings + LangGraph mein ek jaisa. Ninja ka `schemas.py` = DRF ka `serializers.py` |
| DB | **PostgreSQL 17 + pgvector**, driver **psycopg 3** | Embeddings same DB mein; LangGraph checkpointer bhi psycopg 3 |
| Settings | `base/dev/prod` split + **pydantic-settings** (`config/env.py`) | Secrets env se, type check, fail fast |
| Multi-tenancy | **Har row par `tenant_id`**, har query tenant filter | Ek company doosri ka data na dekh sake (Learning 5 ⭐) |
| IDs | `id` BigInt (andar) + `public_id` UUID (bahar) | Enumeration attack se bachao |
| LangGraph | **Sirf Graph API** (Functional API nahi) | Client ko graph diagram (Mermaid text) docs mein chahiye |
| Events | **Kafka 4 (KRaft)**, auto-create topics **off** | Hypernim ka stack; topics jaan boojh kar banein |
| Temporary memory | **Redis 8** | Chat memory (TTL), cache, locks, idempotency, pub/sub |
| Business logic | Sirf `services/` (likhna) aur `selectors.py` (parhna) | Ek rule ek jagah — API ho ya AI agent |

## 4. Environment facts

| Cheez | Value |
|---|---|
| Python | 3.12.15 (uv-managed; system par 3.14 bhi hai) |
| Django server | `uv run src/manage.py runserver` → http://127.0.0.1:8000 |
| Admin | http://127.0.0.1:8000/admin/ (superuser `kashif`) |
| API docs (Swagger) | http://127.0.0.1:8000/api/docs → Authorize → `X-Tenant-ID` |
| Postgres (Docker) | `localhost:5433` (5432 par user ka native Windows Postgres hai), DB/user `opspilot`, password `.env` mein |
| Redis | `localhost:6379` |
| Kafka | Windows se `localhost:9092`, Docker network ke andar `kafka:19092` |
| Kafka UI | http://localhost:8080 |
| Dev tenants | Demo Company `ac5b565b-f62b-4806-bb6a-9c9e1037226b`, NimbusTech `41832ee0-a2c3-4869-babe-49606dafa97f` |

**Gotchas jo ho chuke hain:**
- Computer restart ke baad **Docker Desktop band** hota hai → Django commands bina error **atak** jati hain. Pehle `docker compose up -d --wait`. Docker ko `Start-Process` se chalao (terminal tab se `&` se chalaya to tab band karte hi Docker bhi band).
- `POSTGRES_PASSWORD` sirf pehli dafa lagta hai; baad mein badalna ho to `ALTER USER`.
- Sandbox (Claude ka) Docker/DB tak nahi pahunch pata — DB wale commands user ke Terminal panel (`run_in_terminal`) se chalao.
- uv cache `C:` par, project `E:` par → hardlink warning (nuqsan nahi; `UV_LINK_MODE=copy`).

## 5. Folder map (jo ab tak bana)

```
opspilot/
├── MEMORY.md              ← ye file (project ki yaadasht)
├── CLAUDE.md              ← AI ke liye: pehle MEMORY.md parho
├── docs/learnings.md      ← Learning 1–7 (har lesson ka sabaq)
├── docker-compose.yml     ← postgres+pgvector, redis, kafka, kafka-ui
├── .env / .env.example    ← secrets (.env gitignored)
├── pyproject.toml, uv.lock
└── src/
    ├── manage.py          ← default settings: config.settings.dev
    ├── config/
    │   ├── settings/ base.py dev.py prod.py
    │   ├── env.py         ← pydantic-settings (POSTGRES_*)
    │   ├── api.py         ⭐ NinjaAPI: har app ka router ek line + DomainError handler
    │   ├── urls.py        ← admin/ + api/
    │   └── asgi.py, wsgi.py (default prod)
    ├── core/              ← shared bunyaad
    │   ├── models/ base.py (BaseModel, TenantScopedModel — abstract), tenant.py (Tenant)
    │   ├── tenancy.py     ← TenantHeader (X-Tenant-ID → request.auth; arzi, JWT baad mein)
    │   ├── exceptions.py  ← DomainError (code + status_code)
    │   └── admin.py
    └── apps/
        └── customers/     ← pehla business app
            ├── models/customer.py   Customer(TenantScopedModel), UNIQUE(tenant, phone)
            ├── services/customers.py create_customer (IntegrityError → 409)
            ├── selectors.py          list_customers, get_customer (hamesha tenant filter)
            ├── schemas.py            CustomerIn, CustomerOut
            ├── api.py                GET / , POST / , GET /{public_id}
            ├── exceptions.py, utils.py (normalize_phone), admin.py
```

**Har naye app ki shakal yahi hogi:** `models/` `services/` `selectors.py` `schemas.py` `api.py` `exceptions.py` `utils.py` `admin.py` `migrations/` (+ baad mein `events.py`, `tests/`). Naya app = `config/api.py` mein ek `add_router` line + `INSTALLED_APPS` mein ek line.

## 6. Lesson log

| # | Lesson | Kya bana | Learning |
|---|---|---|---|
| 1 | Tools + project | uv init, git repo, tool versions check | — |
| 2 | Django | pyproject saaf, Django 5.2, `startproject config src`, repo-local git identity | L1 |
| 2B | Settings split | `settings/base.py dev.py prod.py`, fail-fast env, `check --deploy` | L2 |
| 3A | Docker infra | `docker-compose.yml` (Postgres+pgvector 5433, Redis 8, Kafka 4.3.1 KRaft, Kafka UI), TTL/partition/auto-create tests | L3 |
| 3B | Django ↔ Postgres | psycopg 3 + pydantic-settings, `config/env.py`, pehli `migrate` (10 tables), superuser | L4 |
| 4 | core app | BaseModel, TenantScopedModel, Tenant; `core.0001_initial`; Demo Company tenant | L5 ⭐ |
| 5 | customers app | Pehli API (Ninja), tenant guard, DomainError, unique phone per tenant; 10 tests pass incl. tenant isolation | L6, L7 |
| — | Git | Commit `7a92e22` pushed to GitHub (Lessons 1–5) | — |

## 7. Current state

- ✅ Infra (Docker), Django + Postgres, tenants, customers API — sab chal raha hai.
- ⚠️ Auth abhi **arzi** hai (`X-Tenant-ID` header) — JWT lesson mein badlega.
- ❌ Abhi tak nahi: LangGraph, Kafka producer/consumer code, Redis code, tests folder, ruff/mypy, CI.
- Uncommitted: `MEMORY.md`, `CLAUDE.md` (agle commit mein jayenge).

## 8. Next steps (roadmap)

| Lesson | Topic |
|---|---|
| **6** | **LangGraph ki bunyaad** (Django ke bagair): state, node, edge, pehla chhota graph, Mermaid diagram |
| 7 | Graph mein LLM, tools, conditional edges |
| 8 | Checkpointer (Redis + Postgres), `thread_id`, memory |
| 9 | Graph ↔ Django + SSE streaming |
| 10+ | Kafka outbox + consumer, interrupt approvals, subgraphs/Send/Command (supervisor), RAG (pgvector), Text-to-SQL, evals (LangSmith), JWT auth, tests, CI |

Bara design (flagship OpsPilot): Kafka `tickets.created` → agent worker → LangGraph supervisor → domain subgraphs (billing/tech/knowledge/analytics) → `interrupt()` approvals → `tickets.resolved`. `agents/` folder: `core/`, `domains/<name>/` (spec.py, graph.py, state.py, routing.py, nodes/, tools/, prompts/), `orchestrator/`, `pipelines/`, `registry.py` (har domain ek line).
