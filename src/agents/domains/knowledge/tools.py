"""The retriever tool: hybrid (meaning + keyword) search over the current tenant's policy documents."""

from langchain.tools import ToolRuntime, tool

from agents.domains.support.context import SupportContext
from apps.knowledge.selectors import hybrid_search_chunks
from infra.llm.embeddings import embed_query

SEARCH_LIMIT = 5


@tool
def search_policies(query: str, runtime: ToolRuntime[SupportContext]) -> str:
    """Search this company's policy documents: returns and refunds, delivery or shipping, payments and installments, account and privacy, contact and support hours, warranty, FAQ. Use short English keyword queries."""
    # The tenant comes from runtime.context, so one company's policies can never answer another company's customer.
    chunks = hybrid_search_chunks(
        tenant=runtime.context.tenant, query=query, query_embedding=embed_query(query), limit=SEARCH_LIMIT
    )
    if not chunks:
        return "No policy documents found."
    return "\n\n".join(
        f"[{index}] Source: {chunk.document.title}, section {chunk.section} ({chunk.document.version})\n"
        f"{chunk.text.split(chr(10), 1)[-1]}"
        for index, chunk in enumerate(chunks, start=1)
    )
