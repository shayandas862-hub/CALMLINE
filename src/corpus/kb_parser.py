"""Parse `data/kb/` into typed, uniquely-keyed chunks — the system's only corpus.

The metadata contract (`data/kb/README.md` §3): every `##`/`###` heading that
carries a `*meta:` line is one chunk, and the line names all five fields:

    *meta: doc=02-BOND | sec=12.4 | aud=all | type=tax_rule | data=real*

`chunk_id` is `doc:sec` — derived from the section number, never from position
or wording, so a re-write never moves a citation or breaks an upsert.

Three deliberate behaviours:
  * A heading with no `*meta:` line is a **container** ("PART I — PRODUCT"): it
    emits no chunk, but it still locates its descendants in `heading_path`.
  * **Atomicity is declared, not sniffed** — it keys off `type`, never off
    pipe-table detection. Prose containing a table is still splittable prose.
  * **`type=sample_record` chunks are parsed but flagged `embed=False`**
    (AD-CL-023). Phase 2 seeds the book from them; keeping them out of the index
    is what makes "facts never come from retrieval" true at ingestion, so the
    agent cannot cite a stale record — there is none to cite.

Anything that cannot be parsed raises. The parser this replaces returned zero
chunks from this directory and reported nothing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.corpus.provenance import Provenance, parse_provenance

_META_KEYS = ("doc", "sec", "aud", "type", "data")

# Never overlap-split these — the KB marks them atomic by `type`
# (`data/kb/README.md` §4), not by how they happen to render.
ATOMIC_TYPES = frozenset({"table", "sources", "data_dictionary", "case_study"})

# The two-store boundary, enforced at ingestion (AD-CL-023).
NON_EMBEDDED_TYPES = frozenset({"sample_record"})

# README.md documents the contract by example; its meta lines are not corpus.
EXCLUDED_FILENAMES = frozenset({"README.md"})

_HASH_LENGTH = 16


class KbParseError(ValueError):
    """A heading whose `*meta:` line cannot yield a chunk. Never swallowed."""


@dataclass(frozen=True)
class KbChunk:
    """One retrievable (or, for sample records, one seedable) unit of the KB."""
    chunk_id: str
    doc: str
    sec: str
    aud: str
    type: str
    heading: str
    heading_path: str
    text: str
    token_estimate: int
    content_hash: str
    provenance: Provenance
    embed: bool
    atomic: bool
    source_file: str
    version: int = 1

    @property
    def citation_style(self) -> str:
        """How an answer citing this chunk must attribute it."""
        return self.provenance.citation_style

    @property
    def embed_text(self) -> str:
        """Exactly what task 7 embeds — and exactly what `content_hash` covers.

        Heading-first, because 15 corpus chunks are section headers whose prose
        lives in their subsections (`05-OPS:1 PURPOSE AND SCOPE`). Their heading
        *is* their content; embedding a bare empty body would spend an API call
        on a meaningless vector.
        """
        return embed_text(self.heading, self.text)


def parse_document(markdown: str, *, source_file: str) -> list[KbChunk]:
    """Parse one KB document into ordered chunks."""
    chunks: list[KbChunk] = []
    lines = markdown.splitlines()
    ancestors: list[tuple[int, str]] = []  # (heading level, title)

    for index, line in enumerate(lines):
        level, heading = _heading(line)
        if level == 0:
            continue

        # A heading at level L replaces its peers and everything below them.
        while ancestors and ancestors[-1][0] >= level:
            ancestors.pop()
        ancestors.append((level, heading))

        meta_index = _next_content_index(lines, index + 1)
        fields = _meta_fields(lines[meta_index]) if meta_index is not None else {}
        if not fields:
            continue  # a container heading — it locates, it does not carry

        chunks.append(_build_chunk(
            fields=fields,
            heading=heading,
            heading_path=" > ".join(title for _, title in ancestors),
            text=_body(lines, meta_index + 1),
            source_file=source_file,
        ))
    return chunks


def parse_kb(kb_dir: Path | str) -> list[KbChunk]:
    """Parse every corpus document under `kb_dir`, in filename order."""
    chunks: list[KbChunk] = []
    for md in sorted(Path(kb_dir).glob("*.md")):
        if md.name in EXCLUDED_FILENAMES:
            continue
        chunks.extend(parse_document(md.read_text(encoding="utf-8"),
                                     source_file=md.name))
    return chunks


# --- internals ------------------------------------------------------------

def _build_chunk(*, fields: dict[str, str], heading: str, heading_path: str,
                 text: str, source_file: str) -> KbChunk:
    missing = [key for key in _META_KEYS if not fields.get(key)]
    if missing:
        raise KbParseError(
            f"{source_file}: heading {heading!r} has a *meta: line missing "
            f"{missing} — all of {list(_META_KEYS)} are required to key, filter "
            "and cite a chunk."
        )
    chunk_type = fields["type"]
    return KbChunk(
        chunk_id=f"{fields['doc']}:{fields['sec']}",
        doc=fields["doc"],
        sec=fields["sec"],
        aud=fields["aud"],
        type=chunk_type,
        heading=heading,
        heading_path=heading_path,
        text=text,
        token_estimate=_token_estimate(text),
        content_hash=content_hash(heading, text),
        provenance=parse_provenance(fields["data"]),
        embed=chunk_type not in NON_EMBEDDED_TYPES,
        atomic=chunk_type in ATOMIC_TYPES,
        source_file=source_file,
    )


def _heading(line: str) -> tuple[int, str]:
    """`(level, title)` for a markdown ATX heading, else `(0, "")`."""
    stripped = line.lstrip()
    if not stripped.startswith("#"):
        return 0, ""
    hashes = len(stripped) - len(stripped.lstrip("#"))
    rest = stripped[hashes:]
    if not 1 <= hashes <= 6 or not rest.startswith(" "):
        return 0, ""
    return hashes, rest.strip()


def _meta_fields(line: str) -> dict[str, str]:
    """Fields of a `*meta: k=v | k=v*` line; `{}` if the line is not one."""
    stripped = line.strip()
    if not (stripped.startswith("*meta:") and stripped.endswith("*")):
        return {}
    fields: dict[str, str] = {}
    for part in stripped[len("*meta:"):-1].split("|"):
        key, sep, value = part.partition("=")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def _next_content_index(lines: list[str], start: int) -> int | None:
    for offset, line in enumerate(lines[start:]):
        if line.strip():
            return start + offset
    return None


def _body(lines: list[str], start: int) -> str:
    """The lines between the meta line and the next heading, less layout rules."""
    body: list[str] = []
    for line in lines[start:]:
        if _heading(line)[0]:
            break
        body.append(line)
    while body and _is_layout(body[-1]):
        body.pop()
    return "\n".join(body).strip()


def _is_layout(line: str) -> bool:
    """A horizontal rule separating sections — layout, not content."""
    stripped = line.strip()
    return not stripped or set(stripped) == {"-"} and len(stripped) >= 3


def _token_estimate(text: str) -> int:
    """`chars/4`, the approximation the KB's own contract states (README §10).

    Deliberately not tiktoken: this number exists to reconcile against the KB's
    documented sizing, and the production tokenizer would give different figures
    for the same corpus. Re-measure with tiktoken only if a size cap is tuned.
    """
    return len(text) // 4


def embed_text(heading: str, text: str) -> str:
    """The string that gets embedded: the heading, then the body."""
    return f"{heading}\n{text}".strip()


def content_hash(heading: str, text: str) -> str:
    """The re-embedding diff key (KB README §5): hash changed → re-embed.

    Hashes exactly `embed_text`, so the two can never drift: if the embedded
    string is unchanged the hash is unchanged, and the seeding script correctly
    skips the chunk. Covering the heading also means re-wording one triggers a
    re-embed — a citation displays the heading, so it is part of the content.
    """
    digest = hashlib.sha256(embed_text(heading, text).encode("utf-8")).hexdigest()
    return digest[:_HASH_LENGTH]
