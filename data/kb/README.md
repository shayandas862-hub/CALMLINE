# Aldercrest Life — RAG Knowledge Base
### Reference package: documents, ingestion pipeline, evals and observability

A synthetic-but-realistic UK life insurance knowledge base built to power and **test** an agentic RAG customer-service assistant spanning front office, back office and operations.

- **Company:** Aldercrest Life Assurance plc — fictional; not a real FCA-authorised insurer.
- **Grounding rule:** every operating standard (charges, SLAs, thresholds, codes, scripts) is fictional but realistic; every **legal and regulatory** rule is real, current for 2025/26, and carries a source URL.
- **Knowledge-base date:** 13 July 2026. Rules legislated but not yet in force are flagged with `data=real (not yet in force)` and an effective date.

---

## 1. What's in the package

| File | What it is |
|---|---|
| `01_Whole_of_Life_Assurance_Product_Master.md` | Product + operations + RAG assets — protection, trusts, IHT |
| `02_Onshore_Investment_Bond_Product_Master.md` | Product + operations + RAG assets — chargeable events, trust wrappers |
| `03_Personal_Pension_Product_Master.md` | Product + operations + RAG assets — allowances, decumulation, bypass trusts |
| `04_FCA_Regulatory_Mandate.md` | Firm-level and product-level regulation with real sources |
| `05_Operations_Servicing_and_Claims_Manual.md` | Cross-product procedures: identity, authority, servicing, money, claims |
| `06_RAG_Ops_Evals_and_Change_Management.md` | Metadata pipeline, change control, golden evals, observability |
| `07_Front_Back_Office_Ops_Runbook.md` | Operating model: call lifecycle, case states, payments, incidents, QA, AI governance |
| `ingest_chunks.py` | Splits documents into metadata-tagged chunks → `chunks.jsonl` |
| `inject_meta.py` | Backfills missing `meta:` lines (idempotent) |
| `validate_kb.py` | Pre-flight checks; **non-zero exit blocks release** |
| `golden_evals.jsonl` | 44 machine-readable eval cases across 6 tiers |
| `chunks.jsonl` | Generated output — ready to embed |

Each product document has three parts: **Part I** product rules and tax, **Part II** operations tailored to that product, **Part III** RAG assets (glossary, FAQs, synthetic policy record, worked case studies, cross-source reasoning map).

---

## 2. Quick start

```bash
python -m src.corpus.kb_validate data/kb   # must print "PASS"; non-zero exit blocks release
```

Expected on a clean package: **441 chunks** — 438 embeddable, 3 withheld (the
`sample_record` chunks, which seed the system of record instead) — median ~103
tokens, longest ~891, `PASS`.

CalmLine owns this pipeline: `src/corpus/kb_parser.py` parses, and
`src/corpus/kb_validate.py` is the gate. If you edit a document and the gate
complains about a missing `meta:` field, it names the chunk id and the field —
add the line by hand; there is no backfill step.

---

## 3. The metadata contract

Every `##` / `###` heading is one chunk, and carries a machine-readable tag:

```
*meta: doc=02-BOND | sec=12.4 | aud=all | type=tax_rule | data=real*
```

The parser turns that into filterable fields:

```json
{
  "chunk_id": "02-BOND:12.4",
  "doc": "02-BOND", "sec": "12.4",
  "heading": "12.4 Chargeable-gain attribution ladder for trust-held bonds",
  "heading_path": "PART I — PRODUCT > 12. ESTATE-PLANNING TRUST WRAPPERS > 12.4 ...",
  "aud": "all", "type": "tax_rule", "data": "real",
  "text": "...", "token_estimate": 228,
  "content_hash": "0c8570cb6a07c56f", "version": 1,
  "effective_from": null, "superseded_by": null
}
```

**Field vocabulary**

- `doc` — `01-WOL` · `02-BOND` · `03-PEN` · `04-FCA` · `05-OPS` · `06-RAGOPS` · `07-RUNBOOK`
- `aud` — `customer` · `back_office` · `ops` · `regulatory` · `all`
- `type` — `overview, eligibility, product_rule, tax_rule, journey, procedure, claims, table, legal, ops, glossary, faq, customer_info, sample_record, case_study, routing, sources, worked_example, caveats, data_dictionary, script`
- `data` — `real` · `fictional` · `mixed` · `real (not yet in force)`

**Why it matters.** `chunk_id` is derived from the section number, not from position or text — so it stays stable when wording changes, which is what makes incremental re-embedding possible (§5).

---

## 4. Loading into a vector store

Index `text` as the embedding and keep `doc`, `aud`, `type`, `data`, `version`, `effective_from` as **filterable** metadata. Use `chunk_id` as the primary key so upserts are idempotent.

Retrieval is **filter-then-search**, not search-alone:

```python
filters = {"aud": {"$in": [audience, "all"]}}
if product_code:                      # from LP- / HB- / RA- prefix
    filters["doc"] = {"$in": [product_code, "05-OPS", "04-FCA", "07-RUNBOOK"]}
hits = index.query(embed(question), filter=filters, top_k=8)
```

Two things this buys you:

1. **Duplicate collapse.** Identity and data-protection rules are deliberately repeated in each product document so every chunk is self-contained. Filtering by `doc` returns the pension copy for a pension question instead of four near-identical hits. Add MMR if you retrieve across products.
2. **Correct citation behaviour.** `data=real` → cite the source URL. `data=fictional` → label it "Aldercrest operating standard". `real (not yet in force)` → the answer **must** state the effective date.

**Actual chunking:** heading-aware, with **no size target** — one `meta:`-tagged heading is one chunk, so the document's own section structure sets every boundary. That yields a median of ~103 tokens and a longest chunk of ~891 (7 chunks over 500, 1 over 800), which is well inside any context budget; there is no recursive splitter and no overlap, because there is nothing to split. Never overlap-split tables, source lists or sample records — `type` in `{table, sources, data_dictionary, case_study}` marks these atomic, and **atomicity is read from `type`, never inferred from whether a chunk contains a pipe table**.

---

## 5. Changing the knowledge base after it's embedded

The question every reviewer asks. You never rebuild the corpus.

1. **Edit the markdown.** The `.md` files are the single source of truth; never edit vectors directly.
2. **Re-run `ingest_chunks.py`.** Every chunk gets a fresh `content_hash`.
3. **Diff by `chunk_id`:**
   - hash unchanged → skip (no embedding cost)
   - hash changed → re-embed, upsert same id, `version += 1`
   - new id → embed and insert
   - id disappeared → **tombstone** (set `superseded_by`, keep in an archive namespace) — never silently drop
4. **Run `validate_kb.py`.** Non-zero exit blocks the release.
5. **Shadow index + eval gate.** Apply to staging, run `golden_evals.jsonl`; promote only at **≥95% pass** and **zero Tier-G failures**.
6. **Audit.** Log `{kb_version, chunks_changed, eval_run_id, approver}`.

A tax-rate change touches 2–5 chunks: seconds of re-embedding, not a corpus rebuild. Because the knowledge base drives a regulated customer-facing process, this change control **is** a compliance control (Doc 7 §8.9).

**Time-versioned rules.** Future changes (savings rates 22/42/47% and pension IHT from 6 April 2027; NMPA 57 from 2028) are already in the corpus tagged `real (not yet in force)` with an effective date. The generator compares that date to the question's operative date — so the same chunk answers "from April 2027…" today and becomes the operative rule later **with no re-embedding**. On commencement day you flip one flag in markdown.

---

## 6. Evaluation

`golden_evals.jsonl` — 44 cases, six tiers:

| Tier | Cases | Tests |
|---|---|---|
| **R** retrieval | 9 | single-hop facts; wrong-figure regressions |
| **M** multi-hop | 9 | chained reasoning (tax arithmetic, trust attribution, cascades) |
| **X** cross-document | 6 | 3–5 source chains across products, procedures and runbook |
| **T** temporal | 4 | not-yet-in-force rules; same question, different dates |
| **G** guardrail | 8 | must-refuse: advice boundary, tipping off, confirm/deny, attorney-as-trustee |
| **O** operational | 8 | SLA clocks, maker-checker, CoP, incidents, containment, abstention |

Each case carries `question`, `answer_keys`, `expected_chunks` and the `failure_mode` being guarded against.

**Scoring:** retrieval recall@5 against `expected_chunks`; answer-key coverage by LLM judge; Tier G is **binary** — any guardrail failure blocks release regardless of overall score.

**Harness contract:** read the JSONL, run each `question` through your pipeline, capture retrieved chunk ids and the answer, then score. `validate_kb.py` already checks that every `expected_chunks` reference resolves to a real chunk, so evals can't silently rot when documents are edited.

The set is **append-only** — mine production failures and agent corrections into new cases (Doc 6 §4.3).

---

## 7. Observability

Per-query trace schema, metrics and alerting are specified in **Doc 6 §4**. The metrics that matter most:

- **gate-bypass count** — any disclosure logged before identity verification. Target **0**; doubles as a data-breach detector.
- **advice-boundary violations** — the assistant is information-only. Target **0**.
- **stale-citation rate** — answers citing a superseded or tombstoned chunk version. Must be **0** after every promotion.
- **abstention rate with correct-routing rate** — abstention is a **success state**, but only when the handoff was right.
- **containment** — tracked, **never targeted**. A containment target pressures the assistant to answer what it should escalate (Doc 7 §8.6).

---

## 8. Demonstration script

Ten minutes covering retrieval, change control, temporal reasoning, safety and operational depth:

1. **Cross-document chain** — run eval `E12` (LPA holder wants £30k from mother's bond to a new account). Show the trace: filters applied, four-source retrieval, gates enforced, citations with versions.
2. **Change management** — edit a figure in `02_..._Bond_...md` §4.2, re-run the pipeline, show only 1–2 chunks re-embed, eval gate green, stale-citations 0.
3. **Temporal** — run `E20` (bypass-trust death January vs June 2027). Same chunks, two correct answers.
4. **Guardrail** — run `E33` (asks for a recommendation) and `E34` (asks if a hold is a money-laundering check). Show the refusals and `guardrail_events`.
5. **Operational depth** — run `E38` (does the SLA clock stop for a GP report?) or `E42` (claims system down). Shows the assistant reasoning about controls, not just product facts.

---

## 9. Complexity map — what this corpus is designed to stress

| Dimension | Where it lives |
|---|---|
| Multi-step arithmetic | Bond chargeable events, top-slicing, trust periodic charges |
| Interlocking constraints | Pension AA / taper / MPAA / LSA / protections |
| Temporal reasoning | 2027 tax and IHT changes; 2028 NMPA; PS25/19 reporting |
| Jurisdictional variation | Scotland (Confirmation, assignation, S-codes, legal rights) vs England & Wales |
| Authority law | LOA vs LPA vs EPA vs deputy vs executor vs trustee — and their limits |
| Who-is-assessable logic | Bond attribution ladder: settlor → trustees → beneficiaries |
| Control chains | Identity gates → authority → sanctions → four-eyes → dual authorisation |
| Refusal behaviour | Advice boundary, tipping off, confirm/deny, attorney-as-trustee, skip-the-check |
| Operational reasoning | SLA clock rules, pend codes, incident severity, redress calculation |

The three products are deliberately pitched at different difficulty: **Whole of Life** low–medium, **Bond** medium–high (tax arithmetic), **Pension** high (allowance interplay and temporal splits). A system that handles all three is demonstrably reasoning, not pattern-matching.

---

## 10. Known limitations

- Aldercrest operating standards are invented; do not treat any threshold, SLA or code as industry benchmark.
- Regulatory content is accurate as at **13 July 2026** — verify against the cited sources before any real-world use. Nothing here is legal, tax or financial advice.
- Sample policy records are synthetic; the named individuals do not exist.
- `token_estimate` is a `chars/4` approximation; re-measure with your production tokenizer if you tune size caps.

---

## 11. Sources and attribution

**Aldercrest Life Assurance plc is fictional**, and so is every operating
standard, service level, pend code and internal procedure in this package. See
the [legal and data notice](../../README.md#legal-and-data-notice).

The regulatory and legal content is **paraphrased and cited by reference, not
reproduced**. Rule numbers and short labels are given so a reader can check each
point at its source; no substantial passage of any third-party document is
copied into this corpus.

| Source | Rights position |
|---|---|
| legislation.gov.uk, gov.uk, HMRC manuals | Crown copyright, reproduced under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) |
| Bank of England / PRA supervisory statements | Crown copyright, OGL v3.0 |
| FCA Handbook, FCA publications | © Financial Conduct Authority. Cited by rule reference only; no Handbook text is reproduced here |
| Financial Ombudsman Service, FSCS, ICO, NCA, JMLSG | cited by reference; no text reproduced |

Rule references drift as the Handbook and legislation are amended. **Always
check the live source before relying on any reference in this package.**
