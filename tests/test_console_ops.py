"""v3 phase 6 · Tasks 2–3 — the demo-case seeder and the ops endpoint.

The seeder builds illustrative cases through the SAME real path the front office
uses, so the ops (and back-office) screens are populated offline. The endpoint
is role-guarded to ops and reads the live queue + book — not a static snapshot.
Every phase-5 endpoint stays unchanged (the default keeps the queue empty).
"""

from fastapi.testclient import TestClient

from src.casework.models import sla_seconds_left
from src.casework.queue import CaseQueue
from src.records.models import gbp
from src.records.seed import build_seed_book
from src.web.console.app import create_console_app
from src.web.console.demo_cases import _pick, seed_demo_cases

NOW = "2026-07-13T09:00:00"


def _client(*, seed_demo=False):
    return TestClient(create_console_app(secret="test-secret", seed_demo=seed_demo))


def _login(client, role):
    assert client.post("/api/login", json={"role": role}).status_code == 200


# ── the demo seeder (unit) ────────────────────────────────────────────────
def test_seed_demo_cases_creates_a_spread_of_outcomes():
    # Arrange
    queue, book = CaseQueue(), build_seed_book()
    # Act
    seed_demo_cases(queue, book, NOW)
    cases = queue.all()
    # Assert — a real mix so all three lenses show honest, non-zero numbers
    assert len(cases) >= 4
    assert any(c.recommendation == "do_not_proceed" for c in cases)      # an AI block
    assert any(c.status == "completed" for c in cases)                   # throughput
    assert any(c.status == "pending_review" and sla_seconds_left(c, NOW) < 0
               for c in cases)                                           # an SLA breach


def test_seed_demo_leaves_a_pending_case_ledger_untouched():
    """A pending case carries a *proposal*, which has no write capability. The
    policy is now chosen by property rather than named, so the claim is asserted
    as the change it is — nothing moved — rather than as an absolute figure that
    only held for one book."""
    queue, book = CaseQueue(), build_seed_book()
    protection = _pick(book, "lifelong_protection")
    before = book.current_value(protection)

    seed_demo_cases(queue, book, NOW)

    assert book.current_value(protection) == before


def test_seed_demo_moves_only_the_one_approved_ledger():
    """Exactly one of the four demo cases is approved, and it moves £1,000 —
    approval being the only path that moves money."""
    queue, book = CaseQueue(), build_seed_book()
    bond = _pick(book, "horizon_bond", at_least_pence=gbp(3_000))
    before = book.current_value(bond)

    seed_demo_cases(queue, book, NOW)

    assert book.current_value(bond) == before - gbp(1_000)


# ── the ops endpoint (role-guarded) ───────────────────────────────────────
def test_ops_endpoint_needs_a_session():
    assert _client().get("/api/ops").status_code == 401


def test_ops_endpoint_refuses_a_front_office_session():
    c = _client()
    _login(c, "front_office")
    assert c.get("/api/ops").status_code == 403   # wrong role, server-side


def test_ops_snapshot_reports_all_three_lenses_from_seeded_data():
    # The v4 board chamber: safety, grounding, operations. `compliance` and
    # `system` are gone — this is the one v3 surface v4 deliberately replaces
    # (D-CL-017), and the queue/ledger numbers that were honest moved into
    # `operations` rather than being dropped.
    # Arrange
    c = _client(seed_demo=True)
    _login(c, "ops")
    # Act
    snap = c.get("/api/ops").json()
    # Assert
    assert set(snap) >= {"safety", "grounding", "operations"}
    assert snap["safety"]["gate_bypass"]["value"] == 0
    assert snap["operations"]["completed"] == 1
    # The demo approves exactly one £1,000 withdrawal, so the book under
    # administration is the seeded total less that single committed movement.
    from src.records.models import format_gbp
    from src.records.seed import build_seed_book
    seeded = build_seed_book()
    expected = sum(seeded.current_value(p.policy_no)
                   for p in seeded.list_policies()) - gbp(1_000)
    assert snap["operations"]["policies"] == len(seeded.list_policies())
    assert snap["operations"]["funds_under_admin"] == format_gbp(expected)
    assert snap["grounding"]["corpus_clauses"] > 0       # the KB is loaded
    assert snap["grounding"]["kb_version"]               # and stamped


def test_the_board_can_be_sliced_to_one_model():
    # D-CL-061: swapping models to compare them means every lens must be able
    # to say which model's traces it is describing.
    c = _client()
    _login(c, "ops")
    snap = c.get("/api/ops", params={"model_id": "claude-sonnet-5"}).json()
    assert snap["safety"]["model_id"] == "claude-sonnet-5"
    assert snap["grounding"]["model_id"] == "claude-sonnet-5"


def test_ops_snapshot_reflects_a_live_raise_not_a_static_view():
    # the ops screen reads the SAME live queue the front office writes to
    c = _client()  # no demo seed
    _login(c, "front_office")
    # Raising reads the record, so it goes through the gate like any disclosure.
    cn_ref = c.post("/api/interaction/open",
                    json={"policy_no": "LP-20419876"}).json()["cn_ref"]
    assert c.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": "LP-20419876",
        "confirmed": ["policy_no", "name_dob",
                      "address_or_bank"]}).json()["outcome"] == "passed"
    raised = c.post("/api/cases/raise", json={
        "policy_no": "LP-20419876", "request": "partial surrender",
        "priority": "high", "amount_pence": gbp(1_000), "cn_ref": cn_ref}).json()
    _login(c, "ops")
    ops = c.get("/api/ops").json()
    assert ops["operations"]["open"] >= 1
    assert any(item["case_id"] == raised["case_id"] for item in ops["operations"]["queue"])


def test_seed_demo_defaults_off_and_preserves_the_phase5_empty_queue():
    c = _client()  # default seed_demo=False → unchanged phase-5 behaviour
    _login(c, "back_office")
    assert c.get("/api/cases").json() == []
