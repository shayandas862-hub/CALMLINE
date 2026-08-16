"""The committed Aldercrest corpus — the shape everything downstream cites.

Where `test_kb_parser.py` tests the parser's mechanics on fixtures, this file
asserts facts about `data/kb/` as committed: how many chunks it yields, that
every id is unique, and — the one that carries the most weight — that **no
sample record ever reaches the retrieval index**.

That last point is the two-store boundary made structural (AD-CL-023). Facts
(names, valuations, transactions) come from the system of record; rules come
from the knowledge base. The agent cannot cite a stale policy record because, by
construction, there is no policy record in the index to cite.
"""

from pathlib import Path

from src.corpus.kb_parser import parse_kb
from src.corpus.provenance import CITATION_STYLES

KB = Path(__file__).resolve().parent.parent / "data" / "kb"

# The seven documents of the knowledge base (`data/kb/README.md` §1).
DOCS = {"01-WOL", "02-BOND", "03-PEN", "04-FCA", "05-OPS", "06-RAGOPS", "07-RUNBOOK"}


def corpus():
    return parse_kb(KB)


# --- size and keys --------------------------------------------------------

def test_the_knowledge_base_parses_to_441_chunks():
    assert len(corpus()) == 441


def test_every_chunk_id_is_unique():
    ids = [c.chunk_id for c in corpus()]
    duplicates = sorted({cid for cid in ids if ids.count(cid) > 1})
    assert duplicates == [], f"a collision leaves a chunk uncitable: {duplicates}"


def test_all_seven_documents_contribute_chunks():
    assert {c.doc for c in corpus()} == DOCS


def test_the_kb_readme_is_not_part_of_the_corpus():
    # README.md documents the metadata contract *by example*; those illustrative
    # meta lines must never be retrievable as though they were corpus.
    assert not [c for c in corpus() if c.source_file == "README.md"]


# --- the two-store boundary, enforced at ingestion (AD-CL-023) -----------

def test_exactly_three_chunks_are_withheld_from_embedding():
    withheld = [c for c in corpus() if not c.embed]
    assert [c.chunk_id for c in withheld] == [
        "01-WOL:III.4", "02-BOND:III.4", "03-PEN:III.4",
    ]


def test_the_withheld_chunks_are_the_sample_records():
    withheld = [c for c in corpus() if not c.embed]
    assert all(c.type == "sample_record" for c in withheld)


def test_no_sample_record_is_embeddable():
    # Stated from the other direction: whatever else changes, a record must not
    # become retrievable. Phase 2 seeds the book from these three chunks.
    assert not [c for c in corpus() if c.type == "sample_record" and c.embed]


def test_everything_that_is_not_a_sample_record_is_embedded():
    assert all(c.embed for c in corpus() if c.type != "sample_record")


# --- every chunk is citable ----------------------------------------------

def test_every_chunk_has_something_to_embed():
    # Not "has a body": 15 chunks are section headers whose prose lives in their
    # subsections. The invariant is that nothing empty reaches the embedder.
    empty = [c.chunk_id for c in corpus() if not c.embed_text]
    assert empty == [], f"nothing to embed for: {empty}"


def test_the_heading_only_section_headers_are_a_known_corpus_property():
    # e.g. "05-OPS:1 PURPOSE AND SCOPE", detailed by 1.1 … 1.4. Pinned so the
    # count is a deliberate property, not a surprise rediscovered later.
    heading_only = [c for c in corpus() if not c.text.strip()]
    assert len(heading_only) == 15
    assert "05-OPS:1" in {c.chunk_id for c in heading_only}
    assert all(c.embed_text == c.heading for c in heading_only)


def test_every_chunk_locates_itself_with_a_heading_path():
    pathless = [c.chunk_id for c in corpus() if not c.heading_path]
    assert pathless == []


def test_every_chunk_resolves_to_a_citation_style():
    # No chunk may be retrieved without the system knowing how to attribute it.
    assert all(c.citation_style in CITATION_STYLES for c in corpus())


def test_chunks_sharing_a_content_hash_share_their_content():
    # Duplicate hashes are legitimate — identity and data-protection rules are
    # deliberately repeated per product so each chunk is self-contained — but
    # they must be genuinely identical content, never a hashing collision.
    by_hash: dict[str, set[str]] = {}
    for chunk in corpus():
        by_hash.setdefault(chunk.content_hash, set()).add(chunk.embed_text)
    for texts in by_hash.values():
        assert len(texts) == 1, "same hash, different content — hashing is broken"
