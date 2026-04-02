"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Set

from .constants import DEFAULT_BASE_WEIGHTS, DOMAIN_STOP_WORDS, FACTOR_KEYS, STOP_WORDS
from .embeddings import cosine_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState

DIRECT_MATCH_FACTORS = ("industry", "degree", "orgs", "identity", "grad_year")
NLP_FACTOR = "nlp"
NLP_WEIGHT = 0.5
DIRECT_MATCH_SHARE = 0.5
RANKING_TO_PRIORITY = {
    1: 0.0,
    2: 11.0,
    3: 44.0,
    4: 100.0,
}


def _normalize_items(values: Sequence[str]) -> Set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _tokenize_values(values: Sequence[str], extra_stop_words: Set[str] | None = None) -> Set[str]:
    blocked = set(STOP_WORDS) | set(DOMAIN_STOP_WORDS)
    if extra_stop_words:
        blocked |= {token.lower() for token in extra_stop_words}

    tokens: Set[str] = set()
    for value in values:
        text = str(value).strip().lower()
        if not text:
            continue
        text = text.replace("&", " and ")
        text = re.sub(r"\bother:\s*", "", text)
        for token in re.findall(r"[a-z0-9]+", text):
            if len(token) <= 1 or token in blocked:
                continue
            tokens.add(token)
    return tokens


def jaccard_similarity(values_a: Sequence[str], values_b: Sequence[str]) -> float:
    """Set overlap similarity with guardrails for empty values."""
    set_a = _normalize_items(values_a)
    set_b = _normalize_items(values_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _token_overlap_similarity(
    values_a: Sequence[str],
    values_b: Sequence[str],
    *,
    extra_stop_words: Set[str] | None = None,
) -> float:
    tokens_a = _tokenize_values(values_a, extra_stop_words=extra_stop_words)
    tokens_b = _tokenize_values(values_b, extra_stop_words=extra_stop_words)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _hybrid_list_similarity(
    values_a: Sequence[str],
    values_b: Sequence[str],
    *,
    extra_stop_words: Set[str] | None = None,
) -> float:
    exact = jaccard_similarity(values_a, values_b)
    token = _token_overlap_similarity(values_a, values_b, extra_stop_words=extra_stop_words)
    return max(exact, token)


def ranking_to_priority_value(value: float) -> float:
    """Convert a 1..4 importance ranking into its relative direct-match priority."""
    try:
        ranking = int(round(float(value)))
    except (TypeError, ValueError):
        ranking = int(DEFAULT_BASE_WEIGHTS["industry"])
    ranking = min(4, max(1, ranking))
    return RANKING_TO_PRIORITY[ranking]


def _build_raw_rankings(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """Build raw factor rankings from defaults, mentee selections, and overrides."""
    raw = dict(DEFAULT_BASE_WEIGHTS)

    for factor, value in state.global_weights.items():
        if factor in raw:
            raw[factor] = float(value)

    for factor, value in (mentee.ranking_weights or {}).items():
        if factor in raw:
            raw[factor] = float(value)

    for factor, value in state.mentee_weight_overrides.get(mentee.mentee_id, {}).items():
        if factor in raw:
            raw[factor] = float(value)

    return {factor: float(raw.get(factor, DEFAULT_BASE_WEIGHTS[factor])) for factor in FACTOR_KEYS}


def calculate_direct_match_weights(rankings: Dict[str, float]) -> Dict[str, float]:
    """
    Allocate the direct-match half of the final score across the five direct factors.

    If every direct ranking maps to zero priority, the direct half is intentionally left
    unused so NLP still contributes exactly 50% of the final score.
    """
    priorities = {
        factor: ranking_to_priority_value(rankings.get(factor, DEFAULT_BASE_WEIGHTS[factor]))
        for factor in DIRECT_MATCH_FACTORS
    }
    total_priority = sum(priorities.values())

    if total_priority == 0:
        return {factor: 0.0 for factor in DIRECT_MATCH_FACTORS}

    return {
        factor: DIRECT_MATCH_SHARE * (priorities[factor] / total_priority)
        for factor in DIRECT_MATCH_FACTORS
    }


def compute_effective_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """
    Build final factor weights with a fixed 50/50 split:
    - NLP always contributes exactly 50%
    - direct-match factors divide the other 50% by mapped priority
    """
    rankings = _build_raw_rankings(mentee, state)
    weights = {factor: 0.0 for factor in FACTOR_KEYS}
    weights.update(calculate_direct_match_weights(rankings))
    weights[NLP_FACTOR] = NLP_WEIGHT
    return weights


def compute_display_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """Return final scoring weights for reporting as fractions of 1.0."""
    return compute_effective_weights(mentee, state)


def _industry_similarity(mentee: Mentee, mentor: Mentor) -> float:
    mentee_values = list(mentee.interests) + list(mentee.help_topics)
    mentor_values = list(mentor.expertise) + list(mentor.domain_tags)
    return _hybrid_list_similarity(mentee_values, mentor_values)


def _degree_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return _hybrid_list_similarity(mentee.degree_programs, mentor.degree_programs)


def _orgs_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return _hybrid_list_similarity(
        mentee.student_orgs,
        mentor.student_orgs,
        extra_stop_words={"pack", "university", "state", "club", "team", "lab"},
    )


def _identity_similarity(mentee: Mentee, mentor: Mentor) -> float:
    if not mentee.pronouns or not mentor.pronouns:
        return 0.5
    return 1.0 if mentee.pronouns.strip().lower() == mentor.pronouns.strip().lower() else 0.2


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


def _nlp_similarity(mentee: Mentee, mentor: Mentor) -> float:
    return cosine_similarity(mentee.embedding, mentor.embedding)


def score_pair(mentee: Mentee, mentor: Mentor, state: MatchingState) -> PairScore:
    """Score one mentor-mentee pair with weighted factor aggregation."""
    component_scores = {
        "industry": _industry_similarity(mentee, mentor),
        "degree": _degree_similarity(mentee, mentor),
        "orgs": _orgs_similarity(mentee, mentor),
        "identity": _identity_similarity(mentee, mentor),
        "grad_year": _grad_year_similarity(mentee, mentor),
        "nlp": _nlp_similarity(mentee, mentor),
    }

    weights = compute_effective_weights(mentee, state)
    display_weights = compute_display_weights(mentee, state)
    match_score = sum(component_scores[key] * weights[key] for key in FACTOR_KEYS)

    return PairScore(
        mentee_id=mentee.mentee_id,
        mentee_name=mentee.name,
        mentor_id=mentor.mentor_id,
        mentor_name=mentor.name,
        component_scores=component_scores,
        effective_weights=weights,
        display_weights=display_weights,
        match_score=match_score,
    )
