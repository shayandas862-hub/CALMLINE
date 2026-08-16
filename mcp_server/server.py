# MIT License — Copyright (c) 2026 Shayan Das
"""The MCP socket — CalmLine's policy lookup, reachable over the Model Context Protocol.

A thin FastMCP wrapper around `src/tools/policy_lookup.py`: the SAME cited-or-refuse
retrieval the agent calls (Phase 3), now callable by any external MCP client over
stdio. It adds no retrieval logic of its own — it serializes the typed
`RetrievedContext` to a small JSON payload (a `found` flag + the cited clauses) so a
client can tell "no relevant clause" (a retrieval-level refusal signal) apart from an
error.

Run it for a real client:  python -m mcp_server.server   (stdio transport)
Live use needs the OpenAI + Cohere keys and a seeded Supabase — the operator gate.
Building and listing the tool needs neither, so this is unit-tested with a stub.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from mcp.server.fastmcp import FastMCP

from src.retrieval.assemble import RetrievedContext
from src.tools.policy_lookup import policy_lookup as _default_lookup

# The lookup seam: real `policy_lookup` in production, a stub in tests.
LookupFn = Callable[..., Awaitable[RetrievedContext]]

_INSTRUCTIONS = (
    "CalmLine policy retrieval (synthetic demo data). Call policy_lookup with a "
    "plain-language question about the insurance policies; it returns cited clauses "
    "to quote, or found=false when nothing clears the relevance threshold — in which "
    "case do not answer from general knowledge."
)

_TOOL_DESCRIPTION = (
    "Look up CalmLine policy clauses for a plain-language question. Returns cited "
    "clauses (chunk_id, doc, clause_type, text) to quote, or found=false when "
    "nothing is relevant enough — a refusal signal; do not answer from general "
    "knowledge. Synthetic demonstration data only."
)


def _serialize(ctx: RetrievedContext) -> dict:
    """Wire payload: the found signal + citation fields only (the internal score stays out)."""
    return {
        "found": ctx.found,
        "clauses": [
            {
                "chunk_id": c.chunk_id,
                "doc": c.doc,
                "clause_type": c.clause_type,
                "text": c.text,
            }
            for c in ctx.clauses
        ],
    }


def build_server(lookup: LookupFn | None = None) -> FastMCP:
    """Build the MCP server.

    `lookup` defaults to the real `policy_lookup` (which composes the vendored
    hybrid-search → rerank → assemble pipeline); tests inject a stub so no DB,
    network, or live model is touched. Constructing the server and listing the
    tool never invoke `lookup` — it runs only when a client calls the tool.
    """
    do_lookup = lookup or _default_lookup
    server = FastMCP("calmline-policy", instructions=_INSTRUCTIONS)

    @server.tool(name="policy_lookup", description=_TOOL_DESCRIPTION)
    async def policy_lookup_tool(query: str, top_k: int = 8) -> dict:
        ctx = await do_lookup(query, top_k=top_k)
        return _serialize(ctx)

    return server


def main() -> None:  # pragma: no cover — the live stdio entry point (needs live credentials)
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
