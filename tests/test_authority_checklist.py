"""v4 phase 2 · task 5 — the money-out pre-check, cited to Aldercrest.

The raise path used to cite `WL-1.2`, `WL-7.1`, `WL-3.1` and `TL-3.4` — clauses
from a corpus that no longer exists. Every requirement now names a real chunk in
`data/kb/`, resolved per product, so a reviewer can open the rule behind any
line of the pre-check.
"""

import pytest

from src.authority.checklist import money_out_checklist
from src.corpus.kb_parser import parse_kb
from src.records.models import gbp
from src.records.seed import build_seed_book


@pytest.fixture(scope="module")
def book():
    return build_seed_book(with_synthetics=False)


@pytest.fixture(scope="module")
def chunk_ids():
    return {chunk.chunk_id for chunk in parse_kb("data/kb")}


def _checklist(book, policy_no, amount=gbp(1_000)):
    return money_out_checklist(book, policy_no, amount_pence=amount)


# ── every citation resolves to a real chunk ──────────────────────────────
def test_every_cited_chunk_id_exists_in_the_corpus(book, chunk_ids):
    for policy_no in ("LP-20419876", "HB-40582213", "RA-77103428"):
        for row in _checklist(book, policy_no):
            assert row["clause_ref"] in chunk_ids, (
                f"{policy_no}: {row['clause_ref']} is not a chunk in data/kb/")


def test_no_requirement_cites_a_retired_harbour_and_vale_clause(book):
    for policy_no in ("LP-20419876", "HB-40582213", "RA-77103428"):
        for row in _checklist(book, policy_no):
            assert not row["clause_ref"].startswith(("WL-", "TL-", "EN-"))


def test_every_row_carries_a_requirement_and_a_verdict(book):
    for row in _checklist(book, "HB-40582213"):
        assert row["requirement"]
        assert row["verdict"] in {"pass", "fail"}


# ── the citations are resolved per product ───────────────────────────────
def test_a_bond_withdrawal_cites_the_bond_processing_rule(book):
    refs = {row["clause_ref"] for row in _checklist(book, "HB-40582213")}
    assert "02-BOND:II.8.2" in refs           # method selection and processing


def test_a_lifelong_protection_surrender_cites_its_own_rule(book):
    refs = {row["clause_ref"] for row in _checklist(book, "LP-20419876")}
    assert "05-OPS:8.4" in refs               # Lifelong Protection money out
    assert "02-BOND:II.8.2" not in refs       # not another product's rule


def test_a_pension_request_cites_the_pension_access_rule(book):
    refs = {row["clause_ref"] for row in _checklist(book, "RA-77103428")}
    assert "05-OPS:8.3" in refs               # Retirement Account — pension access


def test_every_product_cites_the_universal_controls_and_verification(book):
    for policy_no in ("LP-20419876", "HB-40582213", "RA-77103428"):
        refs = {row["clause_ref"] for row in _checklist(book, policy_no)}
        assert "05-OPS:8.1" in refs           # universal controls before any payment
        assert "05-OPS:3.2" in refs           # standard verification


# ── the verdicts are real, not decorative ────────────────────────────────
def test_a_pension_cash_withdrawal_fails_the_product_rule(book):
    # An RA pays out only through a benefit route.
    rows = _checklist(book, "RA-77103428")
    failed = [r for r in rows if r["verdict"] == "fail"]
    assert failed
    assert any("benefit route" in r["requirement"].lower() for r in failed)


def test_a_pension_request_through_a_benefit_route_passes_the_product_rule(book):
    rows = money_out_checklist(book, "RA-77103428", amount_pence=gbp(1_000),
                               route="ufpls")
    assert all(row["verdict"] == "pass" for row in rows)


def test_a_bond_withdrawal_within_value_passes_every_check(book):
    assert all(row["verdict"] == "pass"
               for row in _checklist(book, "HB-40582213", gbp(1_000)))


def test_a_withdrawal_beyond_the_policy_value_fails_the_sufficiency_check(book):
    rows = _checklist(book, "HB-40582213", gbp(10_000_000))
    failing = [r for r in rows if r["verdict"] == "fail"]
    assert len(failing) == 1
    assert "sufficient" in failing[0]["requirement"].lower()


def test_a_lapsed_policy_fails_the_in_force_check(book):
    lapsed = build_seed_book(with_synthetics=False)
    lapsed.update_policy("HB-40582213", actor="tester", source_ref="seed",
                         at="2026-07-13T00:00:00", status="lapsed")
    rows = money_out_checklist(lapsed, "HB-40582213", amount_pence=gbp(1_000))
    assert any(r["verdict"] == "fail" and "in force" in r["requirement"].lower()
               for r in rows)


def test_an_unknown_policy_raises(book):
    with pytest.raises(Exception):
        _checklist(book, "HB-99999999")
