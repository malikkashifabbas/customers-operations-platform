"""Change an email only after the new address proves it is reachable: a signed one-time link, valid for 24 hours."""

from django.core.mail import send_mail
from django.db import transaction

from apps.agent_actions.models import AgentActionStatus
from apps.agent_actions.services import record_action
from apps.customers.models import Customer
from apps.customers.services import change_customer_email
from config.env import env

from .. import tokens
from ..exceptions import InvalidToken


def send_email_change_link(*, customer: Customer, new_email: str) -> None:
    claims = {
        "sub": str(customer.public_id),
        "customer_public_id": str(customer.public_id),
        "tenant_public_id": str(customer.tenant.public_id),
        "current_email": customer.email,
        "new_email": new_email,
        "pwd": tokens.password_fingerprint(customer.password),
    }
    link = f"{env.public_base_url}/api/auth/email/confirm?token={tokens.mint(claims, tokens.EMAIL_CHANGE)}"
    send_mail(
        subject=f"Confirm your new email for {customer.tenant.name}",
        message=f"Open this link within 24 hours to use this email on your account:\n\n{link}\n\nIf you did not ask for this, ignore this message.",
        from_email=None,
        recipient_list=[new_email],
    )


def confirm_email_change(*, token: str) -> str:
    claims = tokens.read(token, tokens.EMAIL_CHANGE)
    if not claims:
        raise InvalidToken()
    customer = (
        Customer.objects.select_related("tenant")
        .filter(public_id=claims.get("customer_public_id"), tenant__public_id=claims.get("tenant_public_id"), tenant__is_active=True)
        .first()
    )
    # A changed password or email since the link was sent means this request may no longer be what the customer wants.
    if customer is None or claims.get("pwd") != tokens.password_fingerprint(customer.password) or claims.get("current_email") != customer.email:
        raise InvalidToken()
    new_email = claims["new_email"]
    with transaction.atomic():
        change_customer_email(customer=customer, email=new_email)
        record_action(
            tenant=customer.tenant,
            customer=customer,
            action="email_change_applied",
            status=AgentActionStatus.CONFIRMED,
            details={"field": "email", "old_email": claims.get("current_email"), "new_email": new_email},
            target_public_id=customer.public_id,
        )
    tokens.revoke(claims)
    return new_email
