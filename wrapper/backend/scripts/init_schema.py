"""
Initialize the Neon Postgres schema for the NLP Mentor Matching backend.

Usage:
    python wrapper/backend/scripts/init_schema.py --database-url "postgresql://..."

Or set DATABASE_URL in the environment and run without --database-url.

This script is idempotent — safe to re-run; it uses CREATE TABLE IF NOT EXISTS.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make sure we can import psycopg even when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import psycopg
except ImportError:
    sys.exit(
        "psycopg is not installed. Run: pip install 'psycopg[binary]>=3.2.1'"
    )


DDL = """
-- ----------------------------------------------------------------
-- mentor_records
-- The actual mentor storage table used by PostgresMentorStore in
-- wrapper/backend/app/mentor_store.py. This table is also created
-- automatically by mentor_store.py on first connect, but is included
-- here so a fresh database is fully initialized without needing a
-- live API server.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mentor_records (
    mentor_id                   TEXT PRIMARY KEY,
    email                       TEXT,
    first_name                  TEXT,
    last_name                   TEXT,
    full_name                   TEXT,
    linkedin_url                TEXT,
    profile_photo_url           TEXT,
    current_company             TEXT,
    current_job_title           TEXT,
    current_location            TEXT,
    current_city                TEXT,
    current_state               TEXT,
    degrees_text                TEXT,
    industry_focus_area         TEXT,
    professional_experience     TEXT,
    about_yourself              TEXT,
    students_interested         TEXT,
    phone                       TEXT,
    preferred_contact_method    TEXT,
    is_active                   BOOLEAN DEFAULT TRUE,
    source_csv_path             TEXT,
    source_timestamp            TIMESTAMPTZ,
    last_modified_at            TIMESTAMPTZ,
    last_modified_by            TEXT,
    last_enriched_at            TIMESTAMPTZ,
    enrichment_status           TEXT,
    enrichment_provider_metadata JSONB,
    extra_fields                JSONB,
    is_demo                     BOOLEAN DEFAULT FALSE,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent migration: add is_demo to existing tables created before this column existed.
ALTER TABLE mentor_records ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS mentor_records_normalized_email_unique
    ON mentor_records (lower(trim(email))) WHERE trim(email) <> '';
CREATE INDEX IF NOT EXISTS mentor_records_normalized_full_name_idx
    ON mentor_records (lower(trim(full_name)));

-- ----------------------------------------------------------------
-- config_lists
-- Replaces the flat .txt files (ncsu_orgs, concentrations, etc.).
-- Content is stored as newline-separated text, mirroring the file
-- format so existing read/parse logic requires no changes.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config_lists (
    list_key    TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_by  TEXT
);

-- ----------------------------------------------------------------
-- match_results
-- Stores the JSON output of each /run_match call for audit trail
-- and history display in the admin UI.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_results (
    id                  SERIAL PRIMARY KEY,
    run_at              TIMESTAMPTZ DEFAULT NOW(),
    run_by              TEXT,
    mentee_source       TEXT,
    mentor_source       TEXT,
    summary             JSONB,
    assignments         JSONB,
    top_ranked_pairs    JSONB,
    stdout              TEXT
);

CREATE INDEX IF NOT EXISTS match_results_run_at_idx ON match_results (run_at DESC);

-- ----------------------------------------------------------------
-- mentee_submissions
-- Stores mentee form submissions from /public/forms/mentee.
-- Provides a durable record for matching and audit, separate from
-- the transient CSV upload used by /run_match.
-- ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mentee_submissions (
    mentee_id               TEXT PRIMARY KEY,
    email                   TEXT,
    first_name              TEXT,
    last_name               TEXT,
    full_name               TEXT,
    pronouns                TEXT,
    education_level         TEXT,
    graduation_semester     TEXT,
    graduation_year         TEXT,
    degree_programs         TEXT,
    concentrations          TEXT,
    phd_specialization      TEXT,
    student_orgs            TEXT,
    experience_level        TEXT,
    industries_of_interest  TEXT,
    about_yourself          TEXT,
    help_topics             TEXT,
    submitted_at            TIMESTAMPTZ DEFAULT NOW(),
    extra_fields            JSONB
);

CREATE INDEX IF NOT EXISTS mentee_submissions_email_idx ON mentee_submissions (email);
CREATE INDEX IF NOT EXISTS mentee_submissions_submitted_at_idx ON mentee_submissions (submitted_at DESC);
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Neon Postgres schema.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Postgres connection string (default: $DATABASE_URL env var).",
    )
    args = parser.parse_args()

    db_url = args.database_url.strip()
    if not db_url:
        sys.exit(
            "No database URL provided. Pass --database-url or set DATABASE_URL."
        )

    print(f"Connecting to database…")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()

    print("Schema initialized successfully.")
    print("Tables created (or already existed): mentor_records, config_lists, match_results, mentee_submissions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
