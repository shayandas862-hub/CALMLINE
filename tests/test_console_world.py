"""The console reading the world instead of inventing one.

The card's done-when: **the console serves a policy from the dataset, its
history renders, and the whole existing suite still passes untouched.**

That last clause is why the generator is not deleted and the default book is not
switched underneath 1,800 tests. The split is the one the card states — *the
dataset becomes what the console uses; the generator becomes what tests use* —
so `build_world_book()` is a second way to build a book, and `run_console.py`
is what asks for it.

**`src/` does not import `world/`.** The world-builder imports the rulebook so
it can check what it generates; the reverse would make the console depend on the
builder and ship one with the other. What crosses the line is the committed
*file*, exactly as `synthetic_history` already reads its own manifest — so this
module reads `data/world/` and knows nothing about how it was made.

The cross-check that stops the two ends drifting is
``test_the_console_reads_exactly_what_the_world_writer_wrote``: it writes with
`world.dataset` and reads with `src.records`, so a change to either side that
the other did not follow fails here rather than in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.records.seed import build_world_book
from src.records.world_seed import WORLD_ROOT, WorldSeedError
from src.web.console.app import create_console_app


@pytest.fixture(scope="module")
def world_book():
    """The committed dataset, read once."""
    return build_world_book()


def _client(book) -> TestClient:
    return TestClient(create_console_app(book=book, secret="test-secret"))


def _verified(client: TestClient, book, policy_no: str) -> str:
    """Log in, open a contact and pass the gate — the console's real path.

    The panel presents the world's own record and the handler's three ticks
    pass it (D-CL-114): the caller is verified against what the book actually
    holds, not against a fixture.
    """
    client.post("/api/login", json={"role": "front_office", "actor": "handler"})
    cn_ref = client.post("/api/interaction/open",
                         json={"policy_no": policy_no,
                               "channel": "phone"}).json()["cn_ref"]

    client.post("/api/verify", json={"cn_ref": cn_ref, "policy_no": policy_no})
    passed = client.post("/api/verify", json={
        "cn_ref": cn_ref, "policy_no": policy_no,
        "confirmed": ["policy_no", "name_dob", "address_or_bank"]})
    assert passed.json()["outcome"] == "passed", passed.json()
    return cn_ref


# ── the book ─────────────────────────────────────────────────────────────
def test_the_world_book_holds_the_two_hundred(world_book):
    assert len(world_book.list_policies()) == 200


def test_no_policy_in_the_world_book_is_a_specimen(world_book):
    """The three the rulebook documents are specimens, not customers. A world
    that quietly contained them would make two of the card's claims false at
    once — that the book is the dataset, and that no policy in it is special."""
    numbers = {p.policy_no for p in world_book.list_policies()}
    assert numbers.isdisjoint({"LP-20419876", "HB-40582213", "RA-77103428"})


def test_every_policys_value_is_the_sum_of_its_movements(world_book):
    """The book is loaded through the real store API, so the ledger folds the
    same way it does for a handler's movement."""
    for policy in world_book.list_policies():
        entries = world_book.history(policy.policy_no)
        assert entries, f"{policy.policy_no} has no movements"
        assert entries[-1].balance_after_pence == sum(
            e.transaction.signed_pence for e in entries)


# ── the console ──────────────────────────────────────────────────────────
def test_the_console_serves_a_policy_from_the_dataset(world_book):
    """The card's headline: type a world policy number and see the record."""
    policy_no = sorted(p.policy_no for p in world_book.list_policies())[0]
    client = _client(world_book)
    cn_ref = _verified(client, world_book, policy_no)

    response = client.get(f"/api/policy/{policy_no}", params={"cn_ref": cn_ref})
    assert response.status_code == 200
    assert response.json()["policy_no"] == policy_no


def test_a_thirty_year_history_renders(world_book):
    """The oldest policy in the book, through the history endpoint. Not a unit
    test of the fold — the endpoint, because that is what a person opens."""
    oldest = min(world_book.list_policies(), key=lambda p: p.start_date)
    assert oldest.start_date < "2000-01-01", "the book has lost its long histories"

    client = _client(world_book)
    cn_ref = _verified(client, world_book, oldest.policy_no)
    response = client.get(f"/api/policy/{oldest.policy_no}/history",
                          params={"cn_ref": cn_ref})

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) > 20, "a thirty-year policy with almost no movements"


def test_the_gate_still_refuses_an_unverified_world_policy(world_book):
    """Pointing the console at a new book must not open a side door: the
    disclosure surfaces are gated on the verification, not on the book."""
    policy_no = sorted(p.policy_no for p in world_book.list_policies())[0]
    client = _client(world_book)
    client.post("/api/login", json={"role": "front_office", "actor": "handler"})

    assert client.get(f"/api/policy/{policy_no}").status_code == 428


def test_a_world_policys_valuation_folds_its_own_ledger(world_book):
    policy_no = sorted(p.policy_no for p in world_book.list_policies())[0]
    client = _client(world_book)
    cn_ref = _verified(client, world_book, policy_no)

    response = client.get(f"/api/policy/{policy_no}/value",
                          params={"cn_ref": cn_ref})
    assert response.status_code == 200
    assert response.json()["value_pence"] == sum(
        e.transaction.signed_pence for e in world_book.history(policy_no))


# ── the two ends agree ───────────────────────────────────────────────────
def test_the_console_reads_exactly_what_the_world_writer_wrote(tmp_path: Path,
                                                               world_book):
    """Written by `world.dataset`, read by `src.records` — the one test that
    fails if either end of the format moves without the other."""
    from world import WORLD_BIRTH_DATE
    from world.dataset import World, write_world
    from world.lifetimes.build import build_book

    write_world(World.of(build_book(seed=11, born=WORLD_BIRTH_DATE), seed=11),
                tmp_path)
    fresh = build_world_book(tmp_path)

    assert [p.policy_no for p in fresh.list_policies()] == \
        [p.policy_no for p in world_book.list_policies()]
    for policy in fresh.list_policies():
        assert [e.transaction.signed_pence
                for e in fresh.history(policy.policy_no)] == \
            [e.transaction.signed_pence
             for e in world_book.history(policy.policy_no)]


def test_the_committed_dataset_is_the_one_the_console_reads():
    """`WORLD_ROOT` points at the committed files, not at a copy."""
    assert (WORLD_ROOT / "policies.jsonl").is_file()
    assert (WORLD_ROOT / "manifest.json").is_file()


def test_the_launched_console_serves_the_world_not_the_generator():
    """The card's claim is about **the console**, not about a function a test
    can reach. `run_console.py` is the only thing that launches one, so this
    asserts what it passes rather than trusting that it was wired up."""
    source = (Path(__file__).resolve().parents[1] /
              "scripts" / "run_console.py").read_text()
    assert "build_world_book()" in source
    assert "create_console_app(book=book" in source


def test_the_demo_cases_name_no_policy(world_book):
    """The demo picks by product from whatever book it is given. Naming three
    numbers tied it to the generator's book and made three policies special —
    both of which this phase is undoing."""
    from src.casework.queue import CaseQueue
    from src.web.console.demo_cases import seed_demo_cases

    cases = seed_demo_cases(CaseQueue(), build_world_book(), "2026-07-13T09:00:00")

    assert len(cases) >= 4
    numbers = {c.policy_no for c in cases}
    assert numbers <= {p.policy_no for p in world_book.list_policies()}


# ── what the console refuses to boot on ──────────────────────────────────
def test_a_damaged_dataset_is_refused_rather_than_half_loaded(tmp_path: Path):
    """A console that boots on a corrupted book serves wrong policies silently.
    The same guarantee as task 0, enforced on the reading side too."""
    from world import WORLD_BIRTH_DATE
    from world.dataset import World, write_world
    from world.lifetimes.build import build_book

    write_world(World.of(build_book(seed=11, born=WORLD_BIRTH_DATE), seed=11),
                tmp_path)
    path = tmp_path / "policies.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:120]) + "\n")

    with pytest.raises(WorldSeedError) as caught:
        build_world_book(tmp_path)
    assert "policies.jsonl" in str(caught.value)


def test_a_dataset_with_no_manifest_is_refused(tmp_path: Path):
    (tmp_path / "policies.jsonl").write_text("")
    with pytest.raises(WorldSeedError) as caught:
        build_world_book(tmp_path)
    assert "manifest.json" in str(caught.value)


def test_an_edited_policy_row_is_refused(tmp_path: Path, world_book):
    """The digest catches what a line count cannot."""
    from world import WORLD_BIRTH_DATE
    from world.dataset import World, write_world
    from world.lifetimes.build import build_book

    write_world(World.of(build_book(seed=11, born=WORLD_BIRTH_DATE), seed=11),
                tmp_path)
    path = tmp_path / "policies.jsonl"
    rows = path.read_text().splitlines()
    row = json.loads(rows[0])
    row["entries"][0]["amount_pence"] += 1
    rows[0] = json.dumps(row, sort_keys=True)
    path.write_text("\n".join(rows) + "\n")

    with pytest.raises(WorldSeedError):
        build_world_book(tmp_path)
