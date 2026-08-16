"""Somewhere to put a note — the schema had nowhere, and this checks the fix.

**Found by checking rather than assuming.** `interactions` (`0001_init.sql:294`)
carries `intent` and `outcome` — two short strings — and nothing that could hold
what was actually said on a call. Phase 4 generates exactly that, and without
this table it would exist in the files and be absent from the database.

A note is **attributable and immutable**: what was discussed, who wrote it, when,
against which contact and which policy. Append-only like everything else that is
evidence, because a note editable after the call is not a record of the call. A
correction is a new note referencing the one it corrects.

**No new reference format is invented.** The project defines six reference
grammars and a note is not among them; D-CL-109 settled that reference grammars are a real decision
rather than a convenience. So a note is keyed by a generated identity, exactly as
`record_changes` is — the house pattern for an internal journal that no customer
ever quotes down a telephone.

These are text assertions on the committed SQL, in the style of
`test_migration.py`. Kept in their own file because that one is already at 273
lines and the 300-line rule does not bend for a good reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.records.notes import ContactNote, NoteLog

MIGRATION = (Path(__file__).resolve().parent.parent
             / "src" / "db" / "migrations" / "0004_contact_notes.sql")


def sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


# ── the migration's shape ────────────────────────────────────────────────
def test_the_migration_exists():
    assert MIGRATION.exists(), "0004_contact_notes.sql must exist"


def test_it_creates_the_contact_notes_table():
    assert "create table if not exists contact_notes" in sql()


def test_it_creates_only_and_never_drops():
    """The card's constraint: creates only, no `drop`, no `alter` to an
    existing table. `0001` is still unapplied and carries an open decision;
    widening it by accident is how that decision gets made by accident."""
    body = sql().lower()
    assert "drop " not in body
    assert "alter table" not in body


def test_it_is_safe_to_run_twice():
    """Postgres has no `create trigger if not exists`, so the guard asks the
    catalogue — the same shape `0003` uses for its constraint."""
    body = sql().lower()
    assert "if not exists" in body
    assert "pg_trigger" in body


def test_a_note_is_attributable():
    """Who wrote it, when, against which contact and which policy."""
    body = sql()
    for column in ("cn_ref", "policy_no", "author", "written_at"):
        assert column in body, f"a note must record {column}"


def test_a_note_carries_what_was_actually_said():
    assert "body" in sql()


def test_the_contact_reference_is_a_foreign_key():
    """The card's done-when: a note whose contact does not exist is refused by
    the database, not by a hopeful application check."""
    assert "references interactions (cn_ref)" in sql()


def test_the_policy_reference_is_a_foreign_key():
    assert "references policies (policy_no)" in sql()


def test_a_correction_references_the_note_it_corrects():
    """Not an edit. The original stays exactly as written."""
    body = sql()
    assert "corrects_id" in body
    assert "references contact_notes (note_id)" in body


def test_the_table_is_append_only_by_trigger_not_by_convention():
    """The card's done-when: the table refuses an update. `0001` established
    that append-only is enforced for anything holding a connection string,
    not just for the application's one write path."""
    body = sql().lower()
    assert "before update or delete on contact_notes" in body
    assert "refuse_mutation" in body


def test_it_invents_no_new_customer_facing_reference_format():
    """Six reference grammars are defined and a note is not among them."""
    body = sql()
    assert "generated always as identity" in body
    assert "NOTE-" not in body


def test_an_empty_note_is_refused_by_the_database():
    """A blank note is not a record of anything."""
    assert "length(btrim(body))" in sql()


# ── the Python record ────────────────────────────────────────────────────
def test_a_note_round_trips_whole():
    # Arrange
    note = ContactNote(
        cn_ref="CN-0000000001", policy_no="LP-20419876",
        body="Caller asked why the premium had gone up at the year-10 review.",
        author="front_office:handler-7", written_at="2026-05-02T09:14:00")

    # Act
    restored = ContactNote(**note.as_dict())

    # Assert
    assert restored == note


def test_a_note_refuses_a_contact_reference_that_is_not_one():
    with pytest.raises(ValueError, match="cn_ref"):
        ContactNote(cn_ref="not-a-contact", policy_no="LP-20419876",
                    body="x", author="a", written_at="2026-05-02T09:14:00")


def test_a_note_refuses_a_policy_number_that_is_not_one():
    with pytest.raises(ValueError, match="policy"):
        ContactNote(cn_ref="CN-0000000001", policy_no="XX-1",
                    body="x", author="a", written_at="2026-05-02T09:14:00")


@pytest.mark.parametrize("blank", ["", "   ", "\n\t "])
def test_a_note_with_nothing_in_it_is_refused(blank):
    with pytest.raises(ValueError, match="body"):
        ContactNote(cn_ref="CN-0000000001", policy_no="LP-20419876",
                    body=blank, author="a", written_at="2026-05-02T09:14:00")


def test_a_note_refuses_an_author_nobody_can_be_held_to():
    with pytest.raises(ValueError, match="author"):
        ContactNote(cn_ref="CN-0000000001", policy_no="LP-20419876",
                    body="x", author="  ", written_at="2026-05-02T09:14:00")


# ── the append-only log ──────────────────────────────────────────────────
def _note(body="a note", corrects_id=None):
    return ContactNote(cn_ref="CN-0000000001", policy_no="LP-20419876",
                       body=body, author="front_office:handler-7",
                       written_at="2026-05-02T09:14:00", corrects_id=corrects_id)


def test_a_log_numbers_notes_from_one():
    log = NoteLog()
    assert log.record(_note()).note_id == 1
    assert log.record(_note()).note_id == 2


def test_a_recorded_note_keeps_everything_it_was_given():
    log = NoteLog()
    stored = log.record(_note(body="what was said"))
    assert stored.body == "what was said"
    assert stored.cn_ref == "CN-0000000001"


def test_notes_for_a_contact_come_back_in_the_order_written():
    log = NoteLog()
    for body in ("first", "second", "third"):
        log.record(_note(body=body))
    assert [n.body for n in log.for_contact("CN-0000000001")] == \
        ["first", "second", "third"]


def test_a_correction_is_a_new_note_and_leaves_the_original_alone():
    # Arrange
    log = NoteLog()
    original = log.record(_note(body="premium is £212.40"))

    # Act
    correction = log.record(_note(body="correction: £214.20",
                                  corrects_id=original.note_id))

    # Assert — two notes, and the first is untouched
    assert correction.corrects_id == original.note_id
    assert len(log.for_contact("CN-0000000001")) == 2
    assert log.for_contact("CN-0000000001")[0].body == "premium is £212.40"


def test_a_correction_of_a_note_that_does_not_exist_is_refused():
    with pytest.raises(ValueError, match="corrects"):
        NoteLog().record(_note(corrects_id=99))


def test_there_is_no_way_to_edit_or_remove_a_note():
    """Append-only in the Python record as well as in the table — the object
    is frozen and the log offers nothing but `record`."""
    log = NoteLog()
    log.record(_note())
    assert not [name for name in dir(log)
                if name.startswith(("update", "edit", "delete", "remove"))]
