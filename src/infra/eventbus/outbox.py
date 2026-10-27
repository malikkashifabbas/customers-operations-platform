"""publish_event() writes to the outbox table; call it inside the same transaction as the data change."""

from .events import Event
from .models import OutboxEvent


def publish_event(*, topic: str, key: str, event: Event) -> OutboxEvent:
    return OutboxEvent.objects.create(topic=topic, key=key, payload=event.model_dump(mode="json"))
