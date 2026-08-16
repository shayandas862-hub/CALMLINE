"""Document chunker.

Primary path: split enriched text on [CHUNK_BREAK] markers inserted by the enricher.
Fallback path: RecursiveCharacterTextSplitter at 600 tokens / 100 overlap when no
markers are present (e.g. text that bypassed enrichment).

Each output Chunk carries chunk_index, token_count, and source_label.
"""
from __future__ import annotations

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel

_ENCODING = tiktoken.get_encoding("cl100k_base")
_CHUNK_BREAK = "[CHUNK_BREAK]"
_FALLBACK_CHUNK_SIZE = 600
_FALLBACK_CHUNK_OVERLAP = 100


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


class Chunk(BaseModel):
    content: str
    chunk_index: int
    token_count: int
    source_label: str


def _split_on_markers(text: str) -> list[str]:
    parts = text.split(_CHUNK_BREAK)
    return [p.strip() for p in parts if p.strip()]


def _fallback_split(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=_FALLBACK_CHUNK_SIZE,
        chunk_overlap=_FALLBACK_CHUNK_OVERLAP,
    )
    return [p.strip() for p in splitter.split_text(text) if p.strip()]


def chunk(enriched_text: str, source_label: str = "") -> list[Chunk]:
    """Split `enriched_text` into Chunks with metadata attached."""
    if _CHUNK_BREAK in enriched_text:
        parts = _split_on_markers(enriched_text)
    else:
        parts = _fallback_split(enriched_text)

    return [
        Chunk(
            content=content,
            chunk_index=idx,
            token_count=_count_tokens(content),
            source_label=source_label,
        )
        for idx, content in enumerate(parts)
    ]
