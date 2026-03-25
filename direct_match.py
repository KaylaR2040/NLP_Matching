"""Similarity scoring + greedy assignment with NLP-aware weights."""

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

Pair = Dict[str, object]


# =============================================================================
# Similarity helpers
# =============================================================================
def _normalize_list(values: Sequence[str]) -> set:
    if not values:
        return set()
    return {str(item).strip().lower() for item in values if str(item).strip()}


def jaccard(list_a: Sequence[str], list_b: Sequence[str]) -> float:
    set_a = _normalize_list(list_a)
    set_b = _normalize_list(list_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def cosine(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    if vec_a is None or vec_b is None:
        return 0.0
    if vec_a.shape[0] == 0 or vec_b.shape[0] == 0:
        return 0.0
    denom = (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


# =============================================================================
# Pair scoring
# =============================================================================
def score_pair(mentee, mentor) -> Pair:
    """Calculate weighted score across categorical overlap + NLP similarity."""
    weights = mentee.weights or {}

    sims = {
        "industry": jaccard(mentee.industries, mentor.industries),
        "degree": jaccard(mentee.major, mentor.degrees_completed),
        "interest": jaccard(getattr(mentee, "interests", []), getattr(mentor, "interests", [])),
        "organization": jaccard(getattr(mentee, "orgs", []), getattr(mentor, "orgs", [])),
        "nlp": cosine(getattr(mentee, "embedding", None), getattr(mentor, "embedding", None)),
    }

    # Weighted average per golden-path formula
    weight_sum = sum(weights.values()) + 1.0  # +1 to keep NLP at base weight=1
    weighted_sum = (
        sims["industry"] * weights.get("industry", 1.0)
        + sims["degree"] * weights.get("degree", 1.0)
        + sims["interest"] * weights.get("interest", 1.0)
        + sims["organization"] * weights.get("organization", 1.0)
        + sims["nlp"] * 1.0
    )
    match_score = weighted_sum / weight_sum if weight_sum else 0.0

    return {
        "mentee_email": mentee.email,
        "mentee_name": mentee.name,
        "mentor_email": mentor.email,
        "mentor_name": mentor.name,
        "scores": sims,
        "weights": weights,
        "match_score": match_score,
    }


# =============================================================================
# Ranking
# =============================================================================
def build_ranked_pairs(
    mentees: Sequence, mentors: Sequence, prohibited: Iterable[Tuple[str, str]] | None = None
) -> List[Pair]:
    prohibited = set(prohibited or [])
    pairs: List[Pair] = []

    for mentee in mentees:
        for mentor in mentors:
            if (mentee.email, mentor.email) in prohibited:
                continue
            pairs.append(score_pair(mentee, mentor))

    return sorted(pairs, key=lambda row: row["match_score"], reverse=True)


# =============================================================================
# Greedy Assignment
# =============================================================================
def greedy_assign(ranked_pairs: Sequence[Pair], locked: Iterable[Tuple[str, str]] | None = None):
    """Greedily assign mentors to mentees honoring any locked pairs first."""
    locked = list(locked or [])
    name_lookup_mentee = {pair["mentee_email"]: pair.get("mentee_name") for pair in ranked_pairs}
    name_lookup_mentor = {pair["mentor_email"]: pair.get("mentor_name") for pair in ranked_pairs}
    assigned_mentees = {m for m, _ in locked}
    assigned_mentors = {n for _, n in locked}
    assignments: List[Pair] = []

    # Seed assignments with locked pairs (score left as None)
    for mentee_email, mentor_email in locked:
        assignments.append(
            {
                "mentee_email": mentee_email,
                "mentor_email": mentor_email,
                "mentee_name": name_lookup_mentee.get(mentee_email),
                "mentor_name": name_lookup_mentor.get(mentor_email),
                "match_score": None,
                "locked": True,
            }
        )

    for pair in ranked_pairs:
        mentee_email = pair["mentee_email"]
        mentor_email = pair["mentor_email"]

        if mentee_email in assigned_mentees or mentor_email in assigned_mentors:
            continue

        assignments.append(pair)
        assigned_mentees.add(mentee_email)
        assigned_mentors.add(mentor_email)

    return assignments
