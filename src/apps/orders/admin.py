from django.contrib import admin, messages

from core.exceptions import DomainError

from . import services
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "customer", "amount", "currency", "status", "tenant", "created_at"]
    list_filter = ["tenant", "status"]
    search_fields = ["order_number", "customer__full_name", "customer__phone"]
    # Status changes only through services (refund_order locks the row and checks it is paid), never a plain Save.
    readonly_fields = ["public_id", "status", "paid_at", "created_at", "updated_at"]
    list_select_related = ["customer", "tenant"]
    actions = ["refund_selected"]

    def has_add_permission(self, request):
        return False  # orders come from checkout or seed_data, where create_order checks customer and tenant match

    @admin.action(description="Refund selected paid orders (staff decision, uses refund_order)")
    def refund_selected(self, request, queryset):
        done = 0
        for order in queryset:
            try:
                services.refund_order(order=order)
                done += 1
            except DomainError as exc:
                self.message_user(request, f"{order.order_number}: {exc.message}", messages.WARNING)
        if done:
            self.message_user(request, f"Refunded {done} order(s).", messages.SUCCESS)
