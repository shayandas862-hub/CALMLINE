"""Incremental seeding — embed only what changed (`data/kb/README.md` §5).

You never rebuild the corpus. Re-running the seed diffs the parsed chunks
against what the index already holds, by `content_hash`:

    hash unchanged  -> skip, no embedding call
    hash changed    -> re-embed, upsert the SAME chunk_id, version + 1
    new chunk_id    -> embed and insert at version 1
    id disappeared  -> TOMBSTONE (set superseded_by), never a silent drop

The rule with teeth is the last one: a chunk that vanishes from the markdown
must remain resolvable, because answers already given cite it. Dropping the row
would turn a real citation into a dangling reference.

Sample records are excluded from the index entirely — not merely left without an
embedding. The `tsv` column is `generated always`, so a row present with a null
embedding would still be reachable by keyword search, which is exactly the
two-store leak AD-CL-023 exists to prevent.
"""

from src.corpus.kb_parser import KbChunk, content_hash
from src.corpus.kb_seed import build_row, plan_seed
from src.corpus.provenance import parse_provenance


def _chunk(chunk_id, *, text="body text", heading="4.1 A heading",
           type="tax_rule", aud="all", data="real"):
    doc, _, sec = chunk_id.partition(":")
    return KbChunk(
        chunk_id=chunk_id, doc=doc, sec=sec, aud=aud, type=type,
        heading=heading, heading_path=f"PART I > {heading}", text=text,
        token_estimate=len(text) // 4, content_hash=content_hash(heading, text),
        provenance=parse_provenance(data),
        embed=type != "sample_record", atomic=False, source_file="f.md",
    )


def _indexed(chunk, *, version=1):
    """What a row already in kb_chunks looks like to the planner."""
    return {"content_hash": chunk.content_hash, "version": version}


# --- a fresh index --------------------------------------------------------

def test_everything_embeddable_is_seeded_into_an_empty_index():
    chunks = [_chunk("02-BOND:4.1"), _chunk("02-BOND:4.2")]

    plan = plan_seed(chunks, existing={})

    assert [c.chunk_id for c in plan.to_embed] == ["02-BOND:4.1", "02-BOND:4.2"]
    assert plan.unchanged == ()
    assert plan.to_tombstone == ()


def test_a_new_chunk_starts_at_version_one():
    plan = plan_seed([_chunk("02-BOND:4.1")], existing={})
    assert plan.version_for("02-BOND:4.1") == 1


# --- the hash diff --------------------------------------------------------

def test_an_unchanged_hash_is_skipped_entirely():
    # The whole point: re-seeding an untouched corpus costs nothing.
    chunk = _chunk("02-BOND:4.1")

    plan = plan_seed([chunk], existing={chunk.chunk_id: _indexed(chunk)})

    assert plan.to_embed == ()
    assert [c.chunk_id for c in plan.unchanged] == ["02-BOND:4.1"]


def test_a_changed_hash_is_re_embedded():
    before = _chunk("02-BOND:4.1", text="the original wording")
    after = _chunk("02-BOND:4.1", text="the revised wording")

    plan = plan_seed([after], existing={before.chunk_id: _indexed(before)})

    assert [c.chunk_id for c in plan.to_embed] == ["02-BOND:4.1"]


def test_a_changed_chunk_keeps_its_id_and_bumps_its_version():
    before = _chunk("02-BOND:4.1", text="the original wording")
    after = _chunk("02-BOND:4.1", text="the revised wording")

    plan = plan_seed([after], existing={before.chunk_id: _indexed(before, version=3)})

    assert plan.version_for("02-BOND:4.1") == 4


def test_only_the_touched_chunks_are_re_embedded():
    # "A tax-rate change touches 2–5 chunks: seconds of re-embedding, not a
    # corpus rebuild" — data/kb/README.md §5.
    unchanged = [_chunk(f"05-OPS:{n}") for n in range(1, 6)]
    edited = _chunk("02-BOND:4.1", text="revised")
    existing = {c.chunk_id: _indexed(c) for c in unchanged}
    existing["02-BOND:4.1"] = _indexed(_chunk("02-BOND:4.1", text="original"))

    plan = plan_seed(unchanged + [edited], existing=existing)

    assert [c.chunk_id for c in plan.to_embed] == ["02-BOND:4.1"]
    assert len(plan.unchanged) == 5


# --- tombstoning ----------------------------------------------------------

def test_a_disappeared_chunk_is_tombstoned_not_dropped():
    # Answers already given cite it; dropping the row dangles the citation.
    kept = _chunk("02-BOND:4.1")
    gone = _chunk("02-BOND:9.9")
    existing = {kept.chunk_id: _indexed(kept), gone.chunk_id: _indexed(gone)}

    plan = plan_seed([kept], existing=existing)

    assert plan.to_tombstone == ("02-BOND:9.9",)


def test_nothing_is_tombstoned_when_the_corpus_only_grows():
    existing = {"02-BOND:4.1": _indexed(_chunk("02-BOND:4.1"))}
    plan = plan_seed([_chunk("02-BOND:4.1"), _chunk("02-BOND:4.2")], existing=existing)
    assert plan.to_tombstone == ()


def test_tombstoning_is_deterministic_in_id_order():
    existing = {cid: _indexed(_chunk(cid))
                for cid in ("05-OPS:3", "01-WOL:1", "02-BOND:2")}
    plan = plan_seed([], existing=existing)
    assert plan.to_tombstone == ("01-WOL:1", "02-BOND:2", "05-OPS:3")


# --- the two-store boundary (AD-CL-023) ----------------------------------

def test_a_sample_record_is_never_embedded():
    chunks = [_chunk("01-WOL:III.4", type="sample_record"), _chunk("02-BOND:4.1")]

    plan = plan_seed(chunks, existing={})

    assert [c.chunk_id for c in plan.to_embed] == ["02-BOND:4.1"]
    assert [c.chunk_id for c in plan.withheld] == ["01-WOL:III.4"]


def test_a_sample_record_is_not_written_to_the_index_at_all():
    # Not "inserted without an embedding": kb_chunks.tsv is `generated always`,
    # so a row present at all is reachable by keyword search.
    plan = plan_seed([_chunk("01-WOL:III.4", type="sample_record")], existing={})
    assert plan.to_embed == ()
    assert plan.unchanged == ()
    assert plan.to_tombstone == ()


def test_a_sample_record_already_in_the_index_is_tombstoned_out():
    # If an earlier seed leaked one in, the next seed removes it from retrieval.
    record = _chunk("01-WOL:III.4", type="sample_record")
    plan = plan_seed([record], existing={record.chunk_id: _indexed(record)})
    assert plan.to_tombstone == ("01-WOL:III.4",)


# --- the row that reaches Postgres ---------------------------------------

def test_a_row_carries_the_filterable_metadata():
    chunk = _chunk("02-BOND:4.1", aud="back_office", type="procedure")

    row = build_row(chunk, vector=[0.1] * 1536, version=1)

    assert row["chunk_id"] == "02-BOND:4.1"
    assert row["doc"] == "02-BOND" and row["sec"] == "4.1"
    assert row["aud"] == "back_office" and row["type"] == "procedure"


def test_a_row_carries_provenance_and_its_derived_style():
    row = build_row(_chunk("02-BOND:4.6", data="real (not yet in force)"),
                    vector=[0.0] * 1536, version=1)
    assert row["provenance"] == "real (not yet in force)"
    assert row["citation_style"] == "effective_date_required"


def test_a_row_carries_the_change_control_fields():
    chunk = _chunk("02-BOND:4.1")
    row = build_row(chunk, vector=[0.0] * 1536, version=7)
    assert row["content_hash"] == chunk.content_hash
    assert row["version"] == 7


def test_the_embedded_vector_is_stored():
    row = build_row(_chunk("02-BOND:4.1"), vector=[0.5] * 1536, version=1)
    assert row["embedding"] == [0.5] * 1536


def test_the_row_text_is_what_was_embedded():
    # tsv and the vector must describe the same string, or keyword and semantic
    # search disagree about what the chunk says.
    chunk = _chunk("02-BOND:4.1")
    row = build_row(chunk, vector=[0.0] * 1536, version=1)
    assert row["heading"] == chunk.heading
    assert row["text"] == chunk.text
    assert f"{row['heading']}\n{row['text']}".strip() == chunk.embed_text


def test_a_row_rejects_a_vector_of_the_wrong_dimension():
    # A silent dimension mismatch fails at insert time with a Postgres error
    # nobody reads; fail here instead, naming both numbers.
    try:
        build_row(_chunk("02-BOND:4.1"), vector=[0.0] * 768, version=1)
    except ValueError as error:
        assert "768" in str(error) and "1536" in str(error)
        return
    raise AssertionError("a wrong-dimension vector must raise")
