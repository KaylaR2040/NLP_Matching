# =============================================================================
# File: csv_parse.py
# Purpose: Parse and normalize Google Forms CSV exports for mentors and mentees
#          into clean Python data structures for downstream matching.
# =============================================================================

import csv


# =============================================================================
# Data Structures
# =============================================================================
class Mentee:
    def __init__(self, email, name, education_level, major, prior_mentorship):
        self.email = email                          # Unique ID (email submits once)
        self.name = name                            # Full name [str]
        self.education_level = education_level      # Current education level(s) [list[str]]
        self.major = major                          # Major(s) [list[str]]
        self.prior_mentorship = prior_mentorship    # Prior mentorship [bool]


class Mentor:
    def __init__(self, email, name, education_level, degrees_completed):
        self.email = email                          # Unique ID (email submits once)
        self.name = name                            # Full name [str]
        self.education_level = education_level      # Highest completed education level(s) [list[str]]
        self.degrees_completed = degrees_completed  # Degree(s) completed [list[str]]


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

            education_field = row.get("What level of Education you are currently pursuing?")
            if not education_field:
                education_field = row.get("What level of Education you are currently pursuing or considering?")

            mentee = Mentee(
                # Identification
                email=clean_string(row.get("Email Address")),
                name=clean_string(row.get("First & Last Name")),

                # Checkbox fields stored as list[str]
                education_level=split_checkbox_field(education_field),
                major=split_checkbox_field(
                    row.get("What is your major(s)")
                ),

                # Prior Mentorship stored as bool
                prior_mentorship=prior_mentorship
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
                    row.get("What is your highest level of completed education?")
                ),
                degrees_completed=split_checkbox_field(
                    row.get("What degree(s) have you completed")
                ),
            )
            mentors.append(mentor)

    return mentors
