"""v3 phase 2 · Task 5 — the case tools.

raise_case hands a case to a sink (the back-office queue, provided later);
run_compliance_check assembles a checklist whose every line cites a clause and
recommends proceed only if every item passes.
"""

import pytest

from src.agent.tools.case_tools import raise_case, run_compliance_check


def test_raise_case_sends_the_request_to_the_sink_and_returns_the_case():
    created = []

    def sink(req):
        case = {**req, "case_id": "CASE-0042"}
        created.append(case)
        return case

    out = raise_case(sink, policy_no="WL-88213", request="Death claim", priority="high")
    assert out["case_id"] == "CASE-0042"
    assert created[0]["policy_no"] == "WL-88213"
    assert created[0]["request"] == "Death claim"
    assert created[0]["priority"] == "high"
    assert created[0]["status"] == "pending_review"


def test_compliance_check_recommends_proceed_when_every_item_passes():
    items = [
        {"requirement": "Death certificate received", "clause_ref": "CH-2.2", "verdict": "pass"},
        {"requirement": "Policy in force", "clause_ref": "WL-1.2", "verdict": "pass"},
    ]
    out = run_compliance_check(items)
    assert out["recommendation"] == "proceed"
    assert len(out["checklist"]) == 2


def test_compliance_check_recommends_do_not_proceed_on_any_non_pass():
    for bad in ("fail", "unverifiable"):
        items = [
            {"requirement": "Death certificate received", "clause_ref": "CH-2.2", "verdict": bad},
            {"requirement": "Policy in force", "clause_ref": "WL-1.2", "verdict": "pass"},
        ]
        assert run_compliance_check(items)["recommendation"] == "do_not_proceed"


def test_compliance_check_requires_a_clause_on_every_line():
    with pytest.raises(ValueError):
        run_compliance_check([{"requirement": "no clause", "verdict": "pass"}])


def test_compliance_check_rejects_an_unknown_verdict():
    with pytest.raises(ValueError):
        run_compliance_check([{"requirement": "x", "clause_ref": "CH-2.2", "verdict": "maybe"}])
