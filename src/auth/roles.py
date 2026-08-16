"""Roles, signed session tokens, and the server-side guard.

The token is ``"<role>:<actor>.<hmac>"`` — the role and the handler identity in
the clear, signed with a secret so neither can be forged or swapped. This is a
mock login for a synthetic demo: there are no passwords and no user records.

**What changed in v4 phase 3 (D-CL-045).** The token used to prove *which role*
was acting but not *who*, so every back-office session was literally the same
actor. That made maker-checker (`07-RUNBOOK:4.3`: the maker cannot be the
checker) and dual authorisation (`05-OPS:14`: two approvers above £250,000)
impossible to enforce and worse, impossible to test — the assertions would have
passed or failed for reasons unrelated to the control. The session now carries a
handler identity inside the same signature.

The actor format is a **security control**, not a naming convention: the payload
is separated by ``:``, so an actor allowed to contain one could smuggle a second
role into a validly-signed token.

The secret is injected (the web layer supplies it); nothing here touches config.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Iterable, Optional

ROLES = frozenset({"front_office", "back_office", "ops"})

# Lowercase, no separators, no spaces — see the module docstring.
ACTOR_RE = re.compile(r"^[a-z0-9_-]{3,32}$")


class AuthError(RuntimeError):
    """Raised for an unknown role or actor, or a malformed / tampered token."""


@dataclass(frozen=True)
class Session:
    """Who is acting, and in what capacity.

    ``role`` decides what is permitted; ``actor`` decides whether two approvals
    came from two different people. Both come from the signed token and never
    from a request body (rule 11).
    """

    role: str
    actor: str


class RoleSession:
    """Issues and verifies role-and-actor tokens signed with ``secret``."""

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("a session secret is required")
        self._secret = secret.encode("utf-8")

    def _sign(self, payload: str) -> str:
        return hmac.new(self._secret, payload.encode("utf-8"),
                        hashlib.sha256).hexdigest()

    def issue(self, role: str, *, actor: Optional[str] = None) -> str:
        """Return a signed token for ``role``, acting as ``actor``.

        An omitted actor defaults to ``"<role>_1"``. That is deliberate and it
        collides on purpose: a caller who never says who is acting gets refused
        by the distinctness checks rather than quietly satisfying them.
        """
        if role not in ROLES:
            raise AuthError(f"unknown role {role!r}")
        actor = actor if actor is not None else f"{role}_1"
        if not ACTOR_RE.match(actor):
            raise AuthError(
                f"actor {actor!r} must be 3-32 chars of a-z, 0-9, underscore "
                f"or hyphen (no separators)")
        payload = f"{role}:{actor}"
        return f"{payload}.{self._sign(payload)}"

    def verify(self, token: str) -> Session:
        """Return the session a token carries, or raise ``AuthError``."""
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            raise AuthError("malformed session token")
        payload, signature = parts
        if not hmac.compare_digest(signature, self._sign(payload)):
            raise AuthError("bad session signature")
        # Only parsed once the signature is known good, so a forged payload
        # never reaches this.
        role, sep, actor = payload.partition(":")
        if not sep or role not in ROLES or not ACTOR_RE.match(actor):
            raise AuthError("malformed session payload")
        return Session(role=role, actor=actor)

    def guard(self, token: str, allowed: Iterable[str]) -> Session:
        """Verify the token and require its role to be in ``allowed``."""
        session = self.verify(token)
        if session.role not in set(allowed):
            raise AuthError(
                f"role {session.role!r} is not permitted for this action")
        return session
