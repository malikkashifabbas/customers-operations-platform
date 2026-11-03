"""Write-side rules for the audit trail."""

from uuid import UUID

from apps.customers.models import Customer
from core.models import Tenant

from .models import AgentAction, AgentActionStatus


def record_action(
    *,
    tenant: Tenant,
    customer: Customer,
    action: str,
    status: AgentActionStatus,
    details: dict,
    thread_id: str = "",
    tool_call_id: str = "",
    target_public_id: UUID | None = None,
) -> AgentAction:
    return AgentAction.objects.create(
        tenant=tenant,
        customer=customer,
        action=action,
        status=status,
        details=details,
        thread_id=thread_id,
        tool_call_id=tool_call_id,
        target_public_id=target_public_id,
    )
