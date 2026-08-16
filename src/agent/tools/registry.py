"""The tool registry and dispatcher.

A ``Tool`` is a name + description + callable. The ``ToolRegistry`` holds them
by name and runs one by name with a dict of arguments (passed as keyword args).
This is the generic seam the orchestrator dispatches through, so adding a tool
never touches the calling code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


class ToolError(RuntimeError):
    """Raised for an unknown tool name or a duplicate registration."""


@dataclass(frozen=True)
class Tool:
    """One callable capability. ``fn`` is invoked with the dispatch args as kwargs.

    ``params`` maps a parameter name to what it means, for the model that has to
    fill it in. It lives here rather than in a schema table because a parallel
    table is a second source of truth: rename a parameter and the two drift.
    The parameter *shape* is never restated — it is read off ``fn`` itself
    (see ``src/agent/tools/schemas.py``).
    """

    name: str
    description: str
    fn: Callable[..., Any]
    params: Mapping[str, str] = field(default_factory=dict)


class ToolRegistry:
    """Holds tools by name and dispatches to them."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"a tool named {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"unknown tool {name!r}")
        return self._tools[name]

    def dispatch(self, name: str, args: dict[str, Any]) -> Any:
        """Run the named tool with ``args`` as keyword arguments."""
        return self.get(name).fn(**args)
