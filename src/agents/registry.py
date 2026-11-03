"""Every domain specialist, one line each: a new domain = a new folder with a spec.py + one line here."""

from agents.core.domain import DomainSpec
from agents.domains.account.spec import SPEC as ACCOUNT
from agents.domains.billing.spec import SPEC as BILLING
from agents.domains.knowledge.spec import SPEC as KNOWLEDGE
from agents.domains.tickets.spec import SPEC as TICKETS

DOMAINS: dict[str, DomainSpec] = {spec.name: spec for spec in (BILLING, ACCOUNT, KNOWLEDGE, TICKETS)}


def domains_for(channel: str) -> dict[str, DomainSpec]:
    return {name: spec for name, spec in DOMAINS.items() if channel in spec.channels}
