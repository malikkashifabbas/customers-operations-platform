"""Relay: read unpublished outbox rows, send them to Kafka, mark them published only after Kafka confirms."""

import json
import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from infra.eventbus.kafka import make_producer
from infra.eventbus.models import OutboxEvent

BATCH_SIZE = 100


class Command(BaseCommand):
    help = "Publish outbox events to Kafka (run as its own process)."

    def handle(self, *args, **options):
        producer = make_producer()
        self.stdout.write("outbox relay started (Ctrl+C to stop)")
        try:
            while True:
                sent = self.relay_batch(producer)
                if sent:
                    self.stdout.write(self.style.SUCCESS(f"published {sent} event(s)"))
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("outbox relay stopped")

    def relay_batch(self, producer) -> int:
        with transaction.atomic():
            # skip_locked lets several relays run at once without sending the same row twice.
            batch = list(
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(published_at__isnull=True)
                .order_by("id")[:BATCH_SIZE]
            )
            if not batch:
                return 0

            failed: set[int] = set()
            for row in batch:
                producer.produce(
                    row.topic,
                    key=row.key,
                    value=json.dumps(row.payload).encode(),
                    on_delivery=lambda err, msg, row_id=row.id: failed.add(row_id) if err else None,
                )
            producer.flush(15)

            delivered = [row.id for row in batch if row.id not in failed]
            OutboxEvent.objects.filter(id__in=delivered).update(published_at=timezone.now())
            for row_id in failed:
                self.stderr.write(f"kafka did not confirm outbox row {row_id}; it will be retried")
            for row in batch:
                if row.id in delivered:
                    self.stdout.write(f"  -> {row.topic} key={row.key}")
            return len(delivered)
