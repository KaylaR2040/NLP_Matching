"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

import re
from typing import Dict, Sequence, Set

from .constants import DEFAULT_BASE_WEIGHTS, FACTOR_KEYS, IMPORTANCE_MULTIPLIER
from .embeddings import semantic_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState


INDUSTRY_HARD_FLOOR = 0.30
LOW_INDUSTRY_PENALTY = 0.50
CORE_FACTORS = ("industry", "degree")
EXTRA_FACTORS = ("personality", "identity", "orgs", "grad_year")
CORE_MATCH_SHARE = 0.80
EXTRA_MATCH_SHARE = 0.20
SCORE_CURVE_EXPONENT = 0.85


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


def _safe_year(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonicalize_degree_value(value: str) -> str:
    clean = (value or "").strip().lower()
    if not clean:
        return ""

    substitutions = (
        (r"\bm\.?\s*s\.?\b", " ms "),
        (r"\bmaster(?:'s|s)?(?:\s+of\s+science)?\b", " ms "),
        (r"\bb\.?\s*s\.?\b", " bs "),
        (r"\bbachelor(?:'s|s)?(?:\s+of\s+science)?\b", " bs "),
        (r"\bph\.?\s*d\.?\b", " phd "),
        (r"\bdoctor(?:al|ate)?\b", " phd "),
        (r"\belectrical\s*&\s*computer\s*engineering\b", " electrical computer engineering "),
        (r"\belectrical\s+and\s+computer\s+engineering\b", " electrical computer engineering "),
    )

    for pattern, replacement in substitutions:
        clean = re.sub(pattern, replacement, clean)

    clean = re.sub(r"[^a-z0-9]+", " ", clean)
    blocked = {"degree", "degrees", "program", "programs", "major", "in", "of"}
    tokens = [token for token in clean.split() if token and token not in blocked]
    return " ".join(tokens)


def _canonical_degree_set(values: Sequence[str]) -> Set[str]:
    return {
        canonical
        for canonical in (_canonicalize_degree_value(value) for value in values)
        if canonical
    }


def _degree_similarity(mentee: Mentee, mentor: Mentor) -> float:
    mentee_degrees = list(mentee.degree_programs)
    if mentee.education_level:
        mentee_degrees.append(mentee.education_level)

    mentor_degrees = list(mentor.degree_programs)
    canonical_mentee = _canonical_degree_set(mentee_degrees)
    canonical_mentor = _canonical_degree_set(mentor_degrees)

    if canonical_mentee and canonical_mentor and (canonical_mentee & canonical_mentor):
        # User expectation: if a canonical exact degree overlap exists, this factor is full match.
        return 1.0

    semantic = semantic_similarity(mentee.degree_embedding, mentor.degree_embedding)
    if not canonical_mentee or not canonical_mentor:
        return semantic

    exact = len(canonical_mentee & canonical_mentor) / len(canonical_mentee | canonical_mentor)
    return max(semantic, exact)


def _has_vector_signal(vector: Sequence[float]) -> bool:
    return bool(vector) and any(abs(float(value)) > 1e-12 for value in vector)


def _active_factor_flags(mentee: Mentee, mentor: Mentor) -> Dict[str, bool]:
    return {
        "industry": _has_vector_signal(mentee.industry_embedding) and _has_vector_signal(mentor.industry_embedding),
        "degree": bool(_canonical_degree_set(list(mentee.degree_programs) + ([mentee.education_level] if mentee.education_level else [])))
        and bool(_canonical_degree_set(mentor.degree_programs)),
        "personality": _has_vector_signal(mentee.personality_embedding) and _has_vector_signal(mentor.personality_embedding),
        "identity": bool((mentee.pronouns or "").strip()) and bool((mentor.pronouns or "").strip()),
        "orgs": bool(mentee.student_orgs) and bool(mentor.student_orgs),
        "grad_year": _safe_year(mentee.graduation_year) is not None and _safe_year(mentor.graduation_year) is not None,
    }


def _weighted_average(scores: Dict[str, float], weights: Dict[str, float], factors: Sequence[str]) -> float:
    active_weights = {factor: weights.get(factor, 0.0) for factor in factors if weights.get(factor, 0.0) > 0.0}
    denom = sum(active_weights.values())
    if denom <= 0.0:
        return 0.0
    return sum(scores[factor] * active_weights[factor] for factor in active_weights) / denom


def _pair_factor_weights(
    raw_weights: Dict[str, float],
    active_flags: Dict[str, bool],
) -> Dict[str, float]:
    display = {factor: 0.0 for factor in FACTOR_KEYS}

    active_core = [factor for factor in CORE_FACTORS if active_flags.get(factor, False)]
    active_extras = [factor for factor in EXTRA_FACTORS if active_flags.get(factor, False)]

    core_share = CORE_MATCH_SHARE if active_core else 0.0
    extras_share = EXTRA_MATCH_SHARE if active_extras else 0.0
    share_total = core_share + extras_share
    if share_total <= 0.0:
        return display

    core_share /= share_total
    extras_share /= share_total

    if active_core:
        core_total = sum(raw_weights[factor] for factor in active_core)
        if core_total > 0.0:
            for factor in active_core:
                display[factor] = core_share * (raw_weights[factor] / core_total)

    if active_extras:
        extras_total = sum(raw_weights[factor] for factor in active_extras)
        if extras_total > 0.0:
            for factor in active_extras:
                display[factor] = extras_share * (raw_weights[factor] / extras_total)

    return display


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
        "degree": _degree_similarity(mentee, mentor),
        "personality": semantic_similarity(mentee.personality_embedding, mentor.personality_embedding),
        "identity": _identity_similarity(mentee, mentor),
        "orgs": jaccard_similarity(mentee.student_orgs, mentor.student_orgs),
        "grad_year": _grad_year_similarity(mentee, mentor),
    }

    raw_weights = compute_effective_weights(mentee, state)
    active_flags = _active_factor_flags(mentee, mentor)
    effective_weights = _pair_factor_weights(raw_weights, active_flags)

    core_factors = [factor for factor in CORE_FACTORS if active_flags.get(factor, False)]
    extra_factors = [factor for factor in EXTRA_FACTORS if active_flags.get(factor, False)]

    core_score = _weighted_average(component_scores, raw_weights, core_factors)
    extras_score = _weighted_average(component_scores, raw_weights, extra_factors)

    core_share = CORE_MATCH_SHARE if core_factors else 0.0
    extras_share = EXTRA_MATCH_SHARE if extra_factors else 0.0
    total_share = core_share + extras_share
    if total_share > 0.0:
        core_share /= total_share
        extras_share /= total_share
        match_score = (core_score * core_share) + (extras_score * extras_share)
    else:
        match_score = 0.0

    if active_flags.get("industry", False) and component_scores["industry"] < INDUSTRY_HARD_FLOOR:
        match_score *= LOW_INDUSTRY_PENALTY

    if match_score > 0.0:
        match_score = match_score ** SCORE_CURVE_EXPONENT
    match_score = max(0.0, min(1.0, match_score))

    display_weights = effective_weights

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
