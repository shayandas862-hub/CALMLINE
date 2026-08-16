# MIT License — Copyright (c) 2026 Shayan Das
# Adapted from the author's earlier original work
# (vendor/secondbrain/query_reranker.py). Reranks ClauseHits instead of the
# multi-tenant SearchResult; the threshold-based empty return (the retrieval-
# level refusal signal) and the injectable async client are preserved.
"""Cohere Rerank 3 — cross-encoder reranking with threshold-based refusal.

Sends the query and clause texts to Cohere; keeps hits whose relevance clears
the threshold (default 0.3); returns the top-k, ordered by relevance. If
nothing clears the bar, returns [] — the caller treats that as "nothing found"
and the agent refuses. Inject `_client` in tests.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from src.retrieval.hybrid_search import ClauseHit

_RERANK_MODEL = "rerank-v3.5"
_DEFAULT_THRESHOLD = 0.3
_DEFAULT_TOP_K = 8


def _default_client() -> Any:
    import cohere

    from src.config import load_config

    return cohere.AsyncClient(api_key=load_config().COHERE_API_KEY)


async def rerank(
    query: str,
    hits: list[ClauseHit],
    *,
    threshold: float = _DEFAULT_THRESHOLD,
    top_k: int = _DEFAULT_TOP_K,
    _client: Any = None,
) -> list[ClauseHit]:
    """Rerank `hits` for `query`; return survivors (score replaced by relevance).

    Returns [] when nothing clears `threshold` — the caller should refuse.
    """
    if not hits:
        return []

    client = _client or _default_client()
    response = await client.rerank(
        query=query,
        documents=[h.text for h in hits],
        model=_RERANK_MODEL,
        return_documents=False,
    )

    passing = [item for item in response.results if item.relevance_score >= threshold]
    if not passing:
        return []

    return [
        dataclasses.replace(hits[item.index], score=item.relevance_score)
        for item in passing[:top_k]
    ]
