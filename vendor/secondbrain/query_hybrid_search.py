"""Hybrid search — pgvector cosine + tsvector keyword, merged via RRF.

Two searches run in parallel (asyncio.gather). Results are merged with
Reciprocal Rank Fusion (k=60), deduplicated, and truncated to top_k (default 20).
Metadata filters are applied as WHERE constraints to both searches.

Inject _db and _embedder in tests to avoid real DB / OpenAI calls.
_db   : any object with async vector_search() and fulltext_search() methods.
_embedder : callable(texts: list[str]) -> list[list[float]] (no prefix added internally).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import openai

from app.core.config import get_settings
from app.observability.tracer import _NoopTrace


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class MetadataFilters:
    source_type: str | None = None
    topic: str | None = None
    date_after: str | None = None   # ISO date string, e.g. "2024-01-01"
    date_before: str | None = None


@dataclass
class SearchResult:
    id: str
    item_id: str
    user_id: str
    content: str
    metadata: dict
    chunk_index: int
    score: float  # RRF score


# ---------------------------------------------------------------------------
# RRF helper
# ---------------------------------------------------------------------------

def _rrf_merge(
    vector_rows: list[dict],
    fulltext_rows: list[dict],
    *,
    k: int = 60,
    top_k: int = 20,
) -> list[SearchResult]:
    """Merge two ranked lists with Reciprocal Rank Fusion.

    score(chunk) = Σ 1/(k + rank)   where rank is 1-based position in each list.
    """
    scores: dict[str, float] = {}
    rows_by_id: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows, start=1):
        cid = row["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        rows_by_id[cid] = row

    for rank, row in enumerate(fulltext_rows, start=1):
        cid = row["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        rows_by_id[cid] = row

    ranked = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)[:top_k]

    return [
        SearchResult(
            id=cid,
            item_id=rows_by_id[cid]["item_id"],
            user_id=rows_by_id[cid]["user_id"],
            content=rows_by_id[cid]["content"],
            metadata=rows_by_id[cid]["metadata"],
            chunk_index=rows_by_id[cid]["chunk_index"],
            score=scores[cid],
        )
        for cid in ranked
    ]


# ---------------------------------------------------------------------------
# Default embedder  (query: prefix — distinct from passage: in embedder.py)
# ---------------------------------------------------------------------------

def _default_embedder(texts: list[str]) -> list[list[float]]:
    client = openai.OpenAI(api_key=get_settings().OPENAI_API_KEY)
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in resp.data]


# ---------------------------------------------------------------------------
# Async DB searcher (production — asyncpg direct SQL)
# ---------------------------------------------------------------------------

class _AsyncDBSearcher:
    """Runs vector and fulltext searches against Postgres via asyncpg."""

    def __init__(self, database_url: str) -> None:
        self._url = database_url

    @classmethod
    async def create(cls, database_url: str) -> "_AsyncDBSearcher":
        return cls(database_url)

    async def vector_search(
        self,
        query_vec: list[float],
        user_id: str,
        *,
        filters: MetadataFilters | None = None,
        limit: int = 30,
    ) -> list[dict]:
        from app.db.pool import get_pool

        # BUG #6 fix: vector + limit parameterized (no f-string SQL injection seam).
        conditions = ["c.user_id = $1"]
        params: list[Any] = [user_id]
        _apply_filters(conditions, params, filters)
        # `$N` placeholders for the vector and limit
        vec_idx = len(params) + 1
        limit_idx = len(params) + 2
        params.append(query_vec)
        params.append(int(limit))

        sql = f"""
            SELECT c.id, c.item_id, c.user_id, c.content,
                   c.metadata::text AS metadata_json, c.chunk_index
            FROM chunks c
            WHERE {" AND ".join(conditions)}
            ORDER BY c.embedding <=> ${vec_idx}::vector
            LIMIT ${limit_idx}
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Cast list[float] to a pgvector-compatible textual representation.
            params[vec_idx - 1] = "[" + ",".join(str(v) for v in query_vec) + "]"
            rows = await conn.fetch(sql, *params)
            return [_row_to_dict(r) for r in rows]

    async def fulltext_search(
        self,
        query_text: str,
        user_id: str,
        *,
        filters: MetadataFilters | None = None,
        limit: int = 30,
    ) -> list[dict]:
        from app.db.pool import get_pool

        conditions = [
            "c.user_id = $1",
            "c.tsvector_content @@ plainto_tsquery('english', $2)",
        ]
        params: list[Any] = [user_id, query_text]
        _apply_filters(conditions, params, filters)
        limit_idx = len(params) + 1
        params.append(int(limit))

        sql = f"""
            SELECT c.id, c.item_id, c.user_id, c.content,
                   c.metadata::text AS metadata_json, c.chunk_index
            FROM chunks c
            WHERE {" AND ".join(conditions)}
            ORDER BY ts_rank(c.tsvector_content, plainto_tsquery('english', $2)) DESC
            LIMIT ${limit_idx}
        """
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [_row_to_dict(r) for r in rows]


def _apply_filters(conditions: list[str], params: list[Any], filters: MetadataFilters | None) -> None:
    if filters is None:
        return
    n = len(params)
    if filters.source_type:
        n += 1
        conditions.append(f"c.metadata->>'source_type' = ${n}")
        params.append(filters.source_type)
    if filters.topic:
        n += 1
        conditions.append(f"c.metadata->>'topic' = ${n}")
        params.append(filters.topic)
    if filters.date_after:
        n += 1
        conditions.append(f"c.created_at >= ${n}::timestamptz")
        params.append(filters.date_after)
    if filters.date_before:
        n += 1
        conditions.append(f"c.created_at <= ${n}::timestamptz")
        params.append(filters.date_before)


def _row_to_dict(row: Any) -> dict:
    metadata = row["metadata_json"]
    return {
        "id": str(row["id"]),
        "item_id": str(row["item_id"]),
        "user_id": str(row["user_id"]),
        "content": row["content"],
        "metadata": json.loads(metadata) if isinstance(metadata, str) else (metadata or {}),
        "chunk_index": row["chunk_index"],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def hybrid_search(
    query: str,
    user_id: str,
    *,
    metadata_filters: MetadataFilters | None = None,
    top_k: int = 20,
    rrf_k: int = 60,
    _embedder=None,
    _db=None,
    _trace=None,
) -> list[SearchResult]:
    """Run hybrid search and return top-k results ranked by RRF score.

    Args:
        query: Natural-language query (will be embedded with 'query: ' prefix).
        user_id: Row-level security scope.
        metadata_filters: Optional date/type/topic constraints for both searches.
        top_k: Maximum results to return (default 20).
        rrf_k: RRF smoothing constant (default 60).
        _embedder: Inject for tests. callable(texts) -> list[list[float]].
        _db: Inject for tests. Object with vector_search / fulltext_search async methods.
        _trace: Langfuse trace object for span emission. If None, no-ops.
    """
    trace = _trace or _NoopTrace()
    embedder_fn = _embedder or _default_embedder
    db = _db or await _AsyncDBSearcher.create(get_settings().DATABASE_URL)

    with trace.span("hybrid_search", input={"query": query, "user_id": user_id}):
        # Embed the query with the retrieval prefix
        query_vec = embedder_fn(["query: " + query])[0]

        # Run vector + fulltext in parallel
        vector_rows, fulltext_rows = await asyncio.gather(
            db.vector_search(
                query_vec,
                user_id,
                filters=metadata_filters,
                limit=30,
            ),
            db.fulltext_search(
                query,
                user_id,
                filters=metadata_filters,
                limit=30,
            ),
        )

        results = _rrf_merge(vector_rows, fulltext_rows, k=rrf_k, top_k=top_k)

    return results
