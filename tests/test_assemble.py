"""Citation assembly: dedup by chunk id, cap, typed found/not-found.

Assembly carries three things through from the retrieved chunk to the citation
the agent quotes, and all three come from **retrieval, never from the model**:

* **`citation_style`** — what makes the provenance rule enforceable at the point
  of use: real law gets its source URL, an Aldercrest invention gets labelled an
  operating standard, and a rule not yet in force gets its effective date stated.
  A citation that arrives without its style must say so rather than be assumed
  safe.
* **`version`** — what `stale_citation_rate` compares a cited chunk against.
  Dropped here until phase 5; without it the metric has nothing to compare
  (D-CL-056 retired).
* **`chunk_id`** — the KB's own name for the citation key. It was `clause_ref`
  through v3, which meant every consumer translated at its own boundary.
"""

from src.retrieval.assemble import RetrievedContext, assemble
from src.retrieval.hybrid_search import ClauseHit


def _hit(ref, score, citation_style=None, aud="all", version=1):
    return ClauseHit(clause_id=ref, doc="term_life", chunk_id=ref,
                     clause_type="coverage", text=f"text {ref}", score=score,
                     aud=aud, citation_style=citation_style, version=version)


def test_empty_hits_is_not_found():
    ctx = assemble([])
    assert isinstance(ctx, RetrievedContext)
    assert ctx.found is False and ctx.clauses == []


def test_found_context_carries_cited_clauses():
    ctx = assemble([_hit("TL-4.2", 0.9), _hit("TL-9.1", 0.5)])
    assert ctx.found is True
    assert [c.chunk_id for c in ctx.clauses] == ["TL-4.2", "TL-9.1"]
    assert ctx.clauses[0].text == "text TL-4.2"


def test_dedup_keeps_highest_scoring_occurrence():
    ctx = assemble([_hit("TL-4.2", 0.4), _hit("TL-4.2", 0.9), _hit("TL-1.1", 0.5)])
    refs = [c.chunk_id for c in ctx.clauses]
    assert refs.count("TL-4.2") == 1
    assert refs == ["TL-4.2", "TL-1.1"]  # ordered by score desc


def test_max_clauses_caps_output():
    hits = [_hit(f"TL-{i}.0", 1.0 - i * 0.1) for i in range(8)]
    ctx = assemble(hits, max_clauses=3)
    assert len(ctx.clauses) == 3


# --- citation_style carries through --------------------------------------

def test_the_citation_style_reaches_the_citation():
    ctx = assemble([_hit("02-BOND:4.1", 0.9, citation_style="cite_source")])
    assert ctx.clauses[0].citation_style == "cite_source"


def test_each_citation_keeps_its_own_style():
    ctx = assemble([
        _hit("02-BOND:4.1", 0.9, citation_style="cite_source"),
        _hit("05-OPS:14", 0.8, citation_style="aldercrest_standard"),
        _hit("03-PEN:14.3", 0.7, citation_style="effective_date_required"),
    ])
    assert [c.citation_style for c in ctx.clauses] == [
        "cite_source", "aldercrest_standard", "effective_date_required",
    ]


def test_a_missing_style_stays_none_rather_than_being_assumed():
    # An unknown provenance must be visible to the caller, never defaulted to a
    # style that would attribute an invention as though it were law.
    ctx = assemble([_hit("TL-4.2", 0.9)])
    assert ctx.clauses[0].citation_style is None


def test_the_audience_carries_through_too():
    ctx = assemble([_hit("05-OPS:17.3", 0.9, aud="back_office")])
    assert ctx.clauses[0].aud == "back_office"


def test_dedup_keeps_the_winning_hits_style():
    ctx = assemble([
        _hit("02-BOND:4.1", 0.4, citation_style="aldercrest_standard"),
        _hit("02-BOND:4.1", 0.9, citation_style="cite_source"),
    ])
    assert len(ctx.clauses) == 1
    assert ctx.clauses[0].citation_style == "cite_source"


# --- the citation key is chunk_id, the KB's own name for it ---------------

def test_the_citation_key_is_named_chunk_id():
    # `clause_ref` was the v3 name; every consumer translated at its own
    # boundary, and phase 5 is about to pin the name into a persisted schema.
    ctx = assemble([_hit("02-BOND:4.1", 0.9)])
    assert ctx.clauses[0].chunk_id == "02-BOND:4.1"


# --- version carries through (enables stale_citation_rate) ----------------

def test_the_version_reaches_the_citation():
    # Without this, `stale_citation_rate` has nothing to compare a cited chunk
    # against and the metric cannot be built at all.
    ctx = assemble([_hit("02-BOND:4.1", 0.9, version=3)])
    assert ctx.clauses[0].version == 3


def test_a_chunk_never_re_embedded_is_version_one():
    # Not a guessed default: `KbChunk.version` and the `kb_chunks` column both
    # declare 1, so a chunk that has never been re-embedded *is* version 1.
    ctx = assemble([_hit("02-BOND:4.1", 0.9)])
    assert ctx.clauses[0].version == 1


def test_dedup_keeps_the_winning_hits_version():
    # The surviving citation must carry the version of the row that survived,
    # or the freshness metric reads the loser's.
    ctx = assemble([
        _hit("02-BOND:4.1", 0.4, version=1),
        _hit("02-BOND:4.1", 0.9, version=7),
    ])
    assert len(ctx.clauses) == 1
    assert ctx.clauses[0].version == 7
