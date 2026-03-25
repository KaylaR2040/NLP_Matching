# =============================================================================
# File: main.py
# Purpose: Load survey data, encode free-text, run weighted similarity matching,
#          honor admin overrides (blacklist/locks), and print a quick summary.
# =============================================================================

from pathlib import Path
import json

from csv_parse import parse_mentor_csv, parse_mentee_csv
from direct_match import build_ranked_pairs, greedy_assign
from filters import apply_filters
from nlp_ai_prep import attach_embeddings


def load_overrides(path: Path):
    """Load blacklist/locks file. Returns (blacklist_set, locked_pairs)."""
    if not path.exists():
        return set(), []
    with path.open() as f:
        data = json.load(f)
    blacklist = {(item[0], item[1]) for item in data.get("blacklist", [])}
    locks = [(item[0], item[1]) for item in data.get("locks", [])]
    return blacklist, locks


def run_matching_cycle(mentee_data, mentor_data, overrides_path: Path):
    """Core workflow used by CLI and (future) UI reruns."""
    blacklist, locks = load_overrides(overrides_path)

    # 1) Apply hard filters
    filtered_mentees, filtered_mentors = apply_filters(mentee_data, mentor_data)

    # 2) Encode text → vectors
    attach_embeddings(filtered_mentees)
    attach_embeddings(filtered_mentors)

    # 3) Build ranked pairs, skipping blacklisted combos
    ranked_pairs = build_ranked_pairs(filtered_mentees, filtered_mentors, prohibited=blacklist)

    # 4) Greedy assign, seeding with locked pairs
    assignments = greedy_assign(ranked_pairs, locked=locks)

    return {
        "ranked_pairs": ranked_pairs,
        "assignments": assignments,
        "blacklist": blacklist,
        "locks": locks,
        "filtered_mentees": filtered_mentees,
        "filtered_mentors": filtered_mentors,
    }


def main():
    # CSV Default Locations (relative to this file)
    base_dir = Path(__file__).resolve().parent
    mentee_csv_path = base_dir / "data/sample_mentees.csv"
    mentor_csv_path = base_dir / "data/sample_mentors.csv"
    overrides_path = base_dir / "overrides.json"

    mentees = parse_mentee_csv(mentee_csv_path)
    mentors = parse_mentor_csv(mentor_csv_path)

    results = run_matching_cycle(mentees, mentors, overrides_path)
    ranked_pairs = results["ranked_pairs"]
    assignments = results["assignments"]

    print("\n=== Summary ===")
    print(f"Mentees parsed: {len(mentees)}")
    print(f"Mentees after filter: {len(results['filtered_mentees'])}")
    print(f"Mentors parsed: {len(mentors)}")
    print(f"Ranked pairs (after blacklist): {len(ranked_pairs)}")
    print(f"Assignments (with locks): {len(assignments)}")

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
        print(f"  Match % : {pair['match_score']*100:5.2f}%")

        weights = pair.get("weights", {})
        scores = pair.get("scores", {})
        for key in ["industry", "degree", "interest", "organization", "nlp"]:
            w = weights.get(key, 1.0 if key != "nlp" else 1.0)
            s = scores.get(key, 0.0)
            label = key.upper() if key == "nlp" else key.title()
            print(f"  - {label:<15} score={s:4.2f}  weight={w:3.1f}")

        print("-" * 36)


if __name__ == "__main__":
    main()
