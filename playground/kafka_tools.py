"""Lesson 11 test helpers that talk to Kafka directly (bypassing the outbox on purpose).

    uv run python playground/kafka_tools.py replay-last     re-send the newest tickets.created event (duplicate test)
    uv run python playground/kafka_tools.py bogus-event     send an event for a ticket that does not exist (DLQ test)
"""

import json
import sys
import uuid

import django_setup  # noqa: F401  (must run before any Django model import)

from core.models import Tenant
from infra.eventbus.events import TicketCreatedV1
from infra.eventbus.kafka import make_producer
from infra.eventbus.models import OutboxEvent
from infra.eventbus.topics import TICKETS_CREATED


def send(key: str, payload: dict) -> None:
    producer = make_producer()
    producer.produce(TICKETS_CREATED, key=key, value=json.dumps(payload).encode())
    producer.flush(10)
    print(f"sent to {TICKETS_CREATED}: key={key} event_id={payload['event_id']}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "replay-last":
        row = OutboxEvent.objects.filter(topic=TICKETS_CREATED).order_by("-id").first()
        send(row.key, row.payload)
    elif command == "bogus-event":
        tenant = Tenant.objects.get(slug="demo-company")
        event = TicketCreatedV1(tenant_public_id=str(tenant.public_id), ticket_public_id=str(uuid.uuid4()))
        send(event.ticket_public_id, event.model_dump(mode="json"))
    else:
        print(__doc__)
