"""Stop-word removal utilities."""

from __future__ import annotations

from typing import Iterable, List, Optional, Set

try:
    from spacy.lang.en.stop_words import STOP_WORDS
except Exception:  # pragma: no cover - optional dependency fallback
    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }


def remove_stopwords(tokens: Iterable[str], extra_stopwords: Optional[Set[str]] = None) -> List[str]:
    """Remove stop words case-insensitively from tokens."""
    stop_words = {word.lower() for word in STOP_WORDS}
    if extra_stopwords:
        stop_words.update({word.lower() for word in extra_stopwords})

    return [token for token in tokens if token.lower() not in stop_words]
