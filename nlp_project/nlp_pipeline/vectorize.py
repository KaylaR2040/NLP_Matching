"""Feature vectorization for text classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np


@dataclass
class TfidfTextVectorizer:
    """TF-IDF vectorizer wrapper with stable defaults for small classifiers."""

    vectorizer: Any = field(default=None)

    def __post_init__(self) -> None:
        """Create sklearn vectorizer lazily at instance construction time."""
        if self.vectorizer is not None:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except Exception as exc:
            raise RuntimeError("scikit-learn is not installed.") from exc
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            token_pattern=r"(?u)\b\w+\b",
        )

    def fit_transform(self, texts: Iterable[str]) -> np.ndarray:
        """Fit TF-IDF vectorizer and return dense feature matrix."""
        matrix = self.vectorizer.fit_transform(list(texts))
        return matrix.toarray().astype(np.float32)

    def transform(self, texts: Iterable[str]) -> np.ndarray:
        """Transform text using fitted TF-IDF vectorizer and return dense matrix."""
        matrix = self.vectorizer.transform(list(texts))
        return matrix.toarray().astype(np.float32)
