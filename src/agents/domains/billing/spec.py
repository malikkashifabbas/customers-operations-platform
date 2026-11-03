"""Billing specialist: orders, payments, spending totals, refunds that need staff approval (tickets) and pending-order cancels (chat)."""

from pathlib import Path

from agents.core.domain import DomainSpec
from agents.core.prompts import load_prompt
from agents.core.react_subgraph import build_react_subgraph
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import REFUND_RULE, _capabilities
from agents.domains.support.guards import REPLY_LANGUAGE
from agents.domains.support.tools import get_my_order, get_my_spending_summary, list_my_orders, request_refund

from .tools import cancel_my_order

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v4.md"
READ_TOOLS = [list_my_orders, get_my_order, get_my_spending_summary]


def tools_for(context: SupportContext) -> list:
    return [*READ_TOOLS, request_refund] if context.channel == "ticket" else [*READ_TOOLS, cancel_my_order]


def prompt_for(state, context: SupportContext, tools: list) -> str:
    return load_prompt(
        SYSTEM_PROMPT,
        company_name=context.tenant.name,
        capabilities=_capabilities(tools),
        refund_rule=REFUND_RULE[context.channel],
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )


SPEC = DomainSpec(
    name="billing",
    description="the customer's OWN orders: order status, why their order failed, how much they spent, asking to refund or cancel a specific order",
    build=lambda: build_react_subgraph(
        all_tools=[*READ_TOOLS, request_refund, cancel_my_order], tools_for=tools_for, prompt_for=prompt_for, context_schema=SupportContext
    ),
)
