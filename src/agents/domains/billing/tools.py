"""Billing tools that change an order: chat only, and only after the customer confirms."""

import json

from django.db import transaction
from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from agents.core.write_actions import earlier_result, finish
from agents.domains.support.context import SupportContext
from apps.agent_actions.models import AgentActionStatus
from apps.orders import selectors as order_selectors
from apps.orders.exceptions import OrderNotCancellable
from apps.orders.models import OrderStatus
from apps.orders.services import cancel_order

ACTION = "cancel_order"


def _result(status: str, **extra) -> str:
    return json.dumps({"order_status": status, **extra})


@tool
def cancel_my_order(order_number: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Cancel one of the current customer's own PENDING orders (payment not received yet). The customer is asked to confirm first; nothing changes unless they do. A paid order cannot be cancelled here: it needs a refund through a support ticket."""
    context = runtime.context
    if context.channel != "chat":
        return "Orders can be cancelled only in chat, where the customer can confirm."
    order = order_selectors.get_order_for_customer(tenant=context.tenant, customer=context.customer, order_number=order_number)
    if order is None:
        return f"No order {order_number} was found for this customer."
    if order.status == OrderStatus.PAID:
        return f"Order {order.order_number} is already paid, so cancelling it means a refund: the customer must open a support ticket for staff approval."
    if order.status != OrderStatus.PENDING:
        return f"Order {order.order_number} is {order.status}; only pending orders can be cancelled."

    # On resume this whole tool runs again from the top, so everything above must stay read-only.
    decision = interrupt({"type": "order_cancel", "order_number": order.order_number, "amount": f"{order.amount} {order.currency}"})

    earlier = earlier_result(runtime)
    if earlier:
        return earlier
    details = {"order_number": order.order_number, "amount": f"{order.amount} {order.currency}"}
    if not decision.get("approved"):
        return finish(runtime, action=ACTION, status=AgentActionStatus.CANCELLED, details=details, result=_result("unchanged", reason="the customer chose not to cancel"))
    try:
        # One transaction: the cancel, its outbox event and its audit row are saved together or not at all.
        with transaction.atomic():
            cancelled = cancel_order(order=order)
            return finish(
                runtime, action=ACTION, status=AgentActionStatus.CONFIRMED, details=details, target_public_id=cancelled.public_id,
                result=_result("cancelled", order_number=cancelled.order_number),
            )
    except OrderNotCancellable as exc:
        return finish(runtime, action=ACTION, status=AgentActionStatus.BLOCKED, details=details, result=_result("not_cancellable", reason=exc.message))
