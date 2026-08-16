"""v3 phase 2 · Task 1 — the tool registry + dispatcher.

The registry holds the agent's tools by name and runs one by name with a dict
of args. It's the generic seam the orchestrator dispatches through.
"""

import pytest

from src.agent.tools.registry import Tool, ToolError, ToolRegistry


def _add(a, b):
    return a + b


def test_register_and_dispatch_runs_the_tool():
    reg = ToolRegistry()
    reg.register(Tool(name="add", description="add two numbers", fn=_add))
    assert reg.dispatch("add", {"a": 2, "b": 3}) == 5


def test_dispatch_passes_args_through_as_kwargs():
    reg = ToolRegistry()
    reg.register(Tool(name="echo", description="echo", fn=lambda **kw: kw))
    assert reg.dispatch("echo", {"x": 1, "y": "z"}) == {"x": 1, "y": "z"}


def test_dispatch_unknown_tool_raises_toolerror():
    reg = ToolRegistry()
    with pytest.raises(ToolError):
        reg.dispatch("nope", {})


def test_registering_a_duplicate_name_raises():
    reg = ToolRegistry()
    reg.register(Tool(name="add", description="d", fn=_add))
    with pytest.raises(ToolError):
        reg.register(Tool(name="add", description="d2", fn=_add))


def test_names_lists_registered_tools_and_has_checks_membership():
    reg = ToolRegistry()
    reg.register(Tool(name="add", description="d", fn=_add))
    reg.register(Tool(name="echo", description="d", fn=lambda **kw: kw))
    assert set(reg.names()) == {"add", "echo"}
    assert reg.has("add") is True
    assert reg.has("missing") is False
