from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "email", "tenant", "created_at"]
    list_filter = ["tenant"]
    search_fields = ["full_name", "phone", "email"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
