# =============================================================================
# File: direct_matching.py
# Purpose: Compute rule-based scores for candidate pairs and perform greedy
#          assignment to produce baseline matches.
# Inputs/Outputs:
#   Inputs: Candidate pairs from filters.
#   Outputs: Ranked matches and final greedy assignments.
# Key Sections:
#   - Imports and Types
#   - Scoring Helpers
#   - Ranking
#   - Greedy Assignment
# Notes on Future Work:
#   - Replace greedy selection with ILP/LP optimization.
#   - Add fairness and capacity constraints.
# =============================================================================

import numpy as np
import pandas as pd


# =============================================================================
# Scoring Helpers
# =============================================================================
def _normalize_list(values):
    if not values:
        return set()
    return {str(item).strip().lower() for item in values if str(item).strip()}


def _overlap_count(list_a, list_b):
    set_a = _normalize_list(list_a)
    set_b = _normalize_list(list_b)
    return len(set_a.intersection(set_b))


def score_pair(mentee, mentor):
    """
    Score a mentor-mentee pair based on shared fields.
    """
    major_overlap = _overlap_count(mentee.major, mentor.degrees_completed)
    education_overlap = _overlap_count(mentee.education_level, mentor.education_level)

    score = (2 * major_overlap) + (1 * education_overlap)
    return {
        "mentee_email": mentee.email,
        "mentee_name": mentee.name,
        "mentor_email": mentor.email,
        "mentor_name": mentor.name,
        "major_overlap": major_overlap,
        "education_overlap": education_overlap,
        "score": score,
    }


# =============================================================================
# Ranking
# =============================================================================
def build_ranked_pairs(mentees, mentors):
    """
    Build and rank all mentor-mentee pairs.
    """
    pairs = []
    for mentee in mentees:
        for mentor in mentors:
            pairs.append(score_pair(mentee, mentor))

    return sorted(pairs, key=lambda row: row["score"], reverse=True)


# =============================================================================
# Greedy Assignment
# =============================================================================
def greedy_assign(ranked_pairs):
    """
    Greedily assign mentors to mentees based on ranked pairs.
    """
    assigned_mentees = set()
    assigned_mentors = set()
    assignments = []

    for pair in ranked_pairs:
        mentee_email = pair["mentee_email"]
        mentor_email = pair["mentor_email"]

        if mentee_email in assigned_mentees or mentor_email in assigned_mentors:
            continue

        assignments.append(pair)
        assigned_mentees.add(mentee_email)
        assigned_mentors.add(mentor_email)

    return assignments
