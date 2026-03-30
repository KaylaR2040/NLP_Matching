"""Candidate generation and assignment algorithms."""

from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .models import Mentee, Mentor, PairScore
from .scoring import score_pair
from .state_store import MatchingState


PairKey = Tuple[str, str]


def build_ranked_pairs(
    mentees: Sequence[Mentee],
    mentors: Sequence[Mentor],
    state: MatchingState,
    prohibited_pairs: Set[PairKey],
    locked_pairs: Set[PairKey],
) -> List[PairScore]:
    """Build all legal candidate pairs and sort by descending match score."""
    ranked: List[PairScore] = []

    for mentee in mentees:
        for mentor in mentors:
            key = (mentee.mentee_id, mentor.mentor_id)
            if key in prohibited_pairs and key not in locked_pairs:
                continue
            ranked.append(score_pair(mentee, mentor, state))

    return sorted(ranked, key=lambda pair: pair.match_score, reverse=True)


def greedy_assign(
    ranked_pairs: Sequence[PairScore],
    locked_pairs: Set[PairKey],
) -> List[PairScore]:
    """One-to-one assignment with locked pairs applied first."""
    assigned_mentees: Set[str] = set()
    assigned_mentors: Set[str] = set()
    assignments: List[PairScore] = []

    lookup: Dict[PairKey, PairScore] = {
        (pair.mentee_id, pair.mentor_id): pair
        for pair in ranked_pairs
    }

    for locked_pair in sorted(locked_pairs):
        if locked_pair not in lookup:
            continue
        locked_score = replace(lookup[locked_pair], locked=True)
        assignments.append(locked_score)
        assigned_mentees.add(locked_score.mentee_id)
        assigned_mentors.add(locked_score.mentor_id)

    for pair in ranked_pairs:
        if pair.mentee_id in assigned_mentees or pair.mentor_id in assigned_mentors:
            continue
        assignments.append(pair)
        assigned_mentees.add(pair.mentee_id)
        assigned_mentors.add(pair.mentor_id)

    return assignments
