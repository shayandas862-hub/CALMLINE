"""The console's tool-calling loop — N tools from the registry, one ConsoleReply.

Split out of ``src/agent/loop.py`` at the 300-line rule, and it earned its own
file: the eval harness's loop answers "what is the verdict on this case" with
one retrieval tool, and this one answers "what should I tell this caller" with
whatever the registry holds. They share an SDK contract and an error type, not
a job.

What the model decides and what the loop decides are deliberately separated.
The model writes the answer and chooses the tools; the loop states what actually
happened — which tools were dispatched, and which of them refused. Neither of
those is read back out of the model's output, so a model cannot under-report a
tool it used or quietly drop a refusal it was given.

A refused tool is fed back as an error the model must handle by abstaining. It
is never swallowed into a silent gap, because a gap is exactly what a model
fills from memory.

``client`` and ``registry`` are injected; the whole loop unit-tests with zero
network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import ValidationError

from src.agent.loop import _MAX_STEPS, _MAX_TOKENS, AgentError, _final_text
from src.agent.prompts import console_prompt
from src.agent.provenance import retrieved_provenance, stated_provenance
from src.agent.reply import ConsoleReply
from src.agent.tools.schemas import tool_definitions
from src.agent.trace import DecisionTrace

# Adaptive thinking and `output_config.effort` arrived with the 4.6 generation.
# Earlier models reject them outright — verified against the API, which answers
# a Haiku 4.5 request with `400 adaptive thinking is not supported on this
# model`. Holding the models known to accept them, rather than pattern-matching
# an id, means an unrecognised id gets the conservative shape that every model
# accepts instead of a request that cannot succeed.
_ADAPTIVE_THINKING = frozenset({
    "claude-fable-5", "claude-mythos-5",
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
    "claude-sonnet-5", "claude-sonnet-4-6",
})


@dataclass
class ConsoleResult:
    """What the console gets back: the reply, and how it was reached.

    The trace is RETURNED, not stored — persistence is phase 5's job.

    ``retrieved`` is the loop's chunk id → provenance map. It is handed back
    because the route is what writes the trace record, and until it had this the
    stored ``retrieved[].version`` was ``None`` on every trace the console ever
    wrote — the loop knew the versions and had nowhere to put them.
    """

    reply: ConsoleReply
    trace: DecisionTrace
    retrieved: dict[str, dict[str, Any]] = field(default_factory=dict)


def run_console_agent(
    message: str,
    *,
    client: Any,
    registry: Any,
    model: str,
    operative_date: str,
    audience: str,
    verification_id: str = "",
    policy_no: str = "",
    history: Optional[list[dict[str, Any]]] = None,
    max_steps: int = _MAX_STEPS,
) -> ConsoleResult:
    """Answer a handler's question using the registry's tools.

    ``model`` is required and has no default: the id belongs in configuration,
    not in this file. ``operative_date`` and ``audience`` are stated in the
    system prompt because neither may be guessed.

    ``verification_id`` is the record the endpoint's gate already produced. The
    record tools require it and the model cannot invent one, so it is handed
    over as request context — without it the agent can see the record tools but
    can never satisfy them, which is a refusal loop rather than a safeguard.
    (Binding it into the tools, as ``cn_ref`` already is, would be the tidier
    design and is worth revisiting: the guard checks ``(cn_ref, policy_no)``
    first, so a server-bound id would carry the same guarantee with one less
    thing in the model's context.)
    """
    trace = DecisionTrace()
    dispatched: list[str] = []
    guardrails: list[str] = []
    # chunk id -> what retrieval said about it. The keys police grounding; the
    # values are backfilled onto the reply's citations (D-CL-061).
    retrieved: dict[str, dict[str, Any]] = {}
    tools = tool_definitions(registry)
    system = console_prompt(operative_date=operative_date, audience=audience)
    output_format = {"type": "json_schema", "schema": ConsoleReply.model_json_schema()}
    shape = request_shape(model, output_format)
    # Earlier turns of THIS conversation first, then the new question. The
    # history is scoped to `(cn_ref, policy_no)` by its store (AD-CL-037), so a
    # policy switch inside one interaction starts a fresh thread rather than
    # carrying the previous policy's record into it.
    messages: list[dict[str, Any]] = [
        *(history or []),
        {"role": "user", "content": _with_context(message, verification_id,
                                                 policy_no)}]

    for _ in range(max_steps):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=_MAX_TOKENS,
                system=system,
                tools=tools,
                messages=messages,
                **shape,
            )
        except Exception as exc:  # any SDK/transport error → typed failure
            raise AgentError(f"agent API call failed: {exc}") from exc

        if getattr(response, "stop_reason", None) == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [
                _run_tool(registry, block, trace, dispatched, guardrails,
                          retrieved)
                for block in response.content
                if getattr(block, "type", None) == "tool_use"
            ]})
            continue

        reply = _parse_reply(_final_text(response))
        _check_grounding(reply, dispatched, retrieved)
        trace.verdict("abstained" if reply.abstained else "answered")
        # The model writes the answer; the loop states the facts about what
        # happened. A model cannot under-report a tool it used or a refusal it
        # was given, because neither is taken from its output.
        return ConsoleResult(
            reply=reply.model_copy(update={
                "tools_used": _unique(dispatched),
                "guardrail_events": [*guardrails, *reply.guardrail_events],
                "citations": stated_provenance(reply.citations, retrieved),
            }),
            trace=trace,
            retrieved=dict(retrieved),
        )

    raise AgentError("agent exceeded the step limit without producing a reply")


def _with_context(message: str, verification_id: str, policy_no: str) -> str:
    """The handler's question, plus what the screen already knows.

    Both facts are things the console holds and the model cannot infer. A
    handler types "this policy" because the record is in front of them; without
    the number the agent has a pronoun with no referent, and the honest response
    to that is the refusal it actually gave when this was missing. The
    verification is the same story — the record tools require an id the model
    cannot invent, so withholding it makes a refusal loop, not a safeguard.
    """
    lines = []
    if policy_no:
        lines.append(f"policy on screen: {policy_no} "
                     f'(the caller\'s question refers to this policy)')
    if verification_id:
        lines.append(f"verification_id for this caller: {verification_id} "
                     f"(pass it to any record tool that asks for one)")
    if not lines:
        return message
    return "\n".join(lines) + f"\n\n{message}"


def request_shape(model: str, output_format: dict[str, Any]) -> dict[str, Any]:
    """The thinking/effort parameters ``model`` will actually accept.

    Structured output is asked for either way — every current model supports it.
    What differs is the reasoning controls: a pre-4.6 model rejects both
    `thinking: adaptive` and `output_config.effort`, so it is sent neither and
    answers without them.
    """
    if model in _ADAPTIVE_THINKING:
        return {"thinking": {"type": "adaptive"},
                "output_config": {"effort": "high", "format": output_format}}
    return {"output_config": {"format": output_format}}


def _check_grounding(reply: ConsoleReply, dispatched: list[str],
                     retrieved: set[str]) -> None:
    """An answer rests on tools that ran, and cites only clauses really returned.

    This lives here rather than on ``ConsoleReply`` because only the loop knows
    what happened: the model's own account of which tools it used is exactly the
    thing that must not be trusted.

    Two checks, and the second is the one that matters. Requiring a *citation*
    would be wrong — a ledger figure has no clause behind it, and demanding one
    would push the agent into fabricating a reference for a number that came
    from the system of record. Requiring that every citation it **does** make
    was actually returned by retrieval catches the real failure: a plausible
    clause id the model produced from memory.
    """
    if reply.abstained:
        return
    if not dispatched:
        raise AgentError(
            "the agent answered without using any tool — every claim must come "
            "from the record or the rules, never from memory")
    invented = [c.chunk_id for c in reply.citations if c.chunk_id not in retrieved]
    if invented:
        raise AgentError(
            f"the agent cited {', '.join(invented)}, which retrieval did not "
            f"return — a citation nobody can follow is a fabricated one")


def _run_tool(registry: Any, block: Any, trace: DecisionTrace,
              dispatched: list[str], guardrails: list[str],
              retrieved: set[str]) -> dict[str, Any]:
    """Dispatch one tool call, recording it — refusal included — in the trace."""
    args = dict(getattr(block, "input", None) or {})
    trace.tool_call(block.name, args)
    dispatched.append(block.name)
    try:
        result = registry.dispatch(block.name, args)
    except Exception as exc:
        # A refused tool is fed back as an error the model must handle by
        # abstaining, never swallowed into a gap it might fill from memory.
        guardrails.append(f"{block.name} refused: {exc}")
        trace.tool_result(block.name, f"refused: {exc}")
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"REFUSED: {exc}", "is_error": True}
    found = retrieved_provenance(result)
    if found:
        retrieved.update(found)
    trace.tool_result(block.name, _summarise_result(result),
                      refs=None if found is None else list(found),
                      ranked=_ranking(result))
    return {"type": "tool_result", "tool_use_id": block.id,
            "content": json.dumps(result, default=str)}


def _parse_reply(text: str) -> ConsoleReply:
    try:
        return ConsoleReply(**json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AgentError(f"agent produced a malformed console reply: {exc}") from exc


def _ranking(result: Any) -> Optional[list[dict[str, Any]]]:
    """Where this one call placed each clause — the searcher's own order.

    Rank is the position in the list retrieval returned, 1-based. It is taken
    from the order rather than recomputed from the score, because the order is
    what retrieval actually decided: filter-then-search, then MMR, which can
    place a lower-scoring chunk above a higher one on purpose.

    ``None`` for a result that is not a retrieval, matching
    ``retrieved_provenance`` — a valuation has no clauses to rank.
    """
    if not isinstance(result, dict) or "clauses" not in result:
        return None
    return [{"chunk_id": c.get("chunk_id", ""), "rank": position,
             "score": c.get("score")}
            for position, c in enumerate(result["clauses"], start=1)]


def _summarise_result(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result)[:80]
    if "clauses" in result:
        clauses = result["clauses"]
        return (f"{len(clauses)} clause(s); top {clauses[0]['chunk_id']}"
                if clauses else "nothing found")
    return "found" if result.get("found") else "not found"


def _unique(names: list[str]) -> list[str]:
    """De-duplicated, in the order first used."""
    return list(dict.fromkeys(names))
