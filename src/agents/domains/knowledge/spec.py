"""Knowledge specialist: company policies and general questions. No knowledge base yet (RAG is Lesson 15), so it says so in fixed text."""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from agents.core.domain import DomainSpec
from agents.core.react_subgraph import DomainState
from agents.domains.support.context import SupportContext

# Fixed text, not an LLM: without a knowledge base an LLM would invent office hours and policies.
NO_KNOWLEDGE = {
    "english": "I don't have information about our policies or general company details yet. Please contact the support team for that.",
    "roman_urdu": "Mere paas abhi company ki policies ya general maloomat nahi hain. Is ke liye support team se rabta karein.",
    "urdu": "میرے پاس ابھی کمپنی کی پالیسیوں یا عمومی معلومات نہیں ہیں۔ اس کے لیے سپورٹ ٹیم سے رابطہ کریں۔",
}


def answer(state: DomainState) -> dict:
    return {"messages": [AIMessage(NO_KNOWLEDGE[state.get("language", "english")])]}


def build():
    builder = StateGraph(DomainState, context_schema=SupportContext)
    builder.add_node("answer", answer)
    builder.add_edge(START, "answer")
    builder.add_edge("answer", END)
    return builder.compile()


SPEC = DomainSpec(
    name="knowledge",
    description="company policies and general questions: returns, delivery times, office hours, contact options, how things work",
    build=build,
)
