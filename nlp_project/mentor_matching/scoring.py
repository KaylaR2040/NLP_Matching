"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

from typing import Dict, Sequence, Set

from .constants import DEFAULT_BASE_WEIGHTS, FACTOR_KEYS, IMPORTANCE_MULTIPLIER
from .embeddings import semantic_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState


INDUSTRY_HARD_FLOOR = 0.30
LOW_INDUSTRY_PENALTY = 0.50


def _normalize_items(values: Sequence[str]) -> Set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def jaccard_similarity(values_a: Sequence[str], values_b: Sequence[str]) -> float:
    """Set overlap similarity with guardrails for empty values."""
    set_a = _normalize_items(values_a)
    set_b = _normalize_items(values_b)
    if not set_a and not set_b:
        return 0.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _identity_similarity(mentee: Mentee, mentor: Mentor) -> float:
    if not mentee.pronouns or not mentor.pronouns:
        return 0.0
    return 1.0 if mentee.pronouns.strip().lower() == mentor.pronouns.strip().lower() else 0.0


def _grad_year_similarity(mentee: Mentee, mentor: Mentor) -> float:
    try:
        mentee_year = int(mentee.graduation_year)
    except (TypeError, ValueError):
        return 0.5

    try:
        mentor_year = int(mentor.graduation_year)
    except (TypeError, ValueError):
        return 0.5

    diff = abs(mentee_year - mentor_year)
    if diff <= 5:
        return max(0.25, 1.0 - (diff * 0.15))
    if diff <= 10:
        return 0.15
    return 0.05


def _rank_multiplier(rank: int) -> float:
    normalized = min(4, max(1, int(rank)))
    if normalized >= 4:
        return IMPORTANCE_MULTIPLIER
    if normalized == 3:
        return 1.5
    if normalized == 2:
        return 1.0
    return 0.5


def _resolve_factor_rank(mentee: Mentee, state: MatchingState, factor: str) -> int:
    rank = int((mentee.ranking_preferences or {}).get(factor, 2))

    if factor in state.global_weights:
        rank = int(round(float(state.global_weights[factor])))

    mentee_override = state.mentee_weight_overrides.get(mentee.mentee_id, {})
    if factor in mentee_override:
        rank = int(round(float(mentee_override[factor])))

    return min(4, max(1, rank))


def compute_effective_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """Build non-normalized factor weights for this mentee."""
    weights: Dict[str, float] = {}
    for factor in FACTOR_KEYS:
        base_weight = float(DEFAULT_BASE_WEIGHTS.get(factor, 1.0))
        rank = _resolve_factor_rank(mentee, state, factor)
        weights[factor] = base_weight * _rank_multiplier(rank)
    return weights


def compute_display_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """Return weights normalized to fractions that sum to 1.0."""
    effective = compute_effective_weights(mentee, state)
    total = sum(effective.values())
    if total <= 0.0:
        return {factor: 0.0 for factor in FACTOR_KEYS}
    return {factor: effective[factor] / total for factor in FACTOR_KEYS}


def score_pair(mentee: Mentee, mentor: Mentor, state: MatchingState) -> PairScore:
    """
    Score one mentor-mentee pair using segmented semantic vectors + direct factors.
    """
    component_scores = {
        "industry": semantic_similarity(mentee.industry_embedding, mentor.industry_embedding),
        "degree": semantic_similarity(mentee.degree_embedding, mentor.degree_embedding),
        "personality": semantic_similarity(mentee.personality_embedding, mentor.personality_embedding),
        "identity": _identity_similarity(mentee, mentor),
        "orgs": jaccard_similarity(mentee.student_orgs, mentor.student_orgs),
        "grad_year": _grad_year_similarity(mentee, mentor),
    }

    effective_weights = compute_effective_weights(mentee, state)
    weighted_sum = sum(component_scores[factor] * effective_weights[factor] for factor in FACTOR_KEYS)
    total_weight = sum(effective_weights.values())
    match_score = (weighted_sum / total_weight) if total_weight else 0.0

    if component_scores["industry"] < INDUSTRY_HARD_FLOOR:
        match_score *= LOW_INDUSTRY_PENALTY

    display_weights = compute_display_weights(mentee, state)

    return PairScore(
        mentee_id=mentee.mentee_id,
        mentee_name=mentee.name,
        mentor_id=mentor.mentor_id,
        mentor_name=mentor.name,
        component_scores=component_scores,
        effective_weights=effective_weights,
        display_weights=display_weights,
        match_score=match_score,
    )
