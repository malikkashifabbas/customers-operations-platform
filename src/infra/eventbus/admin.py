from django.contrib import admin

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "key", "created_at", "published_at"]
    # "published at: Empty" = events still waiting for the relay; a growing list means the relay is down.
    list_filter = ["topic", ("published_at", admin.EmptyFieldListFilter)]
    readonly_fields = ["topic", "key", "payload", "created_at", "published_at"]

    def has_add_permission(self, request):
        return False  # a hand-made row would be published to Kafka as if a real change had happened
