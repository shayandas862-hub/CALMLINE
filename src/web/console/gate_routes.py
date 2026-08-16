"""The identity gate's HTTP surface — opening a contact, and verifying on it.

Split out of ``app.py`` at the 300-line rule. One job: the endpoints that turn
a caller on the phone into a recorded verification, plus the ``_unlock`` helper
the disclosure endpoints share.

The gate is checked **after** the role guard. An anonymous request is a 401, not
a 428 — a 428 would confirm to a caller with no session that the policy number
is worth retrying with one.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Request

from src.identity.authority import authorise, resolve_authority
from src.identity.gate import cannot_verify_route
from src.records.authorisations import AuthorityRecord
from src.web.console.verify_view import (
    authorities_view,
    checks_view,
    search_policies,
)


def build_unlock(gate: Any, events: Any, now: str) -> Callable[..., str]:
    """Return the helper that permits — or refuses — one disclosure.

    A refused read is logged as a ``bypass_attempt`` and a permitted one as a
    ``disclosure``, which is what makes "did anything leak?" answerable from the
    log rather than by reading the code.
    """

    def _unlock(policy_no: str, cn_ref: Optional[str], actor: str) -> str:
        record = gate.active_record(cn_ref, policy_no) if cn_ref else None
        if record is None:
            events.record(kind="bypass_attempt", policy_no=policy_no, actor=actor,
                          at=now, cn_ref=cn_ref)
            raise HTTPException(
                status_code=428,
                detail="verify the caller before disclosing personal data "
                       "(05-OPS:2.4)")
        events.record(kind="disclosure", policy_no=policy_no, actor=actor,
                      at=now, cn_ref=cn_ref)
        return record.verification_id

    return _unlock


def _adviser_authority(policy: Any, *, firm: str, frn: str,
                       now: str) -> Optional[AuthorityRecord]:
    """The policy's adviser LOA as an ``AuthorityRecord``, if it matches.

    `05-OPS:5.1` verifies the **firm** and its **FRN** on the FCA Register —
    not a named individual — and that is exactly what the corpus records: an
    `adviser_LOA` naming a firm, an FRN, a scope and an expiry, with no person
    attached. So an LOA claim resolves against the policy's own adviser record
    rather than against an invented party (D-CL-050).
    """
    loa = getattr(policy, "adviser_loa", None)
    if loa is None or loa.firm != firm or loa.frn != frn:
        return None
    # `expiry` is `YYYY-MM`; compare on the same precision.
    expired = loa.expiry < now[:7]
    return AuthorityRecord(
        authority_id=f"LOA-{loa.frn}", policy_no=policy.policy_no,
        party_id=loa.frn, type="LOA", scope=tuple(loa.scope),
        evidence_ref=f"{loa.firm} FRN {loa.frn}", verified_date=None,
        status="expired" if expired else "active")


def register_gate_routes(app: FastAPI, *, book: Any, session: Callable[..., Any],
                         interactions: Any, gate: Any, events: Any,
                         now: str) -> None:
    """Mount the interaction, verification and authority endpoints onto ``app``."""

    @app.post("/api/authority/check")
    def authority_check(body: dict, request: Request) -> dict:
        """May this third party do this, on this policy?

        Decides through `src.identity.authority`; this endpoint only resolves
        the claim to a record. Disclosing nothing on refusal is the module's
        job, and it is tested there.
        """
        session(request, {"front_office"})
        policy_no, claimed = body["policy_no"], body["claimed"]
        policy = book.get_policy(policy_no)
        if policy is None:
            raise HTTPException(status_code=404, detail=f"unknown policy {policy_no}")

        if claimed == "LOA":
            authority = _adviser_authority(policy, firm=body.get("firm", ""),
                                           frn=body.get("frn", ""), now=now)
        else:
            authority = resolve_authority(book.get_authorities(policy_no),
                                          party_id=body.get("party_id", ""),
                                          claimed=claimed)

        decision = authorise(authority, action=body["action"])
        return {"allowed": decision.allowed, "reason": decision.reason,
                "sources": list(decision.sources), "remedy": decision.remedy,
                "authority_id": decision.authority_id,
                "customer_direct_route": decision.customer_direct_route}

    @app.post("/api/interaction/open")
    def open_interaction(body: dict, request: Request) -> dict:
        """Start a contact and mint its `CN-` reference."""
        current = session(request, {"front_office"})
        row = interactions.open(
            policy_no=body["policy_no"], at=now, channel=body.get("channel"),
            caller_party_id=body.get("caller_party_id"),
            claimed_relationship=body.get("claimed_relationship", ""))
        return {"cn_ref": row.cn_ref, "policy_no": row.policy_no,
                "opened_at": row.opened_at, "actor": current.actor}

    @app.get("/api/policies/search")
    def search(request: Request, q: str = "") -> dict:
        """Find a policy by number or holder name — every desk's front door."""
        session(request, {"front_office", "back_office", "ops"})
        return search_policies(book, q)

    @app.post("/api/verify")
    def verify(body: dict, request: Request) -> dict:
        """Present the handler's panel, or record which checks were ticked.

        With no ``confirmed`` this presents: the held checks the handler
        compares the caller against, and everyone with authority on the policy
        (D-CL-114). With ``confirmed`` it records the handler's ticks. What is
        read aloud still carries no held value, and a failure still names no
        element (`07-RUNBOOK:4.1`) — those rules live in ``src.identity``.
        """
        current = session(request, {"front_office"})
        if "answers" in body:
            raise HTTPException(
                status_code=400,
                detail="the typed-answer contract was retired (D-CL-114) — "
                       "post the ticked checks as confirmed: [kinds]")
        policy_no, cn_ref = body["policy_no"], body["cn_ref"]
        policy = book.get_policy(policy_no)
        if policy is None:
            raise HTTPException(status_code=404, detail=f"unknown policy {policy_no}")
        party = book.get_party(policy.holder_party_id)

        if "confirmed" not in body:
            gate.present(cn_ref=cn_ref, policy_no=policy_no,
                         party=party, policy=policy, at=now)
            events.record(kind="presented", policy_no=policy_no,
                          actor=current.actor, at=now, cn_ref=cn_ref)
            return {"cn_ref": cn_ref,
                    "checks": checks_view(party, policy),
                    "authorities": authorities_view(book, policy)}

        record = gate.confirm(cn_ref=cn_ref, policy_no=policy_no, party=party,
                              policy=policy, ticked=tuple(body["confirmed"]),
                              actor=current.actor, at=now)
        events.record(kind=record.outcome, policy_no=policy_no,
                      actor=current.actor, at=now, cn_ref=cn_ref)
        if record.outcome == "passed":
            interactions.log(cn_ref, verification_ref=record.verification_id)
            return {"outcome": "passed", "verification_id": record.verification_id,
                    "cn_ref": cn_ref}
        # No detail about which check failed — correction is itself disclosure.
        return {"outcome": record.outcome, "cn_ref": cn_ref,
                "route": cannot_verify_route()}
