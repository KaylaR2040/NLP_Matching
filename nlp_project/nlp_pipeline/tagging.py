"""POS tagging and named entity recognition utilities."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency fallback
    spacy = None


@lru_cache(maxsize=1)
def _get_tagger():
    """Load spaCy model for POS and NER."""
    if spacy is None:
        raise RuntimeError("spaCy is not installed")
    return spacy.load("en_core_web_sm")


def pos_tag_text(text: str) -> List[Tuple[str, str]]:
    """Return (token, POS) tuples for input text."""
    if not text or not text.strip():
        return []

    try:
        nlp = _get_tagger()
        doc = nlp(text)
        return [(token.text, token.pos_) for token in doc if token.text.strip()]
    except Exception:
        return [(token, "") for token in text.split()]


def named_entities(text: str) -> List[Tuple[str, str]]:
    """Return (entity_text, entity_label) tuples for input text."""
    if not text or not text.strip():
        return []

    try:
        nlp = _get_tagger()
        doc = nlp(text)
        return [(ent.text, ent.label_) for ent in doc.ents]
    except Exception:
        return []
