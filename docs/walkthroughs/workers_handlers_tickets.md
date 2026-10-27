# Walkthrough: `src/workers/handlers/tickets.py`

## Senior ko kisi bhi file ka 5-step jawab
1. **Ek line:** file kya karti hai.
2. **Kaun bulata hai** (caller) — kahan se is file ke functions chalte hain.
3. **Ye kis ko bulati hai** (imports) — group mein, har group ka "kyun".
4. **Main function qadam ba qadam.**
5. **Design ke faisle ("kyun aisa?")** + edge cases.

---

## 1. Ek line
Worker ka **asal kaam**: Kafka se `tickets.created` event aaye to ticket DB se uthao, AI support agent se jawab banwao, aur ticket ko `answered` kar do.

## 2. Kaun bulata hai
`src/workers/management/commands/run_agent_worker.py`:
- line 56: `handle_ticket_created(event)` — har naye event par.
- line 67: `mark_failed(event)` — 3 koshishein fail hon to.
- line 61: `except PermanentEventError` — is file ki exception pakad kar DLQ.

**Kyun alag file?** `run_agent_worker.py` = mashinri (Kafka loop, retry, DLQ, commit). `handlers/tickets.py` = kaam (ticket + agent). Kal email worker aaye to mashinri wahi, sirf naya handler.

## 3. Imports — 4 group
| Group | Import | Kyun |
|---|---|---|
| Python | `logging` | Logger (abhi is file mein istemal nahi — ya error log ke liye use karein ya hata dein) |
| Python | `functools.lru_cache` | Graph ek hi dafa bane (neeche) |
| LangChain | `AIMessage`, `HumanMessage` | Ticket ka text agent ko `HumanMessage` mein; jawab `AIMessage` mein dhoondna |
| Agents (AI) | `get_pool_checkpointer` | Postgres yaadasht, connection pool ke saath (Lesson 10) |
| Agents (AI) | `SupportContext` | Pehchaan ki parchi: kaun si company, kaun sa customer (Lesson 9) |
| Agents (AI) | `build_graph` | Support agent ka graph (Lesson 9) |
| Apps (business) | `selectors` | Ticket **parhna** — `get_ticket_for_event` |
| Apps (business) | `services` | Ticket **likhna** — `mark_ticket_answered`, `mark_ticket_failed` |
| Apps (business) | `TicketStatus` | `OPEN` se muqabla |
| Infra | `TicketCreatedV1` | Event ki pakki shakal (type hint) |

**Ek line mein:** ye file **AI (agents)** aur **business (apps)** ko jorti hai — isliye `workers/` mein hai (qaida: `apps/` kabhi `agents/` import nahi karte).

## 4. Line by line

```python
logger = logging.getLogger(__name__)
```
`__name__` = `"workers.handlers.tickets"` — logs mein pata chale message kis file se aaya.

```python
class PermanentEventError(Exception):
    """Retrying will never help (e.g. the ticket does not exist): send the event straight to the DLQ."""
```
Apni **exception class**. Do qisam ki ghalti: **transient** (LLM rate limit — dobara koshish karo) aur **permanent** (ticket hi nahi — 100 dafa bhi nahi milega). Worker isay alag pakad kar **bina retry** DLQ bhejta hai. Body mein sirf docstring kaafi hai.

```python
@lru_cache(maxsize=1)
def get_graph():
    return build_graph(checkpointer=get_pool_checkpointer())
```
`lru_cache` = function ka nateeja **yaad rakho**. Pehli call graph banati hai (graph compile + Postgres pool), baad ki har call **wahi** graph lautati hai. Har ticket par naya graph + naye connections bohat mehenga hota. `maxsize=1` = ek hi cheez yaad rakhni hai.

```python
def handle_ticket_created(event: TicketCreatedV1) -> str:
```
Event leta hai, ek **text** lautata hai (worker log mein chhapta hai: `answered (196 chars)`).

```python
    ticket = selectors.get_ticket_for_event(
        tenant_public_id=event.tenant_public_id, ticket_public_id=event.ticket_public_id
    )
```
Ticket DB se — **dono IDs** se. Sirf ticket ID se dhoondte to jaali event doosri company ka ticket utha sakta tha. Seedha `Ticket.objects` nahi, **selector** (parhne ka qaida ek jagah).

```python
    if ticket is None:
        raise PermanentEventError(f"ticket {event.ticket_public_id} not found for tenant {event.tenant_public_id}")
```
Ticket nahi mila → permanent ghalti → worker DLQ bhejta hai, wajah ke saath.

```python
    if ticket.status != TicketStatus.OPEN:
        return f"skipped: ticket already {ticket.status}"
```
**Doosra idempotency pehredaar.** Redis 7 din baad bhool jata hai; status hamesha DB mein hai. Ticket pehle se answered/failed → dobara agent nahi (LLM ka kharcha + do jawab nahi).

```python
    config = {"configurable": {"thread_id": f"{ticket.tenant.public_id}:{ticket.customer.public_id}:ticket-{ticket.public_id}"}}
```
Yaadasht ki **chaabi** (Lesson 8/10): `company:customer:ticket-<id>`. Har ticket ki apni baat-cheet; company/customer andar hain → kisi aur ka thread kabhi nahi khulta.

```python
    context = SupportContext(tenant=ticket.tenant, customer=ticket.customer)
```
Pehchaan ki parchi — tools isi se data lete hain, LLM ko nazar nahi aati. Customer **ticket se** aata hai (system), LLM se nahi.

```python
    question = f"Support ticket subject: {ticket.subject}\n\n{ticket.body}"
```
Agent ko sawal: subject + khali line (`\n\n`) + body.

```python
    result = get_graph().invoke({"messages": [HumanMessage(question)]}, config, context=context)
```
**Agent chalao** (Lesson 7–9): input = customer ka message, config = yaadasht, context = pehchaan. `result["messages"]` = poori baat-cheet: Human → AI (tool call) → Tool → AI (jawab).

```python
    reply = next((m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content), "")
```
Aakhri **asli jawab** nikalna. Tukde:
- `reversed(...)` — aakhir se shuru (jawab aakhir mein hota hai).
- `isinstance(m, AIMessage)` — sirf AI ke messages.
- `and m.content` — tool-call wale AI messages ka content khali hota hai, unhein chhoro.
- `next(..., "")` — pehla mila hua lo; kuch na mile to `""`.

```python
    services.mark_ticket_answered(ticket=ticket, reply=reply)
```
Save — **service** ke zariye (likhne ka qaida ek jagah): ticket `answered` + `tickets.answered` event outbox mein, **ek transaction**.

```python
    return f"answered ({len(reply)} chars)"
```
Worker log ke liye.

```python
def mark_failed(event: TicketCreatedV1) -> None:
    ticket = selectors.get_ticket_for_event(...)
    if ticket is not None and ticket.status == TicketStatus.OPEN:
        services.mark_ticket_failed(ticket=ticket)
```
3 koshishein fail → ticket `failed` (customer ko `open` mein latka na rahe). Sirf `OPEN` ko — pehle se answered ko failed nahi karna.

## 5. Senior ke mumkin sawal
| Sawal | Jawab |
|---|---|
| `lru_cache` kyun? | Graph aur DB pool har ticket par banana mehenga; process mein ek dafa banta hai |
| `PermanentEventError` alag kyun? | Na milne wala ticket retry se nahi milega — seedha DLQ, line nahi rukti |
| Redis hai to status check kyun? | Do pehredaar: Redis TTL ke baad bhool jata hai, DB status hamesha rehta hai |
| Ticket dono IDs se kyun? | Jaali/ghalat event doosri company ke ticket tak na pahunche |
| Seedha ORM kyun nahi? | Parhna `selectors`, likhna `services` — qaida aur tenant filter ek jagah |
| Ye `apps/tickets` mein kyun nahi? | `apps/` AI ko import nahi karte; workers AI + business ko jorte hain |
| Agent beech mein fail ho to? | Exception worker tak jati hai → 2s, 4s retry → 3 dafa → `mark_failed` + DLQ; offset tab hi commit |
| `thread_id` mein ticket kyun? | Har ticket ki alag yaadasht; follow-up isi ticket mein jur sakta hai |
