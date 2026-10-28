"""Account specialist: the customer's own profile (name, phone, email)."""

from pathlib import Path

from agents.core.domain import DomainSpec
from agents.core.prompts import load_prompt
from agents.core.react_subgraph import build_react_subgraph
from agents.domains.support.context import SupportContext
from agents.domains.support.graph import _capabilities
from agents.domains.support.guards import REPLY_LANGUAGE
from agents.domains.support.tools import get_my_profile

SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system.v1.md"
TOOLS = [get_my_profile]


def prompt_for(state, context: SupportContext, tools: list) -> str:
    return load_prompt(
        SYSTEM_PROMPT,
        company_name=context.tenant.name,
        capabilities=_capabilities(tools),
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )


SPEC = DomainSpec(
    name="account",
    description="the customer's own profile: their name, phone number or email address",
    build=lambda: build_react_subgraph(
        all_tools=TOOLS, tools_for=lambda context: TOOLS, prompt_for=prompt_for, context_schema=SupportContext
    ),
)
