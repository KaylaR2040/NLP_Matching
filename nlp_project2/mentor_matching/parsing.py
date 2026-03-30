"""CSV parsing utilities for mentor and mentee datasets."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .constants import FACTOR_KEYS
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


def _safe_positive_float(raw: str, default: float = 1.0) -> float:
    if not _clean(raw):
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _ranking_aliases() -> Dict[str, Sequence[str]]:
    return {
        "industry": (
            "rank_industry",
            "weight_industry",
            "industry_rank",
            "industry_weight",
            "matching by industry",
            "matchbyindustry",
        ),
        "topics": (
            "rank_topics",
            "weight_topics",
            "topic_rank",
            "topic_weight",
            "matching by topics",
            "matchbytopics",
            "matchbyinterests",
        ),
        "style": (
            "rank_style",
            "weight_style",
            "style_rank",
            "style_weight",
            "matching by style",
        ),
        "availability": (
            "rank_availability",
            "weight_availability",
            "availability_rank",
            "availability_weight",
            "matching by availability",
        ),
        "nlp": (
            "rank_nlp",
            "weight_nlp",
            "nlp_rank",
            "nlp_weight",
            "matching by bio",
            "matching by about",
        ),
    }


def _normalize_headers(row: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in row.items():
        normalized[key] = value
        normalized[key.strip().lower()] = value
    return normalized


def _extract_ranking_weights(row: Dict[str, str]) -> Dict[str, float]:
    normalized = _normalize_headers(row)
    alias_map = _ranking_aliases()
    output: Dict[str, float] = {}

    for factor in FACTOR_KEYS:
        aliases = alias_map.get(factor, ())
        extracted = ""
        for alias in aliases:
            if alias in normalized and _clean(normalized[alias]):
                extracted = normalized[alias]
                break
        output[factor] = _safe_positive_float(extracted, default=1.0)

    return output


def parse_mentee_csv(path: str | Path) -> List[Mentee]:
    """Parse mentees from CSV into strongly typed records."""
    mentees: List[Mentee] = []

    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            clean_row = _normalize_headers(row)
            mentees.append(
                Mentee(
                    mentee_id=_first_present(clean_row, ("mentee_id", "id", "email")),
                    name=_first_present(clean_row, ("mentee_name", "name", "full_name")),
                    role=_first_present(clean_row, ("role", "program", "title")),
                    interests=_split_multi_value(_first_present(clean_row, ("interests",))),
                    goals=_first_present(clean_row, ("goals", "goal", "mentee_goals")),
                    topics=_split_multi_value(_first_present(clean_row, ("topics", "topic"))),
                    style=_split_multi_value(_first_present(clean_row, ("style", "communication_style"))),
                    availability=_split_multi_value(_first_present(clean_row, ("availability",))),
                    background=_first_present(clean_row, ("background", "bio", "about")),
                    source_mentor_id=_first_present(clean_row, ("source_mentor_id",)),
                    source_row_index=_safe_int(_first_present(clean_row, ("source_row_index",))),
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
            mentors.append(
                Mentor(
                    mentor_id=_first_present(clean_row, ("mentor_id", "id", "email")),
                    name=_first_present(clean_row, ("mentor_name", "name", "full_name")),
                    role=_first_present(clean_row, ("role", "title")),
                    expertise=_split_multi_value(_first_present(clean_row, ("expertise", "industries", "domain"))),
                    goals=_first_present(clean_row, ("goals", "goal", "mentor_goals")),
                    topics=_split_multi_value(_first_present(clean_row, ("topics", "topic"))),
                    style=_split_multi_value(_first_present(clean_row, ("style", "communication_style"))),
                    availability=_split_multi_value(_first_present(clean_row, ("availability",))),
                    bio=_first_present(clean_row, ("bio", "about")),
                    prior_mentoring_experience=_first_present(clean_row, ("prior_mentoring_experience",)),
                    mentorship_motivation=_first_present(clean_row, ("mentorship_motivation",)),
                    professional_experience=_first_present(clean_row, ("professional_experience",)),
                    personal_interests=_split_multi_value(_first_present(clean_row, ("personal_interests",))),
                    domain_tags=_split_multi_value(_first_present(clean_row, ("domain_tags", "tags"))),
                    source_row_index=_safe_int(_first_present(clean_row, ("source_row_index",))),
                )
            )

    return mentors
