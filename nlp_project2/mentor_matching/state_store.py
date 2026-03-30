"""State persistence for rerunnable mentor-mentee matching."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .constants import FACTOR_KEYS
from .retry_utils import run_with_retry


def _pair_key(mentee_id: str, mentor_id: str) -> str:
    return f"{mentee_id}::{mentor_id}"


def _parse_pair_key(value: str) -> Tuple[str, str]:
    if "::" not in value:
        return value, ""
    return tuple(value.split("::", 1))  # type: ignore[return-value]


@dataclass
class MatchingState:
    """Mutable state that controls reruns and manual constraints."""

    excluded_mentee_ids: Set[str] = field(default_factory=set)
    excluded_mentor_ids: Set[str] = field(default_factory=set)
    rejected_pairs: Set[str] = field(default_factory=set)
    locked_pairs: Set[str] = field(default_factory=set)
    global_weights: Dict[str, float] = field(default_factory=dict)
    mentee_weight_overrides: Dict[str, Dict[str, float]] = field(default_factory=dict)
    run_count: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": 1,
            "excluded_mentee_ids": sorted(self.excluded_mentee_ids),
            "excluded_mentor_ids": sorted(self.excluded_mentor_ids),
            "rejected_pairs": sorted(self.rejected_pairs),
            "locked_pairs": sorted(self.locked_pairs),
            "global_weights": self.global_weights,
            "mentee_weight_overrides": self.mentee_weight_overrides,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "MatchingState":
        return cls(
            excluded_mentee_ids=set(payload.get("excluded_mentee_ids", [])),
            excluded_mentor_ids=set(payload.get("excluded_mentor_ids", [])),
            rejected_pairs=set(payload.get("rejected_pairs", [])),
            locked_pairs=set(payload.get("locked_pairs", [])),
            global_weights=dict(payload.get("global_weights", {})),
            mentee_weight_overrides=dict(payload.get("mentee_weight_overrides", {})),
            run_count=int(payload.get("run_count", 0)),
        )

    def reject_pair(self, mentee_id: str, mentor_id: str) -> None:
        self.rejected_pairs.add(_pair_key(mentee_id, mentor_id))

    def unreject_pair(self, mentee_id: str, mentor_id: str) -> None:
        self.rejected_pairs.discard(_pair_key(mentee_id, mentor_id))

    def lock_pair(self, mentee_id: str, mentor_id: str) -> None:
        self.locked_pairs.add(_pair_key(mentee_id, mentor_id))

    def unlock_pair(self, mentee_id: str, mentor_id: str) -> None:
        self.locked_pairs.discard(_pair_key(mentee_id, mentor_id))

    def exclude_user(self, role: str, user_id: str) -> None:
        if role == "mentee":
            self.excluded_mentee_ids.add(user_id)
            return
        self.excluded_mentor_ids.add(user_id)

    def include_user(self, role: str, user_id: str) -> None:
        if role == "mentee":
            self.excluded_mentee_ids.discard(user_id)
            return
        self.excluded_mentor_ids.discard(user_id)

    def set_global_weight(self, factor: str, value: float) -> None:
        if factor not in FACTOR_KEYS:
            raise ValueError(f"Unknown factor '{factor}'. Allowed: {', '.join(FACTOR_KEYS)}")
        self.global_weights[factor] = value

    def set_mentee_weight(self, mentee_id: str, factor: str, value: float) -> None:
        if factor not in FACTOR_KEYS:
            raise ValueError(f"Unknown factor '{factor}'. Allowed: {', '.join(FACTOR_KEYS)}")
        self.mentee_weight_overrides.setdefault(mentee_id, {})[factor] = value

    def rejected_pair_tuples(self) -> Set[Tuple[str, str]]:
        return {_parse_pair_key(item) for item in self.rejected_pairs}

    def locked_pair_tuples(self) -> Set[Tuple[str, str]]:
        return {_parse_pair_key(item) for item in self.locked_pairs}


def load_state(path: str | Path) -> MatchingState:
    state_path = Path(path)

    def _load() -> MatchingState:
        if not state_path.exists():
            return MatchingState()
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("State file must contain a JSON object")
        return MatchingState.from_dict(payload)

    return run_with_retry("load_state", _load)


def save_state(state: MatchingState, path: str | Path) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    def _save() -> None:
        state_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

    run_with_retry("save_state", _save)
