"""One policy's rows, written inside the caller's transaction.

Dates and timestamps cross the wire as Python objects, because asyncpg's
binary codecs demand them — the `::date`-cast-with-text-string convention
`pg_store` wrote was never proven against a live write, and it fails there.
Every stamp is the record's own, made timezone-aware as UTC (the world's
times are date-anchored midnights and the database session is UTC); nothing
here ever consults a clock. JSON stays a string with a `::jsonb` cast, which
asyncpg does accept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from typing import Any, Mapping, Optional, Sequence


def _ts(iso: str) -> datetime:
    """The record's own moment, as the tz-aware datetime asyncpg requires."""
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def _day(value: Any) -> Optional[date]:
    """A date column's value: a date, an ISO string, or nothing."""
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _refuse(message: str) -> None:
    from world.load import LoadError

    raise LoadError(message)


@dataclass(frozen=True)
class PolicyCounts:
    people: int = 0
    movements: int = 0
    events: int = 0
    contacts: int = 0
    notes: int = 0
    cases: int = 0
    narratives: int = 0
    evidence: int = 0

    def plus(self, other: "PolicyCounts") -> "PolicyCounts":
        return PolicyCounts(**{f.name: getattr(self, f.name) +
                               getattr(other, f.name) for f in fields(self)})


_PARTY_SQL = (
    "insert into parties (party_id, name, dob, registered_address, contact) "
    "values ($1, $2, $3, $4, $5::jsonb) "
    "on conflict (party_id) do nothing")


def _party_row(person: Mapping[str, Any]) -> tuple:
    return (person["party_id"], person["name"], _day(person["dob"]),
            person["registered_address"],
            json.dumps(person.get("contact") or {}))


async def write_policy(conn: Any, world: Any, policy: Any,
                       people_by_id: Mapping[str, Mapping], *,
                       notes: Sequence[Mapping], narratives: Sequence[Mapping],
                       written_people: set) -> PolicyCounts:
    """Everything hanging off one policy, in dependency order."""
    policy_no = policy.policy_no
    trust = world.trusts.get(policy_no)
    loa = world.adviser_mandates.get(policy_no)
    held = world.authorities.get(policy_no, ())
    mandate = world.bank_mandates.get(policy_no)
    operations = world.operations.get(policy_no)
    contacts = operations.contacts if operations else ()
    cases = operations.cases if operations else ()

    cast = _cast_of(policy, trust, loa, held)
    people = []
    for party_id in cast:
        person = people_by_id.get(party_id)
        if person is None:
            _refuse(f"{policy_no} names {party_id}, who is not in "
                    f"people.jsonl — refusing rather than inventing a person")
        people.append(person)
    await conn.executemany(_PARTY_SQL, [_party_row(p) for p in people])
    written_people.update(cast)

    await conn.execute(
        "insert into policies (policy_no, product, status, start_date, "
        "holder_party_id, lives_assured, lives_assured_basis, trust, "
        "adviser_loa, bank_last4) "
        "values ($1, $2, $3, $4, $5, '[]'::jsonb, 'single', $6::jsonb, "
        "$7::jsonb, $8)",
        policy_no, policy.product, policy.status, policy.start,
        policy.holder_party_id,
        None if trust is None else json.dumps(trust.__dict__),
        None if loa is None else json.dumps(loa.__dict__),
        mandate.account_last4 if mandate else None)

    if mandate is not None:
        await conn.execute(
            "insert into bank_mandates (policy_no, account_last4, verified, "
            "hold_until, change_history) "
            "values ($1, $2, $3, $4, $5::jsonb)",
            policy_no, mandate.account_last4, mandate.verified,
            _day(mandate.hold_until),
            json.dumps([change.__dict__ for change in mandate.change_history]))

    await conn.executemany(
        "insert into authority_records (authority_id, policy_no, party_id, "
        "type, scope, evidence_ref, verified_date, status) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8)",
        [(a.authority_id, policy_no, a.party_id, a.type, list(a.scope),
          a.evidence_ref, _day(a.verified_date), a.status) for a in held])

    await conn.executemany(
        "insert into transactions (txn_id, policy_no, seq, kind, amount_pence, "
        "balance_after_pence, reason, actor, at) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
        [(e.transaction.txn_id, policy_no, e.seq, e.transaction.kind,
          e.transaction.amount_pence, e.balance_after_pence,
          e.transaction.reason, e.transaction.actor, _ts(e.transaction.at))
         for e in policy.entries])

    await conn.executemany(
        "insert into record_changes (entity_type, entity_id, changes, actor, "
        "source_ref, at) values ('policy', $1, $2::jsonb, 'world', 'seed', $3)",
        [(policy_no,
          json.dumps([{"field": event.kind, "old": None,
                       "new": event.detail}]),
          _ts(f"{event.on.isoformat()}T00:00:00")) for event in policy.events])

    await conn.executemany(
        "insert into interactions (cn_ref, policy_no, opened_at, channel, "
        "intent, outcome) values ($1, $2, $3, $4, $5, $6)",
        [(c.cn_ref, policy_no, _ts(f"{c.on.isoformat()}T00:00:00"), c.channel,
          c.intent, c.outcome) for c in contacts])

    contact_dates = {c.cn_ref: c.on.isoformat() for c in contacts}
    note_rows = []
    for note in notes:
        when = contact_dates.get(note["ref"])
        if when is None:
            _refuse(f"{policy_no}: a note is written against {note['ref']}, "
                    f"which is not one of this policy's contacts")
        note_rows.append((note["ref"], policy_no, note["text"], "world",
                          _ts(f"{when}T00:00:00")))
    await conn.executemany(
        "insert into contact_notes (cn_ref, policy_no, body, author, "
        "written_at) values ($1, $2, $3, $4, $5)", note_rows)

    await conn.executemany(
        "insert into cases (cw_ref, policy_no, request, type, status, "
        "human_decision, sla_due, created_at, audit) "
        "values ($1, $2, $3, $4, $5, $6, null, $7, $8::jsonb)",
        [(k.cw_ref, policy_no, k.request, k.type, k.status, k.human_decision,
          _ts(f"{k.opened_on.isoformat()}T00:00:00"),
          json.dumps([_milestones(k)])) for k in cases])

    case_dates = {k.cw_ref: k.closed_on.isoformat() for k in cases}
    narrative_rows = []
    for narrative in narratives:
        when = case_dates.get(narrative["ref"])
        if when is None:
            _refuse(f"{policy_no}: a narrative is written against "
                    f"{narrative['ref']}, which is not one of this policy's "
                    f"cases")
        narrative_rows.append((narrative["ref"], policy_no, narrative["text"],
                               "world", _ts(f"{when}T00:00:00")))
    await conn.executemany(
        "insert into case_narratives (cw_ref, policy_no, body, author, "
        "written_at) values ($1, $2, $3, $4, $5)", narrative_rows)

    await conn.executemany(
        "insert into evidence (evidence_id, cw_ref, policy_no, requirement, "
        "requirement_source, received_via, received_at, satisfies) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8)",
        [(e.evidence_id, k.cw_ref, policy_no, e.requirement,
          e.requirement_source, e.received_via,
          _ts(f"{e.received_on.isoformat()}T00:00:00"), e.satisfies)
         for k in cases for e in k.evidence])

    return PolicyCounts(
        people=len(cast), movements=len(policy.entries),
        events=len(policy.events), contacts=len(contacts),
        notes=len(note_rows), cases=len(cases),
        narratives=len(narrative_rows),
        evidence=sum(len(k.evidence) for k in cases))


def _cast_of(policy: Any, trust: Any, loa: Any, held: tuple) -> tuple[str, ...]:
    """Everyone this policy names, holder first, in a stable order."""
    cast = [policy.holder_party_id]
    if trust is not None:
        cast.extend(trust.trustees)
    if loa is not None:
        cast.extend(loa.individuals)
    cast.extend(record.party_id for record in held)
    return tuple(dict.fromkeys(cast))


def _milestones(case: Any) -> dict:
    """The case's dated trail, kept as data — nothing invented."""
    trail = {"cn_ref": case.cn_ref,
             "opened_on": case.opened_on.isoformat(),
             "closed_on": case.closed_on.isoformat()}
    if case.authorised_movement_on is not None:
        trail["authorised_movement_on"] = case.authorised_movement_on.isoformat()
    return trail


async def sweep_people(conn: Any, pending: Sequence[Mapping]) -> int:
    """Everyone no loaded policy named — the people table is still complete."""
    await conn.executemany(_PARTY_SQL, [_party_row(p) for p in pending])
    return len(pending)


async def write_queue_case(conn: Any, row: Mapping[str, Any]) -> None:
    """One piece of live work, open in the database exactly as the dataset
    holds it: its own reference, an open status, a real deadline — and no
    human_decision, because nobody has decided anything yet."""
    await conn.execute(
        "insert into cases (cw_ref, policy_no, request, type, status, "
        "priority, sla_due, created_at, audit) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)",
        row["cw_ref"], row["policy_no"], row["request"], row["type"],
        row["status"], row["priority"], _ts(row["sla_due"]),
        _ts(f"{row['opened_on']}T00:00:00"),
        json.dumps([{"cn_ref": row["cn_ref"],
                     "opened_on": row["opened_on"]}]))
    await conn.executemany(
        "insert into evidence (evidence_id, cw_ref, policy_no, requirement, "
        "requirement_source, received_via, received_at, satisfies) "
        "values ($1, $2, $3, $4, $5, $6, $7, $8)",
        [(item["evidence_id"], row["cw_ref"], row["policy_no"],
          item["requirement"], item["requirement_source"],
          item["received_via"], _ts(f"{item['received_on']}T00:00:00"),
          item["satisfies"]) for item in row["evidence"]])
