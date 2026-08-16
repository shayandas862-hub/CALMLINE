"""`PostgresRecordStore` — the same RecordStore interface, backed by Postgres.

Phase 2 delivers Postgres *readiness*, not a Postgres dependency (AD-CL-030):
every offline path keeps the in-memory book, and the day this is pointed
`DATABASE_URL` at a live database, cutover is a wiring change with the
invariant tests already written.

The rules that matter are enforced in the same places they always were. The
overdraw check runs **before** the insert, in the same ledger engine the
in-memory book uses, so a movement the app would refuse is never written and
then reversed. Append-only is enforced by a database trigger as well, because
the application's single write path is only a guarantee about the application.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from src.records.changelog import FieldDelta
from src.records.ledger import LedgerError
from src.records.models import (
    DEBIT_KINDS,
    AdviserLoa,
    Contact,
    IdVerification,
    LedgerEntry,
    LifeAssured,
    Party,
    Policy,
    Transaction,
    Trust,
    VulnerabilityFlag,
)

PARTY_COLUMNS = ("party_id", "name", "dob", "registered_address", "contact",
                 "scottish_taxpayer", "vulnerability_flag", "id_verified_level",
                 "id_verified_at")
POLICY_COLUMNS = ("policy_no", "product", "status", "start_date", "holder_party_id",
                  "lives_assured", "lives_assured_basis", "trust", "adviser_loa",
                  "bank_last4")


def _json(value: Any) -> str:
    return json.dumps(value, default=lambda item: item.__dict__)


def _as_dict(value: Any) -> Any:
    """asyncpg returns jsonb as text; a fake connection returns it decoded."""
    return json.loads(value) if isinstance(value, str) else value


# ── rows → models ────────────────────────────────────────────────────────
def row_to_party(row: Optional[dict]) -> Optional[Party]:
    """Build a ``Party`` from a `parties` row, or ``None`` for a missing one."""
    if row is None:
        return None
    contact = _as_dict(row["contact"]) or {}
    flag = _as_dict(row.get("vulnerability_flag"))
    level = row.get("id_verified_level")
    return Party(
        party_id=row["party_id"], name=row["name"], dob=str(row["dob"]),
        registered_address=row["registered_address"],
        contact=Contact(phone=contact.get("phone", ""), email=contact.get("email", ""),
                        registered=bool(contact.get("registered", False))),
        scottish_taxpayer=bool(row.get("scottish_taxpayer", False)),
        vulnerability_flag=None if not flag else VulnerabilityFlag(
            support_needs_ref=flag["support_needs_ref"], category=flag["category"]),
        id_verified_level=None if not level else IdVerification(
            level=level, at=str(row.get("id_verified_at"))))


def row_to_policy(row: Optional[dict]) -> Optional[Policy]:
    """Build a ``Policy`` from a `policies` row, or ``None`` for a missing one."""
    if row is None:
        return None
    trust = _as_dict(row.get("trust"))
    loa = _as_dict(row.get("adviser_loa"))
    lives = _as_dict(row.get("lives_assured")) or []
    return Policy(
        policy_no=row["policy_no"], product=row["product"], status=row["status"],
        start_date=str(row["start_date"]), holder_party_id=row["holder_party_id"],
        lives_assured=tuple(LifeAssured(name=life["name"],
                                        party_id=life.get("party_id"))
                            for life in lives),
        lives_assured_basis=row.get("lives_assured_basis", "single"),
        trust=None if not trust else Trust(
            kind=trust["kind"], executed=trust["executed"],
            trustees=tuple(trust.get("trustees", ())),
            registrable=bool(trust.get("registrable", False)), urn=trust.get("urn")),
        adviser_loa=None if not loa else AdviserLoa(
            firm=loa["firm"], frn=loa["frn"], scope=tuple(loa.get("scope", ())),
            expiry=loa["expiry"],
            individuals=tuple(loa.get("individuals", ()))),
        bank_last4=row.get("bank_last4"))


def row_to_entry(row: dict) -> LedgerEntry:
    """Build a ``LedgerEntry`` from a `transactions` row."""
    return LedgerEntry(
        seq=row["seq"],
        transaction=Transaction(
            txn_id=row["txn_id"], policy_no=row["policy_no"], kind=row["kind"],
            amount_pence=row["amount_pence"], reason=row["reason"],
            actor=row["actor"], at=str(row["at"])),
        balance_after_pence=row["balance_after_pence"])


class PostgresRecordStore:
    """The system of record, in Postgres. Async, because the pool is."""

    def __init__(self, *, pool: Any) -> None:
        self._pool = pool

    # ── writes ───────────────────────────────────────────────────────────
    async def add_party(self, party: Party, *, actor: str, source_ref: str,
                        at: str) -> None:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "insert into parties (party_id, name, dob, registered_address, "
                    "contact, scottish_taxpayer, vulnerability_flag) "
                    "values ($1, $2, $3::date, $4, $5::jsonb, $6, $7::jsonb) "
                    "on conflict (party_id) do nothing",
                    party.party_id, party.name, party.dob, party.registered_address,
                    _json(party.contact.__dict__), party.scottish_taxpayer,
                    None if party.vulnerability_flag is None
                    else _json(party.vulnerability_flag.__dict__))
                await self._journal(connection, "party", party.party_id,
                                    [FieldDelta(field="created", old=None,
                                                new=party.party_id)],
                                    actor=actor, source_ref=source_ref, at=at)

    async def add_policy(self, policy: Policy, *, actor: str, source_ref: str,
                         at: str) -> None:
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "insert into policies (policy_no, product, status, start_date, "
                    "holder_party_id, lives_assured, lives_assured_basis, trust, "
                    "adviser_loa, bank_last4) "
                    "values ($1, $2, $3, $4::date, $5, $6::jsonb, $7, $8::jsonb, "
                    "$9::jsonb, $10) on conflict (policy_no) do nothing",
                    policy.policy_no, policy.product, policy.status, policy.start_date,
                    policy.holder_party_id,
                    _json([life.__dict__ for life in policy.lives_assured]),
                    policy.lives_assured_basis,
                    None if policy.trust is None else _json(policy.trust.__dict__),
                    None if policy.adviser_loa is None
                    else _json(policy.adviser_loa.__dict__),
                    policy.bank_last4)
                await self._journal(connection, "policy", policy.policy_no,
                                    [FieldDelta(field="created", old=None,
                                                new=policy.policy_no)],
                                    actor=actor, source_ref=source_ref, at=at)

    async def apply_transaction(self, policy_no: str, txn: Transaction, *,
                                source_ref: str = "seed") -> LedgerEntry:
        """Append a movement, refusing an overdraw before anything is written."""
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                balance = await connection.fetchval(
                    "select coalesce(max(balance_after_pence), 0) from transactions "
                    "where policy_no = $1 and seq = (select max(seq) from transactions "
                    "where policy_no = $1)", policy_no) or 0
                new_balance = balance + txn.signed_pence
                if new_balance < 0:
                    raise LedgerError(
                        f"{txn.kind} of {txn.amount_pence}p would overdraw "
                        f"{policy_no} (balance {balance}p)")
                seq = await connection.fetchval(
                    "select coalesce(max(seq), 0) + 1 from transactions "
                    "where policy_no = $1", policy_no) or 1
                await connection.execute(
                    "insert into transactions (txn_id, policy_no, seq, kind, "
                    "amount_pence, balance_after_pence, reason, actor, at) "
                    "values ($1, $2, $3, $4, $5, $6, $7, $8, $9::timestamptz)",
                    txn.txn_id, policy_no, seq, txn.kind, txn.amount_pence,
                    new_balance, txn.reason, txn.actor, txn.at)
                await self._journal(connection, "policy", policy_no,
                                    [FieldDelta(field="ledger", old=None,
                                                new=f"{txn.kind} {txn.signed_pence}p")],
                                    actor=txn.actor, source_ref=source_ref, at=txn.at)
                return LedgerEntry(seq=seq, transaction=txn,
                                   balance_after_pence=new_balance)

    @staticmethod
    async def _journal(connection: Any, entity_type: str, entity_id: str,
                       deltas: "list[FieldDelta]", *, actor: str, source_ref: str,
                       at: str) -> None:
        await connection.execute(
            "insert into record_changes (entity_type, entity_id, changes, actor, "
            "source_ref, at) values ($1, $2, $3::jsonb, $4, $5, $6::timestamptz)",
            entity_type, entity_id, _json([delta.__dict__ for delta in deltas]),
            actor, source_ref, at)

    # ── reads ────────────────────────────────────────────────────────────
    async def get_party(self, party_id: str) -> Optional[Party]:
        async with self._pool.acquire() as connection:
            return row_to_party(await connection.fetchrow(
                "select * from parties where party_id = $1", party_id))

    async def get_policy(self, policy_no: str) -> Optional[Policy]:
        async with self._pool.acquire() as connection:
            return row_to_policy(await connection.fetchrow(
                "select * from policies where policy_no = $1", policy_no))

    async def list_policies(self) -> "list[Policy]":
        async with self._pool.acquire() as connection:
            rows = await connection.fetch("select * from policies order by policy_no")
        return [row_to_policy(row) for row in rows]

    async def history(self, policy_no: str) -> "tuple[LedgerEntry, ...]":
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                "select * from transactions where policy_no = $1 order by seq",
                policy_no)
        return tuple(row_to_entry(row) for row in rows)

    async def current_value(self, policy_no: str) -> int:
        async with self._pool.acquire() as connection:
            return await connection.fetchval(
                "select coalesce(sum(case when kind = any($2) then -amount_pence "
                "else amount_pence end), 0) from transactions where policy_no = $1",
                policy_no, sorted(DEBIT_KINDS)) or 0


# ── helpers the integration tests use ────────────────────────────────────
async def table_names(config: Any) -> "set[str]":
    """Every table in the applied public schema."""
    from src.db.pool import close_pool, reset_pool
    from src.db.pool import get_pool

    reset_pool()
    pool = await get_pool(config)
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                "select tablename from pg_tables where schemaname = 'public'")
        return {row["tablename"] for row in rows}
    finally:
        await close_pool()


async def assert_append_only(config: Any, table: str) -> bool:
    """Prove the database itself refuses an update to ``table``."""
    import asyncpg

    from src.db.pool import close_pool, get_pool, reset_pool

    reset_pool()
    pool = await get_pool(config)
    try:
        async with pool.acquire() as connection:
            try:
                await connection.execute(f"update {table} set actor = actor")
            except asyncpg.PostgresError as error:
                return "append-only" in str(error)
        return False
    finally:
        await close_pool()
