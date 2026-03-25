import os

import numpy as np
import pytest

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

pytest.importorskip("tensorflow")
pytest.importorskip("sklearn")

from nlp_pipeline.pipeline import NLPPipeline


def test_full_integration_pipeline() -> None:
    pipeline = NLPPipeline(use_stemming=False)

    sample_text = "Cricket is popular in England. It is loved by many fans."
    processed = pipeline.preprocess(sample_text)

    assert len(processed["sentences"]) >= 2
    assert len(processed["tokens"]) > 0
    assert len(processed["filtered_tokens"]) > 0
    assert len(processed["normalized_tokens"]) > 0

    train_texts = [
        "team won the cricket match",
        "great batting and bowling",
        "stock market crashed badly",
        "investors fear heavy losses",
        "fantastic football game tonight",
        "the economy is in decline",
    ]
    train_labels = ["sports", "sports", "finance", "finance", "sports", "finance"]

    pipeline.train_classifier(train_texts, train_labels)
    preds = pipeline.predict_labels(["cricket game and batting", "market losses and investors"])

    assert len(preds) == 2
    assert set(preds).issubset({"sports", "finance"})

    expected = np.array(["sports", "finance"])
    actual = np.array(preds)
    assert np.mean(actual == expected) >= 0.5
