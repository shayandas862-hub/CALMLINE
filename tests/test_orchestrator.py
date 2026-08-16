"""v3 phase 2 · Task 7 — the orchestrator routes a request to the right tool.

The model (a fake here; a real LLM behind the same interface later) chooses the
tool; the orchestrator dispatches it through the registry. The routing
intelligence lives in the model, so the orchestrator is model-agnostic.
"""

from functools import partial
from types import SimpleNamespace

import pytest

from src.agent.orchestrator import ToolCall, orchestrate
from src.agent.tools.case_tools import raise_case
from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.record_tools import get_transaction_history
from src.agent.tools.registry import Tool, ToolError, ToolRegistry
from src.records.models import gbp
from src.records.seed import build_seed_book


def _retriever(_q):
    return SimpleNamespace(found=True, clauses=[
        SimpleNamespace(chunk_id="CH-2.2", doc="claims_handling", clause_type="procedure",
                        text="…the death certificate…")])


def _build():
    book = build_seed_book()
    created = []
    reg = ToolRegistry()
    reg.register(Tool("retrieve_clause", "search rules", partial(retrieve_clause, _retriever)))
    reg.register(Tool("get_transaction_history", "ledger", partial(get_transaction_history, book, as_at="2026-04-12")))
    reg.register(Tool("raise_case", "open a case",
                      partial(raise_case, lambda req: created.append({**req, "case_id": "CASE-1"}) or created[-1])))
    return reg, created


class _FakeModel:
    """Deterministic stand-in for the LLM: maps a request to a tool call."""

    def select(self, request, tool_names):
        r = request.lower()
        if "raise" in r:
            return ToolCall("raise_case", {"policy_no": "LP-20419876", "request": request, "priority": "high"})
        if "balance" in r or "history" in r or "withdraw" in r:
            return ToolCall("get_transaction_history", {"policy_no": "LP-20419876"})
        return ToolCall("retrieve_clause", {"query": request})


def test_claim_question_routes_to_retrieve_clause():
    reg, _ = _build()
    out = orchestrate("how do they claim?", reg, _FakeModel())
    assert out["tool"] == "retrieve_clause"
    assert out["result"]["clauses"][0]["chunk_id"] == "CH-2.2"


def test_balance_question_routes_to_history():
    reg, _ = _build()
    out = orchestrate("what's their balance?", reg, _FakeModel())
    assert out["tool"] == "get_transaction_history"
    assert out["result"]["value_pence"] == gbp(46_210)


def test_raise_request_routes_to_raise_case():
    reg, created = _build()
    out = orchestrate("raise a claim for them", reg, _FakeModel())
    assert out["tool"] == "raise_case"
    assert out["result"]["case_id"] == "CASE-1"
    assert created[0]["policy_no"] == "LP-20419876"


def test_orchestrator_surfaces_an_unknown_tool_from_the_model():
    reg, _ = _build()

    class BadModel:
        def select(self, request, tool_names):
            return ToolCall("nonexistent_tool", {})

    with pytest.raises(ToolError):
        orchestrate("anything", reg, BadModel())
