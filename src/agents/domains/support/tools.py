"""Tools; the customer comes from runtime.context, so the LLM can never choose whose data it sees.

Read tools run freely; request_refund changes money, so it pauses the graph (interrupt) until a staff member decides.
"""

import json

from langchain.tools import ToolRuntime, tool
from langgraph.types import interrupt

from apps.orders import selectors as order_selectors
from apps.orders import services as order_services
from apps.orders.models import Order, OrderStatus

from .context import SupportContext


def _order_to_dict(order: Order) -> dict:
    return {
        "order_number": order.order_number,
        "amount": f"{order.amount} {order.currency}",
        "status": order.status,
        "failure_reason": order.failure_reason or None,
        "placed_on": order.created_at.date().isoformat(),
        "paid_on": order.paid_at.date().isoformat() if order.paid_at else None,
    }


@tool
def get_my_profile(runtime: ToolRuntime[SupportContext]) -> str:
    """Get the current customer's own name, phone number and email."""
    customer = runtime.context.customer
    return json.dumps({"full_name": customer.full_name, "phone": customer.phone, "email": customer.email or None})


@tool
def list_my_orders(runtime: ToolRuntime[SupportContext]) -> str:
    """List the current customer's own orders, newest first, with number, amount, status and failure reason."""
    context = runtime.context
    orders = list(order_selectors.list_orders_for_customer(tenant=context.tenant, customer=context.customer))
    if not orders:
        return "This customer has no orders."
    return json.dumps([_order_to_dict(order) for order in orders])


@tool
def get_my_order(order_number: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Get one of the current customer's own orders by its order number, for example ORD-1002."""
    context = runtime.context
    order = order_selectors.get_order_for_customer(
        tenant=context.tenant, customer=context.customer, order_number=order_number
    )
    if order is None:
        return f"No order {order_number} was found for this customer."
    return json.dumps(_order_to_dict(order))


@tool
def get_my_spending_summary(runtime: ToolRuntime[SupportContext]) -> str:
    """Get the current customer's order totals per status (paid, failed, pending, refunded): count and total amount. Use it for any 'how much did I spend / pay' question."""
    context = runtime.context
    rows = order_selectors.spending_summary_for_customer(tenant=context.tenant, customer=context.customer)
    if not rows:
        return "This customer has no orders."
    return json.dumps(
        [
            {"status": row["status"], "order_count": row["order_count"], "total_amount": f"{row['total_amount']} {row['currency']}"}
            for row in rows
        ]
    )


@tool
def request_refund(order_number: str, reason: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Ask a staff member to approve a refund of one of the customer's own PAID orders. Nothing is refunded unless staff approve. Use it only when the customer clearly asks for a refund of a specific order."""
    context = runtime.context
    if context.channel != "ticket":
        return "Refunds need staff approval and can only be requested in a support ticket, not in chat."
    order = order_selectors.get_order_for_customer(
        tenant=context.tenant, customer=context.customer, order_number=order_number
    )
    if order is None:
        return f"No order {order_number} was found for this customer."
    if order.status != OrderStatus.PAID:
        return f"Order {order.order_number} is {order.status}; only paid orders can be refunded."

    # On resume this whole tool runs again from the top, so everything above must stay read-only.
    decision = interrupt(
        {
            "type": "refund_approval",
            "order_number": order.order_number,
            "amount": f"{order.amount} {order.currency}",
            "reason": reason,
        }
    )
    if not decision.get("approved"):
        return json.dumps({"refund_status": "rejected", "order_number": order.order_number, "staff_note": decision.get("note") or None})
    order = order_services.refund_order(order=order)
    return json.dumps({"refund_status": "done", "order_number": order.order_number, "amount": f"{order.amount} {order.currency}"})


TOOLS = [get_my_profile, list_my_orders, get_my_order, get_my_spending_summary]
TICKET_TOOLS = [*TOOLS, request_refund]
ALL_TOOLS = TICKET_TOOLS


def tools_for(context: SupportContext) -> list:
    return TICKET_TOOLS if context.channel == "ticket" else TOOLS
