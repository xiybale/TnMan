from __future__ import annotations

import argparse
import sys

from .calibration import load_calibration_scenarios, run_calibration_suite
from .models import MatchConfig, Surface
from .reporting import (
    format_batch_report,
    format_calibration_report,
    format_match_report,
    format_player_profile,
)
from .roster import load_player, load_roster
from .simulator import MatchSimulator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tennis Pro Manager CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate_match = subparsers.add_parser("simulate-match", help="Simulate one singles match")
    simulate_match.add_argument("player_one")
    simulate_match.add_argument("player_two")
    simulate_match.add_argument("--surface", choices=[surface.value for surface in Surface], default="hard")
    simulate_match.add_argument("--best-of", type=int, default=3, choices=[3, 5])
    simulate_match.add_argument("--seed", type=int, default=1)
    simulate_match.add_argument("--shots", type=int, default=25)
    simulate_match.add_argument("--initial-server")
    simulate_match.add_argument("--roster-path")

    simulate_batch = subparsers.add_parser("simulate-batch", help="Simulate many matches")
    simulate_batch.add_argument("player_one")
    simulate_batch.add_argument("player_two")
    simulate_batch.add_argument("--surface", choices=[surface.value for surface in Surface], default="hard")
    simulate_batch.add_argument("--best-of", type=int, default=3, choices=[3, 5])
    simulate_batch.add_argument("--seed", type=int, default=1)
    simulate_batch.add_argument("--iterations", type=int, default=100)
    simulate_batch.add_argument("--initial-server")
    simulate_batch.add_argument("--roster-path")

    calibrate = subparsers.add_parser("calibrate", help="Run deterministic benchmark scenarios")
    calibrate.add_argument("--config")
    calibrate.add_argument("--roster-path")

    inspect_player = subparsers.add_parser("inspect-player", help="Inspect a player profile")
    inspect_player.add_argument("player_id")
    inspect_player.add_argument("--roster-path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect-player":
            player = load_player(args.player_id, args.roster_path)
            print(format_player_profile(player))
            return 0

        roster = load_roster(args.roster_path)
        simulator = MatchSimulator(roster)

        if args.command == "calibrate":
            scenarios = load_calibration_scenarios(args.config)
            report = run_calibration_suite(simulator, scenarios, config_path=args.config)
            print(format_calibration_report(report, roster))
            return 0 if report.passed else 3

        config = MatchConfig(
            surface=Surface(args.surface),
            best_of_sets=args.best_of,
            initial_server=args.initial_server,
            seed=args.seed,
        )

        if args.command == "simulate-match":
            result = simulator.simulate_match(args.player_one, args.player_two, config)
            print(format_match_report(result, roster, shot_limit=args.shots))
            return 0

        if args.command == "simulate-batch":
            summary = simulator.simulate_batch(
                args.player_one,
                args.player_two,
                config,
                iterations=args.iterations,
            )
            print(format_batch_report(summary, roster))
            return 0

    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1
