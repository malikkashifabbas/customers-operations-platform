"""Request and response shapes for the tickets API."""

from ninja import Field, ModelSchema, Schema

from .models import Ticket


class TicketIn(Schema):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class TicketOut(ModelSchema):
    class Meta:
        model = Ticket
        fields = ["public_id", "subject", "body", "status", "reply", "approval_request", "created_at", "answered_at"]


class StaffTicketOut(ModelSchema):
    customer_name: str = Field(alias="customer.full_name")

    class Meta:
        model = Ticket
        fields = ["public_id", "subject", "body", "status", "approval_request", "approval_decision", "created_at"]


class ApprovalIn(Schema):
    approved: bool
    reviewer: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=500)
