# MIT License — Copyright (c) 2026 Shayan Das
# Adapted (kept deliberately lean) from the author's earlier original
# work (vendor/secondbrain/query_assembler.py). The source assembles a
# token-budgeted prose context block for a generation step; CalmLine instead
# returns STRUCTURED cited clauses for the agent's tool, so the agent can quote
# exact clause IDs. Kept: dedup and the typed found/not-found signal. Dropped:
# the token-budget / lost-in-the-middle machinery a ~70-clause corpus needn't.
"""Turn ranked clause hits into a typed, deduplicated, cited result.

Each citation carries its **`citation_style`** through from the retrieved chunk,
so the provenance rule is enforceable where the answer is written: real law cites
its source URL, an Aldercrest invention is labelled an operating standard, and a
rule not yet in force must state its effective date (AD-CL-027). A citation that
arrives without a style keeps `None` — an explicit unknown the caller can handle
conservatively, never a guess.

It carries its **`version`** through for the same reason: `stale_citation_rate`
asks whether a cited chunk has since been re-embedded, and it can only ask that
of a citation that states which version it read.

Both facts come from **retrieval, never from the model**. The model writes the
answer; the loop states the provenance.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.retrieval.hybrid_search import ClauseHit

_DEFAULT_MAX_CLAUSES = 8


@dataclass(frozen=True)
class CitedClause:
    chunk_id: str
    doc: str
    clause_type: str
    text: str
    score: float
    aud: str = "all"
    citation_style: str | None = None
    version: int = 1


@dataclass(frozen=True)
class RetrievedContext:
    """What the policy-lookup tool hands the agent."""
    clauses: list[CitedClause]

    @property
    def found(self) -> bool:
        return bool(self.clauses)


def assemble(hits: list[ClauseHit], *, max_clauses: int = _DEFAULT_MAX_CLAUSES) -> RetrievedContext:
    """Dedup by chunk_id (keeping the highest score), order by score, cap."""
    best: dict[str, ClauseHit] = {}
    for hit in hits:
        current = best.get(hit.chunk_id)
        if current is None or hit.score > current.score:
            best[hit.chunk_id] = hit

    ordered = sorted(best.values(), key=lambda h: h.score, reverse=True)[:max_clauses]
    clauses = [
        CitedClause(
            chunk_id=h.chunk_id,
            doc=h.doc,
            clause_type=h.clause_type,
            text=h.text,
            score=h.score,
            aud=h.aud,
            citation_style=h.citation_style,
            version=h.version,
        )
        for h in ordered
    ]
    return RetrievedContext(clauses=clauses)
