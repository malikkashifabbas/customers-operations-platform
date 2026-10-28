# OpsPilot — Project Memory

> **Har nayi chat / naya developer / naya AI: kaam shuru karne se pehle ye file poori parho.**
> Ye project ki permanent history hai — kya bana, kyun bana, kahan hai, aur agla qadam kya hai.
> **Har lesson mukammal hone par is file ko update karna lazmi hai** (neeche "Lesson log" aur "Current state").

**Last updated:** 27 Oct 2026 — after Lesson 14 (supervisor + billing/account/knowledge subgraphs, `Send` fan-out, compose, registry). Lesson 14 abhi uncommitted.

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
4. **Commit aur push user KHUD karta hai** (26 Oct 2026 se). Har lesson ke baad AI sirf commands (`git add`, `git commit -m "..."`, `git push`) + commit message deta hai, aur pehle secrets scan karta hai. Commit author: `Malik Kashif Abbas <malikkashifabbas28@gmail.com>` (repo-local git config).
5. **Postman:** har nayi ya badli API isi change mein `docs/postman/OpsPilot.postman_collection.json` mein bhi (headers, example body, response note); naye ids environment file mein.
6. **Public repo:** har push se pehle passwords/secrets scan karo. `.env` gitignored hai — kabhi commit nahi. Docs mein asli password kabhi mat likho.
7. Code comments: **ek line** max, sirf "kyun" — code ko dohrao mat.
8. ⭐ **Naming = database ka naam (HARD RULE, 27 Oct 2026).** Jo bhi ID bahar jaye (header, JSON field, event field, query param), us ke naam se **table aur column saaf pata chale**: `<model>_public_id` (maslan `tenant_public_id`, `customer_public_id`, `ticket_public_id`), headers mein `X-Tenant-Public-Id`. `tenant_id`/`customer_id` naam sirf DB ke andar ke BigInt FK columns ke liye — bahar kabhi nahi. Wajah: `X-Tenant-ID` header mein `core_tenant.public_id` jata tha, jabke `customers_customer.tenant_id` column BigInt `1` hai — user ko pata hi nahi chal sakta tha ID kahan se le.

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
| LLM | **Groq Cloud free tier**, `groq:openai/gpt-oss-120b`, sirf `infra/llm/gateway.py` ke zariye | Free, tez, achhi tool calling; provider badalna = `.env` ki ek line |
| Events | **Kafka 4 (KRaft)**, auto-create topics **off** | Hypernim ka stack; topics jaan boojh kar banein |
| Temporary memory | **Redis 8** | Chat memory (TTL), cache, locks, idempotency, pub/sub |
| Business logic | Sirf `services/` (likhna) aur `selectors.py` (parhna) | Ek rule ek jagah — API ho ya AI agent |
| Guardrails | Graph nodes: `guard_input` (regex → LLM classifier) + `refuse` (fixed text) + `guard_output` (code grounding); **fail-open** | Prompt = darkhwast, code = guarantee; asal security tools (`runtime.context`) mein hai |
| Paisa wale actions | Tool ke andar `interrupt()` (read-only checks pehle, action baad mein) + staff decision → outbox + Kafka → worker `Command(resume)`; sirf ticket channel | LLM paisa nahi hila sakta; insaan ki haan ghanton baad bhi aa sakti hai; state Postgres checkpointer mein |

## 4. Environment facts

| Cheez | Value |
|---|---|
| Python | 3.12.15 (uv-managed; system par 3.14 bhi hai) |
| Django server | `uv run src/manage.py runserver` → http://127.0.0.1:8000 |
| Admin | http://127.0.0.1:8000/admin/ (superuser `kashif`) |
| API docs (Swagger) | http://127.0.0.1:8000/api/docs → Authorize → `X-Tenant-Public-Id` (chat/tickets routes par `X-Customer-Public-Id` field bhi) |
| Postman | `docs/postman/` — collection + *OpsPilot Local* environment (demo tenant/customer ids) |
| Tickets + Kafka | `POST /api/tickets/` (202) → outbox → `run_outbox_relay` → Kafka `tickets.created` → `run_agent_worker` (group `agent-workers`) → `answered`. Pehli dafa `uv run src/manage.py create_topics`. Topics: `tickets.created` (3), `tickets.answered` (3), `tickets.created.dlq` (1). Redis keys `opspilot:evt:done:*` (7 din TTL). Test helpers: `playground/kafka_tools.py replay-last / bogus-event` |
| Redis kaam (11B) | Ticket live: `GET /api/tickets/{id}/stream` (SSE from **Redis Stream** `opspilot:ticket:<id>:events` — replay from start, resume with `Last-Event-ID`, heartbeat 15s, MAXLEN ~1000, TTL 1h). Chat: lock `opspilot:lock:thread:<thread_id>` (409), rate limit `opspilot:rate:chat:<customer>:<minute>` (10/min, 429), memory `opspilot:checkpoint*` (24h TTL). Hadein `core/limits.py` |
| Processes (dev) | 3 terminal: `runserver`, `run_outbox_relay`, `run_agent_worker` (+ Docker) |
| Chat API | `POST /api/chat/messages` (JSON) aur `/api/chat/messages/stream` (SSE); headers `X-Tenant-Public-Id` + `X-Customer-Public-Id`; body `{message, conversation_id?}`. Terminal client: `uv run python playground/stream_client.py "my orders"` |
| Postgres (Docker) | `localhost:5433` (5432 par user ka native Windows Postgres hai), DB/user `opspilot`, password `.env` mein |
| Redis | `localhost:6379` |
| Kafka | Windows se `localhost:9092`, Docker network ke andar `kafka:19092` |
| Kafka UI | http://localhost:8080 |
| LLM | `.env`: `Groq_Api_Key` (ya `LLM_API_KEY`), optional `LLM_MODEL` (default `groq:openai/gpt-oss-120b`). Playground scripts `src/` ko khud `sys.path` mein daalte hain |
| Agent se terminal mein chat | `uv run python playground/chat_agent.py` (RAM) ya `... --thread ali-1` (Postgres, restart ke baad yaad). `new` = naya thread, `state` = saved memory, `exit` = band |
| Postman ke liye IDs | `uv run src/manage.py list_ids [--tenant demo-company] [--search fatima] [--limit 20]` → har tenant ka `X-Tenant-Public-Id` + customers ke `X-Customer-Public-Id` |
| Test data | `uv run src/manage.py seed_data` → 2 tenants, 43 customers, **160 orders** (Demo 108, NimbusTech 52); dobara chalana safe. Ali `+923001234567` (ORD-1001 paid, ORD-1002 failed "Card declined by bank", ORD-1003 pending), Sara `sara@example.com` (ORD-2001 refunded, ORD-2002 paid), NimbusTech Ali ORD-1001 = $999 |
| Asli agent se chat | `uv run python playground/chat_support.py [--tenant nimbustech] [--customer sara@example.com] [--thread name]` — har jawab ke saath waqt + LLM calls + tokens |
| Agent eval | `uv run python playground/lesson09_eval.py` — 10 fixed sawal, latency/tokens/tools |
| LangGraph tables | `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` — `PostgresSaver.setup()` banata hai, **Django migrations nahi**. Test threads: `demo-ali`, `demo-sara` |
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
├── docs/learnings.md      ← Learning 1–22 (har lesson ka sabaq)
├── docs/walkthroughs/     ← zaroori files ki line-by-line wazahat + "senior ke sawal" (5-step template); har nayi walkthrough yahan
├── docs/cheatsheet.md     ← sab se zaroori code lines (LangGraph, Kafka, outbox, events, Redis, workers) — naya concept aaye to yahan bhi line jodo
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
    │   ├── tenancy.py     ← TenantHeader (X-Tenant-Public-Id → request.auth; arzi, JWT baad mein)
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
| — | Project memory | `MEMORY.md` + `CLAUDE.md` banaye; commit `69ee763` pushed | — |
| 14 | Supervisor + subgraphs | **`agents/orchestrator/`** (`graph.py`: guard_input → supervisor → `Send` to specialists → compose → guard_output ⇄ compose; `supervisor.py` structured `Route` with `include_raw`, fallback billing+account; prompts `supervisor.v1.md`, `compose.v1.md`); **`agents/registry.py`** (`DOMAINS`); `agents/core/react_subgraph.py` (generic ReAct subgraph, `DomainState`), `agents/core/domain.py` (`DomainSpec`); domains **billing** (orders/spending/refund), **account** (profile), **knowledge** (fixed text until RAG) each with `spec.py` + `prompts/system.v1.md`; specialist wrapper returns only new messages + `response_metadata["domain"]`; compose merges 2+ drafts (RemoveMessage) or rewrites on guard feedback; streaming `routing` event + only compose tokens when multi-domain; chat/worker now use orchestrator (support/graph.py kept as single-agent version + shared guard nodes); chat JSON `routes`; `LLM_MAX_RETRIES=6` (Groq 8000 TPM 429s); Postman multi-domain request; tests: lesson14_eval 7/7, lesson13 4/4, lesson12 16/16 (after restoring the latest-message language rule), Kafka refund E2E, Redis `billing:<task-id>` namespaces | L22 ⭐ |
| 13 | Human approval (`interrupt`) | `request_refund` tool (read-only checks → `interrupt({type, order_number, amount, reason})` → `orders.refund_order` with `select_for_update`); `SupportContext.channel` (chat/ticket) + `tools_for()` (chat never gets the refund tool); **`system.v4.md`** (`{capabilities}` from bound tools, `{refund_rule}` per channel); Ticket `waiting_approval` + `approval_request`/`approval_decision` (migration `tickets.0002`); `decide_approval` (lock + 409 `APPROVAL_NOT_PENDING` + outbox `tickets.approval_decided`); **`staff_api.py`** `GET /api/staff/tickets/`, `POST /{id}/decision` with `core/staff.py` (`X-Staff-Key`, env `STAFF_API_KEY`); worker `ROUTES` (created + approval_decided, per-topic DLQ), `_run()` saves answer OR approval request, `Command(resume=...)`; stream pauses at `approval_required` only while undecided; output guard allows refund claims after `refund_status: done`; Postman *Staff approvals* folder (`staffApiKey` secret, empty in git); tests: `lesson13_approval.py` 4/4, E2E Kafka approve→refunded, 409, 401, eval 16/16 | L21 ⭐ |
| 12B | Output guard rewrite | `guard_output`: bad draft → `RemoveMessage` + `guard_feedback` (`feedback_for`) → back to agent once (`MAX_OUTPUT_RETRIES=1`), then same-id fallback; SSE `reset`; `guard_usage` (classifier via `include_raw=True` + rejected drafts) in API `llm_calls`/`tokens`; `output_retries` in chat JSON; payment-link case now rewrites instead of fallback | L20 |
| 12 | Guardrails + prompt v3 | `agents/domains/support/`: **`state.py`** (`SupportState` = messages + `language`, `blocked_reason`, `output_flags`), **`guards.py`** (free email/phone check → LLM classifier `with_structured_output(InputVerdict)`; fixed refusals per reason × language; `check_output` grounding of emails/links/ORD + banned phrases; `_normalize` for U+2011 hyphens), `prompts/input_guard.v1.md`, **`system.v3.md`** (exact tool list, no pages/links, `{reply_language}`); graph `guard_input → agent/refuse`, `tools_condition` path map `END → guard_output` (same-id replace), fail-open; tool `get_my_spending_summary` (selector `Sum`/`Count` GROUP BY); env `LLM_GUARD_MODEL` (optional) + `get_chat_model(model=)`; SSE events `guardrail` / `replace`; chat JSON `blocked_reason` + `output_flags`; Postman *Guardrails* folder; `playground/lesson12_eval.py` **16/16 PASS** (avg 7.1s vs 2.4s v2) | L19 ⭐ |
| 11B+ | Redis Streams (best practice) | Ticket live updates Pub/Sub se **Redis Streams** par (`infra/cache/streams.py`: XADD maxlen~1000 + EXPIRE 1h, XREAD block); SSE `id:` + `Last-Event-ID` resume + `: keep-alive` heartbeat + `retry:` (`core/sse.py`); DB fallback for expired streams; `pubsub.py` hataya; 6 tests pass (late replay, resume 42/42, heartbeat, reconnect after worker restart) | L18 ⭐ |
| 11B | Redis ke 4 kaam | `langgraph-checkpoint-redis 0.5.2`; `infra/cache/` pubsub (Subscription: subscribe pehle, DB baad), locks (SET NX EX + Lua token release, `redis_lock` CM), ratelimit (INCR + EXPIRE NX); `core/sse.py`, `core/limits.py`; `agents/core/streaming.py::agent_events` (chat + worker share); `get_redis_checkpointer()` (TTL 1440 min, refresh_on_read, prefix `opspilot:checkpoint`) — **chat memory ab Redis**, tickets Postgres; worker `stream` + Pub/Sub + per-ticket lock; `GET /api/tickets/{id}/stream`; chat 409/429; Postman stream request; 6 tests pass | L17 ⭐ |
| 11A | Kafka event flow | `confluent-kafka 2.16`, `redis 6.4`; env `KAFKA_BOOTSTRAP_SERVERS`, `REDIS_URL` (defaults); **`apps/tickets`** (Ticket open/answered/failed, `create_ticket` + `mark_ticket_answered` = data + outbox ek transaction, API POST 202 + GET); **`infra/eventbus`** Django app (OutboxEvent + partial index, topics.py, versioned Pydantic events, publish_event, idempotent producer, manual-commit consumer); **`infra/cache`** (client, keys, idempotency); **`workers`** app (handlers/tickets.py + commands create_topics, run_outbox_relay (skip_locked, mark after Kafka confirm), run_agent_worker (Redis dedupe, 3 attempts, PermanentEventError → DLQ)); Postman Tickets folder; 7 tests pass (duplicate skip, DLQ, worker down → lag → catch-up, relay down → outbox waits); ⚠️ "payment link" hallucination | L14 ⭐ |
| 10 | Chat API + SSE | **`apps/chat`** (no models): `CustomerHeaders` auth (tenant + customer, cross-tenant 401), `ChatIn` (`conversation_id` pattern), `services.run_chat` / `stream_chat` (`stream_mode=["messages","updates"]` → SSE start/tool_call/tool_result/token/done/error), `AssistantUnavailable` 503; `get_pool_checkpointer()` (psycopg pool, lru_cache); thread_id = tenant:customer:conversation; **`docs/postman/`** collection + environment; 9 tests pass | L13 ⭐ |
| 9 | Agent ↔ asli DB | **`apps/orders`** (Order, Decimal amount, TextChoices status, UNIQUE per tenant, `create_order` tenant check, selectors tenant+customer); **`devtools` app** `seed_data` (160 orders); **`agents/domains/support/`** (`SupportContext` via runtime context, `ToolRuntime` tools: get_my_profile / list_my_orders / get_my_order — koi pehchaan wala argument nahi; prompts v1 → **v2**; `agents/core/prompts.py`); eval: v2 ne Roman Urdu + jhoota "forward" wada theek kiya; "Sara ke orders" par ab bhi apne orders dikhata hai (leak nahi) → guardrail chahiye; avg latency 1.9–3.6s | L12 ⭐ |
| 8 | Checkpointer | `langgraph-checkpoint-postgres 3.2.0`; **`src/agents/core/checkpointers.py`** (`postgres_url` with `quote`, `postgres_checkpointer` context manager + `setup()`); 8A InMemory (ali-1 yaad, sara-1 alag; 8 checkpoints); `chat_agent.py --thread` Postgres — naye process mein bhi yaad; ⚠️ agent ne "we can unlock it" wada kiya (koi tool nahi) | L10 ⭐ |
| 7 | LLM + tools | `langchain 1.4.7`, `langchain-groq 1.1.3`; `config/env.py` LLM fields (optional key, `AliasChoices`); **`src/infra/llm/gateway.py`** (`get_chat_model`); 7A LLM classify (structured output) — "account locked" ab `tech+high`; 7B ReAct agent (`@tool`, `bind_tools`, `ToolNode`, `tools_condition`, loop) — 2 tools ek ke baad ek; ⚠️ office hours **hallucinate** kiye | L9 ⭐ |
| 6 | LangGraph bunyaad | `langgraph 1.2.17` installed; `playground/lesson06_first_graph.py` (ticket triage: classify → set_priority → conditional → 3 reply nodes); reducer, invoke, stream, Mermaid → `docs/graphs/lesson06_ticket_triage.md`; 3 tajurbe (path map ke bagair **khamosh bug**) | L8 ⭐ |

## 7. Current state

- ✅ Infra (Docker), Django + Postgres, tenants, customers API — sab chal raha hai.
- ✅ LangGraph + LLM (Groq) chal rahe hain; `infra/llm/gateway.py` bana. Playground mein: ticket triage graph (L6), LLM classify (7A), ReAct tool agent (7B), memory demo (8A), chat with Postgres memory.
- ✅ `src/agents/`: `core/checkpointers.py`, `core/prompts.py`, aur pehla domain agent **`domains/support/`** — tools **asli DB** (orders + customer) par, tenant + customer ke andar band.
- ✅ `apps/orders` + `devtools` (seed_data). Orders ki REST API abhi nahi bani.
- ✅ **Chat API** (`apps/chat`): JSON + SSE streaming, Postman collection. Memory **Redis** (24h TTL) since 11B; lock (409) + rate limit (429).
- ✅ Tickets live stream (Redis Streams: replay + resume + heartbeat) — polling ki zaroorat nahi.
- ✅ **Event-driven tickets** (Lesson 11A): outbox pattern, Kafka relay, agent worker, Redis idempotency, DLQ. `apps/tickets` auth `apps.chat.auth.CustomerHeaders` import karta hai (JWT lesson mein shared auth banegi).
- ✅ Guardrails (Lesson 12): doosre customer / prompt injection / off-topic → fixed refusal (no tools); ghadhe hue links/emails/ORD aur "payment link" jaise jumle → safe fallback; zabaan code tay karta hai; totals DB `SUM()` se.
- ✅ 12B: output guard pehle ek dafa dobara likhwata hai (feedback ke saath), phir fallback; API `tokens` mein guards ka kharcha shamil.
- ✅ 14: multi-agent — supervisor routes to billing / account / knowledge subgraphs (parallel with `Send`), compose merges; refund interrupt works inside the billing subgraph.
- ✅ 13: refund sirf staff approval se (`interrupt` → `waiting_approval` → staff API → Kafka `tickets.approval_decided` → `Command(resume)`); chat mein refund tool nahi.
- ⚠️ Grounding sirf email/link/ORD dekhti hai. Latency +1 LLM call (eval avg 7–10s, Groq free-tier throttle) → `LLM_GUARD_MODEL` chhota model. Staff auth arzi (`X-Staff-Key`) — JWT roles lesson mein. Staff ko naye approval ki notification nahi jati (abhi list poll karna padta hai) — aage `tickets.approval_requested` event. **Code badlo to SAARE workers restart karo** (purane worker ne consumer group mein ticket chura liya tha).
- ⚠️ Auth abhi **arzi** hai (`X-Tenant-Public-Id` + `X-Customer-Public-Id` headers) — JWT lesson mein badlega.
- ✅ 27 Oct 2026: saare bahar wale naam database se milaye — headers `X-Tenant-Public-Id` / `X-Customer-Public-Id`, event fields `tenant_public_id` / `ticket_public_id` (purane `X-Tenant-ID` ab 401). Purane outbox rows / DLQ message purani shakal mein hain — replay karoge to "bad payload" DLQ.
- ⚠️ Agent jo nahi jaanta (office hours, policies) uske liye RAG chahiye — abhi wo "support team se rabta karein" kehta hai.
- ❌ Abhi tak nahi: Redis checkpointer, Kafka producer/consumer code, Redis code, tests folder, ruff/mypy, CI.
- Git: pushed — `7a92e22` (Lessons 1–5), `69ee763` (MEMORY.md + CLAUDE.md), `3926d6d` (Lesson 6), `3440413` (Lesson 7), `c134dd1` (Lessons 8–9; message mein galti se quotes + `-m` aa gaye — pushed hai, isliye chhor diya, force push nahi), `fb17ed1` (Lesson 10, saaf message ✅), `17d9619` (Lesson 11A + naming fix + cheatsheet/walkthroughs), `0c76234` (Lesson 11B + Streams + roadmap decision), `fe17e6f` (Lesson 12 guardrails), `f48b044` (12B + 13 approvals). **Uncommitted:** Lesson 14. User **SourceTree** se khud commit/push karta hai — commit message SourceTree ke liye do: pehli line title, khali line, phir tafseel (bina quotes/`-m`).
- `playground/` = seekhne ki files (git mein, magar project ka hissa nahi); asal code `src/` mein.

## 8. Next steps (roadmap)

| Lesson | Topic |
|---|---|
| ~~6~~ | ✅ LangGraph ki bunyaad — ho gaya (26 Oct 2026) |
| ~~7~~ | ✅ LLM + tools + ReAct agent — ho gaya (26 Oct 2026) |
| ~~8~~ | ✅ Checkpointer (InMemory + Postgres) — ho gaya (26 Oct 2026) |
| ~~9~~ | ✅ Orders app + agent tools ↔ asli DB + prompt v2 + eval — ho gaya (26 Oct 2026) |
| ~~10~~ | ✅ Chat API (JSON + SSE) + Postman — ho gaya (26 Oct 2026) |
| ~~11A~~ | ✅ Kafka event flow (outbox, relay, worker, idempotency, DLQ) — ho gaya (26 Oct 2026) |
| ~~11B~~ | ✅ Redis: Pub/Sub live ticket stream, locks, rate limit, chat memory TTL — ho gaya (27 Oct 2026) |
| ~~12~~ | ✅ Guardrails + prompt v3 + spending summary + PASS/FAIL eval — ho gaya (27 Oct 2026) |
| ~~12B~~ | ✅ Output guard retry with feedback + guard usage — ho gaya (27 Oct 2026) |
| ~~13~~ | ✅ Human approval (`interrupt`) — refund sirf staff ki haan par, Kafka resume — ho gaya (27 Oct 2026) |
| ~~14~~ | ✅ Supervisor + subgraphs (billing / account / knowledge) — ho gaya (27 Oct 2026) |
| **15** | **RAG (pgvector)**: knowledge specialist ko asli policies/FAQ — embeddings, chunking, retriever tool, citations, eval |
| — | Orders REST API |
| 10+ | Kafka outbox + consumer, interrupt approvals, subgraphs/Send/Command (supervisor), RAG (pgvector), Text-to-SQL, evals (LangSmith), JWT auth, tests, CI |
| Later | **Extract AI service (Kafka contracts)**: `agents/` + `workers/` alag deployable service; tools ORM ki jagah backend API (service JWT); `tickets.answered` backend consume kare (eventual consistency); shared/versioned event schemas. Hypernim-style service-to-service Kafka seekhna |
| Later | **Frontend + `src/` → `backend/` rename**: root par `backend/` (Django + apps + agents + workers) aur `frontend/` (React/Next.js); rename sirf frontend shuru hone par, pehle nahi |

**Faisla (27 Oct 2026): AI abhi alag service nahi.** Folder alag ≠ service alag — API, relay, AI worker pehle se alag processes hain (ek image, alag command) aur alag scale hote hain. Alag service tab: alag team, alag runtime (GPU/torch), alag release speed, ya Hypernim-style Kafka seekhna (upar "Later" lesson). Boundary ready hai: `apps/` kabhi `agents/` import nahi karta, sirf `workers/` dono jodta hai.

Bara design (flagship OpsPilot): Kafka `tickets.created` → agent worker → LangGraph supervisor → domain subgraphs (billing/tech/knowledge/analytics) → `interrupt()` approvals → `tickets.resolved`. `agents/` folder: `core/`, `domains/<name>/` (spec.py, graph.py, state.py, routing.py, nodes/, tools/, prompts/), `orchestrator/`, `pipelines/`, `registry.py` (har domain ek line).
