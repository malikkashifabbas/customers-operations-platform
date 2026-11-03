"""Tools that change the customer's own profile: only for companies that allow it, and only after the customer confirms."""

import json
import logging
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from agents.core.write_actions import earlier_result, finish
from agents.domains.support.context import SupportContext
from apps.accounts.services import send_email_change_link
from apps.agent_actions.models import AgentActionStatus
from apps.customers.services import change_customer_name
from core.limits import EMAIL_CHANGE_LINKS_PER_HOUR
from infra.cache import ratelimit

logger = logging.getLogger(__name__)
MAX_NAME = 200
MIN_NAME = 2
# A name is shown to staff and in replies, so links, emails and markup have no place in it.
BAD_NAME = re.compile(r"[<>@/\\{}\[\]\d]")


def _result(status: str, **extra) -> str:
    return json.dumps({"profile_status": status, **extra})


def _not_allowed(context: SupportContext) -> str | None:
    # Checked here too: not offering a tool to the LLM is not a guarantee, because ToolNode can run every tool it holds.
    if context.channel != "chat" or not context.tenant.agent_can_edit_profile:
        return "Profile changes are not available here. The customer can open a support ticket."
    return None


@tool
def update_my_name(new_name: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Change the current customer's name. The customer is asked to confirm first; nothing changes unless they do. Use it only when they clearly ask to change their own name and have given the new name."""
    refused = _not_allowed(runtime.context)
    if refused:
        return refused
    customer = runtime.context.customer
    new_name = " ".join(new_name.split())
    if not MIN_NAME <= len(new_name) <= MAX_NAME or BAD_NAME.search(new_name):
        return "That name cannot be used: it must be 2 to 200 characters, with no digits, links or symbols."
    if new_name == customer.full_name:
        return "That is already the name on this account."

    # On resume this whole tool runs again from the top, so everything above must stay read-only.
    decision = interrupt({"type": "name_change", "old_name": customer.full_name, "new_name": new_name})

    earlier = earlier_result(runtime)
    if earlier:
        return earlier
    details = {"field": "name", "old_name": customer.full_name, "new_name": new_name}
    if not decision.get("approved"):
        return finish(runtime, action="change_name", status=AgentActionStatus.CANCELLED, details=details, result=_result("unchanged", reason="the customer chose not to change it"))
    # One transaction: the name can never change without its audit row.
    with transaction.atomic():
        change_customer_name(customer=customer, full_name=new_name)
        return finish(
            runtime, action="change_name", status=AgentActionStatus.CONFIRMED, details=details, target_public_id=customer.public_id,
            result=_result("updated", field="name", new_name=new_name),
        )


@tool
def request_email_change(new_email: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Start changing the current customer's email. The customer confirms first, then a link goes to the new address, and the email changes only when that link is opened. Use it only when they clearly ask to change their own email and have given the new one."""
    refused = _not_allowed(runtime.context)
    if refused:
        return refused
    customer = runtime.context.customer
    new_email = new_email.strip().lower()
    try:
        validate_email(new_email)
    except ValidationError:
        return "That is not a valid email address."
    if new_email == customer.email.lower():
        return "That is already the email on this account."

    # On resume this whole tool runs again from the top, so everything above must stay read-only.
    decision = interrupt({"type": "email_change", "old_email": customer.email or "-", "new_email": new_email})

    earlier = earlier_result(runtime)
    if earlier:
        return earlier
    details = {"field": "email", "old_email": customer.email, "new_email": new_email}
    audit = {"action": "request_email_change", "details": details}
    if not decision.get("approved"):
        return finish(runtime, **audit, status=AgentActionStatus.CANCELLED, result=_result("unchanged", reason="the customer chose not to change it"))
    # The limit protects the address too: without it this could flood a stranger's inbox with our links.
    if not ratelimit.allow(scope="email_change", subject=str(customer.public_id), limit=EMAIL_CHANGE_LINKS_PER_HOUR, window_seconds=3600):
        return finish(runtime, **audit, status=AgentActionStatus.BLOCKED, result=_result("limit_reached"))
    try:
        send_email_change_link(customer=customer, new_email=new_email)
    except Exception:
        logger.exception("email change link could not be sent")
        return finish(runtime, **audit, status=AgentActionStatus.BLOCKED, result=_result("link_failed"))
    return finish(runtime, **audit, status=AgentActionStatus.CONFIRMED, target_public_id=customer.public_id, result=_result("link_sent", field="email", new_email=new_email))
