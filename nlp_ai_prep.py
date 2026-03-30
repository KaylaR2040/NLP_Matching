"""NLP helper functions used by the matching engine.

Responsibilities:
1) Load a sentence-transformer once when available.
2) Encode free-text (“About Me”) into 384-d vectors.
3) Fall back to deterministic local embeddings when the model is unavailable.
4) Attach embeddings onto mentee / mentor objects in-place.
"""

from functools import lru_cache
from typing import Iterable, List, Optional
import hashlib

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency fallback
    SentenceTransformer = None

EMBEDDING_DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load and memoize the encoder. Cached to avoid re-download per run."""
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(MODEL_NAME)


def _hash_token(token: str) -> int:
    """Map a token to a stable index in the fallback embedding space."""
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % EMBEDDING_DIM


def _fallback_encode(clean: str) -> np.ndarray:
    """Create a deterministic normalized bag-of-words style embedding."""
    vector = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    for token in clean.lower().split():
        vector[_hash_token(token)] += 1.0
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def encode_text(text: str) -> np.ndarray:
    """Encode a single string to a numpy vector. Returns zeros for empty text."""
    clean = (text or "").strip()
    if not clean:
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)
    try:
        model = _get_model()
        return np.asarray(model.encode(clean, normalize_embeddings=True), dtype=np.float32)
    except Exception:
        return _fallback_encode(clean)


def bulk_encode(texts: Iterable[str]) -> List[np.ndarray]:
    """Vectorize a list of strings with one model call."""
    texts = [t or "" for t in texts]
    # Fast path: if all empty, skip model
    if all(not t.strip() for t in texts):
        zero = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        return [zero.copy() for _ in texts]

    try:
        model = _get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [
            np.zeros(EMBEDDING_DIM, dtype=np.float32)
            if not txt.strip()
            else np.asarray(vec, dtype=np.float32)
            for txt, vec in zip(texts, vectors)
        ]
    except Exception:
        return [
            np.zeros(EMBEDDING_DIM, dtype=np.float32)
            if not txt.strip()
            else _fallback_encode(txt.strip())
            for txt in texts
        ]


def attach_embeddings(people) -> None:
    """Mutate a list of mentees/mentors by filling their .embedding from NLP-ready text."""
    source_texts = [getattr(p, "nlp_text", getattr(p, "about", "")) or "" for p in people]
    encoded = bulk_encode(source_texts)
    for person, vec in zip(people, encoded):
        person.embedding = vec
