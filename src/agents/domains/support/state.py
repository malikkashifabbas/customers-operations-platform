"""Graph state: the chat messages plus what the guard nodes decided for the latest message."""

from typing import Literal

from langgraph.graph import MessagesState

Language = Literal["english", "roman_urdu", "urdu"]
BlockedReason = Literal["other_customer", "prompt_injection", "off_topic"]


class SupportState(MessagesState):
    language: Language
    blocked_reason: BlockedReason | None
    output_flags: list[str]
