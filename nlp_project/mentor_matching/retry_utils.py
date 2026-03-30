"""Retry helpers for resilient pipeline operations."""

from __future__ import annotations

import time
from typing import Callable, TypeVar


T = TypeVar("T")


def run_with_retry(
    operation_name: str,
    operation: Callable[[], T],
    attempts: int = 3,
    delay_seconds: float = 0.2,
) -> T:
    """
    Execute an operation with bounded retries.

    The final exception is raised after all attempts fail.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:  # pragma: no cover - defensive reliability path
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds * attempt)

    if last_error is None:
        raise RuntimeError(f"{operation_name} failed without an exception")

    raise RuntimeError(
        f"{operation_name} failed after {attempts} attempts: {last_error}"
    ) from last_error
