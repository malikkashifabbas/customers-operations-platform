# Walkthrough: `src/infra/eventbus/` (Kafka wala hissa)

## Ek line
`infra/eventbus/` = Kafka se baat karne ke **auzaar**: topic ke naam, event ki shakal, outbox table, aur Kafka clients. Ye khud kuch "chalata" nahi — relay aur worker in auzaaron ko use karte hain.

## Files, flow ki tarteeb mein
| # | File | Ek line | Kaun use karta hai |
|---|---|---|---|
| 1 | `topics.py` | **Saare topic names** + har topic ke partitions | events.py, relay/worker, `create_topics` |
| 2 | `events.py` | **Event ki shakal** — message ke andar kaun se fields (Pydantic) | services (event banana), worker (event parhna) |
| 3 | `models.py` | **`OutboxEvent` table** — "Kafka par bhejna hai" wali tokri | outbox.py, relay |
| 4 | `outbox.py` | `publish_event()` — event ko **outbox table mein likhna** (Kafka ko nahi) | `apps/tickets/services` |
| 5 | `kafka.py` | **Kafka clients banane ki jagah** — `make_producer()` (bhejne wala), `make_consumer()` (sunne wala) | relay, worker, `kafka_tools` |
| — | `apps.py`, `admin.py`, `migrations/` | Django app card, admin mein outbox, table ki migration | Django |

Kafka ka **start** relay (`run_outbox_relay.py`) aur worker (`run_agent_worker.py`) ke `while True` loops hain; `kafka.py` sirf un ke liye clients banata hai.

## `topics.py`
```python
TICKETS_CREATED = "tickets.created"          # naya ticket bana
TICKETS_ANSWERED = "tickets.answered"        # ticket ka jawab ban gaya
TICKETS_CREATED_DLQ = "tickets.created.dlq"  # jo tickets.created event process na ho sake
TOPICS = {TICKETS_CREATED: 3, TICKETS_ANSWERED: 3, TICKETS_CREATED_DLQ: 1}   # naam → partitions
```
Har jagah `TICKETS_CREATED` likhte hain, `"tickets.created"` nahi → spelling ki galti naamumkin. `TOPICS` se `create_topics` command topics banata hai (Kafka auto-create band hai).

## `events.py`
```python
class Event(BaseModel):                       # har event ki mushtarka bunyaad
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)   # har event ki apni ID (idempotency ke liye)
    event_version: int = 1                    # shakal badle to version badle
    tenant_public_id: str                     # kaun si company (core_tenant.public_id)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))   # kab hua (UTC)

class TicketCreatedV1(Event):
    event_type: Literal["tickets.created"] = TICKETS_CREATED   # topic ka naam event ke andar bhi
    ticket_public_id: str                     # kaun sa ticket (tickets_ticket.public_id)
```
- Kaam: message ke andar **kya likha jayega** — sirf IDs, poora ticket nahi (worker DB se taaza data parhta hai).
- `default_factory` = har naye event par nayi value **khud** banao (event_id, waqt).
- `TicketCreatedV1(Event)` = `Event` ke saare fields wirasat mein + apne.
- `topics.py` se sirf naam leta hai taa ke `event_type` aur topic hamesha same rahein.
- Do jagah use: **banate** waqt (`services`: `TicketCreatedV1(tenant_public_id=..., ticket_public_id=...)`) aur **parhte** waqt (worker: `TicketCreatedV1.model_validate_json(msg.value())` — ghalat shakal → DLQ).

## `models.py`
```python
class OutboxEvent(models.Model):
    topic = CharField(...)          # kis topic mein jana hai
    key = CharField(...)            # partition key (ticket public_id)
    payload = JSONField()           # event ka JSON
    created_at = DateTimeField(auto_now_add=True)
    published_at = DateTimeField(null=True)   # NULL = abhi Kafka nahi gaya; waqt = bhej diya
    # partial index sirf published_at IS NULL rows par — relay sirf wahi dhoondta hai
```

## `outbox.py` — line by line
```python
from .events import Event          # type: koi bhi event (TicketCreatedV1, TicketAnsweredV1...)
from .models import OutboxEvent    # outbox table

def publish_event(*, topic: str, key: str, event: Event) -> OutboxEvent:
    return OutboxEvent.objects.create(topic=topic, key=key, payload=event.model_dump(mode="json"))
```
| Hissa | Matlab |
|---|---|
| `*` | Har argument **naam ke saath** dena lazmi (`topic=..., key=..., event=...`) |
| `topic: str` | Kis topic mein jana hai (`TICKETS_CREATED`) |
| `key: str` | Partition key — ticket ka `public_id` |
| `event: Event` | Event object |
| `event.model_dump(mode="json")` | Event → dict, JSON ke qabil (`datetime` → `"2026-10-27T06:06:36Z"` text) |
| `OutboxEvent.objects.create(...)` | `eventbus_outboxevent` table mein **ek row** (`published_at = NULL`) |
| `-> OutboxEvent` | Bani hui row wapas |

⚠️ Ye **koi response nahi deta** aur **Kafka ko nahi chhuta** — sirf DB row likhta hai. Isay hamesha caller ke `with transaction.atomic():` ke **andar** bulaya jata hai (`apps/tickets/services/tickets.py`), taa ke ticket aur event ek saath save hon ya dono nahi. Kafka tak relay le jata hai. ("publish" = "bhejne ke liye darj karo".)

## `kafka.py`
```python
def make_producer() -> Producer:      # BHEJNE wala client (relay, DLQ, kafka_tools)
    return Producer({"bootstrap.servers": ..., "enable.idempotence": True, "acks": "all"})

def make_consumer(group_id) -> Consumer:   # SUNNE wala client (worker)
    return Consumer({"bootstrap.servers": ..., "group.id": group_id,
                     "enable.auto.commit": False, "auto.offset.reset": "earliest"})
```
Kaam: Kafka clients **ek jagah** se, ek jaisi settings ke saath. Settings ka matlab: `docs/cheatsheet.md` §2 aur §6B.

## Senior ke sawal
| Sawal | Jawab |
|---|---|
| Topic names alag file mein kyun? | Ek jagah, spelling galti naamumkin, `create_topics` isi list se banata hai |
| Event mein poora ticket kyun nahi? | Chhota message, aur worker hamesha DB ka taaza data parhta hai |
| `event_version` kyun? | Shakal badle to purane/naye consumers dono sambhal sakein |
| `publish_event` Kafka ko seedha kyun nahi bhejta? | Outbox pattern: DB aur Kafka kabhi alag nahi hon; Kafka band ho to event intezar kare |
| `kafka.py` kyun? | Clients ki settings (idempotence, manual commit) ek jagah — har jagah alag likhne se galti |
