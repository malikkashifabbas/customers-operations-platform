"""The retriever tool: hybrid (meaning + keyword) search over the current tenant's policy documents."""

from langchain.tools import ToolRuntime, tool

from agents.domains.support.context import SupportContext
from apps.knowledge.selectors import hybrid_search_chunks
from config.env import env
from infra.llm.embeddings import embed_query


@tool(response_format="content_and_artifact")
def search_policies(query: str, runtime: ToolRuntime[SupportContext]) -> tuple[str, dict]:
    """Search this company's policy documents: returns and refunds, delivery or shipping, payments and installments, account and privacy, contact and support hours, warranty, FAQ. Use short English keyword queries."""
    # The tenant comes from runtime.context, so one company's policies can never answer another company's customer.
    chunks = hybrid_search_chunks(
        tenant=runtime.context.tenant, query=query, query_embedding=embed_query(query), limit=env.rag_search_limit
    )
    if not chunks:
        return "No policy documents found.", {"confident": False}
    text = "\n\n".join(
        f"[{index}] Source: {chunk.document.title}, section {chunk.section} ({chunk.document.version})\n"
        f"{chunk.text.split(chr(10), 1)[-1]}"
        for index, chunk in enumerate(chunks, start=1)
    )
    # The artifact goes into the ToolMessage for code to read, but is never shown to the LLM.
    # Both searches must rank it FIRST: "found by both" was true for almost every chunk (words like "return" match all).
    return text, {"confident": chunks[0].ranks == {"meaning": 1, "words": 1}}
