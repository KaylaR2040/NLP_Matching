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
