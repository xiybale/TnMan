from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .analysis import build_match_pattern_summary
from .models import BatchSummary, MatchResult, PlayerMatchStats, PlayerProfile, PointRecord, Surface

SKILL_LABELS = {
    "serve_power": "Serve power",
    "serve_accuracy": "Serve accuracy",
    "second_serve_reliability": "Second serve reliability",
    "return_quality": "Return quality",
    "forehand_quality": "Forehand quality",
    "backhand_quality": "Backhand quality",
    "movement": "Movement",
    "anticipation": "Anticipation",
    "rally_tolerance": "Rally tolerance",
    "net_play": "Net play",
    "composure": "Composure",
    "pressure_handling": "Pressure handling",
    "stamina": "Stamina",
}


def build_health_payload(roster: dict[str, PlayerProfile]) -> dict[str, Any]:
    return {
        "status": "ok",
        "players": len(roster),
    }


def build_player_directory_payload(
    roster: dict[str, PlayerProfile],
    *,
    query: str | None = None,
    surface: Surface | None = None,
) -> dict[str, Any]:
    players = list(roster.values())
    if query:
        needle = query.strip().lower()
        players = [
            player
            for player in players
            if needle in player.player_id.lower()
            or needle in player.name.lower()
            or needle in player.country.lower()
        ]

    summaries = [
        (build_player_summary_payload(player), player.surface_profile.comfort(surface) if surface else 0)
        for player in players
    ]
    summaries.sort(
        key=lambda item: (
            -item[0]["overallRating"],
            -item[1],
            item[0]["name"],
        )
    )
    return {"players": [summary for summary, _surface_comfort in summaries]}


def build_player_summary_payload(player: PlayerProfile) -> dict[str, Any]:
    top_skills = [
        {"label": label, "value": value}
        for label, value in _top_skill_pairs(player.skills, count=3)
    ]
    return _jsonable(
        {
            "player_id": player.player_id,
            "name": player.name,
            "country": player.country,
            "tour": player.tour,
            "handedness": player.handedness,
            "backhand_hands": player.backhand_hands,
            "overall_rating": round(_overall_rating(player), 1),
            "surface_comfort": {
                "hard": player.surface_profile.hard,
                "clay": player.surface_profile.clay,
                "grass": player.surface_profile.grass,
            },
            "tags": _profile_tags(player),
            "top_skills": top_skills,
        }
    )


def build_player_payload(player: PlayerProfile) -> dict[str, Any]:
    strengths = [
        {"label": label, "value": value}
        for label, value in _top_skill_pairs(player.skills, count=4)
    ]
    weaknesses = [
        {"label": label, "value": value}
        for label, value in _bottom_skill_pairs(player.skills, count=3)
    ]
    payload = {
        "summary": build_player_summary_payload(player),
        "skills": asdict(player.skills),
        "tactics": {
            "baseline_aggression": player.tactics.baseline_aggression,
            "preferred_serve_direction": player.tactics.preferred_serve_direction,
            "short_ball_attack": player.tactics.short_ball_attack,
            "net_frequency": player.tactics.net_frequency,
        },
        "spin": asdict(player.spin),
        "physical": asdict(player.physical),
        "surface_profile": asdict(player.surface_profile),
        "derived_stats": asdict(player.derived_stats),
        "strengths": strengths,
        "weaknesses": weaknesses,
    }
    return _jsonable(payload)


def build_compare_payload(
    player_one: PlayerProfile,
    player_two: PlayerProfile,
    *,
    surface: Surface,
) -> dict[str, Any]:
    skill_deltas = []
    for field_name, label in SKILL_LABELS.items():
        player_one_value = getattr(player_one.skills, field_name)
        player_two_value = getattr(player_two.skills, field_name)
        if player_one_value == player_two_value:
            edge_for = None
        else:
            edge_for = player_one.player_id if player_one_value > player_two_value else player_two.player_id
        skill_deltas.append(
            {
                "skill": field_name,
                "label": label,
                "player_one": player_one_value,
                "player_two": player_two_value,
                "delta": player_one_value - player_two_value,
                "edge_for": edge_for,
            }
        )

    matchup_tags = []
    if player_one.handedness != player_two.handedness:
        matchup_tags.append("opposite-handed baseline geometry")
    if player_one.backhand_hands == 1 or player_two.backhand_hands == 1:
        matchup_tags.append("one-handed backhand spin target")
    if abs(player_one.surface_profile.comfort(surface) - player_two.surface_profile.comfort(surface)) >= 8:
        matchup_tags.append(f"{surface.value} comfort mismatch")
    if abs(player_one.skills.pressure_handling - player_two.skills.pressure_handling) >= 8:
        matchup_tags.append("pressure handling edge")
    if abs(player_one.skills.serve_power - player_two.skills.serve_power) >= 8:
        matchup_tags.append("serve power separation")

    tactical_themes = _matchup_themes(player_one, player_two, surface)
    payload = {
        "surface": surface,
        "player_one": build_player_payload(player_one),
        "player_two": build_player_payload(player_two),
        "skill_deltas": skill_deltas,
        "surface_edge": {
            "player_one": player_one.surface_profile.comfort(surface),
            "player_two": player_two.surface_profile.comfort(surface),
            "delta": player_one.surface_profile.comfort(surface)
            - player_two.surface_profile.comfort(surface),
        },
        "matchup_tags": matchup_tags,
        "tactical_themes": tactical_themes,
    }
    return _jsonable(payload)


def build_match_report_payload(
    result: MatchResult,
    roster: dict[str, PlayerProfile],
) -> dict[str, Any]:
    player_one_id, player_two_id = result.players
    player_lookup = {player_id: build_player_summary_payload(roster[player_id]) for player_id in result.players}
    pattern_summary = build_match_pattern_summary(result, roster)
    set_stats = _build_set_stats(result)
    set_points: dict[int, list[PointRecord]] = defaultdict(list)
    for point in result.points:
        set_points[point.set_number].append(point)

    sets_payload = []
    global_game_number = 1
    for set_number, completed_set in enumerate(result.set_scores, start=1):
        points = set_points.get(set_number, [])
        games_payload = []
        for game in _group_games(points):
            game["game_number"] = global_game_number
            games_payload.append(_jsonable(game))
            global_game_number += 1

        set_winner_id = (
            player_one_id
            if completed_set.games[player_one_id] > completed_set.games[player_two_id]
            else player_two_id
        )
        sets_payload.append(
            _jsonable(
                {
                    "set_number": set_number,
                    "score": completed_set.score_for(player_one_id, player_two_id),
                    "winner_id": set_winner_id,
                    "games": dict(completed_set.games),
                    "tiebreak_points": completed_set.tiebreak_points,
                    "stats": {
                        player_id: _serialize_match_stats(set_stats[set_number][player_id])
                        for player_id in result.players
                    },
                    "games_timeline": games_payload,
                }
            )
        )

    payload = {
        "meta": {
            "players": result.players,
            "winner_id": result.winner_id,
            "scoreline": result.scoreline,
            "surface": result.surface,
            "best_of_sets": result.best_of_sets,
            "seed": result.seed,
            "average_rally_length": round(result.average_rally_length, 3),
            "total_points": result.total_points,
        },
        "players": player_lookup,
        "match_stats": {
            player_id: _serialize_match_stats(result.stats[player_id]) for player_id in result.players
        },
        "pattern_summary": pattern_summary,
        "sets": sets_payload,
    }
    return _jsonable(payload)


def build_batch_payload(summary: BatchSummary, roster: dict[str, PlayerProfile]) -> dict[str, Any]:
    payload = {
        "meta": {
            "players": summary.players,
            "iterations": summary.iterations,
            "surface": summary.surface,
            "average_rally_length": round(summary.average_rally_length, 3),
            "average_points_per_match": round(summary.average_points_per_match, 3),
        },
        "players": {
            player_id: build_player_summary_payload(roster[player_id]) for player_id in summary.players
        },
        "wins": dict(summary.wins),
        "win_rates": {player_id: summary.win_rate(player_id) for player_id in summary.players},
        "hold_rate": dict(summary.hold_rate),
        "break_rate": dict(summary.break_rate),
        "ace_rate": dict(summary.ace_rate),
        "first_serve_in_rate": dict(summary.first_serve_in_rate),
        "double_fault_rate": dict(summary.double_fault_rate),
        "second_serve_double_fault_rate": dict(summary.second_serve_double_fault_rate),
        "service_points_won_rate": dict(summary.service_points_won_rate),
        "return_points_won_rate": dict(summary.return_points_won_rate),
        "winner_to_error_ratio": dict(summary.winner_to_error_ratio),
        "common_scorelines": dict(summary.common_scorelines),
        "rally_band_distribution": dict(summary.rally_band_distribution),
    }
    return _jsonable(payload)


def _group_games(points: list[PointRecord]) -> list[dict[str, Any]]:
    games = []
    current_group: list[PointRecord] = []
    current_number: int | None = None
    for point in points:
        if current_number is None or point.game_number_in_set != current_number:
            if current_group:
                games.append(_build_game_payload(current_group))
            current_group = [point]
            current_number = point.game_number_in_set
        else:
            current_group.append(point)

    if current_group:
        games.append(_build_game_payload(current_group))
    return games


def _build_game_payload(points: list[PointRecord]) -> dict[str, Any]:
    first = points[0]
    last = points[-1]
    return {
        "set_number": first.set_number,
        "game_number_in_set": first.game_number_in_set,
        "score_before": _format_games(first.games_before),
        "score_after": _format_games(last.games_after),
        "server_id": first.server_id,
        "winner_id": last.game_winner_id or last.winner_id,
        "is_tiebreak": first.is_tiebreak,
        "holds_serve": (last.game_winner_id or last.winner_id) == first.server_id,
        "point_count": len(points),
        "points": [_serialize_point(point) for point in points],
    }


def _serialize_point(point: PointRecord) -> dict[str, Any]:
    return _jsonable(
        {
            "point_number": point.point_number,
            "set_number": point.set_number,
            "game_number_in_set": point.game_number_in_set,
            "server_id": point.server_id,
            "receiver_id": point.receiver_id,
            "winner_id": point.winner_id,
            "score_before": point.score_before,
            "score_after": point.score_after,
            "point_score_before": point.point_score_before,
            "point_score_after": point.point_score_after,
            "sets_before": dict(point.sets_before),
            "sets_after": dict(point.sets_after),
            "games_before": dict(point.games_before),
            "games_after": dict(point.games_after),
            "is_tiebreak": point.is_tiebreak,
            "break_point_for": point.break_point_for,
            "set_point_for": point.set_point_for,
            "match_point_for": point.match_point_for,
            "pressure_index": point.pressure_index,
            "pressure_label": point.pressure_label,
            "rally_length": point.rally_length,
            "terminal_outcome": point.terminal_outcome,
            "terminal_shot_kind": point.terminal_shot_kind,
            "terminal_striker_id": point.terminal_striker_id,
            "shot_count": len(point.events),
            "game_completed": point.game_completed,
            "set_completed": point.set_completed,
            "match_completed": point.match_completed,
            "shots": point.events,
        }
    )


def _build_set_stats(result: MatchResult) -> dict[int, dict[str, PlayerMatchStats]]:
    stats: dict[int, dict[str, PlayerMatchStats]] = {}
    for set_number, _completed_set in enumerate(result.set_scores, start=1):
        stats[set_number] = {player_id: PlayerMatchStats() for player_id in result.players}

    for point in result.points:
        set_bucket = stats.setdefault(
            point.set_number,
            {player_id: PlayerMatchStats() for player_id in result.players},
        )
        _apply_point_to_stats(set_bucket, point)
    return stats


def _apply_point_to_stats(stats: dict[str, PlayerMatchStats], point: PointRecord) -> None:
    server = stats[point.server_id]
    receiver = stats[point.receiver_id]
    winner = stats[point.winner_id]

    server.points_played += 1
    receiver.points_played += 1
    server.service_points_played += 1
    receiver.return_points_played += 1
    winner.total_points_won += 1

    if point.winner_id == point.server_id:
        server.service_points_won += 1
    else:
        receiver.return_points_won += 1

    if point.break_point_for == point.receiver_id:
        receiver.break_points_created += 1
        server.break_points_faced += 1
        if point.winner_id == point.receiver_id:
            receiver.break_points_converted += 1
        else:
            server.break_points_saved += 1

    for event in point.events:
        stats[event.striker_id].total_shots += 1
        if event.shot_kind.value != "serve":
            continue
        if event.serve_number == 1:
            server.first_serve_attempts += 1
            if event.outcome.value != "fault":
                server.first_serves_in += 1
        elif event.serve_number == 2:
            server.second_serve_attempts += 1
            if event.outcome.value != "double_fault":
                server.second_serves_in += 1

    if point.terminal_outcome.value == "double_fault":
        server.double_faults += 1
    elif point.terminal_outcome.value == "ace":
        server.aces += 1
    elif point.terminal_outcome.value == "service_winner":
        server.service_winners += 1
    elif point.terminal_outcome.value == "return_winner":
        receiver.return_winners += 1
    elif point.terminal_outcome.value == "winner":
        stats[point.terminal_striker_id].winners += 1
    elif point.terminal_outcome.value == "forced_error":
        winner.forced_errors_drawn += 1
    elif point.terminal_outcome.value == "unforced_error":
        stats[point.terminal_striker_id].unforced_errors += 1

    if point.game_completed:
        server.games_served += 1
        if point.game_winner_id == point.server_id:
            server.service_games_won += 1


def _serialize_match_stats(stats: PlayerMatchStats) -> dict[str, Any]:
    return _jsonable(
        {
            "points_played": stats.points_played,
            "total_points_won": stats.total_points_won,
            "service_points_played": stats.service_points_played,
            "service_points_won": stats.service_points_won,
            "return_points_played": stats.return_points_played,
            "return_points_won": stats.return_points_won,
            "aces": stats.aces,
            "service_winners": stats.service_winners,
            "double_faults": stats.double_faults,
            "winners": stats.winners,
            "return_winners": stats.return_winners,
            "forced_errors_drawn": stats.forced_errors_drawn,
            "unforced_errors": stats.unforced_errors,
            "break_points_created": stats.break_points_created,
            "break_points_converted": stats.break_points_converted,
            "break_points_faced": stats.break_points_faced,
            "break_points_saved": stats.break_points_saved,
            "games_served": stats.games_served,
            "service_games_won": stats.service_games_won,
            "total_shots": stats.total_shots,
            "first_serve_attempts": stats.first_serve_attempts,
            "first_serves_in": stats.first_serves_in,
            "second_serve_attempts": stats.second_serve_attempts,
            "second_serves_in": stats.second_serves_in,
            "total_winners": stats.total_winners(),
            "first_serve_percentage": stats.first_serve_percentage(),
            "service_points_won_percentage": stats.service_points_won_percentage(),
            "return_points_won_percentage": stats.return_points_won_percentage(),
            "hold_percentage": stats.hold_percentage(),
            "ace_rate": stats.ace_rate(),
            "double_fault_rate": stats.double_fault_rate(),
            "second_serve_double_fault_rate": stats.second_serve_double_fault_rate(),
            "winner_to_error_ratio": stats.winner_to_error_ratio(),
        }
    )


def _top_skill_pairs(skills: Any, *, count: int) -> list[tuple[str, int]]:
    items = [(label, getattr(skills, field_name)) for field_name, label in SKILL_LABELS.items()]
    items.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return items[:count]


def _bottom_skill_pairs(skills: Any, *, count: int) -> list[tuple[str, int]]:
    items = [(label, getattr(skills, field_name)) for field_name, label in SKILL_LABELS.items()]
    items.sort(key=lambda item: (item[1], item[0]))
    return items[:count]


def _overall_rating(player: PlayerProfile) -> float:
    ratings = [getattr(player.skills, field_name) for field_name in SKILL_LABELS]
    return sum(ratings) / len(ratings)


def _profile_tags(player: PlayerProfile) -> list[str]:
    tags = [
        "left-handed" if player.handedness.value == "left" else "right-handed",
        "one-handed backhand" if player.backhand_hands == 1 else "two-handed backhand",
    ]
    if player.skills.serve_power >= 85:
        tags.append("elite serve pop")
    if player.skills.return_quality >= 85:
        tags.append("elite return")
    if player.skills.pressure_handling >= 85:
        tags.append("pressure resistant")
    if max(player.surface_profile.hard, player.surface_profile.clay, player.surface_profile.grass) >= 88:
        best_surface = max(
            ("hard", player.surface_profile.hard),
            ("clay", player.surface_profile.clay),
            ("grass", player.surface_profile.grass),
            key=lambda item: item[1],
        )[0]
        tags.append(f"{best_surface} specialist")
    if max(player.spin.forehand_spin, player.spin.backhand_spin) >= 85:
        tags.append("heavy topspin")
    return tags


def _matchup_themes(
    player_one: PlayerProfile,
    player_two: PlayerProfile,
    surface: Surface,
) -> list[dict[str, Any]]:
    themes: list[dict[str, Any]] = []
    if player_one.skills.serve_power - player_two.skills.serve_power >= 8:
        themes.append({"edge_for": player_one.player_id, "label": "clear serve power edge"})
    elif player_two.skills.serve_power - player_one.skills.serve_power >= 8:
        themes.append({"edge_for": player_two.player_id, "label": "clear serve power edge"})

    if player_one.skills.return_quality - player_two.skills.return_quality >= 8:
        themes.append({"edge_for": player_one.player_id, "label": "return control edge"})
    elif player_two.skills.return_quality - player_one.skills.return_quality >= 8:
        themes.append({"edge_for": player_two.player_id, "label": "return control edge"})

    if player_one.surface_profile.comfort(surface) - player_two.surface_profile.comfort(surface) >= 8:
        themes.append({"edge_for": player_one.player_id, "label": f"{surface.value} comfort edge"})
    elif player_two.surface_profile.comfort(surface) - player_one.surface_profile.comfort(surface) >= 8:
        themes.append({"edge_for": player_two.player_id, "label": f"{surface.value} comfort edge"})

    if player_one.backhand_hands == 1 and player_two.spin.forehand_spin >= 80:
        themes.append(
            {
                "edge_for": player_two.player_id,
                "label": "heavy topspin into one-handed backhand",
            }
        )
    if player_two.backhand_hands == 1 and player_one.spin.forehand_spin >= 80:
        themes.append(
            {
                "edge_for": player_one.player_id,
                "label": "heavy topspin into one-handed backhand",
            }
        )
    return themes


def _format_games(games: dict[str, int]) -> str:
    values = list(games.values())
    if len(values) != 2:
        return ""
    return f"{values[0]}-{values[1]}"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {
            _camel_case(key) if isinstance(key, str) and "_" in key else key: _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])
