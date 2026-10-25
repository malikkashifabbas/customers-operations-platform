"""Write-side business rules for customers."""

from django.db import IntegrityError, transaction

from core.models import Tenant

from ..exceptions import CustomerAlreadyExists
from ..models import Customer
from ..utils import normalize_phone


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
