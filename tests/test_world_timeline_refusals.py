"""What the timeline engine refuses — the phase's headline guarantee.

**A refused movement stops that policy and is recorded.** It is never adjusted,
never retried, never skipped quietly. The world cannot be born breaking its own
rules, because the code that would refuse a live handler is the code that builds
it.

The refusals here are the product-independent ones: the money guard, the
overdraw check, the world's own calendar, and the order of history. What a
*bond* or a *pension* additionally refuses arrives through the rule seam, which
is why the seam is proved here and filled in later.

Split from `test_world_timeline.py` — that file proves what the engine builds,
this one proves what it will not.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.records.models import Policy
from world import WORLD_BIRTH_DATE
from world.lifetimes.report import RefusalReport
from world.lifetimes.timeline import Movement, play

START = date(2015, 3, 1)
POLICY_NO = "HB-40000001"


def _policy(policy_no=POLICY_NO, start=START, product="horizon_bond"):
    return Policy(
        policy_no=policy_no,
        product=product,
        status="in_force",
        start_date=start.isoformat(),
        holder_party_id="PH-2001",
    )


def _opening(amount=100_000_00, on=START):
    return Movement(on=on, kind="opening", amount_pence=amount, reason="invested")


def _played(movements, policy=None, report=None, rules=()):
    report = report if report is not None else RefusalReport()
    lifetime = play(policy or _policy(), movements, report=report, rules=rules)
    return lifetime, report


# ── the overdraw check, and the no-partial-policy rule ───────────────────
def test_a_withdrawal_larger_than_the_balance_is_refused():
    # Arrange — the card's own deliberately impossible timeline
    movements = [
        _opening(amount=1_000_00),
        Movement(on=date(2016, 3, 1), kind="withdrawal",
                 amount_pence=5_000_00, reason="more than there is"),
    ]

    # Act
    lifetime, report = _played(movements)

    # Assert
    assert lifetime is None
    (refusal,) = report.refusals
    assert refusal.policy_no == POLICY_NO
    assert refusal.kind == "withdrawal"
    assert refusal.on == date(2016, 3, 1)
    assert refusal.amount_pence == 5_000_00
    assert "overdraw" in refusal.reason.lower()


def test_a_refused_policy_produces_no_partial_lifetime():
    """The card's done-when: no partial policy in the output.

    The opening movement was perfectly legal, so a lenient engine would hand
    back a one-entry policy worth £1,000. That policy never existed, and a book
    containing it would be a book nobody can reconcile.
    """
    lifetime, _ = _played([
        _opening(amount=1_000_00),
        Movement(on=date(2016, 3, 1), kind="withdrawal",
                 amount_pence=5_000_00, reason="impossible"),
    ])
    assert lifetime is None


def test_movements_after_the_refusal_are_never_applied():
    # Arrange — a perfectly legal movement sits *after* the illegal one
    report = RefusalReport()
    _played([
        _opening(amount=1_000_00),
        Movement(on=date(2016, 3, 1), kind="withdrawal",
                 amount_pence=5_000_00, reason="impossible"),
        Movement(on=date(2017, 3, 1), kind="bonus", amount_pence=100,
                 reason="never reached"),
    ], report=report)

    # Assert — exactly one refusal: the walk stopped, it did not carry on
    assert len(report.refusals) == 1
    assert report.refusals[0].kind == "withdrawal"


def test_a_withdrawal_of_the_exact_balance_is_allowed():
    """Zero is a legal balance — a full surrender empties a policy."""
    lifetime, report = _played([
        _opening(amount=1_000_00),
        Movement(on=date(2016, 3, 1), kind="surrender", amount_pence=1_000_00,
                 reason="full surrender"),
    ])
    assert report.is_empty()
    assert lifetime.value_pence == 0


# ── the world's calendar ─────────────────────────────────────────────────
def test_a_movement_after_the_worlds_birth_date_is_refused():
    lifetime, report = _played([
        _opening(),
        Movement(on=date(2026, 7, 29), kind="bonus", amount_pence=100,
                 reason="the world has not got there yet"),
    ])
    assert lifetime is None
    assert "birth" in report.refusals[0].reason.lower()


def test_a_movement_on_the_worlds_birth_date_itself_is_allowed():
    """The boundary is inclusive — the world exists on the day it was born."""
    lifetime, report = _played([
        _opening(),
        Movement(on=WORLD_BIRTH_DATE, kind="bonus", amount_pence=100,
                 reason="on the day"),
    ])
    assert report.is_empty()
    assert lifetime.value_pence == 100_000_00 + 100


def test_a_movement_before_the_policy_started_is_refused():
    lifetime, report = _played([
        Movement(on=date(2015, 2, 28), kind="opening", amount_pence=100,
                 reason="before the policy existed"),
    ])
    assert lifetime is None
    assert "start" in report.refusals[0].reason.lower()


def test_movements_out_of_date_order_are_refused():
    """A ledger is a history, and history does not go backwards."""
    lifetime, report = _played([
        _opening(),
        Movement(on=date(2018, 1, 1), kind="bonus", amount_pence=100, reason="b"),
        Movement(on=date(2017, 1, 1), kind="bonus", amount_pence=100, reason="a"),
    ])
    assert lifetime is None
    assert "order" in report.refusals[0].reason.lower()


def test_two_movements_on_the_same_day_are_in_order_not_out_of_it():
    lifetime, report = _played([
        _opening(),
        Movement(on=date(2016, 1, 1), kind="charge", amount_pence=100, reason="a"),
        Movement(on=date(2016, 1, 1), kind="bonus", amount_pence=100, reason="b"),
    ])
    assert report.is_empty()
    assert len(lifetime.entries) == 3


# ── the money guard and the closed vocabulary ────────────────────────────
@pytest.mark.parametrize("kind", ["adjustment", "interest", "", "PREMIUM",
                                  "investment_gain"])
def test_an_unknown_kind_is_refused_rather_than_raising(kind):
    """The vocabulary is closed at seventeen by `0003_world_movements.sql`. An
    unknown kind is a refusal the report can show, not a traceback that takes
    the whole build down with it."""
    lifetime, report = _played([Movement(on=START, kind=kind, amount_pence=100,
                                         reason="not a kind")])
    assert lifetime is None
    assert len(report.refusals) == 1
    assert kind in report.refusals[0].reason or "kind" in report.refusals[0].reason


@pytest.mark.parametrize("amount", [-1, -100_00])
def test_a_negative_amount_is_refused(amount):
    """`amount_pence` is a magnitude; the kind carries the direction. A signed
    return was tried and rejected — a fall in value is `investment_loss`."""
    lifetime, report = _played([Movement(on=START, kind="opening",
                                         amount_pence=amount, reason="signed")])
    assert lifetime is None
    assert len(report.refusals) == 1


@pytest.mark.parametrize("amount", [100.5, 100.0, "100"])
def test_a_non_integer_amount_is_refused(amount):
    """Money is integer pence. No fractional penny may ever appear — and a
    float that happens to be whole is still a float."""
    lifetime, report = _played([Movement(on=START, kind="opening",
                                         amount_pence=amount, reason="not pence")])
    assert lifetime is None


def test_a_movement_for_another_policy_cannot_be_smuggled_in():
    """The engine stamps every transaction with the policy it is playing, so a
    crossed wire is impossible rather than merely unlikely."""
    lifetime, _ = _played([_opening()], policy=_policy(policy_no="HB-40000009"))
    assert all(e.transaction.policy_no == "HB-40000009" for e in lifetime.entries)


# ── the rule seam ────────────────────────────────────────────────────────
def test_a_product_rule_refusal_stops_the_policy_and_is_reported():
    # Arrange — a pension refusing a plain withdrawal is exactly this shape
    def no_plain_withdrawals(policy, movement, balance_pence):
        if movement.kind == "withdrawal":
            return "a retirement account pays out only through a benefit route"
        return None

    # Act
    lifetime, report = _played([
        _opening(),
        Movement(on=date(2020, 1, 1), kind="withdrawal", amount_pence=100,
                 reason="cash please"),
    ], rules=(no_plain_withdrawals,))

    # Assert
    assert lifetime is None
    assert "benefit route" in report.refusals[0].reason


def test_a_product_rule_refuses_before_the_ledger_is_touched():
    """A rule refusing a movement the ledger would happily have accepted proves
    the ordering: the rulebook is asked first, not consulted afterwards."""
    lifetime, report = _played(
        [_opening()], rules=(lambda p, m, b: "refused by the product",))
    assert lifetime is None
    assert report.refusals[0].reason == "refused by the product"


def test_a_later_rule_can_refuse_what_an_earlier_one_allowed():
    rules = (lambda p, m, b: None, lambda p, m, b: "the second rule says no")
    lifetime, report = _played([_opening()], rules=rules)
    assert lifetime is None
    assert report.refusals[0].reason == "the second rule says no"


def test_one_refused_policy_does_not_stop_the_next_one_being_built():
    """A refusal stops *that* policy. The book carries on, which is what makes
    the report a list rather than a crash."""
    report = RefusalReport()
    _played([_opening(amount=100), Movement(on=date(2016, 1, 1),
                                            kind="withdrawal", amount_pence=999,
                                            reason="too much")], report=report)
    good, _ = _played([_opening()], policy=_policy(policy_no="HB-40000003"),
                      report=report)
    assert good is not None
    assert len(report.refusals) == 1
