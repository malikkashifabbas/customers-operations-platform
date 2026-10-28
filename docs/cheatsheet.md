# OpsPilot Code Cheat Sheet — sab se zaroori lines

Har line: **kya likhte hain → kya karti hai → hamare project mein kahan.** Roz ke kaam ke liye yahi kaafi hai.

## 0. IDs ke naam = database ke naam
| Bahar ka naam (header / JSON / event) | Database | Kahan se lein |
|---|---|---|
| `X-Tenant-Public-Id` header, `tenant_public_id` event field | `core_tenant.public_id` | `uv run src/manage.py list_ids` |
| `X-Customer-Public-Id` header | `customers_customer.public_id` | `list_ids` |
| `ticket_public_id` event field, `public_id` in ticket JSON | `tickets_ticket.public_id` | `POST /api/tickets/` ka jawab |
| `tenant_id`, `customer_id` (DB columns) | andar ke BigInt FK (1, 2, 3) | **kabhi bahar nahi** |

---

## 1. LangGraph (agent ka dimagh)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `builder = StateGraph(MessagesState, context_schema=SupportContext)` | Naya graph banao: whiteboard (state) + pehchaan ki parchi (context) | `agents/domains/support/graph.py` |
| `builder.add_node("agent", agent)` | Dabba (node) daalo: naam + function | graph.py |
| `builder.add_edge(START, "agent")` | Seedha arrow: shuru mein agent | graph.py |
| `builder.add_conditional_edges("agent", tools_condition)` | Signboard: tool chahiye → `tools`, warna END | graph.py |
| `builder.add_edge("tools", "agent")` | Loop: tool ke baad wapas agent | graph.py |
| `graph = builder.compile(checkpointer=saver)` | Check karo + chalne ke qabil banao, yaadasht ke saath | graph.py |
| `graph.invoke({"messages": [HumanMessage(text)]}, config, context=ctx)` | Poora chalao, aakhri state lo | `apps/chat/services.py`, `workers/handlers/tickets.py` |
| `graph.stream(input, config, context=ctx, stream_mode=["messages", "updates"])` | Chalte chalte tukde do (tokens + node updates) | `apps/chat/services.py::stream_chat` |
| `config = {"configurable": {"thread_id": "tenant:customer:conv"}}` | Kaun si baat-cheet (yaadasht ki chaabi) | services.py |
| `graph.get_state(config).values["messages"]` | Us baat-cheet ki aakhri photo | chat_support.py |
| `@tool` + `def list_my_orders(runtime: ToolRuntime[SupportContext])` | Function ko tool banao; `runtime` LLM ko nazar nahi aata | `agents/domains/support/tools.py` |
| `ToolNode(TOOLS)` | LLM ke tool call ko asal function chala kar chalane wala node | graph.py |
| `get_chat_model().bind_tools(TOOLS)` | LLM ko tools ki list do | graph.py |
| `get_chat_model().with_structured_output(MyPydantic)` | LLM se pakki shakal ka jawab | `playground/lesson07a_llm_classify.py` |
| `init_chat_model("groq:openai/gpt-oss-120b", api_key=...)` | Provider dekh kar LLM banao | `infra/llm/gateway.py` |

### 1B. Guardrails (Lesson 12)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `class SupportState(MessagesState): language; blocked_reason; output_flags` | Whiteboard par messages ke ilawa guards ke faisle | `agents/domains/support/state.py` |
| `builder.add_conditional_edges("guard_input", route_after_input, {"agent": "agent", "refuse": "refuse"})` | Bura sawal → `refuse` (fixed text, koi LLM nahi), achha → `agent` | graph.py |
| `builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "guard_output"})` | Path map se `END` ka raasta **badla**: jawab pehle guard se guzre | graph.py |
| `guards.mentions_other_person(message, customer)` | Muft code check (kisi aur ki email/phone) — LLM se **pehle** | `agents/domains/support/guards.py` |
| `get_chat_model(model=env.llm_guard_model).with_structured_output(InputVerdict)` | LLM classifier: `decision` + `language` | guards.py |
| `except Exception: ... "blocked_reason": None` | **Fail-open**: guard gira to sawal agent ko (asal security tools mein hai) | graph.py::guard_input |
| `guards.check_output(reply, state["messages"])` | Reply ki email/link/ORD tool results mein hain? mana jumle? | guards.py |
| `AIMessage(safe, id=reply.id)` | **Same id** → `add_messages` purana jawab **badal** deta hai, naya nahi jodta | graph.py::guard_output |
| `_normalize(text)` | LLM ke `‑` (U+2011), ` `, `’` ko seedha karo, warna regex chook jaye | guards.py |
| SSE `guardrail` / `replace` events | Frontend: inkaar ka sabab / poora bubble text badlo | `agents/core/streaming.py` |
| `uv run python playground/lesson12_eval.py` | 16 sawal, PASS/FAIL, exit code 1 agar koi fail | playground |
| `RemoveMessage(id=reply.id)` + `guard_feedback` + `output_retries` | 12B: bura draft mitao, wajah batao, **ek** dafa dobara likhwao (counter = infinite loop se bachao) | graph.py::guard_output |
| `add_conditional_edges("guard_output", route_after_output, {"agent": "agent", END: END})` | Guard se wapis agent ka loop | graph.py |
| `with_structured_output(Model, include_raw=True)` → `{"raw", "parsed", "parsing_error"}` | `raw.usage_metadata` = classifier ka kharcha | guards.py::classify_input |

### 1C. Human approval — `interrupt` (Lesson 13)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `decision = interrupt({...})` | Graph **roko**, state checkpointer mein; resume par yahi line `decision` lautati hai | `tools.py::request_refund` |
| ⚠️ `interrupt()` se pehle sirf **read-only** | Resume par tool **upar se dobara** chalta hai; paisa `interrupt()` ke **baad** | tools.py |
| `graph.get_state(config).interrupts[0].value` | Ruka hua hai? kis cheez ki approval chahiye? | `workers/handlers/tickets.py::_run` |
| `graph.stream(Command(resume=decision), config, context=ctx)` | Wahin se chalao jahan ruka tha | `handle_approval_decided` |
| `tools_for(context)` + `ToolNode(ALL_TOOLS)` | Chat ko refund tool **dikhao hi mat**; ToolNode sab chala sakta hai | tools.py / graph.py |
| `services.decide_approval(...)` = faisla + outbox event **ek transaction** | Staff API tez; worker Kafka se resume karta hai | `apps/tickets/services/tickets.py` |
| `select_for_update()` + status dobara check | Double approval → 409, double refund → impossible | `decide_approval`, `orders.refund_order` |
| `ROUTES = {topic: (EventClass, handler, dlq_topic)}` | Ek worker, kai event types | `run_agent_worker.py` |
| `X-Tenant-Public-Id` + `X-Staff-Key` (`hmac.compare_digest`) | Arzi staff auth (JWT roles tak) | `core/staff.py` |
| `uv run python playground/lesson13_approval.py` | A failed / B reject / C approve / D chat — PASS/FAIL | playground |

### 1D. Supervisor + subgraphs (Lesson 14)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `DOMAINS = {spec.name: spec for spec in (BILLING, ACCOUNT, KNOWLEDGE)}` | Registry: naya domain = folder + ek line | `agents/registry.py` |
| `DomainSpec(name, description, build)` | `description` = supervisor ka menu | `agents/core/domain.py` |
| `build_react_subgraph(all_tools=, tools_for=, prompt_for=, context_schema=)` | Ek generic ReAct subgraph, domain sirf tools + prompt deta hai | `agents/core/react_subgraph.py` |
| `with_structured_output(Route, include_raw=True)` → `routes` | Supervisor: kaun se specialist (jawab nahi deta) | `agents/orchestrator/supervisor.py` |
| `return [Send(name, payload) for name in state["routes"]]` | **Map**: specialists parallel, ek superstep mein | `orchestrator/graph.py::route_to_domains` |
| `add_conditional_edges("supervisor", route_to_domains, list(DOMAINS))` | Send ke liye mumkin manzilein batao | graph.py |
| `add_node(name, specialist(spec), input_schema=DomainState)` | Specialist ko sirf `messages` + `language` | graph.py |
| `subgraph.invoke(state, context=runtime.context)` → sirf naye messages | Subgraph ko node ke andar chalao; parent ka checkpointer namespace `billing:<task id>` mein | graph.py::specialist |
| `response_metadata["domain"] = "billing"` | Draft ka label (LLM API ko nahi jata) | graph.py::specialist |
| `[RemoveMessage(id=d.id) for d in drafts] + [merged]` | **Reduce**: compose 2+ drafts ko ek jawab banata hai | graph.py::compose |
| ⚠️ Parallel nodes ek plain key (`language`) na likhein | `InvalidUpdateError`; reducer wali key (`messages`) theek hai | — |
| SSE `routing` + multi-domain mein sirf `compose` tokens | Do specialists ke tokens aapas mein na milein | `agents/core/streaming.py` |
| `LLM_MAX_RETRIES=6` → `init_chat_model(..., max_retries=)` | 429 par `retry-after` ke mutabiq ruk kar dobara | `infra/llm/gateway.py` |
| `uv run python playground/lesson14_eval.py` | Routing + "ek hi jawab" PASS/FAIL | playground |

### 1E. RAG — pgvector + hybrid search (Lesson 15)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `VectorExtension()` migration ke shuru mein | `CREATE EXTENSION vector` (makemigrations khud nahi likhta) | `apps/knowledge/migrations/0001_initial.py` |
| `embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)` | 384 numbers ka column; model ke saath hi badlo | `apps/knowledge/models/chunk.py` |
| `HnswIndex(fields=["embedding"], opclasses=["vector_cosine_ops"])` | Tez nearest-neighbour index | chunk.py |
| `GinIndex(SearchVector("text", config="english"))` | Keyword (full-text) index | chunk.py |
| `annotate(distance=CosineDistance("embedding", vec)).order_by("distance")` | Matlab se milte tukde (0 = same) | `apps/knowledge/selectors.py` |
| `SearchQuery(a) \| SearchQuery(b)` + `.filter(search=query)` | Alfaaz ka OR match (`@@`, GIN use hota hai) | selectors.py |
| `score += 1 / (60 + rank)` | **Reciprocal Rank Fusion**: dono searches ko milao | `hybrid_search_chunks` |
| `TextEmbedding(model, cache_dir=...)` + `lru_cache` | Local embeddings, model ek dafa load | `infra/llm/embeddings.py` |
| `parse_markdown()` → `"Title › Section
..."` | `##` par chunks, tables poore, har chunk ka header | `apps/knowledge/chunking.py` |
| `sha256(markdown)` == `content_hash` → `unchanged` | Seed idempotent, sirf badli files embed | `services/documents.py` |
| `uv run src/manage.py seed_knowledge` | `devtools/knowledge/<tenant>/*.md` → DB | devtools |
| query → `retrieve` → `grade_documents` → `generate_answer` / `rewrite_question` | Agentic RAG; steps `nodes.py`, wiring `graph.py` | `agents/domains/knowledge/` |
| `if not response.tool_calls: response = _search_call(question)` | Search ki guarantee **code** se (`tool_choice="required"` crash karta hai) | `nodes.py` |
| `graph.stream(..., subgraphs=True)` | Node ke andar wale subgraph ke tokens bhi stream hon | `apps/chat/services.py`, `workers/handlers/tickets.py` |
| `uv run python playground/lesson15_retrieval.py` | Vector vs hybrid nateeje + tenant `assert` (bina LLM) | playground |
| `uv run python playground/lesson15_eval.py` | 19 jaal wale sawal, PASS/FAIL | playground |

### 1F. Observability — Langfuse self-hosted (Lesson 16)

| Code / command | Kya karta hai | Kahan |
|---|---|---|
| `docker compose --profile observability up -d` | Langfuse + ClickHouse + SeaweedFS chalao (UI `localhost:3100`) | `docker-compose.yml` |
| `LANGFUSE_ENABLED=true` (`.env`) + runserver/worker **restart** | Tracing on (autoreload `.env` nahi dekhta) | `.env` |
| `config = trace_config(config, session_id=, user_id=, tenant=, channel=, tags=)` | Callback + labels jodo; off ho to config waisi hi | `infra/observability/tracing.py` |
| `metadata["langfuse_session_id" / "langfuse_user_id" / "langfuse_tags"]` | Langfuse callback ye keys padhta hai | tracing.py |
| `Langfuse(..., mask=mask)` + `model_dump()` | PII trace bhejne se **pehle** chhupao (messages pydantic objects hain) | tracing.py |
| `flush()` | Chhoti scripts exit se pehle traces bhejein | tracing.py |
| `dataset.run_experiment(name=, run_name=, task=, evaluators=[...])` + `Evaluation(name=, value=)` | Har run ek experiment; UI mein side by side | `playground/lesson16_bench.py` |
| `uv run python playground/lesson16_bench.py --run <name> --pause 60` | 8 sawal: waqt, TTFT, calls, tokens per node | playground |
| Groq headers `x-ratelimit-limit-tokens` / `-requests` | Free tier: 8000 tokens/min, 1000 requests/day | — |

---

## 2. Kafka (dak-khana / post office)

**Misaal:** Kafka = **dak-khana**. Topic = **mailbox**, partition = mailbox ke **khaane**, message = **khat**, producer = khat **daalne wala**, consumer = khat **uthane wala dakiya**, consumer group = **dakiyon ki team**, offset = **khat number**, commit = register mein sign: "is number tak parh liya".

| Code | Kya karta hai | Kahan |
|---|---|---|
| `Producer({"bootstrap.servers": "localhost:9092", "enable.idempotence": True, "acks": "all"})` | Khat bhejne wala banao; idempotent = retry se duplicate nahi | `infra/eventbus/kafka.py` |
| `producer.produce(topic, key=ticket_id, value=json_bytes, on_delivery=callback)` | Khat mailbox mein daalo (key = kaun sa khaana) | `run_outbox_relay.py` |
| `producer.flush(15)` | Ruko jab tak saare khat pahunch na jayein (max 15s) | relay |
| `Consumer({"bootstrap.servers": ..., "group.id": "agent-workers", "enable.auto.commit": False, "auto.offset.reset": "earliest"})` | Dakiya banao: team ka naam, sign khud karenge, shuru se parho | `infra/eventbus/kafka.py` |
| `consumer.subscribe(["tickets.created"])` | Ye mailbox dekhte raho | `run_agent_worker.py` |
| `msg = consumer.poll(1.0)` | "Koi khat aaya?" (1 second intezar; nahi to `None`) | worker |
| `msg.value()`, `msg.key()`, `msg.partition()`, `msg.offset()`, `msg.error()` | Khat ka andar ka maal, chaabi, khaana, number, ghalti | worker |
| `consumer.commit(message=msg, asynchronous=False)` | Sign karo: "ye khat ho gaya" — **kaam ke baad** | worker |
| `consumer.close()` | Team chhorte waqt batao (partitions doosron ko mil jayein) | worker |
| `AdminClient({...}).create_topics([NewTopic(name, num_partitions=3, replication_factor=1)])` | Naya mailbox banao | `create_topics.py` |

---

## 3. Outbox (bhejne wale khaton ki tokri) + Django

| Code | Kya karta hai | Kahan |
|---|---|---|
| `with transaction.atomic():` | Andar ka sab kuch **ek saath**: ya sab save, ya kuch nahi | `apps/tickets/services/tickets.py` |
| `publish_event(topic=TICKETS_CREATED, key=..., event=TicketCreatedV1(...))` | Event tokri (outbox table) mein daalo — Kafka ko nahi | services |
| `OutboxEvent.objects.select_for_update(skip_locked=True).filter(published_at__isnull=True)` | Unbheje khat uthao; doosra relay jo utha chuka wo chhor do | relay |
| `OutboxEvent.objects.filter(id__in=ids).update(published_at=timezone.now())` | Bheje hue khaton par "bhej diya" ki mohar | relay |

---

## 4. Events (Pydantic)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `TicketCreatedV1(tenant_public_id=..., ticket_public_id=...)` | Event banao (`event_id`, `occurred_at` khud) | services |
| `event.model_dump(mode="json")` | Event → dict (JSON ke qabil) — outbox mein save | `infra/eventbus/outbox.py` |
| `TicketCreatedV1.model_validate_json(msg.value())` | Kafka ke bytes → pakka event; ghalat ho to `ValidationError` | worker |

---

## 5. Redis (mitne wali siyahi wala notice board)

| Code | Kya karta hai | Kahan |
|---|---|---|
| `redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)` | Redis se connection | `infra/cache/client.py` |
| `r.set(key, 1, ex=7*24*3600)` | Likho, 7 din baad **khud mit jaye** (TTL) | `infra/cache/idempotency.py` |
| `r.exists(key)` | Likha hua hai? (1/0) | idempotency |
| `r.get(key)`, `r.delete(key)`, `r.ttl(key)` | Parho, mitao, kitne second baqi | — |
| `keys.event_done(event_id)` → `"opspilot:evt:done:<id>"` | Har key ka naam ek jagah se | `infra/cache/keys.py` |
| `r.set(key, token, nx=True, ex=60)` | **Lock** lagao: sirf tab likho jab pehle se na ho (`nx`), 60s baad khud khule (`ex`) | `infra/cache/locks.py::acquire` |
| `r.eval(RELEASE_SCRIPT, 1, key, token)` | Lock kholo — sirf apna (token mile to hi delete) | `locks.py::release` |
| `with redis_lock("thread:<id>", 120) as acquired:` | Lock ka context manager: andar kaam, bahar khud khule | chat services, worker handler |
| `pipe.incr(key); pipe.expire(key, 60, nx=True)` | **Rate limit**: is minute ki ginti +1 (atomic), key 60s baad mite | `infra/cache/ratelimit.py::allow` |
| `r.xadd(stream, {"event": ..., "data": ...}, maxlen=1000, approximate=True)` | **Stream** mein entry jodo (id khud: `1793086122728-0` = ms timestamp-sequence), ~1000 tak rakho | `infra/cache/streams.py::append` |
| `r.expire(stream, 3600)` | Poora stream 1 ghante baad mite | `streams.py::append` |
| `r.xread({stream: after_id}, count=100, block=15000)` | `after_id` ke baad wali entries; kuch na ho to 15s intezar (`"0"` = shuru se) | `streams.py::read_after` |
| `sse(event, data, event_id=entry_id)` → `id: ...` | SSE event ke saath id — browser reconnect par `Last-Event-ID` bhejta hai | `core/sse.py` |
| `": keep-alive\n\n"` / `"retry: 3000\n\n"` | Heartbeat (proxy connection na kaate) / browser 3s baad reconnect kare | `core/sse.py` |
| (purana) `r.publish` / `r.pubsub()` | Pub/Sub: history nahi — Lesson 11B mein use hua, phir Streams se badla | — |
| `RedisSaver(redis_url=..., ttl={"default_ttl": 1440, "refresh_on_read": True})` + `.setup()` | LangGraph yaadasht Redis mein, 24 ghante (minutes mein) baad mite, parhne par TTL dobara | `agents/core/checkpointers.py::get_redis_checkpointer` |

---

## 6. Management command (alag process ka dhaancha)

```python
class Command(BaseCommand):          # python manage.py <file ka naam>
    help = "..."                     # --help mein dikhta hai
    def handle(self, *args, **options):
        self.stdout.write("started")  # terminal mein likhna
        try:
            while True:               # hamesha chalte raho
                ...
        except KeyboardInterrupt:     # Ctrl+C par saaf band
            ...
```

## 6B. Kafka start → end, ek table (file:line ke saath, asli data)

Asli message (test ka ticket `e8bd04a3...`):
```
topic : tickets.created
key   : e8bd04a3-0f12-4ba0-8b01-4c7942062053        → partition 1
value : {"event_id": "5a1eb6b0bd5c...", "event_version": 1, "tenant_public_id": "ac5b565b-...",
         "occurred_at": "2026-10-26T...Z", "event_type": "tickets.created", "ticket_public_id": "e8bd04a3-..."}
         (tenant_public_id = core_tenant.public_id, ticket_public_id = tickets_ticket.public_id)
```

| # | Kahan (file:line) | Code | Kya hota hai |
|---|---|---|---|
| 1 | `apps/tickets/api.py:17` | `def create_ticket(request, payload)` | **START.** Client ne ticket bheja |
| 2 | `apps/tickets/services/tickets.py:16` | `with transaction.atomic():` | Ab jo hoga, ek saath save hoga ya bilkul nahi |
| 3 | `services/tickets.py:17` | `Ticket.objects.create(...)` | `tickets_ticket` mein row, `status=open` |
| 4 | `services/tickets.py:18` → `infra/eventbus/outbox.py:8` | `publish_event(...)` → `OutboxEvent.objects.create(topic, key, payload)` | `eventbus_outboxevent` mein row, `published_at = NULL` (Kafka ko abhi kuch nahi gaya) |
| 5 | `apps/tickets/api.py:21` | `return 202, ticket` | Client ko foran jawab: `status: open` |
| 6 | `infra/eventbus/kafka.py:10` | `Producer({"bootstrap.servers", "enable.idempotence": True, "acks": "all"})` | Relay ka Kafka client: kahan hai Kafka, retry se duplicate nahi, saare copies save hon tab "ho gaya" |
| 7 | `run_outbox_relay.py:23` | `while True: relay_batch()` | **Relay process ka START** — har second dekhta hai |
| 8 | `run_outbox_relay.py:35-39` | `select_for_update(skip_locked=True).filter(published_at__isnull=True)` | Outbox se unbheje events (max 100) uthao |
| 9 | `run_outbox_relay.py:45-50` | `producer.produce(topic, key=, value=, on_delivery=)` | Message ko producer ki **andar ki line** mein daalo (abhi network par nahi gaya) |
| 10 | `run_outbox_relay.py:51` | `producer.flush(15)` | Ab asal mein Kafka bhejo, 15s tak tasdeeq ka intezar; har message par `on_delivery` chalta hai |
| 11 | `run_outbox_relay.py:53-54` | `.update(published_at=timezone.now())` | Sirf tasdeeq wale rows par mohar — **relay ka kaam khatam** |
| 12 | `infra/eventbus/kafka.py:14-19` | `Consumer({"group.id", "enable.auto.commit": False, "auto.offset.reset": "earliest"})` | Worker ka Kafka client: kaun si team, offset hum khud commit karenge, pehli dafa shuru se |
| 13 | `run_agent_worker.py:24` | `consumer.subscribe([TICKETS_CREATED])` | **Worker process ka START** — is topic ko suno |
| 14 | `run_agent_worker.py:28` | `msg = consumer.poll(1.0)` | 1s tak naye message ka intezar; na aaye to `None` |
| 15 | `run_agent_worker.py:31` | `if msg.error():` | Kafka ki taraf ki ghalti → log, aage |
| 16 | `run_agent_worker.py:44` | `TicketCreatedV1.model_validate_json(msg.value())` | Bytes → pakka event object (ghalat → DLQ) |
| 17 | `run_agent_worker.py:49` | `idempotency.is_done(event.event_id)` | Redis: ye event pehle ho chuka? haan → skip |
| 18 | `workers/handlers/tickets.py:28` | `get_ticket_for_event(tenant, ticket)` | DB se ticket (na mile → DLQ) |
| 19 | `handlers/tickets.py:31` | `if ticket.status != OPEN` | Doosra pehredaar: pehle se answered → skip |
| 20 | `handlers/tickets.py:37` | `get_graph().invoke(...)` | **AI agent** jawab banata hai |
| 21 | `handlers/tickets.py:40` | `services.mark_ticket_answered(...)` | Ticket `answered` + naya event `tickets.answered` outbox mein (phir #7 se dobara) |
| 22 | `run_agent_worker.py:72` | `idempotency.mark_done(event.event_id)` | Redis mein likho: ho gaya (7 din) |
| 23 | `run_agent_worker.py:35` | `consumer.commit(message=msg, asynchronous=False)` | Kafka ko batao: is offset tak kaam poora — **Kafka flow ka END** |
| 24 | `apps/tickets/api.py` `get_ticket` | `GET /api/tickets/{id}` | Client ko `status: answered` + `reply` |

## 6C. Teen dhaanche (har project mein yahi shakal)

**Agent (LangGraph):**
```python
builder = StateGraph(MessagesState, context_schema=MyContext)
builder.add_node("agent", agent_node)                      # node = function(state, runtime) -> {"messages": [...]}
builder.add_node("tools", ToolNode(TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)    # tool call? -> "tools" : END
builder.add_edge("tools", "agent")                         # ReAct loop
graph = builder.compile(checkpointer=saver)
config = {"configurable": {"thread_id": "tenant:customer:conversation"}}
result = graph.invoke({"messages": [HumanMessage(text)]}, config, context=MyContext(...))
for mode, data in graph.stream(input, config, context=ctx, stream_mode=["messages", "updates"]): ...
```

**Kafka:**
```python
producer = Producer({"bootstrap.servers": ..., "enable.idempotence": True, "acks": "all"})
producer.produce(topic, key=entity_public_id, value=json.dumps(payload).encode(), on_delivery=cb)
producer.flush(15)
consumer = Consumer({"bootstrap.servers": ..., "group.id": "team", "enable.auto.commit": False, "auto.offset.reset": "earliest"})
consumer.subscribe([topic])
msg = consumer.poll(1.0)                                   # None = kuch nahi aaya
event = MyEventV1.model_validate_json(msg.value())
consumer.commit(message=msg, asynchronous=False)           # kaam ke BAAD
consumer.close()
```

**Worker (management command):**
```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        consumer = make_consumer("team"); consumer.subscribe([TOPIC])
        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None or msg.error(): continue
                event = MyEventV1.model_validate_json(msg.value())
                if not idempotency.is_done(event.event_id):
                    for attempt in range(1, MAX_ATTEMPTS + 1):
                        try: handle(event); break
                        except PermanentEventError: to_dlq(msg); break
                        except Exception: time.sleep(2 ** attempt)   # last attempt -> DLQ
                    idempotency.mark_done(event.event_id)
                consumer.commit(message=msg, asynchronous=False)
        except KeyboardInterrupt: pass
        finally: consumer.close()
```

**Outbox (data + event ek saath):**
```python
with transaction.atomic():
    obj = Model.objects.create(...)
    publish_event(topic=TOPIC, key=str(obj.public_id), event=MyEventV1(tenant_public_id=..., <model>_public_id=...))
```

## 7. Worker ka poora dil (8 lines yaad rakho)

```python
consumer.subscribe([TICKETS_CREATED])
while True:
    msg = consumer.poll(1.0)                                # khat aaya?
    if msg is None: continue
    event = TicketCreatedV1.model_validate_json(msg.value()) # khat kholo
    if not idempotency.is_done(event.event_id):             # pehle nahi hua?
        handle_ticket_created(event)                        # kaam (agent)
        idempotency.mark_done(event.event_id)               # yaad rakho
    consumer.commit(message=msg)                            # sign: ho gaya
```
