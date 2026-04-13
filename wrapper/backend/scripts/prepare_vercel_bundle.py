from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent

DEFAULT_SOURCE = BACKEND_ROOT.parent.parent / "nlp_project"
DEFAULT_DESTINATION = BACKEND_ROOT / "nlp_project"

REQUIRED_BUNDLE_PATHS = (
    "main.py",
    "mentor_matching",
    "data",
    "state",
)

OPTIONAL_BUNDLE_PATHS = (
    "pyproject.toml",
    "README.md",
    "scoring.csv",
)

IGNORE_PATTERNS = (
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
)


def _copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
        )
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_many(source_root: Path, destination_root: Path, paths: Iterable[str]) -> None:
    for relative in paths:
        source = source_root / relative
        if not source.exists():
            raise FileNotFoundError(
                f"Required bundle path missing: {source}. "
                "Check WRAPPER_NLP_PROJECT_SOURCE_DIR or repository layout."
            )
        _copy_path(source, destination_root / relative)


def _copy_optional(source_root: Path, destination_root: Path, paths: Iterable[str]) -> None:
    for relative in paths:
        source = source_root / relative
        if not source.exists():
            continue
        _copy_path(source, destination_root / relative)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a Vercel-deployable NLP bundle inside wrapper/backend/nlp_project."
        )
    )
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Source nlp_project directory (default: ../../nlp_project).",
    )
    parser.add_argument(
        "--destination",
        default=str(DEFAULT_DESTINATION),
        help="Destination bundle directory (default: wrapper/backend/nlp_project).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete destination before copying.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    source_root = Path(args.source).expanduser().resolve()
    destination_root = Path(args.destination).expanduser().resolve()

    if not source_root.exists():
        raise SystemExit(
            f"Source nlp_project directory does not exist: {source_root}"
        )

    if not args.no_clean and destination_root.exists():
        shutil.rmtree(destination_root)

    destination_root.mkdir(parents=True, exist_ok=True)

    _copy_many(source_root, destination_root, REQUIRED_BUNDLE_PATHS)
    _copy_optional(source_root, destination_root, OPTIONAL_BUNDLE_PATHS)

    if not (destination_root / "main.py").exists():
        raise SystemExit(
            f"Bundle incomplete. Missing {destination_root / 'main.py'} after copy."
        )

    file_count = sum(1 for path in destination_root.rglob("*") if path.is_file())
    print(
        "Prepared Vercel NLP bundle:",
        f"source={source_root}",
        f"destination={destination_root}",
        f"files={file_count}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
