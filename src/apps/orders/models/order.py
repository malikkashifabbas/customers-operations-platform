"""An order belongs to one customer inside one tenant; money is always Decimal, never float."""

from django.db import models

from core.models import TenantScopedModel


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Order(TenantScopedModel):
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="orders")
    order_number = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    failure_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "order_number"], name="orders_unique_number_per_tenant"),
        ]
        indexes = [
            models.Index(fields=["tenant", "customer", "-created_at"], name="orders_customer_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} ({self.status})"
