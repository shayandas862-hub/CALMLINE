"""What retrieval said about a chunk, stated onto the reply that cites it.

Split out of ``console_loop.py`` at the 300-line rule, and it is its own job:
the loop decides when to call a tool and when to stop, this decides what a
citation is allowed to claim about itself.

**A citation states what retrieval said, not what the model remembered.**
``citation_style`` used to be model-supplied — the model was asked to copy it
out of the tool result into its structured reply. Running one question on two
models showed why that is not a contract: ``claude-haiku-4-5`` returned ``None``
for both citations where ``claude-sonnet-5`` returned ``cite_source``
(D-CL-061). The style drives the provenance chip on screen, so the display
degraded to "style unknown" on one model and not the other, silently, with
nothing failing.

The same argument covers ``version``, which the model is never asked for at all
and which ``stale_citation_rate`` cannot be computed without.

So both are taken from the tool result the loop already tracks for its grounding
check — the same principle by which the loop overwrites ``tools_used``: the
model writes the answer, the loop states the facts.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import ValidationError

from src.agent.loop import AgentError
from src.agent.reply import Citation


def retrieved_provenance(result: Any) -> Optional[dict[str, dict[str, Any]]]:
    """What retrieval said about each chunk it returned, keyed by chunk id.

    Two jobs in one pass. The keys make grounding checkable — a cited id that is
    not among them was never returned. The values carry the provenance the reply
    must state: the style that drives the citation chip, and the version
    ``stale_citation_rate`` compares against.

    ``None`` for a result that is not a retrieval — a valuation has no clauses,
    and that is different from a retrieval which found nothing.
    """
    if isinstance(result, dict) and "clauses" in result:
        return {
            c.get("chunk_id", ""): {"citation_style": c.get("citation_style"),
                                    "version": c.get("version")}
            for c in result["clauses"]
        }
    return None


def stated_provenance(citations: list[Citation],
                      retrieved: dict[str, dict[str, Any]]) -> list[Citation]:
    """The citations with style and version taken from retrieval, not the model.

    A model that omits the style is corrected, and so is one that copies the
    wrong style — the screen cannot tell those apart, and both make the chip
    lie about where a rule came from.

    Rebuilt rather than ``model_copy``-ed, so ``Citation``'s own validators run
    against the *stated* style. That is what makes AD-CL-032 enforceable: a
    clause retrieval says is not yet in force must cite its effective date, and
    until now that rule only fired when the model happened to have remembered
    the style that triggers it.

    A citation retrieval never returned is left untouched. ``_check_grounding``
    has already raised on it, and inventing provenance for a clause nobody
    returned would be the fabrication this whole module exists to prevent.
    """
    stated: list[Citation] = []
    for citation in citations:
        facts = retrieved.get(citation.chunk_id)
        if facts is None:
            stated.append(citation)
            continue
        try:
            stated.append(Citation(**{**citation.model_dump(), **facts}))
        except ValidationError as exc:
            raise AgentError(
                f"retrieval says {citation.chunk_id} is cited as "
                f"{facts.get('citation_style')!r}, and the answer does not "
                f"satisfy that: {exc}") from exc
    return stated
