from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "customer", "status", "tenant", "created_at", "answered_at"]
    list_filter = ["tenant", "status"]
    search_fields = ["subject", "body", "customer__full_name"]
    readonly_fields = ["public_id", "created_at", "updated_at", "answered_at"]
    list_select_related = ["customer", "tenant"]
