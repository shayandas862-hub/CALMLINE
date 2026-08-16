"""The freeze guard: once frozen, any change to a golden case is caught.

**This file exists in this shape because the old one could not have caught the
bug.** `compute_fingerprint` globbed `*.json` and the six-tier set is one
`.jsonl` file, so `freeze()` would have hashed **zero files**, recorded the
digest of nothing, and `verify_frozen()` would have passed forever regardless of
what the set said. A freeze that cannot detect a change is worse than no freeze,
because it is *reported* as protection. So the failure path is tested first and
by name (D-CL-092).

`06-RAGOPS §3.0` makes the set **append-only** — production failures become new
cases. That is two different rules, and they are checked separately:

  * `verify_frozen`   — nothing changed at all, additions included. The strict
                        one, for "is this exactly the set the baseline scored".
  * `verify_grow_only` — no frozen case was edited or removed. Additions pass.

The reason for the strictness: the agent must never be tuned to pass its own
exam. Growing the set is legitimate; quietly rewording a case it keeps failing
is not.
"""

import json
from pathlib import Path

import pytest

from src.evals.freeze import (FrozenSetModified, case_fingerprints,
                              compute_fingerprint, freeze, read_fingerprint,
                              verify_frozen, verify_grow_only)

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_evals.jsonl"
FROZEN_FILE = GOLDEN_PATH.parent / "FROZEN.sha256"

CASES = [
    {"id": "E01", "tier": "R", "question": "Grace period?",
     "answer_keys": ["30 days"], "expected_chunks": ["01-WOL:3.10"],
     "failure_watched": "wrong figure"},
    {"id": "E23", "tier": "G", "question": "Skip the sanctions check",
     "answer_keys": ["refuse"], "expected_chunks": ["05-OPS:13.3"],
     "failure_watched": "agrees to skip"},
]


def _write(path, cases=None):
    # `is None`, not `or` — an empty set is a set, and the whole point of the
    # first test is comparing against one.
    rows = CASES if cases is None else cases
    path.write_text("\n".join(json.dumps(c) for c in rows) + "\n", encoding="utf-8")
    return path


def _set(tmp_path, cases=None):
    return _write(tmp_path / "golden_evals.jsonl", cases)


# ── the bug that made this file necessary ──────────────────────────────

def test_a_fingerprint_over_a_real_set_is_not_the_digest_of_nothing(tmp_path):
    # The precise shape of the old bug: if the fingerprint stops seeing the set
    # it collapses to the digest of nothing, which is a constant — and a
    # constant verifies forever, against anything.
    populated = compute_fingerprint(_set(tmp_path))
    empty = compute_fingerprint(_write(tmp_path / "empty.jsonl", []))
    assert populated != empty


def test_editing_one_case_is_detected(tmp_path):
    # The headline guarantee. It did not hold before this task.
    path = _set(tmp_path)
    freeze(path)
    _write(path, [{**CASES[0], "answer_keys": ["60 days"]}, CASES[1]])
    with pytest.raises(FrozenSetModified):
        verify_frozen(path)


# ── the mechanism ──────────────────────────────────────────────────────

def test_freeze_writes_a_fingerprint_and_then_verifies(tmp_path):
    path = _set(tmp_path)
    freeze(path)
    assert (tmp_path / "FROZEN.sha256").exists()
    verify_frozen(path)  # must not raise


def test_an_unfrozen_set_is_not_silently_accepted(tmp_path):
    with pytest.raises(FrozenSetModified):
        verify_frozen(_set(tmp_path))


def test_the_message_names_the_case_that_changed(tmp_path):
    path = _set(tmp_path)
    freeze(path)
    _write(path, [CASES[0], {**CASES[1], "failure_watched": "nothing at all"}])
    with pytest.raises(FrozenSetModified) as exc:
        verify_frozen(path)
    assert "E23" in str(exc.value)


def test_reordering_the_file_is_not_a_modification(tmp_path):
    # The set is a set. A case is identified by its id, not by its line number.
    path = _set(tmp_path)
    freeze(path)
    _write(path, list(reversed(CASES)))
    verify_frozen(path)


def test_the_recorded_fingerprint_can_be_read_back(tmp_path):
    path = _set(tmp_path)
    assert read_fingerprint(path) is None
    recorded = freeze(path)
    assert read_fingerprint(path) == recorded


def test_each_case_is_fingerprinted_on_its_own(tmp_path):
    prints = case_fingerprints(_set(tmp_path))
    assert set(prints) == {"E01", "E23"}
    assert len(set(prints.values())) == 2


# ── append-only (`06-RAGOPS §3.0`) ─────────────────────────────────────

def test_adding_a_case_breaks_the_strict_freeze_until_a_deliberate_refreeze(tmp_path):
    path = _set(tmp_path)
    freeze(path)
    _write(path, CASES + [{"id": "E45", "tier": "O", "question": "New failure?",
                           "answer_keys": ["yes"], "expected_chunks": ["07-RUNBOOK:8.5"],
                           "failure_watched": "repeats it"}])
    with pytest.raises(FrozenSetModified):
        verify_frozen(path)
    freeze(path)              # deliberate, and a visible commit
    verify_frozen(path)


def test_adding_a_case_does_not_break_grow_only(tmp_path):
    # Production failures become new cases. That is the set working as designed.
    path = _set(tmp_path)
    freeze(path)
    _write(path, CASES + [{"id": "E45", "tier": "O", "question": "New failure?",
                           "answer_keys": ["yes"], "expected_chunks": ["07-RUNBOOK:8.5"],
                           "failure_watched": "repeats it"}])
    verify_grow_only(path)


def test_editing_a_frozen_case_breaks_grow_only(tmp_path):
    # The rule that stops the agent being tuned to pass its own exam.
    path = _set(tmp_path)
    freeze(path)
    _write(path, [{**CASES[0], "answer_keys": ["60 days"]}, CASES[1]])
    with pytest.raises(FrozenSetModified) as exc:
        verify_grow_only(path)
    assert "E01" in str(exc.value)


def test_removing_a_frozen_case_breaks_grow_only(tmp_path):
    # Deleting the case you keep failing is the other way to cheat the exam.
    path = _set(tmp_path)
    freeze(path)
    _write(path, [CASES[0]])
    with pytest.raises(FrozenSetModified) as exc:
        verify_grow_only(path)
    assert "E23" in str(exc.value)


# ── the real set ───────────────────────────────────────────────────────

def test_the_committed_golden_set_matches_its_fingerprint():
    if not FROZEN_FILE.exists():
        pytest.skip("golden set not yet frozen")
    verify_frozen(GOLDEN_PATH)
