"""Read-only tools; the customer comes from runtime.context, so the LLM can never choose whose data it sees."""

import json

from langchain.tools import ToolRuntime, tool

from apps.orders import selectors as order_selectors
from apps.orders.models import Order

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


TOOLS = [get_my_profile, list_my_orders, get_my_order, get_my_spending_summary]
