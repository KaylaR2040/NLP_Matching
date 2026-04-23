"""Shared constants for mentor-mentee matching."""

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
INDUSTRY_BROAD_WEIGHT = 0.65
INDUSTRY_NICHE_WEIGHT = 0.35
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
