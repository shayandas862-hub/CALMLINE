"""Lazy asyncpg connection pool singleton (BUG #11).

Replaces the previous pattern where every DB call opened a fresh asyncpg
connection — saves the TCP handshake + Postgres auth on every query and
prevents exhausting Supabase's connection limit under load.

Usage:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

`get_pool` is lazy — the pool is created on first call and reused
process-wide. Call `close_pool()` during shutdown to drain it cleanly.
"""
from __future__ import annotations

from typing import Any, Callable

import asyncpg

from app.core.config import get_settings

_pool: asyncpg.Pool | None = None


async def _default_factory(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=10)


async def get_pool(
    *,
    _factory: Callable[[str], Any] | None = None,
    _dsn: str | None = None,
) -> asyncpg.Pool:
    """Return the process-wide asyncpg pool, creating it lazily on first call."""
    global _pool
    if _pool is None:
        factory = _factory or _default_factory
        dsn = _dsn or get_settings().DATABASE_URL
        _pool = await factory(dsn)
    return _pool


async def close_pool() -> None:
    """Drain and close the pool. Safe to call multiple times."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def reset_pool() -> None:
    """Test helper — clears the cached singleton without awaiting close."""
    global _pool
    _pool = None
