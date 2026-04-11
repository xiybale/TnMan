from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import BatchSummary, MatchConfig, Surface
from .simulator import MatchSimulator


@dataclass(slots=True)
class CalibrationTargetRange:
    minimum: float
    maximum: float

    def contains(self, value: float) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(slots=True)
class CalibrationScenario:
    scenario_id: str
    description: str
    player_one: str
    player_two: str
    surface: Surface
    best_of_sets: int
    iterations: int
    seed: int
    targets: dict[str, CalibrationTargetRange]


@dataclass(slots=True)
class CalibrationScenarioResult:
    scenario: CalibrationScenario
    metrics: dict[str, float]
    failures: dict[str, float]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(slots=True)
class CalibrationReport:
    config_path: Path
    scenarios: list[CalibrationScenarioResult]

    @property
    def passed(self) -> bool:
        return all(scenario.passed for scenario in self.scenarios)

    @property
    def passed_count(self) -> int:
        return sum(1 for scenario in self.scenarios if scenario.passed)


def default_calibration_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "calibration" / "benchmark_scenarios.json"


def load_calibration_scenarios(config_path: str | Path | None = None) -> list[CalibrationScenario]:
    path = Path(config_path) if config_path is not None else default_calibration_path()
    payload = json.loads(path.read_text())
    raw_scenarios = payload["scenarios"] if isinstance(payload, dict) else payload
    scenarios: list[CalibrationScenario] = []

    for raw in raw_scenarios:
        scenarios.append(
            CalibrationScenario(
                scenario_id=raw["scenario_id"],
                description=raw["description"],
                player_one=raw["player_one"],
                player_two=raw["player_two"],
                surface=Surface(raw["surface"]),
                best_of_sets=int(raw.get("best_of_sets", 3)),
                iterations=int(raw.get("iterations", 100)),
                seed=int(raw.get("seed", 1)),
                targets={
                    metric: CalibrationTargetRange(
                        minimum=float(target["minimum"]),
                        maximum=float(target["maximum"]),
                    )
                    for metric, target in raw["targets"].items()
                },
            )
        )

    return scenarios


def run_calibration_suite(
    simulator: MatchSimulator,
    scenarios: list[CalibrationScenario],
    config_path: str | Path | None = None,
) -> CalibrationReport:
    results: list[CalibrationScenarioResult] = []
    for scenario in scenarios:
        summary = simulator.simulate_batch(
            scenario.player_one,
            scenario.player_two,
            MatchConfig(
                surface=scenario.surface,
                best_of_sets=scenario.best_of_sets,
                seed=scenario.seed,
            ),
            iterations=scenario.iterations,
        )
        metrics = extract_metrics(summary)
        failures = {
            metric: value
            for metric, value in metrics.items()
            if metric in scenario.targets and not scenario.targets[metric].contains(value)
        }
        results.append(
            CalibrationScenarioResult(
                scenario=scenario,
                metrics=metrics,
                failures=failures,
            )
        )

    return CalibrationReport(
        config_path=Path(config_path) if config_path is not None else default_calibration_path(),
        scenarios=results,
    )


def extract_metrics(summary: BatchSummary) -> dict[str, float]:
    player_one, player_two = summary.players
    return {
        "player_one_win_rate": summary.win_rate(player_one),
        "player_two_win_rate": summary.win_rate(player_two),
        "player_one_hold_rate": summary.hold_rate[player_one],
        "player_two_hold_rate": summary.hold_rate[player_two],
        "player_one_break_rate": summary.break_rate[player_one],
        "player_two_break_rate": summary.break_rate[player_two],
        "player_one_service_points_won_rate": summary.service_points_won_rate[player_one],
        "player_two_service_points_won_rate": summary.service_points_won_rate[player_two],
        "player_one_return_points_won_rate": summary.return_points_won_rate[player_one],
        "player_two_return_points_won_rate": summary.return_points_won_rate[player_two],
        "combined_hold_rate": _average(summary.hold_rate[player_one], summary.hold_rate[player_two]),
        "combined_break_rate": _average(summary.break_rate[player_one], summary.break_rate[player_two]),
        "combined_ace_rate": _average(summary.ace_rate[player_one], summary.ace_rate[player_two]),
        "combined_first_serve_in_rate": _average(
            summary.first_serve_in_rate[player_one],
            summary.first_serve_in_rate[player_two],
        ),
        "combined_double_fault_rate": _average(
            summary.double_fault_rate[player_one],
            summary.double_fault_rate[player_two],
        ),
        "combined_second_serve_double_fault_rate": _average(
            summary.second_serve_double_fault_rate[player_one],
            summary.second_serve_double_fault_rate[player_two],
        ),
        "combined_winner_to_error_ratio": _average(
            summary.winner_to_error_ratio[player_one],
            summary.winner_to_error_ratio[player_two],
        ),
        "average_rally_length": summary.average_rally_length,
        "average_points_per_match": summary.average_points_per_match,
        "rally_band_1_2": summary.rally_band_distribution["1-2"],
        "rally_band_3_6": summary.rally_band_distribution["3-6"],
        "rally_band_7_10": summary.rally_band_distribution["7-10"],
        "rally_band_11_plus": summary.rally_band_distribution["11+"],
    }


def _average(left: float, right: float) -> float:
    return (left + right) / 2
