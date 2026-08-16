"""Plan an incremental re-seed of `kb_chunks` — embed only what changed.

`data/kb/README.md` §5: you never rebuild the corpus. Each seed run diffs the
parsed chunks against what the index already holds, keyed by `chunk_id` and
compared by `content_hash`:

    hash unchanged  → skip, no embedding call
    hash changed    → re-embed, upsert the SAME chunk_id, version + 1
    new chunk_id    → embed and insert at version 1
    id disappeared  → **tombstone**, never a silent drop

The tombstone rule is the one with consequences. A chunk that vanishes from the
markdown must stay resolvable, because answers already given cite it by id;
deleting the row turns a real citation into a dangling reference. Retrieval
excludes tombstoned rows, so the chunk stops being *found* without ceasing to
*exist*.

Sample records are excluded from the index entirely, not merely left without an
embedding: `kb_chunks.tsv` is `generated always`, so any row present at all is
reachable by keyword search — which is exactly the two-store leak AD-CL-023
exists to prevent (facts come from the system of record, never from retrieval).

This module is pure: it decides, it does not call OpenAI or Postgres. That is
what makes the diff logic testable with no credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from src import constants
from src.corpus.kb_parser import KbChunk

TABLE = "kb_chunks"


@dataclass(frozen=True)
class SeedPlan:
    """What one seed run will do. Nothing here has happened yet."""
    to_embed: tuple[KbChunk, ...]
    unchanged: tuple[KbChunk, ...]
    to_tombstone: tuple[str, ...]
    withheld: tuple[KbChunk, ...]
    _versions: Mapping[str, int]

    def version_for(self, chunk_id: str) -> int:
        """The version this chunk will carry after the run."""
        return self._versions[chunk_id]

    @property
    def embedding_calls(self) -> int:
        return len(self.to_embed)


def plan_seed(chunks: Sequence[KbChunk],
              existing: Mapping[str, Mapping[str, object]]) -> SeedPlan:
    """Diff parsed `chunks` against the `{chunk_id: {content_hash, version}}` index."""
    to_embed: list[KbChunk] = []
    unchanged: list[KbChunk] = []
    withheld: list[KbChunk] = []
    versions: dict[str, int] = {}

    for chunk in chunks:
        if not chunk.embed:
            withheld.append(chunk)
            continue
        indexed = existing.get(chunk.chunk_id)
        if indexed is None:
            versions[chunk.chunk_id] = 1
            to_embed.append(chunk)
        elif indexed["content_hash"] == chunk.content_hash:
            unchanged.append(chunk)
        else:
            versions[chunk.chunk_id] = int(indexed["version"]) + 1
            to_embed.append(chunk)

    # Anything the index holds that the corpus no longer offers for embedding —
    # including a sample record an earlier run may have leaked in.
    live = {chunk.chunk_id for chunk in chunks if chunk.embed}
    to_tombstone = tuple(sorted(set(existing) - live))

    return SeedPlan(
        to_embed=tuple(to_embed),
        unchanged=tuple(unchanged),
        to_tombstone=to_tombstone,
        withheld=tuple(withheld),
        _versions=versions,
    )


def build_row(chunk: KbChunk, *, vector: list[float], version: int) -> dict:
    """One `kb_chunks` row. `heading` + `text` together are what was embedded."""
    if len(vector) != constants.EMBED_DIM:
        raise ValueError(
            f"embedding has {len(vector)} dimensions, but kb_chunks.embedding is "
            f"vector({constants.EMBED_DIM}) — check constants.EMBED_MODEL"
        )
    return {
        "chunk_id": chunk.chunk_id,
        "doc": chunk.doc,
        "sec": chunk.sec,
        "aud": chunk.aud,
        "type": chunk.type,
        "provenance": chunk.provenance.raw,
        "citation_style": chunk.citation_style,
        "heading": chunk.heading,
        "heading_path": chunk.heading_path,
        "text": chunk.text,
        "token_estimate": chunk.token_estimate,
        "content_hash": chunk.content_hash,
        "version": version,
        "superseded_by": None,
        "embedding": vector,
    }


# --- the run --------------------------------------------------------------

@dataclass(frozen=True)
class SeedResult:
    """What a seed run actually did."""
    embedded: int
    skipped: int
    tombstoned: int
    withheld: int


def read_index(client: Any) -> dict[str, dict]:
    """`{chunk_id: {content_hash, version}}` for every row already in the table."""
    response = client.table(TABLE).select("chunk_id,content_hash,version").execute()
    return {
        row["chunk_id"]: {"content_hash": row["content_hash"],
                          "version": row["version"]}
        for row in (response.data or [])
    }


def seed_kb_chunks(chunks: Sequence[KbChunk], client: Any, *,
                   _embed: Callable[[list[str]], list[list[float]]] | None = None
                   ) -> SeedResult:
    """Embed and upsert only what changed; tombstone what disappeared.

    `_embed` is injected in tests so the diff can be proven without an API call —
    and the strongest assertion is the negative one: an unchanged corpus must
    make no embedding call at all.
    """
    plan = plan_seed(chunks, read_index(client))

    if plan.to_embed:
        embed = _embed or _default_embedder()
        vectors = embed([chunk.embed_text for chunk in plan.to_embed])
        rows = [
            build_row(chunk, vector=vector,
                      version=plan.version_for(chunk.chunk_id))
            for chunk, vector in zip(plan.to_embed, vectors)
        ]
        client.table(TABLE).upsert(rows, on_conflict="chunk_id").execute()

    for chunk_id in plan.to_tombstone:
        # Self-reference means "retired, with no successor": the row survives so
        # an existing citation still resolves, and retrieval excludes any row
        # whose superseded_by is set.
        (client.table(TABLE)
               .update({"superseded_by": chunk_id})
               .eq("chunk_id", chunk_id)
               .execute())

    return SeedResult(
        embedded=len(plan.to_embed),
        skipped=len(plan.unchanged),
        tombstoned=len(plan.to_tombstone),
        withheld=len(plan.withheld),
    )


def _default_embedder() -> Callable[[list[str]], list[list[float]]]:
    from src.corpus.embed import embed

    return embed
