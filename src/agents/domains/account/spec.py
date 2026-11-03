"""Account specialist: reads the customer's own profile and, where the company allows it, changes the name or email."""

from pathlib import Path

from agents.core.domain import DomainSpec
from agents.core.prompts import load_prompt
from agents.core.react_subgraph import build_react_subgraph
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import _capabilities
from agents.domains.support.guards import REPLY_LANGUAGE
from agents.domains.support.tools import get_my_profile

from .tools import request_email_change, update_my_name

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v3.md"
READ_TOOLS = [get_my_profile]
WRITE_TOOLS = [update_my_name, request_email_change]


def tools_for(context: SupportContext) -> list:
    can_edit = context.channel == "chat" and context.tenant.agent_can_edit_profile
    return [*READ_TOOLS, *WRITE_TOOLS] if can_edit else READ_TOOLS


def prompt_for(state, context: SupportContext, tools: list) -> str:
    return load_prompt(
        SYSTEM_PROMPT,
        company_name=context.tenant.name,
        capabilities=_capabilities(tools),
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )


SPEC = DomainSpec(
    name="account",
    description="the customer's own profile: seeing their name, phone number or email address, or asking to change their own name or email",
    build=lambda: build_react_subgraph(
        all_tools=[*READ_TOOLS, *WRITE_TOOLS], tools_for=tools_for, prompt_for=prompt_for, context_schema=SupportContext
    ),
)
