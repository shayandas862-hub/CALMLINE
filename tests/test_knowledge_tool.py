"""v3 phase 2 · Task 4 — retrieve_clause wraps the RAG behind an injected retriever.

In production the retriever is the existing `policy_lookup`; here it's a fake, so
the tool is proven with no DB or keys.
"""

from functools import partial
from types import SimpleNamespace

from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.registry import Tool, ToolRegistry


def _clause(ref, text):
    return SimpleNamespace(chunk_id=ref, doc="claims_handling", clause_type="procedure", text=text)


def _found_retriever(_query):
    return SimpleNamespace(found=True, clauses=[_clause("CH-2.2", "…the death certificate…")])


def _empty_retriever(_query):
    return SimpleNamespace(found=False, clauses=[])


def test_retrieve_normalizes_found_clauses():
    out = retrieve_clause(_found_retriever, "how do they claim?")
    assert out["found"] is True
    assert out["clauses"][0]["chunk_id"] == "CH-2.2"
    assert "death certificate" in out["clauses"][0]["text"]
    assert out["query"] == "how do they claim?"


def test_retrieve_reports_nothing_found():
    out = retrieve_clause(_empty_retriever, "unrelated question")
    assert out["found"] is False
    assert out["clauses"] == []


def test_retrieve_clause_works_through_the_registry():
    reg = ToolRegistry()
    reg.register(Tool("retrieve_clause", "search the rules", partial(retrieve_clause, _found_retriever)))
    out = reg.dispatch("retrieve_clause", {"query": "how do they claim?"})
    assert out["clauses"][0]["chunk_id"] == "CH-2.2"


# --- provenance must survive the tool boundary ---------------------------

def test_the_citation_style_reaches_the_agent():
    # Without this the phase's demonstrable outcome is impossible: the agent
    # cannot label a citation "Aldercrest operating standard" versus giving a
    # source URL if the style is dropped on the way out of retrieval.
    def retriever(_query):
        return SimpleNamespace(found=True, clauses=[
            SimpleNamespace(chunk_id="02-BOND:4.4", doc="02-BOND",
                            clause_type="tax_rule", text="Top-slicing relief…",
                            aud="all", citation_style="cite_source"),
        ])

    out = retrieve_clause(retriever, "top-slicing relief")

    assert out["clauses"][0]["citation_style"] == "cite_source"
    assert out["clauses"][0]["aud"] == "all"


def test_a_retriever_that_supplies_no_style_reports_none():
    # The old clause-shaped retrievers carry no provenance; an explicit None is
    # the honest answer, never a guessed style.
    out = retrieve_clause(_found_retriever, "how do they claim?")
    assert out["clauses"][0]["citation_style"] is None
