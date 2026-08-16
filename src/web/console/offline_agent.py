"""The deterministic offline agent stand-in for the console.

``KeywordModel`` implements the ``ModelClient`` interface — it maps a handler's
message to a tool call by keyword, with no LLM. ``build_offline_retriever``
returns a keyword-overlap search over the Aldercrest knowledge base so
``retrieve_clause`` answers with a real, cited chunk offline. Both are demo
wiring; the live hybrid pipeline (vector + tsvector + RRF + rerank) plugs in
behind the same interface once the credentials checkpoint clears.

Two guarantees this file is responsible for keeping offline, because offline is
where the console actually runs today:

  * **Sample records are never retrievable.** This retriever is the index when
    there is no database, so ``embed=False`` chunks are excluded from it exactly
    as they are excluded from the live index (AD-CL-023). Facts come from the
    system of record; no record is here to be cited stale.
  * **Audience filtering is the server's decision.** ``aud`` is supplied when the
    retriever is built, never taken from a query. A chunk is visible if its own
    ``aud`` is that audience or the shared ``"all"``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Optional

from src.agent.orchestrator import ToolCall
from src.corpus.kb_parser import KbChunk, parse_kb
from src.retrieval.assemble import CitedClause, RetrievedContext

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "kb"

_STOP = frozenset({"the", "a", "an", "of", "to", "is", "do", "how", "what", "i",
                   "they", "them", "their", "my", "for", "on", "in", "can", "s",
                   "and", "it", "this", "that", "are", "have", "has", "with"})

# Reference material answers "what does this word mean", not "what is the rule".
# Operative content should win a tie against it — the same intent the retired
# clause retriever had when it demoted `definition` clauses.
_REFERENCE_TYPES = frozenset({"glossary", "data_dictionary", "sources", "caveats"})
_REFERENCE_WEIGHT = 0.6

_DEFAULT_TOP_K = 3


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP}


class KeywordModel:
    """A deterministic ``ModelClient``: choose a tool from the message's words."""

    def __init__(self, policy_no: Optional[str] = None) -> None:
        self._policy_no = policy_no

    def select(self, request: str, tool_names: list[str]) -> ToolCall:
        r = request.lower()
        if "raise" in r or "open a case" in r:
            return ToolCall("raise_case", {"policy_no": self._policy_no,
                                           "request": request, "priority": "high"})
        if any(w in r for w in ("balance", "history", "withdraw", "transaction", "ledger")):
            return ToolCall("get_transaction_history", {"policy_no": self._policy_no})
        if any(w in r for w in ("record", "details", "policy info")):
            return ToolCall("lookup_policy_record", {"policy_no": self._policy_no})
        return ToolCall("retrieve_clause", {"query": request})


def searchable_chunks(kb_dir: Path | str = KB_DIR, *, aud: str | None = None
                      ) -> list[KbChunk]:
    """The KB chunks this session may retrieve — never the sample records."""
    audiences = None if aud is None else {aud, "all"}
    return [
        chunk for chunk in parse_kb(kb_dir)
        if chunk.embed and (audiences is None or chunk.aud in audiences)
    ]


def build_offline_retriever(kb_dir: Path | str = KB_DIR, *,
                            top_k: int = _DEFAULT_TOP_K, aud: str | None = None
                            ) -> Callable[[str], Any]:
    """Return a keyword-overlap retriever over the KB (parsed once, at build time).

    `aud` is the session's audience, applied when the retriever is built so a
    query can never widen it.
    """
    indexed = [(chunk, _tokens(chunk.embed_text))
               for chunk in searchable_chunks(kb_dir, aud=aud)]

    def retrieve(query: str) -> RetrievedContext:
        wanted = _tokens(query)
        scored = [
            (len(wanted & tokens) * _weight(chunk), chunk)
            for chunk, tokens in indexed
        ]
        hits = [chunk for score, chunk in
                sorted(scored, key=lambda pair: -pair[0]) if score > 0][:top_k]
        return RetrievedContext(clauses=[_cite(chunk) for chunk in hits])

    return retrieve


def _weight(chunk: KbChunk) -> float:
    return _REFERENCE_WEIGHT if chunk.type in _REFERENCE_TYPES else 1.0


def _cite(chunk: KbChunk) -> CitedClause:
    """A KB chunk as the citation the agent quotes.

    `text` is the heading plus the body, so a citation is locatable in the source
    document and so the 15 heading-only section chunks still cite as something.
    """
    return CitedClause(
        chunk_id=chunk.chunk_id,
        doc=chunk.doc,
        clause_type=chunk.type,
        text=chunk.embed_text,
        score=1.0,
        aud=chunk.aud,
        citation_style=chunk.citation_style,
        version=chunk.version,
    )
