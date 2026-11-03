"""Audit trail: every change the agent makes or the customer cancels, so "who asked for this?" always has an answer."""

from django.db import models

from core.models import TenantScopedModel


class AgentActionStatus(models.TextChoices):
    CONFIRMED = "confirmed", "Confirmed by customer"
    CANCELLED = "cancelled", "Cancelled by customer"
    BLOCKED = "blocked", "Blocked by a limit"


class AgentAction(TenantScopedModel):
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="agent_actions")
    action = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=AgentActionStatus.choices)
    details = models.JSONField(default=dict)
    thread_id = models.CharField(max_length=200, blank=True)
    tool_call_id = models.CharField(max_length=100, blank=True)
    target_public_id = models.UUIDField(null=True, blank=True)

    class Meta:
        constraints = [
            # A tool can run twice for one call (interrupt resume, crash replay); the second run must not act again.
            models.UniqueConstraint(fields=["thread_id", "tool_call_id"], condition=~models.Q(tool_call_id=""), name="agent_action_once_per_tool_call"),
        ]
        indexes = [
            models.Index(fields=["tenant", "customer", "-created_at"], name="agent_action_customer_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} ({self.status})"
