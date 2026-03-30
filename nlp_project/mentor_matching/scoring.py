"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Set

from .constants import DEFAULT_BASE_WEIGHTS, FACTOR_KEYS, MIN_WEIGHT
from .embeddings import cosine_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState


def _normalize_items(values: Sequence[str]) -> Set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def jaccard_similarity(values_a: Sequence[str], values_b: Sequence[str]) -> float:
    """Set overlap similarity with guardrails for empty values."""
    set_a = _normalize_items(values_a)
    set_b = _normalize_items(values_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _normalize_weight_map(raw_weights: Dict[str, float]) -> Dict[str, float]:
    cleaned: Dict[str, float] = {}
    for factor in FACTOR_KEYS:
        value = raw_weights.get(factor, DEFAULT_BASE_WEIGHTS[factor])
        cleaned[factor] = max(MIN_WEIGHT, float(value))

    total = sum(cleaned.values())
    if total == 0:
        return {factor: 1.0 / len(FACTOR_KEYS) for factor in FACTOR_KEYS}

    return {factor: cleaned[factor] / total for factor in FACTOR_KEYS}


def compute_effective_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """
    Build final factor weights by combining:
    1) defaults
    2) global admin overrides
    3) mentee-provided rankings
    4) mentee-specific admin overrides
    """
    raw = dict(DEFAULT_BASE_WEIGHTS)

    for factor, value in state.global_weights.items():
        if factor in raw:
            raw[factor] = max(MIN_WEIGHT, float(value))

    for factor, value in (mentee.ranking_weights or {}).items():
        if factor in raw:
            raw[factor] *= max(MIN_WEIGHT, float(value))

    for factor, value in state.mentee_weight_overrides.get(mentee.mentee_id, {}).items():
        if factor in raw:
            raw[factor] = max(MIN_WEIGHT, float(value))

    return _normalize_weight_map(raw)


def _industry_similarity(mentee: Mentee, mentor: Mentor) -> float:
    mentee_values = list(mentee.interests) + list(mentee.topics)
    mentor_values = list(mentor.expertise) + list(mentor.domain_tags)
    return jaccard_similarity(mentee_values, mentor_values)


def _topics_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return jaccard_similarity(mentee.topics, mentor.topics)


def _style_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return jaccard_similarity(mentee.style, mentor.style)


def _availability_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return jaccard_similarity(mentee.availability, mentor.availability)


def _nlp_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return cosine_similarity(mentee.embedding, mentor.embedding)


def score_pair(mentee: Mentee, mentor: Mentor, state: MatchingState) -> PairScore:
    """Score one mentor-mentee pair with weighted factor aggregation."""
    component_scores = {
        "industry": _industry_similarity(mentee, mentor),
        "topics": _topics_similarity(mentee, mentor),
        "style": _style_similarity(mentee, mentor),
        "availability": _availability_similarity(mentee, mentor),
        "nlp": _nlp_similarity(mentee, mentor),
    }

    weights = compute_effective_weights(mentee, state)
    match_score = sum(component_scores[key] * weights[key] for key in FACTOR_KEYS)

    return PairScore(
        mentee_id=mentee.mentee_id,
        mentee_name=mentee.name,
        mentor_id=mentor.mentor_id,
        mentor_name=mentor.name,
        component_scores=component_scores,
        effective_weights=weights,
        match_score=match_score,
    )
