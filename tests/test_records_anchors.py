"""The three **specimen** policies the rulebook documents, parsed from the KB.

Rewritten in v4.5 phase 3, because the semantics changed. They were *anchors* —
three policies the system read out of the corpus and made real, sitting in the
book beside eighty invented ones and indistinguishable from them. They are now
**specimens**: labelled illustrations on numbers the generator is structurally
forbidden from issuing.

The round-trip assertions below are unchanged and deliberately so — turning a
policy into a specimen must not change a single figure it states. What is new is
the block, and the block is the whole point of the task: before it, the three
numbers missed the generator's range **by arithmetic accident**, a property
nobody had stated and nothing checked.

Specimens ledger **exactly what their records state** (D-CL-028). Where a stated
value cannot be reached from the stated movements, the gap is carried by one
explicitly-reasoned entry rather than by quietly adjusting a figure (D-CL-038).
"""

import pytest

from src.records.anchors import (
    GENERATED_CEILING,
    SPECIMEN_FLOOR,
    SPECIMEN_IDS,
    digits_of,
    is_specimen,
    seed_specimens,
)
from src.records.models import gbp
from src.records.products import can_pay_cash_out
from src.records.store import InMemoryRecordBook
from src.records.valuation import value_as_at

AS_AT = "2026-07-13"          # the knowledge-base date — injected, never the clock


@pytest.fixture(scope="module")
def book():
    store = InMemoryRecordBook()
    seed_specimens(store, kb_dir="data/kb", as_at=AS_AT)
    return store


# ── the reserved block ───────────────────────────────────────────────────
def test_the_two_blocks_cannot_overlap():
    """The guarantee, stated as arithmetic rather than as a promise."""
    assert GENERATED_CEILING < SPECIMEN_FLOOR


def test_every_specimen_number_is_inside_the_reserved_block():
    for policy_no in SPECIMEN_IDS:
        assert is_specimen(policy_no), policy_no
        assert digits_of(policy_no) >= SPECIMEN_FLOOR


def test_the_generator_cannot_issue_a_specimen_number():
    """Checked where numbers are **made**. A book already built on a colliding
    number is a book that has to be thrown away, so the allocator refuses."""
    from world.lifetimes.allocation import _mint

    with pytest.raises(ValueError) as caught:
        _mint("LP", (SPECIMEN_FLOOR - 20_000_000) // 137 + 1)
    assert str(GENERATED_CEILING) in str(caught.value)


def test_the_whole_generated_book_stays_below_the_ceiling():
    """Not a property of the mint alone — of the two hundred it actually mints."""
    from datetime import date

    from world.lifetimes.allocation import allocate_book

    holders = [f"PH-{2000 + n:04d}" for n in range(1, 201)]
    specs = allocate_book(seed=11, born=date(2026, 7, 28),
                          holders=holders[:162], second_lives=holders[162:200])

    assert specs
    for spec in specs:
        assert digits_of(spec.policy_no) <= GENERATED_CEILING, spec.policy_no
        assert not is_specimen(spec.policy_no)


def test_no_generated_number_is_a_specimen_number():
    """The claim the task is actually about, on the committed world."""
    from src.records.seed import build_world_book

    numbers = {p.policy_no for p in build_world_book().list_policies()}
    assert numbers.isdisjoint(set(SPECIMEN_IDS))


def test_a_specimen_record_on_an_issuable_number_is_refused():
    """If the corpus ever documented a record inside the generator's half, that
    is a collision waiting to happen and seeding says so rather than loading it."""
    from src.records import anchors

    original = anchors.SPECIMEN_FLOOR
    try:
        anchors.SPECIMEN_FLOOR = 90_000_000     # nothing documented reaches this
        with pytest.raises(ValueError) as caught:
            seed_specimens(InMemoryRecordBook(), kb_dir="data/kb", as_at=AS_AT)
        assert "reserved specimen block" in str(caught.value)
    finally:
        anchors.SPECIMEN_FLOOR = original


# ── all three still round-trip, unchanged ────────────────────────────────
def test_all_three_specimen_records_become_policies(book):
    assert {p.policy_no for p in book.list_policies()} == set(SPECIMEN_IDS)


def test_each_specimen_balance_equals_its_stated_value(book):
    # The figure the record states, reached by folding the ledger.
    assert book.current_value("LP-20419876") == gbp(46_210)     # fund_value
    assert book.current_value("HB-40582213") == gbp(151_240)    # current_value
    assert book.current_value("RA-77103428") == gbp(212_400)    # fund_value


def test_every_specimen_ledger_reconciles_against_its_own_history(book):
    for policy_no in SPECIMEN_IDS:
        summed = sum(e.transaction.signed_pence for e in book.history(policy_no))
        assert book.current_value(policy_no) == summed


# ── the parties ──────────────────────────────────────────────────────────
def test_parties_carry_their_stated_details(book):
    theta = book.get_party("PH-0001")
    assert theta.name == "Theta Meridian 12"
    assert theta.dob == "1954-02-11"
    assert theta.registered_address == "14 Lattice Way, Demoford"
    assert theta.contact.registered is True          # "(registered)" on the address


def test_the_pension_member_is_a_scottish_taxpayer(book):
    # Drives S-code PAYE answers; it is a stated field, not an assumption.
    assert book.get_party("PH-0003").scottish_taxpayer is True
    assert book.get_party("PH-0001").scottish_taxpayer is False


# ── Lifelong Protection ──────────────────────────────────────────────────
def test_the_lifelong_protection_policy_matches_its_record(book):
    policy = book.get_policy("LP-20419876")
    assert policy.start_date == "2016-05-01"
    assert policy.lives_assured_basis == "single"
    assert policy.trust.kind == "discretionary"
    assert policy.trust.trustees == ("Theta Meridian 12", "Delta Meridian 41")
    assert policy.adviser_loa.frn == "512345"
    assert policy.adviser_loa.scope == ("servicing", "information")
    assert policy.bank_last4 == "4471"


def test_the_cover_records_both_bases_and_the_declined_indexation(book):
    cover = book.get_cover("LP-20419876")
    assert cover.basis == ("reviewable", "unit_linked")
    assert cover.sum_assured_pence == gbp(400_000)
    assert cover.premium_pence == gbp(212.40)
    assert cover.indexation.declined_years == (2024, 2025)
    assert cover.riders == ()                        # GIO and waiver both "not included"


def test_the_lifelong_protection_ledger_states_only_the_fund_value(book):
    # No premium history: the record does not state one, so the ledger invents none.
    kinds = [e.transaction.kind for e in book.history("LP-20419876")]
    assert kinds == ["opening"]


# ── Horizon Bond — the six withdrawals that tie out ──────────────────────
def test_the_bond_ledgers_its_six_annual_withdrawals(book):
    kinds = [e.transaction.kind for e in book.history("HB-40582213")]
    assert kinds.count("regular_withdrawal") == 6


def test_the_six_withdrawals_total_the_stated_allowance_used(book):
    withdrawn = sum(e.transaction.amount_pence for e in book.history("HB-40582213")
                    if e.transaction.kind == "regular_withdrawal")
    assert withdrawn == gbp(36_000)                  # "£36,000 of £42,000"


def test_the_bond_allowance_matches_the_record(book):
    allowance = book.get_bond_terms("HB-40582213").allowance_5pct
    assert allowance.used_pence == gbp(36_000)
    assert allowance.available_pence == gbp(6_000)


def test_the_bond_opens_at_the_stated_investment(book):
    first = book.history("HB-40582213")[0]
    assert first.transaction.kind == "opening"
    assert first.transaction.amount_pence == gbp(120_000)
    assert first.transaction.at.startswith("2019-03-01")


def test_the_bonds_unstated_growth_is_carried_by_one_reasoned_entry(book):
    # £120,000 in, £36,000 out, £151,240 stated — the £67,240 difference is
    # growth the record does not itemise. It is one labelled entry, not a fudge
    # spread through the withdrawals (D-CL-038).
    growth = [e for e in book.history("HB-40582213")
              if e.transaction.kind == "credit_adjustment"]
    assert len(growth) == 1
    assert growth[0].transaction.amount_pence == gbp(67_240)
    assert "not itemised" in growth[0].transaction.reason


def test_the_bond_is_a_joint_last_survivor_policy(book):
    policy = book.get_policy("HB-40582213")
    assert policy.lives_assured_basis == "joint_last_survivor"
    assert [life.name for life in policy.lives_assured] == [
        "Argon Basalt 27", "Lumen Basalt 33"]


def test_the_bond_funds_split_sixty_forty(book):
    funds = {f.fund_name: f.split_pct for f in book.get_funds("HB-40582213")}
    assert funds == {"Managed Growth": 60, "With-Profits": 40}


# ── the demonstrable outcome ─────────────────────────────────────────────
def test_the_bond_is_worth_different_amounts_across_its_withdrawals(book):
    # "What was this bond worth on 12 April?" — a ledger-fold number.
    before_first = value_as_at(book, "HB-40582213", "2020-02-29")
    after_first = value_as_at(book, "HB-40582213", "2020-03-02")
    after_all = value_as_at(book, "HB-40582213", "2025-04-01")
    assert before_first == gbp(120_000)
    assert after_first == gbp(114_000)
    assert after_all == gbp(84_000)
    assert len({before_first, after_first, after_all}) == 3


# ── Retirement Account ───────────────────────────────────────────────────
def test_the_pension_ledgers_the_stated_transfer_in(book):
    transfers = [e for e in book.history("RA-77103428")
                 if e.transaction.kind == "transfer_in"]
    assert len(transfers) == 1
    assert transfers[0].transaction.amount_pence == gbp(58_000)
    assert transfers[0].transaction.at.startswith("2024-08")


def test_the_pension_ledgers_twelve_months_of_contributions(book):
    contributions = [e for e in book.history("RA-77103428")
                     if e.transaction.kind == "contribution"]
    assert len(contributions) == 12
    # member £600 net + employer £300 gross, at the stated rate
    assert all(e.transaction.amount_pence == gbp(900) for e in contributions)


def test_the_pension_terms_match_the_record(book):
    terms = book.get_pension_terms("RA-77103428")
    assert terms.target_retirement_age == 60
    assert terms.contribution_schedule.member_net_pence == gbp(600)
    assert terms.expression_of_wish.beneficiary == "Vector Quasar 61"
    assert terms.expression_of_wish.signed == "2024-02-10"
    assert terms.transfers_in[0].scam_dd_passed is True
    assert terms.transfers_in[0].safeguarded_benefits is False


def test_the_pension_tax_state_matches_the_record(book):
    tax = book.get_pension_tax("RA-77103428")
    assert tax.mpaa_triggered.value is False
    assert tax.protections == "none"
    assert tax.ttfac is None


def test_the_pension_refuses_a_plain_withdrawal(book):
    policy = book.get_policy("RA-77103428")
    assert can_pay_cash_out(policy) is False
    assert can_pay_cash_out(policy, route="ufpls") is True


# ── interactions and cases from the record's own lines ───────────────────
def test_recent_lines_become_interactions(book):
    # `recent_transactions:` on the LP record lists two contacts.
    assert len(book.interactions.for_policy("LP-20419876")) == 2


def test_an_open_case_line_becomes_a_case(book):
    cases = book.cases_for_policy("LP-20419876")
    assert [c.cw_ref for c in cases] == ["CW-300218754"]


def test_a_record_with_no_open_cases_creates_none(book):
    assert book.cases_for_policy("HB-40582213") == ()


# ── the label, in the corpus itself ──────────────────────────────────────
def test_each_record_says_it_is_a_specimen():
    """A reader of the product manual has to be able to tell. The label is in
    the corpus, not only in the code that parses it."""
    from src.records.sample_record import load_sample_records

    for chunk_id, record in load_sample_records("data/kb").items():
        assert "specimen, not a customer" in record.chunk.text.lower(), chunk_id
        assert "specimen policy record" in record.chunk.heading.lower(), chunk_id


def test_seeding_is_auditable(book):
    assert all(e.source_ref == "seed" for e in book.changes.entries())
    assert len(book.changes.for_entity("policy", "HB-40582213")) > 1
