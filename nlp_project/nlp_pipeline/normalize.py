"""Text normalization (stemming and lemmatization)."""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency fallback
    spacy = None

from .tokenizing import tokenize_text


@lru_cache(maxsize=1)
def _get_lemmatizer():
    """Load spaCy English model for lemmatization, with lightweight fallback."""
    if spacy is None:
        raise RuntimeError("spaCy is not installed")
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return spacy.blank("en")


def _simple_stem(token: str) -> str:
    """Deterministic fallback stemmer when NLTK is unavailable."""
    lowered = token.lower()
    for suffix in ("ingly", "edly", "ing", "ed", "ly", "es", "s"):
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 2:
            return lowered[: -len(suffix)]
    return lowered


def stem_tokens(tokens: Iterable[str]) -> List[str]:
    """Stem a token stream using NLTK PorterStemmer if available."""
    try:
        from nltk.stem import PorterStemmer

        stemmer = PorterStemmer()
        return [stemmer.stem(token) for token in tokens]
    except Exception:
        return [_simple_stem(token) for token in tokens]


def lemmatize_text(text: str) -> List[str]:
    """Lemmatize text with spaCy, falling back to lowercase tokens."""
    if not text or not text.strip():
        return []

    try:
        nlp = _get_lemmatizer()
        doc = nlp(text)

        lemmas: List[str] = []
        for token in doc:
            if not token.text.strip():
                continue
            lemma = token.lemma_ if token.lemma_ else token.text.lower()
            if lemma == "-PRON-":
                lemma = token.text.lower()
            lemmas.append(lemma)

        if lemmas:
            return lemmas
    except Exception:
        pass

    return [tok.lower() for tok in tokenize_text(text)]


def normalize_text(text: str, use_stemming: bool = False) -> List[str]:
    """Return normalized tokens via lemmatization and optional stemming."""
    lemmas = lemmatize_text(text)
    if use_stemming:
        return stem_tokens(lemmas)
    return lemmas
