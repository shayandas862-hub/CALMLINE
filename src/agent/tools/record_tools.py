"""Tools that read the system of record.

``lookup_policy_record`` pulls the full record (holder + policy + current value)
onto the screen; ``get_transaction_history`` returns the ledger; ``get_valuation``
answers what the policy was worth on a given date. All three take a
``RecordStore`` (bound in when the tool is registered) and return plain dicts the
agent and the UI can use. None of them writes anything.

The verification requirement is **not** here — it is added when these are bound
for the agent (``src/agent/tools/verification.py``), because
``src/casework/assembly.py`` calls them directly and their signatures must not
move.
"""

from __future__ import annotations

from typing import Any

from src.records.models import format_gbp
from src.records.products import can_pay_cash_out
from src.records.valuation import entries_as_at, value_as_at


def lookup_policy_record(store: Any, policy_no: str) -> dict[str, Any]:
    """Return the holder, policy, and current value for ``policy_no``.

    Sum assured and premium now live on the LP cover component rather than on
    the policy, so they appear only for a product that has them.
    """
    policy = store.get_policy(policy_no)
    if policy is None:
        return {"found": False, "policy_no": policy_no}
    holder = store.get_party(policy.holder_party_id)
    cover = store.get_cover(policy_no)
    value = store.current_value(policy_no)
    detail: dict[str, Any] = {
        "product": policy.product,
        "status": policy.status,
        "start_date": policy.start_date,
        "can_pay_cash_out": can_pay_cash_out(policy, cover=cover),
    }
    if cover is not None:
        detail.update({
            "sum_assured_pence": cover.sum_assured_pence,
            "sum_assured": format_gbp(cover.sum_assured_pence),
            "premium_pence": cover.premium_pence,
            "premium": format_gbp(cover.premium_pence),
            "cover_basis": list(cover.basis),
        })
    return {
        "found": True,
        "policy_no": policy_no,
        "holder": None if holder is None else {
            "party_id": holder.party_id, "name": holder.name, "dob": holder.dob,
            "address": holder.registered_address,
        },
        "policy": detail,
        "current_value_pence": value,
        "current_value": format_gbp(value),
    }


def get_valuation(store: Any, policy_no: str, as_at: str) -> dict[str, Any]:
    """What ``policy_no`` was worth as at ``as_at``.

    A fold over the ledger rows dated on or before that moment — the same
    function the console's valuation endpoint uses, so the agent and the screen
    can never disagree about the past. ``as_at`` is supplied by the caller;
    nothing here reads the clock.
    """
    if store.get_policy(policy_no) is None:
        return {"found": False, "policy_no": policy_no}
    pence = value_as_at(store, policy_no, as_at)
    return {
        "found": True,
        "policy_no": policy_no,
        "as_at": as_at,
        "value_pence": pence,
        "value": format_gbp(pence),
    }


def get_transaction_history(store: Any, policy_no: str, as_at: str) -> dict[str, Any]:
    """The ordered ledger for ``policy_no`` **as at** ``as_at``.

    ``as_at`` is required and supplied by the caller — the tool binding passes
    the operative date, and nothing here reads the clock. It used to be absent
    entirely, so a dated question got the whole ledger: phase 4's live demo
    asked what a policy was worth in April and was handed movements that had not
    happened by then.

    The value reported is the value **at that date**, folded from the same rows,
    so the figure and the movements behind it can never disagree. ``get_valuation``
    is the template; both defer to ``src/records/valuation.py`` rather than
    re-deriving the fold.
    """
    if store.get_policy(policy_no) is None:
        return {"found": False, "policy_no": policy_no}
    entries = entries_as_at(store, policy_no, as_at)
    pence = value_as_at(store, policy_no, as_at)
    return {
        "found": True,
        "policy_no": policy_no,
        "as_at": as_at,
        "value_pence": pence,
        "value": format_gbp(pence),
        "entries": [
            {
                "seq": e.seq,
                "kind": e.transaction.kind,
                "amount_pence": e.transaction.amount_pence,
                "signed_pence": e.transaction.signed_pence,
                "amount": format_gbp(e.transaction.signed_pence),
                "balance_after_pence": e.balance_after_pence,
                "balance_after": format_gbp(e.balance_after_pence),
                "reason": e.transaction.reason,
                "at": e.transaction.at,
            }
            for e in entries
        ],
    }
