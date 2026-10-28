"""Knowledge subgraph (agentic RAG): only wiring here, the steps live in nodes.py."""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agents.domains.support.context import SupportContext

from .nodes import KnowledgeState, generate_answer, generate_query_or_respond, grade_documents, rewrite_question
from .tools import search_policies


def build_graph():
    builder = StateGraph(KnowledgeState, context_schema=SupportContext)
    builder.add_node("generate_query_or_respond", generate_query_or_respond)
    builder.add_node("retrieve", ToolNode([search_policies]))
    builder.add_node("rewrite_question", rewrite_question)
    builder.add_node("generate_answer", generate_answer)

    builder.add_edge(START, "generate_query_or_respond")
    builder.add_conditional_edges("generate_query_or_respond", tools_condition, {"tools": "retrieve", END: END})
    builder.add_conditional_edges("retrieve", grade_documents, ["generate_answer", "rewrite_question"])
    builder.add_edge("rewrite_question", "retrieve")
    builder.add_edge("generate_answer", END)
    return builder.compile()
