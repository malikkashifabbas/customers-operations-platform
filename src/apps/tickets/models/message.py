"""One message in a ticket's conversation: the customer's questions and the assistant's answers, in order."""

from django.db import models

from core.models import TenantScopedModel


class MessageAuthor(models.TextChoices):
    CUSTOMER = "customer", "Customer"
    ASSISTANT = "assistant", "Assistant"


class TicketMessage(TenantScopedModel):
    ticket = models.ForeignKey("tickets.Ticket", on_delete=models.CASCADE, related_name="messages")
    author = models.CharField(max_length=16, choices=MessageAuthor.choices)
    body = models.TextField()
    # Set on a customer message once the agent has answered it, so a re-delivered Kafka event never answers twice.
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["ticket", "created_at"], name="ticket_messages_order_idx")]

    def __str__(self) -> str:
        return f"{self.author}: {self.body[:40]}"
