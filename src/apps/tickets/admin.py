from django.contrib import admin, messages

from core.exceptions import DomainError

from . import services
from .models import Ticket, TicketStatus


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "customer", "status", "tenant", "created_at", "answered_at"]
    list_filter = ["tenant", "status"]
    search_fields = ["subject", "body", "customer__full_name"]
    # Status, reply and approval fields are written by the worker and services (with outbox events), never a plain Save.
    readonly_fields = [
        "public_id", "status", "reply", "approval_request", "approval_decision", "created_at", "updated_at", "answered_at",
    ]
    list_select_related = ["customer", "tenant"]
    actions = ["approve_refund", "reject_refund"]

    def has_add_permission(self, request):
        return False  # a ticket saved here would get no tickets.created event, so no agent would ever answer it

    def _decide(self, request, queryset, *, approved: bool):
        done = 0
        for ticket in queryset.select_related("tenant"):
            if ticket.status != TicketStatus.WAITING_APPROVAL:
                self.message_user(request, f"{ticket.subject}: not waiting for approval ({ticket.status}).", messages.WARNING)
                continue
            try:
                # Same service as the staff API: decision + tickets.approval_decided event in one transaction.
                services.decide_approval(
                    ticket=ticket, approved=approved, note="Decided in Django admin.", reviewer=request.user.get_username()
                )
                done += 1
            except DomainError as exc:
                self.message_user(request, f"{ticket.subject}: {exc.message}", messages.WARNING)
        if done:
            verb = "Approved" if approved else "Rejected"
            self.message_user(request, f"{verb} {done} ticket(s); the agent worker resumes them via Kafka.", messages.SUCCESS)

    @admin.action(description="Approve refund (resumes the agent)")
    def approve_refund(self, request, queryset):
        self._decide(request, queryset, approved=True)

    @admin.action(description="Reject refund (resumes the agent)")
    def reject_refund(self, request, queryset):
        self._decide(request, queryset, approved=False)
