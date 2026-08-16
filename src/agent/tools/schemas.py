"""The registry's tools as strict Anthropic tool definitions.

The definitions the model is given are *derived* from the callables the registry
dispatches to, so the two cannot drift. A hand-written schema list would be a
second source of truth, and the first parameter rename would separate them: the
model would call a tool with an argument the callable does not accept, and the
break would surface as a confusing runtime error instead of a loud one.

Two rules make the derivation trustworthy:

  * **The shape is read off the callable.** The console binds each tool's
    dependency with ``functools.partial`` — the record store, the retriever, the
    case sink — and a partial's signature omits what it has already bound. That
    is exactly the behaviour wanted: the store is not a parameter the model
    should ever be offered, and it disappears without anyone maintaining a list
    of things to hide.
  * **An unrepresentable signature raises.** A parameter with no type hint, a
    ``**kwargs``, or a type with no JSON-schema equivalent is a ``SchemaError``,
    never a guess. Guessing ``string`` hands the model a contract the callable
    may not honour, which is the same failure the derivation exists to prevent.

``strict`` with ``additionalProperties: false`` is the current API contract for
guaranteeing a tool's input validates exactly as declared.
"""

from __future__ import annotations

import inspect
from typing import Any, get_origin

from src.agent.tools.registry import Tool, ToolRegistry

# Only types with an unambiguous JSON-schema equivalent. Anything else is an
# error rather than a coercion — see the module docstring.
_JSON_TYPES: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class SchemaError(TypeError):
    """Raised when a registered callable cannot be expressed as a strict schema."""


def tool_definitions(registry: ToolRegistry) -> list[dict[str, Any]]:
    """Every registered tool as a definition, in registration order."""
    return [tool_definition(registry.get(name)) for name in registry.names()]


def tool_definition(tool: Tool) -> dict[str, Any]:
    """One tool as a strict Anthropic tool definition."""
    properties, required = _parameters(tool)
    return {
        "name": tool.name,
        "description": tool.description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


def _parameters(tool: Tool) -> tuple[dict[str, Any], list[str]]:
    """The model-facing parameters of ``tool``, and which of them are required."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in _signature(tool).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise SchemaError(
                f"tool {tool.name!r}: parameter {name!r} is variadic, which cannot "
                f"be expressed in a closed schema"
            )
        prop: dict[str, Any] = {"type": _json_type(tool, name, param)}
        description = tool.params.get(name)
        if description:
            prop["description"] = description
        properties[name] = prop
        if param.default is param.empty:
            required.append(name)
    return properties, required


def _signature(tool: Tool) -> inspect.Signature:
    """``tool.fn``'s signature, with string annotations resolved to real types.

    ``eval_str`` matters: the tool modules use ``from __future__ import
    annotations``, so without it every annotation arrives as the *string*
    ``"str"`` and nothing would ever match a JSON type.
    """
    try:
        return inspect.signature(tool.fn, eval_str=True)
    except (TypeError, ValueError, NameError) as exc:
        raise SchemaError(
            f"tool {tool.name!r} has no inspectable signature: {exc}") from exc


def _json_type(tool: Tool, name: str, param: inspect.Parameter) -> str:
    if param.annotation is param.empty:
        raise SchemaError(
            f"tool {tool.name!r}: parameter {name!r} has no type hint, and a guessed "
            f"type is a contract the callable may not honour"
        )
    # `list[dict[str, Any]]` and friends carry their container as the origin.
    origin = get_origin(param.annotation) or param.annotation
    json_type = _JSON_TYPES.get(origin)
    if json_type is None:
        raise SchemaError(
            f"tool {tool.name!r}: parameter {name!r} is annotated "
            f"{param.annotation!r}, which has no strict JSON-schema equivalent"
        )
    return json_type
