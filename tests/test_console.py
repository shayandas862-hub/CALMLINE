"""v3 phase 5 · Task 2 — the console app endpoints (offline, role-guarded).

Drives the whole front→back flow through the API with a fake role login: look
up a policy, ask the agent, raise a case, approve it, and watch the ledger move
— with server-side role guards enforced.

**v4 phase 3.** Reading a record is now gated: a session opens an interaction
and passes verification before any of the three disclosure endpoints answers.
``_verified`` is that preamble, so these tests keep testing what they were
written to test rather than re-testing the gate (which `test_console_gate.py`
owns).
"""

from fastapi.testclient import TestClient

from src.web.console.app import create_console_app


def _client():
    return TestClient(create_console_app(secret="test-secret"))


def _login(client, role, actor=None):
    body = {"role": role}
    if actor is not None:
        body["actor"] = actor
    r = client.post("/api/login", json=body)
    assert r.status_code == 200
    return r


_CONFIRMED = ["policy_no", "name_dob", "address_or_bank"]


def _verified(client, policy_no):
    """Open a contact and pass the gate — the preamble to any disclosure."""
    cn_ref = client.post("/api/interaction/open",
                         json={"policy_no": policy_no}).json()["cn_ref"]
    out = client.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": policy_no,
        "confirmed": _CONFIRMED}).json()
    assert out["outcome"] == "passed", out
    return cn_ref


def test_login_rejects_an_unknown_role():
    assert _client().post("/api/login", json={"role": "admin"}).status_code == 400


def test_a_protected_endpoint_needs_a_session():
    assert _client().get("/api/policy/LP-20419876").status_code == 401


def test_front_office_looks_up_a_policy_record():
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    r = c.get("/api/policy/LP-20419876", params={"cn_ref": cn_ref})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["current_value"] == "£46,210.00"
    assert body["holder"]["name"] == "Theta Meridian 12"


def test_back_office_endpoint_refuses_a_front_office_session():
    c = _client()
    _login(c, "front_office")
    assert c.get("/api/cases").status_code == 403  # wrong role, server-side


def test_agent_chat_answers_a_claim_question_with_a_citation():
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    r = c.post("/api/agent", json={"policy_no": "LP-20419876", "cn_ref": cn_ref,
                                   "message": "how do they claim?"})
    assert r.status_code == 200
    out = r.json()
    assert out["tool"] == "retrieve_clause"
    assert out["result"]["found"] is True
    assert out["result"]["clauses"]


def test_agent_chat_answers_a_balance_question_from_the_ledger():
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    r = c.post("/api/agent", json={"policy_no": "LP-20419876", "cn_ref": cn_ref,
                                   "message": "what is their balance?"})
    out = r.json()
    assert out["tool"] == "get_transaction_history"
    assert out["result"]["value"] == "£46,210.00"


def test_raise_then_approve_moves_the_ledger_end_to_end():
    c = _client()
    # front office raises a withdrawal case
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    raised = c.post("/api/cases/raise", json={
        "policy_no": "LP-20419876", "request": "partial surrender £5,000",
        "priority": "high", "amount_pence": 500000, "cn_ref": cn_ref}).json()
    case_id = raised["case_id"]
    assert raised["recommendation"] == "proceed"

    # back office sees it, opens it, approves it
    _login(c, "back_office")
    queue = c.get("/api/cases").json()
    assert any(item["case_id"] == case_id for item in queue)
    detail = c.get(f"/api/cases/{case_id}").json()
    assert detail["record"]["current_value"] == "£46,210.00"
    approved = c.post(f"/api/cases/{case_id}/approve")
    assert approved.status_code == 200

    # the ledger moved: £46,210 − £5,000 = £41,210
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    assert c.get("/api/policy/LP-20419876",
                 params={"cn_ref": cn_ref}).json()["current_value"] == "£41,210.00"


def test_the_approval_audit_records_who_approved_by_name():
    # The audit trail is evidence, and `07-RUNBOOK:4.3` wants a checker_id on
    # the case. Recording the role — or worse, the session object — names
    # nobody, and two approvals by "back_office" cannot be told apart.
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "LP-20419876")
    raised = c.post("/api/cases/raise", json={
        "policy_no": "LP-20419876", "request": "partial surrender £5,000",
        "priority": "high", "amount_pence": 500000, "cn_ref": cn_ref}).json()

    _login(c, "back_office", actor="reviewer_kim")
    detail = c.post(f"/api/cases/{raised['case_id']}/approve").json()
    approved = next(e for e in detail["audit"] if e["event"] == "approved")
    assert approved["actor"] == "reviewer_kim"


def test_login_rejects_a_malformed_actor():
    assert _client().post("/api/login", json={
        "role": "back_office", "actor": "Reviewer Kim"}).status_code == 400


def test_a_do_not_proceed_case_cannot_be_approved():
    c = _client()
    _login(c, "front_office")
    # a pension pays out only via a benefit route → raised as do_not_proceed
    cn_ref = _verified(c, "RA-77103428")
    raised = c.post("/api/cases/raise", json={
        "policy_no": "RA-77103428", "request": "cash withdrawal",
        "priority": "low", "cn_ref": cn_ref}).json()
    _login(c, "back_office")
    assert c.post(f"/api/cases/{raised['case_id']}/approve").status_code == 409


# ── point-in-time valuation: the phase's demonstrable outcome ────────────
def test_the_console_answers_what_a_bond_was_worth_on_a_date():
    # "What was this bond worth on 12 April?" — a ledger-fold number with its
    # as_at shown, on a real Aldercrest policy.
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "HB-40582213")
    r = c.get("/api/policy/HB-40582213/value",
              params={"as_at": "2026-04-12", "cn_ref": cn_ref})
    assert r.status_code == 200
    body = r.json()
    assert body["policy_no"] == "HB-40582213"
    assert body["as_at"] == "2026-04-12"
    assert body["value"].startswith("£")
    assert body["entries_counted"] > 0


def test_the_valuation_moves_across_a_seeded_withdrawal():
    # The bond's six annual withdrawals are real ledger rows, so two dates
    # either side of one give different answers.
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "HB-40582213")
    before = c.get("/api/policy/HB-40582213/value",
                   params={"as_at": "2020-02-29", "cn_ref": cn_ref}).json()
    after = c.get("/api/policy/HB-40582213/value",
                  params={"as_at": "2020-03-02", "cn_ref": cn_ref}).json()
    assert before["value_pence"] == 12_000_000        # £120,000 invested
    assert after["value_pence"] == 11_400_000         # less the first £6,000
    assert before["value"] != after["value"]


def test_the_valuation_defaults_to_the_consoles_injected_now():
    c = _client()
    _login(c, "front_office")
    cn_ref = _verified(c, "HB-40582213")
    body = c.get("/api/policy/HB-40582213/value", params={"cn_ref": cn_ref}).json()
    assert body["as_at"] == "2026-07-13"              # not the wall clock
    assert body["value_pence"] == c.get(
        "/api/policy/HB-40582213", params={"cn_ref": cn_ref}).json()[
        "current_value_pence"]


def test_the_valuation_endpoint_is_role_guarded():
    assert _client().get("/api/policy/HB-40582213/value").status_code == 401


def test_valuing_an_unknown_policy_is_a_404_not_a_silent_zero():
    c = _client()
    _login(c, "front_office")
    assert c.get("/api/policy/HB-99999999/value").status_code == 404
