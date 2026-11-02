"""Print what the login API needs for demo users: tenant_public_id, phones and staff usernames (local testing only)."""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.accounts.models import StaffProfile
from apps.customers.models import Customer
from core.models import Tenant


class Command(BaseCommand):
    help = "List tenants, customers and staff with the values used in POST /api/auth/customer/login and /staff/login."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="only this tenant slug, e.g. demo-company")
        parser.add_argument("--search", help="filter customers by name, phone or email")
        parser.add_argument("--limit", type=int, default=10, help="customers per tenant (default 10)")

    def handle(self, *args, **options):
        tenants = Tenant.objects.order_by("id")
        if options["tenant"]:
            tenants = tenants.filter(slug=options["tenant"])

        for tenant in tenants:
            self.stdout.write(self.style.SUCCESS(f"\n{tenant.name} ({tenant.slug})"))
            self.stdout.write(f"  tenant_public_id: {tenant.public_id}")
            for staff in StaffProfile.objects.filter(tenant=tenant).select_related("user"):
                self.stdout.write(f"  staff username:   {staff.user.get_username()}")
            self.stdout.write("")
            customers = Customer.objects.filter(tenant=tenant).annotate(order_count=Count("orders")).order_by("id")
            if options["search"]:
                term = options["search"]
                customers = customers.filter(Q(full_name__icontains=term) | Q(phone__icontains=term) | Q(email__icontains=term))
            for customer in customers[: options["limit"]]:
                self.stdout.write(
                    f"  phone: {customer.phone:<15} {customer.full_name:<16} "
                    f"{customer.email or '-':<32} {customer.order_count} orders"
                )
