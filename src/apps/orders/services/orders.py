"""Write-side business rules for orders."""

from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.customers.models import Customer
from core.models import Tenant
from infra.eventbus.events import OrderCancelledV1
from infra.eventbus.outbox import publish_event
from infra.eventbus.topics import ORDERS_CANCELLED

from ..exceptions import CustomerTenantMismatch, OrderAlreadyExists, OrderNotCancellable, OrderNotRefundable
from ..models import Order, OrderStatus


def create_order(
    *,
    tenant: Tenant,
    customer: Customer,
    order_number: str,
    amount: Decimal,
    currency: str = "USD",
    status: str = OrderStatus.PENDING,
    failure_reason: str = "",
    paid_at: datetime | None = None,
) -> Order:
    # The database cannot see that order.tenant and order.customer.tenant must match, so the service checks it.
    if customer.tenant_id != tenant.id:
        raise CustomerTenantMismatch()
    try:
        with transaction.atomic():
            return Order.objects.create(
                tenant=tenant,
                customer=customer,
                order_number=order_number.strip().upper(),
                amount=amount,
                currency=currency,
                status=status,
                failure_reason=failure_reason,
                paid_at=paid_at,
            )
    except IntegrityError as exc:
        raise OrderAlreadyExists() from exc


def refund_order(*, order: Order) -> Order:
    # Row lock + status re-check, so two approvals arriving together can never refund the same order twice.
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != OrderStatus.PAID:
            raise OrderNotRefundable(f"Order {locked.order_number} is {locked.status}; only paid orders can be refunded.")
        locked.status = OrderStatus.REFUNDED
        locked.save(update_fields=["status", "updated_at"])
    return locked


def cancel_order(*, order: Order) -> Order:
    """Pending orders only: no money was taken, so cancelling needs no refund. The event tells other services in the same transaction."""
    with transaction.atomic():
        # The payment can arrive while the customer is deciding, so the status is checked again under a row lock.
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != OrderStatus.PENDING:
            raise OrderNotCancellable(f"Order {locked.order_number} is now {locked.status}; only pending orders can be cancelled.")
        locked.status = OrderStatus.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.save(update_fields=["status", "cancelled_at", "updated_at"])
        publish_event(
            topic=ORDERS_CANCELLED,
            key=str(locked.public_id),
            event=OrderCancelledV1(tenant_public_id=str(locked.tenant.public_id), order_public_id=str(locked.public_id)),
        )
    return locked
