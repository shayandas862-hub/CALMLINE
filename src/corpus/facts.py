"""What the corpus says about itself — its version, and what each chunk claims.

Split out of `src/opsview/lenses.py`, where it sat oddly: reading the knowledge
base is not the same job as turning stored traces into screen numbers, and the
eval runner needs the corpus version without importing the ops screen to get it.
The lenses now take these facts as input and never touch the KB.

``kb_version`` is a **content hash** over every chunk's id and version, not a
number someone bumps by hand. It therefore changes exactly when the corpus
changes and never when it does not — a manual version is wrong the first time
somebody forgets, and a freshness metric resting on a stale version number is
worse than no freshness metric at all (D-CL-064).
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable


def corpus_facts(chunks: Iterable[Any]) -> dict[str, Any]:
    """Versions, citation styles, the corpus version and its size.

    Sorted before hashing, so the same corpus always yields the same id
    whatever order the chunks arrive in.
    """
    versions: dict[str, int] = {}
    styles: dict[str, str] = {}
    for chunk in chunks:
        versions[chunk.chunk_id] = chunk.version
        styles[chunk.chunk_id] = chunk.citation_style

    return {"current_versions": versions, "citation_styles": styles,
            "kb_version": kb_version(versions), "corpus_clauses": len(versions)}


def kb_version(versions: dict[str, int]) -> str:
    """The corpus content hash — twelve hex characters over id:version, sorted."""
    digest = hashlib.sha256()
    for chunk_id in sorted(versions):
        digest.update(f"{chunk_id}:{versions[chunk_id]}".encode())
    return digest.hexdigest()[:12]
