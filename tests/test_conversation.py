"""v4 phase 5 · Task 8 — the agent remembers, scoped to the interaction.

AD-CL-037, accepting `plans/P-CL-001`. Before this, ``run_console_agent`` seeded
``messages`` fresh on every request: a handler's follow-up started cold. Phase
4's demo only appeared to work because ``policy_no`` and ``verification_id``
travel as request context — a workaround for missing memory, not memory.

**Why the interaction is the boundary, and not the session or the handler.**
AD-CL-029 already spends a verification when the `CN-` closes. Making the
interaction the conversation container means the conversation's lifetime and the
right to see what is in it are the *same fact* — a transcript holding disclosed
personal data cannot outlive the permission that unlocked it, because they end
together. No other boundary has that property.

**The policy-switch trap** (`P-CL-001` §2) is the reason this is scoped to
`(CN-, policy_no)` rather than to `CN-` alone. A verification is scoped to the
pair. A handler who verifies policy A, converses, then opens policy B inside the
same interaction leaves A's record sitting in the model's context while the gate
correctly demands fresh verification for B. That is D-CL-052's hole one layer
up: nothing crosses the endpoint, so the endpoint gate cannot see it.
"""

from src.agent.conversation import ConversationStore

CN = "CN-2026041201"
OTHER_CN = "CN-2026041202"
POLICY_A = "LP-20419876"
POLICY_B = "HB-40582213"


def _store_with_one_turn():
    store = ConversationStore()
    store.record(CN, POLICY_A, question="what is their balance?",
                 answer="£46,210.00 as at 13 July 2026.")
    return store


# ── remembering within an interaction ──────────────────────────────────

def test_a_conversation_starts_empty():
    assert ConversationStore().turns(CN, POLICY_A) == ()


def test_a_turn_is_remembered():
    turns = _store_with_one_turn().turns(CN, POLICY_A)
    assert len(turns) == 1
    assert turns[0].question == "what is their balance?"
    assert turns[0].answer == "£46,210.00 as at 13 July 2026."


def test_turns_come_back_in_the_order_they_were_asked():
    store = _store_with_one_turn()
    store.record(CN, POLICY_A, question="and how do they claim?", answer="…")
    assert [t.question for t in store.turns(CN, POLICY_A)] == [
        "what is their balance?", "and how do they claim?"]


def test_a_snapshot_cannot_be_mutated_back_into_the_store():
    store = _store_with_one_turn()
    assert isinstance(store.turns(CN, POLICY_A), tuple)


# ── the boundary: a different interaction is a different conversation ──

def test_another_interaction_sees_nothing_of_this_one():
    # Two callers about the same policy are two conversations. Leaking between
    # them would disclose one caller's questions to another.
    assert _store_with_one_turn().turns(OTHER_CN, POLICY_A) == ()


# ── the policy-switch trap (P-CL-001 §2) ───────────────────────────────

def test_switching_policy_inside_one_interaction_starts_a_fresh_conversation():
    # THE trap. A verification is scoped to (CN-, policy_no), so opening policy
    # B demands a fresh one — but B's conversation must not inherit A's context,
    # or the agent can answer about B using A's record and nothing crosses the
    # endpoint for the gate to catch.
    assert _store_with_one_turn().turns(CN, POLICY_B) == ()


def test_the_first_policys_conversation_survives_the_switch():
    # Partitioned, not discarded: coming back to A within the same interaction
    # should still have A's history, because the verification for A is still live.
    store = _store_with_one_turn()
    store.record(CN, POLICY_B, question="what is this one worth?", answer="…")
    assert len(store.turns(CN, POLICY_A)) == 1
    assert len(store.turns(CN, POLICY_B)) == 1


def test_a_rules_question_naming_no_policy_has_its_own_conversation():
    # 07-RUNBOOK:4.1 keeps that path open and ungated. It holds no policy data,
    # so it neither reads from nor writes to a policy's conversation.
    store = _store_with_one_turn()
    store.record(CN, "", question="how does a claim work?", answer="…")
    assert len(store.turns(CN, "")) == 1
    assert len(store.turns(CN, POLICY_A)) == 1


# ── expiry: the conversation ends when the interaction does ────────────

def test_closing_the_interaction_ends_every_conversation_on_it():
    # The whole argument for this boundary. A transcript of disclosed personal
    # data must not outlive the verification that permitted it.
    store = _store_with_one_turn()
    store.record(CN, POLICY_B, question="and this one?", answer="…")
    ended = store.expire_for_interaction(CN)
    assert ended == 2
    assert store.turns(CN, POLICY_A) == ()
    assert store.turns(CN, POLICY_B) == ()


def test_closing_one_interaction_leaves_another_alone():
    store = _store_with_one_turn()
    store.record(OTHER_CN, POLICY_A, question="different caller", answer="…")
    store.expire_for_interaction(CN)
    assert len(store.turns(OTHER_CN, POLICY_A)) == 1


def test_expiring_an_interaction_that_never_spoke_is_not_an_error():
    assert ConversationStore().expire_for_interaction(CN) == 0


# ── what the loop is handed ────────────────────────────────────────────

def test_history_is_rendered_as_alternating_turns_the_model_can_read():
    store = _store_with_one_turn()
    messages = store.messages(CN, POLICY_A)
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "what is their balance?"


def test_an_empty_conversation_renders_as_no_messages_not_a_placeholder():
    # A placeholder turn would be a fabricated exchange in the model's context.
    assert ConversationStore().messages(CN, POLICY_A) == []


def test_expiry_mirrors_the_gates_own_boundary():
    # The conversation and the verification must end on the same event, or one
    # outlives the other. ConversationStore names the method the gate names.
    from src.identity.gate import VerificationGate

    assert hasattr(ConversationStore, "expire_for_interaction")
    assert hasattr(VerificationGate, "expire_for_interaction")


def test_context_is_pruned_by_turn_never_summarised():
    # P-CL-001 §3: compaction summarises, and a summary of a policy record is a
    # derived figure traceable to no ledger row. Old turns are DROPPED whole so
    # every number left in context is still one the record produced.
    store = ConversationStore(max_turns=2)
    for i in range(4):
        store.record(CN, POLICY_A, question=f"q{i}", answer=f"a{i}")
    kept = store.turns(CN, POLICY_A)
    assert [t.question for t in kept] == ["q2", "q3"]
    assert all(t.answer in ("a2", "a3") for t in kept)
