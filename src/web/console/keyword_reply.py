"""The keyword path's answer, in the console's own reply shape.

Split from ``agent_routes.py`` at the 300-line rule, and it is its own job: the
route decides who may ask and records what happened, this decides what the
offline stand-in actually *says*.

Phase 4 left this path returning a raw ``{tool, args, result}`` dispatch
(D-CL-058) — no ``answer_text``, no citations, nothing to persist and nothing
for the ops screen to fold over. Giving both paths one shape is what keeps the
five metrics **pure folds over a single record type**; the alternative, nullable
fields plus a "was this a real answer?" guard inside every metric, would let the
offline demo produce numbers the live path never would (D-CL-060).

The wording per tool matches what the console already rendered, so the offline
answer reads as it always did — it is now a reply rather than a dump the front
end had to interpret.
"""

from __future__ import annotations

from src.agent.reply import Citation, ConsoleReply, citations_from_clauses
from src.agent.trace import DecisionTrace


def keyword_reply(outcome: dict) -> tuple[ConsoleReply, DecisionTrace]:
    """The keyword path's ``{tool, args, result}``, as a ``ConsoleReply``.

    Phase 4 left this path returning a raw tool dispatch (D-CL-058) — no
    ``answer_text``, no citations, nothing to persist and nothing for the ops
    screen to fold over. Giving both paths one shape is what keeps the five
    metrics **pure folds over a single record type**; the alternative, nullable
    fields plus a "was this a real answer?" guard inside every metric, would let
    the offline demo produce numbers the live path never would.

    The wording matches what the console already rendered for each tool, so the
    offline answer reads the same as before — it is now a reply rather than a
    dump the front end had to interpret.

    A trace comes back too, because a record needs both halves and the keyword
    path has no loop to build one.
    """
    tool = outcome.get("tool") or ""
    result = outcome.get("result") or {}
    trace = DecisionTrace()
    trace.tool_call(tool, outcome.get("args") or {})

    clauses = result.get("clauses") or []
    refs = [c.get("chunk_id", "") for c in clauses]
    trace.tool_result(tool, f"{len(clauses)} clause(s)" if clauses else "found",
                      refs=refs if tool == "retrieve_clause" else None)

    text, citations = _keyword_text(tool, result, clauses)
    if not text:
        return ConsoleReply(
            answer_text="I can't answer that from the record or the wordings — "
                        "I'd check the policy directly rather than guess.",
            abstained=True,
            abstention_reason=f"the keyword path found nothing for {tool!r}",
            tools_used=[tool] if tool else [],
        ), trace
    return ConsoleReply(answer_text=text, citations=citations,
                        tools_used=[tool] if tool else []), trace


def _keyword_text(tool: str, result: dict,
                  clauses: list) -> tuple[str, list[Citation]]:
    """The sentence for each tool, and the citations behind it if any."""
    if tool == "retrieve_clause":
        if not result.get("found") or not clauses:
            return "", []
        return clauses[0].get("text", ""), citations_from_clauses(clauses[:1])
    if tool == "get_transaction_history" and result.get("found"):
        return (f"Value as at {result.get('as_at')} is {result.get('value')}, "
                f"across {len(result.get('entries') or [])} recorded "
                f"movement(s)."), []
    if tool == "lookup_policy_record" and result.get("found"):
        holder = (result.get("holder") or {}).get("name", "")
        return f"{holder} — current value {result.get('current_value')}.", []
    if tool == "get_valuation" and result.get("found"):
        return (f"It was worth {result.get('value')} as at "
                f"{result.get('as_at')}."), []
    return "", []
