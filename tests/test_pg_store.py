"""`PostgresRecordStore` — the same interface, backed by Postgres.

Two kinds of test live here.

The **offline** ones drive the store against a fake connection that records the
SQL it is handed. They prove the mapping — that a `Party` round-trips through
its row shape, that a movement is written with the transaction's own timestamp,
that a read builds the right model back — without a database anywhere.

The **integration** ones talk to the real thing. They are marked so
`pyproject.toml` deselects them from a default `pytest -q` run (D-CL-034), and
they *also* skip when credentials are absent, so `pytest -m integration` on a
bare checkout reports "skipped" rather than "error".
"""

import asyncio

import pytest

from src.config import MissingConfigError, load_config
from src.records.models import Contact, Party, Policy, Transaction, gbp
from src.records.pg_store import PostgresRecordStore, row_to_party, row_to_policy
from src.records.store import RecordStore

SEED = dict(actor="seed", source_ref="seed", at="2026-07-13T00:00:00")


class FakeConnection:
    """Records every statement it is given and replays canned rows."""

    def __init__(self, rows=None):
        self.calls: list[tuple] = []
        self._rows = rows or {}

    async def execute(self, sql, *args):
        self.calls.append((sql, args))

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows.get("row")

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows.get("rows", [])

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows.get("val")

    def transaction(self):
        return _NullTransaction()


class _NullTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, connection):
        self._connection = connection

    def acquire(self):
        return _Acquire(self._connection)


class _Acquire:
    def __init__(self, connection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, *exc):
        return False


def _party() -> Party:
    return Party(party_id="PH-0001", name="Theta Meridian 12", dob="1954-02-11",
                 registered_address="14 Lattice Way, Demoford",
                 contact=Contact(phone="07700 900101", email="ph-0001@example.org",
                                 registered=True))


def _policy() -> Policy:
    return Policy(policy_no="LP-20419876", product="lifelong_protection",
                  status="in_force", start_date="2016-05-01",
                  holder_party_id="PH-0001")


# ── the interface contract ───────────────────────────────────────────────
def test_the_postgres_store_satisfies_the_record_store_protocol():
    # The seam the whole design rests on: swapping the implementation must not
    # change the ledger logic.
    assert isinstance(PostgresRecordStore(pool=FakePool(FakeConnection())), RecordStore)


def test_it_offers_the_same_operations_as_the_in_memory_book():
    from src.records.store import InMemoryRecordBook
    store = PostgresRecordStore(pool=FakePool(FakeConnection()))
    for name in ("get_party", "get_policy", "list_policies", "apply_transaction",
                 "history", "current_value", "add_party", "add_policy"):
        assert hasattr(store, name), f"PostgresRecordStore is missing {name}"
        assert hasattr(InMemoryRecordBook, name)


# ── writes ───────────────────────────────────────────────────────────────
def test_adding_a_party_inserts_it_and_journals_the_change():
    connection = FakeConnection()
    store = PostgresRecordStore(pool=FakePool(connection))
    asyncio.run(store.add_party(_party(), **SEED))

    statements = " ".join(sql for sql, _ in connection.calls).lower()
    assert "insert into parties" in statements
    assert "insert into record_changes" in statements


def test_adding_a_policy_inserts_it_and_journals_the_change():
    connection = FakeConnection()
    store = PostgresRecordStore(pool=FakePool(connection))
    asyncio.run(store.add_policy(_policy(), **SEED))

    statements = " ".join(sql for sql, _ in connection.calls).lower()
    assert "insert into policies" in statements
    assert "insert into record_changes" in statements


def test_a_movement_is_written_with_the_transactions_own_time():
    # Not now(): the ledger's `at` is injected so history is deterministic.
    connection = FakeConnection({"val": 0})
    store = PostgresRecordStore(pool=FakePool(connection))
    txn = Transaction(txn_id="TXN-1", policy_no="LP-20419876", kind="opening",
                      amount_pence=gbp(46_210), reason="opening", actor="seed",
                      at="2016-05-01T00:00:00")
    asyncio.run(store.apply_transaction("LP-20419876", txn))

    insert = next(call for call in connection.calls
                  if "insert into transactions" in call[0].lower())
    assert "2016-05-01T00:00:00" in insert[1]
    assert "now()" not in insert[0].lower()


def test_a_movement_that_would_overdraw_is_refused_before_it_is_written():
    from src.records.ledger import LedgerError
    connection = FakeConnection({"val": gbp(100)})     # current balance £100
    store = PostgresRecordStore(pool=FakePool(connection))
    txn = Transaction(txn_id="TXN-2", policy_no="LP-20419876", kind="withdrawal",
                      amount_pence=gbp(500), reason="too much", actor="seed",
                      at="2026-07-13T00:00:00")
    with pytest.raises(LedgerError):
        asyncio.run(store.apply_transaction("LP-20419876", txn))
    assert not any("insert into transactions" in sql.lower()
                   for sql, _ in connection.calls)


# ── reads ────────────────────────────────────────────────────────────────
def test_a_party_row_becomes_a_party():
    party = row_to_party({
        "party_id": "PH-0001", "name": "Theta Meridian 12", "dob": "1954-02-11",
        "registered_address": "14 Lattice Way, Demoford",
        "contact": {"phone": "07700 900101", "email": "x@example.org",
                    "registered": True},
        "scottish_taxpayer": False, "vulnerability_flag": None,
        "id_verified_level": None, "id_verified_at": None})
    assert party.party_id == "PH-0001"
    assert party.contact.registered is True
    assert party.vulnerability_flag is None


def test_a_policy_row_becomes_a_policy():
    policy = row_to_policy({
        "policy_no": "HB-40582213", "product": "horizon_bond", "status": "in_force",
        "start_date": "2019-03-01", "holder_party_id": "PH-0002",
        "lives_assured": [{"name": "Argon Basalt 27", "party_id": "PH-0002"}],
        "lives_assured_basis": "joint_last_survivor", "trust": None,
        "adviser_loa": None, "bank_last4": "2209"})
    assert policy.policy_no == "HB-40582213"
    assert policy.lives_assured_basis == "joint_last_survivor"
    assert policy.lives_assured[0].name == "Argon Basalt 27"


def test_an_unknown_party_row_is_none_not_an_empty_party():
    assert row_to_party(None) is None
    assert row_to_policy(None) is None


# ── against the real database ────────────────────────────────────────────
@pytest.mark.integration
class TestAgainstLivePostgres:
    """Opt-in: `pytest -m integration`. Requires the migration applied."""

    @staticmethod
    def _config():
        try:
            return load_config()
        except MissingConfigError:
            pytest.skip("no live DATABASE_URL — apply the migration first")

    def test_the_records_tables_exist(self):
        config = self._config()
        from src.records.pg_store import table_names
        names = asyncio.run(table_names(config))
        for table in ("parties", "policies", "transactions", "record_changes",
                      "interactions", "cases", "evidence"):
            assert table in names, f"{table} is not in the applied schema"

    def test_the_retired_v2_tables_are_gone(self):
        config = self._config()
        from src.records.pg_store import table_names
        names = asyncio.run(table_names(config))
        assert "mock_policy_records" not in names
        assert "audit_log" not in names

    def test_the_ledger_refuses_to_be_rewritten(self):
        # The append-only trigger, proven against the real database rather
        # than trusted because the SQL says so.
        config = self._config()
        from src.records.pg_store import assert_append_only
        assert asyncio.run(assert_append_only(config, "transactions")) is True
