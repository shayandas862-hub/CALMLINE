# MIT License — Copyright (c) 2026 Shayan Das
# Adapted from the author's earlier original work
# (vendor/secondbrain/query_hybrid_search.py). Changes for CalmLine:
#   - SINGLE-TENANT: the user_id row-level predicate is removed.
#   - targets kb_chunks (doc, chunk_id, type, text, embedding, tsv) and returns
#     ClauseHit instead of the multi-tenant SearchResult.
#   - query prefix comes from src/constants.py.
# The RRF merge, the parallel vector+fulltext fan-out, and the _db/_embedder
# test seams are preserved verbatim in spirit.
"""Hybrid search — pgvector cosine + tsvector keyword, merged via RRF.

Vector and fulltext searches run in parallel and are fused with Reciprocal
Rank Fusion (k=60). Inject `_db` and `_embedder` in tests to avoid DB/OpenAI.

Retrieval is **filter-then-search** (`data/kb/README.md` §4): the audience comes
from the server-side session and the document set from the policy's product
prefix, and both narrow the candidates before similarity ranking. That collapses
the KB's deliberate per-product duplication onto the right copy, and it keeps
audience-restricted material out of the wrong session.

The filter is applied **twice, deliberately**: pushed down to the searcher for
the efficiency, then re-checked against the rows that come back. Role
enforcement is a guarantee, not a request — a searcher that ignores the filter
must not be able to leak a restricted chunk, and a row that declares no audience
is refused rather than assumed public.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable

from src import constants


@dataclass(frozen=True)
class RetrievalFilters:
    """What a session is allowed to see, derived server-side — never from input.

    `aud` is the session's audience; a chunk qualifies if its own `aud` is that
    audience or the shared `"all"`. `docs`, when given, restricts to a set of
    KB documents (the policy's product plus the cross-product manuals).
    """
    aud: str | None = None
    docs: frozenset[str] | None = None

    @property
    def audiences(self) -> tuple[str, ...]:
        """The `aud` values a chunk may carry to be visible to this session."""
        return () if self.aud is None else (self.aud, "all")

    @property
    def restricts(self) -> bool:
        """Whether this filter narrows anything at all."""
        return self.aud is not None or self.docs is not None

    def allows(self, row: dict) -> bool:
        """Whether a searcher's row may be shown. Absent metadata is refused."""
        if self.audiences and row.get("aud") not in self.audiences:
            return False
        return not (self.docs is not None and row.get("doc") not in self.docs)

    def sql_predicate(self, first_param: int) -> tuple[str, list[Any]]:
        """A `WHERE` fragment numbered from `$first_param`, plus its parameters.

        Always parameterised: no filter value is ever interpolated into the query
        text, server-derived or not. Doc sets are sorted so the same filter
        always yields the same SQL — a frozenset's iteration order must not leak
        into a query plan.
        """
        clauses: list[str] = []
        params: list[Any] = []
        for column, values in (("aud", list(self.audiences)),
                               ("doc", sorted(self.docs) if self.docs else [])):
            if values:
                clauses.append(f"{column} = ANY(${first_param + len(params)})")
                params.append(values)
        return " AND ".join(clauses), params


@dataclass(frozen=True)
class ClauseHit:
    clause_id: str  # the searcher's row key, what RRF merges on
    doc: str
    # The citation key the agent quotes — the KB's own chunk id ('02-BOND:4.4'),
    # stable across re-wordings. Named `clause_ref` through v3, which made every
    # consumer translate at its own boundary.
    chunk_id: str
    clause_type: str
    text: str
    score: float  # RRF score (replaced by relevance after rerank)
    aud: str = "all"
    # How an answer must attribute this chunk. `None` means the row carried no
    # provenance — better an explicit unknown than a guessed citation style.
    citation_style: str | None = None
    # What `stale_citation_rate` compares a cited chunk against. 1 is not a
    # guess: `KbChunk.version` and the `kb_chunks` column both declare it, so a
    # chunk that has never been re-embedded *is* version 1.
    version: int = 1


class _NoopTrace:
    @contextmanager
    def span(self, *args, **kwargs):
        yield


def _rrf_merge(
    vector_rows: list[dict],
    fulltext_rows: list[dict],
    *,
    k: int = 60,
    top_k: int = 20,
) -> list[ClauseHit]:
    """Reciprocal Rank Fusion: score = Σ 1/(k + rank) over both ranked lists."""
    scores: dict[str, float] = {}
    rows_by_id: dict[str, dict] = {}
    for ranked_rows in (vector_rows, fulltext_rows):
        for rank, row in enumerate(ranked_rows, start=1):
            cid = row["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            rows_by_id[cid] = row

    top = sorted(scores, key=lambda cid: scores[cid], reverse=True)[:top_k]
    return [_to_hit(rows_by_id[cid], scores[cid]) for cid in top]


def _to_hit(row: dict, score: float) -> ClauseHit:
    return ClauseHit(
        clause_id=str(row["id"]),
        doc=row["doc"],
        chunk_id=row["chunk_id"],
        clause_type=row["clause_type"],
        text=row["text"],
        score=score,
        aud=row.get("aud", "all"),
        citation_style=row.get("citation_style"),
        version=row.get("version", 1),
    )


async def hybrid_search(
    query: str,
    *,
    filters: RetrievalFilters | None = None,
    top_k: int = 20,
    rrf_k: int = 60,
    _embedder: Callable[[list[str]], list[list[float]]] | None = None,
    _db: Any = None,
    _trace: Any = None,
) -> list[ClauseHit]:
    """Return the top-k chunks for `query`, filtered then ranked by RRF score.

    `query` is embedded with the QUERY_PREFIX for the vector search; the raw
    query text drives the fulltext search. `filters` narrows by audience and
    document — pushed down to the searcher, then re-applied to its rows.
    Single-tenant — no row scoping.
    """
    trace = _trace or _NoopTrace()
    embedder_fn = _embedder or _lazy_embedder()
    db = _db or await _lazy_db()

    with trace.span("hybrid_search", input={"query": query}):
        query_vec = embedder_fn([constants.QUERY_PREFIX + query])[0]
        vector_rows, fulltext_rows = await asyncio.gather(
            db.vector_search(query_vec, limit=30, filters=filters),
            db.fulltext_search(query, limit=30, filters=filters),
        )
        return _rrf_merge(
            _permitted(vector_rows, filters),
            _permitted(fulltext_rows, filters),
            k=rrf_k, top_k=top_k,
        )


def _permitted(rows: list[dict], filters: RetrievalFilters | None) -> list[dict]:
    """Drop rows the filter forbids, whatever the searcher chose to return."""
    if filters is None or not filters.restricts:
        return rows
    return [row for row in rows if filters.allows(row)]


# --- production wiring (exercised only by the deferred integration test) ----

def _lazy_embedder() -> Callable[[list[str]], list[list[float]]]:
    from src.corpus.embed import embed

    # The corpus embedder prefixes with PASSAGE_PREFIX; the query path needs
    # the QUERY_PREFIX already applied by the caller, so embed raw here.
    def _e(texts: list[str]) -> list[list[float]]:
        import openai

        from src.config import load_config

        client = openai.OpenAI(api_key=load_config().OPENAI_API_KEY)
        resp = client.embeddings.create(model=constants.EMBED_MODEL, input=texts)
        return [item.embedding for item in resp.data]

    return _e


async def _lazy_db() -> Any:
    from src.retrieval._pg_searcher import PgClauseSearcher

    return await PgClauseSearcher.create()
