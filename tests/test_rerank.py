"""Cohere rerank with threshold-as-refusal: below the bar → typed empty."""

import asyncio

from src.retrieval.hybrid_search import ClauseHit
from src.retrieval.rerank import rerank


def _hit(ref, score=0.0):
    return ClauseHit(clause_id=ref, doc="term_life", chunk_id=ref,
                     clause_type="coverage", text=f"text {ref}", score=score)


class FakeCohere:
    """Async Cohere stub: returns the given relevance scores, sorted desc."""
    def __init__(self, scores):
        self._scores = scores
        self.seen = {}

    async def rerank(self, *, query, documents, model, return_documents=False):
        self.seen = {"query": query, "n": len(documents), "model": model}
        results = [type("I", (), {"index": i, "relevance_score": s})
                   for i, s in enumerate(self._scores)]
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return type("R", (), {"results": results})


def test_orders_by_relevance_and_replaces_score():
    hits = [_hit("TL-1.1"), _hit("TL-4.2"), _hit("TL-9.1")]
    client = FakeCohere([0.2, 0.9, 0.5])
    out = asyncio.run(rerank("q", hits, threshold=0.3, _client=client))
    assert [h.chunk_id for h in out] == ["TL-4.2", "TL-9.1"]  # 0.2 dropped below threshold
    assert out[0].score == 0.9


def test_below_threshold_returns_typed_empty():
    hits = [_hit("TL-1.1"), _hit("TL-4.2")]
    client = FakeCohere([0.1, 0.2])
    out = asyncio.run(rerank("q", hits, threshold=0.3, _client=client))
    assert out == []  # the retrieval-level refusal signal


def test_empty_input_short_circuits_without_calling_cohere():
    called = FakeCohere([])
    out = asyncio.run(rerank("q", [], _client=called))
    assert out == [] and called.seen == {}


def test_top_k_caps_survivors():
    hits = [_hit(f"TL-{i}.0") for i in range(6)]
    client = FakeCohere([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    out = asyncio.run(rerank("q", hits, threshold=0.3, top_k=3, _client=client))
    assert len(out) == 3
