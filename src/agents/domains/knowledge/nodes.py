"""Agentic RAG steps: write a search query -> (retrieve) -> grade the results -> answer, or rewrite the query once and search again."""

import logging
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
MAX_QUERIES = 4
logger = logging.getLogger(__name__)


class KnowledgeState(DomainState):
    rewrites: int


class SearchPlan(BaseModel):
    queries: list[str] = Field(description="One short English keyword query for EACH thing the customer asks. Never merge or drop a part.")


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


def _search_calls(queries: list[str], prefix: str) -> AIMessage:
    """Ready-made search tool calls: they go straight to the retrieve node and add no customer-visible text."""
    calls = [
        {"name": search_policies.name, "args": {"query": query}, "id": f"{prefix}_{uuid.uuid4().hex[:12]}", "type": "tool_call"}
        for query in queries
    ]
    return AIMessage(content="", tool_calls=calls)


def generate_query_or_respond(state: KnowledgeState, runtime: Runtime[SupportContext]) -> dict:
    prompt = load_prompt(PROMPTS / "query.v4.md", company_name=runtime.context.tenant.name)
    # A form, not bind_tools: given the tool, the model asked one thing of a two-part question (0/5 on the express test).
    llm = get_chat_model().with_structured_output(SearchPlan, include_raw=True)
    # Only a short transcript, not the full history: earlier turns hold other specialists' tool calls.
    request = f"Conversation so far:\n{_transcript(state['messages'][:-1]) or '(none)'}\n\nLatest customer message: {_question(state)}"
    try:
        result = llm.invoke([SystemMessage(prompt), HumanMessage(request)])
    except Exception:
        # A policy answer must come from the documents, so a failed plan still searches with the customer's own words.
        logger.warning("search plan failed, searching with the raw question", exc_info=True)
        return {"messages": [_search_calls([_question(state)], prefix="fallback")]}
    plan = result["parsed"]
    queries = [query.strip() for query in (plan.queries if plan else []) if query.strip()][:MAX_QUERIES]
    message = _search_calls(queries or [_question(state)], prefix="search")
    message.usage_metadata = result["raw"].usage_metadata
    return {"messages": [message]}


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
    return {"messages": [_search_calls([query], prefix="rewrite")], "rewrites": state.get("rewrites", 0) + 1}


def generate_answer(state: KnowledgeState, runtime: Runtime[SupportContext]) -> dict:
    today = datetime.now(ZoneInfo("Asia/Karachi")).strftime("%d %B %Y")
    prompt = load_prompt(
        PROMPTS / "answer.v3.md",
        company_name=runtime.context.tenant.name,
        today=today,
        reply_language=REPLY_LANGUAGE[state.get("language", "english")],
    )
    # The plan's queries, not the whole message: told only "ignore other parts", the answer still refused the orders part.
    topics = [call["args"]["query"] for m in _this_turn(state["messages"]) if isinstance(m, AIMessage) for call in m.tool_calls]
    material = (
        f"Customer question: {_question(state)}\n\nTopics to answer: {', '.join(topics) or 'the question above'}\n\n"
        f"Policy text:\n{_retrieved(state) or '(nothing found)'}"
    )
    return {"messages": [get_chat_model().invoke([SystemMessage(prompt), HumanMessage(material)])]}
