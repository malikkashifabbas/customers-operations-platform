"""Who the agent is talking to: set by the system for every run, never chosen by the LLM."""

from dataclasses import dataclass
from typing import Literal

from apps.customers.models import Customer
from core.models import Tenant


@dataclass(frozen=True)
class SupportContext:
    tenant: Tenant
    customer: Customer
    # "ticket" runs can pause for staff approval (async); "chat" must answer now, so it never gets approval tools.
    channel: Literal["chat", "ticket"] = "chat"
