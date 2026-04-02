"""Shared constants for mentor-mentee matching."""

FACTOR_KEYS = ("industry", "degree", "orgs", "identity", "grad_year", "nlp")

DEFAULT_BASE_WEIGHTS = {
    "industry": 2.0,
    "degree": 2.0,
    "orgs": 2.0,
    "identity": 2.0,
    "grad_year": 2.0,
    "nlp": 2.0,
}

MIN_WEIGHT = 0.05

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
