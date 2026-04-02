"""Deterministic NLP preprocessing utilities."""

from __future__ import annotations

import re
from typing import Iterable, List

from .constants import STOP_WORDS


def segment_sentences(text: str) -> List[str]:
    """Split text into sentences with a lightweight regex."""
    clean = (text or "").strip()
    if not clean:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]


def tokenize_text(text: str) -> List[str]:
    """Split text into words and punctuation tokens."""
    return re.findall(r"\w+(?:'\w+)?|[^\w\s]", text or "")


def remove_stopwords(tokens: Iterable[str]) -> List[str]:
    """Remove common English stop words from tokens."""
    return [token for token in tokens if token.lower() not in STOP_WORDS]


def stem_tokens(tokens: Iterable[str]) -> List[str]:
    """Apply a deterministic lightweight stemming fallback."""
    stems: List[str] = []
    for token in tokens:
        lowered = token.lower()
        for suffix in ("ingly", "edly", "ing", "ed", "ly", "es", "s"):
            if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
                lowered = lowered[: -len(suffix)]
                break
        stems.append(lowered)
    return stems


def lemmatize_tokens(tokens: Iterable[str]) -> List[str]:
    """Lowercase fallback lemmatization."""
    return [token.lower() for token in tokens if token.strip()]


def attach_nlp_features(people: Iterable[object], use_stemming: bool = False) -> None:
    """
    Populate NLP fields on participants in-place.

    This corresponds to pipeline step 3 in ``MatchingPipeline.run``.
    Important: this is deterministic preprocessing, not model training.
    """
    for person in people:
        raw_text = person.profile_text()

        # Sentence splitting is only for inspection/debugging.
        person.nlp.sentences = segment_sentences(raw_text)
        # Tokenization breaks the profile text into individual lexical units.
        person.nlp.tokens = tokenize_text(raw_text)
        # Stopword removal drops very common low-signal words like "the" and "and".
        person.nlp.filtered_tokens = remove_stopwords(person.nlp.tokens)
        # Stemming and lemmatization are simple normalization passes.
        person.nlp.stemmed_tokens = stem_tokens(person.nlp.filtered_tokens)
        person.nlp.lemmatized_tokens = lemmatize_tokens(person.nlp.filtered_tokens)

        # The normalized text is the actual input to embedding generation in the next step.
        final_tokens = person.nlp.stemmed_tokens if use_stemming else person.nlp.lemmatized_tokens
        person.nlp.normalized_text = " ".join(token for token in final_tokens if token.strip())
