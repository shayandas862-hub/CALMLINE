"""The policy-lookup tool: embed → search → rerank → assemble, or typed empty.

This is the single function the agent (Phase 4) and the MCP server (Phase 9)
both call. Composition is unit-tested with stubbed search/rerank — no DB, no
network, no live models.
"""

import asyncio

from src.retrieval.assemble import RetrievedContext
from src.retrieval.hybrid_search import ClauseHit
from src.tools.policy_lookup import policy_lookup


def _hit(ref, score=0.5):
    return ClauseHit(clause_id=ref, doc="term_life", chunk_id=ref,
                     clause_type="coverage", text=f"text {ref}", score=score)


def test_returns_cited_context_when_clauses_survive():
    async def fake_search(query, *, filters=None):
        return [_hit("TL-4.2"), _hit("TL-1.1")]

    async def fake_rerank(query, hits):
        return hits[:1]

    ctx = asyncio.run(policy_lookup("grace period", _search=fake_search, _rerank=fake_rerank))
    assert isinstance(ctx, RetrievedContext)
    assert ctx.found is True
    assert ctx.clauses[0].chunk_id == "TL-4.2"


def test_empty_rerank_yields_typed_not_found():
    async def fake_search(query, *, filters=None):
        return [_hit("TL-4.2")]

    async def fake_rerank(query, hits):
        return []  # nothing cleared the relevance threshold

    ctx = asyncio.run(policy_lookup("does it cover my car", _search=fake_search, _rerank=fake_rerank))
    assert ctx.found is False
    assert ctx.clauses == []


def test_empty_search_yields_typed_not_found():
    async def fake_search(query, *, filters=None):
        return []

    async def fake_rerank(query, hits):
        raise AssertionError("rerank should not be called on empty search")

    ctx = asyncio.run(policy_lookup("nonsense", _search=fake_search, _rerank=fake_rerank))
    assert ctx.found is False


# --- v4 phase 1: audience filtering and diversity (AD-CL-025) ------------

def test_the_session_filter_is_passed_to_the_search():
    # "filter for the common case, MMR for cross-product" — both compose here,
    # in the one retrieval entry point the agent and the MCP server share.
    from src.retrieval.hybrid_search import RetrievalFilters

    seen = {}

    async def fake_search(query, *, filters=None):
        seen["filters"] = filters
        return [_hit("05-OPS:3.1")]

    async def fake_rerank(query, hits):
        return hits

    filters = RetrievalFilters(aud="back_office", docs=frozenset({"03-PEN"}))
    asyncio.run(policy_lookup("bank change", filters=filters,
                              _search=fake_search, _rerank=fake_rerank))

    assert seen["filters"] == filters


def test_no_filter_still_works():
    async def fake_search(query, *, filters=None):
        return [_hit("TL-4.2")]

    async def fake_rerank(query, hits):
        return hits

    ctx = asyncio.run(policy_lookup("q", _search=fake_search, _rerank=fake_rerank))
    assert ctx.found is True


def test_near_duplicate_hits_are_collapsed_by_diversity():
    # The per-product duplication: the same rule from three documents.
    rule = "Verify identity before disclosing any personal data to a caller."

    def dup(ref, doc, score):
        return ClauseHit(clause_id=ref, doc=doc, chunk_id=ref,
                         clause_type="procedure", text=rule, score=score)

    async def fake_search(query, *, filters=None):
        return [dup("01-WOL:6.1", "01-WOL", 0.90),
                dup("02-BOND:6.1", "02-BOND", 0.89),
                dup("03-PEN:6.1", "03-PEN", 0.88),
                _hit("05-OPS:14", 0.50)]

    async def fake_rerank(query, hits):
        return hits

    ctx = asyncio.run(policy_lookup("identity checks across products",
                                    top_k=2, _search=fake_search, _rerank=fake_rerank))

    refs = [c.chunk_id for c in ctx.clauses]
    assert len([r for r in refs if r.endswith(":6.1")]) == 1, "one copy is enough"
    assert "05-OPS:14" in refs


def test_diversity_can_be_turned_off():
    rule = "Verify identity before disclosing any personal data to a caller."

    def dup(ref, score):
        return ClauseHit(clause_id=ref, doc=ref.split(":")[0], chunk_id=ref,
                         clause_type="procedure", text=rule, score=score)

    async def fake_search(query, *, filters=None):
        return [dup("01-WOL:6.1", 0.90), dup("02-BOND:6.1", 0.89)]

    async def fake_rerank(query, hits):
        return hits

    ctx = asyncio.run(policy_lookup("q", diversify=False, top_k=2,
                                    _search=fake_search, _rerank=fake_rerank))
    assert len(ctx.clauses) == 2
