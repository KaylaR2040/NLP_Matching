"""Diagnose import-time hangs for nlp_pipeline modules.

Run from repository root:
    python tools/diagnose_import_hang.py
"""

from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path
from typing import Iterable

MODULES: Iterable[str] = (
    "nlp_pipeline",
    "nlp_pipeline.segmentation",
    "nlp_pipeline.tokenizing",
    "nlp_pipeline.stopwords",
    "nlp_pipeline.normalize",
    "nlp_pipeline.tagging",
    "nlp_pipeline.vectorize",
    "nlp_pipeline.tf_model",
    "nlp_pipeline.pipeline",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "nlp_project"
    if package_root.exists():
        sys.path.insert(0, str(package_root))

    start = time.perf_counter()
    print(f"cwd={os.getcwd()}")
    print(f"python={sys.executable}")
    print(f"sys.path[:5]={sys.path[:5]}")

    for name in MODULES:
        t0 = time.perf_counter()
        print(f"[START] import {name}")
        sys.stdout.flush()
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            dt = time.perf_counter() - t0
            print(f"[SKIP ] import {name} after {dt:.4f}s: {exc}")
            continue
        except Exception as exc:
            dt = time.perf_counter() - t0
            print(f"[FAIL ] import {name} after {dt:.4f}s: {exc.__class__.__name__}: {exc}")
            return 1
        dt = time.perf_counter() - t0
        print(f"[DONE ] import {name} in {dt:.4f}s")

    total = time.perf_counter() - start
    print(f"[OK   ] all imports completed in {total:.4f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
