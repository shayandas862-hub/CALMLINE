"""The knowledge tool — retrieve_clause over the RAG.

Thin wrapper over an injected ``retriever`` (the existing ``policy_lookup`` in
production; a fake in tests). It normalizes whatever the retriever returns into
a plain dict the agent can cite from. The retriever is expected to return an
object with ``.found`` and ``.clauses`` (each clause having ``.chunk_id`` and
``.text``) — exactly the shape of the existing ``RetrievedContext``.

``citation_style``, ``version`` and ``aud`` travel with each clause, because
provenance has to reach the point where the answer is written: real law cites its
source URL, an Aldercrest invention is labelled an operating standard, and a rule
not yet in force must state its effective date (AD-CL-027). A retriever that
carries no provenance yields ``None`` — an explicit unknown, never a guessed
style.

``version`` travels for a second reason: the loop backfills it onto the reply's
citations from *this* result, so a citation states the version retrieval read
rather than one the model remembered.
"""

from __future__ import annotations

from typing import Any, Callable

# Which document states a product's own rules. The KB is organised one master
# per product, so this is a reading of the corpus rather than a new taxonomy —
# the same three documents the authority matrix cites for its bands.
PRODUCT_DOCS = {
    "lifelong_protection": "01-WOL",     # 01_Whole_of_Life_Assurance_Product_Master
    "horizon_bond": "02-BOND",           # 02_Onshore_Investment_Bond_Product_Master
    "retirement_account": "03-PEN",      # 03_Personal_Pension_Product_Master
}


def retrieve_clause(retriever: Callable[[str], Any], query: str,
                    product_code: str = "", operative_date: str = "") -> dict[str, Any]:
    """Search the rules for ``query`` and return normalized, citable clauses.

    ``product_code`` narrows the search to one product's master document, for a
    question that is only about that product. It **narrows** and never widens:
    an unrecognised code raises rather than quietly searching everything, because
    a filter that silently does nothing is worse than no filter.

    ``operative_date`` is carried through untouched so the caller can apply
    AD-CL-032 — a rule not yet in force must be cited with its effective date.
    The tool does not decide that; it makes deciding it possible.

    There is deliberately no ``aud`` parameter. The audience is bound when the
    retriever is built and is the server's decision (`07-RUNBOOK:4.1`); exposing
    it here would turn "which audience am I" into something the caller asks for.
    """
    doc = _document_for(product_code)
    ctx = retriever(query)
    clauses = list(getattr(ctx, "clauses", []) or [])
    if doc is not None:
        clauses = [c for c in clauses if getattr(c, "doc", None) == doc]
    return {
        "found": bool(clauses),
        "query": query,
        "product_code": product_code,
        "operative_date": operative_date,
        "clauses": [
            {
                "chunk_id": c.chunk_id,
                "doc": getattr(c, "doc", None),
                "clause_type": getattr(c, "clause_type", None),
                "text": c.text,
                "aud": getattr(c, "aud", None),
                "citation_style": getattr(c, "citation_style", None),
                "version": getattr(c, "version", 1),
                # What the searcher scored it. Carried so the trace can record
                # where each chunk placed — `recall@5` needs a ranking, and the
                # clause dicts are all the loop ever sees of a retrieval.
                "score": getattr(c, "score", None),
            }
            for c in clauses
        ],
    }


def _document_for(product_code: str) -> str | None:
    """The master document for ``product_code``, or ``None`` for no filter."""
    if not product_code:
        return None
    try:
        return PRODUCT_DOCS[product_code]
    except KeyError:
        raise ValueError(
            f"unknown product {product_code!r}: expected one of "
            f"{sorted(PRODUCT_DOCS)}"
        ) from None
