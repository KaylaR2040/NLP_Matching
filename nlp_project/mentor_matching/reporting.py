"""CLI reporting helpers."""

from __future__ import annotations

from typing import Sequence

from .models import PairScore
from .pipeline import MatchingRunResult


def print_nlp_preview(people: Sequence[object], label: str) -> None:
    """Show one representative NLP feature preview in CLI output."""
    if not people:
        return

    person = people[0]
    print(f"\n=== NLP Preview: {label} ===")
    print(f"Name: {person.name}")
    print(f"Sentences: {person.nlp.sentences[:2]}")
    print(f"Tokens: {person.nlp.tokens[:12]}")
    print(f"Filtered Tokens: {person.nlp.filtered_tokens[:12]}")
    print(f"Normalized Text: {person.nlp.normalized_text[:140]}")


def print_run_summary(result: MatchingRunResult, top_n: int = 5) -> None:
    """Print concise run summary and final assignment results."""
    print("\n=== Summary ===")
    for key, value in result.summary.items():
        print(f"{key}: {value}")

    print("\nFinal Assignments")
    print("=" * 60)
    for idx, pair in enumerate(result.assignments[:top_n], start=1):
        _print_pair(idx, pair)


def _print_pair(index: int, pair: PairScore) -> None:
    print(f"\n#{index} {pair.mentee_name} ({pair.mentee_id}) -> {pair.mentor_name} ({pair.mentor_id})")
    print(f"  Match: {pair.match_score * 100:.2f}%")
    for key, value in pair.component_scores.items():
        weight = pair.display_weights.get(key, 0.0) * 100.0
        print(f"  - {key:<12} score={value:.3f} weight={weight:.0f}%")
