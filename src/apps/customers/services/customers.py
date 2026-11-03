"""Write-side business rules for customers."""

from django.db import IntegrityError, transaction

from core.models import Tenant

from ..exceptions import CustomerAlreadyExists
from ..models import Customer
from ..utils import normalize_phone


def change_customer_name(*, customer: Customer, full_name: str) -> Customer:
    customer.full_name = full_name.strip()
    customer.save(update_fields=["full_name", "updated_at"])
    return customer


def change_customer_email(*, customer: Customer, email: str) -> Customer:
    customer.email = email
    customer.save(update_fields=["email", "updated_at"])
    return customer


def create_customer(*, tenant: Tenant, full_name: str, phone: str, email: str = "") -> Customer:
    try:
        with transaction.atomic():
            return Customer.objects.create(
                tenant=tenant,
                full_name=full_name.strip(),
                phone=normalize_phone(phone),
                email=email,
            )
    except IntegrityError as exc:
        raise CustomerAlreadyExists() from exc
