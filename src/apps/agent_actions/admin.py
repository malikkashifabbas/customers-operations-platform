from django.contrib import admin

from .models import AgentAction


@admin.register(AgentAction)
class AgentActionAdmin(admin.ModelAdmin):
    list_display = ["action", "status", "customer", "tenant", "created_at"]
    list_filter = ["tenant", "action", "status"]
    list_select_related = ["customer", "tenant"]

    # An audit trail that can be edited proves nothing, so this page only reads.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
