"""The KB parser — one `*meta:`-tagged heading is one chunk (v4 phase 1, task 3).

This is the pipeline the whole system cites through. The old clause parser
returned **zero** chunks from `data/kb/` and said nothing about it, which is the
failure this replaces: everything here either produces a chunk or raises.

Two rules carry design weight:
  * **Atomicity keys off the `type` metadata, never off pipe-table detection.**
    Prose that happens to contain a table is still splittable prose; a chunk
    typed `table` is atomic whether or not it renders as pipes.
  * **`type=sample_record` chunks are parsed but never embedded** (AD-CL-023) —
    they seed the book in phase 2. Facts come from the system of record, so no
    record may ever sit in the retrieval index to be cited stale.
"""

from pathlib import Path

import pytest

from src.corpus.kb_parser import (
    ATOMIC_TYPES,
    KbParseError,
    NON_EMBEDDED_TYPES,
    content_hash,
    embed_text,
    parse_document,
    parse_kb,
)
from src.corpus.provenance import CITE_SOURCE, MIXED_EXPLAIN, ProvenanceError

KB = Path(__file__).resolve().parent.parent / "data" / "kb"

SAMPLE = """# DOCUMENT 2 — ONSHORE INVESTMENT BOND (PRODUCT MASTER) v2
*meta: doc=02-BOND | sec=frontmatter | aud=all | type=caveats | data=mixed*
Front matter body.

# PART I — PRODUCT

## 4. Tax treatment (real UK rules)
*meta: doc=02-BOND | sec=4 | aud=all | type=overview | data=real*
The tax overview.

### 4.1 Fund taxation and the 20% credit
*meta: doc=02-BOND | sec=4.1 | aud=all | type=tax_rule | data=real*
Life funds pay corporation tax on income and gains.

---

## 5. HOW WE SERVICE IT
*meta: doc=02-BOND | sec=5 | aud=back_office | type=procedure | data=fictional*
Servicing runs through the case system.
"""


def _by_id(chunks):
    return {c.chunk_id: c for c in chunks}


# --- one tagged heading, one chunk ----------------------------------------

def test_each_meta_tagged_heading_becomes_one_chunk():
    # Act
    chunks = parse_document(SAMPLE, source_file="02_bond.md")

    # Assert — four tagged headings; "PART I — PRODUCT" carries no meta line
    assert [c.chunk_id for c in chunks] == [
        "02-BOND:frontmatter", "02-BOND:4", "02-BOND:4.1", "02-BOND:5",
    ]


def test_a_container_heading_emits_nothing():
    chunks = parse_document(SAMPLE, source_file="02_bond.md")
    assert not [c for c in chunks if c.heading == "PART I — PRODUCT"]


def test_chunk_id_is_doc_colon_sec():
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert chunk.doc == "02-BOND"
    assert chunk.sec == "4.1"
    assert chunk.chunk_id == "02-BOND:4.1"


def test_metadata_fields_are_carried_through():
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:5"]
    assert chunk.aud == "back_office"
    assert chunk.type == "procedure"
    assert chunk.source_file == "02_bond.md"
    assert chunk.version == 1


# --- heading_path ---------------------------------------------------------

def test_heading_path_is_the_ancestor_chain_including_containers():
    # A container heading owns no chunk but still locates its descendants.
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert chunk.heading_path == (
        "PART I — PRODUCT > 4. Tax treatment (real UK rules) "
        "> 4.1 Fund taxation and the 20% credit"
    )


def test_a_same_level_heading_replaces_its_predecessor_in_the_path():
    # "# PART I" is level 1, like "# DOCUMENT 2" before it — it replaces, not nests.
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4"]
    assert chunk.heading_path.startswith("PART I — PRODUCT > ")
    assert "DOCUMENT 2" not in chunk.heading_path


def test_a_top_level_chunks_path_is_its_own_heading():
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:frontmatter"]
    assert chunk.heading_path == (
        "DOCUMENT 2 — ONSHORE INVESTMENT BOND (PRODUCT MASTER) v2"
    )


# --- text -----------------------------------------------------------------

def test_text_is_the_body_without_the_meta_line():
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert chunk.text == "Life funds pay corporation tax on income and gains."
    assert "meta:" not in chunk.text


def test_text_stops_at_the_next_heading_and_drops_the_section_rule():
    # The KB separates sections with "---"; that is layout, not content.
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert "---" not in chunk.text
    assert "HOW WE SERVICE IT" not in chunk.text


def test_token_estimate_approximates_four_characters_per_token():
    chunk = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert chunk.token_estimate == len(chunk.text) // 4
    assert chunk.token_estimate > 0


# --- content_hash ---------------------------------------------------------

def test_content_hash_is_stable_across_parses():
    first = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    second = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))["02-BOND:4.1"]
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 16


def test_content_hash_changes_when_the_body_changes():
    # The hash is what incremental re-embedding diffs by (KB README §5).
    edited = SAMPLE.replace("corporation tax on income", "corporation tax on profits")
    before = _by_id(parse_document(SAMPLE, source_file="f.md"))["02-BOND:4.1"]
    after = _by_id(parse_document(edited, source_file="f.md"))["02-BOND:4.1"]
    assert before.content_hash != after.content_hash


def test_content_hash_changes_when_the_heading_is_reworded():
    # A citation displays the heading, so a heading edit must trigger a re-embed.
    edited = SAMPLE.replace("4.1 Fund taxation and the 20% credit",
                            "4.1 Fund taxation and the notional credit")
    before = _by_id(parse_document(SAMPLE, source_file="f.md"))["02-BOND:4.1"]
    after = _by_id(parse_document(edited, source_file="f.md"))["02-BOND:4.1"]
    assert before.content_hash != after.content_hash


def test_the_content_hash_is_the_hash_of_what_gets_embedded():
    # Keeps the re-embedding diff key honest: same embedded string → same hash,
    # so the seeding script skips exactly the chunks it should.
    chunk = _by_id(parse_document(SAMPLE, source_file="f.md"))["02-BOND:4.1"]
    assert chunk.content_hash == content_hash(chunk.heading, chunk.text)
    assert chunk.embed_text == embed_text(chunk.heading, chunk.text)
    assert chunk.embed_text.startswith(chunk.heading)


def test_the_chunk_id_survives_a_rewording():
    # chunk_id derives from the section number, never from position or text.
    edited = SAMPLE.replace("corporation tax on income", "corporation tax on profits")
    assert "02-BOND:4.1" in _by_id(parse_document(edited, source_file="f.md"))


# --- provenance -----------------------------------------------------------

def test_provenance_and_citation_style_are_attached():
    chunks = _by_id(parse_document(SAMPLE, source_file="02_bond.md"))
    assert chunks["02-BOND:4.1"].citation_style == CITE_SOURCE
    assert chunks["02-BOND:frontmatter"].citation_style == MIXED_EXPLAIN
    assert chunks["02-BOND:4.1"].provenance.base == "real"


def test_an_unparseable_provenance_raises():
    broken = (
        "## 1. Thing\n"
        "*meta: doc=01-WOL | sec=1 | aud=all | type=overview | data=invented*\n"
        "Body.\n"
    )
    with pytest.raises(ProvenanceError):
        parse_document(broken, source_file="f.md")


# --- embedding boundary (AD-CL-023) --------------------------------------

def test_a_sample_record_is_parsed_but_not_embedded():
    doc = (
        "### III.4 Synthetic policy record\n"
        "*meta: doc=01-WOL | sec=III.4 | aud=all | type=sample_record | data=fictional*\n"
        "Policy LP-20419876, sum assured 50000.\n"
    )
    chunk = parse_document(doc, source_file="f.md")[0]
    assert chunk.chunk_id == "01-WOL:III.4"
    assert chunk.text, "it is parsed — phase 2 seeds the book from it"
    assert chunk.embed is False, "no record may ever enter the retrieval index"


def test_every_other_type_is_embedded():
    chunks = parse_document(SAMPLE, source_file="02_bond.md")
    assert all(c.embed for c in chunks)
    assert NON_EMBEDDED_TYPES == frozenset({"sample_record"})


# --- atomicity keys off type, never off pipe detection -------------------

def test_atomicity_comes_from_the_type_metadata():
    doc = (
        "### 15 SLA table\n"
        "*meta: doc=05-OPS | sec=15 | aud=all | type=table | data=fictional*\n"
        "Prose describing service levels, with no pipe characters at all.\n"
    )
    chunk = parse_document(doc, source_file="f.md")[0]
    assert chunk.atomic is True, "type=table is atomic regardless of rendering"


def test_a_pipe_table_inside_prose_does_not_make_the_chunk_atomic():
    doc = (
        "### 2.2 The master inbound flow\n"
        "*meta: doc=05-OPS | sec=2.2 | aud=back_office | type=procedure | data=mixed*\n"
        "Steps:\n"
        "| step | action |\n"
        "|---|---|\n"
        "| 1 | capture the contact |\n"
    )
    chunk = parse_document(doc, source_file="f.md")[0]
    assert chunk.atomic is False, "atomicity is declared, not sniffed"


def test_the_atomic_types_are_the_four_the_kb_declares():
    assert ATOMIC_TYPES == frozenset({"table", "sources", "data_dictionary", "case_study"})


# --- loud failure on a broken meta line ----------------------------------

@pytest.mark.parametrize("meta", [
    "*meta: sec=1 | aud=all | type=overview | data=real*",       # no doc
    "*meta: doc=01-WOL | aud=all | type=overview | data=real*",   # no sec
    "*meta: doc=01-WOL | sec=1 | type=overview | data=real*",     # no aud
    "*meta: doc=01-WOL | sec=1 | aud=all | data=real*",            # no type
    "*meta: doc=01-WOL | sec=1 | aud=all | type=overview*",        # no data
])
def test_a_meta_line_missing_a_required_field_raises(meta):
    with pytest.raises(KbParseError):
        parse_document(f"## 1. Thing\n{meta}\nBody.\n", source_file="f.md")


def test_the_parse_error_names_the_file_and_the_heading():
    broken = "## 1. Thing\n*meta: doc=01-WOL | sec=1 | aud=all | type=overview*\nBody.\n"
    with pytest.raises(KbParseError, match="bond.md"):
        parse_document(broken, source_file="bond.md")
