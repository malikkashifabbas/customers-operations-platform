# Observability — LLM traces with self-hosted Langfuse

Every agent run (chat, ticket worker, evals, benchmarks) can be traced: each graph node, LLM call, tool call,
its time, tokens and model. Everything runs **on your machine**; no account, no data leaves it.

## 1. Start it (once per machine restart)

```bash
docker compose --profile observability up -d
```

Without `--profile observability`, `docker compose up -d` starts only Postgres, Redis and Kafka as before.
First start downloads ~1.5 GB of images and needs ~3 GB RAM.

| Container | Why it exists |
|---|---|
| `langfuse-web` | UI + API on **http://localhost:3100** |
| `langfuse-worker` | Writes incoming traces into ClickHouse in the background |
| `clickhouse` | Column database for traces (fast "p95 of the last 7 days" queries) |
| `seaweedfs` | S3-compatible storage for raw trace events (MinIO no longer ships Docker images) |
| `langfuse-db-init`, `langfuse-bucket-init` | One-shot jobs: create the `langfuse` database in our Postgres and the S3 bucket |

Langfuse also reuses our Postgres (database `langfuse`) and Redis (db `1`).

## 2. Log in

**http://localhost:3100** — `dev@opspilot.example` / `opspilot-local-dev` (local defaults from `docker-compose.yml`).
Organisation **OpsPilot**, project **opspilot-dev** and its API keys already exist (headless init), so nobody signs up.

## 3. Switch tracing on in the app

In `.env`:
```
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3100
```
Restart runserver and the agent worker (they read `.env` only at start). `LANGFUSE_ENABLED=false` (the default)
turns tracing off completely; the app works the same without Langfuse running.

## 4. Find things in the UI

| I want to… | Where |
|---|---|
| See one customer message step by step | **Tracing → Traces** → open a trace → the tree shows `guard_input → supervisor → billing/knowledge → …` with time per node |
| Find the slow step | In a trace, sort/scan the **latency** column of the observations; LLM calls show model and tokens |
| See a whole conversation or ticket | **Sessions** — chat: session = `conversation_id`; ticket: `ticket-<public_id>` (first run + resume after approval) |
| Only one company / channel | Filter **Tags**: `tenant:demo-company`, `channel:chat`, `channel:ticket`, `resume` |
| Compare benchmark runs | **Datasets → opspilot-bench → Runs** — each `lesson16_bench.py --run <name>` is one run with scores `seconds`, `ttft`, `llm_calls`, `tokens` |

## 5. Benchmarks

```bash
uv run python playground/lesson16_bench.py --run baseline
```
8 fixed questions (guard refuse, billing, account, multi-domain, 4× RAG). Prints a table (total time, time to first
token, LLM calls, tokens, calls/tokens per node) and records a Langfuse experiment.

**Rate limits distort latency.** A free Groq tier allows ~8000 tokens/minute; the 8 questions use ~27k tokens, so
without a pause most of the measured time is the SDK waiting on `retry-after`. For real latency numbers use
`--pause 60` (each question starts with a full token bucket). Token counts are not affected either way. Change one thing, run again with a
new `--run` name, compare in the UI. Always re-run the evals too (`lesson15_eval.py`, `lesson14_eval.py`,
`lesson12_eval.py`): a faster answer that is wrong is not an improvement.

## 6. Personal data

`infra/observability/tracing.py` masks phone numbers, emails and CNICs **before** a trace leaves the process
(`my phone is [phone]`). Our data is fake, but this is the habit for real data. Tags and sessions use public ids and
tenant slugs, never names.

## 7. How it is wired (for code reviews)

- Only `infra/observability/tracing.py` knows Langfuse: `trace_config()` adds the Langfuse callback + labels to the
  LangGraph config, `flush()` sends buffered traces from short scripts.
- Called from `apps/chat/services.py` (`_prepare`) and `workers/handlers/tickets.py` (`_run`).
- The Langfuse SDK v3 is built on **OpenTelemetry**, so the same spans could go to Grafana Tempo or any OTel backend.
- Gotcha: pydantic-settings reads `.env` into `Env`, not into `os.environ`; the client therefore gets its keys passed in.
