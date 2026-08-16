"""The deterministic offline agent stand-in, now over the Aldercrest KB.

A keyword model that routes a message to a tool (no LLM), and a keyword-overlap
retriever over `data/kb/` so `retrieve_clause` answers with a real cited chunk
with no database and no keys. Demo wiring — the live hybrid pipeline plugs in
behind the same interface once the credentials checkpoint clears.

Three properties matter beyond "it finds something":
  * **sample records are unreachable** — the offline retriever *is* the retrieval
    index offline, so the two-store boundary has to hold here too (AD-CL-023).
  * **the `aud` filter works** — audience comes from the session, and an
    ops-only chunk must not surface for a back-office one.
  * **citations carry their provenance** — a cited chunk arrives with the
    citation style its `data=` marking implies.
"""

from src.corpus.provenance import CITE_SOURCE
from src.web.console.offline_agent import KeywordModel, build_offline_retriever


# --- the keyword model (unchanged; WL-88213 is Phase 2's to retire) -------

def test_keyword_model_routes_a_claim_question_to_retrieve_clause():
    call = KeywordModel(policy_no="WL-88213").select("how do they claim?", [])
    assert call.name == "retrieve_clause"
    assert call.args["query"] == "how do they claim?"


def test_keyword_model_routes_a_balance_question_to_history():
    call = KeywordModel(policy_no="WL-88213").select("what's their balance?", [])
    assert call.name == "get_transaction_history"
    assert call.args["policy_no"] == "WL-88213"


def test_keyword_model_routes_a_raise_request_to_raise_case():
    call = KeywordModel(policy_no="WL-88213").select("please raise a claim for them", [])
    assert call.name == "raise_case"
    assert call.args["policy_no"] == "WL-88213"


# --- retrieval over the Aldercrest corpus --------------------------------

def test_the_retriever_finds_the_governing_aldercrest_chunk():
    retrieve = build_offline_retriever()

    ctx = retrieve("missed premium grace period lapse")

    assert ctx.found is True
    # 01-WOL:3.10 — "Premium arrears, grace period, lapse and reinstatement"
    assert "01-WOL:3.10" in [c.chunk_id for c in ctx.clauses]


def test_the_retriever_finds_a_bond_tax_chunk():
    ctx = build_offline_retriever()("top-slicing relief on a chargeable gain")

    assert ctx.found is True
    assert "02-BOND:4.4" in [c.chunk_id for c in ctx.clauses]


def test_an_unrelated_query_finds_nothing():
    ctx = build_offline_retriever()("banana spaceship zebra")
    assert ctx.found is False
    assert ctx.clauses == []


def test_a_citation_is_keyed_by_chunk_id():
    ctx = build_offline_retriever()("top-slicing relief on a chargeable gain")
    assert all(":" in c.chunk_id for c in ctx.clauses)


def test_a_citation_carries_its_document_and_type():
    ctx = build_offline_retriever()("top-slicing relief on a chargeable gain")
    cited = next(c for c in ctx.clauses if c.chunk_id == "02-BOND:4.4")
    assert cited.doc == "02-BOND"
    assert cited.clause_type == "tax_rule"


def test_a_citation_carries_its_provenance_style():
    # 02-BOND:4.4 is data=real — real UK tax law, so the answer cites the source.
    ctx = build_offline_retriever()("top-slicing relief on a chargeable gain")
    cited = next(c for c in ctx.clauses if c.chunk_id == "02-BOND:4.4")
    assert cited.citation_style == CITE_SOURCE


def test_a_citation_shows_its_heading_so_the_quote_is_locatable():
    ctx = build_offline_retriever()("top-slicing relief on a chargeable gain")
    cited = next(c for c in ctx.clauses if c.chunk_id == "02-BOND:4.4")
    assert "Top-slicing relief" in cited.text


def test_top_k_caps_the_result():
    ctx = build_offline_retriever(top_k=2)("premium grace period lapse")
    assert len(ctx.clauses) <= 2


# --- the two-store boundary holds offline (AD-CL-023) --------------------

def test_no_sample_record_is_ever_retrievable():
    # Query the sample records' own content; they still must not come back.
    retrieve = build_offline_retriever()
    for query in ("synthetic policy record sum assured",
                  "Kappa Retirement Account bypass trust nomination",
                  "sample policy record holder date of birth"):
        refs = [c.chunk_id for c in retrieve(query).clauses]
        assert "01-WOL:III.4" not in refs
        assert "02-BOND:III.4" not in refs
        assert "03-PEN:III.4" not in refs


# --- the aud filter ------------------------------------------------------

def test_without_a_filter_an_ops_chunk_is_reachable():
    # The control for the test below: this query does reach ops-only content.
    ctx = build_offline_retriever()("operating hours escalation windows on call")
    assert "07-RUNBOOK:1.2" in [c.chunk_id for c in ctx.clauses]


def test_a_back_office_retriever_never_returns_an_ops_only_chunk():
    retrieve = build_offline_retriever(aud="back_office")

    ctx = retrieve("operating hours escalation windows on call")

    assert "07-RUNBOOK:1.2" not in [c.chunk_id for c in ctx.clauses]
    assert all(c.aud in ("back_office", "all") for c in ctx.clauses)


def test_an_audience_filter_keeps_the_shared_chunks():
    # `aud=all` content is everyone's — filtering must not hide it.
    ctx = build_offline_retriever(aud="back_office")(
        "top-slicing relief on a chargeable gain")
    assert ctx.found is True
    assert "02-BOND:4.4" in [c.chunk_id for c in ctx.clauses]


def test_an_ops_retriever_sees_the_ops_chunk():
    ctx = build_offline_retriever(aud="ops")(
        "operating hours escalation windows on call")
    assert "07-RUNBOOK:1.2" in [c.chunk_id for c in ctx.clauses]
