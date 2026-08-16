"""v4 phase 4 · Task 1 — Anthropic tool definitions derived from the registry.

The contract the model is given must be *derived* from the tools the registry
actually dispatches to, never written alongside them. A hand-maintained schema
list is a second source of truth, and the two drift the first time a parameter
is renamed — the model then calls a tool with an argument the callable does not
accept, and the failure surfaces as a confusing runtime error rather than a
loud one.

So the shape comes from ``inspect.signature`` on the registered callable. The
console binds each tool's dependency with ``functools.partial`` (the record
store, the retriever, the case sink), and a partial's signature omits what it
has already bound — which is exactly right: the model must never be offered the
record store as a parameter it could fill in.

The one thing a signature cannot carry is what a parameter *means*, so
descriptions travel on the ``Tool`` itself.
"""

from functools import partial
from typing import Any

import pytest

from src.agent.tools.case_tools import raise_case
from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.record_tools import get_transaction_history, lookup_policy_record
from src.agent.tools.registry import Tool, ToolRegistry
from src.agent.tools.schemas import SchemaError, tool_definition, tool_definitions


def _sink(request: dict[str, Any]) -> dict[str, Any]:
    return request


def _retriever(query: str) -> Any:
    return None


def _console_registry() -> ToolRegistry:
    """The four tools the console registers, bound the way the console binds them."""
    reg = ToolRegistry()
    reg.register(Tool("lookup_policy_record", "look up a policy",
                      partial(lookup_policy_record, object()),
                      params={"policy_no": "The policy number, e.g. LP-20419876"}))
    reg.register(Tool("get_transaction_history", "the ledger",
                      partial(get_transaction_history, object())))
    reg.register(Tool("retrieve_clause", "search the rules",
                      partial(retrieve_clause, _retriever),
                      params={"query": "What to look up in the rules"}))
    reg.register(Tool("raise_case", "open a case", partial(raise_case, _sink)))
    return reg


def _by_name(definitions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {d["name"]: d for d in definitions}


# ── the drift test: the registry is the only source ──────────────────────

def test_definitions_cover_exactly_the_registered_tools():
    # Arrange
    reg = _console_registry()

    # Act
    defs = tool_definitions(reg)

    # Assert
    assert [d["name"] for d in defs] == reg.names()


def test_a_tool_registered_later_appears_without_touching_the_schema_module():
    # Arrange — the drift this whole module exists to prevent
    def _run_totals(*, a: int) -> int:
        return a

    reg = _console_registry()
    reg.register(Tool("run_totals", "add two numbers", _run_totals,
                      params={"a": "a number"}))

    # Act
    defs = tool_definitions(reg)

    # Assert
    assert "run_totals" in _by_name(defs)


# ── the API contract shape ───────────────────────────────────────────────

def test_a_definition_matches_the_api_contract_shape():
    # Arrange
    tool = _console_registry().get("retrieve_clause")

    # Act
    definition = tool_definition(tool)

    # Assert
    assert definition["name"] == "retrieve_clause"
    assert definition["description"] == "search the rules"
    assert definition["input_schema"]["type"] == "object"
    assert definition["input_schema"]["properties"]["query"]["type"] == "string"


def test_a_definition_is_strict_and_closed():
    # A strict schema guarantees the tool_use input validates exactly; without
    # additionalProperties=false the model may invent an argument.
    # Arrange
    reg = _console_registry()

    # Act
    defs = tool_definitions(reg)

    # Assert
    for definition in defs:
        assert definition["strict"] is True, definition["name"]
        assert definition["input_schema"]["additionalProperties"] is False, definition["name"]


# ── the bound dependency must never reach the model ──────────────────────

def test_the_bound_dependency_is_never_a_model_facing_parameter():
    # The record store is bound with functools.partial at registration. Offering
    # it to the model would be both meaningless and a way to smuggle in a store.
    # Arrange
    tool = _console_registry().get("lookup_policy_record")

    # Act
    definition = tool_definition(tool)

    # Assert
    assert "store" not in definition["input_schema"]["properties"]
    assert list(definition["input_schema"]["properties"]) == ["policy_no"]


# ── required-ness comes from the signature's defaults ────────────────────

def test_required_omits_parameters_that_have_defaults():
    # raise_case takes priority="medium" — a default means the model may omit it.
    # Arrange
    tool = _console_registry().get("raise_case")

    # Act
    schema = tool_definition(tool)["input_schema"]

    # Assert
    assert set(schema["properties"]) == {"policy_no", "request", "priority"}
    assert set(schema["required"]) == {"policy_no", "request"}


# ── descriptions travel with the tool, not a parallel table ──────────────

def test_parameter_descriptions_travel_from_the_registered_tool():
    # Arrange
    tool = _console_registry().get("retrieve_clause")

    # Act
    definition = tool_definition(tool)

    # Assert
    assert definition["input_schema"]["properties"]["query"]["description"] == (
        "What to look up in the rules")


def test_a_parameter_without_a_description_still_yields_a_valid_property():
    # get_transaction_history is registered with no params mapping at all.
    # Arrange
    tool = _console_registry().get("get_transaction_history")

    # Act
    prop = tool_definition(tool)["input_schema"]["properties"]["policy_no"]

    # Assert
    assert prop["type"] == "string"
    assert "description" not in prop


# ── unrepresentable signatures fail loudly, never silently ───────────────

def test_a_parameter_with_no_type_hint_fails_loudly():
    # Guessing "string" for an unannotated parameter would hand the model a
    # contract the callable does not honour.
    # Arrange
    tool = Tool("untyped", "d", lambda *, a: a)

    # Act / Assert
    with pytest.raises(SchemaError, match="a"):
        tool_definition(tool)


def test_a_variadic_parameter_fails_loudly():
    # **kwargs cannot be expressed in a closed schema.
    # Arrange
    tool = Tool("variadic", "d", lambda **kw: kw)

    # Act / Assert
    with pytest.raises(SchemaError):
        tool_definition(tool)


def test_an_unsupported_annotation_fails_loudly():
    # Arrange
    def _fn(*, when: complex) -> None: ...
    tool = Tool("odd", "d", _fn)

    # Act / Assert
    with pytest.raises(SchemaError):
        tool_definition(tool)


def test_the_supported_scalar_types_map_to_json_schema_types():
    # Arrange
    def _fn(*, name: str, count: int, ratio: float, ok: bool) -> None: ...
    tool = Tool("scalars", "d", _fn)

    # Act
    props = tool_definition(tool)["input_schema"]["properties"]

    # Assert
    assert [props[k]["type"] for k in ("name", "count", "ratio", "ok")] == [
        "string", "integer", "number", "boolean"]
