"""v3 phase 3 · Task 3 — assemble the whole-story case detail for the reviewer."""

from src.casework.assembly import assemble_case_detail
from src.casework.queue import CaseQueue
from src.records.models import gbp
from src.records.seed import build_seed_book


def _case_with_mixed_precheck():
    book = build_seed_book()
    q = CaseQueue()
    case = q.open({"policy_no": "LP-20419876", "request": "Death claim", "priority": "high"})
    q.attach_precheck(case.case_id, checklist=[
        {"requirement": "Policy in force", "clause_ref": "WL-1.2", "verdict": "pass"},
        {"requirement": "Death certificate received", "clause_ref": "CH-2.2", "verdict": "fail"},
    ], recommendation="do_not_proceed")
    return q.get(case.case_id), book


def test_assembly_includes_the_policy_record_and_value():
    case, book = _case_with_mixed_precheck()
    detail = assemble_case_detail(case, book)
    assert detail["record"]["holder"]["name"] == "Theta Meridian 12"
    assert detail["record"]["current_value_pence"] == gbp(46_210)
    assert detail["request"] == "Death claim"
    assert detail["recommendation"] == "do_not_proceed"


def test_assembly_splits_received_from_still_needed_using_the_checklist():
    case, book = _case_with_mixed_precheck()
    detail = assemble_case_detail(case, book)
    received = [r["clause_ref"] for r in detail["received"]]
    needed = [n["clause_ref"] for n in detail["needed"]]
    assert received == ["WL-1.2"]   # the passing line
    assert needed == ["CH-2.2"]     # the failing line is still outstanding
