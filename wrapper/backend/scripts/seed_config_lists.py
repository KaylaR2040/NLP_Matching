"""
Seed the config_lists table from the .txt files in the data/ directory.

Usage:
    python wrapper/backend/scripts/seed_config_lists.py --database-url "postgresql://..."

Or set DATABASE_URL in the environment.

This script is idempotent — it uses INSERT ... ON CONFLICT DO UPDATE so it
is safe to run multiple times. Existing rows are overwritten with file content.

Run init_schema.py first to ensure the config_lists table exists.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import psycopg
except ImportError:
    sys.exit("psycopg is not installed. Run: pip install 'psycopg[binary]>=3.2.1'")


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent.parent  # NLP_Matching/

# Resolve data directory: prefer repo-root data/, fall back to backend data/.
_repo_data = REPO_ROOT / "data"
_backend_data = BACKEND_ROOT / "data"
DATA_DIR = _repo_data if _repo_data.exists() else _backend_data

# Map list_key → (label, filename)
CONFIG_FILES: dict[str, tuple[str, str]] = {
    "ncsu_orgs":      ("NCSU Organizations",       "ncsu_orgs.txt"),
    "concentrations": ("ECE Concentrations",        "concentrations.txt"),
    "grad_programs":  ("Graduate Programs (MS)",    "grad_programs.txt"),
    "abm_programs":   ("ABM Degree Programs",       "abm_programs.txt"),
    "phd_programs":   ("PhD Programs",              "phd_programs.txt"),
}


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed config_lists table from .txt files."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Postgres connection string (default: $DATABASE_URL env var).",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DATA_DIR),
        help=f"Directory containing .txt files (default: {DATA_DIR}).",
    )
    args = parser.parse_args()

    db_url = args.database_url.strip()
    if not db_url:
        sys.exit(
            "No database URL provided. Pass --database-url or set DATABASE_URL."
        )

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        sys.exit(f"Data directory not found: {data_dir}")

    upsert_sql = """
        INSERT INTO config_lists (list_key, label, content, updated_at, updated_by)
        VALUES (%s, %s, %s, NOW(), 'seed_script')
        ON CONFLICT (list_key) DO UPDATE
            SET label      = EXCLUDED.label,
                content    = EXCLUDED.content,
                updated_at = NOW(),
                updated_by = 'seed_script'
    """

    print(f"Connecting to database…")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for list_key, (label, filename) in CONFIG_FILES.items():
                file_path = data_dir / filename
                content = _read_file(file_path)
                if not content:
                    print(f"  SKIP {list_key}: file not found or empty ({file_path})")
                    continue
                line_count = len([l for l in content.splitlines() if l.strip()])
                cur.execute(upsert_sql, (list_key, label, content))
                print(f"  OK   {list_key}: {line_count} lines from {file_path.name}")
        conn.commit()

    print("\nSeeding complete. Verify with:")
    print("  SELECT list_key, label, length(content) FROM config_lists;")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
