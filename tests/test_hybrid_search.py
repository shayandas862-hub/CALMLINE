"""Single-tenant hybrid search: vector + fulltext, RRF-merged, filter-then-search.

Retrieval is **filter-then-search**, not search-alone (`data/kb/README.md` §4):
the audience comes from the server-side session and the document set from the
policy's product prefix, and both are applied *before* similarity ranking.

The filter is enforced twice on purpose — pushed down to the searcher for the
efficiency, and re-checked on the rows that come back so a searcher that ignores
it cannot leak a restricted chunk. Role enforcement does not depend on a
component remembering to cooperate.
"""

import asyncio

from src import constants
from src.retrieval.hybrid_search import (
    ClauseHit,
    RetrievalFilters,
    hybrid_search,
)


def _row(cid, ref, *, doc="term_life", aud="all"):
    return {"id": cid, "doc": doc, "chunk_id": ref, "aud": aud,
            "clause_type": "coverage", "text": f"text of {ref}"}


class StubDB:
    """Records the query it was embedded/searched with; returns fixed rankings."""
    def __init__(self, vector_rows, fulltext_rows):
        self._v = vector_rows
        self._f = fulltext_rows
        self.seen_query_text = None
        self.seen_filters = None

    async def vector_search(self, query_vec, *, limit=30, filters=None):
        self.seen_filters = filters
        return self._v[:limit]

    async def fulltext_search(self, query_text, *, limit=30, filters=None):
        self.seen_query_text = query_text
        self.seen_filters = filters
        return self._f[:limit]


class UncooperativeDB(StubDB):
    """A searcher that accepts the filter and ignores it — the leak we guard."""
    async def vector_search(self, query_vec, *, limit=30, filters=None):
        self.seen_filters = filters
        return self._v[:limit]

    async def fulltext_search(self, query_text, *, limit=30, filters=None):
        self.seen_filters = filters
        return self._f[:limit]


def _embedder_capturing(sink):
    def _e(texts):
        sink.append(texts[0])
        return [[0.1, 0.2, 0.3]]
    return _e


def test_returns_clause_hits_merged_by_rrf():
    # clause "c2" appears in BOTH lists → should rank first after RRF
    db = StubDB(
        vector_rows=[_row("c1", "TL-1.1"), _row("c2", "TL-4.2")],
        fulltext_rows=[_row("c2", "TL-4.2"), _row("c3", "TL-9.1")],
    )
    hits = asyncio.run(hybrid_search("grace period", _embedder=lambda t: [[0.0]], _db=db))
    assert all(isinstance(h, ClauseHit) for h in hits)
    assert hits[0].chunk_id == "TL-4.2"
    assert {h.chunk_id for h in hits} == {"TL-1.1", "TL-4.2", "TL-9.1"}


def test_query_is_embedded_with_the_query_prefix():
    sink = []
    db = StubDB([_row("c1", "TL-1.1")], [])
    asyncio.run(hybrid_search("missed payment", _embedder=_embedder_capturing(sink), _db=db))
    assert sink == [constants.QUERY_PREFIX + "missed payment"]


def test_fulltext_gets_the_raw_query_not_the_prefixed_one():
    db = StubDB([], [_row("c1", "TL-1.1")])
    asyncio.run(hybrid_search("missed payment", _embedder=lambda t: [[0.0]], _db=db))
    assert db.seen_query_text == "missed payment"


def test_top_k_is_respected():
    rows = [_row(f"c{i}", f"TL-{i}.0") for i in range(10)]
    db = StubDB(rows, [])
    hits = asyncio.run(hybrid_search("x", top_k=3, _embedder=lambda t: [[0.0]], _db=db))
    assert len(hits) == 3


def test_no_results_yields_empty():
    db = StubDB([], [])
    hits = asyncio.run(hybrid_search("nothing", _embedder=lambda t: [[0.0]], _db=db))
    assert hits == []


def test_hybrid_search_is_single_tenant_no_user_id():
    # Calling with only a query (no user_id) must work — the multi-tenant
    # predicate from the source system was stripped.
    db = StubDB([_row("c1", "TL-1.1")], [])
    hits = asyncio.run(hybrid_search("q", _embedder=lambda t: [[0.0]], _db=db))
    assert hits[0].chunk_id == "TL-1.1"


# --- RetrievalFilters -----------------------------------------------------

def test_an_audience_admits_its_own_chunks_and_the_shared_ones():
    # `aud ∈ {audience, "all"}` — the shared rules must stay visible.
    assert RetrievalFilters(aud="back_office").audiences == ("back_office", "all")


def test_no_audience_means_no_audience_restriction():
    assert RetrievalFilters().audiences == ()
    assert RetrievalFilters().restricts is False


def test_a_filter_with_either_dimension_restricts():
    assert RetrievalFilters(aud="ops").restricts is True
    assert RetrievalFilters(docs=frozenset({"03-PEN"})).restricts is True


# --- the SQL projection (parameterised — never interpolated) -------------

def test_an_unrestricted_filter_produces_no_predicate():
    clause, params = RetrievalFilters().sql_predicate(3)
    assert clause == ""
    assert params == []


def test_an_audience_filter_becomes_a_parameterised_any():
    clause, params = RetrievalFilters(aud="back_office").sql_predicate(3)
    assert clause == "aud = ANY($3)"
    assert params == [["back_office", "all"]]


def test_a_doc_filter_becomes_a_parameterised_any():
    clause, params = RetrievalFilters(docs=frozenset({"03-PEN"})).sql_predicate(3)
    assert clause == "doc = ANY($3)"
    assert params == [["03-PEN"]]


def test_both_dimensions_are_anded_and_numbered_in_order():
    filters = RetrievalFilters(aud="ops", docs=frozenset({"05-OPS", "03-PEN"}))

    clause, params = filters.sql_predicate(3)

    assert clause == "aud = ANY($3) AND doc = ANY($4)"
    assert params == [["ops", "all"], ["03-PEN", "05-OPS"]]


def test_the_predicate_starts_at_whatever_parameter_index_is_free():
    clause, _ = RetrievalFilters(aud="ops").sql_predicate(7)
    assert clause == "aud = ANY($7)"


def test_doc_parameters_are_sorted_so_the_sql_is_deterministic():
    # A frozenset iterates in arbitrary order; the query text must not.
    docs = frozenset({"05-OPS", "01-WOL", "03-PEN"})
    _, params = RetrievalFilters(docs=docs).sql_predicate(1)
    assert params == [["01-WOL", "03-PEN", "05-OPS"]]


def test_no_filter_value_is_ever_interpolated_into_the_sql():
    # Server-derived or not, values go through parameters.
    clause, params = RetrievalFilters(
        aud="back_office'; drop table kb_chunks; --").sql_predicate(1)
    assert "drop table" not in clause
    assert params[0][0] == "back_office'; drop table kb_chunks; --"


# --- the filter reaches the searcher (filter-then-search) ----------------

def test_the_filter_is_pushed_down_to_both_searches():
    db = StubDB([_row("c1", "TL-1.1")], [_row("c1", "TL-1.1")])
    filters = RetrievalFilters(aud="back_office", docs=frozenset({"term_life"}))

    asyncio.run(hybrid_search("q", filters=filters,
                              _embedder=lambda t: [[0.0]], _db=db))

    assert db.seen_filters == filters


def test_no_filter_is_passed_when_none_is_given():
    db = StubDB([_row("c1", "TL-1.1")], [])
    asyncio.run(hybrid_search("q", _embedder=lambda t: [[0.0]], _db=db))
    assert db.seen_filters is None


# --- the filter is enforced on what comes back ---------------------------

def test_a_back_office_query_never_retrieves_an_ops_only_chunk():
    # The spec's done criterion, and the reason the guard is doubled: this
    # searcher returns the ops chunk regardless of the filter it was handed.
    db = UncooperativeDB(
        vector_rows=[_row("ops1", "OPS-1.1", aud="ops"),
                     _row("shared", "TL-1.1", aud="all")],
        fulltext_rows=[_row("bo1", "BO-2.2", aud="back_office")],
    )

    hits = asyncio.run(hybrid_search(
        "q", filters=RetrievalFilters(aud="back_office"),
        _embedder=lambda t: [[0.0]], _db=db))

    refs = {h.chunk_id for h in hits}
    assert "OPS-1.1" not in refs, "an ops-only chunk reached a back-office session"
    assert refs == {"TL-1.1", "BO-2.2"}


def test_a_row_that_declares_no_audience_is_refused_when_filtering():
    # Absent metadata is not permission. Fail closed.
    db = UncooperativeDB([{"id": "x", "doc": "term_life", "chunk_id": "TL-9.9",
                           "clause_type": "coverage", "text": "no aud field"}], [])

    hits = asyncio.run(hybrid_search(
        "q", filters=RetrievalFilters(aud="back_office"),
        _embedder=lambda t: [[0.0]], _db=db))

    assert hits == []


def test_a_doc_filter_keeps_only_the_named_documents():
    db = UncooperativeDB(
        vector_rows=[_row("p", "PEN-1", doc="03-PEN"),
                     _row("b", "BOND-1", doc="02-BOND"),
                     _row("o", "OPS-1", doc="05-OPS")],
        fulltext_rows=[],
    )

    hits = asyncio.run(hybrid_search(
        "q", filters=RetrievalFilters(docs=frozenset({"03-PEN", "05-OPS"})),
        _embedder=lambda t: [[0.0]], _db=db))

    assert {h.doc for h in hits} == {"03-PEN", "05-OPS"}


def test_the_two_dimensions_apply_together():
    db = UncooperativeDB(
        vector_rows=[_row("keep", "PEN-1", doc="03-PEN", aud="back_office"),
                     _row("wrongdoc", "BOND-1", doc="02-BOND", aud="back_office"),
                     _row("wrongaud", "PEN-2", doc="03-PEN", aud="ops")],
        fulltext_rows=[],
    )

    hits = asyncio.run(hybrid_search(
        "q", filters=RetrievalFilters(aud="back_office", docs=frozenset({"03-PEN"})),
        _embedder=lambda t: [[0.0]], _db=db))

    assert [h.chunk_id for h in hits] == ["PEN-1"]


def test_filtering_everything_out_yields_empty_not_an_error():
    db = UncooperativeDB([_row("o", "OPS-1", aud="ops")], [])
    hits = asyncio.run(hybrid_search(
        "q", filters=RetrievalFilters(aud="customer"),
        _embedder=lambda t: [[0.0]], _db=db))
    assert hits == []


# --- the hit carries what a citation needs -------------------------------

def test_a_hit_carries_its_audience_and_citation_style():
    db = StubDB([{**_row("c1", "02-BOND:4.1", doc="02-BOND", aud="all"),
                  "citation_style": "cite_source"}], [])

    hits = asyncio.run(hybrid_search("q", _embedder=lambda t: [[0.0]], _db=db))

    assert hits[0].aud == "all"
    assert hits[0].citation_style == "cite_source"


def test_a_hit_without_a_citation_style_reports_none_rather_than_guessing():
    # A wrong default here is a mis-citation in a regulated answer.
    db = StubDB([_row("c1", "TL-1.1")], [])
    hits = asyncio.run(hybrid_search("q", _embedder=lambda t: [[0.0]], _db=db))
    assert hits[0].citation_style is None
