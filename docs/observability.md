# Observability — tracing and experiments with LangSmith

Every agent run (chat, ticket worker, benchmarks, evals) can be traced in **LangSmith**: each graph node, LLM call and
tool call with its latency, tokens, model, inputs and outputs. Benchmarks become **experiments** that can be compared
side by side.

## 1. Switch it on

Create a key at **https://smith.langchain.com → Settings → API Keys**, then in `.env`:
```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=opspilot-dev
```
Restart runserver and the agent worker (they read `.env` only at start; Django's autoreload does not watch `.env`).
`LANGSMITH_TRACING=false` (the default) switches tracing off completely; nothing is sent.

## 2. What you see in LangSmith

| I want to… | Where |
|---|---|
| One customer message, step by step | **Projects → opspilot-dev** → a run named `support-chat` / `support-ticket` → the tree: `triage → billing/knowledge → agent → tools → compose → guard_output` |
| The slow step | Inside a trace, the latency of every child run; LLM runs show model, prompt/completion tokens |
| A whole conversation or ticket | **Threads** (grouped by `session_id`): chat = `conversation_id`, ticket = `ticket-<public_id>` (first run + resume after approval) |
| Only one company / channel | Filter by tag `tenant:demo-company`, `channel:chat`, `channel:ticket`, `resume` |
| p50/p99 latency, tokens, error rate over time | **Monitor** tab of the project |
| Compare optimizations | **Datasets → opspilot-bench → Experiments** — select two and compare `seconds`, `ttft`, `llm_calls`, `tokens` per question |
| Cost in $ | Tokens are counted automatically; add the Groq model prices once under the workspace's model pricing settings |

## 3. Benchmarks = experiments

```bash
uv run python playground/lesson16_bench.py --run optimized --pause 60
```
8 fixed questions (guard refuse, billing, account, multi-domain, 4× RAG) on the LangSmith dataset `opspilot-bench`.
Every run stores its switches (triage on/off, chunks, grade skip, models) as experiment metadata, so a comparison
always shows what was different. Switches come from `.env` or env vars:

| Switch | Default | What it does |
|---|---|---|
| `ORCHESTRATOR_TRIAGE` | `true` | One triage LLM call instead of input guard + supervisor |
| `RAG_SEARCH_LIMIT` | `3` | Policy chunks per search |
| `RAG_SKIP_CONFIDENT_GRADE` | `true` | Skip the LLM grade when vector and keyword search agree on the top chunk |
| `LLM_GUARD_MODEL` | (main model) | Model for triage / grade |

**Rate limits distort latency.** A free Groq tier allows ~8000 tokens/minute; use `--pause 60` for real latency.
Token counts are not affected. Always re-run the evals after a change (`lesson15_eval.py`, `lesson14_eval.py`,
`lesson12_eval.py`): a faster answer that is wrong is not an improvement.

## 4. Personal data

`infra/observability/tracing.py` passes a masking function to LangSmith's `hide_inputs` / `hide_outputs`: phone numbers,
emails and CNICs become `[phone]`, `[email]`, `[cnic]` **before** a trace leaves the process. Our data is fake, so
`LANGSMITH_MASK_PII=false` would be acceptable here, but masking stays on as the habit for real data. Tags and metadata
use public ids and tenant slugs, never names. For data that must never leave the company, LangSmith also exists as a
self-hosted (enterprise) deployment; the code only needs a different `LANGSMITH_ENDPOINT`.

## 5. How it is wired (for code reviews)

- Only `infra/observability/tracing.py` knows LangSmith: `trace_config()` adds a `LangChainTracer` (our own `Client`
  with masking), a run name, tags and metadata to the LangGraph config; `flush()` waits for pending traces in scripts;
  `langsmith_client()` is used for datasets and experiments.
- Called from `apps/chat/services.py` (`_prepare`) and `workers/handlers/tickets.py` (`_run`).
- Inside `client.evaluate()` LangChain traces by itself (nested under the experiment row), so the benchmark adds no tracer.
- Gotchas: pydantic-settings reads `.env` into `Env`, not into `os.environ` (the client gets its key passed in, and the key
  is also exported for runs started by `evaluate()`); `client.list_runs()` / `get_run_url()` are deprecated in favour of
  `client.runs.query()` / `client.runs.get_url()`.
