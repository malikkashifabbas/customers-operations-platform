"""Agent worker: consume ticket events (created, approval_decided), run the support agent, commit only when done."""

import time
from datetime import UTC, datetime

from django.core.management.base import BaseCommand
from pydantic import ValidationError

from infra.cache import idempotency
from infra.eventbus.events import TicketApprovalDecidedV1, TicketCreatedV1
from infra.eventbus.kafka import make_consumer, make_producer
from infra.eventbus.topics import (
    TICKETS_APPROVAL_DECIDED,
    TICKETS_APPROVAL_DECIDED_DLQ,
    TICKETS_CREATED,
    TICKETS_CREATED_DLQ,
)
from infra.observability.tracing import record_span, trace_span
from workers.handlers.tickets import PermanentEventError, handle_approval_decided, handle_ticket_created, mark_failed

GROUP_ID = "agent-workers"
MAX_ATTEMPTS = 3

# topic -> (event class, handler, dead-letter topic): one worker, one loop, many event types.
ROUTES = {
    TICKETS_CREATED: (TicketCreatedV1, handle_ticket_created, TICKETS_CREATED_DLQ),
    TICKETS_APPROVAL_DECIDED: (TicketApprovalDecidedV1, handle_approval_decided, TICKETS_APPROVAL_DECIDED_DLQ),
}


class Command(BaseCommand):
    help = "Answer new tickets from Kafka with the support agent (run as its own process; start more to scale)."

    def handle(self, *args, **options):
        consumer = make_consumer(GROUP_ID)
        dlq = make_producer()
        consumer.subscribe(list(ROUTES))
        self.stdout.write(f"agent worker started, group={GROUP_ID} (Ctrl+C to stop)")
        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    self.stderr.write(f"kafka error: {msg.error()}")
                    continue
                self.process(msg, dlq)
                consumer.commit(message=msg, asynchronous=False)
        except KeyboardInterrupt:
            self.stdout.write("agent worker stopping")
        finally:
            consumer.close()

    def process(self, msg, dlq) -> None:
        where = f"{msg.topic()} partition={msg.partition()} offset={msg.offset()}"
        event_class, handler, _ = ROUTES[msg.topic()]
        try:
            event = event_class.model_validate_json(msg.value())
        except ValidationError as exc:
            self.to_dlq(dlq, msg, f"bad payload: {exc.errors()[0]['msg']}")
            return

        if idempotency.is_done(event.event_id):
            self.stdout.write(f"[{where}] event {event.event_id[:8]} already processed -> skipping")
            return

        trace_headers = {key: value.decode(errors="replace") for key, value in msg.headers() or [] if value}
        _, sent_at_ms = msg.timestamp()
        if sent_at_ms > 0:  # Kafka reports -1 when a message has no timestamp
            record_span(
                "kafka wait", parent=trace_headers, start_time=datetime.fromtimestamp(sent_at_ms / 1000, UTC), metadata={"topic": msg.topic()}
            )

        for attempt in range(1, MAX_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                # One span per attempt, so a failed try stays visible in the trace next to the one that worked.
                with trace_span(
                    f"consume {msg.topic()}",
                    parent=trace_headers,
                    metadata={"attempt": attempt, "partition": msg.partition(), "offset": msg.offset(), "event_id": event.event_id},
                ):
                    outcome = handler(event)
                self.stdout.write(self.style.SUCCESS(
                    f"[{where}] ticket {event.ticket_public_id[:8]} {outcome} in {time.perf_counter() - started:.1f}s"
                ))
                break
            except PermanentEventError as exc:
                self.to_dlq(dlq, msg, str(exc))
                break
            except Exception as exc:  # transient (LLM rate limit, network): wait and try again
                self.stderr.write(f"[{where}] attempt {attempt}/{MAX_ATTEMPTS} failed: {type(exc).__name__}: {exc}")
                if attempt == MAX_ATTEMPTS:
                    mark_failed(event)
                    self.to_dlq(dlq, msg, f"failed {MAX_ATTEMPTS} times: {type(exc).__name__}")
                else:
                    time.sleep(2 ** attempt)

        idempotency.mark_done(event.event_id)

    def to_dlq(self, dlq, msg, reason: str) -> None:
        dlq_topic = ROUTES[msg.topic()][2]
        # Keep the trace headers: a dead event can then be followed back to the request that created it.
        dlq.produce(dlq_topic, key=msg.key(), value=msg.value(), headers={**dict(msg.headers() or []), "dlq_reason": reason})
        dlq.flush(10)
        self.stderr.write(self.style.WARNING(f"sent to {dlq_topic}: {reason}"))
