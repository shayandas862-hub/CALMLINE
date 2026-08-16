"""v4 phase 3 · task 5 — the gate wired into the console (tick model, D-CL-114).

The page contract's access rule, enforced server-side: the three disclosure
endpoints return **428 Precondition Required** without an in-scope passed
verification, and 200 with one. `/value` is the third of them — it was added in
phase 2 to deliver that phase's demonstrable outcome and discloses what a policy
is worth, so it is gated exactly like the other two (D-CL-044).

The flow is: open an interaction (`CN-`), present the panel (held details +
authority holders — see test_policy_search.py), the handler ticks what the
caller states correctly, then reads the record. Every 200 writes a
``disclosure`` event and every refused read writes a ``bypass_attempt``, so
"did anything leak?" is answerable from the log rather than by inspection.

The gate is checked *after* the role guard, so an unauthenticated request is
still a 401 — a 428 would otherwise tell an anonymous caller that the policy
number is worth trying again with a session.
"""

from fastapi.testclient import TestClient

from src.web.console.app import create_console_app

POLICY_NO = "LP-20419876"
THREE = ["policy_no", "name_dob", "address_or_bank"]


def _app():
    return create_console_app(secret="test-secret")


def _client(app=None):
    return TestClient(app or _app())


def _front_office(client, actor=None):
    body = {"role": "front_office"}
    if actor:
        body["actor"] = actor
    assert client.post("/api/login", json=body).status_code == 200


def _open_interaction(client, policy_no=POLICY_NO, **extra):
    r = client.post("/api/interaction/open", json={"policy_no": policy_no, **extra})
    assert r.status_code == 200
    return r.json()["cn_ref"]


def _verify(client, cn_ref, policy_no=POLICY_NO, confirmed=None):
    return client.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": policy_no,
        "confirmed": THREE if confirmed is None else confirmed})


def _verified_client():
    """A logged-in front-office session that has passed the gate.

    Presents before confirming, because that is the real flow — the handler
    sees the panel before anyone ticks it.
    """
    app = _app()
    client = _client(app)
    _front_office(client)
    cn_ref = _open_interaction(client)
    client.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO})
    assert _verify(client, cn_ref).json()["outcome"] == "passed"
    return app, client, cn_ref


# ── opening an interaction ───────────────────────────────────────────────
def test_opening_an_interaction_mints_a_cn_reference():
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c)
    assert cn_ref.startswith("CN-") and len(cn_ref) == 13


def test_opening_an_interaction_needs_a_session():
    assert _client().post("/api/interaction/open",
                          json={"policy_no": POLICY_NO}).status_code == 401


# ── present → tick → record ──────────────────────────────────────────────
def test_presenting_returns_the_checks_for_this_record():
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c)
    body = c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO}).json()
    kinds = [chk["kind"] for chk in body["checks"]]
    assert kinds == THREE            # nobody in the seeded book has a memorable item


def test_ticking_three_checks_passes_and_returns_a_verification_id():
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c)
    body = _verify(c, cn_ref).json()
    assert body["outcome"] == "passed"
    assert body["verification_id"]


def test_ticking_too_few_fails_and_returns_the_cannot_verify_route():
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c)
    body = _verify(c, cn_ref, confirmed=["policy_no", "name_dob"]).json()
    assert body["outcome"] == "failed"
    assert body["route"]["source"] == "05-OPS:3.5"
    assert body["route"]["disclose"] is False


# ── the access rule: 428 without, 200 with ───────────────────────────────
def test_the_record_is_428_without_a_verification():
    c = _client()
    _front_office(c)
    assert c.get(f"/api/policy/{POLICY_NO}").status_code == 428


def test_the_history_is_428_without_a_verification():
    c = _client()
    _front_office(c)
    assert c.get(f"/api/policy/{POLICY_NO}/history").status_code == 428


def test_the_valuation_is_428_without_a_verification():
    # The third disclosure endpoint, added in phase 2 (D-CL-044).
    c = _client()
    _front_office(c)
    assert c.get(f"/api/policy/{POLICY_NO}/value").status_code == 428


def test_all_three_open_once_verified():
    _, c, cn_ref = _verified_client()
    for path in ("", "/history", "/value"):
        r = c.get(f"/api/policy/{POLICY_NO}{path}?cn_ref={cn_ref}")
        assert r.status_code == 200, path


def test_a_verified_response_names_the_verification_that_unlocked_it():
    _, c, cn_ref = _verified_client()
    body = c.get(f"/api/policy/{POLICY_NO}?cn_ref={cn_ref}").json()
    assert body["meta"]["verification_id"]


def test_a_failed_verification_does_not_open_the_record():
    c = _client()
    _front_office(c)
    cn_ref = _open_interaction(c)
    _verify(c, cn_ref, confirmed=["policy_no"])
    assert c.get(f"/api/policy/{POLICY_NO}?cn_ref={cn_ref}").status_code == 428


def test_a_verification_on_one_policy_does_not_open_another():
    _, c, cn_ref = _verified_client()
    assert c.get(f"/api/policy/HB-40582213?cn_ref={cn_ref}").status_code == 428


def test_an_unauthenticated_request_is_still_401_not_428():
    # A 428 would tell an anonymous caller the number is worth retrying with a
    # session. The role guard runs first.
    assert _client().get(f"/api/policy/{POLICY_NO}").status_code == 401


# ── every disclosure is logged ───────────────────────────────────────────
def test_a_disclosure_is_recorded_for_each_200():
    app, c, cn_ref = _verified_client()
    c.get(f"/api/policy/{POLICY_NO}?cn_ref={cn_ref}")
    log = app.state.gate_events
    assert len(log.of_kind("disclosure")) == 1


def test_a_refused_read_is_recorded_as_a_bypass_attempt():
    app = _app()
    c = _client(app)
    _front_office(c)
    c.get(f"/api/policy/{POLICY_NO}")
    assert len(app.state.gate_events.of_kind("bypass_attempt")) == 1


def test_no_disclosure_ever_happens_without_a_passed_record():
    # The phase's headline assertion, over a whole session's traffic.
    app = _app()
    c = _client(app)
    _front_office(c)
    c.get(f"/api/policy/{POLICY_NO}")                       # refused
    cn_ref = _open_interaction(c)
    c.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": POLICY_NO})
    _verify(c, cn_ref)                                       # passed
    c.get(f"/api/policy/{POLICY_NO}?cn_ref={cn_ref}")        # allowed
    c.get(f"/api/policy/{POLICY_NO}/value?cn_ref={cn_ref}")  # allowed
    assert app.state.gate_events.bypass_count() == 0


def test_the_presented_and_passed_events_are_recorded():
    app, c, cn_ref = _verified_client()
    kinds = [e.kind for e in app.state.gate_events.for_interaction(cn_ref)]
    assert "presented" in kinds and "passed" in kinds


# ── the raise path carries the verification forward ──────────────────────
def test_raising_a_case_stamps_the_interaction_and_verification_on_it():
    _, c, cn_ref = _verified_client()
    raised = c.post("/api/cases/raise", json={
        "policy_no": POLICY_NO, "request": "partial surrender £5,000",
        "priority": "high", "amount_pence": 500000, "cn_ref": cn_ref}).json()
    assert raised["cn_ref"] == cn_ref
    assert raised["verification_id"]


def test_a_case_cannot_be_raised_without_a_verification():
    c = _client()
    _front_office(c)
    r = c.post("/api/cases/raise", json={
        "policy_no": POLICY_NO, "request": "partial surrender", "priority": "high"})
    assert r.status_code == 428


# ── the agent is a disclosure surface too ────────────────────────────────
# Found by the phase-3 review. The spec names three disclosure endpoints and
# omits /api/agent — but the agent's tools read the same book, so asking it
# "what is their balance?" returned the balance with no verification, logged
# nothing, and left bypass_count() reporting zero. A metric that is satisfied
# by not looking is worse than no metric (D-CL-052).

def test_the_agent_is_428_without_a_verification():
    c = _client()
    _front_office(c)
    r = c.post("/api/agent", json={"policy_no": POLICY_NO,
                                   "message": "what is their balance?"})
    assert r.status_code == 428


def test_the_agent_answers_once_verified():
    _, c, cn_ref = _verified_client()
    r = c.post("/api/agent", json={"policy_no": POLICY_NO, "cn_ref": cn_ref,
                                   "message": "what is their balance?"})
    assert r.status_code == 200
    assert r.json()["result"]["value"] == "£46,210.00"


def test_an_ungated_agent_call_is_counted_as_a_bypass_attempt():
    app = _app()
    c = _client(app)
    _front_office(c)
    c.post("/api/agent", json={"policy_no": POLICY_NO, "message": "balance?"})
    assert len(app.state.gate_events.of_kind("bypass_attempt")) == 1


def test_the_agent_needs_no_verification_for_a_rules_question():
    # Retrieval answers "what does the rule say" and touches no personal data,
    # so gating it would refuse a question the handler is allowed to ask before
    # the caller is verified (07-RUNBOOK:4.1 permits general product info).
    c = _client()
    _front_office(c)
    r = c.post("/api/agent", json={"message": "how do they claim?"})
    assert r.status_code == 200
