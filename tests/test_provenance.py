"""`data=` provenance → structured aspects + a derived citation style (AD-CL-027).

The KB marks every chunk's provenance in its `*meta:` line. That marking is what
decides how an answer may cite the chunk: real law gets a source URL, an
Aldercrest invention gets labelled as an operating standard, a chunk that is
partly both must explain which is which, and a rule legislated but not yet in
force must state its effective date.

The grammar is deliberately narrow and **fails loudly** — an unrecognised
pattern raises rather than defaulting to a citation style, because a wrong
default here is a mis-citation in a regulated answer.
"""

import re
from pathlib import Path

import pytest

from src.corpus.provenance import (
    ALDERCREST_STANDARD,
    CITATION_STYLES,
    CITE_SOURCE,
    EFFECTIVE_DATE_REQUIRED,
    MIXED_EXPLAIN,
    ProvenanceError,
    parse_provenance,
)

KB = Path(__file__).resolve().parent.parent / "data" / "kb"

# Every distinct `data=` value in data/kb/ as committed. The spec requires all
# sixteen to parse; this list is the observed set, so it doubles as the grammar's
# specification.
OBSERVED = [
    "real",
    "fictional",
    "mixed",
    "real (not yet in force)",
    "fictional (rules real)",
    "real (figures fictional)",
    "fictional (aligned to UK market practice)",
    "fictional (lawful-basis anchored)",
    "real (structure) / fictional (terms)",
    "real (law) / fictional (process)",
    "real (duty) / fictional (process)",
    "real (framework) / fictional (wording)",
    "real (framework) / fictional (tolerances)",
    "real (mechanism) / fictional (thresholds)",
    "real (scheme) / fictional (thresholds)",
    "fictional (operational) / real (rail behaviour)",
]


def test_the_observed_set_is_the_sixteen_the_card_names():
    assert len(OBSERVED) == 16


@pytest.mark.parametrize("value", OBSERVED)
def test_every_observed_value_parses(value):
    # Act
    provenance = parse_provenance(value)

    # Assert
    assert provenance.raw == value
    assert provenance.aspects, "every value yields at least one aspect"
    assert provenance.citation_style in CITATION_STYLES


# --- structure ------------------------------------------------------------

def test_a_bare_base_has_one_aspect_and_no_note():
    # Act
    provenance = parse_provenance("real")

    # Assert
    assert provenance.base == "real"
    assert provenance.note is None
    assert [(a.base, a.note) for a in provenance.aspects] == [("real", None)]


def test_a_parenthetical_becomes_the_note():
    # Act
    provenance = parse_provenance("real (not yet in force)")

    # Assert
    assert provenance.base == "real"
    assert provenance.note == "not yet in force"
    assert len(provenance.aspects) == 1


def test_a_slash_splits_into_ordered_aspects():
    # Act
    provenance = parse_provenance("real (structure) / fictional (terms)")

    # Assert — order is meaningful: the leading aspect is the chunk's base
    assert [(a.base, a.note) for a in provenance.aspects] == [
        ("real", "structure"),
        ("fictional", "terms"),
    ]
    assert provenance.base == "real"
    assert provenance.note == "structure"


def test_surrounding_whitespace_is_tolerated():
    assert parse_provenance("  real  ").base == "real"
    assert parse_provenance("real (law)  /  fictional (process)").aspects[1].note == "process"


# --- the derived citation style -------------------------------------------

def test_real_alone_cites_the_source():
    assert parse_provenance("real").citation_style == CITE_SOURCE


def test_fictional_alone_is_labelled_an_aldercrest_standard():
    assert parse_provenance("fictional").citation_style == ALDERCREST_STANDARD


def test_mixed_must_explain_which_part_is_which():
    assert parse_provenance("mixed").citation_style == MIXED_EXPLAIN


def test_not_yet_in_force_requires_the_effective_date():
    assert parse_provenance("real (not yet in force)").citation_style == (
        EFFECTIVE_DATE_REQUIRED
    )


@pytest.mark.parametrize("value", [
    "real (structure) / fictional (terms)",
    "fictional (operational) / real (rail behaviour)",
    "real (mechanism) / fictional (thresholds)",
])
def test_a_real_and_a_fictional_aspect_together_must_explain(value):
    assert parse_provenance(value).citation_style == MIXED_EXPLAIN


@pytest.mark.parametrize("value", ["fictional (rules real)", "real (figures fictional)"])
def test_a_note_naming_the_opposite_provenance_must_explain(value):
    # "fictional (rules real)" is a mixed claim written as one aspect — the
    # answer still has to say which half is which.
    assert parse_provenance(value).citation_style == MIXED_EXPLAIN


@pytest.mark.parametrize("value", [
    "fictional (aligned to UK market practice)",
    "fictional (lawful-basis anchored)",
])
def test_a_qualifying_note_that_claims_nothing_real_stays_an_aldercrest_standard(value):
    assert parse_provenance(value).citation_style == ALDERCREST_STANDARD


def test_an_unseen_in_force_wording_still_requires_the_effective_date():
    # Guards the correctness risk: a future variant must not silently degrade
    # to cite_source and drop the effective date from the answer.
    assert parse_provenance("real (not in force until 2028)").citation_style == (
        EFFECTIVE_DATE_REQUIRED
    )


# --- loud failure ---------------------------------------------------------

@pytest.mark.parametrize("value", [
    "",
    "   ",
    "invented",
    "REAL",                      # the vocabulary is lower-case
    "real fictional",            # two bases, no separator
    "real (unclosed",
    "real ()",                   # an empty note says nothing
    "real (a (nested) note)",
    "real (law) / ",             # a trailing empty aspect
    "/ real",
    "real (law) extra",
    "probably real",
])
def test_an_unknown_pattern_raises(value):
    with pytest.raises(ProvenanceError):
        parse_provenance(value)


def test_the_error_names_the_offending_value():
    with pytest.raises(ProvenanceError, match="invented"):
        parse_provenance("invented")


# --- against the committed corpus ----------------------------------------

def test_every_data_value_in_the_knowledge_base_parses():
    # Arrange — read the `data=` field straight out of every meta line
    pattern = re.compile(r"^\*meta:.*\bdata=(?P<data>[^|*]+?)\s*\*$")
    values: set[str] = set()
    for md in sorted(KB.glob("*.md")):
        if md.name == "README.md":
            continue
        for line in md.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line.strip())
            if match:
                values.add(match.group("data"))

    # Assert — the corpus holds exactly the observed set, and all of it parses
    assert values == set(OBSERVED)
    for value in sorted(values):
        assert parse_provenance(value).citation_style in CITATION_STYLES
