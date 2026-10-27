"""Request and response shapes for the tickets API."""

from ninja import Field, ModelSchema, Schema

from .models import Ticket


class TicketIn(Schema):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class TicketOut(ModelSchema):
    class Meta:
        model = Ticket
        fields = ["public_id", "subject", "body", "status", "reply", "created_at", "answered_at"]
