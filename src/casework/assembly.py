"""Assemble the "whole story" a reviewer needs to work a case.

Combines the case, the policy record (via the phase-2 ``lookup_policy_record``
tool), and the cited pre-check — and splits the checklist into what has been
received (passing lines) and what is still needed (failing / unverifiable).
"""

from __future__ import annotations

from typing import Any

from src.agent.tools.record_tools import lookup_policy_record
from src.casework.models import Case


def _proposed_summary(case: Case) -> Any:
    if case.proposed is None:
        return None
    p = case.proposed
    return {"policy_no": p.policy_no, "kind": p.kind, "amount_pence": p.amount_pence,
            "reason": p.reason, "requires_human": p.requires_human}


def assemble_case_detail(case: Case, record_store: Any) -> dict[str, Any]:
    """Return the full case view: record + checklist + received / still-needed."""
    received = [line for line in case.checklist if line.get("verdict") == "pass"]
    needed = [line for line in case.checklist if line.get("verdict") != "pass"]
    return {
        "case_id": case.case_id,
        "policy_no": case.policy_no,
        "request": case.request,
        "priority": case.priority,
        "status": case.status,
        "sla_due": case.sla_due,
        "recommendation": case.recommendation,
        "record": lookup_policy_record(record_store, case.policy_no),
        "checklist": case.checklist,
        "received": received,
        "needed": needed,
        "proposed": _proposed_summary(case),
        "audit": case.audit,
    }
