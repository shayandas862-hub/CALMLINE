"""``ConsoleReply`` — what the agent hands the console.

`CallVerdict` and `ComplianceChecklist` were shaped for the eval harness: a
triage decision, a compliance recommendation. The console needs something else —
an answer a handler can read out, the citations standing behind it, and an
honest account of what the agent used and what it refused to do. Both of the
older shapes stay exactly as they are; phase 6 decides their fate and the eval
harness still runs on them.

The invariants live here as validators rather than as sentences in the system
prompt. A prompt instruction is a request; a validator is a guarantee, and a
model that produces an uncited answer fails to produce a `ConsoleReply` at all.

Two are load-bearing here:

  * **An abstention says why.** A refusal with no reason cannot be told apart
    from a failure, and refusing correctly is the product working.
  * **A rule not yet in force is cited with its effective date** (AD-CL-032).
    Retrieval supplies the *style* saying a date is required; the model supplies
    the date it read in the clause; this checks that it did.

And note what is deliberately **not** here: a rule that every answer must carry
a citation. An earlier version had one, and a handler hit it on the first
obvious question — *"what is the value today?"*. This product answers across two
stores, and a ledger figure has no clause behind it, so the rule forced a choice
between fabricating a reference and refusing a question the agent could answer
correctly. Both are worse than what it was guarding against.

Grounding lives in ``console_loop.py`` instead, where the tools that actually ran
are known: an answer must rest on a tool that ran, and every clause it cites must
be one retrieval really returned. That is a stronger guarantee than "cite
something" — it catches a plausible clause id invented from memory — and it is
not a guarantee this model can make about itself.

Both of the fields that held less than the phase spec asked for now hold what it
asked for, and D-CL-056's compromise is retired. ``chunk_id`` is the retrieval
layer's own field name rather than something translated at this boundary, and
``version`` carries `KbChunk.version` all the way through `ClauseHit` and
`CitedClause` — which is what makes ``stale_citation_rate`` computable at all.

``citation_style`` and ``version`` are **stated by the loop, not by the model**.
A model is asked to copy them out of a tool result, and one that forgets produces
a citation whose provenance chip silently degrades to "style unknown" — observed
between two models on the same question (D-CL-061). So both are backfilled from
what retrieval actually returned. A ``None`` on either means the loop has not
backfilled it yet, never that the fact is unknowable.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Structured outputs require every object in the schema to close itself
# explicitly: `output_config.format` rejects a schema whose objects omit
# `additionalProperties: false`, exactly as strict tool schemas do. Pydantic
# does not emit it unless extras are forbidden, so this config **is** the API
# contract, not a preference — `extra="forbid"` is what puts the key in
# `model_json_schema()`. Found by the live smoke: every stubbed test accepted
# the open schema happily, and the API refused it on the first real request.
_CLOSED = ConfigDict(extra="forbid")

# The one style that obliges the answer to state a date (AD-CL-027/032). Mirrors
# `src.corpus.provenance.EFFECTIVE_DATE_REQUIRED`; kept as a literal so this
# module does not reach into the corpus package it is not allowed to edit.
EFFECTIVE_DATE_REQUIRED = "effective_date_required"


class Citation(BaseModel):
    """One clause the answer stands on."""

    model_config = _CLOSED

    chunk_id: str
    citation_style: str | None = None
    effective_note: str | None = None
    # The version retrieval read, which `stale_citation_rate` compares against a
    # chunk's current one. The model is not asked for it and does not supply it;
    # the loop backfills it, so `None` means "not yet backfilled" rather than
    # "unknowable". Never a guessed "1" at this boundary.
    version: int | None = None

    @model_validator(mode="after")
    def _not_yet_in_force_states_its_date(self) -> "Citation":
        if self.citation_style == EFFECTIVE_DATE_REQUIRED and not (
                self.effective_note or "").strip():
            raise ValueError(
                f"{self.chunk_id}: a rule not yet in force must be cited with its "
                f"effective date (AD-CL-032) — set effective_note"
            )
        return self


class ConsoleReply(BaseModel):
    """The agent's answer, its citations, and what it did to get there."""

    model_config = _CLOSED

    answer_text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool = False
    abstention_reason: str = ""
    guardrail_events: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _answers_are_cited_and_abstentions_are_explained(self) -> "ConsoleReply":
        answered = bool(self.answer_text.strip())
        if self.abstained:
            # ``answer_text`` is permitted here and is the line the handler reads
            # to the caller — "I can't confirm that from the wordings". An
            # earlier version forbade it, on the theory that abstaining and
            # answering are contradictory. The live smoke showed that is the
            # wrong model of the field: a model that declines naturally explains
            # itself, and forcing the explanation out of the caller-facing field
            # buys nothing. The guarantee that matters is the one below — if you
            # did **not** abstain, you must cite — and it is untouched.
            if not self.abstention_reason.strip():
                raise ValueError("an abstention must give its reason")
            return self
        if not answered:
            raise ValueError(
                "a reply must either answer or abstain — an empty answer that "
                "does not abstain is neither")
        return self


def citations_from_clauses(
        clauses: Sequence[Mapping[str, Any]]) -> list[Citation]:
    """Turn the knowledge tool's clause dicts into citations.

    No translation happens here any more. The retrieval types carry ``chunk_id``
    and ``version`` under the KB's own names, so this reads them straight through
    — and what it reads is what *retrieval* said, not what the model echoed back.
    """
    return [
        Citation(
            chunk_id=clause["chunk_id"],
            citation_style=clause.get("citation_style"),
            # No default. Retrieval always states a version now, so an absent
            # one means something upstream did not — and inventing "1" for it
            # would be a fabricated number (rule 7).
            version=clause.get("version"),
        )
        for clause in clauses
    ]
