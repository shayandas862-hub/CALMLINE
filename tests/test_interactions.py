"""v4 phase 2 · task 4 — the interaction store (`CN-` + 10).

An interaction is the container a verification lives in and a case is raised
from. It opens, things get logged against it, and it closes — at which point
(from phase 3) any verification inside it expires with it (AD-CL-029).

Every timestamp is injected. The store never reads the clock.
"""

import pytest

from src.records.interactions import (
    Interaction,
    InteractionError,
    InteractionStore,
)

OPENED = "2026-07-13T09:00:00"


def _store() -> InteractionStore:
    return InteractionStore()


# ── the shape ────────────────────────────────────────────────────────────
def test_interaction_requires_the_kb_grammar():
    with pytest.raises(ValueError):
        Interaction(cn_ref="CN-123", policy_no="LP-20419876", opened_at=OPENED)


def test_channel_is_a_closed_vocabulary():
    assert Interaction(cn_ref="CN-1000000001", policy_no="LP-20419876",
                       opened_at=OPENED, channel="phone").channel == "phone"
    with pytest.raises(ValueError):
        Interaction(cn_ref="CN-1000000001", policy_no="LP-20419876",
                    opened_at=OPENED, channel="telepathy")


def test_a_seeded_row_may_carry_no_channel_at_all():
    # A sample record says what happened and when, never through which channel.
    # A gap is more honest than a plausible guess.
    assert Interaction(cn_ref="CN-1000000001", policy_no="LP-20419876",
                       opened_at=OPENED).channel is None


# ── open ─────────────────────────────────────────────────────────────────
def test_open_mints_a_reference_and_returns_an_open_interaction():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED,
                     claimed_relationship="policyholder")
    assert row.cn_ref.startswith("CN-") and len(row.cn_ref) == 13
    assert row.is_open
    assert row.opened_at == OPENED
    assert store.get(row.cn_ref) is row


def test_each_opened_interaction_gets_its_own_reference():
    store = _store()
    refs = {store.open(policy_no="LP-20419876", channel="phone", at=OPENED).cn_ref
            for _ in range(3)}
    assert len(refs) == 3


def test_open_refuses_an_unknown_channel():
    with pytest.raises(ValueError):
        _store().open(policy_no="LP-20419876", channel="smoke signal", at=OPENED)


# ── log ──────────────────────────────────────────────────────────────────
def test_log_records_the_intent_and_outcome_on_an_open_interaction():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    updated = store.log(row.cn_ref, intent="valuation request", outcome="answered")
    assert updated.intent == "valuation request"
    assert updated.outcome == "answered"
    assert store.get(row.cn_ref).outcome == "answered"


def test_log_attaches_a_verification_reference():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    assert store.log(row.cn_ref, verification_ref="VR-0001").verification_ref == "VR-0001"


def test_logging_against_an_unknown_interaction_raises():
    with pytest.raises(InteractionError):
        _store().log("CN-9999999999", intent="x")


def test_logging_against_a_closed_interaction_is_refused():
    # A closed contact is a historical record, not a scratchpad.
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    store.close(row.cn_ref, at="2026-07-13T09:20:00", outcome="answered")
    with pytest.raises(InteractionError):
        store.log(row.cn_ref, intent="one more thing")


# ── close ────────────────────────────────────────────────────────────────
def test_close_stamps_the_injected_time_and_ends_the_interaction():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    closed = store.close(row.cn_ref, at="2026-07-13T09:20:00", outcome="answered")
    assert closed.closed_at == "2026-07-13T09:20:00"
    assert not closed.is_open
    assert closed.outcome == "answered"


def test_closing_twice_is_refused():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    store.close(row.cn_ref, at="2026-07-13T09:20:00")
    with pytest.raises(InteractionError):
        store.close(row.cn_ref, at="2026-07-13T09:30:00")


def test_closing_before_it_opened_is_refused():
    store = _store()
    row = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    with pytest.raises(InteractionError):
        store.close(row.cn_ref, at="2026-07-13T08:00:00")


# ── reads ────────────────────────────────────────────────────────────────
def test_for_policy_returns_only_that_policys_contacts():
    store = _store()
    store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    store.open(policy_no="HB-40582213", channel="email", at=OPENED)
    assert len(store.for_policy("LP-20419876")) == 1
    assert store.for_policy("RA-77103428") == ()


def test_open_interactions_can_be_listed():
    store = _store()
    first = store.open(policy_no="LP-20419876", channel="phone", at=OPENED)
    store.open(policy_no="LP-20419876", channel="email", at=OPENED)
    store.close(first.cn_ref, at="2026-07-13T09:20:00")
    assert len(store.open_interactions()) == 1
