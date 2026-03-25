"""TensorFlow/Keras baseline text classification model."""

from __future__ import annotations

import os
import random
from typing import Any, List, Sequence, Tuple

import numpy as np


def set_global_seeds(seed: int = 42) -> None:
    """Set seeds for Python, NumPy, and TensorFlow."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        tf = _import_tensorflow()
        tf.random.set_seed(seed)
    except Exception:
        # Keep deterministic behavior for available RNGs only.
        pass


def _import_tensorflow() -> Any:
    """Import TensorFlow lazily to avoid heavy import-time initialization."""
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    try:
        import tensorflow as tf  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency fallback
        raise RuntimeError("TensorFlow is not installed.") from exc
    return tf


def build_model(input_dim: int, num_classes: int):
    """Build and compile a small dense classifier model."""
    tf = _import_tensorflow()
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(num_classes, activation="softmax"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(
    X_train: np.ndarray,
    y_train: Sequence[str],
    epochs: int = 12,
    batch_size: int = 4,
    seed: int = 42,
) -> Tuple[Any, Any]:
    """Train baseline model and return trained model with label encoder."""
    from sklearn.preprocessing import LabelEncoder

    set_global_seeds(seed)

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(list(y_train))

    model = build_model(input_dim=X_train.shape[1], num_classes=len(label_encoder.classes_))
    model.fit(X_train, y_encoded, epochs=epochs, batch_size=batch_size, verbose=0)

    setattr(model, "label_encoder", label_encoder)
    return model, label_encoder


def predict(model: Any, X: np.ndarray) -> List[str]:
    """Predict class labels as strings for feature matrix X."""
    label_encoder = getattr(model, "label_encoder", None)
    if label_encoder is None:
        raise ValueError("Model is missing a label_encoder attribute. Use train_model first.")

    probs = model.predict(X, verbose=0)
    pred_idx = np.argmax(probs, axis=1)
    return list(label_encoder.inverse_transform(pred_idx))
