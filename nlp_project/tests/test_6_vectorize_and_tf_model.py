import os

import numpy as np
import pytest

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

tf = pytest.importorskip("tensorflow")
pytest.importorskip("sklearn")

from nlp_pipeline.tf_model import predict, set_global_seeds, train_model
from nlp_pipeline.vectorize import TfidfTextVectorizer


def test_vectorize_and_train_tf_model() -> None:
    set_global_seeds(42)

    texts = [
        "I love this movie",
        "This film is great",
        "I hate this movie",
        "This film is terrible",
        "Wonderful and uplifting story",
        "Awful and boring story",
    ]
    labels = ["pos", "pos", "neg", "neg", "pos", "neg"]

    vectorizer = TfidfTextVectorizer()
    X = vectorizer.fit_transform(texts)

    model, _ = train_model(X, labels, epochs=20, batch_size=2, seed=42)

    y_pred = predict(model, X)
    accuracy = np.mean(np.array(y_pred) == np.array(labels))

    assert X.ndim == 2
    assert X.shape[0] == len(texts)
    assert accuracy >= 0.75
