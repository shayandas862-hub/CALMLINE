"""Cohere Rerank 3 wrapper — cross-encoder reranking with threshold-based refusal.

Flow:
  1. Send query + chunk contents to Cohere Rerank (model rerank-v3.5).
  2. Filter results to those with relevance_score >= threshold (default 0.3).
  3. If nothing survives → return [] to signal retrieval refusal upstream.
  4. Otherwise return the top_k survivors (default 8), ordered by score desc.

Inject _client in tests to avoid real Cohere API calls.
_client must expose rerank(*, query, documents, model, return_documents) and
return an object whose .results is a list of items with .index and .relevance_score.
"""
from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.observability.tracer import _NoopTrace
from app.query.hybrid_search import SearchResult


_RERANK_MODEL = "rerank-v3.5"
_DEFAULT_THRESHOLD = 0.3
_DEFAULT_TOP_K = 8


def _default_client() -> Any:
    import cohere
    # AsyncClient — BUG #9 fix. Sync cohere.Client blocks the event loop.
    return cohere.AsyncClient(api_key=get_settings().COHERE_API_KEY)


async def rerank(
    query: str,
    results: list[SearchResult],
    *,
    threshold: float = _DEFAULT_THRESHOLD,
    top_k: int = _DEFAULT_TOP_K,
    _client: Any = None,
    _trace: Any = None,
) -> list[SearchResult]:
    """Rerank *results* for *query* and apply threshold-based refusal.

    Args:
        query: The user query string.
        results: Candidate chunks from hybrid search (typically top 20).
        threshold: Minimum relevance_score to keep a result (default 0.3).
        top_k: Maximum results to return after filtering (default 8).
        _client: Injectable Cohere client; uses real client when omitted.
        _trace: Langfuse trace object; no-ops when None.

    Returns:
        Reranked list of SearchResult (score replaced with Cohere relevance).
        Returns [] when no results survive the threshold — caller should refuse.
    """
    if not results:
        return []

    trace = _trace or _NoopTrace()
    client = _client or _default_client()

    with trace.span("rerank", input={"query": query, "n_candidates": len(results)}):
        documents = [r.content for r in results]

        response = await client.rerank(
            query=query,
            documents=documents,
            model=_RERANK_MODEL,
            return_documents=False,
        )

        # Cohere returns results sorted descending by relevance_score already.
        passing = [
            item for item in response.results
            if item.relevance_score >= threshold
        ]

        if not passing:
            return []

        reranked: list[SearchResult] = []
        for item in passing[:top_k]:
            src = results[item.index]
            reranked.append(
                SearchResult(
                    id=src.id,
                    item_id=src.item_id,
                    user_id=src.user_id,
                    content=src.content,
                    metadata=src.metadata,
                    chunk_index=src.chunk_index,
                    score=item.relevance_score,
                )
            )

    return reranked
