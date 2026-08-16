"""The committed world, projected into the shape the loader writes.

One projection, used by the verify command as the answer key: every table as
a dictionary keyed the way the database keys it, every value already
normalised to plain strings and integers. Kept beside the loader on purpose —
if the mapping ever changes there, the comparison changes here or the verify
command says so on the next run, which is the point of having one.
"""

from __future__ import annotations

import json
from typing import Any, Optional

# The schema's own default: historical cases are loaded without a priority
# and take the column default. Recorded here once, so the projection and the
# database agree about what "unstated" reads back as.
HISTORICAL_PRIORITY = "medium"


def _normalised(obj: Any) -> Optional[dict]:
    """A dataclass as jsonb returns it — tuples to lists, or None."""
    return None if obj is None else json.loads(json.dumps(obj.__dict__))


def project(world: Any, only: Any = None) -> dict:
    """Every table the loader writes, as `{table: {key: row}}`."""
    wanted = frozenset(only) if only is not None else None
    policies = [policy for policy in world.policies
                if wanted is None or policy.policy_no in wanted]

    snapshot: dict[str, Any] = {
        # the sweep completes the people table whatever the policy scope
        "parties": {
            person["party_id"]: {
                "name": person["name"], "dob": person["dob"],
                "registered_address": person["registered_address"],
                "contact": person.get("contact") or {}}
            for person in world.people if "party_id" in person},
        "policies": {}, "mandates": {}, "authorities": {},
        "transactions": {}, "events": {}, "interactions": {},
        "notes": {}, "cases": {}, "narratives": {}, "evidence": {},
        "values": {},
    }

    stories = {row["ref"]: row for row in world.stories
               if wanted is None or row["policy_no"] in wanted}

    for policy in policies:
        policy_no = policy.policy_no
        mandate = world.bank_mandates.get(policy_no)
        snapshot["policies"][policy_no] = {
            "product": policy.product, "status": policy.status,
            "start_date": policy.start.isoformat(),
            "holder_party_id": policy.holder_party_id,
            "trust": _normalised(world.trusts.get(policy_no)),
            "adviser_loa": _normalised(world.adviser_mandates.get(policy_no)),
            "bank_last4": mandate.account_last4 if mandate else None,
        }
        if mandate is not None:
            snapshot["mandates"][policy_no] = {
                "account_last4": mandate.account_last4,
                "verified": mandate.verified,
                "hold_until": mandate.hold_until,
                "change_history": [change.__dict__ for change
                                   in mandate.change_history]}
        for record in world.authorities.get(policy_no, ()):
            snapshot["authorities"][record.authority_id] = {
                "policy_no": policy_no, "party_id": record.party_id,
                "type": record.type, "scope": list(record.scope),
                "status": record.status}
        for entry in policy.entries:
            snapshot["transactions"][(policy_no, entry.seq)] = {
                "txn_id": entry.transaction.txn_id,
                "kind": entry.transaction.kind,
                "amount_pence": entry.transaction.amount_pence,
                "balance_after_pence": entry.balance_after_pence,
                "reason": entry.transaction.reason,
                "actor": entry.transaction.actor,
                "at": entry.transaction.at}
        snapshot["events"][policy_no] = [
            {"field": event.kind, "new": event.detail,
             "on": event.on.isoformat()} for event in policy.events]
        snapshot["values"][policy_no] = (
            policy.entries[-1].balance_after_pence if policy.entries else 0)

        operations = world.operations.get(policy_no)
        for contact in (operations.contacts if operations else ()):
            snapshot["interactions"][contact.cn_ref] = {
                "policy_no": policy_no, "on": contact.on.isoformat(),
                "channel": contact.channel, "intent": contact.intent,
                "outcome": contact.outcome}
            story = stories.get(contact.cn_ref)
            if story is not None:
                snapshot["notes"][contact.cn_ref] = {
                    "policy_no": policy_no, "body": story["text"]}
        for case in (operations.cases if operations else ()):
            snapshot["cases"][case.cw_ref] = {
                "policy_no": policy_no, "request": case.request,
                "type": case.type, "status": case.status,
                "priority": HISTORICAL_PRIORITY,
                "human_decision": case.human_decision,
                "opened_on": case.opened_on.isoformat(),
                "sla_due": None}
            story = stories.get(case.cw_ref)
            if story is not None:
                snapshot["narratives"][case.cw_ref] = {
                    "policy_no": policy_no, "body": story["text"]}
            for item in case.evidence:
                snapshot["evidence"][item.evidence_id] = {
                    "cw_ref": case.cw_ref, "policy_no": policy_no,
                    "requirement": item.requirement,
                    "requirement_source": item.requirement_source,
                    "received_via": item.received_via,
                    "received_on": item.received_on.isoformat(),
                    "satisfies": item.satisfies}

    for row in getattr(world, "queue", ()):
        if wanted is not None and row["policy_no"] not in wanted:
            continue
        snapshot["cases"][row["cw_ref"]] = {
            "policy_no": row["policy_no"], "request": row["request"],
            "type": row["type"], "status": row["status"],
            "priority": row["priority"], "human_decision": None,
            "opened_on": row["opened_on"], "sla_due": row["sla_due"]}
        for item in row["evidence"]:
            snapshot["evidence"][item["evidence_id"]] = {
                "cw_ref": row["cw_ref"], "policy_no": row["policy_no"],
                "requirement": item["requirement"],
                "requirement_source": item["requirement_source"],
                "received_via": item["received_via"],
                "received_on": item["received_on"],
                "satisfies": item["satisfies"]}

    return snapshot
