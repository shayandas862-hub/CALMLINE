"""v4 phase 3 · task 1 — the data-protection gate, on the tick model (D-CL-114).

`05-OPS:3.2` (standard verification) is **three of four**: policy number;
full name + DOB; registered address *or* last-4 of the collection account;
memorable-data item set at onboarding. The "or" sits *inside* the third check,
so there are four checks and never five.

Since D-CL-114 the gate shows the **handler** what the record holds, and the
handler ticks each item the caller states correctly — a handler who cannot see
the record cannot judge a match. The system records the ticks; it never decides
them (D-CL-019, now literal). What survives from `07-RUNBOOK:4.1`: the prompts
read aloud to the caller still carry no held value, the memorable item is
marked ask-only (never read out), and on failure the caller-facing route never
says which element failed — correction is itself disclosure.

Time is injected. Nothing here reads the clock.
"""

import pytest

from src.identity.gate import (
    VerificationGate,
    VerificationRecord,
    cannot_verify_route,
)
from src.identity.questions import SV_THRESHOLD, held_checks
from src.records.models import Contact, Party, Policy

AT = "2026-07-13T09:00:00"
CN = "CN-1000000001"
POLICY_NO = "HB-40582213"
THREE = ("policy_no", "name_dob", "address_or_bank")


def _party(**over) -> Party:
    kw = dict(party_id="PH-1002", name="Argon Basalt 27", dob="1962-09-30",
              registered_address="8 Cornice Row, Sampleton",
              contact=Contact(phone="07700 900456", email="ph-1002@example.org",
                              registered=True))
    kw.update(over)
    return Party(**kw)


def _policy(**over) -> Policy:
    kw = dict(policy_no=POLICY_NO, product="horizon_bond", status="in_force",
              start_date="2019-03-01", holder_party_id="PH-1002",
              bank_last4="2209")
    kw.update(over)
    return Policy(**kw)


def _confirm(gate, ticked, *, party=None, policy=None, cn_ref=CN,
             policy_no=POLICY_NO, actor="handler_a", at=AT):
    return gate.confirm(cn_ref=cn_ref, policy_no=policy_no,
                        party=party if party is not None else _party(),
                        policy=policy if policy is not None else _policy(),
                        ticked=ticked, actor=actor, at=at)


# ── the check set (05-OPS:3.2) ───────────────────────────────────────────
def test_the_threshold_is_three():
    assert SV_THRESHOLD == 3


def test_a_party_with_a_memorable_item_has_all_four_checks():
    checks = held_checks(_party(memorable="first pet"), _policy())
    assert [c.kind for c in checks] == [
        "policy_no", "name_dob", "address_or_bank", "memorable"]


def test_a_party_without_a_memorable_item_has_only_what_the_record_holds():
    # A check the record cannot answer is not shown: ticking it could only be
    # a tick against nothing.
    checks = held_checks(_party(), _policy())
    assert [c.kind for c in checks] == list(THREE)


def test_the_held_values_are_on_the_screen_for_the_handler():
    # The point of D-CL-114: a handler who cannot see the record cannot
    # confirm that what the caller says matches it.
    checks = held_checks(_party(memorable="first pet"), _policy())
    shown = " ".join(f.value for c in checks for f in c.fields)
    for held in (POLICY_NO, "Argon Basalt 27", "1962-09-30",
                 "8 Cornice Row, Sampleton", "2209", "first pet"):
        assert held in shown


def test_the_prompts_read_to_the_caller_still_carry_no_held_value():
    # 07-RUNBOOK:4.1 — the handler asks; the caller states. What is read
    # aloud never contains the answer.
    checks = held_checks(_party(memorable="first pet"), _policy())
    rendered = " ".join(f"{c.kind} {c.prompt}" for c in checks)
    for secret in ("first pet", "2209", "8 Cornice Row", "1962-09-30"):
        assert secret not in rendered


def test_the_memorable_item_is_marked_ask_only():
    # Shown to the handler, never read out — the flag is how the screen knows.
    checks = held_checks(_party(memorable="first pet"), _policy())
    memorable = next(c for c in checks if c.kind == "memorable")
    assert all(f.ask_only for f in memorable.fields)
    others = [f for c in checks if c.kind != "memorable" for f in c.fields]
    assert not any(f.ask_only for f in others)


def test_the_third_check_shows_the_account_last_four_only_when_held():
    with_bank = next(c for c in held_checks(_party(), _policy())
                     if c.kind == "address_or_bank")
    assert len(with_bank.fields) == 2
    without = next(c for c in held_checks(_party(), _policy(bank_last4=None))
                   if c.kind == "address_or_bank")
    assert [f.value for f in without.fields] == ["8 Cornice Row, Sampleton"]


# ── the gate: present → tick → record ────────────────────────────────────
def test_ticking_three_of_four_passes():
    record = _confirm(VerificationGate(), THREE,
                      party=_party(memorable="first pet"))
    assert record.outcome == "passed"
    assert record.matched == THREE


def test_ticking_two_of_four_fails():
    record = _confirm(VerificationGate(), ("policy_no", "name_dob"),
                      party=_party(memorable="first pet"))
    assert record.outcome == "failed"


def test_a_tick_for_a_check_that_was_not_presented_does_not_count():
    # Three ticks, but one names a check this record does not hold — only the
    # presented ones count, so the attempt fails rather than sneaking through.
    record = _confirm(VerificationGate(),
                      ("policy_no", "name_dob", "memorable"))
    assert record.outcome == "failed"
    assert record.matched == ("policy_no", "name_dob")


def test_when_only_three_are_askable_all_three_are_needed():
    assert _confirm(VerificationGate(), THREE).outcome == "passed"
    assert _confirm(VerificationGate(), THREE[:2]).outcome == "failed"


def test_a_passed_record_carries_its_scope_actor_and_injected_time():
    record = _confirm(VerificationGate(), THREE)
    assert isinstance(record, VerificationRecord)
    assert (record.cn_ref, record.policy_no) == (CN, POLICY_NO)
    assert record.actor == "handler_a"
    assert record.at == AT
    assert record.verification_id


def test_presenting_alone_verifies_nothing():
    gate = VerificationGate()
    gate.present(cn_ref=CN, policy_no=POLICY_NO, party=_party(),
                 policy=_policy(), at=AT)
    assert gate.is_verified(CN, POLICY_NO) is False


# ── scope: one (CN-, policy) pair, and nothing else ──────────────────────
def test_a_passed_record_verifies_only_its_own_policy():
    gate = VerificationGate()
    _confirm(gate, THREE)
    assert gate.is_verified(CN, POLICY_NO) is True
    assert gate.is_verified(CN, "LP-20419876") is False


def test_a_passed_record_verifies_only_its_own_interaction():
    gate = VerificationGate()
    _confirm(gate, THREE)
    assert gate.is_verified("CN-1000000002", POLICY_NO) is False


def test_a_failed_record_does_not_verify():
    gate = VerificationGate()
    _confirm(gate, ("policy_no",))
    assert gate.is_verified(CN, POLICY_NO) is False


# ── expiry when the interaction closes (AD-CL-029) ───────────────────────
def test_closing_the_interaction_expires_the_verification():
    gate = VerificationGate()
    _confirm(gate, THREE)
    gate.expire_for_interaction(CN, at="2026-07-13T09:30:00")
    assert gate.is_verified(CN, POLICY_NO) is False


def test_expiry_does_not_delete_the_record():
    # The verification still happened; it simply no longer unlocks anything.
    gate = VerificationGate()
    _confirm(gate, THREE)
    gate.expire_for_interaction(CN, at="2026-07-13T09:30:00")
    kept = gate.records()
    assert len(kept) == 1 and kept[0].outcome == "passed"


# ── failed and abandoned outcomes are recorded ───────────────────────────
def test_a_failed_attempt_is_recorded():
    gate = VerificationGate()
    _confirm(gate, ("policy_no",))
    assert [r.outcome for r in gate.records()] == ["failed"]


def test_an_abandoned_attempt_is_recorded():
    gate = VerificationGate()
    gate.present(cn_ref=CN, policy_no=POLICY_NO, party=_party(),
                 policy=_policy(), at=AT)
    record = gate.abandon(cn_ref=CN, policy_no=POLICY_NO, actor="handler_a",
                          at="2026-07-13T09:05:00")
    assert record.outcome == "abandoned"
    assert gate.is_verified(CN, POLICY_NO) is False


def test_the_record_log_is_append_only():
    gate = VerificationGate()
    for forbidden in ("delete", "remove", "update", "edit", "clear", "pop"):
        assert not hasattr(gate, forbidden), f"append-only: {forbidden} must not exist"


def test_an_unknown_outcome_is_refused():
    with pytest.raises(ValueError):
        VerificationRecord(verification_id="V-1", cn_ref=CN, policy_no=POLICY_NO,
                           outcome="probably_fine", presented=(), matched=(),
                           actor="a", at=AT)


# ── the cannot-verify route (05-OPS:3.5) ─────────────────────────────────
def test_the_cannot_verify_route_offers_the_secure_alternative_and_cites_its_source():
    route = cannot_verify_route()
    assert route["source"] == "05-OPS:3.5"
    assert route["disclose"] is False
    assert route["alternatives"]


def test_the_cannot_verify_route_never_names_the_failing_element():
    # 07-RUNBOOK:4.1 — "do not say which element failed"; correction is itself
    # disclosure. The audit record keeps the detail; the caller-facing route
    # must not. The strongest form of that guarantee is that the route does not
    # vary with the failure at all, so there is nothing to leak.
    one = cannot_verify_route(failed_kinds=("name_dob",))
    several = cannot_verify_route(failed_kinds=("address_or_bank", "memorable"))
    assert one == several == cannot_verify_route()
    rendered = " ".join(str(v) for v in one.values())
    for leaked in ("name_dob", "address_or_bank", "memorable"):
        assert leaked not in rendered


def test_the_audit_record_keeps_which_checks_the_handler_confirmed():
    # The opposite of the rule above, and both must hold at once.
    record = _confirm(VerificationGate(), ("policy_no", "name_dob"))
    assert "policy_no" in record.matched
    assert "address_or_bank" not in record.matched
