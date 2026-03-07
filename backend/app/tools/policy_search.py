"""RAG-based policy document search tool.

Flow: Query → Bedrock embeddings → cosine similarity against stored embeddings
→ fetch top-K documents from S3 → return synthesized results.
"""

import logging
import math

from langchain_core.tools import tool

from app.services import bedrock, dynamodb, s3

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@tool
def search_policies(query: str, state: str = "", category: str = "") -> str:
    """Search government agricultural policies and schemes.

    Use this tool when the farmer asks about government policies, subsidies,
    schemes (like PM-KISAN, PMFBY), agricultural guidelines, or official
    agricultural advisories.

    Args:
        query: The policy search query in natural language
        state: Optional state name to filter state-specific policies
        category: Optional category filter (e.g., 'subsidy', 'insurance', 'loan')

    Returns:
        Relevant policy information synthesized from government documents
    """
    try:
        query_embedding = bedrock.generate_embeddings(query)
        all_docs = dynamodb.get_all_policy_documents()

        if not all_docs:
            return "No policy documents are currently indexed. Please check back later."

        # Filter by state/category if provided
        filtered = all_docs
        if state:
            filtered = [d for d in filtered if d.get("state", "").lower() == state.lower() or d.get("state") == "central"]
        if category:
            filtered = [d for d in filtered if d.get("category", "").lower() == category.lower()]

        if not filtered:
            filtered = all_docs

        # Score documents by cosine similarity
        scored = []
        for doc in filtered:
            doc_embedding = doc.get("embedding")
            if doc_embedding:
                score = _cosine_similarity(query_embedding, doc_embedding)
                scored.append((score, doc))

        if not scored:
            return "No policy documents with embeddings found. Documents may still be processing."

        scored.sort(key=lambda x: x[0], reverse=True)
        top_docs = scored[:3]

        results = []
        for score, doc in top_docs:
            if score < 0.3:
                continue
            # Fetch full document content from S3
            try:
                content_bytes = s3.get_policy_document(doc["s3_key"])
                content = content_bytes.decode("utf-8")[:2000]
            except Exception:
                content = doc.get("title", "Document content unavailable")

            results.append(
                f"**{doc.get('title', 'Untitled')}** (Relevance: {score:.0%})\n"
                f"Category: {doc.get('category', 'N/A')} | State: {doc.get('state', 'N/A')}\n"
                f"{content}"
            )

        if not results:
            return f"No highly relevant policies found for: '{query}'. Try rephrasing or broadening your search."

        return "\n\n---\n\n".join(results)

    except Exception as e:
        logger.error("Policy search error: %s", e)
        return f"Error searching policies: {str(e)}. Please try again."
