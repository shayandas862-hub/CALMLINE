"""The synthetic-book generator: 50–100 policyholders, formatted for the
v4 Party shape, with details that can never belong to a real person.

The guarantees under test (D-CL-022):
- names are built from non-human vocabularies AND carry a mandatory numeric
  tag — never shaped like a real human name;
- phone numbers sit in Ofcom's reserved fictional mobile range (07700 900xxx);
- emails use the RFC 2606 reserved domain example.org;
- postcodes use the unallocated ZZ area;
- DOBs are valid and adult against an injected as-of date (never the clock);
- output is deterministic for a seed, and every id/name/policy_no is unique.
"""

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from scripts.generate_policyholders import (
    FAMILY_TOKENS,
    GIVEN_TOKENS,
    KB_SAMPLE_POLICY_NOS,
    generate_book,
    write_jsonl,
)

AS_OF = date(2026, 7, 25)


def _book(count=50, seed=4):
    return generate_book(count=count, seed=seed, as_of=AS_OF)


def test_generates_requested_count_within_bounds():
    # Arrange / Act
    book = _book(count=72)

    # Assert
    assert len(book) == 72


@pytest.mark.parametrize("bad", [0, 49, 101, 1000])
def test_rejects_count_outside_50_to_100(bad):
    with pytest.raises(ValueError):
        generate_book(count=bad, seed=4, as_of=AS_OF)


def test_names_are_synthetic_and_never_humanlike():
    # Every name is "<GivenToken> <FamilyToken> <numeric tag>" — the tag makes
    # the full string impossible as a real legal name, the vocabularies are
    # minerals/geometry/astronomy, never human given-name or surname lists.
    pattern = re.compile(r"^([A-Z][a-z]+) ([A-Z][a-z]+) (\d{1,3})$")
    for holder in _book():
        m = pattern.match(holder["name"])
        assert m, f"name {holder['name']!r} must be token-token-number"
        assert m.group(1) in GIVEN_TOKENS
        assert m.group(2) in FAMILY_TOKENS


def test_contact_details_can_never_be_real():
    for holder in _book():
        phone = holder["contact"]["phone"]
        assert re.fullmatch(r"07700 900\d{3}", phone), (
            f"{phone!r} must sit in Ofcom's reserved fictional range")
        assert holder["contact"]["email"].endswith("@example.org")
        # ZZ is not an allocated UK postcode area.
        assert re.search(r"\bZZ\d{1,2} \d[A-Z]{2}$", holder["registered_address"])


def test_dob_is_valid_and_adult_at_as_of():
    for holder in _book():
        dob = date.fromisoformat(holder["dob"])  # raises if invalid
        age = (AS_OF - dob).days // 365
        assert 25 <= age <= 90


def test_policy_numbers_match_grammar_and_avoid_kb_samples():
    for holder in _book():
        policy_no = holder["policy"]["policy_no"]
        assert re.fullmatch(r"(LP|HB|RA)-\d{8}", policy_no)
        assert policy_no not in KB_SAMPLE_POLICY_NOS
        assert holder["policy"]["product"] in {
            "lifelong_protection", "horizon_bond", "retirement_account"}


def test_verification_is_never_pre_seeded():
    # Identity verification only ever happens through the gate at runtime —
    # a generated holder must not arrive "already verified".
    assert all(h["id_verified_level"] is None for h in _book())


def test_deterministic_per_seed_and_unique_throughout():
    # Arrange / Act
    a, b, c = _book(seed=4), _book(seed=4), _book(seed=5)

    # Assert — same seed reproduces byte-identical records; a new seed doesn't.
    assert a == b
    assert a != c
    for field in ("party_id", "name"):
        values = [h[field] for h in a]
        assert len(values) == len(set(values)), f"duplicate {field}"
    policy_nos = [h["policy"]["policy_no"] for h in a]
    assert len(policy_nos) == len(set(policy_nos))


def test_the_reserved_ranges_have_exactly_one_definition():
    # The world's cast (`world/identities/`) and this manifest must draw from
    # the same reserved ranges. Holding two copies is how they end up
    # disagreeing, and a drifted copy is how a "synthetic" detail stops being
    # reserved without anyone noticing.
    from world.identities import reserved

    assert GIVEN_TOKENS is reserved.GIVEN_TOKENS
    assert FAMILY_TOKENS is reserved.FAMILY_TOKENS


def test_the_committed_manifest_is_still_eighty_holders():
    # v4.5 changes no running behaviour: the seeded book keeps its 80 until
    # the world replaces it wholesale. The 200 belong to `data/world/`.
    from pathlib import Path

    manifest = (Path(__file__).resolve().parent.parent
                / "data" / "synthetic" / "policyholders.jsonl")
    assert len(manifest.read_text().splitlines()) == 80


def test_write_jsonl_round_trips(tmp_path):
    # Arrange
    book = _book(count=50)
    out = tmp_path / "holders.jsonl"

    # Act
    write_jsonl(book, out)
    back = [json.loads(line) for line in out.read_text().splitlines()]

    # Assert
    assert back == book
