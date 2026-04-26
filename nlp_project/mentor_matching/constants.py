"""Shared constants for mentor-mentee matching."""

from typing import Dict, List, Set

FACTOR_KEYS = ("industry", "degree", "personality", "identity", "orgs", "grad_year")

DEFAULT_BASE_WEIGHTS = {
    "industry": 2.5,
    "degree": 2.0,
    "personality": 1.5,
    "identity": 1.0,
    "orgs": 1.0,
    "grad_year": 1.0,
}

IMPORTANCE_MULTIPLIER = 2.0
MIN_WEIGHT = 0.01

# Score calibration knobs.
INDUSTRY_HARD_FLOOR = 0.20
LOW_INDUSTRY_PENALTY = 0.80
# Industry score = broad_semantic * BROAD + niche_keyword * NICHE + role_relevance * ROLE_RELEVANCE
INDUSTRY_BROAD_WEIGHT = 0.40   # semantic embedding similarity (what broad field they're in)
INDUSTRY_NICHE_WEIGHT = 0.35   # weighted Jaccard over canonical domain tokens (what subfield)
ROLE_RELEVANCE_WEIGHT = 0.15   # mentor's job title vs mentee's career goal
# Penalty applied when mentee/mentor share a cluster but no exact token (adjacent ≠ exact).
ADJACENCY_PENALTY = 0.18

CORE_MATCH_SHARE = 0.95
EXTRA_MATCH_SHARE = 0.05
SCORE_CURVE_EXPONENT = 0.60
DEGREE_SEMANTIC_WEIGHT = 0.55
DEGREE_STRUCTURED_WEIGHT = 0.45
DEGREE_EXACT_MULTI_BONUS_STEP = 0.03
DEGREE_EXACT_MULTI_BONUS_CAP = 0.10
DEGREE_PARTIAL_MULTI_BONUS_STEP = 0.015
DEGREE_PARTIAL_MULTI_BONUS_CAP = 0.05

# Match interpretation bands (percentage cutoffs).
MATCH_BAND_EXCEPTIONAL = 90.0
MATCH_BAND_STRONG = 75.0
MATCH_BAND_DECENT = 55.0
MATCH_BAND_POSSIBLE = 35.0

# Domain specificity: how narrow/rare the domain is (0–1, higher = more specialized).
# Used by _role_relevance_score to weight the value of a role-title hit by domain rarity.
DOMAIN_SPECIFICITY: Dict[str, float] = {
    "analog": 0.95,
    "mixed_signal": 0.95,
    "rf": 0.95,
    "power_management_ic": 0.92,
    "asic": 0.90,
    "rtl": 0.88,
    "fpga": 0.82,
    "embedded_firmware": 0.75,
    "compute_hw": 0.72,
    "power_systems": 0.60,
    "signal_processing": 0.65,
    "cyber": 0.65,
    "robotics": 0.70,
    "ml_ai": 0.55,
    "software": 0.35,
}

# Adjacency clusters: domains within a cluster are related but not identical.
# A mentee with RF interest matched to an analog mentor is "adjacent" — valid but imperfect.
DOMAIN_CLUSTERS: List[Set[str]] = [
    {"analog", "mixed_signal", "rf", "power_management_ic", "signal_processing"},
    {"asic", "rtl", "fpga"},
    {"embedded_firmware", "compute_hw"},
    {"power_systems"},
    {"ml_ai", "software"},
]

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "with",
    "was", "were", "will", "would", "you", "your", "i", "me", "my", "we", "our",
}

DOMAIN_STOP_WORDS = {
    "bs", "b", "b.s", "ms", "m", "m.s", "phd", "ph", "undergraduate", "graduate",
    "degree", "degrees", "program", "programs", "engineering", "engineer", "student",
    "students", "club", "clubs", "team", "society", "association", "university",
    "state", "ncsu", "nc", "school", "current", "other",
}
