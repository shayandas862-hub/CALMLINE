"""The orchestrator — route a request to the right tool.

The model (behind the ``ModelClient`` interface — a deterministic stand-in now,
a real LLM at the gate) chooses which tool to call for a request; the
orchestrator dispatches that choice through the registry and returns the result
alongside the tool it used (so the UI can show "used: retrieve_clause").

Scope note: this is single-tool selection, the agreed v3-phase-2 scope. The
full multi-step agentic loop and per-provider tool-calling adapters are a
separate, parked piece of work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.agent.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ToolCall:
    """A tool choice: which tool, and the arguments to run it with."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


class ModelClient(Protocol):
    """The brain seam: given a request and the available tool names, choose one."""

    def select(self, request: str, tool_names: list[str]) -> ToolCall: ...


def orchestrate(request: str, registry: ToolRegistry, model: ModelClient) -> dict[str, Any]:
    """Have the model pick a tool for ``request`` and dispatch it."""
    call = model.select(request, registry.names())
    result = registry.dispatch(call.name, call.args)
    return {"tool": call.name, "args": call.args, "result": result}
