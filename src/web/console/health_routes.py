"""`GET /healthz` — the one endpoint that answers when everything else cannot.

Split out of `app.py` under the 300-line rule, the same way `agent_routes.py`
and `gate_routes.py` were before it.

Three components, each **derived by doing the thing** rather than asserted: the
store is counted, the corpus is counted, and configuration reports whether a
check actually ran. A hard-coded ``"store": "ok"`` is worse than no health check
at all, because somebody believes it.

**It answers 200 even when a component is down**, and puts the truth in the body.
A health check that 500s tells the platform to restart a service at the exact
moment a human wants to look at it, and one behind a login cannot be read by the
platform at all. The status code says *the service is answering*; the body says
*what is wrong*.
"""

from __future__ import annotations

from typing import Any, Optional

_UNCHECKED = "not checked — development boots without validating (D-CL-053)"


def _store_state(book: Any) -> dict[str, Any]:
    """Count the policies. Reading the store IS the check."""
    try:
        return {"ok": True, "policies": len(book.list_policies())}
    except Exception as exc:  # a store that cannot be read is the thing we report
        return {"ok": False, "policies": None, "detail": f"{type(exc).__name__}: {exc}"}


def _config_state(config_ok: Optional[bool]) -> dict[str, Any]:
    """Tri-state, because *unknown* and *broken* are different answers.

    ``None`` is development, where nothing is validated on purpose. Reporting
    that as ``ok`` would be claiming a check that never ran.
    """
    if config_ok is None:
        return {"ok": None, "detail": _UNCHECKED}
    if config_ok:
        return {"ok": True, "detail": "every required variable present at boot"}
    return {"ok": False, "detail": "required configuration missing or empty"}


def health_report(*, book: Any, corpus_clauses: int,
                  config_ok: Optional[bool] = None) -> dict[str, Any]:
    """The three component states, and the worst of them as the headline.

    ``status`` is the **worst** component, never an average: a service with two
    healthy parts and one dead one is not two-thirds well.
    """
    components = {
        "config": _config_state(config_ok),
        "store": _store_state(book),
        "corpus": {"ok": corpus_clauses > 0, "clauses": corpus_clauses},
    }
    degraded = any(state["ok"] is False for state in components.values())
    return {"status": "degraded" if degraded else "ok", "components": components}


def register_health_route(app: Any, *, book: Any, corpus_clauses: int,
                          config_ok: Optional[bool] = None) -> None:
    """Mount `GET /healthz`. Never rate-limited, never behind the session."""

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return health_report(book=book, corpus_clauses=corpus_clauses,
                             config_ok=config_ok)
