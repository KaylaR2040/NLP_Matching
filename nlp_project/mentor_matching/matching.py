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


def _coverage_ranked_pairs(ranked_pairs: Sequence[PairScore]) -> List[PairScore]:
    """Re-sort pairs for the coverage pass using per-mentor normalized scores.

    Each mentor's raw scores are scaled so their personal best becomes 1.0.
    This lets a mentor with generally lower scores still compete fairly for
    their best available mentee instead of being crowded out globally.
    The original PairScore objects are returned — only sort order changes.
    """
    mentor_max: Dict[str, float] = {}
    for pair in ranked_pairs:
        if pair.match_score > mentor_max.get(pair.mentor_id, 0.0):
            mentor_max[pair.mentor_id] = pair.match_score

    def normalized(pair: PairScore) -> float:
        denom = mentor_max.get(pair.mentor_id, 1.0)
        return pair.match_score / denom if denom > 0.0 else 0.0

    return sorted(ranked_pairs, key=normalized, reverse=True)


def greedy_assign(
    ranked_pairs: Sequence[PairScore],
    mentors: Sequence[Mentor],
    locked_pairs: Set[PairKey],
) -> List[PairScore]:
    """Two-phase capacity-aware assignment that guarantees mentor coverage.

    Phase 0 — locked pairs are applied first regardless of score.
    Phase 1 — coverage pass: every mentor is capped at 1 mentee.
               Uses per-mentor normalized ordering so lower-scoring mentors
               still compete fairly for their best available mentee.
               No mentor receives a second mentee until every possible mentor
               has at least one.
    Phase 2 — overflow pass: remaining unmatched mentees are assigned to
               mentors who have remaining capacity (max_mentees > 1).
               Uses global score ordering so the best overflow pairs win.
    """
    assigned_mentees: Set[str] = set()
    assignments: List[PairScore] = []
    mentor_capacity: Dict[str, int] = {
        mentor.mentor_id: max(1, int(mentor.max_mentees))
        for mentor in mentors
    }
    mentor_load: Dict[str, int] = {mentor_id: 0 for mentor_id in mentor_capacity}

    lookup: Dict[PairKey, PairScore] = {
        (pair.mentee_id, pair.mentor_id): pair
        for pair in ranked_pairs
    }

    # ── Phase 0: locked pairs ────────────────────────────────────────────────
    for locked_pair in sorted(locked_pairs):
        if locked_pair not in lookup:
            continue
        locked_score = replace(lookup[locked_pair], locked=True)
        if locked_score.mentee_id in assigned_mentees:
            continue
        if locked_score.mentor_id not in mentor_capacity:
            continue
        if mentor_load[locked_score.mentor_id] >= mentor_capacity[locked_score.mentor_id]:
            continue
        assignments.append(locked_score)
        assigned_mentees.add(locked_score.mentee_id)
        mentor_load[locked_score.mentor_id] += 1

    # ── Phase 1: coverage pass ───────────────────────────────────────────────
    # Cap every mentor at 1 so no mentor gets a second mentee before all
    # mentors have had the chance to get their first.
    # Per-mentor normalized ordering ensures low-scoring mentors can still
    # claim their best available mentee.
    for pair in _coverage_ranked_pairs(ranked_pairs):
        if pair.mentee_id in assigned_mentees:
            continue
        if pair.mentor_id not in mentor_capacity:
            continue
        if mentor_load[pair.mentor_id] >= 1:
            continue  # already has one — wait for Phase 2
        assignments.append(pair)
        assigned_mentees.add(pair.mentee_id)
        mentor_load[pair.mentor_id] += 1

    # ── Phase 2: overflow pass ───────────────────────────────────────────────
    # Fill remaining capacity for mentors who can take more than one mentee.
    # Uses global score ordering so the best overflow pairs win.
    for pair in ranked_pairs:
        if pair.mentee_id in assigned_mentees:
            continue
        if pair.mentor_id not in mentor_capacity:
            continue
        if mentor_load[pair.mentor_id] >= mentor_capacity[pair.mentor_id]:
            continue
        overflow_pair = replace(
            pair,
            match_reason=(
                f"[Additional assignment] {pair.match_reason}"
                if pair.match_reason
                else "[Additional assignment]"
            ),
        )
        assignments.append(overflow_pair)
        assigned_mentees.add(pair.mentee_id)
        mentor_load[pair.mentor_id] += 1

    return assignments
