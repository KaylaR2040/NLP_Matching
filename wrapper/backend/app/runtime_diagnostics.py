from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


def emit_runtime_diagnostics(entrypoint: str) -> None:
    """Print lightweight runtime diagnostics before importing heavy app modules.

    This is primarily for Vercel/serverless debugging. It intentionally uses only
    stdlib imports so it can run even when third-party packages are missing.
    """

    try:
        pandas_spec = importlib.util.find_spec("pandas")
        payload = {
            "entrypoint": entrypoint,
            "cwd": os.getcwd(),
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "sys_prefix": sys.prefix,
            "sys_base_prefix": sys.base_prefix,
            "virtual_env": os.getenv("VIRTUAL_ENV", ""),
            "vercel": os.getenv("VERCEL", ""),
            "pythonpath": os.getenv("PYTHONPATH", ""),
            "sys_path_head": sys.path[:8],
            "cwd_requirements_exists": Path("requirements.txt").exists(),
            "repo_relative_backend_requirements_exists": Path(
                "wrapper/backend/requirements.txt"
            ).exists(),
            "pandas_spec_found": pandas_spec is not None,
            "pandas_spec_origin": getattr(pandas_spec, "origin", None) if pandas_spec else None,
        }
        print(
            "[wrapper.runtime-diagnostics] "
            + json.dumps(payload, sort_keys=True, default=str),
            flush=True,
        )
    except Exception as exc:
        print(
            "[wrapper.runtime-diagnostics] failed to emit diagnostics: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
