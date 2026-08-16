"""The agent's HTTP surface — gated, and honest about which path answered.

Split out of ``app.py`` at the 300-line rule, following ``gate_routes.py``.

Two things happen here that are easy to miss:

**The gate runs first, and it runs the same way it did in phase 3.** A question
naming a policy clears ``_unlock`` before anything else — the agent's tools read
the same book the disclosure endpoints read, so gating those and not this one
would refuse the record at the front door and hand it out at the side one
(D-CL-052). A question naming no policy stays open: retrieval touches no personal
data and `07-RUNBOOK:4.1` permits general product information before verification.

**The live path rebuilds the registry per request, with the record tools guarded.**
The app-level registry is built once and has no interaction to check against; the
guard needs the request's ``cn_ref``, which is session state. So the live agent
gets its own registry whose record tools refuse without a live verification —
the endpoint gate is the front door, and that is the lock on the cabinet.

The keyword path keeps the endpoint gate only. It cannot supply a
``verification_id`` because it is a keyword matcher, not a model, and adding a
second lock it has no key for would refuse every offline answer.

The response says which path answered and why. A keyword answer presented as the
agent would misrepresent the product in the one direction that flatters it.
"""

from __future__ import annotations

import time
from functools import partial
from itertools import count
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request

from src.agent.console_loop import run_console_agent
from src.agent.loop import AgentError
from src.agent.orchestrator import orchestrate
from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.record_tools import (
    get_transaction_history,
    get_valuation,
    lookup_policy_record,
)
from src.agent.tools.registry import Tool, ToolRegistry
from src.agent.reply import ConsoleReply
from src.agent.tools.verification import verified
from src.agent.trace import DecisionTrace, to_trace_record
from src.web.console.agent_select import select_agent
from src.web.console.keyword_reply import keyword_reply
from src.web.console.offline_agent import KeywordModel

_AUDIENCE = "front_office"


def register_agent_route(app: FastAPI, *, book: Any, session: Callable[..., Any],
                         registry: Any, gate: Any, unlock: Callable[..., str],
                         retriever: Callable[[str], Any], now: str,
                         traces: Any = None, conversations: Any = None,
                         clock: Optional[Callable[[], float]] = None,
                         api_key: Optional[str] = None, model: str = "",
                         client_factory: Optional[Callable[..., Any]] = None) -> None:
    """Mount ``POST /api/agent``.

    ``client_factory`` builds the Anthropic client and defaults to the real one.
    It is a seam so the live path can be driven by a stub in tests: rule 10 says
    zero live API calls in the suite, and a live path that is never exercised
    offline is a live path nobody has tested.

    ``traces`` records every answer, live or keyword. ``clock`` is the elapsed
    time source — injected, defaulting to ``time.monotonic``, because rule 8 has
    no exception for measurement and a duration nobody can control is a duration
    nobody can assert.
    """
    build_client = client_factory or _client
    tick = clock or time.monotonic
    counter = count(1)

    def _persist(reply: ConsoleReply, trace: DecisionTrace, *, cn_ref: Any,
                 role: str, mode: str, model_id: Optional[str],
                 elapsed_ms: Optional[int],
                 versions: Optional[dict[str, Any]] = None) -> None:
        """Record what just happened. One record type, whichever path answered.

        ``versions`` is the loop's provenance map. The bridge has always taken
        it and this route never passed it, so ``retrieved[].version`` was
        ``None`` on every trace stored — the versions existed one frame up the
        stack the whole time.
        """
        if traces is None:
            return
        traces.append(to_trace_record(
            trace, reply,
            trace_id=f"TR-{next(counter):06d}",
            ts=now,
            user_role=role,
            mode=mode,
            model_id=model_id,
            cn_ref=cn_ref or None,
            latency_ms={"generate": elapsed_ms} if elapsed_ms is not None else {},
            versions=versions,
        ))

    def _remember(cn_ref: Any, policy_no: Any, question: str,
                  reply: ConsoleReply) -> None:
        """Add this exchange to the conversation, so the next question sees it.

        Only when there is an interaction to hang it on: an answer given outside
        a `CN-` has no container that can expire, and a conversation that cannot
        end is one that outlives its permission (AD-CL-037).
        """
        if conversations is None or not cn_ref:
            return
        conversations.record(cn_ref, policy_no or "", question=question,
                             answer=reply.answer_text)

    @app.post("/api/agent")
    def agent(body: dict, request: Request) -> dict:
        """Ask the agent. A question **about a policy** is a disclosure."""
        current = session(request, {"front_office"})
        policy_no = body.get("policy_no")
        cn_ref = body.get("cn_ref")
        message = body.get("message", "")
        operative_date = body.get("operative_date") or now[:10]

        verification_id = ""
        if policy_no:
            verification_id = unlock(policy_no, cn_ref, current.actor)

        choice = select_agent(api_key=api_key, model=model)
        envelope = {
            "mode": choice.mode,
            "reason": choice.reason,
            "model": choice.model,
            "cn_ref": cn_ref,
            "verification_id": verification_id,
            "operative_date": operative_date,
        }

        if not choice.live:
            # The offline stand-in: one tool, dispatched by keyword — now
            # adapted to a ConsoleReply so both paths persist the same shape.
            outcome = orchestrate(message, registry,
                                  KeywordModel(policy_no=policy_no))
            reply, trace = keyword_reply(outcome)
            _persist(reply, trace, cn_ref=cn_ref, role=current.role,
                     mode="keyword", model_id=None, elapsed_ms=None)
            _remember(cn_ref, policy_no, message, reply)
            return {**envelope, **outcome, "reply": reply.model_dump()}

        started = tick()
        try:
            result = run_console_agent(
            message,
            client=build_client(api_key),
            registry=_guarded_registry(book, retriever, gate=gate,
                                       cn_ref=cn_ref or "",
                                       operative_date=operative_date),
            model=choice.model or model,
            operative_date=operative_date,
            audience=_AUDIENCE,
            verification_id=verification_id,
            policy_no=policy_no or "",
            # Scoped to (cn_ref, policy_no) by the store, so switching policy
            # inside one interaction starts a fresh thread (AD-CL-037).
            history=(conversations.messages(cn_ref or "", policy_no or "")
                     if conversations is not None else None),
        )
        except AgentError as exc:
            # The agent failing to finish is a bad answer, not a broken server.
            # Returning 500 here would render as "something went wrong" — the
            # opposite of the stance that a refusal is the product working.
            # It is still recorded: an answer that failed is exactly the kind
            # the ops screen exists to show.
            failed = ConsoleReply(
                answer_text="I couldn't complete that — please try a narrower "
                            "question, or check the record directly.",
                abstained=True,
                abstention_reason=f"the agent did not finish: {exc}",
                guardrail_events=[f"agent_error: {exc}"])
            _persist(failed, DecisionTrace(), cn_ref=cn_ref, role=current.role,
                     mode="live", model_id=choice.model or model,
                     elapsed_ms=_ms(started, tick()))
            return {**envelope, "reply": failed.model_dump(), "trace": []}

        _persist(result.reply, result.trace, cn_ref=cn_ref, role=current.role,
                 mode="live", model_id=choice.model or model,
                 elapsed_ms=_ms(started, tick()), versions=result.retrieved)
        _remember(cn_ref, policy_no, message, result.reply)
        return {**envelope,
                "reply": result.reply.model_dump(),
                "trace": result.trace.as_list()}


def _client(api_key: Optional[str]) -> Any:
    """The Anthropic client, imported here so the offline path never needs it."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def _ms(started: float, ended: float) -> int:
    """Elapsed milliseconds, never negative — a clock that went backwards is 0."""
    return max(0, round((ended - started) * 1000))


def _guarded_registry(book: Any, retriever: Callable[[str], Any], *, gate: Any,
                      cn_ref: str, operative_date: str) -> ToolRegistry:
    """This request's tools: the record ones refuse without a live verification.

    Built per request because the guard needs ``cn_ref``, and an interaction is
    a property of the request rather than of the app.

    ``operative_date`` is bound into the ledger tool rather than exposed as a
    parameter the model fills in. The date an answer is given as at is the
    server's to decide (rule 11), and a model free to choose it could answer a
    question about April with a ledger read at some other moment.
    """
    reg = ToolRegistry()
    reg.register(Tool(
        "lookup_policy_record",
        "Look up a policy: the holder, the policy detail, and its current value.",
        verified(partial(lookup_policy_record, book), gate=gate, cn_ref=cn_ref),
        params={"policy_no": "The policy number, e.g. LP-20419876",
                "verification_id": "The id of this caller's passed verification"}))
    reg.register(Tool(
        "get_transaction_history",
        "The ordered ledger for a policy: every movement and the balance after it.",
        verified(partial(get_transaction_history, book, as_at=operative_date),
                 gate=gate, cn_ref=cn_ref),
        params={"policy_no": "The policy number",
                "verification_id": "The id of this caller's passed verification"}))
    reg.register(Tool(
        "get_valuation",
        "What a policy was worth on a given date. Use for any question about the past.",
        verified(partial(get_valuation, book), gate=gate, cn_ref=cn_ref),
        params={"policy_no": "The policy number",
                "as_at": "The date to value at, YYYY-MM-DD",
                "verification_id": "The id of this caller's passed verification"}))
    reg.register(Tool(
        "retrieve_clause",
        "Search the insurer's rules. Returns clauses with their exact ids; cite them.",
        partial(retrieve_clause, retriever),
        params={"query": "What to look up in the rules",
                "product_code": "Optional: restrict to one product "
                                "(lifelong_protection, horizon_bond, retirement_account)",
                "operative_date": "The date the answer is given as at"}))
    return reg
