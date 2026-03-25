# =============================================================================
# File: filters.py
# Purpose: Normalize data and apply hard constraints to construct candidate
#          pools for matching.
# Inputs/Outputs:
#   Inputs: Raw mentee/mentor DataFrames and filter configuration.
#   Outputs: Candidate pools with normalized profiles for downstream scoring.
# Key Sections:
#   - Imports
#   - Constants and Types
#   - Normalization Utilities
#   - Filter Rules
#   - Candidate Pool Construction
# Notes on Future Work:
#   - Expand constraint logic (timezone, capacity, program requirements).
#   - Add fairness-aware filtering constraints.
# =============================================================================

import numpy as np
import pandas as pd


# =============================================================================
# Filter Rules
# =============================================================================
def filter_mentees_without_prior_experience(mentees):
    """
    Return mentees who have NOT participated in prior mentorship programs.
    """
    return [mentee for mentee in mentees if not mentee.prior_mentorship]


def apply_filters(mentees, mentors):
    """
    Apply all hard filters and return filtered mentees and mentors.
    """
    filtered_mentees = filter_mentees_without_prior_experience(mentees)
    filtered_mentors = mentors # No filters applied to mentors yet
    return filtered_mentees, filtered_mentors
