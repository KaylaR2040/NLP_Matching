import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_import(command: str, timeout_seconds: float = 5.0) -> tuple[float, subprocess.CompletedProcess[str]]:
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed = time.perf_counter() - started
    return elapsed, proc


def _assert_fast_import(module_stmt: str) -> None:
    elapsed, proc = _run_import(module_stmt)
    assert proc.returncode == 0, f"Import failed: {proc.stderr}\n{proc.stdout}"
    assert "ok" in proc.stdout
    assert elapsed < 1.0, f"Import too slow ({elapsed:.3f}s): {module_stmt}"


def test_segmentation_import_is_fast() -> None:
    _assert_fast_import("from nlp_pipeline.segmentation import segment_sentences; print('ok')")


def test_tokenizing_import_is_fast() -> None:
    _assert_fast_import("from nlp_pipeline.tokenizing import tokenize_text; print('ok')")


def test_stopwords_import_is_fast() -> None:
    _assert_fast_import("from nlp_pipeline.stopwords import remove_stopwords; print('ok')")


def test_tf_model_import_does_not_hang() -> None:
    elapsed, proc = _run_import("import nlp_pipeline.tf_model; print('ok')")
    assert proc.returncode == 0, f"tf_model import failed: {proc.stderr}\n{proc.stdout}"
    assert "ok" in proc.stdout
    assert elapsed < 1.0, f"tf_model import too slow ({elapsed:.3f}s)"
