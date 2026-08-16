"""The two ways to build a book — the generator, and the world.

**`build_seed_book`** is the generator: Aldercrest's three specimen policies
plus 80 synthetic holders. Nothing in it is typed out. The specimens are
**parsed** from the KB's own three `III.4` sample records, and the synthetic
book's history is **derived** at seed time from a fixed RNG seed plus the
injected as-of date. Change the KB and the book changes with it; run it twice
and get the same book both times.

The as-of date defaults to the knowledge base's own "as at" (13 July 2026) —
a property of the corpus, not of the run, so the book is the same whenever it
is built. Nothing here reads the wall clock.

**`build_world_book`** is v4.5's: the two hundred policies of `data/world/`,
replayed from committed files. It is what `run_console.py` serves. The two
coexist deliberately — *the dataset is what the console uses; the generator is
what tests use* — because 1,800 tests build books with the generator and this
phase is not a rewrite of the suite.
"""

from __future__ import annotations

from src.corpus.kb_validate import KB_DATE
from src.records.anchors import SPECIMEN_IDS, seed_specimens
from src.records.store import InMemoryRecordBook
from src.records.synthetic_history import MANIFEST_PATH, seed_synthetics
from src.records.world_seed import build_world_book

SEED_AS_AT = KB_DATE.isoformat()

__all__ = ["SEED_AS_AT", "SPECIMEN_IDS", "build_seed_book", "build_world_book"]


def build_seed_book(*, as_at: str = SEED_AS_AT, kb_dir: str = "data/kb",
                    manifest_path: str = MANIFEST_PATH,
                    with_synthetics: bool = True) -> InMemoryRecordBook:
    """Return the in-memory book: the three KB specimens, then the wider book.

    ``with_synthetics=False`` gives just the specimens — useful when a test
    wants the three records the KB actually documents and nothing else.
    """
    book = InMemoryRecordBook()
    seed_specimens(book, kb_dir=kb_dir, as_at=as_at)
    if with_synthetics:
        seed_synthetics(book, manifest_path=manifest_path, as_at=as_at)
    return book
