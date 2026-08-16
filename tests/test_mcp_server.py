"""Phase 9 — the MCP socket.

The one retrieval entry point (`src/tools/policy_lookup.py`) exposed over the
Model Context Protocol, so any MCP client reaches the same cited-or-refuse
lookup the agent uses. Every test drives the server with a STUBBED lookup —
zero DB, zero network, zero live models. Async is driven with asyncio.run,
matching the suite convention (see tests/test_policy_lookup.py).
"""

import asyncio
import json

from mcp_server.server import build_server
from src.retrieval.assemble import CitedClause, RetrievedContext


def _ctx(*clauses):
    return RetrievedContext(clauses=list(clauses))


CLAUSE = CitedClause(
    chunk_id="TL-3.1",
    doc="term_life",
    clause_type="requirement",
    text="The death benefit is payable on receipt of a certified death certificate.",
    score=0.91,
)


def test_lists_policy_lookup_tool_with_query_schema():
    async def stub(query, *, top_k=8):
        return _ctx(CLAUSE)

    server = build_server(lookup=stub)
    tools = asyncio.run(server.list_tools())

    tool = next((t for t in tools if t.name == "policy_lookup"), None)
    assert tool is not None, "policy_lookup must be listed over the protocol"
    props = tool.inputSchema["properties"]
    assert props["query"]["type"] == "string"
    assert "query" in tool.inputSchema["required"]
    assert tool.description  # a client needs to know what the tool does


def test_call_returns_cited_clauses_over_the_protocol():
    async def stub(query, *, top_k=8):
        assert query == "what proof is needed for a death claim?"
        return _ctx(CLAUSE)

    server = build_server(lookup=stub)
    result = asyncio.run(
        server.call_tool("policy_lookup", {"query": "what proof is needed for a death claim?"})
    )
    payload = json.loads(result[0].text)

    assert payload["found"] is True
    # exactly the four citation fields — no internal retrieval score leaks out
    assert payload["clauses"] == [
        {
            "chunk_id": "TL-3.1",
            "doc": "term_life",
            "clause_type": "requirement",
            "text": "The death benefit is payable on receipt of a certified death certificate.",
        }
    ]


def test_not_found_is_signalled_not_errored():
    async def stub(query, *, top_k=8):
        return _ctx()  # empty → the retrieval-level refusal signal

    server = build_server(lookup=stub)
    result = asyncio.run(server.call_tool("policy_lookup", {"query": "does it cover my car?"}))
    payload = json.loads(result[0].text)

    assert payload["found"] is False
    assert payload["clauses"] == []


def test_top_k_is_forwarded_to_the_lookup():
    seen = {}

    async def stub(query, *, top_k=8):
        seen["top_k"] = top_k
        return _ctx(CLAUSE)

    server = build_server(lookup=stub)
    asyncio.run(server.call_tool("policy_lookup", {"query": "x", "top_k": 3}))
    assert seen["top_k"] == 3


def test_default_server_builds_without_env_or_live_calls():
    # build_server() with no injection wires the real policy_lookup as default;
    # constructing it must not touch the network or require secrets.
    server = build_server()
    tools = asyncio.run(server.list_tools())
    assert any(t.name == "policy_lookup" for t in tools)
