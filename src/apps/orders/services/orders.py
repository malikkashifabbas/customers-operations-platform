"""Write-side business rules for orders."""

from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.customers.models import Customer
from core.models import Tenant

from ..exceptions import CustomerTenantMismatch, OrderAlreadyExists, OrderNotRefundable
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
