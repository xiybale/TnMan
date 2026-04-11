from __future__ import annotations

from .analysis import MatchPatternSummary, build_match_pattern_summary
from .calibration import CalibrationReport
from .models import BatchSummary, MatchResult, PlayerProfile, ShotEvent


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _short_name(full_name: str) -> str:
    parts = full_name.split()
    if len(parts) == 1:
        return full_name
    return f"{parts[0][0]}. {parts[-1]}"


def format_player_profile(player: PlayerProfile) -> str:
    lines = [
        f"{player.name} ({player.country})",
        f"Tour: {player.tour} | Handedness: {player.handedness.value} | Backhand hands: {player.backhand_hands}",
        "",
        "Skills",
        (
            f"Serve power {player.skills.serve_power}, serve accuracy {player.skills.serve_accuracy}, "
            f"second serve {player.skills.second_serve_reliability}, return {player.skills.return_quality}"
        ),
        (
            f"Forehand {player.skills.forehand_quality}, backhand {player.skills.backhand_quality}, "
            f"movement {player.skills.movement}, anticipation {player.skills.anticipation}"
        ),
        (
            f"Rally tolerance {player.skills.rally_tolerance}, net play {player.skills.net_play}, "
            f"composure {player.skills.composure}, pressure handling {player.skills.pressure_handling}, "
            f"stamina {player.skills.stamina}"
        ),
        "",
        "Tactics",
        (
            f"Aggression {player.tactics.baseline_aggression}, short-ball attack {player.tactics.short_ball_attack}, "
            f"net frequency {player.tactics.net_frequency}, preferred serve {player.tactics.preferred_serve_direction.value}"
        ),
        "",
        "Spin Profile",
        (
            f"Serve spin {player.spin.serve_spin}, forehand spin {player.spin.forehand_spin}, "
            f"backhand spin {player.spin.backhand_spin}, slice usage {player.spin.slice_frequency}"
        ),
        "",
        "Surface Comfort",
        (
            f"Hard {player.surface_profile.hard}, clay {player.surface_profile.clay}, "
            f"grass {player.surface_profile.grass}"
        ),
    ]

    if player.derived_stats.source_notes:
        lines.extend(["", "Notes", *player.derived_stats.source_notes])

    return "\n".join(lines)


def format_match_report(
    result: MatchResult,
    roster: dict[str, PlayerProfile],
    shot_limit: int = 25,
) -> str:
    player_one = roster[result.players[0]]
    player_two = roster[result.players[1]]
    winner = roster[result.winner_id]

    lines = [
        "Tennis Pro Manager Match Report",
        (
            f"Winner: {winner.name} | Score: {player_one.name} vs {player_two.name} "
            f"| {result.scoreline}"
        ),
        f"Surface: {result.surface.value} | Best of: {result.best_of_sets} | Seed: {result.seed}",
        f"Average rally length: {result.average_rally_length:.2f} shots",
        "",
        "Key Stats",
    ]

    for player in (player_one, player_two):
        stats = result.stats[player.player_id]
        lines.append(
            (
                f"{_short_name(player.name)}: aces {stats.aces}, service winners {stats.service_winners}, "
                f"double faults {stats.double_faults}, 1st serve in {_pct(stats.first_serve_percentage())}, "
                f"hold {_pct(stats.hold_percentage())}, winners {stats.total_winners()}, UFE {stats.unforced_errors}"
            )
        )

    pattern_summary = build_match_pattern_summary(result, roster)
    lines.extend(["", "Pattern Summary"])
    lines.append(_format_rally_bands(pattern_summary))
    for player in (player_one, player_two):
        lines.extend(_format_player_pattern_summary(player.player_id, player.name, pattern_summary))

    if shot_limit > 0 and result.shot_log:
        lines.extend(["", "Shot Log Preview"])
        for event in result.shot_log[:shot_limit]:
            lines.append(_format_shot_event(event, roster))

    return "\n".join(lines)


def format_batch_report(summary: BatchSummary, roster: dict[str, PlayerProfile]) -> str:
    player_one = roster[summary.players[0]]
    player_two = roster[summary.players[1]]

    lines = [
        "Tennis Pro Manager Batch Report",
        f"Players: {player_one.name} vs {player_two.name}",
        f"Surface: {summary.surface.value} | Iterations: {summary.iterations}",
        "",
        "Win Rates",
        f"{_short_name(player_one.name)}: {_pct(summary.win_rate(player_one.player_id))}",
        f"{_short_name(player_two.name)}: {_pct(summary.win_rate(player_two.player_id))}",
        "",
        "Aggregate Metrics",
        f"Average rally length: {summary.average_rally_length:.2f} shots",
        f"Average points per match: {summary.average_points_per_match:.1f}",
        "Rally bands: "
        + ", ".join(
            f"{label} {_pct(rate)}"
            for label, rate in summary.rally_band_distribution.items()
        ),
    ]

    for player in (player_one, player_two):
        lines.append(
            (
                f"{_short_name(player.name)}: hold {_pct(summary.hold_rate[player.player_id])}, "
                f"break {_pct(summary.break_rate[player.player_id])}, "
                f"ace rate {_pct(summary.ace_rate[player.player_id])}, "
                f"1st serve in {_pct(summary.first_serve_in_rate[player.player_id])}, "
                f"svc pts won {_pct(summary.service_points_won_rate[player.player_id])}, "
                f"ret pts won {_pct(summary.return_points_won_rate[player.player_id])}, "
                f"double fault {_pct(summary.double_fault_rate[player.player_id])}, "
                f"df on 2nd serve {_pct(summary.second_serve_double_fault_rate[player.player_id])}, "
                f"winner/UFE {summary.winner_to_error_ratio[player.player_id]:.2f}"
            )
        )

    if summary.common_scorelines:
        lines.extend(["", "Most Common Scorelines"])
        for scoreline, count in summary.common_scorelines.items():
            lines.append(f"{scoreline}: {count}")

    return "\n".join(lines)


def _format_shot_event(event: ShotEvent, roster: dict[str, PlayerProfile]) -> str:
    striker = _short_name(roster[event.striker_id].name)
    receiver = _short_name(roster[event.receiver_id].name)
    serve_bits = []
    if event.serve_number is not None:
        serve_bits.append(f"serve {event.serve_number}")
    if event.serve_direction is not None:
        serve_bits.append(event.serve_direction.value)
    serve_bits.append(event.spin_type.value)
    serve_label = f" ({', '.join(serve_bits)})" if serve_bits else ""
    return (
        f"P{event.point_number:03d} S{event.shot_number:02d} [{event.score_before}] "
        f"{striker} -> {receiver}: {event.shot_kind.value}/{event.shot_hand.value}"
        f"{serve_label} | {event.quality.value} | {event.outcome.value}"
    )


def format_calibration_report(report: CalibrationReport, roster: dict[str, PlayerProfile]) -> str:
    lines = [
        "Tennis Pro Manager Calibration Report",
        f"Scenarios: {len(report.scenarios)} | Passed: {report.passed_count}/{len(report.scenarios)}",
    ]

    for scenario_result in report.scenarios:
        scenario = scenario_result.scenario
        player_one = roster[scenario.player_one]
        player_two = roster[scenario.player_two]
        lines.extend(
            [
                "",
                (
                    f"[{'PASS' if scenario_result.passed else 'FAIL'}] {scenario.scenario_id}: "
                    f"{scenario.description}"
                ),
                (
                    f"{player_one.name} vs {player_two.name} | surface {scenario.surface.value} | "
                    f"iterations {scenario.iterations} | seed {scenario.seed}"
                ),
            ]
        )
        for metric_name, target in scenario.targets.items():
            actual = scenario_result.metrics[metric_name]
            lines.append(
                (
                    f"{metric_name}: { _format_metric(metric_name, actual) } "
                    f"(target { _format_metric(metric_name, target.minimum) }"
                    f" to { _format_metric(metric_name, target.maximum) })"
                )
            )

    return "\n".join(lines)


def _format_rally_bands(pattern_summary: MatchPatternSummary) -> str:
    total = sum(pattern_summary.rally_bands.values())
    if total == 0:
        return "Rally bands: no rallies recorded"
    return "Rally bands: " + ", ".join(
        f"{label} {_pct(count / total)}" for label, count in pattern_summary.rally_bands.items()
    )


def _format_player_pattern_summary(
    player_id: str,
    full_name: str,
    pattern_summary: MatchPatternSummary,
) -> list[str]:
    summary = pattern_summary.players[player_id]
    return [
        (
            f"{_short_name(full_name)} serve mix: "
            f"{_format_counter(summary.serve_directions)} | spin { _format_counter(summary.serve_spins) }"
        ),
        (
            f"{_short_name(full_name)} targeting: { _format_counter(summary.targeted_wings) } | "
            f"rally spin { _format_counter(summary.shot_spins) }"
        ),
        (
            f"{_short_name(full_name)} winners by hand { _format_count_counter(summary.winners_by_hand) } | "
            f"forced drawn { _format_count_counter(summary.forced_errors_drawn_by_hand) } | "
            f"UFE { _format_count_counter(summary.unforced_errors_by_hand) }"
        ),
    ]


def _format_counter(counter: dict[str, int]) -> str:
    total = sum(counter.values())
    if total == 0:
        return "n/a"
    ordered = [(label, count) for label, count in counter.items() if count > 0]
    if not ordered:
        return "n/a"
    return ", ".join(f"{label} {_pct(count / total)}" for label, count in ordered)


def _format_count_counter(counter: dict[str, int]) -> str:
    ordered = [(label, count) for label, count in counter.items() if count > 0]
    if not ordered:
        return "n/a"
    return ", ".join(f"{label} {count}" for label, count in ordered)


def _format_metric(metric_name: str, value: float) -> str:
    if "rate" in metric_name or metric_name.startswith("rally_band_"):
        return _pct(value)
    return f"{value:.2f}"
