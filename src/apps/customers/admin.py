from django.contrib import admin

from apps.orders.models import Order
from apps.tickets.models import Ticket

from .models import Customer


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OrderInline(ReadOnlyInline):
    model = Order
    fields = readonly_fields = ["order_number", "amount", "currency", "status", "created_at"]
    ordering = ["-created_at"]


class TicketInline(ReadOnlyInline):
    model = Ticket
    fields = readonly_fields = ["subject", "status", "created_at", "answered_at"]
    ordering = ["-created_at"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "email", "tenant", "created_at"]
    list_filter = ["tenant"]
    search_fields = ["full_name", "phone", "email"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
    inlines = [OrderInline, TicketInline]  # one page shows everything about a customer when a ticket comes in
