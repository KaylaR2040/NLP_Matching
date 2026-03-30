"""Deterministic local text embeddings for reliable matching."""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, List


EMBEDDING_DIM = 256


def _hash_token(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % EMBEDDING_DIM


def _normalize(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def encode_text(text: str) -> List[float]:
    """Create a stable normalized bag-of-words embedding."""
    vector = [0.0] * EMBEDDING_DIM
    clean = (text or "").strip().lower()
    if not clean:
        return vector

    for token in clean.split():
        vector[_hash_token(token)] += 1.0

    return _normalize(vector)


def bulk_encode(texts: Iterable[str]) -> List[List[float]]:
    """Encode a list of texts using the deterministic local embedding."""
    return [encode_text(text) for text in texts]


def attach_embeddings(people: Iterable[object]) -> None:
    """Populate participant embeddings from normalized NLP text."""
    texts = [getattr(person.nlp, "normalized_text", "") for person in people]
    for person, vector in zip(people, bulk_encode(texts)):
        person.embedding = vector


def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """Cosine for normalized vectors. Returns 0.0 for missing vectors."""
    if not vector_a or not vector_b:
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(vector_a, vector_b))))
