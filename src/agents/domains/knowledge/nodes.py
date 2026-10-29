"""Agentic RAG steps: write a search query -> (retrieve) -> grade the results -> answer, or rewrite the query once and search again."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from agents.core.prompts import load_prompt
from agents.core.react_subgraph import DomainState
from agents.domains.support.context import SupportContext
from agents.domains.support.guards import REPLY_LANGUAGE
from config.env import env
from infra.llm.gateway import get_chat_model

from .tools import search_policies

PROMPTS = Path(__file__).parent / "prompts"
MAX_REWRITES = 1
TRANSCRIPT_MESSAGES = 4


class KnowledgeState(DomainState):
    rewrites: int


class Grade(BaseModel):
    relevant: bool = Field(description="True if the retrieved text answers the question fully or partly.")


def _this_turn(messages: list[BaseMessage]) -> list[BaseMessage]:
    last_human = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    return messages[last_human:]


def _question(state: KnowledgeState) -> str:
    return str(_this_turn(state["messages"])[0].content)


def _retrieved(state: KnowledgeState) -> str:
    return "\n\n".join(str(m.content) for m in _this_turn(state["messages"]) if isinstance(m, ToolMessage))


def _transcript(messages: list[BaseMessage]) -> str:
    lines = [
        f"{'Customer' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and m.content and not m.tool_calls)
    ]
    return "\n".join(lines[-TRANSCRIPT_MESSAGES:])


def _search_call(query: str, prefix: str) -> AIMessage:
    """A ready-made search tool call: it goes straight to the retrieve node and adds no customer-visible text."""
    call = {"name": search_policies.name, "args": {"query": query}, "id": f"{prefix}_{uuid.uuid4().hex[:12]}", "type": "tool_call"}
    return AIMessage(content="", tool_calls=[call])


def generate_query_or_respond(state: KnowledgeState, runtime: Runtime[SupportContext]) -> dict:
    prompt = load_prompt(PROMPTS / "query.v1.md", company_name=runtime.context.tenant.name)
    llm = get_chat_model().bind_tools([search_policies])
    # Only a short transcript, not the full history: earlier turns hold other specialists' tool calls.
    request = f"Conversation so far:\n{_transcript(state['messages'][:-1]) or '(none)'}\n\nLatest customer message: {_question(state)}"
    response = llm.invoke([SystemMessage(prompt), HumanMessage(request)])
    if not response.tool_calls:
        # Code, not tool_choice="required", guarantees the search: that API flag errors out when the model ignores it.
        response = _search_call(_question(state), prefix="fallback")
    return {"messages": [response]}


def grade_documents(state: KnowledgeState) -> Literal["generate_answer", "rewrite_question"]:
    if state.get("rewrites", 0) >= MAX_REWRITES:
        return "generate_answer"  # already searched twice: answer with what we have (it may say "I don't know")
    searches = [m for m in _this_turn(state["messages"]) if isinstance(m, ToolMessage)]
    if env.rag_skip_confident_grade and searches and all((m.artifact or {}).get("confident") for m in searches):
        return "generate_answer"  # Lesson 16B: both searches agree on the top chunk, so skip the LLM grade call
    llm = get_chat_model(model=env.llm_guard_model).with_structured_output(Grade)
    grade = llm.invoke(
        [
            SystemMessage(load_prompt(PROMPTS / "grade.v1.md")),
            HumanMessage(f"Question: {_question(state)}\n\nRetrieved policy text:\n{_retrieved(state)}"),
        ]
    )
    return "generate_answer" if grade.relevant else "rewrite_question"


def rewrite_question(state: KnowledgeState) -> dict:
    llm = get_chat_model()
    query = llm.invoke(
        [SystemMessage(load_prompt(PROMPTS / "rewrite.v1.md")), HumanMessage(f"Customer question: {_question(state)}")]
    ).content.strip().strip('"')
    return {"messages": [_search_call(query, prefix="rewrite")], "rewrites": state.get("rewrites", 0) + 1}


def generate_answer(state: KnowledgeState, runtime: Runtime[SupportContext]) -> dict:
    today = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %B %Y")
    prompt = load_prompt(
        PROMPTS / "answer.v1.md",
        company_name=runtime.context.tenant.name,
        today=today,
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )
    material = f"Customer question: {_question(state)}\n\nPolicy text:\n{_retrieved(state) or '(nothing found)'}"
    return {"messages": [get_chat_model().invoke([SystemMessage(prompt), HumanMessage(material)])]}
