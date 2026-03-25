"""End-to-end NLP pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .normalize import normalize_text
from .segmentation import segment_sentences
from .stopwords import remove_stopwords
from .tagging import named_entities, pos_tag_text
from .tf_model import predict, train_model
from .tokenizing import tokenize_text
from .vectorize import TfidfTextVectorizer


@dataclass
class NLPPipeline:
    """Pipeline covering preparation, AI-prepping, and training stages."""

    use_stemming: bool = False
    vectorizer: TfidfTextVectorizer = field(default_factory=TfidfTextVectorizer)
    model: object | None = None

    def preprocess(self, text: str) -> Dict[str, object]:
        """Run segmentation, tokenization, stopword removal, normalization, POS, and NER."""
        sentences = segment_sentences(text)
        tokens = tokenize_text(text)
        filtered_tokens = remove_stopwords(tokens)
        normalized = normalize_text(" ".join(filtered_tokens), use_stemming=self.use_stemming)
        pos_tags = pos_tag_text(text)
        entities = named_entities(text)

        return {
            "sentences": sentences,
            "tokens": tokens,
            "filtered_tokens": filtered_tokens,
            "normalized_tokens": normalized,
            "pos_tags": pos_tags,
            "entities": entities,
        }

    def train_classifier(self, texts: Sequence[str], labels: Sequence[str]) -> Tuple[object, object]:
        """Vectorize texts, train TF/Keras classifier, and store trained artifacts."""
        X_train = self.vectorizer.fit_transform(texts)
        model, label_encoder = train_model(X_train, labels)
        setattr(model, "label_encoder", label_encoder)
        self.model = model
        return model, label_encoder

    def predict_labels(self, texts: Sequence[str]) -> List[str]:
        """Predict labels for raw texts using trained vectorizer and model."""
        if self.model is None:
            raise ValueError("Model is not trained. Call train_classifier first.")
        X = self.vectorizer.transform(texts)
        return predict(self.model, X)
