"""
Seed fake demo mentees into the database from demo_mentees.csv.

These mentees are fictional — all names and emails are made up.
They are tagged with is_demo=TRUE so the public demo account (eceaccount)
sees them automatically without needing to upload a CSV.

Run:
    python wrapper/backend/scripts/seed_demo_mentees.py
    python wrapper/backend/scripts/seed_demo_mentees.py --clear   # remove demo mentees first
    python wrapper/backend/scripts/seed_demo_mentees.py --dry-run  # preview only
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary]")
    sys.exit(1)

DEMO_CSV = Path(__file__).resolve().parents[1] / "data" / "demo_mentees.csv"


def _load_csv() -> list[dict]:
    rows = []
    with DEMO_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _to_record(row: dict) -> dict:
    email = row.get("Email", "").strip().lower()
    first = row.get("First Name", "").strip()
    last = row.get("Last Name", "").strip()
    return {
        "mentee_id": f"demo-{email}" if email else f"demo-{uuid.uuid4()}",
        "email": email,
        "first_name": first,
        "last_name": last,
        "full_name": f"{first} {last}".strip(),
        "pronouns": row.get("Pronouns", "").strip(),
        "education_level": row.get("Education Level", "").strip(),
        "graduation_semester": row.get("Graduation Semester", "").strip(),
        "graduation_year": None,
        "degree_programs": None,
        "concentrations": row.get("Concentration", "").strip() or None,
        "phd_specialization": None,
        "student_orgs": row.get("Organizations", "").strip() or None,
        "experience_level": None,
        "industries_of_interest": row.get("Career Interests", "").strip() or None,
        "about_yourself": row.get("About Yourself", "").strip() or None,
        "help_topics": None,
        "submitted_at": row.get("Timestamp", "").strip() or None,
        "extra_fields": None,
        "is_demo": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo mentees into the database.")
    parser.add_argument("--clear", action="store_true", help="Delete existing demo mentees first.")
    parser.add_argument("--dry-run", action="store_true", help="Print records without inserting.")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    records = [_to_record(row) for row in _load_csv()]
    if not records:
        print("No rows found in demo_mentees.csv.")
        sys.exit(0)

    if args.dry_run:
        for r in records:
            print(r)
        print(f"\n{len(records)} records would be inserted.")
        return

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            if args.clear:
                cur.execute("DELETE FROM mentee_submissions WHERE is_demo = TRUE")
                print(f"Deleted existing demo mentees.")

            inserted = 0
            skipped = 0
            for r in records:
                cur.execute(
                    """
                    INSERT INTO mentee_submissions (
                        mentee_id, email, first_name, last_name, full_name,
                        pronouns, education_level, graduation_semester, graduation_year,
                        degree_programs, concentrations, phd_specialization,
                        student_orgs, experience_level, industries_of_interest,
                        about_yourself, help_topics, submitted_at, extra_fields, is_demo
                    ) VALUES (
                        %(mentee_id)s, %(email)s, %(first_name)s, %(last_name)s, %(full_name)s,
                        %(pronouns)s, %(education_level)s, %(graduation_semester)s, %(graduation_year)s,
                        %(degree_programs)s, %(concentrations)s, %(phd_specialization)s,
                        %(student_orgs)s, %(experience_level)s, %(industries_of_interest)s,
                        %(about_yourself)s, %(help_topics)s, %(submitted_at)s, %(extra_fields)s, %(is_demo)s
                    )
                    ON CONFLICT (mentee_id) DO NOTHING
                    """,
                    r,
                )
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1

        conn.commit()

    print(f"Done. Inserted {inserted}, skipped {skipped} (already existed).")


if __name__ == "__main__":
    main()
