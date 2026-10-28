"""Knowledge specialist: answers company-policy questions from the tenant's own documents (agentic RAG over pgvector)."""

from agents.core.domain import DomainSpec

from .graph import build_graph

SPEC = DomainSpec(
    name="knowledge",
    description=(
        "company policies and general questions: returns and refunds rules, delivery or shipping times and costs, "
        "payment methods, cash on delivery, installments, warranty, account and privacy rules, support hours and contact"
    ),
    build=build_graph,
)
