"""The RecordStore interface + in-memory implementation, on the v4 shapes.

The store holds the book of business, the per-product detail that hangs off each
policy, and delegates every balance change to the ledger engine. In-memory now;
the same interface is backed by Postgres later.
"""

import pytest

from src.records.ledger import LedgerError
from src.records.models import Contact, Party, Policy, Transaction, gbp
from src.records.authorisations import (
    AuthorityRecord,
    BankMandate,
    MandateChange,
)
from src.records.products import (
    Allowance5Pct,
    ContributionSchedule,
    CoverComponent,
    FundHolding,
    HorizonBondTerms,
    PensionTax,
    MpaaStatus,
    RetirementAccountTerms,
)
from src.records.store import InMemoryRecordBook, RecordError

SEED = dict(actor="seed", source_ref="seed", at="2026-01-01T00:00:00")


def _book():
    book = InMemoryRecordBook()
    book.add_party(Party(party_id="PH-1001", name="Theta Meridian 12", dob="1954-02-11",
                         registered_address="14 Lattice Way, Demoford",
                         contact=Contact(phone="07700 900819",
                                         email="ph-1001@example.org", registered=True)),
                   **SEED)
    book.add_policy(Policy(policy_no="LP-20419876", product="lifelong_protection",
                           status="in_force", start_date="2016-05-01",
                           holder_party_id="PH-1001"), **SEED)
    return book


def _txn(kind, pounds, txn_id, policy_no="LP-20419876"):
    return Transaction(txn_id=txn_id, policy_no=policy_no, kind=kind,
                       amount_pence=gbp(pounds), reason="test", actor="tester",
                       at="2026-07-02T10:00:00")


# ── the book ─────────────────────────────────────────────────────────────
def test_get_policy_and_party_by_id():
    book = _book()
    assert book.get_policy("LP-20419876").product == "lifelong_protection"
    assert book.get_party("PH-1001").name == "Theta Meridian 12"


def test_get_unknown_policy_or_party_returns_none():
    assert _book().get_policy("LP-00000000") is None
    assert _book().get_party("PH-9999") is None


def test_list_policies_returns_everything_added():
    book = _book()
    book.add_policy(Policy(policy_no="HB-40582213", product="horizon_bond",
                           status="in_force", start_date="2019-03-01",
                           holder_party_id="PH-1001"), **SEED)
    assert {p.policy_no for p in book.list_policies()} == {"LP-20419876", "HB-40582213"}


def test_policies_for_party_finds_every_policy_a_party_holds():
    book = _book()
    book.add_policy(Policy(policy_no="HB-40582213", product="horizon_bond",
                           status="in_force", start_date="2019-03-01",
                           holder_party_id="PH-1001"), **SEED)
    assert len(book.policies_for_party("PH-1001")) == 2
    assert book.policies_for_party("PH-9999") == []


# ── the ledger, through the store ────────────────────────────────────────
def test_apply_transaction_persists_and_updates_the_value():
    book = _book()
    book.apply_transaction("LP-20419876", _txn("opening", 50_000, "T1"))
    book.apply_transaction("LP-20419876", _txn("withdrawal", 20_000, "T2"))
    assert book.current_value("LP-20419876") == gbp(30_000)
    assert len(book.history("LP-20419876")) == 2


def test_apply_transaction_for_unknown_policy_raises():
    with pytest.raises(RecordError):
        _book().apply_transaction("LP-00000000", _txn("opening", 1_000, "T1",
                                                      policy_no="LP-00000000"))


def test_overdraw_surfaces_as_a_ledger_error():
    book = _book()
    book.apply_transaction("LP-20419876", _txn("opening", 50_000, "T1"))
    with pytest.raises(LedgerError):
        book.apply_transaction("LP-20419876", _txn("withdrawal", 60_000, "T2"))


def test_history_and_value_of_a_fresh_policy_are_empty_and_zero():
    book = _book()
    assert book.history("LP-20419876") == ()
    assert book.current_value("LP-20419876") == 0


# ── per-product detail hangs off the policy ──────────────────────────────
def test_cover_component_is_stored_and_retrieved_per_policy():
    book = _book()
    cover = CoverComponent(policy_no="LP-20419876", sum_assured_pence=gbp(400_000),
                           basis=("reviewable", "unit_linked"), premium_pence=gbp(212.40))
    book.add_cover(cover, **SEED)
    assert book.get_cover("LP-20419876") is cover
    assert book.get_cover("HB-40582213") is None


def test_bond_terms_are_stored_and_retrieved_per_policy():
    book = _book()
    book.add_policy(Policy(policy_no="HB-40582213", product="horizon_bond",
                           status="in_force", start_date="2019-03-01",
                           holder_party_id="PH-1001"), **SEED)
    terms = HorizonBondTerms(policy_no="HB-40582213", invested_pence=gbp(120_000),
                             invested_date="2019-03-01", segments_total=1_000,
                             segments_remaining=1_000,
                             allowance_5pct=Allowance5Pct(used_pence=gbp(36_000),
                                                          available_pence=gbp(6_000),
                                                          policy_year=7))
    book.add_bond_terms(terms, **SEED)
    assert book.get_bond_terms("HB-40582213").segments_total == 1_000


def test_pension_terms_and_tax_are_stored_per_policy():
    book = _book()
    book.add_policy(Policy(policy_no="RA-77103428", product="retirement_account",
                           status="in_force", start_date="2005-04-06",
                           holder_party_id="PH-1001"), **SEED)
    book.add_pension_terms(RetirementAccountTerms(
        policy_no="RA-77103428",
        contribution_schedule=ContributionSchedule(member_net_pence=gbp(600),
                                                   employer_gross_pence=gbp(300)),
        target_retirement_age=60), **SEED)
    book.add_pension_tax(PensionTax(policy_no="RA-77103428",
                                    mpaa_triggered=MpaaStatus(value=False)), **SEED)
    assert book.get_pension_terms("RA-77103428").target_retirement_age == 60
    assert book.get_pension_tax("RA-77103428").protections == "none"


def test_funds_accumulate_per_policy():
    book = _book()
    book.add_policy(Policy(policy_no="HB-40582213", product="horizon_bond",
                           status="in_force", start_date="2019-03-01",
                           holder_party_id="PH-1001"), **SEED)
    book.add_fund(FundHolding(fund_id="MG", fund_name="Managed Growth", split_pct=60,
                              amc_bp=65, price_date="2026-07-10"), "HB-40582213", **SEED)
    book.add_fund(FundHolding(fund_id="WP", fund_name="With-Profits", split_pct=40,
                              amc_bp=65, price_date="2026-07-10"), "HB-40582213", **SEED)
    assert len(book.get_funds("HB-40582213")) == 2
    assert book.get_funds("LP-20419876") == ()


def test_bank_mandate_and_authority_are_stored():
    book = _book()
    book.add_mandate(BankMandate(policy_no="LP-20419876", account_last4="4471",
                                 verified=True), **SEED)
    book.add_authority(AuthorityRecord(authority_id="AUTH-1", policy_no="LP-20419876",
                                       party_id="PH-1002", type="LOA",
                                       scope=("servicing", "information"),
                                       evidence_ref="FRN 512345", status="active"), **SEED)
    assert book.get_mandate("LP-20419876").account_last4 == "4471"
    assert book.get_authorities("LP-20419876")[0].type == "LOA"


def test_adding_product_detail_for_an_unknown_policy_is_refused():
    book = _book()
    with pytest.raises(RecordError):
        book.add_cover(CoverComponent(policy_no="LP-99999999",
                                      sum_assured_pence=gbp(1), basis=("guaranteed",),
                                      premium_pence=gbp(1)), **SEED)


def test_adding_product_detail_is_journalled():
    book = _book()
    book.add_cover(CoverComponent(policy_no="LP-20419876", sum_assured_pence=gbp(400_000),
                                  basis=("unit_linked",), premium_pence=gbp(212.40)),
                   **SEED)
    kinds = [e.entity_type for e in book.changes.entries()]
    assert "cover" in kinds
