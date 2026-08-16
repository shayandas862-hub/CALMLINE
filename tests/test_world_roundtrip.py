"""The proof: load the world, read it back, and it is the same world.

Integration-marked and deliberately the whole book — two hundred policies into
a throwaway schema, then every table read back whole and compared field by
field against the committed files: holder, product, status, authorities,
every ledger row, every note and narrative, and the value — re-folded from
the database's own rows, to the penny, per policy and across the book.

This is the slowest test in the suite (one transaction per policy against a
remote database) and that is accepted: it is the phase's demonstrable
outcome, and it runs only under `pytest -m integration`.
"""

import asyncio
import json

import pytest

from scripts.migrate import apply_migrations
from src.records.models import DEBIT_KINDS
from world.dataset import DEFAULT_ROOT, read_world
from world.load import load_world

pytestmark = pytest.mark.integration

SCHEMA = "calmline_roundtrip_selftest"

NOTES = 1406
NARRATIVES = 476


def _quiet(line):
    pass


async def _connect():
    from src.config import MissingConfigError, load_config
    try:
        config = load_config()
    except MissingConfigError:
        pytest.skip("no live DATABASE_URL")
    import asyncpg

    return await asyncpg.connect(config.DATABASE_URL, statement_cache_size=0)


def _plain(stamp) -> str:
    """A database timestamptz back to the world's own ISO second string."""
    return stamp.replace(tzinfo=None).isoformat(timespec="seconds")


def _jsonb(value):
    return json.loads(value) if isinstance(value, str) else value


def _normalised(obj) -> dict:
    """A dataclass as the dict jsonb returns — tuples become lists."""
    return json.loads(json.dumps(obj.__dict__))


async def _grouped(conn, sql, key):
    grouped = {}
    for row in await conn.fetch(sql):
        grouped.setdefault(row[key], []).append(row)
    return grouped


def test_all_two_hundred_round_trip_identically_and_the_book_ties_to_the_penny():
    async def scenario():
        conn = await _connect()
        try:
            await conn.execute(f"drop schema if exists {SCHEMA} cascade")
            await conn.execute(f"create schema {SCHEMA}")
            await conn.execute(
                f"set search_path to {SCHEMA}, public, extensions")
            await apply_migrations(conn, out=_quiet)

            world = read_world(DEFAULT_ROOT)
            report = await load_world(conn, world, out=print)
            assert len(report.loaded) == len(world.policies)

            # ── whole tables, read back once ─────────────────────────────
            policies = {row["policy_no"]: row for row in
                        await conn.fetch("select * from policies")}
            ledgers = await _grouped(
                conn, "select * from transactions order by policy_no, seq",
                "policy_no")
            journals = await _grouped(
                conn, "select * from record_changes order by seq", "entity_id")
            calls = await _grouped(
                conn, "select * from interactions order by cn_ref", "policy_no")
            notes = {row["cn_ref"]: row for row in
                     await conn.fetch("select * from contact_notes")}
            cases = {row["cw_ref"]: row for row in
                     await conn.fetch("select * from cases")}
            narratives = {row["cw_ref"]: row for row in
                          await conn.fetch("select * from case_narratives")}
            evidence = {row["evidence_id"]: row for row in
                        await conn.fetch("select * from evidence")}
            held = await _grouped(
                conn, "select * from authority_records order by authority_id",
                "policy_no")
            mandates = {row["policy_no"]: row for row in
                        await conn.fetch("select * from bank_mandates")}
            parties = {row["party_id"]: row for row in
                       await conn.fetch("select * from parties")}
            folded = {row["policy_no"]: row["value"] for row in await conn.fetch(
                "select policy_no, coalesce(sum(case when kind = any($1) "
                "then -amount_pence else amount_pence end), 0) as value "
                "from transactions group by policy_no", sorted(DEBIT_KINDS))}

            # ── the prose, counted explicitly — the easiest thing to drop ─
            assert len(notes) == NOTES
            assert len(narratives) == NARRATIVES

            # ── every person, exactly as the people file has them ────────
            people = [p for p in world.people if "party_id" in p]
            assert len(parties) == len(people)
            for person in people:
                row = parties[person["party_id"]]
                assert row["name"] == person["name"]
                assert row["dob"].isoformat() == person["dob"]
                assert row["registered_address"] == person["registered_address"]
                assert _jsonb(row["contact"]) == (person.get("contact") or {})

            # ── every policy, field by field ─────────────────────────────
            funds_db = funds_file = 0
            for policy in world.policies:
                policy_no = policy.policy_no
                row = policies[policy_no]
                assert row["product"] == policy.product
                assert row["status"] == policy.status
                assert row["start_date"] == policy.start
                assert row["holder_party_id"] == policy.holder_party_id

                trust = world.trusts.get(policy_no)
                assert _jsonb(row["trust"]) == (
                    None if trust is None else _normalised(trust))
                loa = world.adviser_mandates.get(policy_no)
                assert _jsonb(row["adviser_loa"]) == (
                    None if loa is None else _normalised(loa))

                mandate = world.bank_mandates.get(policy_no)
                if mandate is None:
                    assert policy_no not in mandates
                else:
                    stored = mandates[policy_no]
                    assert row["bank_last4"] == mandate.account_last4
                    assert stored["verified"] == mandate.verified
                    assert (stored["hold_until"].isoformat()
                            if stored["hold_until"] else None) == mandate.hold_until
                    assert _jsonb(stored["change_history"]) == [
                        change.__dict__ for change in mandate.change_history]

                stored_held = {row["authority_id"]: row
                               for row in held.get(policy_no, [])}
                records = world.authorities.get(policy_no, ())
                assert len(stored_held) == len(records)
                for record in records:
                    stored = stored_held[record.authority_id]
                    assert stored["party_id"] == record.party_id
                    assert stored["type"] == record.type
                    assert list(stored["scope"]) == list(record.scope)
                    assert stored["status"] == record.status

                ledger = ledgers.get(policy_no, [])
                assert len(ledger) == len(policy.entries)
                for entry, stored in zip(policy.entries, ledger, strict=True):
                    txn = entry.transaction
                    assert stored["txn_id"] == txn.txn_id
                    assert stored["seq"] == entry.seq
                    assert stored["kind"] == txn.kind
                    assert stored["amount_pence"] == txn.amount_pence
                    assert stored["balance_after_pence"] == entry.balance_after_pence
                    assert stored["reason"] == txn.reason
                    assert stored["actor"] == txn.actor
                    assert _plain(stored["at"]) == txn.at

                for event, stored in zip(policy.events,
                                         journals.get(policy_no, []),
                                         strict=True):
                    (delta,) = _jsonb(stored["changes"])
                    assert delta["field"] == event.kind
                    assert delta["new"] == event.detail
                    assert stored["at"].date() == event.on

                # Keyed on the reference, not zipped on order: the file's
                # contacts are chronological while their CN- indexes are not
                # (minting order is not date order) — the round-trip found
                # that, and a reference join is the honest comparison.
                operations = world.operations.get(policy_no)
                contacts = operations.contacts if operations else ()
                stored_calls = {row["cn_ref"]: row
                                for row in calls.get(policy_no, [])}
                assert len(stored_calls) == len(contacts)
                for contact in contacts:
                    stored = stored_calls[contact.cn_ref]
                    assert stored["opened_at"].date() == contact.on
                    assert stored["channel"] == contact.channel
                    assert stored["intent"] == contact.intent
                    assert stored["outcome"] == contact.outcome

                for case in (operations.cases if operations else ()):
                    stored = cases[case.cw_ref]
                    assert stored["policy_no"] == policy_no
                    assert stored["request"] == case.request
                    assert stored["type"] == case.type
                    assert stored["status"] == case.status
                    assert stored["human_decision"] == case.human_decision
                    assert stored["created_at"].date() == case.opened_on
                    (trail,) = _jsonb(stored["audit"])
                    assert trail["cn_ref"] == case.cn_ref
                    assert trail["closed_on"] == case.closed_on.isoformat()
                    for item in case.evidence:
                        kept = evidence[item.evidence_id]
                        assert kept["cw_ref"] == case.cw_ref
                        assert kept["requirement"] == item.requirement
                        assert kept["requirement_source"] == item.requirement_source
                        assert kept["received_via"] == item.received_via
                        assert kept["satisfies"] == item.satisfies
                        assert kept["received_at"].date() == item.received_on

                # ── the value, re-folded from the database's own rows ────
                file_value = (policy.entries[-1].balance_after_pence
                              if policy.entries else 0)
                assert folded.get(policy_no, 0) == file_value, policy_no
                funds_db += folded.get(policy_no, 0)
                funds_file += file_value

            for story in world.stories:
                stored = (notes if story["kind"] == "note" else
                          narratives)[story["ref"]]
                assert stored["body"] == story["text"]
                assert stored["policy_no"] == story["policy_no"]

            assert funds_db == funds_file, (
                f"funds under administration differ: database {funds_db}p, "
                f"file {funds_file}p")
            print(f"round-trip: {len(world.policies)} policies identical · "
                  f"funds under administration {funds_db}p, to the penny")
        finally:
            await conn.execute(f"drop schema if exists {SCHEMA} cascade")
            await conn.close()

    asyncio.run(scenario())
