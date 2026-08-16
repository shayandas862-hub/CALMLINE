"""The human half of the world's history — the prose, and what keeps it honest.

Phase 2 put every contact and every case in time and wrote **not one word** of
what was said. This package is where the words go, and the three things around
them: what is left to write, what shape a story must take, and the offline check
that nobody in the prose was invented.

**The prose is written in-session by a language model, to the committed brief in
`BRIEF.md`, across as many sittings as it takes. There is no script, no key, no
API call from this package and no spend** — nothing here constructs a model
client, and nothing here can produce or reproduce a sentence. The prequel is a
separate build from the product, which is what makes it a prequel — the rule
that every call the console and the judge make is on one comparable model exists
to keep the *product's* numbers comparable, and there is nothing here to compare.

**"Hand-written", here and in the guards that protect these rows, means "not
produced by this codebase, and therefore unrecoverable if lost".** It is a claim
about regenerability, not about authorship — the words came from a model, and
the reason `dataset/carry.py` and `workfile.append_stories` refuse so hard is
that no seed brings them back. Authorship is stated above; the term is kept
because the property it names is the one the guards depend on.

Two hazards shape everything in this package, and both are measured rather than
assumed:

- **the world can be regenerated, and the prose cannot.** `policies.jsonl` comes
  back byte-identically from a seed; 1,876 hand-written pieces do not. So the
  stories live in their own file, `note_slot` stays empty, and the writer refuses
  to leave prose behind (`workfile.append_stories`, `dataset.write_world`).
- **prose can say things the ledger does not.** A figure in a note that is in no
  movement is a fabricated number wearing a sentence, and it is far harder to
  catch than one in a table. `BRIEF.md` says what the numbers will not support.
"""
