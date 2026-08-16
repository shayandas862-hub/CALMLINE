# MIT License — Copyright (c) 2026 Shayan Das
# Adapted from the author's earlier original work
# (vendor/secondbrain/query_hybrid_search.py::_AsyncDBSearcher). Single-tenant
# (no user_id predicate). Exercised by the deferred integration retrieval test
# (needs the live Supabase project); not unit-tested — the filter logic it
# depends on is pure and unit-tested in hybrid_search.RetrievalFilters.
"""Production chunk searcher — parameterised SQL over `kb_chunks` via asyncpg.

Retrieval is filter-then-search: `RetrievalFilters.sql_predicate` supplies a
parameterised `aud`/`doc` restriction that narrows the candidates before the
similarity ordering runs.

Two predicates are **always** applied, filter or no filter:

  * `superseded_by is null` — a tombstoned chunk stays in the table so an
    existing citation still resolves, but it must never be retrieved again.
    This is what keeps the stale-citation metric at zero after a promotion.
  * `embedding is not null` — belt and braces on the two-store boundary. Nothing
    without a vector should be here at all (sample records are never inserted),
    but a half-finished seed must not leak one into the keyword path.

Exercised by the skip-gated integration test; the filter logic it composes is
pure and unit-tested in `hybrid_search.RetrievalFilters`.
"""

from __future__ import annotations

from typing import Any

from src.config import load_config
from src.db.pool import get_pool
from src.retrieval.hybrid_search import RetrievalFilters

_TABLE = "kb_chunks"
_COLUMNS = ("chunk_id, doc, sec, aud, type, citation_style, version, "
            "heading, heading_path, text")
# Live rows only — never a tombstone, never an unembedded row.
_LIVE = "superseded_by is null and embedding is not null"


def _row_to_dict(row: Any) -> dict:
    """A searcher row in the shape `hybrid_search` merges and cites from."""
    return {
        "id": row["chunk_id"],
        "doc": row["doc"],
        # The citation key the agent quotes is the chunk_id ('02-BOND:4.4'),
        # stable across re-wordings. Through v3 this was translated to
        # `clause_ref` here and back again at four other boundaries; the
        # retrieval types now carry the KB's own name, so nothing translates.
        "chunk_id": row["chunk_id"],
        "clause_type": row["type"],
        "aud": row["aud"],
        "citation_style": row["citation_style"],
        # What `stale_citation_rate` compares against: a citation records the
        # version it read, and a later re-embed bumps this past it.
        "version": row["version"],
        "text": f"{row['heading']}\n{row['text']}".strip(),
    }


def _where(filters: RetrievalFilters | None, first_param: int,
           *, prefix: str = "") -> tuple[str, list[Any]]:
    """Compose the WHERE clause: liveness, an optional base predicate, filters."""
    predicate, params = ("", []) if filters is None else filters.sql_predicate(first_param)
    parts = [part for part in (_LIVE, prefix, predicate) if part]
    return f" WHERE {' AND '.join(parts)}", params


class PgClauseSearcher:
    def __init__(self, config) -> None:
        self._config = config

    @classmethod
    async def create(cls) -> "PgClauseSearcher":
        return cls(load_config())

    async def vector_search(self, query_vec: list[float], *, limit: int = 30,
                            filters: RetrievalFilters | None = None) -> list[dict]:
        vec_literal = "[" + ",".join(str(v) for v in query_vec) + "]"
        where, filter_params = _where(filters, first_param=3)
        sql = (
            f"SELECT {_COLUMNS} FROM {_TABLE}{where} "
            "ORDER BY embedding <=> $1::vector LIMIT $2"
        )
        pool = await get_pool(self._config)
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, vec_literal, int(limit), *filter_params)
            return [_row_to_dict(r) for r in rows]

    async def fulltext_search(self, query_text: str, *, limit: int = 30,
                              filters: RetrievalFilters | None = None) -> list[dict]:
        where, filter_params = _where(
            filters, first_param=3,
            prefix="tsv @@ plainto_tsquery('english', $1)",
        )
        sql = (
            f"SELECT {_COLUMNS} FROM {_TABLE}{where} "
            "ORDER BY ts_rank(tsv, plainto_tsquery('english', $1)) DESC LIMIT $2"
        )
        pool = await get_pool(self._config)
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, query_text, int(limit), *filter_params)
            return [_row_to_dict(r) for r in rows]
