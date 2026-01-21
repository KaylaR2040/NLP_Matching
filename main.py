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
    mentee_csv_path = base_dir / "data/sample_mentees.csv"
    mentor_csv_path = base_dir / "data/sample_mentors.csv"

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
    print(f"Mentees parsed: {len(mentees)}")                # Number of mentees parsed from the CSV file.
    print(f"Mentees after filter: {len(filtered_mentees)}") # Number of mentees remaining after applying filters.
    print(f"Mentors parsed: {len(mentors)}")                # Number of mentors parsed from the CSV file.
    print(f"Ranked pairs: {len(ranked_pairs)}")             # Number of mentor-mentee pairs that have been evaluated and ranked based on their compatibility scores.
    print(f"Assignments: {len(assignments)}")               # Number of final mentor-mentee matches made after applying the greedy assignment algorithm.

    print("\nTop 3 Ranked Mentor–Mentee Matches\n" + "=" * 36)

    for rank, pair in enumerate(ranked_pairs[:3], start=1):
        print(f"\nMatch #{rank}")
        print("-" * 36)

        print("Mentee")
        print(f"  Name : {pair['mentee_name']}")
        print(f"  Email: {pair['mentee_email']}")

        print("\nMentor")
        print(f"  Name : {pair['mentor_name']}")
        print(f"  Email: {pair['mentor_email']}")

        print("\nScoring Breakdown")
        print(f"  Total Score: {pair['score']:.3f}")

        weights = pair.get("weights", {})
        if weights:
            for criterion, value in weights.items():
                print(f"  - {criterion.replace('_', ' ').title():<25}: {value:.3f}")
        else:
            print("  (No individual weight data available)")

        print("-" * 36)


if __name__ == "__main__":
    main()
