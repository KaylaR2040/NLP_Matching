# =============================================================================
# File: csv_parse.py
# Purpose: Parse and normalize Google Forms CSV exports for mentors and mentees
#          into clean Python data structures for downstream matching.
# =============================================================================

import csv
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np


# =============================================================================
# Data Structures
# =============================================================================
@dataclass
class Mentee:
    email: str
    name: str
    education_level: List[str]
    major: List[str]
    prior_mentorship: bool
    industries: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    orgs: List[str] = field(default_factory=list)
    about: str = ""
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "industry": 1.0,
            "degree": 1.0,
            "interest": 1.0,
            "organization": 1.0,
        }
    )
    embedding: Optional[np.ndarray] = field(default=None, repr=False)


@dataclass
class Mentor:
    email: str
    name: str
    education_level: List[str]
    degrees_completed: List[str]
    industries: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    orgs: List[str] = field(default_factory=list)
    about: str = ""
    embedding: Optional[np.ndarray] = field(default=None, repr=False)


# =============================================================================
# Shared Parsing Utilities
# =============================================================================
def clean_string(value):
    """
    Safely convert a value to a stripped string.
    Handles None and non-string values gracefully.
    """
    if value is None:
        return ""
    return str(value).strip()


def split_checkbox_field(raw_value):
    """
    Convert a Google Forms checkbox response into a clean list of strings.
    """
    cleaned_value = clean_string(raw_value)
    if not cleaned_value:
        return []

    return [
        item.strip()
        for item in cleaned_value.split(",")
        if item.strip()
    ]


def parse_yes_no_to_bool(raw_value):
    """
    Convert a Google Forms yes/no response into a boolean.

    Assumes "yes" maps to True and "no" maps to False.
    """
    cleaned_value = clean_string(raw_value).lower()
    if(cleaned_value == "yes"):
        return True
    else: # cleaned_value == "no"
        return False


def _first_present(row: dict, keys: Iterable[str]) -> str:
    """Return the first non-empty field value from candidate keys."""
    for key in keys:
        val = row.get(key)
        if val is not None and clean_string(val):
            return val
    return ""


def _parse_weight(row: dict, keys: Iterable[str], default: float = 1.0) -> float:
    raw = _first_present(row, keys)
    try:
        val = float(raw)
        if val <= 0:
            return default
        return val
    except (TypeError, ValueError):
        return default

# =============================================================================
# CSV Parsing Entry Points
# =============================================================================
def parse_mentee_csv(file_path):
    """
    Parse a mentee CSV export into a list of Mentee objects.
    """
    mentees = []

    with open(file_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            prior_mentorship = parse_yes_no_to_bool(
                row.get("Have you ever participated in this or another mentoring program?")
            )

            education_field = _first_present(
                row,
                [
                    "What level of Education you are currently pursuing?",
                    "What level of Education you are currently pursuing or considering?",
                    "educationLevel",
                ],
            )

            mentee = Mentee(
                # Identification
                email=clean_string(row.get("Email Address")),
                name=clean_string(row.get("First & Last Name")),

                # Checkbox fields stored as list[str]
                education_level=split_checkbox_field(education_field),
                major=split_checkbox_field(
                    _first_present(row, ["What is your major(s)", "degreePrograms"])
                ),
                # Prior Mentorship stored as bool
                prior_mentorship=prior_mentorship,
                # Optional extras
                industries=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What industries are you interested in?",
                            "Industries of interest",
                            "industriesOfInterest",
                        ],
                    )
                ),
                interests=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What are your academic interests?",
                            "academicInterests",
                        ],
                    )
                ),
                orgs=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What student organizations are you involved in?",
                            "studentOrgs",
                        ],
                    )
                ),
                about=clean_string(
                    _first_present(
                        row,
                        [
                            "Tell us about yourself",
                            "About Yourself",
                            "aboutYourself",
                        ],
                    )
                ),
                weights={
                    "industry": _parse_weight(row, ["Matching by industry", "matchByIndustry"]),
                    "degree": _parse_weight(row, ["Matching by degree", "matchByDegree"]),
                    "interest": _parse_weight(row, ["Matching by interests", "matchByIdentity"]),
                    "organization": _parse_weight(row, ["Matching by clubs", "matchByClubs"]),
                },
            )
            mentees.append(mentee)

    return mentees


def parse_mentor_csv(file_path):
    """
    Parse a mentor CSV export into a list of Mentor objects.
    """
    mentors = []

    with open(file_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            mentor = Mentor(
                # Identification
                email=clean_string(row.get("Email Address")),
                name=clean_string(row.get("First & Last Name")),

                # Checkbox fields → list[str]
                education_level=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What is your highest level of completed education?",
                            "educationLevel",
                        ],
                    )
                ),
                degrees_completed=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What degree(s) have you completed",
                            "degreePrograms",
                            "degrees_completed",
                        ],
                    )
                ),
                industries=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What industry do you work in?",
                            "industriesOfInterest",
                            "industries",
                        ],
                    )
                ),
                interests=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What are your areas of expertise?",
                            "academicInterests",
                            "interests",
                        ],
                    )
                ),
                orgs=split_checkbox_field(
                    _first_present(
                        row,
                        [
                            "What organizations are you affiliated with?",
                            "orgs",
                        ],
                    )
                ),
                about=clean_string(
                    _first_present(
                        row,
                        [
                            "Tell us about yourself",
                            "About Yourself",
                            "aboutYourself",
                        ],
                    )
                ),
            )
            mentors.append(mentor)

    return mentors
