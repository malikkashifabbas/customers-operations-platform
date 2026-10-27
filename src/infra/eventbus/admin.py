from django.contrib import admin

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "key", "created_at", "published_at"]
    list_filter = ["topic"]
    readonly_fields = ["topic", "key", "payload", "created_at", "published_at"]
