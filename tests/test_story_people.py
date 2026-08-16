"""Nobody was invented — the safety test.

**It runs offline on committed data, so it holds forever rather than only on the
day the stories were written.** Nothing here calls anything; it reads
`data/world/` and answers.

The card's done-when:

- **the whole world passes**
- a deliberately inserted **invented name is caught and named**
- a person **referenced in the wrong role** is caught

The check is on **roles, not names**, and that is a finding rather than a
preference. The world's 299 names are unique only because each carries a
trailing number — `Alpha Feldspar 2` is a trustee and `Alpha Feldspar 265` is a
policyholder — 49 two-word prefixes are shared, and all 299 share 30 surnames.
A name in prose therefore identifies nobody, so prose refers to people by the
role they hold on the policy, and this asserts the role claim against the cast.

That makes the guarantee stronger than the card asked for: a name of **any**
kind is refused, invented or real, because the role is what carries authority
and the role is what a reader acts on.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from world.dataset import DEFAULT_ROOT, DatasetError, read_world
from world.stories.validate import assert_nobody_invented, validate_world

# LP-20000959 holds a trust; HB-20002740 has no third party at all.
WITH_TRUST = "LP-20000959"
TRUST_REF = "CN-1000959006"
NO_PARTIES = "HB-20002740"
PLAIN_REF = "CN-2002740009"


@pytest.fixture(scope="module")
def world():
    return read_world(DEFAULT_ROOT)


def _with(world, policy_no: str, ref: str, text: str):
    return replace(world, stories=({"policy_no": policy_no, "ref": ref,
                                    "kind": "note", "text": text},))


# ── the whole world ──────────────────────────────────────────────────────
def test_the_whole_committed_world_passes(world):
    """Every story written so far, against every policy's cast."""
    assert validate_world(world) == ()


def test_the_whole_world_passes_the_raising_form_too(world):
    assert_nobody_invented(world)


# ── an invented name ─────────────────────────────────────────────────────
def test_an_invented_name_is_caught_and_named(world):
    """A name that appears nowhere in the dataset."""
    problems = validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "Rang about the withdrawal. Spoke to Mrs Wilkinson, who confirmed "
              "the account."))

    assert len(problems) == 1
    assert "Wilkinson" in problems[0].detail
    assert problems[0].ref == PLAIN_REF


def test_a_real_name_from_the_people_file_is_caught_too(world):
    """`Alpha Feldspar 265` is the holder of this very policy — and is still
    refused, because the name identifies nobody without its number and the
    number is not something a handler would write."""
    holder = next(p["name"] for p in world.people
                  if p.get("party_id") == "PH-2048")
    problems = validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              f"Rang about the withdrawal. {holder} confirmed the account."))

    assert problems
    assert any("write the role" in p.detail for p in problems)


# ── the wrong role ───────────────────────────────────────────────────────
def test_a_person_referenced_in_a_role_the_policy_does_not_hold_is_caught(world):
    """The card's example, exactly: an attorney instructing a withdrawal on a
    policy with no attorney."""
    problems = validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "Rang about the withdrawal. Her attorney instructed it and we "
              "released the payment."))

    assert len(problems) == 1
    assert problems[0].role == "attorney"
    assert NO_PARTIES in problems[0].detail


def test_a_trustee_claimed_on_a_policy_with_no_trust_is_caught(world):
    problems = validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "Both trustees signed the instruction before it was released."))
    assert [p.role for p in problems] == ["trustee"]


def test_a_role_the_policy_really_holds_is_allowed(world):
    """LP-20000959 is written into trust, so its notes may say so."""
    assert validate_world(
        _with(world, WITH_TRUST, TRUST_REF,
              "Confirmed that the trustee has to instruct us and that the "
              "holder cannot deal with it on his own.")) == ()


def test_the_adviser_portal_is_a_channel_not_somebody_acting(world):
    """80% of `adviser_portal` contacts are on policies with no mandate. The
    channel says where a message arrived, so naming it cannot be a role claim."""
    assert validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "Instruction in through the adviser portal for the usual yearly "
              "amount. Raised for the January run.")) == ()


def test_an_adviser_acting_on_a_policy_with_no_mandate_is_still_caught(world):
    """The channel is allowed; the person is not."""
    problems = validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "The adviser rang to confirm the withdrawal on her behalf."))
    assert [p.role for p in problems] == ["adviser"]


# ── reporting ────────────────────────────────────────────────────────────
def test_the_raising_form_lists_every_problem_not_just_the_first(world):
    broken = replace(world, stories=(
        {"policy_no": NO_PARTIES, "ref": PLAIN_REF, "kind": "note",
         "text": "Her attorney rang about the payment."},
        {"policy_no": NO_PARTIES, "ref": "CN-2002740008", "kind": "note",
         "text": "The trustee wrote in to confirm it."},
    ))

    with pytest.raises(DatasetError) as raised:
        assert_nobody_invented(broken)

    message = str(raised.value)
    assert "attorney" in message and "trustee" in message
    assert "2 stories" in message


def test_ordinary_prose_with_dates_and_money_is_left_alone(world):
    """Months and amounts are not people. A check that refuses `January` is one
    that gets turned off."""
    assert validate_world(
        _with(world, NO_PARTIES, PLAIN_REF,
              "Rang on Christmas Eve to set the annual amount up again. "
              "£1,461.35 confirmed for the January run.")) == ()
