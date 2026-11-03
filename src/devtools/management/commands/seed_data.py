"""Fill the local database with demo tenants, customers and orders; safe to run again (no duplicates)."""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import StaffProfile
from apps.customers.models import Customer
from apps.orders.models import Order, OrderStatus
from config.env import env
from core.models import Tenant

TENANTS = {"demo-company": "Demo Company", "nimbustech": "NimbusTech"}
# NimbusTech's policy needs a CNIC photo and both emails to confirm, so its agent must not edit profiles.
AGENT_CAN_EDIT_PROFILE = {"demo-company"}

# Known customers and orders that the lesson's test questions rely on.
FIXED = {
    "demo-company": [
        ("Ali Khan", "+923001234567", "ali@example.com", [
            ("ORD-1001", "49.00", OrderStatus.PAID, ""),
            ("ORD-1002", "120.00", OrderStatus.FAILED, "Card declined by bank"),
            ("ORD-1003", "15.50", OrderStatus.PENDING, ""),
        ]),
        ("Sara Ahmed", "+923331112233", "sara@example.com", [
            ("ORD-2001", "75.00", OrderStatus.REFUNDED, ""),
            ("ORD-2002", "30.00", OrderStatus.PAID, ""),
        ]),
    ],
    "nimbustech": [
        ("Ali Khan", "+923001234567", "", [
            ("ORD-1001", "999.00", OrderStatus.PAID, ""),
        ]),
    ],
}

FIRST_NAMES = [
    "Ahmed", "Ayesha", "Bilal", "Fatima", "Hamza", "Hina", "Imran", "Maria", "Usman", "Zainab",
    "Omar", "Sana", "Hassan", "Noor", "Daniyal", "Mehwish", "John", "Emma", "Liam", "Olivia",
]
LAST_NAMES = ["Raza", "Siddiqui", "Qureshi", "Malik", "Chaudhry", "Butt", "Shah", "Iqbal", "Smith", "Brown"]
FAILURE_REASONS = [
    "Card declined by bank",
    "Insufficient funds",
    "Card expired",
    "3-D Secure authentication failed",
    "Payment gateway timeout",
]
STATUS_WEIGHTS = {OrderStatus.PAID: 60, OrderStatus.FAILED: 15, OrderStatus.PENDING: 15, OrderStatus.REFUNDED: 10}
FIRST_RANDOM_ORDER = {"demo-company": 3001, "nimbustech": 5001}


class Command(BaseCommand):
    help = "Create demo tenants, customers and ~200 orders for local testing."

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=25, help="random customers for Demo Company (NimbusTech gets 15)")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(42)  # fixed seed: every run produces the same data, so re-running updates instead of duplicating
        now = timezone.now()
        random_customers = {"demo-company": options["customers"], "nimbustech": 15}

        for slug, name in TENANTS.items():
            tenant, _ = Tenant.objects.update_or_create(
                slug=slug, defaults={"name": name, "agent_can_edit_profile": slug in AGENT_CAN_EDIT_PROFILE}
            )

            for full_name, phone, email, orders in FIXED[slug]:
                customer = self._customer(tenant, full_name, phone, email)
                for number, amount, status, reason in orders:
                    self._order(tenant, customer, number, Decimal(amount), status, reason, now - timedelta(days=rng.randint(1, 60)))

            next_number = FIRST_RANDOM_ORDER[slug]
            for index in range(random_customers[slug]):
                first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
                phone = f"+92300{rng.randint(1_000_000, 9_999_999)}"
                customer = self._customer(tenant, f"{first} {last}", phone, f"{first.lower()}.{last.lower()}{index}@example.com")
                for _ in range(rng.randint(2, 6)):
                    status = rng.choices(list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()))[0]
                    reason = rng.choice(FAILURE_REASONS) if status == OrderStatus.FAILED else ""
                    amount = Decimal(rng.randint(500, 50_000)) / 100
                    placed_at = now - timedelta(days=rng.randint(1, 90), hours=rng.randint(0, 23))
                    self._order(tenant, customer, f"ORD-{next_number}", amount, status, reason, placed_at)
                    next_number += 1

            self._logins(tenant)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {Tenant.objects.count()} tenants, {Customer.objects.count()} customers, {Order.objects.count()} orders"
        ))
        for slug in TENANTS:
            self.stdout.write(f"  {slug}: {Order.objects.filter(tenant__slug=slug).count()} orders")

    def _logins(self, tenant: Tenant) -> None:
        if env.demo_password is None:
            self.stderr.write("DEMO_PASSWORD is not set: demo customers and staff cannot log in")
            return
        password = env.demo_password.get_secret_value()
        # One shared hash: dozens of slow hashes would make every re-seed crawl, and this is fake local data only.
        Customer.objects.filter(tenant=tenant).update(password=make_password(password))
        user, _ = get_user_model().objects.get_or_create(username=f"staff.{tenant.slug}")
        user.set_password(password)
        user.save(update_fields=["password"])
        StaffProfile.objects.get_or_create(user=user, defaults={"tenant": tenant})

    def _customer(self, tenant: Tenant, full_name: str, phone: str, email: str) -> Customer:
        customer, _ = Customer.objects.update_or_create(
            tenant=tenant, phone=phone, defaults={"full_name": full_name, "email": email}
        )
        return customer

    def _order(self, tenant, customer, number, amount, status, reason, placed_at) -> None:
        paid_at = placed_at + timedelta(minutes=5) if status in (OrderStatus.PAID, OrderStatus.REFUNDED) else None
        order, _ = Order.objects.update_or_create(
            tenant=tenant,
            order_number=number,
            defaults={
                "customer": customer,
                "amount": amount,
                "status": status,
                "failure_reason": reason,
                "paid_at": paid_at,
            },
        )
        # created_at is auto_now_add, so back-date it with update() to spread orders over past days.
        Order.objects.filter(pk=order.pk).update(created_at=placed_at)
