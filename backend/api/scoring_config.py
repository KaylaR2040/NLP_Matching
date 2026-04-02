"""CSV-backed scoring configuration for the API matcher."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


DIRECT_MATCH_FACTORS = ("industry", "degree", "orgs", "identity", "grad_year")
DEFAULT_SCORING_CSV = Path(__file__).resolve().parents[2] / "nlp_project" / "scoring.csv"

_CACHE_KEY: tuple[int, int] | None = None
_CACHE_VALUE: "ScoringConfig" | None = None


@dataclass(frozen=True)
class ScoringConfig:
    priorities_by_factor: Dict[str, Dict[int, float]]
    nlp_weight: float


def _parse_float(value: str, *, field_name: str, section: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name!r} value for section {section!r}: {value!r}") from exc


def _read_scoring_csv(path: Path) -> ScoringConfig:
    if not path.exists():
        raise FileNotFoundError(f"Scoring config not found: {path}")

    priorities_by_factor: Dict[str, Dict[int, float]] = {}
    nlp_weight: float | None = None

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"section", "rank_1", "rank_2", "rank_3", "rank_4", "nlp_weight"}
        if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"Scoring config {path} must include columns: {', '.join(sorted(required_columns))}"
            )

        for raw_row in reader:
            section = str(raw_row.get("section", "")).strip().lower()
            if not section:
                continue

            if section == "nlp":
                raw_nlp_weight = str(raw_row.get("nlp_weight", "")).strip()
                if not raw_nlp_weight:
                    raise ValueError("The 'nlp' section in scoring.csv must define nlp_weight")
                nlp_weight = _parse_float(raw_nlp_weight, field_name="nlp_weight", section=section)
                continue

            if section not in DIRECT_MATCH_FACTORS:
                raise ValueError(
                    f"Unknown scoring section {section!r} in {path}. "
                    f"Expected one of: {', '.join((*DIRECT_MATCH_FACTORS, 'nlp'))}"
                )

            priorities_by_factor[section] = {
                ranking: _parse_float(str(raw_row.get(f"rank_{ranking}", "")).strip(), field_name=f"rank_{ranking}", section=section)
                for ranking in (1, 2, 3, 4)
            }

    missing_sections = [factor for factor in DIRECT_MATCH_FACTORS if factor not in priorities_by_factor]
    if missing_sections:
        raise ValueError(f"Missing scoring rows for sections: {', '.join(missing_sections)}")

    if nlp_weight is None:
        raise ValueError("Missing 'nlp' row in scoring.csv")
    if not 0.0 <= nlp_weight <= 1.0:
        raise ValueError(f"nlp_weight must be between 0.0 and 1.0, received {nlp_weight}")

    return ScoringConfig(priorities_by_factor=priorities_by_factor, nlp_weight=nlp_weight)


def load_scoring_config(path: Path = DEFAULT_SCORING_CSV) -> ScoringConfig:
    global _CACHE_KEY, _CACHE_VALUE

    stat = path.stat()
    cache_key = (stat.st_mtime_ns, stat.st_size)
    if _CACHE_KEY == cache_key and _CACHE_VALUE is not None:
        return _CACHE_VALUE

    config = _read_scoring_csv(path)
    _CACHE_KEY = cache_key
    _CACHE_VALUE = config
    return config
