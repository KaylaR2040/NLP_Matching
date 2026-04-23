"""Constraint helpers for exclusions and prohibited pair filtering."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Set, Tuple

from .models import Mentee, Mentor
from .state_store import MatchingState


def apply_user_exclusions(
    mentees: Sequence[Mentee],
    mentors: Sequence[Mentor],
    state: MatchingState,
) -> tuple[List[Mentee], List[Mentor]]:
    """Remove users that were explicitly excluded from algorithmic matching."""
    filtered_mentees = [m for m in mentees if m.mentee_id not in state.excluded_mentee_ids]
    filtered_mentors = [m for m in mentors if m.mentor_id not in state.excluded_mentor_ids]
    return filtered_mentees, filtered_mentors


def build_prohibited_pairs(state: MatchingState) -> Set[Tuple[str, str]]:
    """Pairs that should never be produced by the candidate ranking step."""
    return set(state.rejected_pair_tuples())


def build_locked_pairs(state: MatchingState) -> Set[Tuple[str, str]]:
    """Pairs that should always be included before greedy assignment starts."""
    return set(state.locked_pair_tuples())


def validate_locked_pairs(
    locked_pairs: Iterable[Tuple[str, str]],
    mentee_ids: Set[str],
    mentor_ids: Set[str],
) -> Set[Tuple[str, str]]:
    """Only keep lock entries that still reference active users."""
    valid: Set[Tuple[str, str]] = set()
    for mentee_id, mentor_id in locked_pairs:
        if mentee_id in mentee_ids and mentor_id in mentor_ids:
            valid.add((mentee_id, mentor_id))
    return valid
