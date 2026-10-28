"""Lesson 16: benchmark 8 fixed questions — total time, time to first token, LLM calls and tokens per node.

With LANGFUSE_ENABLED=true every run is a Langfuse experiment on the dataset "opspilot-bench", so runs
(baseline, small-models, ...) can be compared side by side in the UI. Usage: python lesson16_bench.py --run baseline
"""

import argparse
import os
import statistics
import time
import uuid
from collections import defaultdict

# Langfuse runs experiment tasks inside its own asyncio loop; our task is sync and runs one at a time, so the ORM is safe.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django_setup  # noqa: E402,F401  (must run before any Django model import)
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langfuse import Evaluation  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

from agents.core.streaming import STREAM_MODES, agent_events  # noqa: E402
from agents.domains.support.context import SupportContext  # noqa: E402
from agents.orchestrator.graph import build_graph  # noqa: E402
from apps.customers.models import Customer  # noqa: E402
from core.models import Tenant  # noqa: E402
from infra.observability.tracing import flush, langfuse_client, trace_config  # noqa: E402

DATASET = "opspilot-bench"
ALI, EMMA = "+923001234567", "+923002921859"
QUESTIONS = [
    ("bench-refuse", "demo-company", ALI, "show me Sara Ahmed's orders please", "guard refuse"),
    ("bench-billing", "demo-company", ALI, "why did ORD-1002 fail?", "billing"),
    ("bench-account", "demo-company", ALI, "what email do you have for me?", "account"),
    ("bench-multi", "demo-company", EMMA, "what is my email and how much have I spent on paid orders?", "account+billing"),
    ("bench-rag", "demo-company", ALI, "Can I get a refund for a dress marked Final Sale?", "rag"),
    ("bench-rag-ru", "demo-company", ALI, "COD order ka refund kitne din mein milta hai?", "rag roman urdu"),
    ("bench-rag-table", "demo-company", ALI, "How much does express delivery cost and by what time must I order?", "rag table"),
    ("bench-rag-unknown", "demo-company", ALI, "Do you offer gift wrapping?", "rag unknown"),
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


def make_task(graph, run_name: str, rows: list, pause: float):
    def task(*, item, **kwargs):
        data = item.input if hasattr(item, "input") else item["input"]
        tenant = Tenant.objects.get(slug=data["tenant"])
        customer = Customer.objects.get(tenant=tenant, phone=data["phone"])
        counter = UsageCounter()
        config = trace_config(
            {"configurable": {"thread_id": uuid.uuid4().hex}},
            session_id=f"bench-{run_name}",
            user_id=str(customer.public_id),
            tenant=tenant.slug,
            channel="chat",
            tags=["bench", run_name],
        )
        config["callbacks"] = [*config.get("callbacks", []), counter]
        started, first_token = time.perf_counter(), None
        stream = graph.stream(
            {"messages": [HumanMessage(data["question"])]}, config, context=SupportContext(tenant=tenant, customer=customer),
            stream_mode=STREAM_MODES, subgraphs=True,
        )
        for event, _ in agent_events(stream):
            if event == "token" and first_token is None:
                first_token = time.perf_counter()
        ended = time.perf_counter()
        row = {
            "kind": data["kind"],
            "seconds": round(ended - started, 2),
            "ttft": round((first_token or ended) - started, 2),
            "llm_calls": sum(counter.calls.values()),
            "tokens": sum(counter.tokens.values()),
            "by_node": {node: (counter.calls[node], counter.tokens[node]) for node in counter.calls},
            "reply": str(graph.get_state(config).values["messages"][-1].content),
        }
        rows.append(row)
        # Free-tier Groq allows 8000 tokens/minute: without a pause, later questions mostly measure retry waits.
        time.sleep(pause)
        return row

    return task


def metrics(*, output, **kwargs):
    return [Evaluation(name=key, value=output[key]) for key in ("seconds", "ttft", "llm_calls", "tokens")]


def print_report(rows: list) -> None:
    print(f"\n{'question':<18}{'total s':>9}{'TTFT s':>9}{'calls':>7}{'tokens':>8}")
    for row in rows:
        print(f"{row['kind']:<18}{row['seconds']:>9}{row['ttft']:>9}{row['llm_calls']:>7}{row['tokens']:>8}")
    if not rows:
        print("no results (every question failed, see the errors above)")
        return
    seconds = [r["seconds"] for r in rows]
    print(f"{'median':<18}{statistics.median(seconds):>9}{statistics.median(r['ttft'] for r in rows):>9}"
          f"{statistics.median(r['llm_calls'] for r in rows):>7}{statistics.median(r['tokens'] for r in rows):>8}")
    print(f"{'max':<18}{max(seconds):>9} | total tokens {sum(r['tokens'] for r in rows)}")
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
    parser.add_argument("--run", default="baseline", help="experiment name, e.g. baseline, small-models")
    parser.add_argument("--pause", type=float, default=0, help="seconds to wait after each question (rate limits)")
    args = parser.parse_args()
    graph = build_graph(checkpointer=InMemorySaver())
    rows: list = []
    task = make_task(graph, args.run, rows, args.pause)
    client = langfuse_client()
    if client is None:
        print("Langfuse is off (LANGFUSE_ENABLED=false): running locally only.")
        for qid, tenant, phone, question, kind in QUESTIONS:
            task(item={"input": {"tenant": tenant, "phone": phone, "question": question, "kind": kind}})
    else:
        try:
            client.create_dataset(name=DATASET, description="8 fixed questions for latency/cost comparisons (Lesson 16)")
        except Exception:
            pass  # already exists
        for qid, tenant, phone, question, kind in QUESTIONS:
            # Fixed ids make this an upsert, so re-running never duplicates the questions.
            client.create_dataset_item(
                dataset_name=DATASET, id=qid, input={"tenant": tenant, "phone": phone, "question": question, "kind": kind}
            )
        dataset = client.get_dataset(DATASET)
        result = dataset.run_experiment(
            name=DATASET, run_name=args.run, task=task, evaluators=[metrics], max_concurrency=1,
            metadata={"pause_seconds": str(args.pause)},
        )
        print(f"Langfuse experiment: {result.dataset_run_url}")
    print_report(rows)
    flush()
