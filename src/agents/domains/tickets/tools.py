"""Tools that change data: the graph pauses (interrupt) and only the customer's confirmation through the API lets the change happen."""

import json

from django.db import transaction
from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from agents.domains.support.context import SupportContext
from apps.agent_actions.models import AgentAction, AgentActionStatus
from apps.agent_actions.services import record_action
from apps.tickets.services import create_ticket
from core.limits import AGENT_TICKETS_PER_HOUR
from infra.cache import ratelimit

MAX_SUBJECT = 200
MAX_BODY = 5000
ACTION = "create_ticket"


def _result(status: str, **extra) -> str:
    return json.dumps({"ticket_status": status, **extra})


def _earlier_result(action: AgentAction) -> str:
    if action.status == AgentActionStatus.CONFIRMED:
        return _result("created", ticket_public_id=str(action.target_public_id))
    return _result("cancelled" if action.status == AgentActionStatus.CANCELLED else "limit_reached")


@tool
def create_support_ticket(subject: str, details: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Open a support ticket for the current customer. The customer is asked to confirm first; nothing is created unless they do. Use it only when the customer clearly asks you to open a ticket and has said what the problem is."""
    context = runtime.context
    if context.channel != "chat":
        return "This conversation is already a support ticket, so no new ticket is needed."
    subject, details = subject.strip(), details.strip()
    if not subject or not details or len(subject) > MAX_SUBJECT or len(details) > MAX_BODY:
        return f"The subject (up to {MAX_SUBJECT} characters) and details (up to {MAX_BODY}) must both be filled in."

    # On resume this whole tool runs again from the top, so everything above must stay read-only.
    decision = interrupt({"type": "ticket_confirmation", "subject": subject, "body": details})

    thread_id = runtime.config.get("configurable", {}).get("thread_id", "")
    # Two tool calls in one reply share a node: answering the second runs the first again, and it must not create twice.
    earlier = AgentAction.objects.filter(thread_id=thread_id, tool_call_id=runtime.tool_call_id).first()
    if earlier:
        return _earlier_result(earlier)
    audit = {
        "tenant": context.tenant,
        "customer": context.customer,
        "action": ACTION,
        "details": {"subject": subject},
        "thread_id": thread_id,
        "tool_call_id": runtime.tool_call_id,
    }
    if not decision.get("approved"):
        record_action(**audit, status=AgentActionStatus.CANCELLED)
        return _result("cancelled")
    if not ratelimit.allow(scope="agent_ticket", subject=str(context.customer.public_id), limit=AGENT_TICKETS_PER_HOUR, window_seconds=3600):
        record_action(**audit, status=AgentActionStatus.BLOCKED)
        return _result("limit_reached")
    # One transaction: a ticket can never exist without its audit row, or the other way round.
    with transaction.atomic():
        ticket = create_ticket(tenant=context.tenant, customer=context.customer, subject=subject, body=details)
        record_action(**audit, status=AgentActionStatus.CONFIRMED, target_public_id=ticket.public_id)
    return _result("created", ticket_public_id=str(ticket.public_id))
