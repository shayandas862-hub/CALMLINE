"""The three disclosure endpoints — the record, its history, its valuation.

Split out of ``app.py`` at the 300-line rule, before v4.5 phase 3 modified it.
One job: the surfaces that emit personal data, which is why all three are gated
identically — **role first, then an in-scope passed verification, then the
data** (D-CL-044).

There are four disclosure surfaces, not three; the fourth is the agent when a
question names a policy, and it lives in ``agent_routes.py`` behind the same
``_unlock`` (D-CL-052). Gating only the first three refused the record at the
front door and handed it out at the side one.

Nothing here is a fold over stored state: the valuation adds up the ledger rows
on or before its operative date, so a value can never drift out of step with the
movements behind it.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Request

from src.agent.tools.record_tools import get_transaction_history, lookup_policy_record
from src.records.models import format_gbp
from src.records.valuation import entries_as_at, value_as_at


def register_policy_routes(app: FastAPI, *, book: Any,
                           session: Callable[..., Any],
                           unlock: Callable[..., str], now: str) -> None:
    """Mount the record, history and valuation endpoints onto ``app``."""

    @app.get("/api/policy/{policy_no}")
    def policy(policy_no: str, request: Request,
               cn_ref: Optional[str] = None) -> dict:
        current = session(request, {"front_office"})
        verification_id = unlock(policy_no, cn_ref, current.actor)
        record = lookup_policy_record(book, policy_no)
        record["meta"] = {"verification_id": verification_id, "cn_ref": cn_ref}
        return record

    @app.get("/api/policy/{policy_no}/history")
    def policy_history(policy_no: str, request: Request,
                       cn_ref: Optional[str] = None) -> dict:
        current = session(request, {"front_office"})
        verification_id = unlock(policy_no, cn_ref, current.actor)
        history = get_transaction_history(book, policy_no, now[:10])
        history["meta"] = {"verification_id": verification_id, "cn_ref": cn_ref}
        return history

    @app.get("/api/policy/{policy_no}/value")
    def policy_value(policy_no: str, request: Request,
                     as_at: Optional[str] = None,
                     cn_ref: Optional[str] = None) -> dict:
        """What the policy was worth on a date — a fold over its own ledger.

        ``as_at`` defaults to the console's injected now, never the wall clock,
        so the same question gives the same answer whenever it is asked.
        """
        current = session(request, {"front_office", "back_office"})
        if book.get_policy(policy_no) is None:
            raise HTTPException(status_code=404,
                                detail=f"unknown policy {policy_no}")
        verification_id = unlock(policy_no, cn_ref, current.actor)
        operative = as_at or now[:10]
        entries = entries_as_at(book, policy_no, operative)
        value = value_as_at(book, policy_no, operative)
        return {"policy_no": policy_no, "as_at": operative,
                "value_pence": value, "value": format_gbp(value),
                "entries_counted": len(entries),
                "meta": {"verification_id": verification_id, "cn_ref": cn_ref}}
