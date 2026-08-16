"""v4.5 phase 1 · task 2 — everyone the world needs, from reserved ranges.

The world is not policyholders. Somebody has to hold the power of attorney,
somebody has to be the adviser firm that calls and the named individual at it,
somebody has to be the trustee whose signature a deed needs, and somebody has
to be the personal representative when the holder has died. None of them exist
today: the generator invents holders and stops.

The guarantee under test is **structural rather than promised**. Every telephone
number, postcode and email address — of every person type, not only holders —
comes from a range that is officially reserved and can never belong to anybody.
Random values would eventually collide with a real person; reserved ones cannot.

An adviser firm is deliberately not a person: it has a firm name and a regulator
reference, and no date of birth to be wrong about.
"""

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from world.identities import (
    ADVISER_FIRM,
    PERSON_ROLES,
    generate_identities,
    write_jsonl,
)
from world.identities.reserved import FAMILY_TOKENS, GIVEN_TOKENS

AS_OF = date(2026, 7, 25)


def _world(seed=11):
    return generate_identities(seed=seed, as_of=AS_OF)


def _people(world):
    """Everyone who is a person — the firms are not."""
    return [r for r in world if r["role"] != ADVISER_FIRM]


def _firms(world):
    return [r for r in world if r["role"] == ADVISER_FIRM]


# ── the cast ─────────────────────────────────────────────────────────────
def test_every_role_the_world_needs_is_generated():
    roles = {r["role"] for r in _world()}
    assert roles == set(PERSON_ROLES) | {ADVISER_FIRM}


def test_the_book_is_two_hundred_holders():
    assert sum(1 for r in _world() if r["role"] == "policyholder") == 200


def test_there_is_at_least_one_of_every_other_role():
    # A world with no deputy cannot demonstrate refusing a deputy.
    counts = {}
    for record in _world():
        counts[record["role"]] = counts.get(record["role"], 0) + 1
    for role in PERSON_ROLES:
        assert counts.get(role, 0) >= 1, f"nobody is a {role}"


# ── the reserved ranges, for EVERY person type ───────────────────────────
def test_every_telephone_number_is_in_the_reserved_range():
    # Ofcom's 07700 900000–900999 is never allocated to a real subscriber.
    for record in _world():
        phone = record["contact"]["phone"]
        assert re.fullmatch(r"07700 900\d{3}", phone), (
            f"{record['role']} {record.get('party_id')}: {phone!r} is not reserved")


def test_no_two_parties_share_a_telephone_number():
    # The reserved range holds exactly a thousand numbers and the world needs a
    # few hundred, so independent draws collide by the birthday problem rather
    # than by bad luck — around forty-five duplicates on every seed before this
    # was guarded. Two people on one registered mobile is a fault a real book
    # would not have, and it would spoil any question about the number someone
    # is calling from.
    phones = [r["contact"]["phone"] for r in _world()]
    assert len(phones) == len(set(phones))


def test_a_world_too_large_to_stay_reserved_is_refused():
    # Growing past the reserved range must fail loudly. Falling back to an
    # unreserved number is exactly the collision with a real person that the
    # whole scheme exists to make impossible.
    with pytest.raises(ValueError):
        generate_identities(seed=11, as_of=AS_OF, holders=1200)


def test_every_email_is_on_the_reserved_domain():
    # example.org is reserved by RFC 2606 and can never be registered.
    for record in _world():
        assert record["contact"]["email"].endswith("@example.org")


def test_every_postcode_is_in_the_unallocated_area():
    # ZZ is not an allocated UK postcode area.
    for record in _world():
        assert re.search(r"\bZZ\d{1,2} \d[A-Z]{2}$", record["registered_address"]), (
            f"{record['role']}: {record['registered_address']!r}")


def test_every_persons_name_comes_from_the_non_human_vocabularies():
    pattern = re.compile(r"^([A-Z][a-z]+) ([A-Z][a-z]+) (\d{1,3})$")
    for record in _people(_world()):
        match = pattern.match(record["name"])
        assert match, f"{record['name']!r} must be token-token-number"
        assert match.group(1) in GIVEN_TOKENS
        assert match.group(2) in FAMILY_TOKENS


def test_every_date_of_birth_is_valid_and_adult_against_the_injected_date():
    for record in _people(_world()):
        dob = date.fromisoformat(record["dob"])  # raises if invalid
        assert 25 <= (AS_OF - dob).days // 365 <= 90


def test_nobody_arrives_already_verified():
    # Identity verification only ever happens through the gate, at runtime.
    assert all(r["id_verified_level"] is None for r in _people(_world()))


# ── a firm is not a person ───────────────────────────────────────────────
def test_an_adviser_firm_has_no_date_of_birth():
    firms = _firms(_world())
    assert firms, "the world needs adviser firms"
    for firm in firms:
        assert firm.get("dob") is None
        assert "party_id" not in firm


def test_an_adviser_firm_carries_a_regulator_reference_that_cannot_be_real():
    # The FCA register is numeric, so a reference carrying a letter cannot
    # collide with a real firm's FRN. There is no officially reserved range,
    # and this does not pretend there is one.
    for firm in _firms(_world()):
        assert re.fullmatch(r"Z\d{6}", firm["firm_ref"]), firm["firm_ref"]
        assert not firm["firm_ref"].isdigit()


def test_a_firm_names_individuals_who_exist_as_people():
    world = _world()
    advisers = {r["party_id"] for r in world if r["role"] == "adviser"}
    assert advisers, "the world needs named advisers"
    for firm in _firms(world):
        assert firm["individuals"], f"{firm['firm_id']} names nobody"
        for party_id in firm["individuals"]:
            assert party_id in advisers


def test_every_adviser_belongs_to_a_firm_that_exists():
    world = _world()
    firm_ids = {f["firm_id"] for f in _firms(world)}
    for record in world:
        if record["role"] == "adviser":
            assert record["firm_id"] in firm_ids


# ── identity is unique, and reproducible ─────────────────────────────────
def test_party_ids_and_names_are_unique_across_every_role():
    people = _people(_world())
    for field in ("party_id", "name"):
        values = [p[field] for p in people]
        assert len(values) == len(set(values)), f"duplicate {field}"


def test_the_same_seed_reproduces_the_world_exactly():
    assert _world(seed=11) == _world(seed=11)


def test_a_different_seed_produces_a_different_world():
    assert _world(seed=11) != _world(seed=12)


def test_the_written_file_is_byte_for_byte_reproducible(tmp_path):
    # The world is committed and reviewed before it becomes data, so a rerun
    # that shuffles bytes would make the diff unreadable.
    first, second = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_jsonl(_world(), first)
    write_jsonl(_world(), second)
    assert first.read_bytes() == second.read_bytes()


def test_the_written_file_round_trips(tmp_path):
    world = _world()
    out = tmp_path / "people.jsonl"
    write_jsonl(world, out)
    assert [json.loads(line) for line in out.read_text().splitlines()] == world


def test_nothing_is_dated_after_the_worlds_birth_date():
    # The as-of date is injected and frozen into the dataset; the wall clock is
    # never read, so the world cannot shift because a script ran on another day.
    for record in _people(_world()):
        assert date.fromisoformat(record["dob"]) < AS_OF


@pytest.mark.parametrize("count", [0, -1])
def test_a_world_with_no_holders_is_refused(count):
    with pytest.raises(ValueError):
        generate_identities(seed=11, as_of=AS_OF, holders=count)


def test_every_person_can_become_a_party_in_the_system_of_record():
    # A world that cannot be loaded is not a world. `Party` validates the id
    # grammar at construction, so this also proves the role bands stay inside
    # `^PH-\d{4}$` rather than overflowing into five digits.
    from src.records.models import Contact, Party

    for record in _people(_world()):
        party = Party(party_id=record["party_id"], name=record["name"],
                      dob=record["dob"],
                      registered_address=record["registered_address"],
                      contact=Contact(**record["contact"]),
                      scottish_taxpayer=record["scottish_taxpayer"])
        assert party.party_id == record["party_id"]
        assert party.id_verified_level is None
