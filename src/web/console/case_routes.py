"""The case endpoints — raising work, ranking it, and the one approval.

Split out of ``app.py`` at the 300-line rule, before v4.5 phase 3 modified it.

**Approval is the only path that moves money**, and it stays that way here: the
raise path produces a *proposal* — validated, uncommitted, carrying no write
capability — and only ``approve_case`` commits it, under a named human at a role
the server checked. Nothing in this module writes the ledger directly.

Raising a case reads the record, so it is a disclosure like any other and goes
through the same ``unlock``. The case then carries forward **which** verification
permitted it, so an approval months later can still say what the caller was
verified against.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Request

from src.agent.tools.case_tools import run_compliance_check
from src.agent.tools.money_tools import record_transaction
from src.authority.checklist import money_out_checklist
from src.authority.sla import sla_due
from src.casework.approval import ApprovalError, approve_case
from src.casework.assembly import assemble_case_detail
from src.casework.models import sla_seconds_left
from src.casework.queue import QueueError
from src.records.models import gbp


def register_case_routes(app: FastAPI, *, book: Any, session: Callable[..., Any],
                         unlock: Callable[..., str], queue: Any,
                         now: str) -> None:
    """Mount the raise, list, detail and approve endpoints onto ``app``."""

    @app.post("/api/cases/raise")
    def raise_endpoint(body: dict, request: Request) -> dict:
        current = session(request, {"front_office"})
        policy_no = body["policy_no"]
        req = body.get("request", "case")
        priority = body.get("priority", "medium")
        amount = int(body.get("amount_pence", gbp(5_000)))
        # Raising a case reads the record, so it is a disclosure like any other
        # — and the case carries forward which verification permitted it.
        cn_ref = body.get("cn_ref")
        verification_id = unlock(policy_no, cn_ref, current.actor)
        case = queue.open({"policy_no": policy_no, "request": req,
                           "priority": priority, "status": "pending_review",
                           "cn_ref": cn_ref, "verification_id": verification_id},
                          sla_due=sla_due(now, priority))

        proposed: Optional[Any] = None
        checklist = money_out_checklist(book, policy_no, amount_pence=amount)
        if all(row["verdict"] == "pass" for row in checklist):
            proposed = record_transaction(policy_no=policy_no, kind="withdrawal",
                                          amount_pence=amount, reason=req,
                                          actor=current.actor, at=now)

        result = run_compliance_check(checklist)
        queue.attach_precheck(
            case.case_id, checklist=result["checklist"],
            recommendation=result["recommendation"],
            proposed=proposed if result["recommendation"] == "proceed" else None)
        return {"case_id": case.case_id,
                "recommendation": result["recommendation"],
                "status": case.status, "cn_ref": case.cn_ref,
                "verification_id": case.verification_id}

    @app.get("/api/cases")
    def cases(request: Request) -> list[dict]:
        session(request, {"back_office"})
        return [
            {"case_id": c.case_id, "policy_no": c.policy_no, "request": c.request,
             "priority": c.priority, "status": c.status,
             "recommendation": c.recommendation,
             "sla_seconds_left": sla_seconds_left(c, now)}
            for c in queue.list_ranked(now)
        ]

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, request: Request) -> dict:
        session(request, {"back_office"})
        try:
            return assemble_case_detail(queue.get(case_id), book)
        except QueueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/cases/{case_id}/approve")
    def approve(case_id: str, request: Request) -> dict:
        current = session(request, {"back_office"})
        try:
            approve_case(queue, book, case_id, reviewer=current.actor, at=now,
                         txn_id=f"TXN-{case_id}", role=current.role)
        except QueueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ApprovalError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return assemble_case_detail(queue.get(case_id), book)
