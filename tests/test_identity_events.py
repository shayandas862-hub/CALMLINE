"""v4 phase 3 · task 2 — the gate event log.

Five kinds — `presented | passed | failed | disclosure | bypass_attempt` — each
carrying `cn_ref`, `policy_no`, `actor` and an injected `at`. This is the seam
phase 5's TraceStore subsumes, so it stays a narrow store and not a framework.

Append-only **by absence**, exactly like `src/records/changelog.py`: there is no
delete, update, edit or clear to call. A log that can be edited is not evidence.

The log exists to answer one question the phase is judged on: *did anything get
disclosed without a passed verification behind it?* `disclosures_without_pass()`
is that question in code — the gate-bypass count phase 5 reports, and the done
criterion this phase asserts across the whole suite run.
"""

import pytest

from src.identity.events import GATE_EVENT_KINDS, GateEvent, GateEventLog

AT = "2026-07-13T09:00:00"
CN = "CN-1000000001"
POLICY_NO = "HB-40582213"


def _log_with_pass() -> GateEventLog:
    log = GateEventLog()
    log.record(kind="presented", cn_ref=CN, policy_no=POLICY_NO,
               actor="handler_a", at=AT)
    log.record(kind="passed", cn_ref=CN, policy_no=POLICY_NO,
               actor="handler_a", at="2026-07-13T09:01:00")
    return log


# ── the event shape ──────────────────────────────────────────────────────
def test_the_five_kinds_are_the_vocabulary():
    assert GATE_EVENT_KINDS == frozenset(
        {"presented", "passed", "failed", "disclosure", "bypass_attempt"})


def test_an_event_carries_its_scope_actor_and_injected_time():
    event = GateEvent(seq=1, kind="disclosure", cn_ref=CN, policy_no=POLICY_NO,
                      actor="handler_a", at=AT)
    assert (event.kind, event.cn_ref, event.policy_no) == ("disclosure", CN, POLICY_NO)
    assert event.actor == "handler_a" and event.at == AT


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        GateEvent(seq=1, kind="probably_fine", cn_ref=CN, policy_no=POLICY_NO,
                  actor="a", at=AT)


def test_a_bypass_attempt_may_have_no_interaction():
    # Someone hitting a disclosure endpoint with no interaction open has no
    # CN- to record. That is the event worth catching, so it must be recordable.
    event = GateEvent(seq=1, kind="bypass_attempt", cn_ref=None,
                      policy_no=POLICY_NO, actor="handler_a", at=AT)
    assert event.cn_ref is None


# ── the log is append-only ───────────────────────────────────────────────
def test_the_log_sequences_events_from_one():
    log = GateEventLog()
    first = log.record(kind="presented", cn_ref=CN, policy_no=POLICY_NO,
                       actor="a", at=AT)
    second = log.record(kind="failed", cn_ref=CN, policy_no=POLICY_NO,
                        actor="a", at=AT)
    assert (first.seq, second.seq) == (1, 2)


def test_the_log_exposes_no_way_to_edit_or_remove_an_event():
    log = GateEventLog()
    for forbidden in ("delete", "remove", "update", "edit", "clear", "pop"):
        assert not hasattr(log, forbidden), f"append-only: {forbidden} must not exist"


def test_the_event_list_is_an_immutable_snapshot():
    log = GateEventLog()
    log.record(kind="presented", cn_ref=CN, policy_no=POLICY_NO, actor="a", at=AT)
    snapshot = log.events()
    assert isinstance(snapshot, tuple)
    with pytest.raises((AttributeError, TypeError)):
        snapshot.append(None)          # type: ignore[attr-defined]
    assert len(log.events()) == 1


def test_events_keep_the_order_they_were_recorded():
    log = _log_with_pass()
    assert [e.kind for e in log.events()] == ["presented", "passed"]


# ── filtering ────────────────────────────────────────────────────────────
def test_events_filter_by_interaction():
    log = _log_with_pass()
    log.record(kind="presented", cn_ref="CN-1000000002", policy_no=POLICY_NO,
               actor="a", at=AT)
    assert len(log.for_interaction(CN)) == 2


def test_events_filter_by_policy():
    log = _log_with_pass()
    log.record(kind="presented", cn_ref=CN, policy_no="LP-20419876",
               actor="a", at=AT)
    assert len(log.for_policy(POLICY_NO)) == 2


def test_events_filter_by_kind():
    log = _log_with_pass()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO, actor="a", at=AT)
    assert len(log.of_kind("disclosure")) == 1


# ── the gate-bypass question (the phase's done criterion) ────────────────
def test_a_disclosure_behind_a_passed_verification_is_not_a_bypass():
    log = _log_with_pass()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO,
               actor="handler_a", at="2026-07-13T09:02:00")
    assert log.disclosures_without_pass() == ()


def test_a_disclosure_with_no_passed_verification_is_a_bypass():
    log = GateEventLog()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO,
               actor="handler_a", at=AT)
    assert len(log.disclosures_without_pass()) == 1


def test_a_pass_on_a_different_policy_does_not_cover_the_disclosure():
    log = _log_with_pass()
    log.record(kind="disclosure", cn_ref=CN, policy_no="LP-20419876",
               actor="handler_a", at="2026-07-13T09:02:00")
    assert len(log.disclosures_without_pass()) == 1


def test_a_pass_on_a_different_interaction_does_not_cover_the_disclosure():
    log = _log_with_pass()
    log.record(kind="disclosure", cn_ref="CN-1000000002", policy_no=POLICY_NO,
               actor="handler_a", at="2026-07-13T09:02:00")
    assert len(log.disclosures_without_pass()) == 1


def test_a_pass_recorded_after_the_disclosure_does_not_cover_it():
    # Order is the whole point: verify THEN disclose. A pass that arrives
    # afterwards is a bypass with tidy paperwork.
    log = GateEventLog()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO, actor="a", at=AT)
    log.record(kind="passed", cn_ref=CN, policy_no=POLICY_NO, actor="a",
               at="2026-07-13T09:05:00")
    assert len(log.disclosures_without_pass()) == 1


def test_a_failed_verification_does_not_cover_a_disclosure():
    log = GateEventLog()
    log.record(kind="failed", cn_ref=CN, policy_no=POLICY_NO, actor="a", at=AT)
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO, actor="a",
               at="2026-07-13T09:02:00")
    assert len(log.disclosures_without_pass()) == 1


def test_the_bypass_count_is_the_headline_number():
    log = GateEventLog()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO, actor="a", at=AT)
    assert log.bypass_count() == 1


def test_a_clean_log_reports_zero_bypasses():
    log = _log_with_pass()
    log.record(kind="disclosure", cn_ref=CN, policy_no=POLICY_NO, actor="a",
               at="2026-07-13T09:02:00")
    assert log.bypass_count() == 0
