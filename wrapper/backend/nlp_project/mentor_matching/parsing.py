"""CSV parsing utilities for mentor and mentee datasets."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .constants import DEFAULT_BASE_WEIGHTS
from .models import Mentee, Mentor


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def _first_present(row: Dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and _clean(value):
            return _clean(value)
    return ""


def _split_multi_value(raw: str) -> List[str]:
    clean = _clean(raw)
    if not clean:
        return []
    parts = re.split(r"[|,;/]", clean)
    return [part.strip() for part in parts if part.strip()]


def _safe_int(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _safe_priority_rank(raw: str, default: int = 2) -> int:
    if not _clean(raw):
        return default
    try:
        value = int(round(float(raw)))
    except ValueError:
        return default
    return min(4, max(1, value))


def _ranking_aliases() -> Dict[str, Sequence[str]]:
    return {
        "industry": (
            "rank_industry",
            "weight_industry",
            "industry_rank",
            "industry_weight",
            "matching by industry",
            "match by industry",
            "matchbyindustry",
            "matchByIndustry",
        ),
        "degree": (
            "rank_degree",
            "weight_degree",
            "degree_rank",
            "degree_weight",
            "match by degree",
            "matching by degree",
            "matchbydegree",
            "matchByDegree",
        ),
        "orgs": (
            "rank_orgs",
            "weight_orgs",
            "orgs_rank",
            "orgs_weight",
            "match by clubs",
            "matching by clubs",
            "matchbyclubs",
            "matchByClubs",
        ),
        "identity": (
            "rank_identity",
            "weight_identity",
            "identity_rank",
            "identity_weight",
            "match by identity",
            "matching by identity",
            "matchbyidentity",
            "matchByIdentity",
        ),
        "grad_year": (
            "rank_grad_year",
            "weight_grad_year",
            "grad_year_rank",
            "grad_year_weight",
            "match by grad years",
            "matching by grad years",
            "matchbygradyears",
            "matchByGradYears",
        ),
        "personality": (
            "rank_personality",
            "weight_personality",
            "personality_rank",
            "personality_weight",
            "match by personality",
            "matching by personality",
            "matchbypersonality",
            "matchByPersonality",
        ),
    }


def _normalize_headers(row: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in row.items():
        normalized[key] = value
        normalized[key.strip().lower()] = value
    return normalized


def _parse_embedded_json(row: Dict[str, str]) -> Dict[str, Any]:
    raw = row.get("JSON FILE") or row.get("json file") or ""
    if not _clean(raw):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _json_list(payload: Dict[str, Any], *keys: str) -> List[str]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            output: List[str] = []
            for item in value:
                if isinstance(item, dict):
                    text = _clean(item.get("program") or item.get("value") or item.get("name"))
                else:
                    text = _clean(item)
                if text:
                    output.append(text)
            return output
    return []


def _json_str(payload: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            text = ", ".join(_clean(item) for item in value if _clean(item))
            if text:
                return text
        text = _clean(value)
        if text:
            return text
    return ""


def _safe_positive_int(raw: str, default: int = 1) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _mentor_capacity(payload: Dict[str, Any], row: Dict[str, str]) -> int:
    raw = _json_str(payload, "studentsInterested") or _first_present(row, ("students interested",))
    match = re.search(r"(\d+)", raw)
    if match:
        return _safe_positive_int(match.group(1), default=1)
    return 1


def _mentor_degree_programs(payload: Dict[str, Any], row: Dict[str, str]) -> List[str]:
    degrees = payload.get("degrees")
    if isinstance(degrees, list):
        programs: List[str] = []
        for entry in degrees:
            if not isinstance(entry, dict):
                continue
            level = _clean(entry.get("level"))
            program = _clean(entry.get("program"))
            combined = " ".join(part for part in (level, program) if part).strip()
            if combined:
                programs.append(combined)
        if programs:
            return programs
    return _split_multi_value(_first_present(row, ("degrees", "degreessummary")))


def _mentor_graduation_year(payload: Dict[str, Any], row: Dict[str, str]) -> str:
    degrees = payload.get("degrees")
    if isinstance(degrees, list):
        years = [
            _clean(entry.get("graduationYear"))
            for entry in degrees
            if isinstance(entry, dict) and _clean(entry.get("graduationYear"))
        ]
        if years:
            return years[-1]
    text = _first_present(row, ("degrees", "degreessummary"))
    match = re.search(r"\((\d{4})\)", text)
    return match.group(1) if match else ""


def _extract_ranking_preferences(row: Dict[str, str]) -> Dict[str, int]:
    normalized = _normalize_headers(row)
    embedded_json = _parse_embedded_json(row)
    normalized.update({key: str(value) for key, value in embedded_json.items() if not isinstance(value, (dict, list))})
    alias_map = _ranking_aliases()
    output: Dict[str, int] = {}

    for factor in DEFAULT_BASE_WEIGHTS:
        aliases = alias_map.get(factor, ())
        extracted = ""
        for alias in aliases:
            if alias in normalized and _clean(normalized[alias]):
                extracted = normalized[alias]
                break
        output[factor] = _safe_priority_rank(extracted, default=2)

    return output


def _extract_ranking_weights(row: Dict[str, str]) -> Dict[str, float]:
    return {
        factor: float(value)
        for factor, value in _extract_ranking_preferences(row).items()
    }


def parse_mentee_csv(path: str | Path) -> List[Mentee]:
    """Parse mentees from CSV into strongly typed records."""
    mentees: List[Mentee] = []

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            clean_row = _normalize_headers(row)
            embedded_json = _parse_embedded_json(row)
            first_name = _json_str(embedded_json, "firstName") or _first_present(clean_row, ("first name", "first_name"))
            last_name = _json_str(embedded_json, "lastName") or _first_present(clean_row, ("last name", "last_name"))
            mentees.append(
                Mentee(
                    mentee_id=_json_str(embedded_json, "email", "id", "submissionId")
                    or _first_present(clean_row, ("mentee_id", "id", "email")),
                    name=" ".join(part for part in (first_name, last_name) if part).strip()
                    or _first_present(clean_row, ("mentee_name", "name", "full name")),
                    role=_json_str(embedded_json, "experienceLevel")
                    or _first_present(clean_row, ("role", "program", "title", "experience level")),
                    pronouns=_json_str(embedded_json, "pronounsText", "pronouns")
                    or _first_present(clean_row, ("pronouns",)),
                    degree_programs=_json_list(embedded_json, "degreePrograms")
                    or _split_multi_value(_first_present(clean_row, ("degree programs",))),
                    student_orgs=_json_list(embedded_json, "studentOrgs")
                    or _split_multi_value(_first_present(clean_row, ("student orgs",))),
                    graduation_year=_json_str(embedded_json, "graduationYear")
                    or _first_present(clean_row, ("graduation year",)),
                    education_level=_json_str(embedded_json, "educationLevel")
                    or _first_present(clean_row, ("education level",)),
                    help_topics=_json_list(embedded_json, "helpTopics")
                    or _split_multi_value(_first_present(clean_row, ("help topics",))),
                    interests=_json_list(embedded_json, "industriesOfInterest")
                    or _split_multi_value(_first_present(clean_row, ("industries of interest", "interests"))),
                    goals=", ".join(
                        _json_list(embedded_json, "helpTopics")
                        or _split_multi_value(_first_present(clean_row, ("help topics", "goals", "goal", "mentee_goals")))
                    ),
                    background=_json_str(embedded_json, "aboutYourself")
                    or _first_present(clean_row, ("about yourself", "background", "bio", "about")),
                    source_mentor_id=_first_present(clean_row, ("source_mentor_id",)),
                    source_row_index=_safe_int(_first_present(clean_row, ("source_row_index",))),
                    ranking_preferences=_extract_ranking_preferences(clean_row),
                    ranking_weights=_extract_ranking_weights(clean_row),
                )
            )

    return mentees


def parse_mentor_csv(path: str | Path) -> List[Mentor]:
    """Parse mentors from CSV into strongly typed records."""
    mentors: List[Mentor] = []

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            clean_row = _normalize_headers(row)
            embedded_json = _parse_embedded_json(row)
            first_name = _json_str(embedded_json, "firstName") or _first_present(clean_row, ("first name", "first_name"))
            last_name = _json_str(embedded_json, "lastName") or _first_present(clean_row, ("last name", "last_name"))
            mentors.append(
                Mentor(
                    mentor_id=_json_str(embedded_json, "email", "id", "submissionId")
                    or _first_present(clean_row, ("mentor_id", "id", "email")),
                    name=" ".join(part for part in (first_name, last_name) if part).strip()
                    or _first_present(clean_row, ("mentor_name", "name", "full name")),
                    role=_json_str(embedded_json, "currentJobTitle")
                    or _first_present(clean_row, ("current job title", "role", "title")),
                    pronouns=_json_str(embedded_json, "pronouns")
                    or _first_present(clean_row, ("pronouns",)),
                    degree_programs=_mentor_degree_programs(embedded_json, clean_row),
                    student_orgs=_json_list(embedded_json, "previousInvolvementOrgs")
                    or _split_multi_value(_first_present(clean_row, ("previous involvement organizations",))),
                    graduation_year=_mentor_graduation_year(embedded_json, clean_row),
                    help_topics=_json_list(embedded_json, "helpTopics"),
                    max_mentees=_mentor_capacity(embedded_json, clean_row),
                    expertise=_json_list(embedded_json, "industryFocusArea")
                    or _split_multi_value(_first_present(clean_row, ("industry focus area", "expertise", "industries", "domain"))),
                    goals=_json_str(embedded_json, "whyInterested")
                    or _first_present(clean_row, ("why interested", "goals", "goal", "mentor_goals")),
                    bio=_json_str(embedded_json, "aboutYourself")
                    or _first_present(clean_row, ("about yourself", "bio", "about")),
                    prior_mentoring_experience=_json_str(embedded_json, "previousMentorship")
                    or _first_present(clean_row, ("previous mentorship", "prior_mentoring_experience")),
                    mentorship_motivation=_json_str(embedded_json, "whyInterested")
                    or _first_present(clean_row, ("why interested", "mentorship_motivation")),
                    professional_experience=_json_str(embedded_json, "professionalExperience")
                    or _first_present(clean_row, ("professional experience",)),
                    personal_interests=_split_multi_value(
                        _json_str(embedded_json, "aboutYourself")
                        or _first_present(clean_row, ("personal interests", "hobbies", "interests", "about yourself"))
                    ),
                    domain_tags=_split_multi_value(_first_present(clean_row, ("current company", "current state", "current city"))),
                    source_row_index=_safe_int(_first_present(clean_row, ("source_row_index",))),
                )
            )

    return mentors
