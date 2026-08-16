"""The asyncpg pool: lazy singleton, config-injected DSN, clean reset.

Unit tests stub the pool factory — no network. The live connectivity check
lives in test_db_client.py's integration test.
"""

import asyncio

from src.db import pool as db_pool
from tests.test_db_client import FAKE_CONFIG


def setup_function():
    db_pool.reset_pool()


def teardown_function():
    db_pool.reset_pool()


class FakePool:
    def __init__(self, dsn):
        self.dsn = dsn
        self.closed = False

    async def close(self):
        self.closed = True


def test_pool_is_built_from_config_dsn():
    # Arrange
    seen = {}

    async def fake_factory(dsn):
        seen["dsn"] = dsn
        return FakePool(dsn)

    # Act
    pool = asyncio.run(db_pool.get_pool(FAKE_CONFIG, _factory=fake_factory))

    # Assert
    assert isinstance(pool, FakePool)
    assert seen["dsn"] == FAKE_CONFIG.DATABASE_URL


def test_pool_is_a_singleton_across_calls():
    # Arrange
    calls = {"count": 0}

    async def fake_factory(dsn):
        calls["count"] += 1
        return FakePool(dsn)

    async def get_twice():
        first = await db_pool.get_pool(FAKE_CONFIG, _factory=fake_factory)
        second = await db_pool.get_pool(FAKE_CONFIG, _factory=fake_factory)
        return first, second

    # Act
    first, second = asyncio.run(get_twice())

    # Assert — one construction, same object back
    assert first is second
    assert calls["count"] == 1


def test_close_pool_drains_and_resets():
    # Arrange
    async def fake_factory(dsn):
        return FakePool(dsn)

    async def scenario():
        pool = await db_pool.get_pool(FAKE_CONFIG, _factory=fake_factory)
        await db_pool.close_pool()
        replacement = await db_pool.get_pool(FAKE_CONFIG, _factory=fake_factory)
        return pool, replacement

    # Act
    old, new = asyncio.run(scenario())

    # Assert — closed cleanly, next call builds a fresh pool
    assert old.closed is True
    assert new is not old
