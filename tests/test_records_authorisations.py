"""v4.5 phase 1 · task 3 — a mandate belongs to the firm, and names its people.

`05-OPS:5.1` verifies the **firm** and its FRN on the FCA Register, not a named
individual, and that is exactly what the corpus records: an `adviser_LOA` with a
firm, a reference, a scope and an expiry, and no person attached (D-CL-050).
That check is unchanged and still decides whether the mandate is valid at all.

What it cannot answer is the other half of a real adviser call: the firm holds a
valid mandate, and *this caller* is one of the people the firm named on it. That
is a new layer above the firm check, never a replacement for it.

Three standings rather than a boolean, because "this mandate names nobody" and
"this mandate names people and you are not one of them" are different facts with
different remedies. The first describes every mandate the corpus itself carries;
the second describes somebody who should not be on the telephone. Collapsing
them would make the anchors indistinguishable from a refused caller — which is
precisely the distinction this layer exists to draw.
"""

from __future__ import annotations

import pytest

from src.records.authorisations import (
    MANDATE_NAMES_NOBODY,
    MANDATE_STANDINGS,
    NAMED_ON_MANDATE,
    NOT_NAMED_ON_MANDATE,
    mandate_standing,
)
from src.records.models import AdviserLoa

FIRM = dict(firm="Nimbus Financial Planning", frn="Z157251",
            scope=("information", "servicing"), expiry="2027-06")


def _loa(**over) -> AdviserLoa:
    kw = dict(FIRM)
    kw.update(over)
    return AdviserLoa(**kw)


# ── the mandate can name its people ──────────────────────────────────────
def test_a_mandate_names_no_individuals_by_default():
    # Every mandate the corpus records is firm-only, and adding this field
    # must not silently invent people onto them.
    assert _loa().individuals == ()


def test_a_mandate_can_name_the_individuals_who_may_exercise_it():
    loa = _loa(individuals=("PH-3001", "PH-3002"))
    assert loa.individuals == ("PH-3001", "PH-3002")


def test_an_individual_is_a_party_id_not_a_name():
    # A person is referred to by their id everywhere else in the store; taking
    # a display name here would make the mandate the one place a person is
    # identified by something that can be typed two ways.
    with pytest.raises(ValueError):
        _loa(individuals=("Alpha Equinox 70",))


# ── where a caller stands against it ─────────────────────────────────────
def test_a_caller_the_mandate_names_is_named():
    loa = _loa(individuals=("PH-3001", "PH-3002"))
    assert mandate_standing(loa, "PH-3002") == NAMED_ON_MANDATE


def test_a_caller_the_mandate_does_not_name_is_distinguishable():
    # The firm's mandate is perfectly valid. This person is simply not on it.
    loa = _loa(individuals=("PH-3001", "PH-3002"))
    assert mandate_standing(loa, "PH-3099") == NOT_NAMED_ON_MANDATE


def test_a_mandate_naming_nobody_is_its_own_answer():
    # Not a refusal and not an approval — the fact that there is nobody to
    # check against, which is the shape every anchor carries.
    assert mandate_standing(_loa(), "PH-3001") == MANDATE_NAMES_NOBODY


def test_the_three_standings_are_distinct_and_closed():
    assert len({MANDATE_NAMES_NOBODY, NAMED_ON_MANDATE, NOT_NAMED_ON_MANDATE}) == 3
    assert MANDATE_STANDINGS == frozenset(
        {MANDATE_NAMES_NOBODY, NAMED_ON_MANDATE, NOT_NAMED_ON_MANDATE})


def test_the_standing_of_a_policy_with_no_mandate_at_all_is_names_nobody():
    # A policy with no adviser has no mandate to be named on, and asking must
    # not raise — the gate asks this question before it knows the answer.
    assert mandate_standing(None, "PH-3001") == MANDATE_NAMES_NOBODY


# ── the firm check underneath is untouched ───────────────────────────────
def test_naming_individuals_does_not_change_what_verifies_the_firm():
    # `05-OPS:5.1` verifies the firm and its reference. Adding people above it
    # must leave that identity exactly as it was.
    plain, named = _loa(), _loa(individuals=("PH-3001",))
    assert (plain.firm, plain.frn, plain.scope, plain.expiry) == (
        named.firm, named.frn, named.scope, named.expiry)


def test_the_scope_vocabulary_is_still_closed():
    with pytest.raises(ValueError):
        _loa(scope=("information", "borrow_the_car"))


# ── it survives the round trip through Postgres ──────────────────────────
def test_named_individuals_survive_a_row_round_trip():
    # `row_to_policy` names the fields it rebuilds, so a new one that is not
    # named there is silently lost on the way back out of the database.
    from src.records.pg_store import row_to_policy

    policy = row_to_policy({
        "policy_no": "HB-40582213", "product": "horizon_bond",
        "status": "in_force", "start_date": "2019-03-01",
        "holder_party_id": "PH-2001",
        "adviser_loa": dict(FIRM, scope=list(FIRM["scope"]),
                            individuals=["PH-3001", "PH-3002"]),
    })
    assert policy is not None and policy.adviser_loa is not None
    assert policy.adviser_loa.individuals == ("PH-3001", "PH-3002")


def test_a_row_with_no_named_individuals_still_round_trips():
    from src.records.pg_store import row_to_policy

    policy = row_to_policy({
        "policy_no": "HB-40582213", "product": "horizon_bond",
        "status": "in_force", "start_date": "2019-03-01",
        "holder_party_id": "PH-2001",
        "adviser_loa": dict(FIRM, scope=list(FIRM["scope"])),
    })
    assert policy is not None and policy.adviser_loa is not None
    assert policy.adviser_loa.individuals == ()
