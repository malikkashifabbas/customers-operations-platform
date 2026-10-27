"""Request and response shapes for the chat API."""

from ninja import Field, Schema


class ChatIn(Schema):
    message: str = Field(min_length=1, max_length=4000)
    # Only letters, digits, - and _ so a client cannot smuggle ':' into the thread id.
    conversation_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ToolCallOut(Schema):
    name: str
    args: dict


class ChatOut(Schema):
    conversation_id: str
    reply: str
    tool_calls: list[ToolCallOut]
    llm_calls: int
    tokens: int
    latency_ms: int
    # Set by the guard nodes: why the question was refused, and what the output guard caught (empty = clean reply).
    blocked_reason: str | None = None
    output_flags: list[str] = []
