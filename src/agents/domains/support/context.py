"""Who the agent is talking to: set by the system for every run, never chosen by the LLM."""

from dataclasses import dataclass

from apps.customers.models import Customer
from core.models import Tenant


@dataclass(frozen=True)
class SupportContext:
    tenant: Tenant
    customer: Customer
