# MIT License — Copyright (c) 2026 Shayan Das
# Adapted from the author's earlier original work
# (vendor/secondbrain/db_pool.py): config-injected DSN instead of a global
# settings accessor; otherwise the same lazy-singleton pattern.
"""Lazy asyncpg connection pool singleton.

One pool per process instead of a fresh connection per query — saves the TCP
handshake + Postgres auth each time and protects Supabase's connection limit.

Usage:
    pool = await get_pool(config)
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

Call `close_pool()` during shutdown to drain it cleanly.
"""

from __future__ import annotations

from typing import Any, Callable

import asyncpg

from src.config import Config

_pool: asyncpg.Pool | None = None


async def _default_factory(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=10)


async def get_pool(
    config: Config,
    *,
    _factory: Callable[[str], Any] | None = None,
) -> asyncpg.Pool:
    """Return the process-wide asyncpg pool, creating it lazily on first call."""
    global _pool
    if _pool is None:
        factory = _factory or _default_factory
        _pool = await factory(config.DATABASE_URL)
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
