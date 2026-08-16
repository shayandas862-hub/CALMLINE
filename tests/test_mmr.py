"""MMR re-ranking — the deliberate-duplication fix (AD-CL-025).

The KB repeats identity, data-protection and authority rules inside *each*
product document on purpose, so every chunk is self-contained and answerable
alone. That design choice has a retrieval cost: a query that spans products
returns four near-identical hits and burns the context window saying the same
thing four times.

A `doc` filter solves the common case (a pension question wants the pension
copy). MMR solves the case a filter cannot: a genuinely cross-product query,
where the right answer is one copy of the shared rule *plus* whatever else is
relevant — not four copies of the shared rule.

Similarity is token overlap, not embeddings: it detects near-identical wording,
needs no API call (rule 10), and is deterministic.
"""

from src.retrieval.hybrid_search import ClauseHit
from src.retrieval.mmr import mmr, token_similarity

# The shared identity rule, as it appears in each product document — near
# identical wording, different doc and section.
IDENTITY = (
    "Verify identity before disclosing any personal data. Confirm full name, "
    "policy number, date of birth and address before any disclosure."
)
IDENTITY_VARIANT = (
    "Verify identity before disclosing any personal data. Confirm full name, "
    "plan number, date of birth and address before any disclosure."
)
TOP_SLICING = (
    "Top-slicing relief spreads the chargeable gain over the number of complete "
    "years the bond has been held, reducing the higher-rate liability."
)


def _hit(clause_id, doc, text, score, ref=None):
    return ClauseHit(clause_id=clause_id, doc=doc, chunk_id=ref or clause_id,
                     clause_type="procedure", text=text, score=score)


# --- token_similarity -----------------------------------------------------

def test_identical_text_is_fully_similar():
    assert token_similarity(IDENTITY, IDENTITY) == 1.0


def test_unrelated_text_is_not_similar():
    assert token_similarity(IDENTITY, TOP_SLICING) < 0.15


def test_a_one_word_variant_is_still_highly_similar():
    # This is what the per-product duplication actually looks like.
    assert token_similarity(IDENTITY, IDENTITY_VARIANT) > 0.8


def test_empty_text_is_similar_to_nothing():
    assert token_similarity("", IDENTITY) == 0.0
    assert token_similarity("", "") == 0.0


# --- the re-rank ----------------------------------------------------------

def test_no_hits_yields_no_hits():
    assert mmr([]) == []


def test_the_most_relevant_hit_is_always_selected_first():
    hits = [
        _hit("a", "01-WOL", IDENTITY, 0.2),
        _hit("b", "02-BOND", TOP_SLICING, 0.9),
    ]
    assert mmr(hits)[0].clause_id == "b"


def test_distinct_hits_keep_their_relevance_order():
    # With nothing duplicated, MMR must not shuffle a good ranking.
    hits = [
        _hit("a", "01-WOL", "Sum assured is paid on death of the life assured.", 0.9),
        _hit("b", "02-BOND", TOP_SLICING, 0.6),
        _hit("c", "03-PEN", "The annual allowance tapers for high earners.", 0.3),
    ]
    assert [h.clause_id for h in mmr(hits)] == ["a", "b", "c"]


def test_a_near_duplicate_is_demoted_below_a_distinct_weaker_hit():
    # The four-near-identical-hits problem, in miniature: the pension copy of the
    # identity rule should lose its place to the distinct bond chunk.
    hits = [
        _hit("wol-identity", "01-WOL", IDENTITY, 0.90),
        _hit("pen-identity", "03-PEN", IDENTITY_VARIANT, 0.85),
        _hit("bond-slicing", "02-BOND", TOP_SLICING, 0.40),
    ]

    ranked = [h.clause_id for h in mmr(hits, top_k=2)]

    assert ranked == ["wol-identity", "bond-slicing"]


def test_all_four_product_copies_collapse_to_one_in_the_top_slots():
    # The real shape: the shared rule duplicated across all four documents.
    duplicates = [
        _hit(f"{doc}-identity", doc, IDENTITY, 0.9 - index * 0.01)
        for index, doc in enumerate(("01-WOL", "02-BOND", "03-PEN", "05-OPS"))
    ]
    distinct = [
        _hit("slicing", "02-BOND", TOP_SLICING, 0.5),
        _hit("allowance", "03-PEN", "The annual allowance tapers for high earners.", 0.45),
    ]

    ranked = mmr(duplicates + distinct, top_k=3)

    identity_kept = [h for h in ranked if h.clause_id.endswith("-identity")]
    assert len(identity_kept) == 1, "one copy of the shared rule is enough"
    assert {h.clause_id for h in ranked} == {"01-WOL-identity", "slicing", "allowance"}


def test_top_k_caps_the_result():
    hits = [_hit(str(i), "01-WOL", f"distinct text number {i}", 1.0 - i * 0.05)
            for i in range(10)]
    assert len(mmr(hits, top_k=4)) == 4


def test_fewer_hits_than_top_k_returns_them_all():
    hits = [_hit("a", "01-WOL", IDENTITY, 0.9), _hit("b", "02-BOND", TOP_SLICING, 0.5)]
    assert len(mmr(hits, top_k=8)) == 2


# --- the relevance/diversity dial ----------------------------------------

def test_full_relevance_weight_reproduces_the_relevance_ranking():
    # relevance_weight=1.0 turns diversity off entirely — the escape hatch.
    hits = [
        _hit("wol-identity", "01-WOL", IDENTITY, 0.90),
        _hit("pen-identity", "03-PEN", IDENTITY_VARIANT, 0.85),
        _hit("bond-slicing", "02-BOND", TOP_SLICING, 0.40),
    ]
    ranked = [h.clause_id for h in mmr(hits, relevance_weight=1.0)]
    assert ranked == ["wol-identity", "pen-identity", "bond-slicing"]


def test_full_diversity_weight_still_leads_with_the_best_hit():
    hits = [
        _hit("wol-identity", "01-WOL", IDENTITY, 0.90),
        _hit("pen-identity", "03-PEN", IDENTITY_VARIANT, 0.85),
        _hit("bond-slicing", "02-BOND", TOP_SLICING, 0.40),
    ]
    ranked = mmr(hits, relevance_weight=0.0)
    assert ranked[0].clause_id == "wol-identity"
    assert ranked[1].clause_id == "bond-slicing"


def test_the_re_rank_is_deterministic():
    hits = [
        _hit("a", "01-WOL", IDENTITY, 0.9),
        _hit("b", "03-PEN", IDENTITY_VARIANT, 0.9),  # a deliberate score tie
        _hit("c", "02-BOND", TOP_SLICING, 0.9),
    ]
    first = [h.clause_id for h in mmr(hits)]
    assert first == [h.clause_id for h in mmr(hits)]
    assert first == [h.clause_id for h in mmr(list(hits))]


def test_scores_are_preserved_not_overwritten():
    # The score stays the retrieval score; MMR changes order, not relevance.
    hits = [_hit("a", "01-WOL", IDENTITY, 0.9), _hit("b", "02-BOND", TOP_SLICING, 0.4)]
    assert [h.score for h in mmr(hits)] == [0.9, 0.4]


def test_identical_scores_across_identical_text_still_drop_the_duplicate():
    hits = [
        _hit("a", "01-WOL", IDENTITY, 0.5),
        _hit("b", "03-PEN", IDENTITY, 0.5),
        _hit("c", "02-BOND", TOP_SLICING, 0.5),
    ]
    ranked = [h.clause_id for h in mmr(hits, top_k=2)]
    assert ranked == ["a", "c"]
