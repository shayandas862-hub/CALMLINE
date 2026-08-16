# MIT License — Copyright (c) 2026 Shayan Das
# Adapted from the author's earlier original work
# (vendor/secondbrain/ingestion_embedder.py). Model, dimension, and the
# "passage: " prefix now come from src/constants.py (one source of truth)
# instead of being hardcoded; the API key comes from validated Config.
"""OpenAI embedding wrapper for policy clauses.

Every text is prefixed with PASSAGE_PREFIX before embedding (queries use
QUERY_PREFIX in the retrieval path — the asymmetry is load-bearing). Batched at
100 per request; order preserved. Inject `_client` in tests to avoid the API.
"""

from __future__ import annotations

from typing import Any

from src import constants
from src.config import load_config

_BATCH_SIZE = 100


def _default_client() -> Any:
    import openai

    return openai.OpenAI(api_key=load_config().OPENAI_API_KEY)


def embed(texts: list[str], *, _client: Any = None) -> list[list[float]]:
    """Return a 1536-dim embedding for each text, in order. Empty in → empty out."""
    if not texts:
        return []

    client = _client or _default_client()
    prefixed = [constants.PASSAGE_PREFIX + t for t in texts]
    vectors: list[list[float]] = []

    for i in range(0, len(prefixed), _BATCH_SIZE):
        batch = prefixed[i : i + _BATCH_SIZE]
        response = client.embeddings.create(model=constants.EMBED_MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)

    return vectors
