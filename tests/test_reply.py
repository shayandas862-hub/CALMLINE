"""v4 phase 4 · Task 3 — ConsoleReply, the console's output shape.

`CallVerdict` and `ComplianceChecklist` were built for the eval harness: a
triage decision and a compliance recommendation. What the console needs is
different — an answer a handler can read, the citations behind it, and an honest
account of what the agent did and refused to do.

The invariants are enforced here rather than asked for in the prompt, because a
prompt instruction is a request and a validator is a guarantee. Three matter:

  * **An answer cites, or it is an abstention.** There is no third state where
    the agent answers from nowhere. This is rule 7 made structural.
  * **An abstention says why.** A refusal with no reason is indistinguishable
    from a failure, and the product's whole claim is that refusing correctly is
    it working.
  * **A rule not yet in force is cited with its effective date** (AD-CL-032).
    The retrieval layer supplies the *style* that says a date is required; the
    model supplies the date it read in the clause; the validator checks it did.

`CallVerdict` and `ComplianceChecklist` are untouched — phase 6 decides their
fate, and the eval harness still runs on them.
"""

import pytest
from pydantic import ValidationError

from src.agent.reply import Citation, ConsoleReply, citations_from_clauses

EFFECTIVE_DATE_REQUIRED = "effective_date_required"


def _clause(**over):
    clause = {"chunk_id": "02-BOND:4.9", "doc": "02-BOND",
              "clause_type": "procedure", "text": "withdrawal terms",
              "aud": "all", "citation_style": "aldercrest_standard"}
    clause.update(over)
    return clause


def _reply(**over):
    kw = dict(answer_text="Withdrawals above £25,000 need back-office approval.",
              citations=[Citation(chunk_id="02-BOND:4.9",
                                  citation_style="aldercrest_standard")],
              tools_used=["retrieve_clause"])
    kw.update(over)
    return ConsoleReply(**kw)


# ── the shape ────────────────────────────────────────────────────────────

def test_a_reply_carries_the_answer_its_citations_and_what_it_used():
    # Act
    reply = _reply()

    # Assert
    assert reply.answer_text.startswith("Withdrawals")
    assert reply.citations[0].chunk_id == "02-BOND:4.9"
    assert reply.tools_used == ["retrieve_clause"]
    assert reply.abstained is False
    assert reply.guardrail_events == []


def test_the_citation_field_is_chunk_id_even_though_retrieval_says_clause_ref():
    # The retrieval type has carried `chunk_id` since v3 and the rename is a
    # between-phases job, so the reply maps at its own boundary rather than
    # reaching into src/retrieval (D-CL-053 contradiction 8).
    # Act
    citations = citations_from_clauses([_clause()])

    # Assert
    assert citations[0].chunk_id == "02-BOND:4.9"


def test_the_version_retrieval_read_reaches_the_citation():
    # KbChunk's version now flows through ClauseHit and CitedClause, so a
    # citation can state which version it read — which is the whole basis of
    # stale_citation_rate (D-CL-056 retired).
    # Act
    citations = citations_from_clauses([_clause(version=3)])

    # Assert
    assert citations[0].version == 3


def test_an_absent_version_is_not_invented():
    # Retrieval always states a version now. One that arrives without it means
    # something upstream did not, and defaulting to "1" would assert a chunk was
    # never re-embedded on no evidence — a fabricated number (rule 7).
    # Act
    citations = citations_from_clauses([_clause()])

    # Assert
    assert citations[0].version is None


def test_a_citation_keeps_the_style_retrieval_gave_it():
    # Act
    citations = citations_from_clauses([_clause(citation_style="cite_source")])

    # Assert
    assert citations[0].citation_style == "cite_source"


def test_a_clause_with_no_style_stays_an_explicit_unknown():
    # Act
    citations = citations_from_clauses([_clause(citation_style=None)])

    # Assert
    assert citations[0].citation_style is None


# ── an answer cites, or it abstains ──────────────────────────────────────

def test_an_answer_about_the_record_needs_no_citation():
    # A ledger figure has no clause behind it. Demanding one would push the
    # agent into inventing a reference for a number that came from the system
    # of record — the exact failure the rule was meant to prevent. Grounding
    # is checked in the loop, which knows which tools actually ran.
    # Act
    reply = _reply(answer_text="The current value is £150,240.00.", citations=[])

    # Assert
    assert reply.abstained is False
    assert reply.citations == []


def test_an_abstention_needs_no_citation():
    # Act
    reply = ConsoleReply(answer_text="", abstained=True,
                         abstention_reason="the corpus does not cover this")

    # Assert
    assert reply.abstained is True
    assert reply.citations == []


def test_an_abstention_without_a_reason_is_rejected():
    # A refusal with no reason cannot be told apart from a failure.
    # Act / Assert
    with pytest.raises(ValidationError, match="reason"):
        ConsoleReply(answer_text="", abstained=True)


def test_an_answer_with_no_text_is_rejected():
    # Act / Assert
    with pytest.raises(ValidationError):
        _reply(answer_text="   ")


def test_an_abstention_may_carry_the_line_read_to_the_caller():
    # Found by the live smoke: a model that declines explains itself, and
    # forcing that explanation out of the caller-facing field buys nothing.
    # The guarantee is the other one — a NON-abstention must cite.
    # Act
    reply = ConsoleReply(
        answer_text="I can't confirm that from the wordings.",
        abstained=True, abstention_reason="the corpus does not cover it")

    # Assert
    assert reply.abstained is True
    assert reply.citations == []


def test_an_abstention_still_needs_no_citations_when_it_carries_a_line():
    # Act
    reply = ConsoleReply(answer_text="I can't help with that.", abstained=True,
                         abstention_reason="out of scope")

    # Assert
    assert reply.citations == []


# ── AD-CL-032: a rule not yet in force cites its date ────────────────────

def test_a_not_yet_in_force_citation_must_carry_its_effective_note():
    # Act / Assert
    with pytest.raises(ValidationError, match="effective"):
        _reply(citations=[Citation(chunk_id="04-FCA:2.1",
                                   citation_style=EFFECTIVE_DATE_REQUIRED)])


def test_a_not_yet_in_force_citation_is_accepted_with_the_note():
    # Act
    reply = _reply(citations=[Citation(chunk_id="04-FCA:2.1",
                                       citation_style=EFFECTIVE_DATE_REQUIRED,
                                       effective_note="in force from 2027-01-01")])

    # Assert
    assert reply.citations[0].effective_note == "in force from 2027-01-01"


def test_a_blank_effective_note_does_not_satisfy_the_rule():
    # Act / Assert
    with pytest.raises(ValidationError, match="effective"):
        _reply(citations=[Citation(chunk_id="04-FCA:2.1",
                                   citation_style=EFFECTIVE_DATE_REQUIRED,
                                   effective_note="   ")])


def test_an_ordinary_citation_needs_no_effective_note():
    # Act
    reply = _reply()

    # Assert
    assert reply.citations[0].effective_note is None


# ── guardrail events are recorded, not summarised away ───────────────────

def test_guardrail_events_are_carried_through():
    # Act
    reply = _reply(guardrail_events=["refused: no verification for LP-20419876"])

    # Assert
    assert reply.guardrail_events == ["refused: no verification for LP-20419876"]


def test_a_refusal_is_a_valid_reply_not_an_error():
    # The product's claim is that refusing correctly is it working, so a
    # refusal has to be expressible as a well-formed reply.
    # Act
    reply = ConsoleReply(
        answer_text="", abstained=True,
        abstention_reason="the caller is not verified for this policy",
        guardrail_events=["refused: no live verification"],
        tools_used=["lookup_policy_record"])

    # Assert
    assert reply.abstained is True
    assert reply.guardrail_events


# ── building citations from what the knowledge tool returns ──────────────

def test_citations_are_built_from_the_knowledge_tools_own_output():
    # Act
    citations = citations_from_clauses(
        [_clause(), _clause(chunk_id="01-WOL:II.13", doc="01-WOL")])

    # Assert
    assert [c.chunk_id for c in citations] == ["02-BOND:4.9", "01-WOL:II.13"]


def test_no_clauses_yields_no_citations():
    # Act / Assert
    assert citations_from_clauses([]) == []


# ── the schema handed to the API (found by the live smoke) ───────────────

def test_every_object_in_the_generated_schema_closes_itself():
    # `output_config.format` rejects a schema whose objects omit
    # `additionalProperties: false`. Pydantic does not emit it unless extras
    # are forbidden, so the API refused our first real request while every
    # stubbed test passed. This is that 400, caught offline.
    # Act
    schema = ConsoleReply.model_json_schema()

    # Assert
    assert schema["additionalProperties"] is False
    for name, defined in (schema.get("$defs") or {}).items():
        assert defined.get("additionalProperties") is False, name


def test_an_unexpected_field_is_rejected():
    # The runtime half of the same contract.
    # Act / Assert
    with pytest.raises(ValidationError):
        ConsoleReply(answer_text="x", citations=[Citation(chunk_id="a")],
                     invented_field="nope")
