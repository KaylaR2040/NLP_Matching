"""Semantic embedding utilities for segmented mentor/mentee matching."""

from __future__ import annotations

import hashlib
import math
import re
import warnings
from typing import Iterable, List, Sequence

from .constants import DOMAIN_STOP_WORDS


MODEL_NAME = "all-mpnet-base-v2"
FALLBACK_EMBEDDING_DIM = 256
_MODEL = None
_MODEL_FAILED = False
_MODEL_WARNING_SHOWN = False


def _load_model():
    """Lazily load sentence-transformers model for semantic matching."""
    global _MODEL, _MODEL_FAILED, _MODEL_WARNING_SHOWN

    if _MODEL is not None:
        return _MODEL
    if _MODEL_FAILED:
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        _MODEL_FAILED = True
        if not _MODEL_WARNING_SHOWN:
            warnings.warn(
                "sentence-transformers is not installed; using lexical fallback embeddings. "
                "Install dependencies to enable semantic matching: pip install sentence-transformers torch",
                RuntimeWarning,
                stacklevel=2,
            )
            _MODEL_WARNING_SHOWN = True
        return None

    try:
        _MODEL = SentenceTransformer(MODEL_NAME)
    except Exception:
        _MODEL_FAILED = True
        if not _MODEL_WARNING_SHOWN:
            warnings.warn(
                f"Could not load semantic model '{MODEL_NAME}'; using lexical fallback embeddings.",
                RuntimeWarning,
                stacklevel=2,
            )
            _MODEL_WARNING_SHOWN = True
        return None

    return _MODEL


def _normalize(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _hash_token(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % FALLBACK_EMBEDDING_DIM


def _fallback_encode_text(text: str) -> List[float]:
    """Hash-based fallback encoding used only if model loading fails."""
    vector = [0.0] * FALLBACK_EMBEDDING_DIM
    clean = (text or "").strip().lower()
    if not clean:
        return vector
    for token in clean.split():
        vector[_hash_token(token)] += 1.0
    return _normalize(vector)


def _normalize_bucket_text(text: str) -> str:
    """Remove low-signal domain fillers before semantic encoding."""
    clean = (text or "").strip().lower()
    if not clean:
        return ""
    tokens = re.findall(r"[a-z0-9]+", clean)
    filtered = [token for token in tokens if token not in DOMAIN_STOP_WORDS]
    return " ".join(filtered) if filtered else clean


def _encode_with_model(texts: Sequence[str]) -> List[List[float]] | None:
    model = _load_model()
    if model is None:
        return None
    vectors = model.encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return [vector.astype(float).tolist() for vector in vectors]


def get_vector(text: str) -> List[float]:
    """Encode one text string to a semantic embedding vector."""
    vectors = bulk_encode([text or ""])
    return vectors[0] if vectors else []


def bulk_encode(texts: Iterable[str]) -> List[List[float]]:
    """Encode text strings using semantic model with deterministic fallback."""
    text_list = [_normalize_bucket_text(str(text or "")) for text in texts]
    if not text_list:
        return []

    semantic_vectors = _encode_with_model(text_list)
    if semantic_vectors is not None:
        return semantic_vectors

    return [_fallback_encode_text(text) for text in text_list]


def semantic_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Cosine similarity between two vectors, clamped to [0, 1]."""
    if not vec1 or not vec2:
        return 0.0

    limit = min(len(vec1), len(vec2))
    if limit == 0:
        return 0.0

    dot = sum(float(vec1[idx]) * float(vec2[idx]) for idx in range(limit))
    norm1 = math.sqrt(sum(float(vec1[idx]) ** 2 for idx in range(limit)))
    norm2 = math.sqrt(sum(float(vec2[idx]) ** 2 for idx in range(limit)))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    cosine = dot / (norm1 * norm2)
    return max(0.0, min(1.0, cosine))


def _combine_vectors(vectors: Sequence[Sequence[float]]) -> List[float]:
    usable = [vector for vector in vectors if vector]
    if not usable:
        return []
    width = min(len(vector) for vector in usable)
    merged = [
        sum(float(vector[idx]) for vector in usable) / float(len(usable))
        for idx in range(width)
    ]
    return _normalize(merged)


def attach_embeddings(people: Iterable[object]) -> None:
    """
    Populate segmented embeddings in batch for every participant.

    This corresponds to pipeline step 4 in ``MatchingPipeline.run``.
    """
    participants = list(people)
    if not participants:
        return

    industry_texts = [person.industry_profile_text() for person in participants]
    degree_texts = [person.degree_profile_text() for person in participants]
    personality_texts = [person.personality_profile_text() for person in participants]

    industry_vectors = bulk_encode(industry_texts)
    degree_vectors = bulk_encode(degree_texts)
    personality_vectors = bulk_encode(personality_texts)

    for person, industry_vec, degree_vec, personality_vec in zip(
        participants,
        industry_vectors,
        degree_vectors,
        personality_vectors,
    ):
        person.industry_embedding = industry_vec
        person.degree_embedding = degree_vec
        person.personality_embedding = personality_vec
        person.embedding = _combine_vectors((industry_vec, degree_vec, personality_vec))
