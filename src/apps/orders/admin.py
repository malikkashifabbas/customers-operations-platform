from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "customer", "amount", "currency", "status", "tenant", "created_at"]
    list_filter = ["tenant", "status"]
    search_fields = ["order_number", "customer__full_name", "customer__phone"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
    list_select_related = ["customer", "tenant"]
