"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Set

from .constants import DEFAULT_BASE_WEIGHTS, DOMAIN_STOP_WORDS, FACTOR_KEYS, STOP_WORDS
from .embeddings import cosine_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState


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


def _importance_to_consideration(value: float) -> float:
    """Map 1..4 importance to 0..1 consideration with quadratic emphasis."""
    clamped = min(4.0, max(1.0, float(value)))
    shifted = (clamped - 1.0) / 3.0
    return shifted * shifted


def _normalize_weight_map(raw_weights: Dict[str, float]) -> Dict[str, float]:
    cleaned: Dict[str, float] = {}
    for factor in FACTOR_KEYS:
        value = raw_weights.get(factor, DEFAULT_BASE_WEIGHTS[factor])
        cleaned[factor] = max(0.0, float(value))

    total = sum(cleaned.values())
    if total == 0:
        return {factor: 1.0 / len(FACTOR_KEYS) for factor in FACTOR_KEYS}

    return {factor: cleaned[factor] / total for factor in FACTOR_KEYS}


def _build_raw_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """Build unnormalized factor weights from 1..4 importance selections."""
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

    return {
        factor: _importance_to_consideration(float(raw.get(factor, DEFAULT_BASE_WEIGHTS[factor])))
        for factor in FACTOR_KEYS
    }


def compute_effective_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """
    Build final factor weights by combining:
    1) defaults
    2) global admin overrides
    3) mentee-provided rankings
    4) mentee-specific admin overrides
    """
    return _normalize_weight_map(_build_raw_weights(mentee, state))


def compute_display_weights(mentee: Mentee, state: MatchingState) -> Dict[str, float]:
    """
    Convert the human-facing 1..4 importance scale into 0..100 percentages
    for reporting, independent of the internal normalized scoring weights.
    """
    raw = _build_raw_weights(mentee, state)
    return {
        factor: min(1.0, max(0.0, float(raw.get(factor, 0.0))))
        for factor in FACTOR_KEYS
    }


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
