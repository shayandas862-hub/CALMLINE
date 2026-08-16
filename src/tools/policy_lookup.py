"""The policy-lookup tool — the one retrieval entry point the agent calls.

Composes the vendored Layer-1 pipeline, now filter-then-search end to end:

    hybrid search (filtered) → Cohere rerank → MMR diversity → cited assembly

Both halves of AD-CL-025 meet here — **filter for the common case, MMR for the
cross-product one**. A pension question filters to the pension document and gets
the pension copy of a shared rule; a question that genuinely spans products
cannot be filtered, so MMR collapses the four near-identical copies the KB
carries by design and spends the context window on something else.

Returns a `RetrievedContext` that is either `found` (with the clauses to cite,
each carrying its citation style) or not — the not-found signal is how the agent
knows to refuse rather than answer from general knowledge. Inject
`_search`/`_rerank` in tests.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from src.retrieval.assemble import RetrievedContext, assemble
from src.retrieval.hybrid_search import ClauseHit, RetrievalFilters, hybrid_search
from src.retrieval.mmr import mmr
from src.retrieval.rerank import rerank

SearchFn = Callable[..., Awaitable[list[ClauseHit]]]
RerankFn = Callable[[str, list[ClauseHit]], Awaitable[list[ClauseHit]]]

# Rerank a wider slate than we keep, so MMR has room to swap a near-duplicate
# out for something that adds information.
_RERANK_POOL = 20


async def policy_lookup(
    query: str,
    *,
    filters: RetrievalFilters | None = None,
    top_k: int = 8,
    diversify: bool = True,
    _search: SearchFn | None = None,
    _rerank: RerankFn | None = None,
) -> RetrievedContext:
    """Look up KB chunks for `query`; return cited context or typed empty.

    `filters` is the session's audience and document scope, derived server-side.
    `diversify` applies MMR; turn it off when the caller wants the reranker's
    ordering untouched.
    """
    search = _search or (lambda q, *, filters=None: hybrid_search(
        q, filters=filters, top_k=_RERANK_POOL))
    rerank_fn = _rerank or (lambda q, hits: rerank(q, hits, top_k=_RERANK_POOL))

    hits = await search(query, filters=filters)
    if not hits:
        return assemble([])

    reranked = await rerank_fn(query, hits)
    if not reranked:
        return assemble([])

    ranked = mmr(reranked, top_k=top_k) if diversify else reranked[:top_k]
    return assemble(ranked, max_clauses=top_k)
