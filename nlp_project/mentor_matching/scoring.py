"""Weighted scoring logic for mentor-mentee candidate pairs."""

from __future__ import annotations

import re
from typing import Dict, Sequence, Set, Tuple

from .constants import (
    CORE_MATCH_SHARE,
    DEFAULT_BASE_WEIGHTS,
    DEGREE_EXACT_MULTI_BONUS_CAP,
    DEGREE_EXACT_MULTI_BONUS_STEP,
    DEGREE_PARTIAL_MULTI_BONUS_CAP,
    DEGREE_PARTIAL_MULTI_BONUS_STEP,
    DEGREE_SEMANTIC_WEIGHT,
    DEGREE_STRUCTURED_WEIGHT,
    EXTRA_MATCH_SHARE,
    FACTOR_KEYS,
    IMPORTANCE_MULTIPLIER,
    INDUSTRY_BROAD_WEIGHT,
    INDUSTRY_HARD_FLOOR,
    INDUSTRY_NICHE_WEIGHT,
    LOW_INDUSTRY_PENALTY,
    MATCH_BAND_DECENT,
    MATCH_BAND_EXCEPTIONAL,
    MATCH_BAND_POSSIBLE,
    MATCH_BAND_STRONG,
    SCORE_CURVE_EXPONENT,
)
from .embeddings import semantic_similarity
from .models import Mentee, Mentor, PairScore
from .state_store import MatchingState


CORE_FACTORS = ("industry", "degree")
EXTRA_FACTORS = ("personality", "identity", "orgs", "grad_year")

NICHE_TOKEN_WEIGHTS = {
    "analog": 1.85,
    "mixed_signal": 1.80,
    "rf": 1.55,
    "power_management_ic": 1.70,
    "asic": 1.60,
    "rtl": 1.55,
    "fpga": 1.45,
    "embedded_firmware": 1.35,
    "power_systems": 1.20,
    "signal_processing": 1.25,
    "software": 0.85,
    "robotics": 0.95,
    "cyber": 1.00,
}

HIGH_INFORMATION_FAMILIES = {
    "analog",
    "mixed_signal",
    "rf",
    "power_management_ic",
    "asic",
    "rtl",
    "fpga",
    "embedded_firmware",
}


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


def _canonicalize_domain_token(token: str) -> str:
    key = token.strip().lower()
    groups = {
        "analog": {"analog", "analogic"},
        "mixed_signal": {"mixed", "mixedsignal", "mixedsignals", "ams", "ic", "ics"},
        "rf": {"rf", "wireless", "antenna", "transceiver", "microwave", "mmwave"},
        "power_management_ic": {"pmic", "powermanagement", "powermanagement", "regulator", "regulators"},
        "asic": {"asic", "vlsi", "semiconductor", "silicon"},
        "rtl": {"rtl", "verilog", "systemverilog", "hdl", "uvm"},
        "fpga": {"fpga", "fpgas"},
        "embedded_firmware": {"embedded", "firmware", "microcontroller", "baremetal", "rtos"},
        "power_systems": {
            "power",
            "grid",
            "energy",
            "utility",
            "utilities",
            "renewable",
            "rail",
            "railway",
            "infrastructure",
            "transportation",
        },
        "ml_ai": {"ml", "ai", "machine", "learning", "neural", "llm"},
        "software": {"software", "backend", "frontend", "fullstack", "app", "application", "web", "cloud"},
        "signal_processing": {
            "rf",
            "signal",
            "signals",
            "communications",
            "wireless",
            "transceiver",
            "sensing",
            "sensor",
            "dsp",
            "filter",
            "filters",
        },
        "robotics": {"robotics", "autonomy", "autonomous", "controls"},
        "cyber": {"cybersecurity", "security", "infosec"},
    }
    for canonical, aliases in groups.items():
        if key in aliases:
            return canonical
    return ""


def _technical_token_set(values: Sequence[str]) -> Set[str]:
    tokens: Set[str] = set()
    blocked = {"and", "or", "the", "in", "of", "to", "for", "with", "by"}
    for raw in values:
        text = str(raw).lower()
        # Avoid counting company names as false specialty hits.
        text = text.replace("analog devices", "company_adi")
        text = text.replace("advanced micro devices", "company_amd")
        for token in re.findall(r"[a-z0-9]+", text):
            if len(token) <= 1 or token in blocked:
                continue
            canonical = _canonicalize_domain_token(token)
            if canonical:
                tokens.add(canonical)
    return tokens


def _weighted_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    if not set_a or not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    inter = set_a & set_b
    numer = sum(NICHE_TOKEN_WEIGHTS.get(token, 1.0) for token in inter)
    denom = sum(NICHE_TOKEN_WEIGHTS.get(token, 1.0) for token in union)
    if denom <= 0.0:
        return 0.0
    return numer / denom


def _industry_niche_similarity(mentee: Mentee, mentor: Mentor) -> tuple[float, bool, Set[str], Set[str]]:
    mentee_terms = _technical_token_set(
        list(mentee.interests)
        + list(mentee.help_topics)
        + [mentee.role, mentee.goals, mentee.background]
    )
    mentor_terms = _technical_token_set(
        list(mentor.expertise)
        + list(mentor.help_topics)
        + list(mentor.domain_tags)
        + [mentor.role, mentor.professional_experience, mentor.goals]
    )
    if not mentee_terms or not mentor_terms:
        return 0.0, False, mentee_terms, mentor_terms
    return _weighted_jaccard_similarity(mentee_terms, mentor_terms), True, mentee_terms, mentor_terms


def _high_information_overlap_bonus(mentee_terms: Set[str], mentor_terms: Set[str]) -> float:
    shared = (mentee_terms & mentor_terms) & HIGH_INFORMATION_FAMILIES
    if not shared:
        return 0.0

    bonus = 0.0
    if "analog" in shared:
        bonus += 0.12
    if "mixed_signal" in shared:
        bonus += 0.10
    if "rf" in shared:
        bonus += 0.08
    if "power_management_ic" in shared:
        bonus += 0.06

    bonus += 0.04 * max(0, len(shared) - 1)
    return min(0.24, bonus)


def _industry_similarity(mentee: Mentee, mentor: Mentor) -> float:
    broad = semantic_similarity(mentee.industry_embedding, mentor.industry_embedding)
    niche, niche_available, mentee_terms, mentor_terms = _industry_niche_similarity(mentee, mentor)

    if not niche_available:
        return broad

    combined = (broad * INDUSTRY_BROAD_WEIGHT) + (niche * INDUSTRY_NICHE_WEIGHT)

    # Niche alignment should separate technically close matches from broad-only matches.
    if niche >= 0.70 and broad >= 0.50:
        combined = min(1.0, combined + 0.05)
    elif niche <= 0.10 and broad < 0.55:
        combined *= 0.90

    combined += _high_information_overlap_bonus(mentee_terms, mentor_terms)

    return max(0.0, min(1.0, combined))


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
        (r"\bundergraudate\b", " bs "),
        (r"\bundergraduate\b", " bs "),
        (r"\bundergrad\b", " bs "),
    )

    for pattern, replacement in substitutions:
        clean = re.sub(pattern, replacement, clean)

    clean = re.sub(r"[^a-z0-9]+", " ", clean)
    blocked = {
        "degree", "degrees", "program", "programs", "major", "in", "of",
        "undergraduate", "graduate", "alumni", "university", "college",
        "state", "ncsu", "from", "at",
    }
    tokens = []
    for token in clean.split():
        if not token or token in blocked:
            continue
        if token.isdigit():
            continue
        # Ignore year-like numeric fragments.
        if re.fullmatch(r"\d{4}", token):
            continue
        tokens.append(token)
    if not tokens:
        return ""
    # Order-insensitive signature: treats "MS Computer Engineering" the same as
    # "Computer Engineering - M.S."
    return " ".join(sorted(tokens))


def _canonical_degree_set(values: Sequence[str]) -> Set[str]:
    return {
        canonical
        for canonical in (_canonicalize_degree_value(value) for value in values)
        if canonical
    }


def _degree_tokens(value: str) -> Set[str]:
    canonical = _canonicalize_degree_value(value)
    return {token for token in canonical.split() if token}


def _canonical_level_token(raw_level: str) -> str:
    tokens = _degree_tokens(raw_level)
    for token in ("bs", "ms", "phd", "abm"):
        if token in tokens:
            return token
    return ""


def _mentee_degree_values(mentee: Mentee) -> List[str]:
    values = [value for value in mentee.degree_programs if str(value).strip()]
    level = _canonical_level_token(mentee.education_level or "")
    if level:
        has_level_already = any(level in _degree_tokens(value) for value in values)
        if not has_level_already:
            values.append(level.upper() if level != "phd" else "PhD")
    return values


def _participant_degree_features(values: Sequence[str]) -> tuple[Set[frozenset[str]], Set[frozenset[str]], Set[str]]:
    degree_level_tokens = {"bs", "ms", "phd", "abm"}
    signatures: Set[frozenset[str]] = set()
    program_signatures: Set[frozenset[str]] = set()
    level_tokens: Set[str] = set()

    for value in values:
        tokens = _degree_tokens(value)
        if not tokens:
            continue
        signatures.add(frozenset(tokens))
        level_tokens.update(token for token in tokens if token in degree_level_tokens)
        program_tokens = {token for token in tokens if token not in degree_level_tokens}
        if program_tokens:
            program_signatures.add(frozenset(program_tokens))

    return signatures, program_signatures, level_tokens


def _degree_domain_families(tokens: Set[str]) -> Set[str]:
    families: Set[str] = set()

    electrical_aliases = {"electrical", "electronics", "power", "signal", "signals", "rf", "communications"}
    computer_aliases = {"computer", "computing", "software", "cybersecurity", "networking", "data", "ai", "ml"}

    if tokens & electrical_aliases:
        families.add("electrical_track")
    if tokens & computer_aliases:
        families.add("computer_track")
    if "engineering" in tokens and families:
        families.add("ece_core")

    if not families:
        level_tokens = {"bs", "ms", "phd", "abm"}
        ignored = {"engineering", "engineeringtrack", "track"}
        families.update(token for token in tokens if token not in level_tokens and token not in ignored)

    return families


def _degree_entries(values: Sequence[str]) -> List[tuple[frozenset[str], frozenset[str]]]:
    level_tokens = {"bs", "ms", "phd", "abm"}
    entries: List[tuple[frozenset[str], frozenset[str]]] = []
    for value in values:
        tokens = _degree_tokens(value)
        if not tokens:
            continue
        levels = frozenset(token for token in tokens if token in level_tokens)
        domains = frozenset(_degree_domain_families(tokens))
        entries.append((levels, domains))
    return entries


def _degree_entry_similarity(a: tuple[frozenset[str], frozenset[str]], b: tuple[frozenset[str], frozenset[str]]) -> float:
    levels_a, domains_a = a
    levels_b, domains_b = b

    if domains_a and domains_b:
        domain = len(domains_a & domains_b) / len(domains_a | domains_b)
    else:
        domain = 0.0

    if levels_a and levels_b:
        level = 1.0 if (levels_a & levels_b) else 0.55
    else:
        level = 0.90

    return (0.75 * domain) + (0.25 * level)


def _structured_degree_similarity(mentee_values: Sequence[str], mentor_values: Sequence[str]) -> tuple[float, int]:
    mentee_entries = _degree_entries(mentee_values)
    mentor_entries = _degree_entries(mentor_values)
    if not mentee_entries or not mentor_entries:
        return 0.0, 0

    best_mentee = [max(_degree_entry_similarity(entry, candidate) for candidate in mentor_entries) for entry in mentee_entries]
    best_mentor = [max(_degree_entry_similarity(entry, candidate) for candidate in mentee_entries) for entry in mentor_entries]
    merged = best_mentee + best_mentor
    score = sum(merged) / float(len(merged))
    strong_matches = sum(1 for value in merged if value >= 0.80)
    return score, strong_matches


def _degree_similarity_details(mentee: Mentee, mentor: Mentor) -> tuple[float, int]:
    mentee_degrees = _mentee_degree_values(mentee)
    mentor_degrees = list(mentor.degree_programs)
    canonical_mentee = _canonical_degree_set(mentee_degrees)
    canonical_mentor = _canonical_degree_set(mentor_degrees)
    mentee_signatures, mentee_program_signatures, mentee_levels = _participant_degree_features(mentee_degrees)
    mentor_signatures, mentor_program_signatures, mentor_levels = _participant_degree_features(mentor_degrees)
    structured_score, structured_strong_matches = _structured_degree_similarity(mentee_degrees, mentor_degrees)

    exact_overlap_count = len(canonical_mentee & canonical_mentor)
    if canonical_mentee and canonical_mentor and (canonical_mentee & canonical_mentor):
        # User expectation: if a canonical exact degree overlap exists, this factor is full match.
        return 1.0, exact_overlap_count

    signature_overlap_count = len(mentee_signatures & mentor_signatures)
    if mentee_signatures and mentor_signatures and (mentee_signatures & mentor_signatures):
        return 1.0, signature_overlap_count

    # Also treat program-level overlap + same degree-level overlap as exact.
    program_overlap_count = len(mentee_program_signatures & mentor_program_signatures)
    if mentee_program_signatures and mentor_program_signatures and (mentee_program_signatures & mentor_program_signatures):
        # If one side omitted degree level but program matches exactly, treat as exact.
        if (not mentee_levels) or (not mentor_levels) or (mentee_levels & mentor_levels):
            return 1.0, program_overlap_count

    semantic = semantic_similarity(mentee.degree_embedding, mentor.degree_embedding)
    combined = (semantic * DEGREE_SEMANTIC_WEIGHT) + (structured_score * DEGREE_STRUCTURED_WEIGHT)

    structured_floor = structured_score * 0.90
    if not canonical_mentee or not canonical_mentor:
        return max(semantic, combined, structured_floor), structured_strong_matches

    exact = len(canonical_mentee & canonical_mentor) / len(canonical_mentee | canonical_mentor)
    return max(semantic, exact, combined, structured_floor), structured_strong_matches


def _degree_match_bonus(overlap_count: int, degree_score: float) -> float:
    """
    Small boost when multiple degree entries align.

    One exact degree match already yields degree score 1.0.
    Extra aligned degrees add a bounded pair-level bonus.
    """
    if overlap_count <= 1:
        return 0.0
    if degree_score >= 1.0:
        return min(DEGREE_EXACT_MULTI_BONUS_CAP, DEGREE_EXACT_MULTI_BONUS_STEP * float(overlap_count - 1))
    if degree_score >= 0.75:
        return min(DEGREE_PARTIAL_MULTI_BONUS_CAP, DEGREE_PARTIAL_MULTI_BONUS_STEP * float(overlap_count - 1))
    return 0.0


def _has_vector_signal(vector: Sequence[float]) -> bool:
    return bool(vector) and any(abs(float(value)) > 1e-12 for value in vector)


def _active_factor_flags(mentee: Mentee, mentor: Mentor) -> Dict[str, bool]:
    _, niche_available, _, _ = _industry_niche_similarity(mentee, mentor)
    mentee_degrees = _mentee_degree_values(mentee)
    return {
        "industry": (
            _has_vector_signal(mentee.industry_embedding) and _has_vector_signal(mentor.industry_embedding)
        ) or niche_available,
        "degree": bool(_canonical_degree_set(mentee_degrees))
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
    degree_score, degree_overlap_count = _degree_similarity_details(mentee, mentor)
    component_scores = {
        "industry": _industry_similarity(mentee, mentor),
        "degree": degree_score,
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

    if degree_overlap_count > 1:
        match_score += _degree_match_bonus(degree_overlap_count, component_scores["degree"])

    if match_score > 0.0:
        match_score = match_score ** SCORE_CURVE_EXPONENT
    match_score = max(0.0, min(1.0, match_score))

    display_weights = effective_weights
    match_percent = match_score * 100.0
    if match_percent >= MATCH_BAND_EXCEPTIONAL:
        match_band = "exceptional"
    elif match_percent >= MATCH_BAND_STRONG:
        match_band = "strong"
    elif match_percent >= MATCH_BAND_DECENT:
        match_band = "decent"
    elif match_percent >= MATCH_BAND_POSSIBLE:
        match_band = "possible"
    else:
        match_band = "weak"

    return PairScore(
        mentee_id=mentee.mentee_id,
        mentee_name=mentee.name,
        mentor_id=mentor.mentor_id,
        mentor_name=mentor.name,
        component_scores=component_scores,
        effective_weights=effective_weights,
        display_weights=display_weights,
        match_score=match_score,
        match_band=match_band,
    )
