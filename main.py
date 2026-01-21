# =============================================================================
# File: main.py
# Purpose: CLI entry point to load survey data, normalize it, apply filters,
#          run direct matching, and write results to disk.
# Inputs/Outputs:
#   Inputs: CSV paths for mentees (required) and mentors (optional), CLI flags.
#   Outputs: Ranked matches CSV and greedy assignments CSV in ./out/.
# Key Sections:
#   - Imports
#   - Constants and Config
#   - CLI/Argument Parsing
#   - Orchestration Helpers
#   - Main
# Notes on Future Work:
#   - Add support for ILP/LP optimization and fairness constraints.
#   - Expand NLP/ML workflows (see nlp_*.py scaffolds).
# =============================================================================

# Import My Modules
# Imports all Functions, Data Structures, and Constants from my files
# Functions are called using their original names, without importing them under aliases.
from direct_match import *
from filters import *
from csv_parse import *
from nlp_ai_prep import *
from nlp_data_prep import *
from nlp_train import *

# Import External Libraries
import numpy as np
import pandas as pd
from pathlib import Path

def main():

    # CSV Default Locations (relative to this file)
    base_dir = Path(__file__).resolve().parent
    mentee_csv_path = base_dir / "data/Interest Form - Mentee Form Responses.csv"
    mentor_csv_path = base_dir / "data/Interest Form - Mentor Form Responses.csv"

    # Parse Mentee Data
    mentees = parse_mentee_csv(mentee_csv_path)

    # Parse Mentor Data
    mentors = parse_mentor_csv(mentor_csv_path)

    # Apply Filters
    filtered_mentees, filtered_mentors = apply_filters(mentees, mentors)

    # Direct Match
    ranked_pairs = build_ranked_pairs(filtered_mentees, filtered_mentors)
    assignments = greedy_assign(ranked_pairs)

    print("\n=== Summary ===")
    print(f"Mentees parsed: {len(mentees)}")
    print(f"Mentees after filter: {len(filtered_mentees)}")
    print(f"Mentors parsed: {len(mentors)}")
    print(f"Ranked pairs: {len(ranked_pairs)}")
    print(f"Assignments: {len(assignments)}")

    print("\n=== Top Ranked Pairs (Top 10) ===")
    for idx, pair in enumerate(ranked_pairs[:10], start=1):
        print(
            f"{idx:02d}. {pair['mentee_name']} <{pair['mentee_email']}> "
            f"↔ {pair['mentor_name']} <{pair['mentor_email']}> "
            f"| score={pair['score']} "
            f"(major={pair['major_overlap']}, edu={pair['education_overlap']})"
        )

    print("\n=== Assignments ===")
    for idx, pair in enumerate(assignments, start=1):
        print(
            f"{idx:02d}. {pair['mentee_name']} <{pair['mentee_email']}> "
            f"→ {pair['mentor_name']} <{pair['mentor_email']}> "
            f"| score={pair['score']}"
        )

if __name__ == "__main__":
    main()
