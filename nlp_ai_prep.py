"""NLP helper functions used by the matching engine.

Responsibilities:
1) Load a sentence-transformer once (all-MiniLM-L6-v2).
2) Encode free-text (“About Me”) into 384-d vectors.
3) Attach embeddings onto mentee / mentor objects in-place.
"""

from functools import lru_cache
from typing import Iterable, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load and memoize the encoder. Cached to avoid re-download per run."""
    return SentenceTransformer(MODEL_NAME)


def encode_text(text: str) -> np.ndarray:
    """Encode a single string to a numpy vector. Returns zeros for empty text."""
    clean = (text or "").strip()
    if not clean:
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)
    model = _get_model()
    return np.asarray(model.encode(clean, normalize_embeddings=True), dtype=np.float32)


def bulk_encode(texts: Iterable[str]) -> List[np.ndarray]:
    """Vectorize a list of strings with one model call."""
    texts = [t or "" for t in texts]
    # Fast path: if all empty, skip model
    if all(not t.strip() for t in texts):
        zero = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        return [zero.copy() for _ in texts]

    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [
        np.zeros(EMBEDDING_DIM, dtype=np.float32)
        if not txt.strip()
        else np.asarray(vec, dtype=np.float32)
        for txt, vec in zip(texts, vectors)
    ]


def attach_embeddings(people) -> None:
    """Mutate a list of mentees/mentors by filling their .embedding from .about."""
    about_texts = [getattr(p, "about", "") or "" for p in people]
    encoded = bulk_encode(about_texts)
    for person, vec in zip(people, encoded):
        person.embedding = vec
