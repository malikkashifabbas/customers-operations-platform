"""Tickets specialist: opens a support ticket from chat after the customer confirms."""

from pathlib import Path

from agents.core.domain import DomainSpec
from agents.core.prompts import load_prompt
from agents.core.react_subgraph import build_react_subgraph
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import _capabilities
from agents.domains.support.guards import REPLY_LANGUAGE

from .tools import create_support_ticket

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v1.md"
TOOLS = [create_support_ticket]


def tools_for(context: SupportContext) -> list:
    return TOOLS if context.channel == "chat" else []


def prompt_for(state, context: SupportContext, tools: list) -> str:
    return load_prompt(
        SYSTEM_PROMPT,
        company_name=context.tenant.name,
        capabilities=_capabilities(tools) if tools else "- nothing: this conversation is already a support ticket",
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )


SPEC = DomainSpec(
    name="tickets",
    description="the customer asks the assistant to open, raise or create a support ticket for them",
    build=lambda: build_react_subgraph(
        all_tools=TOOLS, tools_for=tools_for, prompt_for=prompt_for, context_schema=SupportContext
    ),
)
