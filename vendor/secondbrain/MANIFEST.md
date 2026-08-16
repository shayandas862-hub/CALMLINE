# Vendored code — provenance manifest

**Copied:** 2026-07-11 19:41 BST · **One-way copy — the source project was not modified in any way.**
**Author of both projects:** Shayan Das. These files are original single-author work from an
earlier private project by the same author, relicensed MIT here by the copyright owner.
See the repo LICENSE.

**Sole authorship.** The source project was created solely by the author, outside any
employment, on personal equipment and personal accounts. No third party holds, or has ever
held, any right in it, and no third-party code was incorporated into it.

## Rules
- Files in this folder are **reference copies only** — they are never imported by CalmLine code.
- Working versions are **adapted into `src/`** per phase (MIT header, single-tenant, no `app.*`
  imports, embedding model+dim taken from `src/constants.py`).
- The source project's environment files are **never** copied. Verified: no live key material
  exists in this folder.

## Files (source path → vendored name → destined adaptation)

| Source (backend/… unless noted) | Vendored as | Adapted into (phase) |
|---|---|---|
| `app/ingestion/embedder.py` | `ingestion_embedder.py` | `src/corpus/embed.py` (Ph 3) |
| `app/ingestion/chunker.py` | `ingestion_chunker.py` | `src/corpus/chunk.py` (Ph 3) |
| `app/query/hybrid_search.py` | `query_hybrid_search.py` | `src/retrieval/hybrid_search.py` (Ph 3) |
| `app/query/reranker.py` | `query_reranker.py` | `src/retrieval/rerank.py` (Ph 3) |
| `app/query/assembler.py` | `query_assembler.py` | `src/retrieval/assemble.py` (Ph 3) |
| `app/db/pool.py` | `db_pool.py` | `src/db/pool.py` (Ph 1) |
| `app/core/config.py` | `core_config.py` | pattern for `src/config.py` (Ph 1) |
| `app/observability/tracer.py` | `observability_tracer.py` | no-op trace seam reference (Ph 3) |
| `evals/ragas/runner.py` | `evals_runner.py` | skeleton for `src/evals/runner.py` (Ph 5) |
| `app/query/faithfulness.py` | `query_faithfulness.py` | pattern for `src/evals/judge.py` (Ph 7) |

The source project's CI eval workflow was also consulted (not vendored) when
authoring `.github/workflows/eval-gate.yml`.

## Known landmines (fix on adaptation, never carry over)
- A stale model id (`claude-sonnet-4-6`) exists in the source project — invalid. CalmLine
  sets its own ids in `src/config.py` and does not inherit any. (Not vendored, noted for
  completeness.)
- Embedding model + 1536 dim are duplicated in `ingestion_embedder.py` and `query_hybrid_search.py`
  — CalmLine centralises both in `src/constants.py`.
- `query_hybrid_search.py` filters by `user_id` (multi-tenant) — stripped in adaptation.
- `evals_runner.py` metrics are RAG-specific (faithfulness / relevance / item-id overlap) — CalmLine
  keeps only the skeleton (loader, injectable runner, thresholds, report writer).
