"""Shared constants for mentor-mentee matching."""

FACTOR_KEYS = ("industry", "topics", "style", "availability", "nlp")

DEFAULT_BASE_WEIGHTS = {
    "industry": 1.0,
    "topics": 1.0,
    "style": 1.0,
    "availability": 1.0,
    "nlp": 1.0,
}

MIN_WEIGHT = 0.05

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "with",
    "was", "were", "will", "would", "you", "your", "i", "me", "my", "we", "our",
}
