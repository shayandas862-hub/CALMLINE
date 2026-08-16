"""Maximal Marginal Relevance — diversity re-ranking for cross-product queries.

The KB repeats identity, data-protection and authority rules inside each product
document deliberately, so that every chunk answers alone (`data/kb/README.md`
§4). The cost is that a query spanning products retrieves the same rule four
times and spends the context window restating it.

A `doc` filter fixes the common case; MMR fixes the case a filter cannot —
a genuinely cross-product question, where the useful answer is one copy of the
shared rule plus whatever else is relevant (AD-CL-025).

The greedy MMR selection, per Carbonell & Goldstein (1998): repeatedly take the
candidate maximising

    relevance_weight · relevance − (1 − relevance_weight) · max_similarity_to_picked

Similarity is token overlap (Jaccard), not embeddings — the duplication being
collapsed is near-identical *wording*, which overlap detects directly, with no
API call and no non-determinism.
"""

from __future__ import annotations

import re
from typing import Callable

from src.retrieval.hybrid_search import ClauseHit

_DEFAULT_TOP_K = 8
# Equal weight to relevance and novelty. Anything higher cannot do the job it
# exists for: a second copy of a shared rule scores ~0.85 on similarity but sits
# only a few points below the first copy on relevance, so at λ=0.7 the near
# duplicate still wins and the four-identical-hits problem survives the re-rank.
_DEFAULT_RELEVANCE_WEIGHT = 0.5

_WORD = re.compile(r"[a-z0-9]+")


def token_similarity(left: str, right: str) -> float:
    """Jaccard overlap of the two texts' word sets — 1.0 identical, 0.0 disjoint."""
    a, b = set(_WORD.findall(left.lower())), set(_WORD.findall(right.lower()))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def mmr(
    hits: list[ClauseHit],
    *,
    top_k: int = _DEFAULT_TOP_K,
    relevance_weight: float = _DEFAULT_RELEVANCE_WEIGHT,
    similarity: Callable[[str, str], float] = token_similarity,
) -> list[ClauseHit]:
    """Re-rank `hits` for diversity, keeping the most relevant hit first.

    `relevance_weight` is the MMR λ: 1.0 disables diversity and reproduces the
    relevance ranking; 0.0 maximises spread but still leads with the best hit.
    Order is fully determined by (score, input position) — never by set iteration
    — so the same hits always re-rank the same way.
    """
    if not hits:
        return []

    relevance = _normalised_relevance(hits)
    remaining = list(range(len(hits)))
    selected: list[int] = []

    while remaining and len(selected) < top_k:
        best = max(
            remaining,
            key=lambda index: (
                _score(index, selected, hits, relevance, relevance_weight, similarity),
                -index,  # a tie goes to the earlier (higher-ranked) candidate
            ),
        )
        selected.append(best)
        remaining.remove(best)

    return [hits[index] for index in selected]


def _score(index: int, selected: list[int], hits: list[ClauseHit],
           relevance: list[float], relevance_weight: float,
           similarity: Callable[[str, str], float]) -> float:
    redundancy = max(
        (similarity(hits[index].text, hits[chosen].text) for chosen in selected),
        default=0.0,
    )
    return relevance_weight * relevance[index] - (1.0 - relevance_weight) * redundancy


def _normalised_relevance(hits: list[ClauseHit]) -> list[float]:
    """Scale scores against the best one, so they compare with a 0…1 similarity.

    RRF scores sit around 0.03; mixing them raw with Jaccard would let redundancy
    decide every comparison. Divided by the maximum rather than min-max scaled,
    because min-max pins the weakest candidate at exactly 0.0 — on a short
    candidate list that throws away most of what the scores said (a hit at 0.40
    against a best of 0.90 is respectable, not worthless).
    """
    scores = [hit.score for hit in hits]
    best = max(scores)
    if best <= 0:
        return [1.0] * len(hits)  # no usable signal; diversity orders them
    return [score / best for score in scores]
