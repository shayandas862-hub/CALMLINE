"""Embedding wrapper: passage prefix, correct model, order preserved, batched."""

from src import constants
from src.corpus.embed import embed


class FakeEmbeddings:
    def __init__(self, sink):
        self._sink = sink

    def create(self, *, model, input):
        self._sink["model"] = model
        self._sink["inputs"] = list(input)
        # echo back a tiny deterministic vector per input, order preserved
        data = [type("E", (), {"embedding": [float(len(t)), 0.0, 1.0]}) for t in input]
        return type("R", (), {"data": data})


class FakeClient:
    def __init__(self, sink):
        self.embeddings = FakeEmbeddings(sink)


def test_returns_empty_for_no_texts():
    assert embed([], _client=FakeClient({})) == []


def test_prefixes_with_passage_and_uses_the_contract_model():
    sink = {}
    embed(["hello clause"], _client=FakeClient(sink))
    assert sink["model"] == constants.EMBED_MODEL
    assert sink["inputs"] == [constants.PASSAGE_PREFIX + "hello clause"]


def test_order_is_preserved():
    vectors = embed(["a", "bbb"], _client=FakeClient({}))
    # fake encodes vector[0] as len(prefixed text); prefix len is constant
    assert vectors[0][0] < vectors[1][0]


def test_batches_over_100_without_dropping():
    texts = [f"clause {i}" for i in range(230)]
    vectors = embed(texts, _client=FakeClient({}))
    assert len(vectors) == 230
