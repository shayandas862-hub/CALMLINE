"""What the reader refuses, and whether it says enough to act on.

This is the half of task 0 that matters. A reader that half-loads a damaged
world hands the console two hundred policies of which some number are wrong, and
nothing downstream can tell which — so every failure here is refused **whole**,
and the message names the file and the thing that did not add up.

Two layers, deliberately not one:

- **integrity** — a digest per file, recorded in the manifest. Catches a changed
  digit, which a line count cannot.
- **structure** — the row actually carries the fields the format promises.
  Catches a file that is intact but not a world.

The structural tests re-stamp the digest first (``_restamp``). Without that they
would pass on the integrity check and never reach the code they exist to test —
a test passing for the wrong reason is worse than one that fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from world.dataset import DatasetError, World, read_world, write_world

SEED = 11


def _restamp(root: Path, name: str) -> None:
    """Re-digest one file so a structural test is not caught by integrity first."""
    from world.dataset.manifest import digest_of

    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    body = (root / name).read_bytes()
    manifest["files"][name] = {"lines": len(body.splitlines()),
                               "sha256": digest_of(body)}
    manifest["counts"][name.split(".")[0]] = len(body.splitlines())
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


# ── integrity ────────────────────────────────────────────────────────────
def test_a_truncated_policies_file_is_refused_naming_the_shortfall(
        tmp_path: Path, world_book):
    """The failure task 0 exists to prevent: a world short of policies, loaded
    anyway, with nothing downstream able to say which are missing."""
    write_world(World.of(world_book, seed=SEED), tmp_path)
    path = tmp_path / "policies.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:150]) + "\n")

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "policies.jsonl" in str(caught.value)
    assert "150" in str(caught.value) and "200" in str(caught.value)


def test_an_edited_policy_is_refused_naming_the_file(tmp_path: Path, tiny_world):
    """A single digit changed — the line count still ties, so only the digest
    catches it. An edited world is not the world that was reviewed."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "policies.jsonl"
    edited = path.read_text().replace('"amount_pence": 50000',
                                      '"amount_pence": 90000')
    assert edited != path.read_text(), "the fixture no longer carries that figure"
    path.write_text(edited)

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "policies.jsonl" in str(caught.value)


def test_an_edited_people_file_is_refused(tmp_path: Path, tiny_world):
    """The people file is carried, not regenerated — so it is also checked."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "people.jsonl"
    path.write_text(path.read_text().replace("PH-0001", "PH-9999"))

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "people.jsonl" in str(caught.value)


def test_a_missing_file_is_refused_naming_it(tmp_path: Path, tiny_world):
    write_world(tiny_world, tmp_path)
    (tmp_path / "stories.jsonl").unlink()

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "stories.jsonl" in str(caught.value)


def test_a_missing_manifest_is_refused(tmp_path: Path, tiny_world):
    """Without it there is no birth date, no seeds and nothing to check
    against — which is not a world, whatever the other files hold."""
    write_world(tiny_world, tmp_path)
    (tmp_path / "manifest.json").unlink()

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "manifest.json" in str(caught.value)


# ── the manifest itself ──────────────────────────────────────────────────
def test_a_manifest_whose_counts_disagree_is_refused(tmp_path: Path, tiny_world):
    """Editing the manifest to match a damaged file must not launder it."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["counts"]["policies"] = 3
    path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "policies" in str(caught.value)


def test_an_unknown_format_version_is_refused(tmp_path: Path, tiny_world):
    """A reader that guesses at a format it has never seen is the half-load this
    task exists to prevent."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["format_version"] = 99
    path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "99" in str(caught.value)


def test_a_manifest_missing_its_birth_date_is_refused(tmp_path: Path, tiny_world):
    """The one field the manifest exists for."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    del manifest["world_birth_date"]
    path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "world_birth_date" in str(caught.value)


# ── structure ────────────────────────────────────────────────────────────
def test_a_policy_row_missing_a_field_is_refused_naming_it(tmp_path: Path,
                                                           tiny_world):
    """Named down to the field, because "policies.jsonl is wrong" is not
    something anybody can act on."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "policies.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    del rows[0]["band"]
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    _restamp(tmp_path, "policies.jsonl")

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "band" in str(caught.value)
    assert "LP-20000137" in str(caught.value)


def test_a_row_that_is_not_json_is_refused_naming_the_line(tmp_path: Path,
                                                           tiny_world):
    write_world(tiny_world, tmp_path)
    path = tmp_path / "policies.jsonl"
    path.write_text(path.read_text() + "{not json\n")
    _restamp(tmp_path, "policies.jsonl")

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "line 3" in str(caught.value)


def test_a_policy_whose_ledger_does_not_reconcile_is_refused(tmp_path: Path,
                                                             tiny_world):
    """The balance a row claims to have left behind must be the balance its own
    movements reach. A file asserting both is a file that can disagree with
    itself, and value is a fold over movements everywhere else in the system."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "policies.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["entries"][1]["balance_after_pence"] += 1
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    _restamp(tmp_path, "policies.jsonl")

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "LP-20000137" in str(caught.value)


def test_a_movement_dated_after_the_birth_date_is_refused(tmp_path: Path,
                                                          tiny_world):
    """The world cannot contain its own future, and the manifest is what makes
    that checkable at read time rather than only at build time."""
    write_world(tiny_world, tmp_path)
    path = tmp_path / "policies.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["entries"][1]["at"] = "2026-09-01T00:00:00"
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    _restamp(tmp_path, "policies.jsonl")

    with pytest.raises(DatasetError) as caught:
        read_world(tmp_path)
    assert "2026-07-28" in str(caught.value)
