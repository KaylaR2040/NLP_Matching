"""Tokenization utilities."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency fallback
    spacy = None


@lru_cache(maxsize=1)
def _get_tokenizer():
    """Return spaCy tokenizer-only pipeline."""
    if spacy is None:
        raise RuntimeError("spaCy is not installed")
    return spacy.blank("en")


def tokenize_text(text: str) -> List[str]:
    """Tokenize input text into words and punctuation tokens."""
    if not text or not text.strip():
        return []

    try:
        nlp = _get_tokenizer()
        doc = nlp(text)
        tokens = [tok.text for tok in doc if tok.text.strip()]
        if tokens:
            return tokens
    except Exception:
        pass

    return re.findall(r"\w+(?:'\w+)?|[^\w\s]", text)
