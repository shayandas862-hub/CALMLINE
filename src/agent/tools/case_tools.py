"""Case tools — raise a case, and run a compliance pre-check.

``raise_case`` builds a case request and hands it to a ``sink`` (the back-office
queue, wired in a later phase), returning whatever the sink creates. It writes
no money. ``run_compliance_check`` assembles a checklist whose every line cites a
clause and recommends ``proceed`` only when every item passes — a fail or an
unverifiable line means ``do_not_proceed`` (never an automatic rejection).
"""

from __future__ import annotations

from typing import Any, Callable

_VALID_VERDICTS = {"pass", "fail", "unverifiable"}


def raise_case(sink: Callable[[dict[str, Any]], Any], *, policy_no: str, request: str,
               priority: str = "medium") -> Any:
    """Open a case for ``policy_no`` and send it to the queue ``sink``."""
    case_request = {
        "policy_no": policy_no,
        "request": request,
        "priority": priority,
        "status": "pending_review",
    }
    return sink(case_request)


def run_compliance_check(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Assemble a cited checklist and a proceed / do-not-proceed recommendation."""
    checklist: list[dict[str, Any]] = []
    for item in items:
        clause_ref = item.get("clause_ref")
        verdict = item.get("verdict")
        if not clause_ref:
            raise ValueError(f"every checklist line must cite a clause: {item!r}")
        if verdict not in _VALID_VERDICTS:
            raise ValueError(f"invalid verdict {verdict!r} (expected one of {_VALID_VERDICTS})")
        checklist.append({
            "requirement": item.get("requirement", ""),
            "clause_ref": clause_ref,
            "verdict": verdict,
        })
    all_pass = all(line["verdict"] == "pass" for line in checklist)
    return {
        "checklist": checklist,
        "recommendation": "proceed" if all_pass else "do_not_proceed",
    }
