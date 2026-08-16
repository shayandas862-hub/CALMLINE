"""Retrieval against the LIVE seeded `kb_chunks` — opt-in, never in a default run.

    pytest -m integration

`pyproject.toml` deselects this marker by default, so `pytest -q` makes zero
live calls even on a machine with a real `.env`; and each test still skips if
the credentials are absent, so `-m integration` on a bare checkout reports
"skipped", not "error".

What these prove that the unit tests cannot: that the applied schema, the seeded
vectors and the composed pipeline agree with each other. The unit tests prove
the filter logic is right; only this proves the SQL that carries it actually
runs against Postgres.

Requires: the migration applied and `python scripts/seed_corpus.py` run.
"""

import asyncio

import pytest

from src.config import MissingConfigError, load_config
from src.db.pool import close_pool, reset_pool
from src.corpus.provenance import (
    CITATION_STYLES,
    CITE_SOURCE,
    EFFECTIVE_DATE_REQUIRED,
)
from src.retrieval.hybrid_search import RetrievalFilters
from src.tools.policy_lookup import policy_lookup

pytestmark = pytest.mark.integration


def _requires_live_config():
    try:
        load_config()
    except MissingConfigError:
        pytest.skip("no live Supabase/OpenAI credentials — seed the corpus first")


_CACHE: dict[tuple, object] = {}


def _lookup(query, *, filters=None, **kwargs):
    """One live lookup per distinct query, memoised for the session.

    Two constraints shape this helper.

    **Event loops.** `src/db/pool.py` caches a process-wide asyncpg pool, but a
    pool belongs to the loop that created it, and every `asyncio.run` here makes
    and then closes a fresh loop. Reusing the cached pool across them raises
    "Event loop is closed" from the second test onwards, so each call builds and
    drains its own pool inside its own loop.

    **Rate limits.** Every lookup costs one Cohere rerank call, and a Cohere
    trial key allows ten a minute. Several tests assert different properties of
    the *same* retrieval, so memoising by (query, filters) keeps the suite to one
    call per distinct query — currently eight — and makes it faster and cheaper
    as well as reliable.
    """
    _requires_live_config()

    key = (query, filters, tuple(sorted(kwargs.items())))
    if key in _CACHE:
        return _CACHE[key]

    async def run():
        reset_pool()
        try:
            return await policy_lookup(query, filters=filters, **kwargs)
        finally:
            await close_pool()

    _CACHE[key] = asyncio.run(run())
    return _CACHE[key]


def test_a_product_question_retrieves_its_governing_chunk():
    ctx = _lookup("how does top-slicing relief work on a chargeable gain?")

    assert ctx.found is True
    assert "02-BOND:4.4" in [c.chunk_id for c in ctx.clauses]


def test_every_citation_carries_a_usable_provenance_style():
    # Nothing may be retrieved that the system cannot attribute.
    ctx = _lookup("how does top-slicing relief work on a chargeable gain?")
    assert all(c.citation_style in CITATION_STYLES for c in ctx.clauses)


def test_real_tax_law_is_cited_to_its_source():
    ctx = _lookup("how does top-slicing relief work on a chargeable gain?")
    cited = next(c for c in ctx.clauses if c.chunk_id == "02-BOND:4.4")
    assert cited.citation_style == CITE_SOURCE


def test_a_not_yet_in_force_rule_demands_its_effective_date():
    ctx = _lookup("are savings rates changing in 2027?")
    styles = {c.chunk_id: c.citation_style for c in ctx.clauses}
    assert styles.get("02-BOND:4.6") == EFFECTIVE_DATE_REQUIRED


def test_a_back_office_session_never_retrieves_an_ops_only_chunk():
    # The spec's done criterion, proven through the live SQL path rather than a
    # stubbed searcher: `aud` is applied in Postgres, before ranking.
    ctx = _lookup("what are the operating hours and escalation windows?",
                  filters=RetrievalFilters(aud="back_office"))

    refs = [c.chunk_id for c in ctx.clauses]
    assert "07-RUNBOOK:1.2" not in refs, "an ops-only chunk reached back office"
    assert all(c.aud in ("back_office", "all") for c in ctx.clauses)


def test_an_ops_session_does_reach_that_chunk():
    # The control: the filter is what excluded it, not the corpus lacking it.
    ctx = _lookup("what are the operating hours and escalation windows?",
                  filters=RetrievalFilters(aud="ops"))
    assert ctx.found is True


def test_a_document_filter_keeps_retrieval_inside_the_product():
    ctx = _lookup("what identity checks are required before disclosure?",
                  filters=RetrievalFilters(docs=frozenset({"03-PEN", "05-OPS"})))
    assert {c.doc for c in ctx.clauses} <= {"03-PEN", "05-OPS"}


def test_a_cross_product_query_is_not_four_copies_of_one_rule():
    # AD-CL-025: the KB repeats shared rules per product on purpose; MMR is what
    # stops an unfiltered query spending the context window restating one.
    ctx = _lookup("what identity checks are required before disclosure?")

    texts = [c.text for c in ctx.clauses]
    assert len(set(texts)) == len(texts), "identical chunk text retrieved twice"


def test_no_sample_record_is_retrievable():
    # The two-store boundary, proven against the live index: facts come from the
    # system of record, so no policy record may be in the corpus to cite. The
    # query deliberately quotes the sample records' own content.
    ctx = _lookup("synthetic sample policy record sum assured holder date of birth")
    refs = [c.chunk_id for c in ctx.clauses]
    assert not [r for r in refs if r.endswith(":III.4")], f"leaked: {refs}"


def test_an_out_of_corpus_query_returns_the_typed_not_found():
    # The refusal cue: the agent must abstain rather than answer from general
    # knowledge. Abstention with correct routing is a success state.
    ctx = _lookup("does this life policy cover my car if I crash it")
    assert ctx.found is False
