"""Sentence segmentation utilities."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import List

try:
    import spacy
except Exception:  # pragma: no cover - optional dependency fallback
    spacy = None


@lru_cache(maxsize=1)
def _get_segmenter():
    """Return a deterministic spaCy pipeline for sentence splitting."""
    if spacy is None:
        raise RuntimeError("spaCy is not installed")
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def segment_sentences(text: str) -> List[str]:
    """Split text into sentences using spaCy sentencizer with regex fallback."""
    if not text or not text.strip():
        return []

    try:
        nlp = _get_segmenter()
        doc = nlp(text.strip())
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if sentences:
            return sentences
    except Exception:
        pass

    fallback = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in fallback if s.strip()]
