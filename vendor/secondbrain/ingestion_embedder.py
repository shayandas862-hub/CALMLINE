"""OpenAI embedding wrapper.

Model: text-embedding-3-small (1536 dimensions).
Prefix: every text is prepended with "passage: " before embedding.
Batching: max 100 texts per API call; order is preserved across batches.
"""
from __future__ import annotations

import openai

from app.core.config import get_settings

MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
_PREFIX = "passage: "


def embed(
    texts: list[str],
    *,
    _client: openai.OpenAI | None = None,
) -> list[list[float]]:
    """Return a 1536-dim embedding vector for each text in `texts`.

    `_client` is injectable for testing — omit in production.
    """
    if not texts:
        return []

    client = _client or openai.OpenAI(api_key=get_settings().OPENAI_API_KEY)
    prefixed = [_PREFIX + t for t in texts]
    vectors: list[list[float]] = []

    for i in range(0, len(prefixed), BATCH_SIZE):
        batch = prefixed[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=MODEL, input=batch)
        vectors.extend(item.embedding for item in response.data)

    return vectors
