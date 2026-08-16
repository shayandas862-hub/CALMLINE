"""The shape a story must take — and what is refused rather than patched.

The card's done-when:

- a well-formed story **parses**
- one naming a **contact that does not exist** is refused
- one attached to the **wrong policy** is refused

The discipline is phase 2's refused movement, applied to prose: a story that
does not fit is **rejected and reported**, never quietly repaired. A patched
story is one whose text no longer describes the contact it hangs off, and
nothing downstream can tell which ones those are.

The vocabulary check is the brief made mechanical. `intent` and `outcome` are
closed categories, not sentences — a note carrying `withdrawal_request` in its
prose is a note somebody filled in rather than wrote.
"""

from __future__ import annotations

import pytest

from world.dataset import DEFAULT_ROOT, DatasetError, read_world
from world.stories.schema import Story, parse_queue, parse_story

BUSIEST = "HB-20002740"
CONTACT = "CN-2002740009"      # phone · withdrawal_request · case_raised
CASE = "CW-202740001"          # servicing · proceed
OTHER_POLICY = "LP-20000137"

NOTE_TEXT = ("Rang to set up the annual withdrawal again, same as last year. "
             "Confirmed identity and the account it goes to.")
CASE_TEXT = ("Surrender of whole segments requested in writing. The written "
             "instruction was received and checked, and the proceeds were "
             "released on the following anniversary.")


@pytest.fixture(scope="module")
def world():
    return read_world(DEFAULT_ROOT)


def _note(**over) -> dict:
    return {"policy_no": BUSIEST, "ref": CONTACT, "kind": "note",
            "text": NOTE_TEXT} | over


def _narrative(**over) -> dict:
    return {"policy_no": BUSIEST, "ref": CASE, "kind": "narrative",
            "text": CASE_TEXT} | over


# ── what parses ──────────────────────────────────────────────────────────
def test_a_well_formed_note_parses(world):
    story = parse_story(_note(), world, "stories.jsonl line 1")
    assert story == Story(policy_no=BUSIEST, ref=CONTACT, kind="note",
                          text=NOTE_TEXT)


def test_a_well_formed_case_narrative_parses(world):
    assert parse_story(_narrative(), world, "where").kind == "narrative"


def test_a_queue_of_stories_parses_in_order(world):
    stories = parse_queue([_note(), _narrative()], world)
    assert [s.ref for s in stories] == [CONTACT, CASE]


# ── the three refusals the card names ────────────────────────────────────
def test_a_note_naming_a_contact_that_does_not_exist_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(ref="CN-9999999999"), world, "where")
    assert "CN-9999999999" in str(raised.value)


def test_a_story_attached_to_the_wrong_policy_is_refused(world):
    """The contact is real and the policy is real; the pairing is not. This is
    the one a careless writer actually makes — the note is about the right call
    and filed against the wrong file."""
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(policy_no=OTHER_POLICY), world, "where")
    message = str(raised.value)
    assert CONTACT in message and OTHER_POLICY in message


def test_a_story_on_a_policy_that_is_not_in_the_book_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(policy_no="LP-20419876"), world, "where")
    assert "LP-20419876" in str(raised.value)


# ── the shape itself ─────────────────────────────────────────────────────
def test_a_story_missing_a_field_names_the_field(world):
    row = _note()
    del row["text"]
    with pytest.raises(DatasetError) as raised:
        parse_story(row, world, "stories.jsonl line 4")
    assert "'text'" in str(raised.value)
    assert "line 4" in str(raised.value)


def test_a_story_of_an_unknown_kind_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(kind="summary"), world, "where")
    assert "summary" in str(raised.value)


def test_empty_prose_is_refused(world):
    with pytest.raises(DatasetError):
        parse_story(_note(text="   "), world, "where")


def test_a_note_carrying_a_case_reference_is_refused(world):
    """One note per contact, one narrative per case. A note pointing at a case
    is a piece of prose with no contact behind it."""
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(ref=CASE), world, "where")
    assert CASE in str(raised.value)


def test_a_narrative_carrying_a_contact_reference_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_narrative(ref=CONTACT), world, "where")
    assert CONTACT in str(raised.value)


def test_a_reference_of_the_wrong_grammar_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(ref="CN-123"), world, "where")
    assert "CN-123" in str(raised.value)


# ── the brief, made mechanical ───────────────────────────────────────────
def test_prose_carrying_a_category_string_is_refused(world):
    """`intent` and `outcome` are closed vocabularies, not sentences."""
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(text="Caller made a withdrawal_request by phone."),
                    world, "where")
    assert "withdrawal_request" in str(raised.value)


def test_prose_carrying_an_outcome_string_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_story(_note(text="Could not verify — refused_verification."),
                    world, "where")
    assert "refused_verification" in str(raised.value)


def test_ordinary_english_that_merely_resembles_a_category_is_allowed(world):
    """The check is on the token, not on the subject. Handlers write about
    withdrawals and verification constantly and must be able to."""
    text = ("Asked to make a withdrawal. Could not verify the caller against "
            "the record, so nothing was disclosed.")
    assert parse_story(_note(text=text), world, "where").text == text


# ── refusing whole ───────────────────────────────────────────────────────
def test_a_queue_refuses_whole_and_names_the_row(world):
    with pytest.raises(DatasetError) as raised:
        parse_queue([_note(), _narrative(ref="CW-999999999")], world)
    assert "line 2" in str(raised.value)


def test_the_same_reference_twice_in_a_queue_is_refused(world):
    with pytest.raises(DatasetError) as raised:
        parse_queue([_note(), _note(text="A second go at the same call.")],
                    world)
    assert CONTACT in str(raised.value)


# ── the whole committed file, whatever is in it so far ───────────────────
def test_every_story_committed_so_far_parses(world):
    """The file on disk is held to the schema, not merely produced by it."""
    assert len(parse_queue(world.stories, world)) == len(world.stories)
