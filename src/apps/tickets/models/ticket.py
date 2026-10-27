"""A support ticket from one customer; the agent worker answers it asynchronously."""

from django.db import models

from core.models import TenantScopedModel


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    WAITING_APPROVAL = "waiting_approval", "Waiting for staff approval"
    ANSWERED = "answered", "Answered"
    FAILED = "failed", "Failed"


class Ticket(TenantScopedModel):
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="tickets")
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=16, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    reply = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    # What the agent asked staff to approve (from interrupt()), and what staff decided; the decision resumes the graph.
    approval_request = models.JSONField(null=True, blank=True)
    approval_decision = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "customer", "-created_at"], name="tickets_customer_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.subject} ({self.status})"
