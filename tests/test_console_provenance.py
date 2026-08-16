"""v4 phase 5 · Task 0 — a citation states what RETRIEVAL said, not what the
model remembered.

Split from ``tests/test_console_loop.py``, which was at 279 lines and would have
crossed the 300-line rule. One job per file: this one is about provenance
backfill, next door is about the loop's control flow.

Why this exists at all. ``citation_style`` was model-supplied: the model was
expected to copy it out of the tool result and write it back into its structured
reply. Running the same question on two models showed why that is not a
contract — ``claude-haiku-4-5`` returned ``None`` for both citations where
``claude-sonnet-5`` returned ``cite_source`` (D-CL-061). The style drives the
provenance chip on screen, so the display silently degraded to "style unknown"
on one model and not the other, with nothing failing.

So the loop states both facts, exactly as it already overwrites ``tools_used``:
the model writes the answer, the loop states what happened. AD-CL-032's
effective-note rule then stops depending on the model having remembered a style.

No live API calls — the fakes stand in for the SDK response objects.
"""

import json

from src.agent.console_loop import run_console_agent
from src.agent.tools.registry import Tool, ToolRegistry

OPERATIVE_DATE = "2026-04-12"
MODEL = "claude-sonnet-5"


# ── fakes for the Anthropic SDK surface ────────────────────────────────
class Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def _tool_use(name="retrieve_clause", args=None, id="tu_1"):
    return Blk(type="tool_use", name=name, input=args or {"query": "x"}, id=id)


def _retrieve(*, query: str) -> dict:
    """Retrieval knows the style and the version. The model is never asked."""
    return {"found": True, "query": query, "clauses": [
        {"chunk_id": "02-BOND:4.9", "citation_style": "aldercrest_standard",
         "version": 4},
    ]}


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool("retrieve_clause", "search the rules", _retrieve,
                      params={"query": "what to look up"}))
    return reg


def _answer(citations) -> str:
    return json.dumps({
        "answer_text": "A withdrawal that size needs back-office approval.",
        "citations": citations,
        "abstained": False,
        "tools_used": [],
    })


def _run(model_citations):
    """One tool round-trip, then the model's reply carrying ``model_citations``."""
    client = FakeClient([
        Resp("tool_use", [_tool_use()]),
        Resp("end_turn", [Blk(type="text", text=_answer(model_citations))]),
    ])
    return run_console_agent(
        "does the policy allow a £40,000 withdrawal?",
        client=client, registry=_registry(), model=MODEL,
        operative_date=OPERATIVE_DATE, audience="front_office",
    )


# ── the backfill ───────────────────────────────────────────────────────

def test_a_style_the_model_omitted_is_filled_in_from_retrieval():
    # Arrange — the model returns a citation with NO style, the exact failure
    # observed on claude-haiku-4-5.
    # Act
    result = _run([{"chunk_id": "02-BOND:4.9"}])

    # Assert
    assert result.reply.citations[0].citation_style == "aldercrest_standard"


def test_a_version_the_model_omitted_is_filled_in_from_retrieval():
    # The model is not asked for a version and never supplies one; without the
    # backfill stale_citation_rate would have nothing to read.
    # Act
    result = _run([{"chunk_id": "02-BOND:4.9"}])

    # Assert
    assert result.reply.citations[0].version == 4


def test_a_style_the_model_got_wrong_is_corrected_not_trusted():
    # The point is not "fill the gap" but "state the fact". A model that copies
    # the wrong style is as wrong as one that omits it, and the screen cannot
    # tell the difference.
    # Act
    result = _run([{"chunk_id": "02-BOND:4.9", "citation_style": "cite_source"}])

    # Assert
    assert result.reply.citations[0].citation_style == "aldercrest_standard"
    assert result.reply.citations[0].version == 4


def test_the_backfill_keeps_the_chunk_id_the_model_cited():
    # Backfilling provenance must not rewrite WHICH clause was cited — that is
    # the model's claim, and the grounding check is what polices it.
    # Act
    result = _run([{"chunk_id": "02-BOND:4.9"}])

    # Assert
    assert [c.chunk_id for c in result.reply.citations] == ["02-BOND:4.9"]
