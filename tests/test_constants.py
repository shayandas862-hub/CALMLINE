"""The single source of truth for the embedding contract.

The vendored RAG pipeline duplicated the model name and dimension across two
files (a known landmine). CalmLine defines them exactly once; everything —
migration, embedder, search — must read from here.
"""

from src import constants


def test_embedding_model_and_dimension():
    assert constants.EMBED_MODEL == "text-embedding-3-small"
    assert constants.EMBED_DIM == 1536


def test_asymmetric_prefixes_are_load_bearing():
    # The vendored pipeline embeds documents and queries with different
    # prefixes; retrieval quality depends on both sides matching.
    assert constants.PASSAGE_PREFIX == "passage: "
    assert constants.QUERY_PREFIX == "query: "
