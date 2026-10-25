from django.contrib import admin

from core.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["public_id", "created_at", "updated_at"]
