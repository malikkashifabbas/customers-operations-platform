from django.contrib import admin

from .models import StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "tenant", "created_at"]
    list_filter = ["tenant"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
