"""The three **specimen** policies the rulebook itself documents.

A real insurer's product manual would never print a live customer's record, and
the corpus's three `III.4` records are the one part of it modelling something no
real company does. From v4.5 phase 3 they are labelled for what they are:
**specimens** — worked illustrations of a filled-in record, on numbers the book
cannot issue to anybody.

**The reserved block is what makes that structural rather than a promise.**
Policy numbers below ``GENERATED_CEILING`` are the world's to issue; numbers at
or above ``SPECIMEN_FLOOR`` are reserved for the corpus and can never be minted.
Before this the three numbers merely happened to miss the generator's range by
arithmetic accident, which is a property nobody stated and nothing checked.

They are still **parsed**, never typed out: change the corpus and these change
with it. Each ledgers exactly what its record states (D-CL-028); where a stated
value cannot be reached from the stated movements, the gap is one
explicitly-reasoned entry rather than an adjusted figure (D-CL-038).

The module keeps its name while the concept has moved on — every importer says
``anchors`` and renaming the file is not this task's business. The term to use
in new work is **specimen**.
"""

from __future__ import annotations

import re
from typing import Any

from src.records.interactions import Interaction
from src.records.models import Contact, Party
from src.records.sample_record import (
    SampleRecord,
    address_and_registered,
    load_sample_records,
    parse_date,
)
from src.records.specimen_products import (
    seed_horizon_bond,
    seed_lifelong_protection,
    seed_retirement_account,
    seed_stamp,
)

# ── the reserved block ───────────────────────────────────────────────────
#
# The eight digits of a policy number, split into two ranges that cannot
# overlap. The world's allocator issues from below the ceiling; the corpus
# documents specimens from above the floor. `world.lifetimes.allocation`
# imports these and refuses to mint into the reserved half, so "a specimen
# number cannot be generated" is enforced where numbers are made rather than
# asserted where they are read.
#
# The gap between the two is deliberate: it leaves room for the generator to
# grow past two hundred policies without ever approaching the reserved half.
GENERATED_CEILING = 20_099_999
SPECIMEN_FLOOR = 20_100_000

SPECIMEN_IDS = ("LP-20419876", "HB-40582213", "RA-77103428")
CHUNK_TO_PARTY = {"01-WOL:III.4": "PH-0001", "02-BOND:III.4": "PH-0002",
                  "03-PEN:III.4": "PH-0003"}


def digits_of(policy_no: str) -> int:
    """The eight digits behind the prefix, as a number."""
    return int(policy_no.split("-", 1)[1])


def is_specimen(policy_no: str) -> bool:
    """Is this number in the block reserved for the corpus's own records?"""
    return digits_of(policy_no) >= SPECIMEN_FLOOR


def _party_from(record: SampleRecord, party_id: str) -> Party:
    """The holder — named `holder:` on two records and `member:` on the pension."""
    name = record.get("holder") or record.require("member")
    address, registered = address_and_registered(record.require("address"))
    return Party(
        party_id=party_id, name=name, dob=record.require("dob"),
        registered_address=address,
        contact=Contact(phone="", email="", registered=registered),
        scottish_taxpayer=record.get("scottish_taxpayer", "").startswith("yes"))


def _add_recent_interactions(book: Any, record: SampleRecord, policy_no: str,
                             party_id: str, as_at: str) -> None:
    """`recent:` / `recent_transactions:` list dated contacts, semicolon-separated.

    The record says what happened and when, never through which channel, so the
    interaction carries no channel rather than a guessed one.
    """
    raw = record.get("recent") or record.get("recent_transactions")
    if not raw or raw.strip().lower() == "none":
        return
    digits = re.sub(r"\D", "", policy_no)
    for index, item in enumerate(part.strip() for part in raw.split(";")):
        if not item:
            continue
        book.add_interaction(Interaction(
            cn_ref=f"CN-{digits[:8]}{index:02d}", policy_no=policy_no,
            opened_at=f"{parse_date(item)}T00:00:00", caller_party_id=party_id,
            intent=item.split(" ", 1)[1] if " " in item else item,
            outcome="logged", closed_at=f"{parse_date(item)}T00:00:00"),
            **seed_stamp(as_at))


def _add_open_cases(book: Any, record: SampleRecord, policy_no: str,
                    as_at: str) -> None:
    """`open_cases:` names live `CW-` work, or says "none"."""
    from src.casework.models import Case

    raw = record.get("open_cases", "none")
    for cw_ref in re.findall(r"CW-\d{9}", raw):
        note = re.search(rf"{cw_ref}\s*\(([^)]*)\)", raw)
        book.add_case(Case(case_id=cw_ref, cw_ref=cw_ref, policy_no=policy_no,
                           request=note.group(1) if note else "open case",
                           status="pending_review", created_at=f"{as_at}T00:00:00"),
                      **seed_stamp(as_at))


def seed_specimens(book: Any, *, kb_dir: str = "data/kb", as_at: str) -> None:
    """Parse the three specimen records into ``book``."""
    records = load_sample_records(kb_dir)
    builders = {"01-WOL:III.4": seed_lifelong_protection,
                "02-BOND:III.4": seed_horizon_bond,
                "03-PEN:III.4": seed_retirement_account}
    for chunk_id, build in builders.items():
        record = records[chunk_id]
        party_id = CHUNK_TO_PARTY[chunk_id]
        policy_no = record.require("policy_no")
        if not is_specimen(policy_no):
            raise ValueError(
                f"{chunk_id}: {policy_no} is not in the reserved specimen block "
                f"(digits must be >= {SPECIMEN_FLOOR}) — a documented record on "
                f"a number the generator can issue would collide with a real "
                f"policy in the book")
        book.add_party(_party_from(record, party_id), **seed_stamp(as_at))
        build(book, record, party_id, as_at)
        _add_recent_interactions(book, record, policy_no, party_id, as_at)
        _add_open_cases(book, record, policy_no, as_at)
