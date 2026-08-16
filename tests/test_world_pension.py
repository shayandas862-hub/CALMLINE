"""A Retirement Account played end to end — money in, and money out one way only.

`03-PEN:3.1` — regular and/or single contributions, personal or employer.
`03-PEN:3.4` — relief at source: the member pays 80% and Aldercrest reclaims 20%
from HMRC, so £80 net becomes £100 gross.

The card's done-when, and the two things that must hold whatever else changes:

- **an attempt to take a plain withdrawal is refused by the product rules before
  the ledger sees it** — through the timeline's rule seam, so the refusal comes
  from `can_pay_cash_out` (`products.py:239`) rather than from a check written
  twice;
- **the annual-allowance trigger, once set, is never unset.**
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.models import Policy
from src.records.products import FundHolding
from world import WORLD_BIRTH_DATE
from world.lifetimes.pension import play_pension, refuse_non_benefit_money_out
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import Movement, play

SEED = 11
START = date(2010, 6, 1)
POLICY_NO = "RA-77103428"
MEMBER_DOB = date(1961, 6, 18)


def _policy(status="in_force", start=START):
    return Policy(policy_no=POLICY_NO, product="retirement_account",
                  status=status, start_date=start.isoformat(),
                  holder_party_id="PH-2001")


def _holdings():
    return (FundHolding("target_date_2036", "Target-Date 2036", 70, 45,
                        "2026-07-28", pathway=3),
            FundHolding("global_index", "Global Index", 30, 22, "2026-07-28"))


def _plan(status="in_force", start=START, **kwargs):
    return play_pension(_policy(status=status, start=start), _holdings(),
                        member_dob=MEMBER_DOB, seed=SEED, **kwargs)


def _through_the_rulebook(plan, status="in_force", start=START):
    report = RefusalReport()
    lifetime = play(_policy(status=status, start=start), plan.movements,
                    report=report, rules=(refuse_non_benefit_money_out,))
    return lifetime, report


# ── the refusal the product exists to make ───────────────────────────────
def test_a_plain_withdrawal_is_refused_before_the_ledger_sees_it():
    """The card's done-when. The rule runs on the seam, so the refusal comes
    from the shipped `can_pay_cash_out` rather than a second copy of it."""
    # Arrange — a legal opening, then an illegal withdrawal
    movements = [
        Movement(on=START, kind="contribution", amount_pence=100_000_00,
                 reason="opening"),
        Movement(on=date(2020, 1, 6), kind="withdrawal", amount_pence=1_000_00,
                 reason="cash please"),
    ]

    # Act
    report = RefusalReport()
    lifetime = play(_policy(), movements, report=report,
                    rules=(refuse_non_benefit_money_out,))

    # Assert
    assert lifetime is None
    assert "benefit route" in report.refusals[0].reason
    assert report.refusals[0].kind == "withdrawal"


@pytest.mark.parametrize("kind", ["withdrawal", "surrender", "segment_surrender",
                                  "regular_withdrawal"])
def test_no_money_leaves_a_pension_by_any_other_door(kind):
    report = RefusalReport()
    lifetime = play(_policy(), [
        Movement(on=START, kind="contribution", amount_pence=100_000_00,
                 reason="opening"),
        Movement(on=date(2020, 1, 6), kind=kind, amount_pence=100,
                 reason="not a benefit route"),
    ], report=report, rules=(refuse_non_benefit_money_out,))
    assert lifetime is None


def test_money_in_is_never_refused():
    report = RefusalReport()
    lifetime = play(_policy(), [
        Movement(on=START, kind="contribution", amount_pence=100_00,
                 reason="member contribution"),
        Movement(on=date(2011, 6, 1), kind="transfer_in", amount_pence=58_000_00,
                 reason="transfer from a workplace scheme"),
    ], report=report, rules=(refuse_non_benefit_money_out,))
    assert report.is_empty(), report.render()
    assert lifetime.value_pence == 58_100_00


# ── the whole pension ────────────────────────────────────────────────────
def test_a_pension_is_built_without_a_single_refusal():
    lifetime, report = _through_the_rulebook(_plan())
    assert report.is_empty(), report.render()
    assert lifetime is not None


def test_it_shows_contributions_growth_and_charges():
    kinds = {m.kind for m in _plan().movements}
    assert "contribution" in kinds
    assert "charge" in kinds
    assert kinds & {"investment_return", "investment_loss"}


def test_a_transfer_in_arrives_as_its_own_kind():
    """`03-PEN:3.1`/§II.12 — a transfer is verified with the ceding scheme and
    scam-checked. It is not a contribution and does not use the allowance."""
    plan = _plan(transfer_in_pence=58_000_00)
    assert [m for m in plan.movements if m.kind == "transfer_in"]


def test_its_value_equals_the_sum_of_its_movements():
    lifetime, _ = _through_the_rulebook(_plan())
    assert lifetime.value_pence == sum(
        e.transaction.signed_pence for e in lifetime.entries)


def test_nothing_is_dated_outside_the_policys_life():
    plan = _plan()
    for item in list(plan.movements) + list(plan.events):
        assert START <= item.on <= WORLD_BIRTH_DATE


def test_the_same_seed_builds_the_same_pension_to_the_penny():
    assert _plan().movements == _plan().movements
    assert _plan().events == _plan().events


def test_a_pension_is_never_surrendered():
    """The bucket plan leaves the cell empty: a pension pays out through a
    benefit route, which is the whole of `03-PEN`."""
    with pytest.raises(ValueError, match="surrender"):
        _plan(status="surrendered")


# ── benefits, and the trigger ────────────────────────────────────────────
def test_taking_ufpls_triggers_the_allowance_and_records_when():
    plan = _plan(benefit_route="ufpls")
    assert plan.mpaa_triggered_on is not None
    assert [e for e in plan.events if e.kind == "mpaa_triggered"]


def test_taking_only_pcls_leaves_the_allowance_untriggered():
    """`03-PEN:9.1` — funds to drawdown, no income, no trigger."""
    plan = _plan(benefit_route="pcls")
    assert plan.mpaa_triggered_on is None
    assert not [e for e in plan.events if e.kind == "mpaa_triggered"]


def test_a_small_pot_leaves_the_allowance_untriggered():
    """`03-PEN:9.5`."""
    plan = _plan(benefit_route="small_pot")
    assert plan.mpaa_triggered_on is None


def test_the_trigger_once_set_is_never_unset():
    """The card's done-when. Contributions carry on afterwards, and none of
    them clears it."""
    plan = _plan(benefit_route="ufpls")
    triggered = plan.mpaa_triggered_on
    assert triggered is not None
    assert plan.mpaa_triggered_on == triggered
    assert all(e.on >= triggered for e in plan.events
               if e.kind == "mpaa_triggered")


def test_a_benefit_is_never_taken_before_the_minimum_pension_age():
    """`03-PEN:8` — 55, and a member who never reaches it takes nothing."""
    young = date(2000, 1, 1)
    plan = play_pension(_policy(), _holdings(), member_dob=young, seed=SEED,
                        benefit_route="ufpls")
    assert not [e for e in plan.events if e.kind == "benefit_taken"]
    assert plan.mpaa_triggered_on is None


def test_a_benefit_taken_is_dated_after_the_member_turned_fifty_five():
    plan = _plan(benefit_route="ufpls")
    (taken,) = [e for e in plan.events if e.kind == "benefit_taken"][:1]
    assert taken.on >= date(MEMBER_DOB.year + 55, MEMBER_DOB.month,
                            MEMBER_DOB.day)


def test_contributions_after_the_trigger_respect_the_capped_allowance():
    """`03-PEN:4.3` — £10,000/yr, no carry-forward. A book that kept paying
    £14,400 a year after a UFPLS would be quietly illegal."""
    plan = _plan(benefit_route="ufpls")
    triggered = plan.mpaa_triggered_on
    after = [m for m in plan.movements
             if m.kind == "contribution" and m.on > triggered]
    assert all(m.amount_pence <= 10_000_00 for m in after)


def test_a_benefit_payment_uses_a_pension_movement_kind():
    plan = _plan(benefit_route="ufpls")
    assert [m for m in plan.movements if m.kind == "ufpls_payment"]
    assert not [m for m in plan.movements if m.kind == "withdrawal"]
