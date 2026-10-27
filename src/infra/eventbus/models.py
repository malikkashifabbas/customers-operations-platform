"""Outbox: events are written in the same DB transaction as the data, then a relay publishes them to Kafka."""

from django.db import models


class OutboxEvent(models.Model):
    topic = models.CharField(max_length=200)
    key = models.CharField(max_length=200)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            # The relay only ever looks for unpublished rows, so index just those.
            models.Index(fields=["id"], name="outbox_unpublished_idx", condition=models.Q(published_at__isnull=True)),
        ]

    def __str__(self) -> str:
        return f"{self.topic} {self.key} ({'published' if self.published_at else 'pending'})"
