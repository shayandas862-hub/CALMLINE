"""v3 phase 4 · mock role login — extended in v4 phase 3 with an actor identity.

Three roles, a signed (not encrypted) session token — no passwords, no user
records. Role is enforced server-side by the guard; tampering or a wrong secret
is rejected.

**v4 phase 3 (D-CL-045).** The token proved *which role* was acting but not
*who*, so every back-office session was the same actor and "two distinct
approvers" could not be tested at all. It now carries a handler identity
alongside the role, inside the same signature. `07-RUNBOOK:4.3` expects
`maker_id` and `checker_id` recorded on the case; this is where they come from.

The payload is `role:actor`, so the actor format is a security control rather
than tidiness: an actor able to contain a separator could forge a different
role inside a validly-signed token.
"""

import pytest

from src.auth.roles import ROLES, AuthError, RoleSession, Session

SECRET = "dev-secret-not-real"


def test_there_are_exactly_three_roles():
    assert ROLES == frozenset({"front_office", "back_office", "ops"})


# ── the session carries role AND actor ───────────────────────────────────
def test_issue_and_verify_roundtrips_each_role():
    s = RoleSession(SECRET)
    for role in ROLES:
        assert s.verify(s.issue(role)).role == role


def test_a_verified_session_names_the_actor():
    s = RoleSession(SECRET)
    session = s.verify(s.issue("back_office", actor="reviewer_kim"))
    assert isinstance(session, Session)
    assert (session.role, session.actor) == ("back_office", "reviewer_kim")


def test_two_logins_on_one_role_can_be_two_distinct_actors():
    # The whole point of the change: without this, maker-checker and dual
    # authorisation are assertions about a single indistinguishable session.
    s = RoleSession(SECRET)
    first = s.verify(s.issue("back_office", actor="reviewer_kim"))
    second = s.verify(s.issue("back_office", actor="reviewer_sam"))
    assert first.role == second.role
    assert first.actor != second.actor


def test_an_omitted_actor_defaults_to_one_per_role():
    # Deterministic, and it collides on purpose: a caller who forgets to say
    # who is acting gets refused by the distinctness checks rather than
    # silently passing them.
    s = RoleSession(SECRET)
    assert s.verify(s.issue("back_office")).actor == "back_office_1"


# ── the actor format is a control, not a convention ──────────────────────
@pytest.mark.parametrize("bad", [
    "back_office:reviewer",     # a role separator — the forgery this prevents
    "reviewer.kim",             # the signature separator
    "ab",                       # too short
    "x" * 33,                   # too long
    "Reviewer Kim",             # spaces and case
    "",
])
def test_issue_rejects_an_actor_that_could_confuse_the_payload(bad):
    with pytest.raises(AuthError):
        RoleSession(SECRET).issue("back_office", actor=bad)


def test_an_actor_cannot_smuggle_a_second_role_into_the_payload():
    # If ``actor`` were unvalidated, "x:ops" would make the payload
    # "front_office:x:ops" and invite a parser into reading the wrong role.
    s = RoleSession(SECRET)
    with pytest.raises(AuthError):
        s.issue("front_office", actor="x:ops")


# ── unchanged guarantees ─────────────────────────────────────────────────
def test_issue_rejects_an_unknown_role():
    with pytest.raises(AuthError):
        RoleSession(SECRET).issue("admin")


def test_verify_rejects_a_tampered_token():
    s = RoleSession(SECRET)
    token = s.issue("front_office")
    tampered = "ops." + token.split(".", 1)[1]  # swap the role, keep the old signature
    with pytest.raises(AuthError):
        s.verify(tampered)


def test_verify_rejects_a_tampered_actor():
    s = RoleSession(SECRET)
    token = s.issue("back_office", actor="reviewer_kim")
    tampered = "back_office:reviewer_sam." + token.split(".", 1)[1]
    with pytest.raises(AuthError):
        s.verify(tampered)


def test_verify_rejects_a_malformed_token():
    s = RoleSession(SECRET)
    for bad in ("", "garbage", "front_office", "unknown.sig"):
        with pytest.raises(AuthError):
            s.verify(bad)


def test_verify_rejects_a_token_signed_with_a_different_secret():
    token = RoleSession(SECRET).issue("ops")
    with pytest.raises(AuthError):
        RoleSession("a-different-secret").verify(token)


def test_guard_allows_the_matching_role():
    s = RoleSession(SECRET)
    session = s.guard(s.issue("back_office"), {"back_office"})
    assert session.role == "back_office"


def test_guard_rejects_a_wrong_role_action_server_side():
    s = RoleSession(SECRET)
    # a back-office-only action refuses a front-office session
    with pytest.raises(AuthError):
        s.guard(s.issue("front_office"), {"back_office"})
    # a front-office-only action refuses an ops session
    with pytest.raises(AuthError):
        s.guard(s.issue("ops"), {"front_office"})
