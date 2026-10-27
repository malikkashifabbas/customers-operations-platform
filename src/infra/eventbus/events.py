"""Versioned event shapes. Events carry public ids (named <model>_public_id), not full records: consumers read fresh data."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from .topics import TICKETS_ANSWERED, TICKETS_CREATED


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_version: int = 1
    tenant_public_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TicketCreatedV1(Event):
    event_type: Literal["tickets.created"] = TICKETS_CREATED
    ticket_public_id: str


class TicketAnsweredV1(Event):
    event_type: Literal["tickets.answered"] = TICKETS_ANSWERED
    ticket_public_id: str
