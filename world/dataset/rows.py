"""One policy, to a line of JSON and back.

A row carries the policy, its whole ledger, its non-money events, its bank
mandate and its operational history — **everything hanging off that policy**,
because the unit the world is read and reviewed in is the policy, not the table.

Two things are deliberately *not* stored:

- **the current value.** It is the sum of the movements, everywhere else in the
  system, and a file carrying both is a file that can disagree with itself.
  What is stored is each movement's ``balance_after_pence``, which is a fact
  about that movement rather than a second copy of the answer — and the reader
  re-folds the ledger and refuses a row where the two disagree.
- **anything derived from the people file.** Names and addresses live in
  `people.jsonl` and are referenced by party id, so a policy row cannot drift
  out of step with its holder.

Every decode names what it could not find, down to the field and the policy,
because "policies.jsonl is wrong" is not something anybody can act on.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Optional

from src.records.authorisations import AuthorityRecord, BankMandate, MandateChange
from src.records.models import AdviserLoa, LedgerEntry, Transaction, Trust
from world.dataset.manifest import DatasetError
from world.lifetimes.events import LifeEvent
from world.operations.shapes import (
    PlannedCase,
    PlannedContact,
    PlannedEvidence,
    PolicyOperations,
)

POLICY_KEYS = ("policy_no", "product", "status", "start", "holder_party_id",
               "band", "headline_value_pence", "entries", "events",
               "bank_mandate", "operations", "trust", "adviser_loa",
               "authorities")


def _need(row: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in row:
        raise DatasetError(f"{where}: missing field {key!r}")
    return row[key]


# ── encoding ─────────────────────────────────────────────────────────────

def encode_policy(policy: Any, mandate: Optional[BankMandate],
                  operations: Optional[PolicyOperations], *,
                  trust: Optional[Trust] = None,
                  adviser_loa: Optional[AdviserLoa] = None,
                  authorities: tuple = ()) -> dict[str, Any]:
    """One finished policy and everything hanging off it, as a plain dict."""
    return {
        "policy_no": policy.policy_no,
        "product": policy.product,
        "status": policy.status,
        "start": policy.start.isoformat(),
        "holder_party_id": policy.holder_party_id,
        "band": policy.band,
        "headline_value_pence": policy.headline_value_pence,
        "entries": [_encode_entry(entry) for entry in policy.entries],
        "events": [{"on": event.on.isoformat(), "kind": event.kind,
                    "detail": event.detail} for event in policy.events],
        "bank_mandate": _encode_mandate(mandate),
        "operations": _encode_operations(operations),
        "trust": _encode_trust(trust),
        "adviser_loa": _encode_loa(adviser_loa),
        "authorities": [{"authority_id": a.authority_id, "party_id": a.party_id,
                         "type": a.type, "scope": list(a.scope),
                         "evidence_ref": a.evidence_ref,
                         "verified_date": a.verified_date, "status": a.status}
                        for a in authorities],
    }


def _encode_trust(trust: Optional[Trust]) -> Optional[dict[str, Any]]:
    if trust is None:
        return None
    return {"kind": trust.kind, "executed": trust.executed,
            "trustees": list(trust.trustees), "registrable": trust.registrable,
            "urn": trust.urn}


def _encode_loa(loa: Optional[AdviserLoa]) -> Optional[dict[str, Any]]:
    if loa is None:
        return None
    return {"firm": loa.firm, "frn": loa.frn, "scope": list(loa.scope),
            "expiry": loa.expiry, "individuals": list(loa.individuals)}


def _encode_entry(entry: LedgerEntry) -> dict[str, Any]:
    txn = entry.transaction
    return {"seq": entry.seq, "txn_id": txn.txn_id, "kind": txn.kind,
            "amount_pence": txn.amount_pence, "reason": txn.reason,
            "actor": txn.actor, "at": txn.at,
            "balance_after_pence": entry.balance_after_pence}


def _encode_mandate(mandate: Optional[BankMandate]) -> Optional[dict[str, Any]]:
    if mandate is None:
        return None
    return {"account_last4": mandate.account_last4, "verified": mandate.verified,
            "hold_until": mandate.hold_until,
            "change_history": [{"at": c.at, "actor": c.actor, "note": c.note}
                               for c in mandate.change_history]}


def _encode_operations(operations: Optional[PolicyOperations]) -> dict[str, Any]:
    if operations is None:
        return {"contacts": [], "cases": []}
    return {
        "contacts": [{"cn_ref": c.cn_ref, "on": c.on.isoformat(),
                      "channel": c.channel, "intent": c.intent,
                      "outcome": c.outcome, "note_slot": c.note_slot}
                     for c in operations.contacts],
        "cases": [{"cw_ref": k.cw_ref, "cn_ref": k.cn_ref,
                   "opened_on": k.opened_on.isoformat(),
                   "closed_on": k.closed_on.isoformat(), "request": k.request,
                   "type": k.type, "status": k.status,
                   "human_decision": k.human_decision,
                   "authorised_movement_on": (
                       k.authorised_movement_on.isoformat()
                       if k.authorised_movement_on else None),
                   "evidence": [{"evidence_id": e.evidence_id,
                                 "requirement": e.requirement,
                                 "requirement_source": e.requirement_source,
                                 "received_on": e.received_on.isoformat(),
                                 "satisfies": e.satisfies,
                                 "received_via": e.received_via}
                                for e in k.evidence]}
                  for k in operations.cases],
    }


# ── decoding ─────────────────────────────────────────────────────────────

def decode_policy(row: Mapping[str, Any], where: str):
    """``(BuiltPolicy, BankMandate | None, PolicyOperations, Authorities)`` —
    or a refusal.

    Imported lazily: `world.lifetimes.build` imports a good deal of the world,
    and the dataset is read in places that have no need of the builder.
    """
    from world.lifetimes.build import BuiltPolicy

    policy_no = row.get("policy_no")
    where = f"{where} {policy_no}" if policy_no else where
    for key in POLICY_KEYS:
        _need(row, key, where)

    built = BuiltPolicy(
        policy_no=row["policy_no"], product=row["product"], status=row["status"],
        start=date.fromisoformat(row["start"]),
        holder_party_id=row["holder_party_id"],
        entries=tuple(_decode_entry(e, row["policy_no"], where)
                      for e in row["entries"]),
        events=tuple(LifeEvent(on=date.fromisoformat(_need(e, "on", where)),
                               kind=_need(e, "kind", where),
                               detail=_need(e, "detail", where))
                     for e in row["events"]),
        band=row["band"], headline_value_pence=row["headline_value_pence"])

    return (built,
            _decode_mandate(row["bank_mandate"], row["policy_no"]),
            _decode_operations(row["operations"], row["policy_no"], where),
            _decode_authority(row, row["policy_no"]))


def _decode_authority(row: Mapping[str, Any], policy_no: str):
    """``(Trust | None, AdviserLoa | None, tuple[AuthorityRecord, ...])``."""
    trust = row["trust"]
    loa = row["adviser_loa"]
    return (
        Trust(kind=trust["kind"], executed=trust["executed"],
              trustees=tuple(trust["trustees"]),
              registrable=trust["registrable"], urn=trust["urn"])
        if trust else None,
        AdviserLoa(firm=loa["firm"], frn=loa["frn"], scope=tuple(loa["scope"]),
                   expiry=loa["expiry"],
                   individuals=tuple(loa["individuals"])) if loa else None,
        tuple(AuthorityRecord(
            authority_id=a["authority_id"], policy_no=policy_no,
            party_id=a["party_id"], type=a["type"], scope=tuple(a["scope"]),
            evidence_ref=a["evidence_ref"], verified_date=a["verified_date"],
            status=a["status"]) for a in row["authorities"]),
    )


def _decode_entry(row: Mapping[str, Any], policy_no: str,
                  where: str) -> LedgerEntry:
    return LedgerEntry(
        seq=_need(row, "seq", where),
        transaction=Transaction(
            txn_id=_need(row, "txn_id", where), policy_no=policy_no,
            kind=_need(row, "kind", where),
            amount_pence=_need(row, "amount_pence", where),
            reason=_need(row, "reason", where), actor=_need(row, "actor", where),
            at=_need(row, "at", where)),
        balance_after_pence=_need(row, "balance_after_pence", where))


def _decode_mandate(row: Optional[Mapping[str, Any]],
                    policy_no: str) -> Optional[BankMandate]:
    if row is None:
        return None
    return BankMandate(
        policy_no=policy_no, account_last4=row["account_last4"],
        verified=row["verified"], hold_until=row["hold_until"],
        change_history=tuple(MandateChange(at=c["at"], actor=c["actor"],
                                           note=c["note"])
                             for c in row["change_history"]))


def _decode_operations(row: Mapping[str, Any], policy_no: str,
                       where: str) -> PolicyOperations:
    return PolicyOperations(
        policy_no=policy_no,
        contacts=tuple(PlannedContact(
            cn_ref=_need(c, "cn_ref", where), policy_no=policy_no,
            on=date.fromisoformat(_need(c, "on", where)),
            channel=c["channel"], intent=c["intent"], outcome=c["outcome"],
            note_slot=c["note_slot"]) for c in row["contacts"]),
        cases=tuple(PlannedCase(
            cw_ref=_need(k, "cw_ref", where), policy_no=policy_no,
            cn_ref=k["cn_ref"], opened_on=date.fromisoformat(k["opened_on"]),
            closed_on=date.fromisoformat(k["closed_on"]), request=k["request"],
            type=k["type"], status=k["status"],
            human_decision=k["human_decision"],
            evidence=tuple(PlannedEvidence(
                evidence_id=e["evidence_id"], requirement=e["requirement"],
                requirement_source=e["requirement_source"],
                received_on=date.fromisoformat(e["received_on"]),
                satisfies=e["satisfies"], received_via=e["received_via"])
                for e in k["evidence"]),
            authorised_movement_on=(
                date.fromisoformat(k["authorised_movement_on"])
                if k["authorised_movement_on"] else None))
            for k in row["cases"]),
    )
