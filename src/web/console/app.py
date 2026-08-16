"""The console FastAPI app — wires the phases-1–4 backend into role-guarded
endpoints, all offline. A NEW app beside the old demo; nothing prior is touched.

Money still only moves through the human-gated approve endpoint (`approve_case`);
no endpoint lets a tool write the ledger. Every read/write endpoint enforces the
role server-side via the phase-4 guard.
"""

from __future__ import annotations

from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.agent.tools.case_tools import raise_case
from src.agent.tools.knowledge_tool import retrieve_clause
from src.agent.tools.record_tools import get_transaction_history, lookup_policy_record
from src.agent.tools.registry import Tool, ToolRegistry
from src.auth.roles import AuthError, RoleSession, Session
from src.identity.events import GateEventLog
from src.identity.gate import VerificationGate
from src.records.interactions import InteractionStore
from src.casework.queue import CaseQueue
from src.corpus.facts import corpus_facts
from src.opsview.lenses import ops_snapshot
from src.records.models import format_gbp
from src.records.seed import build_seed_book
from src.agent.conversation import ConversationStore
from src.traces.store import InMemoryTraceStore
from src.web.console.demo_cases import seed_demo_cases
from src.web.console.agent_routes import register_agent_route
from src.web.console.case_routes import register_case_routes
from src.web.console.gate_routes import build_unlock, register_gate_routes
from src.web.console.health_routes import register_health_route
from src.web.console.offline_agent import build_offline_retriever, searchable_chunks
from src.web.console.policy_routes import register_policy_routes
from src.web.console.ratelimit import RateLimiter, install_rate_limit

_STATIC = Path(__file__).resolve().parent / "static"
_COOKIE = "calmline_session"
_DEMO_NOW = "2026-07-13T09:00:00"  # a fixed Monday morning → deterministic SLA
_MODE_OFFLINE = "offline — deterministic stand-in, no live keys"
_MODE_LIVE = "live agent — {model}"


def create_console_app(*, book: Any = None, secret: str = "dev-session-secret",
                       now: str = _DEMO_NOW, seed_demo: bool = False,
                       queue_cases: Any = (),
                       api_key: Optional[str] = None, model: str = "",
                       client_factory: Any = None, traces: Any = None,
                       conversations: Any = None, clock: Any = None,
                       rate_limit: Optional[RateLimiter] = None,
                       trusted_proxy_hops: int = 0,
                       config_ok: Optional[bool] = None) -> FastAPI:
    """Build the console.

    ``api_key`` is **injected**, never read from configuration here: it selects
    the live agent, and `ANTHROPIC_API_KEY` sits in `config.REQUIRED`, so
    loading config to find it would kill an offline console on a different
    missing variable (D-CL-053 contradiction 4). Left unset — as the whole test
    suite leaves it — the console answers via the keyword fallback and says so,
    which is also why the suite makes zero network calls.

    ``traces`` is where every answer is recorded; ``clock`` is the elapsed-time
    source latency is measured from. Both are injected for the same reason the
    key is: a test that cannot supply the store cannot assert what was stored,
    and one that cannot control the clock cannot assert a duration.

    ``rate_limit`` is injected for that reason and one more: the caps are a
    **deployment** decision, not a property of the console. `run_console.py`
    supplies one in production (AD-CL-008's spend rails); a local console and
    the suite run without, which is why 1,200-odd tests do not each have to
    reason about an allowance they never meant to spend.
    """
    book = book or build_seed_book()
    traces = traces if traces is not None else InMemoryTraceStore()
    conversations = (conversations if conversations is not None
                     else ConversationStore())
    queue = CaseQueue()
    sessions = RoleSession(secret)
    # Bound to the front office, the audience every retrieval surface here
    # serves. `aud` is bound at build time precisely so a query cannot
    # widen it (rule 11); an unbound retriever indexes ops material too.
    retriever = build_offline_retriever(aud="front_office")
    # The retrievable corpus, counted from the same function the retriever
    # indexes: KB chunks minus the sample records, which are never in the index.
    corpus_clauses = len(searchable_chunks())

    registry = ToolRegistry()
    registry.register(Tool("lookup_policy_record", "look up a policy", partial(lookup_policy_record, book)))
    registry.register(Tool("get_transaction_history", "the ledger",
                           partial(get_transaction_history, book, as_at=now[:10])))
    registry.register(Tool("retrieve_clause", "search the rules", partial(retrieve_clause, retriever)))
    registry.register(Tool("raise_case", "open a case", partial(raise_case, queue.open)))

    # The dataset's live work first, under its own references (v4.5 phase 5):
    # the world's queue rows arrive as ready-made cases and are admitted, not
    # re-minted — the same cases sit in the database after a load.
    for case in queue_cases:
        queue.admit(case)

    if seed_demo:  # populate the ops (and back-office) screens for the offline demo
        seed_demo_cases(queue, book, now)

    interactions = InteractionStore()
    gate = VerificationGate()
    events = GateEventLog()

    app = FastAPI(title="CalmLine Console")
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    if rate_limit is not None:
        install_rate_limit(app, rate_limit, trusted_proxy_hops=trusted_proxy_hops)
    # Exposed so a caller — and the suite — can ask "did anything leak?".
    app.state.gate_events = events
    app.state.gate = gate

    def _session(request: Request, allowed: set[str]) -> Session:
        """The signed session behind this request, or 401/403.

        Returns the whole session — role *and* actor — because approval needs
        to know who is acting, not only in what capacity (D-CL-045). Neither is
        ever read from the request body.
        """
        token = request.cookies.get(_COOKIE)
        if not token:
            raise HTTPException(status_code=401, detail="not logged in")
        try:
            return sessions.guard(token, allowed)
        except AuthError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    register_health_route(app, book=book, corpus_clauses=corpus_clauses,
                          config_ok=config_ok)

    _unlock = build_unlock(gate, events, now)
    register_gate_routes(app, book=book, session=_session,
                         interactions=interactions, gate=gate, events=events,
                         now=now)

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.post("/api/login")
    def login(body: dict, response: Response) -> dict:
        try:
            token = sessions.issue(body.get("role"), actor=body.get("actor"))
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        response.set_cookie(_COOKIE, token, httponly=True, samesite="lax")
        return {"role": body.get("role"), "actor": sessions.verify(token).actor}

    # The three disclosure endpoints live in policy_routes.py — split at the
    # 300-line rule. Each is gated identically: role first, then an in-scope
    # passed verification, then the data (D-CL-044).
    register_policy_routes(app, book=book, session=_session, unlock=_unlock,
                           now=now)

    # `/api/agent` lives in agent_routes.py — split at the 300-line rule. It
    # keeps the phase-3 gate (D-CL-052) and adds the live path behind it.
    # A front-office-scoped retriever, NOT the app-wide one: the agent answers
    # front-office questions, and `aud` is bound at build time precisely so a
    # query cannot widen it. The app-wide retriever has no audience bound.
    register_agent_route(app, book=book, session=_session, registry=registry,
                         gate=gate, unlock=_unlock, now=now,
                         retriever=retriever, traces=traces, clock=clock,
                         conversations=conversations,
                         api_key=api_key, model=model,
                         client_factory=client_factory)

    # The case endpoints live in case_routes.py — split at the 300-line rule.
    # Approval remains the only path that moves money.
    register_case_routes(app, book=book, session=_session, unlock=_unlock,
                         queue=queue, now=now)

    @app.get("/api/ops")
    def ops(request: Request, model_id: Optional[str] = None) -> dict:
        """The board chamber: is the AI behaving?

        ``model_id`` slices every lens at once. An operator swaps models to
        compare them on the same questions, and a board filtered in one lens but
        not another is worse than one not filtered at all — only half of it
        would be wrong (D-CL-061).
        """
        _session(request, {"ops"})
        facts = corpus_facts(searchable_chunks())
        snap = ops_snapshot(book, queue.all(), now, traces=traces,
                            gate_events=events,
                            tool_names=registry.names(),
                            model_id=model_id,
                            mode=(_MODE_LIVE.format(model=model)
                                  if api_key else _MODE_OFFLINE),
                            **facts)
        # format money at the edge; the lens keeps exact integer pence.
        snap["operations"]["funds_under_admin"] = format_gbp(
            snap["operations"]["funds_under_admin_pence"])
        return snap

    return app
