"""Context assembler — prepares the final context window for the generator.

Pipeline:
  1. Normalize heterogeneous inputs (SearchResult, ParentDocument,
     StructuralResult, StructuredResult) to a common _NormalizedChunk.
  2. Deduplicate near-identical chunks using Jaccard word-set similarity.
     Chunks are sorted by score descending first; the highest-scored copy wins.
  3. Apply the 6,000-token budget (≈ len(text) // 4). Always keeps at least
     one chunk to avoid returning an empty context.
  4. Reorder survivors via the lost-in-the-middle pattern: highest-scored
     chunk first, second-highest last, remaining in between.
  5. Prepend [Source N] labels and assemble context_text.
  6. Render the system prompt embedding the context and strict-citation rules.

assemble() is synchronous — no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import tiktoken

from app.observability.tracer import _NoopTrace


# BUG #17: was `len(text) // 4` — off by 2-3x for non-English content / code.
# Using tiktoken gives accurate counts so the 6000-token budget is honored.
_ENCODING = tiktoken.get_encoding("cl100k_base")
_DEFAULT_TOKEN_BUDGET = 6000
_DEFAULT_DEDUP_THRESHOLD = 0.85

_SYSTEM_PROMPT_TEMPLATE = """\
You are a personal knowledge assistant. Answer the user's question using ONLY \
the information provided in the CONTEXT section below.

CITATION RULES:
- You MUST cite sources using [Source N] notation for every factual claim.
- Example: "The project deadline is June 1st [Source 2]."
- If multiple sources support a claim, cite all of them: [Source 1][Source 3].
- Never reference a source number that does not appear in the context.

REFUSAL RULES:
- If the context does not contain information relevant to the question, respond \
exactly: "I don't have information about that."
- Do NOT fabricate information or use knowledge outside the provided context.
- Do NOT speculate or infer beyond what the sources explicitly state.

CONTEXT:
{context}"""


# ---------------------------------------------------------------------------
# Public output type
# ---------------------------------------------------------------------------

@dataclass
class AssembledContext:
    system_prompt: str
    context_text: str           # labeled chunks joined with blank lines
    sources: list[dict]         # [{source_label, content, metadata}]
    tools: list[dict]           # tool registry — empty placeholder
    token_estimate: int         # estimated tokens for context_text
    chunks_used: int
    chunks_dropped_dedup: int
    chunks_dropped_budget: int


# ---------------------------------------------------------------------------
# Internal normalized chunk
# ---------------------------------------------------------------------------

@dataclass
class _NormalizedChunk:
    content: str
    score: float
    metadata: dict


# ---------------------------------------------------------------------------
# Normalization — duck-type all supported result types
# ---------------------------------------------------------------------------

def _normalize(item: Any) -> _NormalizedChunk:
    """Convert any retrieval result type to a _NormalizedChunk."""
    # ParentDocument
    if hasattr(item, "full_content"):
        return _NormalizedChunk(
            content=item.full_content,
            score=getattr(item, "score", 0.0),
            metadata=getattr(item, "source_metadata", {}),
        )
    # StructuredResult — format data dict as readable text
    if hasattr(item, "table") and hasattr(item, "data"):
        lines = "\n".join(f"{k}: {v}" for k, v in item.data.items() if v is not None)
        return _NormalizedChunk(
            content=lines or str(item.data),
            score=0.0,
            metadata={"table": item.table, "record_id": item.record_id},
        )
    # SearchResult / StructuralResult (both have .content)
    meta = dict(getattr(item, "metadata", None) or getattr(item, "structural_metadata", {}) or {})
    if "item_id" not in meta and hasattr(item, "item_id"):
        meta["item_id"] = str(item.item_id)
    return _NormalizedChunk(
        content=getattr(item, "content", str(item)),
        score=getattr(item, "score", 0.0),
        metadata=meta,
    )


# ---------------------------------------------------------------------------
# Deduplication — Jaccard word-set similarity
# ---------------------------------------------------------------------------

def _jaccard(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    union = words_a | words_b
    if not union:
        return 1.0
    return len(words_a & words_b) / len(union)


def _deduplicate(
    chunks: list[_NormalizedChunk],
    threshold: float,
) -> tuple[list[_NormalizedChunk], int]:
    """Remove near-duplicates. Chunks must be pre-sorted by score descending."""
    kept: list[_NormalizedChunk] = []
    dropped = 0
    for chunk in chunks:
        if any(_jaccard(chunk.content, k.content) >= threshold for k in kept):
            dropped += 1
        else:
            kept.append(chunk)
    return kept, dropped


# ---------------------------------------------------------------------------
# Token budget
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(_ENCODING.encode(text)))


def _apply_budget(
    chunks: list[_NormalizedChunk],
    budget: int,
) -> tuple[list[_NormalizedChunk], int]:
    """Keep chunks within token budget. Always keeps at least the first."""
    if not chunks:
        return [], 0
    kept: list[_NormalizedChunk] = []
    used = 0
    for i, chunk in enumerate(chunks):
        tokens = _estimate_tokens(chunk.content)
        if i == 0 or used + tokens <= budget:
            kept.append(chunk)
            used += tokens
        else:
            break  # chunks are score-sorted; no benefit in skipping ahead
    return kept, len(chunks) - len(kept)


# ---------------------------------------------------------------------------
# Lost-in-the-middle reorder
# ---------------------------------------------------------------------------

def _lost_in_middle_reorder(chunks: list[_NormalizedChunk]) -> list[_NormalizedChunk]:
    """Place highest-scored chunk first, second-highest last, rest in between.

    For chunks ranked [c1(best), c2, c3, c4, c5(worst)]:
    Result → [c1, c3, c5, c4, c2]

    This keeps the most useful signals at both ends of the context window,
    where LLMs have strongest recall, and buries weaker chunks in the middle.
    """
    if len(chunks) <= 2:
        return list(chunks)
    result: list[_NormalizedChunk | None] = [None] * len(chunks)
    left, right = 0, len(chunks) - 1
    for i, chunk in enumerate(chunks):
        if i % 2 == 0:
            result[left] = chunk
            left += 1
        else:
            result[right] = chunk
            right -= 1
    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Context text + sources assembly
# ---------------------------------------------------------------------------

def _build_context(chunks: list[_NormalizedChunk]) -> tuple[str, list[dict]]:
    """Return (context_text, sources) with [Source N] labels."""
    if not chunks:
        return "", []
    parts: list[str] = []
    sources: list[dict] = []
    for i, chunk in enumerate(chunks, start=1):
        label = f"[Source {i}]"
        parts.append(f"{label}\n{chunk.content}")
        sources.append({
            "source_label": label,
            "content": chunk.content,
            "metadata": chunk.metadata,
        })
    return "\n\n".join(parts), sources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble(
    chunks: list[Any],
    query: str,
    *,
    token_budget: int = _DEFAULT_TOKEN_BUDGET,
    dedup_threshold: float = _DEFAULT_DEDUP_THRESHOLD,
    _trace: Any = None,
) -> AssembledContext:
    """Assemble a context window ready for the generator.

    Args:
        chunks: Any mix of SearchResult, ParentDocument, StructuralResult,
                StructuredResult — normalized internally.
        query: User query string (included in tracing metadata).
        token_budget: Maximum tokens for context_text (default 6000).
        dedup_threshold: Jaccard threshold for near-duplicate removal (default 0.85).
        _trace: Langfuse trace object; no-ops when None.

    Returns:
        AssembledContext ready to pass to generator.py.
    """
    trace = _trace or _NoopTrace()

    with trace.span(
        "context_assembly",
        input={"query": query, "n_chunks_in": len(chunks)},
    ):
        # 1. Normalize
        normalized = [_normalize(c) for c in chunks]

        # 2. Sort by score descending before dedup (keep highest-scored copy)
        normalized.sort(key=lambda c: c.score, reverse=True)

        # 3. Deduplicate
        deduped, dropped_dedup = _deduplicate(normalized, dedup_threshold)

        # 4. Apply token budget (still score-sorted)
        budgeted, dropped_budget = _apply_budget(deduped, token_budget)

        # 5. Lost-in-the-middle reorder
        reordered = _lost_in_middle_reorder(budgeted)

        # 6. Label and assemble
        context_text, sources = _build_context(reordered)
        token_estimate = _estimate_tokens(context_text) if context_text else 0

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            context=context_text if context_text else "(no context available)"
        )

    return AssembledContext(
        system_prompt=system_prompt,
        context_text=context_text,
        sources=sources,
        tools=[],
        token_estimate=token_estimate,
        chunks_used=len(reordered),
        chunks_dropped_dedup=dropped_dedup,
        chunks_dropped_budget=dropped_budget,
    )
