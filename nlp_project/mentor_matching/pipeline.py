"""End-to-end matching pipeline orchestration."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List

from .constraints import (
    apply_user_exclusions,
    build_locked_pairs,
    build_prohibited_pairs,
    validate_locked_pairs,
)
from .embeddings import attach_embeddings
from .matching import build_ranked_pairs, greedy_assign
from .models import Mentee, Mentor, PairScore
from .parsing import parse_mentee_csv, parse_mentor_csv
from .retry_utils import run_with_retry
from .state_store import MatchingState
from .text_processing import attach_nlp_features


@dataclass
class MatchingRunResult:
    """Structured output from a matching run."""

    mentees: List[Mentee]
    mentors: List[Mentor]
    ranked_pairs: List[PairScore]
    assignments: List[PairScore]
    summary: Dict[str, int]


class MatchingPipeline:
    """Coordinator for the mentor-mentee matching run."""

    def run(
        self,
        mentee_csv_path: Path,
        mentor_csv_path: Path,
        state: MatchingState,
    ) -> MatchingRunResult:
        # Step 1: read raw CSV rows into typed Mentee and Mentor objects.
        mentees = run_with_retry("parse_mentee_csv", lambda: parse_mentee_csv(mentee_csv_path))
        mentors = run_with_retry("parse_mentor_csv", lambda: parse_mentor_csv(mentor_csv_path))

        # Step 2: apply manual exclusions from persisted rerun state before NLP/scoring.
        filtered_mentees, filtered_mentors = apply_user_exclusions(mentees, mentors, state)

        # Step 3: build normalized NLP text for every participant.
        # This is preprocessing only; no model training happens here.
        attach_nlp_features(filtered_mentees)
        attach_nlp_features(filtered_mentors)

        # Step 4: build segmented semantic embeddings (industry/degree/personality).
        # Embeddings are generated in batch before scoring for runtime efficiency.
        attach_embeddings(filtered_mentees)
        attach_embeddings(filtered_mentors)

        # Step 5: load pair-level constraints before ranking mentor/mentee pairs.
        prohibited_pairs = build_prohibited_pairs(state)
        locked_pairs = validate_locked_pairs(
            build_locked_pairs(state),
            mentee_ids={mentee.mentee_id for mentee in filtered_mentees},
            mentor_ids={mentor.mentor_id for mentor in filtered_mentors},
        )

        # Step 6: score every possible mentor/mentee pair using segmented semantics + direct factors.
        ranked_pairs = build_ranked_pairs(
            filtered_mentees,
            filtered_mentors,
            state,
            prohibited_pairs=prohibited_pairs,
            locked_pairs=locked_pairs,
        )

        # Step 7: choose final assignments from the ranked pair list.
        assignments = greedy_assign(ranked_pairs, mentors, locked_pairs)

        summary = {
            "mentees_input": len(mentees),
            "mentors_input": len(mentors),
            "mentees_after_exclusions": len(filtered_mentees),
            "mentors_after_exclusions": len(filtered_mentors),
            "ranked_pairs": len(ranked_pairs),
            "assignments": len(assignments),
        }

        return MatchingRunResult(
            mentees=filtered_mentees,
            mentors=filtered_mentors,
            ranked_pairs=ranked_pairs,
            assignments=assignments,
            summary=summary,
        )


def write_outputs(result: MatchingRunResult, output_dir: Path, top_n: int = 25) -> None:
    """Persist the final ranking/assignment artifacts after pipeline execution."""
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": result.summary,
        "assignments": [pair.to_dict() for pair in result.assignments],
        "top_ranked_pairs": [pair.to_dict() for pair in result.ranked_pairs[:top_n]],
    }

    (output_dir / "latest_matches.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    csv_path = output_dir / "latest_assignments.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "mentee_id",
                "mentee_name",
                "mentor_id",
                "mentor_name",
                "match_score",
                "match_percent",
                "match_band",
                "match_reason",
                "locked",
            ],
        )
        writer.writeheader()
        for pair in result.assignments:
            row = pair.to_dict()
            writer.writerow(
                {
                    "mentee_id": row["mentee_id"],
                    "mentee_name": row["mentee_name"],
                    "mentor_id": row["mentor_id"],
                    "mentor_name": row["mentor_name"],
                    "match_score": f"{row['match_score']:.6f}",
                    "match_percent": row["match_percent"],
                    "match_band": row.get("match_band", ""),
                    "match_reason": row.get("match_reason", ""),
                    "locked": row["locked"],
                }
            )
