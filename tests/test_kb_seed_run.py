"""A seed run end to end — fake client, fake embedder, zero live calls.

`test_kb_seed.py` proves the diff decides correctly. This file proves the run
acts on that decision: what gets embedded, what reaches the table, and what
survives a tombstone.

The sharpest assertion here is a negative one — re-seeding an untouched corpus
must make **no embedding call at all**. That is the property `content_hash`
exists for, and the only way to see it is to watch the embedder never get
invoked.
"""

from src.corpus.kb_parser import KbChunk, content_hash
from src.corpus.kb_seed import seed_kb_chunks
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


class FakeTable:
    def __init__(self, store, calls):
        self._store, self._calls = store, calls
        self._filter = None

    def select(self, columns):
        self._calls.append(("select", columns))
        return self

    def upsert(self, rows, **kwargs):
        self._calls.append(("upsert", kwargs.get("on_conflict")))
        for row in rows:
            self._store[row["chunk_id"]] = row
        return self

    def update(self, values):
        self._pending = values
        return self

    def eq(self, column, value):
        self._filter = (column, value)
        return self

    def execute(self):
        if self._filter:
            column, value = self._filter
            self._store[value].update(self._pending)
            self._calls.append(("tombstone", value))
            return type("R", (), {"data": []})()
        return type("R", (), {"data": list(self._store.values())})()


class FakeClient:
    def __init__(self, store=None):
        self.store = store if store is not None else {}
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return FakeTable(self.store, self.calls)


def _embedder(sink):
    def embed(texts):
        sink.extend(texts)
        return [[0.1] * 1536 for _ in texts]
    return embed


def test_a_first_run_embeds_and_upserts_every_embeddable_chunk():
    sink, client = [], FakeClient()

    result = seed_kb_chunks([_chunk("02-BOND:4.1"), _chunk("02-BOND:4.2")],
                            client, _embed=_embedder(sink))

    assert result.embedded == 2
    assert set(client.store) == {"02-BOND:4.1", "02-BOND:4.2"}
    assert ("upsert", "chunk_id") in client.calls


def test_what_is_embedded_is_heading_plus_body():
    sink, chunk = [], _chunk("02-BOND:4.1")
    seed_kb_chunks([chunk], FakeClient(), _embed=_embedder(sink))
    assert sink == [chunk.embed_text]


def test_a_second_run_over_an_untouched_corpus_embeds_nothing():
    # The headline property: re-seeding is free when nothing changed.
    chunks = [_chunk("02-BOND:4.1"), _chunk("02-BOND:4.2")]
    client = FakeClient()
    seed_kb_chunks(chunks, client, _embed=_embedder([]))

    sink = []
    result = seed_kb_chunks(chunks, client, _embed=_embedder(sink))

    assert result.embedded == 0
    assert result.skipped == 2
    assert sink == [], "no embedding call may be made for unchanged chunks"


def test_only_an_edited_chunk_is_re_embedded_on_a_second_run():
    client = FakeClient()
    seed_kb_chunks([_chunk("02-BOND:4.1", text="original"), _chunk("05-OPS:1")],
                   client, _embed=_embedder([]))

    sink = []
    result = seed_kb_chunks([_chunk("02-BOND:4.1", text="revised"), _chunk("05-OPS:1")],
                            client, _embed=_embedder(sink))

    assert result.embedded == 1 and result.skipped == 1
    assert client.store["02-BOND:4.1"]["version"] == 2
    assert client.store["05-OPS:1"]["version"] == 1


def test_a_disappeared_chunk_is_tombstoned_and_its_row_survives():
    client = FakeClient()
    seed_kb_chunks([_chunk("02-BOND:4.1"), _chunk("02-BOND:9.9")],
                   client, _embed=_embedder([]))

    result = seed_kb_chunks([_chunk("02-BOND:4.1")], client, _embed=_embedder([]))

    assert result.tombstoned == 1
    assert "02-BOND:9.9" in client.store, "the row must survive — citations resolve to it"
    assert client.store["02-BOND:9.9"]["superseded_by"] is not None


def test_a_sample_record_never_reaches_the_client():
    client = FakeClient()
    result = seed_kb_chunks([_chunk("01-WOL:III.4", type="sample_record")],
                            client, _embed=_embedder([]))
    assert result.embedded == 0
    assert client.store == {}


def test_the_result_reports_what_actually_happened():
    client = FakeClient()
    result = seed_kb_chunks([_chunk("02-BOND:4.1"),
                             _chunk("01-WOL:III.4", type="sample_record")],
                            client, _embed=_embedder([]))
    assert (result.embedded, result.skipped, result.tombstoned, result.withheld) == (1, 0, 0, 1)
