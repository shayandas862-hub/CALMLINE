"""The working file — what a writing session reads, and what it may append.

The card's done-when:

- the file **round-trips**
- a partly-written world **reports exactly which policies are outstanding**
- **nothing already written is overwritten** by resuming

Plus correction 1's guard, which is this phase's own: **a regeneration must not
be able to delete the stories.** Measured before it was written —
`python -m world.dataset` took a `stories.jsonl` carrying prose to 0 bytes and
rebuilt the manifest around the empty file, so every count tied and every digest
verified afterwards and nothing downstream noticed.

There is deliberately **no second copy of the world**. The persisted state is
`stories.jsonl` itself and the work list is derived from it, because a workfile
holding its own idea of what is written is a workfile that can disagree with the
prose beside it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from world.dataset import DEFAULT_ROOT, DatasetError, World, read_world, write_world
from world.dataset.manifest import digest_of
from world.stories.workfile import (
    append_stories,
    cast_for,
    outstanding,
    plan_work,
    progress,
    work_for,
)

# Measured from the committed dataset, not estimated. The reconciliation that
# gave the three claimed Retirement Accounts their death claims added one
# notification contact and one claim case each.
POLICIES = 200
WITH_CONTACTS = 189
NOTES = 1406
NARRATIVES = 476
BUSIEST = "HB-20002740"


@pytest.fixture(scope="module")
def world():
    """The committed world, however much prose has been written into it."""
    return read_world(DEFAULT_ROOT)


@pytest.fixture(scope="module")
def unwritten(world):
    """The same world with its prose removed.

    Task 3 fills `stories.jsonl` over many sittings, so a test that asserts how
    much is outstanding has to say *from what starting point* or it fails on
    every batch. These describe the mechanism, not the progress.
    """
    return replace(world, stories=())


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A private copy of the committed world with the prose taken out."""
    for name in ("people.jsonl", "policies.jsonl", "stories.jsonl",
                 "queue.jsonl", "manifest.json"):
        shutil.copy(DEFAULT_ROOT / name, tmp_path / name)

    (tmp_path / "stories.jsonl").write_bytes(b"")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest["files"]["stories.jsonl"] = {"lines": 0, "sha256": digest_of(b"")}
    manifest["counts"]["stories"] = 0
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return tmp_path


def _note(policy_no: str, ref: str, text: str = "Called about the valuation.") -> dict:
    return {"policy_no": policy_no, "ref": ref, "kind": "note", "text": text}


# ── the brief for one policy ─────────────────────────────────────────────
def test_the_work_list_covers_every_policy(world):
    """All two hundred, including the eleven that get no prose — a work list
    silently short of the book is the failure this file exists to prevent."""
    assert len(plan_work(world)) == POLICIES


def test_the_work_for_a_policy_carries_its_numbers_and_its_empty_slots(world):
    """Everything the writer needs to write from, and nothing invented."""
    work = work_for(world, BUSIEST)

    assert work.policy_no == BUSIEST
    assert work.product == "horizon_bond"
    assert work.holder["party_id"] == work.cast.holder
    assert work.entries, "a policy with no ledger is nothing to write from"
    assert len(work.contacts) == 20
    assert len(work.cases) == 12
    assert work.pieces == 32
    # The slot is empty and present, exactly as phase 2 left it.
    assert all(contact.note_slot == "" for contact in work.contacts)


def test_the_cast_is_who_may_be_named_on_this_policy(world):
    """The role surface, measured: 115 of 200 policies have no third party at
    all, so on those a story naming anybody but the holder is a failure."""
    holder_only = [w for w in plan_work(world)
                   if set(w.cast.by_role) == {"policyholder"}]
    assert len(holder_only) == 115

    with_trustees = [w for w in plan_work(world) if w.cast.by_role.get("trustee")]
    assert len(with_trustees) == 32


def test_the_cast_names_the_adviser_firm_but_not_as_a_party(world):
    """`AF-` is not a person. The firm is a name; the people it has authorised
    are `PH-3xxx` party ids on the mandate."""
    advised = next(w for w in plan_work(world) if w.cast.adviser_firm)
    assert advised.cast.adviser_firm not in advised.cast.party_ids
    assert advised.cast.by_role["adviser"], "a mandate names its individuals"


# ── what is outstanding ──────────────────────────────────────────────────
def test_every_policy_with_a_contact_history_starts_outstanding(unwritten):
    """Before a word is written, the outstanding list is the whole job."""
    assert len(outstanding(unwritten)) == WITH_CONTACTS


def test_a_policy_with_no_contacts_is_never_outstanding(world, unwritten):
    """Eleven policies get nothing. They are done before they are started, and
    a work list that demands prose for them can never empty."""
    silent = [w.policy_no for w in plan_work(world) if w.pieces == 0]
    assert len(silent) == POLICIES - WITH_CONTACTS
    assert not set(silent) & set(outstanding(unwritten))


def test_progress_counts_pieces_rather_than_policies(unwritten):
    """A policy needing twenty notes and one needing one are not the same
    amount of work, and a policy count says they are."""
    done, total = progress(unwritten)
    assert done == 0
    assert total == NOTES + NARRATIVES


def test_the_committed_world_agrees_with_its_own_prose(world):
    """However far task 3 has got, every story on disk counts towards exactly
    one piece of work — so a story attached to nothing would show up here."""
    done, total = progress(world)
    assert done == len(world.stories)
    assert total == NOTES + NARRATIVES


def test_a_policy_drops_off_the_outstanding_list_when_it_is_complete(world, root):
    """The resumability claim, on a real policy."""
    work = work_for(world, BUSIEST)
    rows = [_note(BUSIEST, contact.cn_ref) for contact in work.contacts]
    rows += [{"policy_no": BUSIEST, "ref": case.cw_ref, "kind": "narrative",
              "text": "Surrender requested; instruction received in writing."}
             for case in work.cases]

    append_stories(root, rows)
    resumed = read_world(root)

    assert BUSIEST not in outstanding(resumed)
    assert len(outstanding(resumed)) == WITH_CONTACTS - 1
    assert progress(resumed) == (32, NOTES + NARRATIVES)


def test_a_partly_written_policy_is_still_outstanding(world, root):
    """Half a policy is not a written policy. The point of the list is that a
    session resuming it cannot leave a hole in the middle of a history."""
    work = work_for(world, BUSIEST)
    append_stories(root, [_note(BUSIEST, work.contacts[0].cn_ref)])

    assert BUSIEST in outstanding(read_world(root))


# ── resuming never destroys ──────────────────────────────────────────────
def test_appending_a_ref_that_is_already_written_is_refused(world, root):
    """Nothing already written is overwritten by resuming."""
    work = work_for(world, BUSIEST)
    ref = work.contacts[0].cn_ref
    append_stories(root, [_note(BUSIEST, ref, "The first version.")])

    with pytest.raises(DatasetError) as raised:
        append_stories(root, [_note(BUSIEST, ref, "A different second version.")])

    assert ref in str(raised.value)
    assert "The first version." in (root / "stories.jsonl").read_text()


def test_appending_the_same_ref_twice_in_one_call_is_refused(world, root):
    """The duplicate does not have to be already on disk to be a duplicate."""
    ref = work_for(world, BUSIEST).contacts[0].cn_ref
    with pytest.raises(DatasetError) as raised:
        append_stories(root, [_note(BUSIEST, ref), _note(BUSIEST, ref)])
    assert ref in str(raised.value)


def test_a_refused_append_writes_nothing_at_all(world, root):
    """All of it or none of it — the same discipline as the reader's refusal.
    A partial append leaves prose on disk that no session knows it wrote."""
    work = work_for(world, BUSIEST)
    good = _note(BUSIEST, work.contacts[0].cn_ref)
    before = (root / "stories.jsonl").read_bytes()

    with pytest.raises(DatasetError):
        append_stories(root, [good, _note(BUSIEST, work.contacts[1].cn_ref),
                              good])

    assert (root / "stories.jsonl").read_bytes() == before


def test_appending_leaves_the_dataset_readable(world, root):
    """The manifest is what the files are checked against, so an append that
    does not refresh it leaves a world its own reader refuses."""
    append_stories(root, [_note(BUSIEST, work_for(world, BUSIEST).contacts[0].cn_ref)])

    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["counts"]["stories"] == 1
    assert read_world(root).stories  # refuses on a stale digest


# ── correction 1: the regeneration must not delete the prose ─────────────
def test_regenerating_the_world_keeps_the_stories(world, root):
    """🔴 Measured before this guard existed: `python -m world.dataset` wrote an
    empty `stories.jsonl` and rebuilt the manifest around it, so every count
    tied and every digest verified and nothing noticed."""
    append_stories(root, [_note(BUSIEST, work_for(world, BUSIEST).contacts[0].cn_ref)])
    before = (root / "stories.jsonl").read_bytes()
    assert before

    finished = subprocess.run(
        [sys.executable, "-m", "world.dataset", "--seed", "11",
         "--out", str(root)],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])

    assert finished.returncode == 0, finished.stderr
    assert (root / "stories.jsonl").read_bytes() == before
    assert read_world(root).stories


def test_a_hand_formatted_stories_file_is_carried_not_refused(world, root):
    """`stories.jsonl` is hand-written by design, so somebody will re-indent it
    or reorder its keys. The guard asks whether any prose would stop existing,
    not whether the bytes match — a guard that cries wolf on an ordinary edit is
    one that gets taken out."""
    ref = work_for(world, BUSIEST).contacts[0].cn_ref
    row = _note(BUSIEST, ref)
    # Compact separators and insertion order: valid, and not what we would write.
    (root / "stories.jsonl").write_text(
        json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")

    write_world(World.of(_book(), seed=11, stories=(row,)), root)

    assert json.loads((root / "stories.jsonl").read_text())["ref"] == ref


def test_writing_a_world_over_prose_it_does_not_carry_is_refused(world, root):
    """The backstop, for any caller that is not the command line. Refusing
    beats overwriting: the prose is hand-written and cannot be regenerated."""
    append_stories(root, [_note(BUSIEST, work_for(world, BUSIEST).contacts[0].cn_ref)])

    with pytest.raises(DatasetError) as raised:
        write_world(World.of(_book(), seed=11), root)

    assert "stories.jsonl" in str(raised.value)


def _book():
    from world import WORLD_BIRTH_DATE
    from world.lifetimes.build import build_book

    return build_book(seed=11, born=WORLD_BIRTH_DATE)
