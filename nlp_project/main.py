"""CLI entrypoint for mentor-mentee matching in nlp_project2.

This script keeps the high-level flow from the original project while adding:
1) modular architecture
2) persistent constraints and weight settings
3) rerunnable matching commands
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from mentor_matching.pipeline import MatchingPipeline, write_outputs
from mentor_matching.reporting import print_nlp_preview, print_run_summary
from mentor_matching.scoring_config import DIRECT_MATCH_FACTORS
from mentor_matching.state_store import MatchingState, load_state, save_state


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MENTEE_CSV = BASE_DIR / "data" / "sample_mentees.csv"
DEFAULT_MENTOR_CSV = BASE_DIR / "data" / "sample_mentors.csv"
DEFAULT_STATE_PATH = BASE_DIR / "state" / "matching_state.json"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


def _path_arg(raw: str) -> Path:
    return Path(raw).expanduser()


def _weight_value(raw: str) -> float:
    value = float(raw)
    if not 1.0 <= value <= 4.0:
        raise argparse.ArgumentTypeError("Value must be between 1 and 4")
    return value


def _run_pipeline(
    mentee_csv: Path,
    mentor_csv: Path,
    state_path: Path,
    output_dir: Path,
    top_n: int,
    preview: bool,
) -> None:
    # Main flow:
    # 1) load persisted rerun state
    # 2) parse mentee + mentor CSV inputs
    # 3) build NLP features and deterministic embeddings
    # 4) score every mentor/mentee pair
    # 5) assign final matches and write outputs
    state = load_state(state_path)
    pipeline = MatchingPipeline()
    result = pipeline.run(mentee_csv, mentor_csv, state)

    state.run_count += 1
    save_state(state, state_path)
    write_outputs(result, output_dir, top_n=top_n)

    if preview:
        # Optional debug view of the intermediate NLP artifacts produced in step 3.
        print_nlp_preview(result.mentees, "Mentee")
        print_nlp_preview(result.mentors, "Mentor")

    print_run_summary(result, top_n=min(5, top_n))
    print(f"\nState file: {state_path}")
    print(f"Output JSON: {output_dir / 'latest_matches.json'}")
    print(f"Output CSV : {output_dir / 'latest_assignments.csv'}")


def _mutate_state(
    state_path: Path,
    operation: Callable[[MatchingState], None],
    rerun: bool,
    mentee_csv: Path,
    mentor_csv: Path,
    output_dir: Path,
    top_n: int,
    preview: bool,
) -> None:
    state = load_state(state_path)
    operation(state)
    save_state(state, state_path)

    print(f"Updated state: {state_path}")
    if rerun:
        _run_pipeline(mentee_csv, mentor_csv, state_path, output_dir, top_n, preview)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mentor-mentee matching pipeline")

    parser.add_argument("--mentee-csv", type=_path_arg, default=DEFAULT_MENTEE_CSV)
    parser.add_argument("--mentor-csv", type=_path_arg, default=DEFAULT_MENTOR_CSV)
    parser.add_argument("--state-path", type=_path_arg, default=DEFAULT_STATE_PATH)
    parser.add_argument("--output-dir", type=_path_arg, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--preview", action="store_true", help="Print NLP previews")

    subparsers = parser.add_subparsers(dest="command", required=True) 

    subparsers.add_parser("run", help="Run matching with current state")
    subparsers.add_parser("show-state", help="Print current state JSON")
    subparsers.add_parser("clear-state", help="Reset state to defaults")

    reject = subparsers.add_parser("reject", help="Reject a mentor-mentee pair")
    reject.add_argument("--mentee-id", required=True)
    reject.add_argument("--mentor-id", required=True)
    reject.add_argument("--rerun", action="store_true")

    unreject = subparsers.add_parser("unreject", help="Undo a rejected pair")
    unreject.add_argument("--mentee-id", required=True)
    unreject.add_argument("--mentor-id", required=True)
    unreject.add_argument("--rerun", action="store_true")

    lock = subparsers.add_parser("lock", help="Lock a mentor-mentee pair")
    lock.add_argument("--mentee-id", required=True)
    lock.add_argument("--mentor-id", required=True)
    lock.add_argument("--rerun", action="store_true")

    unlock = subparsers.add_parser("unlock", help="Unlock a mentor-mentee pair")
    unlock.add_argument("--mentee-id", required=True)
    unlock.add_argument("--mentor-id", required=True)
    unlock.add_argument("--rerun", action="store_true")

    exclude = subparsers.add_parser("exclude", help="Exclude a user from matching")
    exclude.add_argument("--role", choices=["mentee", "mentor"], required=True)
    exclude.add_argument("--user-id", required=True)
    exclude.add_argument("--rerun", action="store_true")

    include = subparsers.add_parser("include", help="Include a previously excluded user")
    include.add_argument("--role", choices=["mentee", "mentor"], required=True)
    include.add_argument("--user-id", required=True)
    include.add_argument("--rerun", action="store_true")

    set_weight = subparsers.add_parser("set-weight", help="Set global or mentee-specific weight")
    set_weight.add_argument("--scope", choices=["global", "mentee"], required=True)
    set_weight.add_argument("--factor", choices=list(DIRECT_MATCH_FACTORS), required=True)
    set_weight.add_argument("--value", type=_weight_value, required=True)
    set_weight.add_argument("--mentee-id")
    set_weight.add_argument("--rerun", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        _run_pipeline(args.mentee_csv, args.mentor_csv, args.state_path, args.output_dir, args.top_n, args.preview)
        return

    if args.command == "show-state":
        state = load_state(args.state_path)
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.command == "clear-state":
        save_state(MatchingState(), args.state_path)
        print(f"Reset state file: {args.state_path}")
        return

    if args.command == "reject":
        _mutate_state(
            args.state_path,
            lambda state: state.reject_pair(args.mentee_id, args.mentor_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "unreject":
        _mutate_state(
            args.state_path,
            lambda state: state.unreject_pair(args.mentee_id, args.mentor_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "lock":
        _mutate_state(
            args.state_path,
            lambda state: state.lock_pair(args.mentee_id, args.mentor_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "unlock":
        _mutate_state(
            args.state_path,
            lambda state: state.unlock_pair(args.mentee_id, args.mentor_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "exclude":
        _mutate_state(
            args.state_path,
            lambda state: state.exclude_user(args.role, args.user_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "include":
        _mutate_state(
            args.state_path,
            lambda state: state.include_user(args.role, args.user_id),
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    if args.command == "set-weight":
        if args.scope == "mentee" and not args.mentee_id:
            parser.error("--mentee-id is required when --scope mentee")

        def _set_weight(state: MatchingState) -> None:
            if args.scope == "global":
                state.set_global_weight(args.factor, args.value)
            else:
                state.set_mentee_weight(args.mentee_id, args.factor, args.value)

        _mutate_state(
            args.state_path,
            _set_weight,
            args.rerun,
            args.mentee_csv,
            args.mentor_csv,
            args.output_dir,
            args.top_n,
            args.preview,
        )
        return

    parser.error(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    main()
