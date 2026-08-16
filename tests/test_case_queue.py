"""v3 phase 3 · Task 2 — the CaseQueue.

Opens cases (it is the sink the phase-2 `raise_case` tool hands to), ranks them
by priority then SLA, and attaches a pre-check result to a case.
"""

import re

import pytest

from src.agent.tools.case_tools import raise_case
from src.agent.tools.money_tools import record_transaction
from src.casework.queue import CaseQueue, QueueError
from src.records.models import gbp


def test_open_mints_sequential_cw_references():
    # The KB's grammar (`05-OPS:1.4`), replacing v3's CASE-0001 ids.
    q = CaseQueue()
    a = q.open({"policy_no": "LP-20419876", "request": "Death claim", "priority": "high",
                "status": "pending_review"})
    b = q.open({"policy_no": "RA-77103428", "request": "Payout", "priority": "low",
                "status": "pending_review"})
    assert re.fullmatch(r"CW-\d{9}", a.cw_ref)
    assert a.case_id == a.cw_ref          # the reference IS the id
    assert b.cw_ref != a.cw_ref
    assert int(b.cw_ref[3:]) == int(a.cw_ref[3:]) + 1


def test_open_carries_the_case_type_when_given_one():
    q = CaseQueue()
    case = q.open({"policy_no": "LP-20419876", "request": "DSAR", "type": "DSAR"})
    assert case.type == "DSAR"


def test_open_defaults_to_a_servicing_case():
    q = CaseQueue()
    assert q.open({"policy_no": "LP-20419876", "request": "x"}).type == "servicing"


def test_raise_case_tool_opens_a_case_in_the_queue():
    q = CaseQueue()
    case = raise_case(q.open, policy_no="LP-20419876", request="Death claim", priority="high")
    assert case.policy_no == "LP-20419876"
    assert case.priority == "high"
    assert q.get(case.case_id) is case


def test_get_missing_case_raises():
    with pytest.raises(QueueError):
        CaseQueue().get("CASE-9999")


def test_list_ranked_orders_by_priority_then_time_left():
    q = CaseQueue()
    q.open({"policy_no": "P1", "request": "r", "priority": "low"}, sla_due="2026-07-02T11:00:00")
    q.open({"policy_no": "P2", "request": "r", "priority": "high"}, sla_due="2026-07-02T18:00:00")
    q.open({"policy_no": "P3", "request": "r", "priority": "high"}, sla_due="2026-07-02T12:00:00")
    ranked = q.list_ranked(now="2026-07-02T10:00:00")
    # both highs first; among them the one due sooner (P3) leads; low last
    assert [c.policy_no for c in ranked] == ["P3", "P2", "P1"]


def test_attach_precheck_sets_recommendation_checklist_and_proposal():
    q = CaseQueue()
    case = q.open({"policy_no": "LP-20419876", "request": "withdrawal", "priority": "high"})
    proposed = record_transaction(policy_no="LP-20419876", kind="withdrawal",
                                  amount_pence=gbp(5_000), reason="request", actor="agent",
                                  at="2026-07-02T10:00:00")
    q.attach_precheck(case.case_id,
                      checklist=[{"requirement": "in force", "clause_ref": "WL-1.2", "verdict": "pass"}],
                      recommendation="proceed", proposed=proposed)
    got = q.get(case.case_id)
    assert got.recommendation == "proceed"
    assert got.checklist[0]["clause_ref"] == "WL-1.2"
    assert got.proposed is proposed
