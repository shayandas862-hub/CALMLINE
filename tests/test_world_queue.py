"""`world/load/queue.py` — live work, written into the dataset, never into history.

The queue is the only thing in the world that ages, so it is a **separate,
re-runnable step**: it appends open cases to `queue.jsonl` — a fourth data
file, present while empty, the `stories.jsonl` precedent — and touches not a
byte of `policies.jsonl` or `stories.jsonl`. Open cases therefore never enter
the prose ledger, phase 4's pins survive untouched, and `PolicyOperations`
keeps meaning finished business.

Dates are injected (`as_of`), never the wall clock; references continue
deterministically from whatever the policy already carries, so two runs
produce two sets and no collisions.
"""

import dataclasses
import json
from datetime import date

import pytest

from src.casework.queue import CaseQueue, QueueError
from src.casework.world_cases import cases_from_queue
from world.dataset import DatasetError, read_world, write_world
from world.dataset.carry import carried_queue, carried_stories
from world.load.queue import LIVE_STATUSES, append_queue, open_queue

AS_OF = date(2026, 7, 28)


@pytest.fixture
def two_live(tiny_world):
    """tiny_world with both policies in force — candidates for live work —
    and both holders present, so the prose ledger can walk it too."""
    bond = dataclasses.replace(tiny_world.policies[1], status="in_force")
    return dataclasses.replace(
        tiny_world, policies=(tiny_world.policies[0], bond),
        people=[{"party_id": "PH-0001"}, {"party_id": "PH-0002"}])


# ── the step itself ──────────────────────────────────────────────────────


def test_the_step_opens_live_cases_only_on_policies_that_exist(two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=4)
    policy_nos = {policy.policy_no for policy in two_live.policies}
    assert len(rows) == 4
    for row in rows:
        assert row["policy_no"] in policy_nos
        assert row["status"] in LIVE_STATUSES
        assert row["status"] != "completed"
        assert row["priority"] in {"high", "medium", "low"}
        assert row["opened_on"] <= AS_OF.isoformat()
        assert row["sla_due"] > AS_OF.isoformat()   # a deadline, not history
        assert row["cn_ref"] is None


def test_only_in_force_policies_get_live_work(tiny_world):
    # tiny_world's bond is surrendered; every case must land on the LP.
    rows = open_queue(tiny_world, as_of=AS_OF, seed=7, count=3)
    assert {row["policy_no"] for row in rows} == {"LP-20000137"}


def test_the_step_is_deterministic_for_a_given_seed(two_live):
    assert open_queue(two_live, as_of=AS_OF, seed=7, count=4) == \
        open_queue(two_live, as_of=AS_OF, seed=7, count=4)
    assert open_queue(two_live, as_of=AS_OF, seed=7, count=4) != \
        open_queue(two_live, as_of=AS_OF, seed=8, count=4)


def test_references_continue_from_history_and_never_collide(two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=4)
    taken = {case.cw_ref for operations in two_live.operations.values()
             for case in operations.cases}
    minted = [row["cw_ref"] for row in rows]
    assert len(set(minted)) == len(minted)
    assert not taken & set(minted)
    # the LP already carries index 001 (its historical case), so its first
    # live case continues at 002, in the policy-derived grammar
    lp_refs = [ref for ref, row in zip(minted, rows)
               if row["policy_no"] == "LP-20000137"]
    assert lp_refs and lp_refs[0] == "CW-100137002"


def test_a_second_run_produces_a_second_set_with_no_collisions(two_live):
    first = open_queue(two_live, as_of=AS_OF, seed=7, count=3)
    grown = dataclasses.replace(two_live, queue=tuple(first))
    second = open_queue(grown, as_of=AS_OF, seed=7, count=3)
    refs = [row["cw_ref"] for row in first + second]
    assert len(set(refs)) == len(refs)


def test_evidence_claims_no_party_the_policy_lacks(two_live):
    # neither tiny policy has a trust or an adviser mandate, so no evidence
    # line may assert one was checked — the reconciliation's rule
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=6)
    for row in rows:
        for item in row["evidence"]:
            assert "trustee" not in item["requirement"]
            assert "adviser" not in item["requirement"]
            assert item["received_on"] <= AS_OF.isoformat()


# ── the dataset carries it ───────────────────────────────────────────────


def test_append_writes_the_queue_and_touches_no_historical_byte(tmp_path,
                                                                two_live):
    write_world(two_live, tmp_path)
    before = {name: (tmp_path / name).read_bytes()
              for name in ("people.jsonl", "policies.jsonl", "stories.jsonl")}

    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=2)
    append_queue(tmp_path, rows)

    for name, body in before.items():
        assert (tmp_path / name).read_bytes() == body, name
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["counts"]["queue"] == 2
    read_back = read_world(tmp_path)
    assert list(read_back.queue) == list(rows)


def test_appending_an_already_written_reference_is_refused_whole(tmp_path,
                                                                 two_live):
    write_world(two_live, tmp_path)
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=2)
    append_queue(tmp_path, rows)
    with pytest.raises(DatasetError) as refusal:
        append_queue(tmp_path, [rows[0]])
    assert rows[0]["cw_ref"] in str(refusal.value)
    assert json.loads((tmp_path / "manifest.json").read_text()
                      )["counts"]["queue"] == 2


def test_the_reader_refuses_a_queue_case_on_an_unknown_policy(tmp_path,
                                                              two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=1)
    bad = dict(rows[0], policy_no="LP-20999999")
    write_world(dataclasses.replace(two_live, queue=(bad,)), tmp_path)
    with pytest.raises(DatasetError) as refusal:
        read_world(tmp_path)
    assert "LP-20999999" in str(refusal.value)


def test_the_reader_refuses_a_completed_queue_case(tmp_path, two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=1)
    finished = dict(rows[0], status="completed")
    write_world(dataclasses.replace(two_live, queue=(finished,)), tmp_path)
    with pytest.raises(DatasetError) as refusal:
        read_world(tmp_path)
    assert "completed" in str(refusal.value)


def test_a_regeneration_carries_the_queue_like_the_stories(tmp_path, two_live):
    write_world(two_live, tmp_path)
    append_queue(tmp_path, open_queue(two_live, as_of=AS_OF, seed=7, count=2))

    carried = dataclasses.replace(two_live,
                                  stories=carried_stories(tmp_path),
                                  queue=carried_queue(tmp_path))
    write_world(carried, tmp_path)          # the __main__ regeneration path
    assert len(read_world(tmp_path).queue) == 2


# ── the prose ledger never sees it ───────────────────────────────────────


def test_the_prose_ledger_ignores_live_work(two_live):
    from world.stories.workfile import outstanding, progress

    with_queue = dataclasses.replace(
        two_live, queue=tuple(open_queue(two_live, as_of=AS_OF, seed=7,
                                         count=4)))
    assert progress(with_queue) == progress(two_live)
    assert outstanding(with_queue) == outstanding(two_live)


# ── the console shows it, ranked ─────────────────────────────────────────


def test_the_console_admits_the_rows_under_their_own_references(two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=4)
    queue = CaseQueue()
    for case in cases_from_queue(rows):
        queue.admit(case)

    ranked = queue.list_ranked(f"{AS_OF.isoformat()}T09:00:00")
    assert {case.cw_ref for case in ranked} == {row["cw_ref"] for row in rows}
    urgencies = [{"high": 0, "medium": 1, "low": 2}[case.priority]
                 for case in ranked]
    assert urgencies == sorted(urgencies)
    for case in ranked:
        assert case.status in LIVE_STATUSES
        assert case.created_at is not None


def test_admitting_the_same_reference_twice_is_refused(two_live):
    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=1)
    queue = CaseQueue()
    (case,) = cases_from_queue(rows)
    queue.admit(case)
    with pytest.raises(QueueError):
        queue.admit(case)


def test_a_minted_console_case_cannot_collide_with_a_dataset_reference(two_live):
    # the console mints CW-3000000xx upward; the dataset's carry policy digits
    queue = CaseQueue()
    for case in cases_from_queue(open_queue(two_live, as_of=AS_OF, seed=7,
                                            count=2)):
        queue.admit(case)
    minted = queue.open({"policy_no": "LP-20000137", "request": "fresh"})
    assert minted.cw_ref not in {row["cw_ref"] for row in
                                 open_queue(two_live, as_of=AS_OF, seed=7,
                                            count=2)}


def test_the_back_office_screen_serves_the_dataset_queue_ranked(two_live):
    """The done criterion is about the console, not about a function a test
    can reach — so ask the endpoint the back office actually uses."""
    from fastapi.testclient import TestClient

    from src.records.seed import build_seed_book
    from src.web.console.app import create_console_app

    rows = open_queue(two_live, as_of=AS_OF, seed=7, count=3)
    app = create_console_app(book=build_seed_book(),
                             queue_cases=cases_from_queue(rows))
    client = TestClient(app)
    client.post("/api/login", json={"role": "back_office", "actor": "reviewer"})

    served = client.get("/api/cases").json()
    # case_id IS the CW- reference — one identifier per piece of work
    refs = [case["case_id"] for case in served]
    assert set(refs) >= {row["cw_ref"] for row in rows}
    urgency = {"high": 0, "medium": 1, "low": 2}
    priorities = [urgency[case["priority"]] for case in served]
    assert priorities == sorted(priorities)


# ── the two readers moved together ───────────────────────────────────────


def test_both_readers_speak_format_two_and_list_the_queue_file():
    from src.records import world_seed
    from world.dataset import manifest

    assert manifest.FORMAT_VERSION == 2
    assert world_seed.FORMAT_VERSION == 2
    assert "queue.jsonl" in manifest.DATA_FILES
    assert "queue.jsonl" in world_seed.DATA_FILES
