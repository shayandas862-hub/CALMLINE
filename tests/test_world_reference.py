"""The reference sheet — what you need to verify a caller against any policy.

The card's done-when:

- **every policy in the book appears**
- **picking any row at random and using it against the running console passes
  the identity check**

The second is the one that matters, and it is asserted the hard way: rows are
taken from the generated sheet, fed to the console's own gate, and the outcome
has to be ``passed``. A sheet that is merely *consistent with* the book is a
sheet that can be consistently wrong.

**Generated from the dataset, never hand-written, so it cannot drift.** The
committed `data/world/reference-sheet.md` is checked against a freshly rendered
one, so an edited sheet fails here rather than misleading somebody at a desk.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.records.seed import build_world_book
from src.web.console.app import create_console_app
from world.dataset import DEFAULT_ROOT, read_world
from world.reference import SHEET_PATH, reference_rows, render_sheet


@pytest.fixture(scope="module")
def world():
    return read_world(DEFAULT_ROOT)


@pytest.fixture(scope="module")
def rows(world):
    return reference_rows(world)


# ── every policy appears ─────────────────────────────────────────────────
def test_every_policy_in_the_book_appears(world, rows):
    assert len(rows) == len(world.policies) == 200
    assert {r.policy_no for r in rows} == {p.policy_no for p in world.policies}


def test_every_row_carries_what_the_gate_will_ask_for(rows):
    """`05-OPS:3.2`'s checks, and nothing a handler could not read out."""
    for row in rows:
        assert row.holder_name and row.dob and row.address
        assert row.bank_last4 is None or len(row.bank_last4) == 4


def test_every_row_says_what_makes_the_policy_interesting(rows):
    """Product, status, trust and authority — the reason to pick one row rather
    than another when demonstrating a refusal."""
    for row in rows:
        assert row.product in {"lifelong_protection", "horizon_bond",
                               "retirement_account"}
        assert row.status
        assert isinstance(row.in_trust, bool)
        assert isinstance(row.authority, str)


# ── the sheet is generated, not written ──────────────────────────────────
def test_the_committed_sheet_matches_a_freshly_rendered_one(world):
    """The anti-drift check. Hand-edit the sheet and this fails."""
    assert SHEET_PATH.read_text(encoding="utf-8") == render_sheet(world)


def test_rendering_twice_produces_the_same_sheet(world):
    assert render_sheet(world) == render_sheet(world)


def test_the_sheet_names_every_policy(world, rows):
    sheet = render_sheet(world)
    for row in rows:
        assert row.policy_no in sheet


def test_the_sheet_states_the_worlds_birth_date(world):
    assert "2026-07-28" in render_sheet(world)


def test_the_sheet_flags_the_policies_that_exist_to_be_refused(world, rows):
    """§4's six never-executed trusts and six unregistered registrable ones are
    in the book **to be refused**, so a sheet that does not point at them is a
    sheet nobody can demonstrate a refusal from.

    This nearly shipped wrong. ``Trust.executed`` is a ``str`` holding
    ``"yes"``/``"no"`` in the world and a **date** in the corpus's specimen
    records — both truthy — so the obvious ``if trust.executed`` check flagged
    none of the six.
    """
    notes = [row.note for row in rows]
    assert sum("trust never executed" in n for n in notes) == 6
    assert sum("registrable trust, unregistered" in n for n in notes) == 6


def test_the_sheet_carries_no_specimen_number(world):
    """The three the corpus documents are not in the book and must not be on a
    sheet a handler uses to look policies up."""
    sheet = render_sheet(world)
    for specimen in ("LP-20419876", "HB-40582213", "RA-77103428"):
        assert specimen not in sheet


# ── the claim that matters ───────────────────────────────────────────────
def _present_panel(client: TestClient, row):
    """Open a contact and present the handler's panel for this row's policy."""
    client.post("/api/login", json={"role": "front_office", "actor": "handler"})
    cn_ref = client.post("/api/interaction/open",
                         json={"policy_no": row.policy_no,
                               "channel": "phone"}).json()["cn_ref"]
    panel = client.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": row.policy_no}).json()
    return cn_ref, {f["label"]: f["value"] for chk in panel["checks"]
                    for f in chk["held"]}


def test_a_row_taken_from_the_sheet_matches_the_handlers_panel(rows):
    """The card's demonstrable outcome, restated for the tick model
    (D-CL-114): the panel the handler ticks against shows exactly what the
    sheet says — so a caller reading from the sheet is confirmable on every
    check, and three ticks pass."""
    client = TestClient(create_console_app(book=build_world_book(),
                                           secret="test-secret"))
    for row in _spread(rows, 12):
        cn_ref, shown = _present_panel(client, row)
        assert shown["Policy number"] == row.policy_no
        assert shown["Full name"] == row.holder_name, row.policy_no
        assert shown["Date of birth"] == row.dob
        assert shown["Registered address"] == row.address
        if row.bank_last4:
            assert shown["Account last 4"] == row.bank_last4
        passed = client.post("/api/verify", json={
            "cn_ref": cn_ref, "policy_no": row.policy_no,
            "confirmed": ["policy_no", "name_dob", "address_or_bank"]}).json()
        assert passed["outcome"] == "passed", row.policy_no


def test_an_impostors_name_is_visibly_wrong_on_the_panel(rows):
    """The defence lives on the screen now (D-CL-114): the panel shows the
    book's holder, so a caller claiming a neighbouring row's name is caught by
    the handler — and without that third tick, the attempt is refused."""
    client = TestClient(create_console_app(book=build_world_book(),
                                           secret="test-secret"))
    first, second = rows[0], next(r for r in rows
                                  if r.holder_name != rows[0].holder_name)
    cn_ref, shown = _present_panel(client, first)
    assert shown["Full name"] != second.holder_name

    refused = client.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": first.policy_no,
        "confirmed": ["policy_no", "address_or_bank"]}).json()
    assert refused["outcome"] != "passed"


def _spread(rows, count: int):
    """Every nth row — a spread across products and statuses rather than the
    first twelve, which would all be the same product."""
    step = max(1, len(rows) // count)
    return rows[::step][:count]
