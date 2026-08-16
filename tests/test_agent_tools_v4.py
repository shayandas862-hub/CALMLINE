"""v4 phase 4 · Task 2 — the toolbox the real agent gets.

Three changes, one theme: the tools stop being a thin pass-through to the stores
and start carrying the phase-3 rules with them.

  * ``get_valuation`` puts point-in-time valuation in the agent's hands, with
    ``as_at`` injected — the brief's target query asks what a policy was worth
    three months ago, and a tool that reads the clock cannot answer it twice the
    same way.
  * ``retrieve_clause`` gains a product filter and an operative date. It does
    **not** gain an ``aud`` parameter: the audience is the server's decision,
    bound when the retriever is built, and a model-facing ``aud`` would be a
    request for ops-only content dressed up as a search filter.
  * The record tools refuse without a live verification. The endpoints already
    refuse (D-CL-052); this is the layer beneath, so a tool reached by any other
    route still refuses.

The guard is applied when the tool is **bound**, not inside the record functions
themselves — ``src/casework/assembly.py`` calls those functions directly and is
not part of this phase, so their signatures must not move.
"""

from functools import partial

import pytest

from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.record_tools import get_valuation
from src.agent.tools.registry import Tool
from src.agent.tools.schemas import tool_definition
from src.records.models import gbp
from src.records.seed import build_seed_book
from src.retrieval.assemble import CitedClause, RetrievedContext
from src.web.console.offline_agent import build_offline_retriever

POLICY_NO = "LP-20419876"


# ── get_valuation: the past, read off the ledger ─────────────────────────

def test_get_valuation_answers_as_at_the_date_it_is_given():
    # Arrange
    book = build_seed_book()

    # Act
    out = get_valuation(book, POLICY_NO, "2026-04-12")

    # Assert
    assert out["found"] is True
    assert out["as_at"] == "2026-04-12"
    assert isinstance(out["value_pence"], int)


def test_get_valuation_reads_the_injected_date_not_the_clock():
    # Two different as_at values must be able to give two different answers,
    # which is only true if the date is genuinely used.
    # Arrange
    book = build_seed_book()

    # The policy's only ledger entry is dated 2016-05-01, so a date before it
    # must value at nothing and a date after it at the full balance.
    # Act
    early = get_valuation(book, POLICY_NO, "2015-01-01")
    today = get_valuation(book, POLICY_NO, "2026-04-12")

    # Assert
    assert early["value_pence"] == 0
    assert today["value_pence"] == gbp(46_210)


def test_get_valuation_formats_money_only_at_the_edge():
    # Arrange / Act
    out = get_valuation(build_seed_book(), POLICY_NO, "2026-04-12")

    # Assert
    assert out["value_pence"] == gbp(46_210)
    assert out["value"] == "£46,210.00"


def test_get_valuation_reports_an_unknown_policy_rather_than_raising():
    # Act
    out = get_valuation(build_seed_book(), "LP-00000000", "2026-04-12")

    # Assert
    assert out["found"] is False


# ── retrieve_clause: filters that narrow, never widen ────────────────────

def test_product_code_restricts_retrieval_to_that_products_document():
    # Arrange
    retriever = build_offline_retriever(aud="front_office")

    # Act
    out = retrieve_clause(retriever, "withdrawal", product_code="horizon_bond")

    # Assert
    assert out["clauses"], "expected the bond document to answer a withdrawal query"
    assert {c["doc"] for c in out["clauses"]} == {"02-BOND"}


def test_an_unknown_product_code_fails_loudly():
    # Silently returning everything would be a filter that quietly does nothing.
    # Arrange
    retriever = build_offline_retriever(aud="front_office")

    # Act / Assert
    with pytest.raises(ValueError, match="product"):
        retrieve_clause(retriever, "withdrawal", product_code="not_a_product")


def test_no_product_code_searches_every_document():
    # Arrange
    retriever = build_offline_retriever(aud="front_office")

    # Act
    out = retrieve_clause(retriever, "withdrawal")

    # Assert
    assert out["clauses"]


def test_the_operative_date_travels_with_the_result():
    # The loop needs it to apply AD-CL-032 — a rule not yet in force must be
    # cited with its effective date — so the tool has to carry it through.
    # Arrange
    retriever = build_offline_retriever(aud="front_office")

    # Act
    out = retrieve_clause(retriever, "withdrawal", operative_date="2026-04-12")

    # Assert
    assert out["operative_date"] == "2026-04-12"


def test_aud_is_not_a_parameter_the_model_can_fill_in():
    # The done criterion: an aud=ops chunk cannot appear in a front-office
    # answer. A model-facing `aud` would be exactly the request that breaks it.
    # Arrange
    tool = Tool("retrieve_clause", "search the rules",
                partial(retrieve_clause, build_offline_retriever(aud="front_office")))

    # Act
    properties = tool_definition(tool)["input_schema"]["properties"]

    # Assert
    assert "aud" not in properties
    assert set(properties) == {"query", "product_code", "operative_date"}


def test_an_ops_chunk_cannot_reach_a_front_office_answer():
    # Arrange
    retriever = build_offline_retriever(aud="front_office")

    # Act
    out = retrieve_clause(retriever, "quality assurance sampling ops")

    # Assert
    assert all(c["aud"] in ("front_office", "all") for c in out["clauses"])


def test_a_retriever_returning_nothing_is_not_an_error():
    # Arrange
    def _empty(query: str) -> RetrievedContext:
        return RetrievedContext(clauses=[])

    # Act
    out = retrieve_clause(_empty, "nothing matches this")

    # Assert
    assert out["found"] is False
    assert out["clauses"] == []


def test_the_product_filter_runs_after_retrieval_not_instead_of_it():
    # A filter that drops everything must say "found nothing", not pretend the
    # retriever failed.
    # Arrange
    def _one_bond_clause(query: str) -> RetrievedContext:
        return RetrievedContext(clauses=[CitedClause(
            chunk_id="02-BOND:4.9", doc="02-BOND", clause_type="procedure",
            text="withdrawal terms", score=1.0, aud="all")])

    # Act
    out = retrieve_clause(_one_bond_clause, "withdrawal",
                          product_code="lifelong_protection")

    # Assert
    assert out["found"] is False
    assert out["clauses"] == []
