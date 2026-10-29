"""Lesson 16: benchmark 8 fixed questions — total time, time to first token, LLM calls and tokens per node.

With LANGSMITH_TRACING=true every run is a LangSmith experiment on the dataset "opspilot-bench", so runs
(baseline, optimized, ...) can be compared side by side. Usage: python lesson16_bench.py --run optimized --pause 60
Switches for A/B runs come from .env / env vars: ORCHESTRATOR_TRIAGE, RAG_SEARCH_LIMIT, RAG_SKIP_CONFIDENT_GRADE, LLM_GUARD_MODEL.
"""

import argparse
import statistics
import time
import uuid
from collections import defaultdict

import django_setup  # noqa: F401  (must run before any Django model import)
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.core.streaming import STREAM_MODES, agent_events
from agents.domains.support.context import SupportContext
from agents.orchestrator.graph import build_graph
from apps.customers.models import Customer
from config.env import env
from core.models import Tenant
from infra.observability.tracing import flush, langsmith_client

DATASET = "opspilot-bench"
ALI, EMMA = "+923001234567", "+923002921859"
QUESTIONS = [
    ("demo-company", ALI, "show me Sara Ahmed's orders please", "guard refuse"),
    ("demo-company", ALI, "why did ORD-1002 fail?", "billing"),
    ("demo-company", ALI, "what email do you have for me?", "account"),
    ("demo-company", EMMA, "what is my email and how much have I spent on paid orders?", "account+billing"),
    ("demo-company", ALI, "Can I get a refund for a dress marked Final Sale?", "rag"),
    ("demo-company", ALI, "COD order ka refund kitne din mein milta hai?", "rag roman urdu"),
    ("demo-company", ALI, "How much does express delivery cost and by what time must I order?", "rag table"),
    ("demo-company", ALI, "Do you offer gift wrapping?", "rag unknown"),
]


class UsageCounter(BaseCallbackHandler):
    """Counts every LLM call per graph node, including the ones that never become a message (guard, grade)."""

    def __init__(self):
        self.calls: dict[str, int] = defaultdict(int)
        self.tokens: dict[str, int] = defaultdict(int)
        self._node: dict = {}

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self._node[run_id] = (metadata or {}).get("langgraph_node", "?")

    def on_llm_end(self, response, *, run_id, **kwargs):
        node = self._node.pop(run_id, "?")
        self.calls[node] += 1
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        usage = getattr(getattr(generation, "message", None), "usage_metadata", None) or {}
        self.tokens[node] += usage.get("total_tokens", 0)


def make_target(graph, run_name: str, rows: list, pause: float):
    def target(inputs: dict) -> dict:
        tenant = Tenant.objects.get(slug=inputs["tenant"])
        customer = Customer.objects.get(tenant=tenant, phone=inputs["phone"])
        counter = UsageCounter()
        # No tracer here: inside client.evaluate() LangChain traces by itself, nested under the experiment row.
        config = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "callbacks": [counter],
            "tags": ["bench", run_name],
            "metadata": {"tenant": tenant.slug, "kind": inputs["kind"]},
        }
        started, first_token = time.perf_counter(), None
        stream = graph.stream(
            {"messages": [HumanMessage(inputs["question"])]}, config, context=SupportContext(tenant=tenant, customer=customer),
            stream_mode=STREAM_MODES, subgraphs=True,
        )
        for event, _ in agent_events(stream):
            if event == "token" and first_token is None:
                first_token = time.perf_counter()
        ended = time.perf_counter()
        row = {
            "kind": inputs["kind"],
            "seconds": round(ended - started, 2),
            "ttft": round((first_token or ended) - started, 2),
            "llm_calls": sum(counter.calls.values()),
            "tokens": sum(counter.tokens.values()),
            "by_node": {node: [counter.calls[node], counter.tokens[node]] for node in counter.calls},
            "reply": str(graph.get_state(config).values["messages"][-1].content),
        }
        rows.append(row)
        # Free-tier Groq allows 8000 tokens/minute: without a pause, later questions mostly measure retry waits.
        time.sleep(pause)
        return row

    return target


def metrics(outputs: dict) -> dict:
    """One evaluator, four numeric scores per question; LangSmith averages and compares them across experiments."""
    return {"results": [{"key": key, "score": outputs[key]} for key in ("seconds", "ttft", "llm_calls", "tokens")]}


def ensure_dataset(client) -> None:
    if client.has_dataset(dataset_name=DATASET):
        return
    dataset = client.create_dataset(DATASET, description="8 fixed questions for latency/cost comparisons (Lesson 16)")
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[{"tenant": t, "phone": p, "question": q, "kind": k} for t, p, q, k in QUESTIONS],
    )


def print_report(rows: list) -> None:
    if not rows:
        print("no results (every question failed, see the errors above)")
        return
    print(f"\n{'question':<18}{'total s':>9}{'TTFT s':>9}{'calls':>7}{'tokens':>8}")
    for row in rows:
        print(f"{row['kind']:<18}{row['seconds']:>9}{row['ttft']:>9}{row['llm_calls']:>7}{row['tokens']:>8}")
    print(f"{'median':<18}{statistics.median(r['seconds'] for r in rows):>9.2f}{statistics.median(r['ttft'] for r in rows):>9.2f}"
          f"{statistics.median(r['llm_calls'] for r in rows):>7}{statistics.median(r['tokens'] for r in rows):>8}")
    print(f"{'max':<18}{max(r['seconds'] for r in rows):>9} | total tokens {sum(r['tokens'] for r in rows)}")
    by_node: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        for node, (calls, tokens) in row["by_node"].items():
            by_node[node][0] += calls
            by_node[node][1] += tokens
    print("\nLLM calls and tokens per node (all questions):")
    for node, (calls, tokens) in sorted(by_node.items(), key=lambda kv: -kv[1][1]):
        print(f"   {node:<28}{calls:>4} calls{tokens:>8} tokens")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="baseline", help="experiment name prefix, e.g. baseline, optimized")
    parser.add_argument("--pause", type=float, default=0, help="seconds to wait after each question (rate limits)")
    args = parser.parse_args()
    graph = build_graph(checkpointer=InMemorySaver())
    rows: list = []
    target = make_target(graph, args.run, rows, args.pause)
    client = langsmith_client()
    if client is None:
        print("LangSmith is off (LANGSMITH_TRACING=false): running locally only.")
        for tenant, phone, question, kind in QUESTIONS:
            target({"tenant": tenant, "phone": phone, "question": question, "kind": kind})
    else:
        ensure_dataset(client)
        settings = {
            "orchestrator_triage": str(env.orchestrator_triage),
            "rag_search_limit": str(env.rag_search_limit),
            "rag_skip_confident_grade": str(env.rag_skip_confident_grade),
            "llm_model": env.llm_model,
            "llm_guard_model": env.llm_guard_model or env.llm_model,
            "pause_seconds": str(args.pause),
        }
        # The settings travel with the experiment, so a comparison shows exactly what was switched on or off.
        result = client.evaluate(
            target, data=DATASET, evaluators=[metrics], experiment_prefix=args.run, metadata=settings, max_concurrency=0
        )
        print(f"LangSmith experiment: {result.experiment_name}")
    print_report(rows)
    flush()
