"""v4 phase 6 · Task 4 — the corpus describes itself, away from the ops screen.

`corpus_facts` used to live in `src/opsview/lenses.py`, which meant the eval
runner would have had to import the ops screen to learn the corpus version.
Moved beside the corpus it reads; the lenses take the facts as input and never
touch the KB.

It had no direct test before the move — it was only ever exercised through the
console app. Giving it one is the point of moving it.
"""

from types import SimpleNamespace

from src.corpus.facts import corpus_facts, kb_version


def _chunk(chunk_id, version=1, style="cite_source"):
    return SimpleNamespace(chunk_id=chunk_id, version=version, citation_style=style)


def test_it_reports_every_chunk_and_the_version_it_is_at():
    facts = corpus_facts([_chunk("02-BOND:4.9", 3), _chunk("01-WOL:3.10")])
    assert facts["current_versions"] == {"02-BOND:4.9": 3, "01-WOL:3.10": 1}
    assert facts["corpus_clauses"] == 2


def test_it_reports_how_each_chunk_must_be_cited():
    facts = corpus_facts([_chunk("02-BOND:4.9", style="cite_effective_date")])
    assert facts["citation_styles"] == {"02-BOND:4.9": "cite_effective_date"}


def test_the_version_does_not_depend_on_the_order_chunks_arrive_in():
    a = corpus_facts([_chunk("A"), _chunk("B")])["kb_version"]
    b = corpus_facts([_chunk("B"), _chunk("A")])["kb_version"]
    assert a == b


def test_bumping_one_chunk_changes_the_corpus_version():
    # This is the whole reason it is a content hash rather than a number: it
    # moves exactly when the corpus moves, and never when it does not.
    before = corpus_facts([_chunk("A", 1)])["kb_version"]
    after = corpus_facts([_chunk("A", 2)])["kb_version"]
    assert before != after


def test_adding_a_chunk_changes_the_corpus_version():
    before = corpus_facts([_chunk("A")])["kb_version"]
    after = corpus_facts([_chunk("A"), _chunk("B")])["kb_version"]
    assert before != after


def test_re_reading_the_same_corpus_gives_the_same_version():
    chunks = [_chunk("A", 2), _chunk("B", 1)]
    assert corpus_facts(chunks)["kb_version"] == corpus_facts(chunks)["kb_version"]


def test_the_version_is_short_enough_to_read_on_a_screen():
    assert len(kb_version({"A": 1})) == 12


def test_an_empty_corpus_still_has_a_version():
    # Not None: an empty corpus is a fact about the corpus, not a missing one.
    facts = corpus_facts([])
    assert facts["corpus_clauses"] == 0 and len(facts["kb_version"]) == 12
