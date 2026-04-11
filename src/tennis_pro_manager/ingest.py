from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping

from .models import (
    DerivedStats,
    Handedness,
    PhysicalProfile,
    PlayerProfile,
    ServeDirection,
    SkillRatings,
    SpinProfile,
    SurfaceProfile,
    TacticalProfile,
)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _percent(value: Any, default: float | None = None) -> float | None:
    if value in (None, "", "NA"):
        return default
    numeric = float(value)
    if numeric > 1.0:
        numeric /= 100.0
    return numeric


def _scale(value: float, lower: float, upper: float) -> int:
    if upper <= lower:
        return 50
    clipped = _clamp((value - lower) / (upper - lower), 0.0, 1.0)
    return int(round(clipped * 100))


def load_stat_rows(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path)
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def build_profile_from_atp_row(
    row: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
) -> PlayerProfile:
    first_serve_in = _percent(row.get("first_serve_in"), 0.62) or 0.62
    first_serve_points_won = _percent(row.get("first_serve_points_won"), 0.72) or 0.72
    second_serve_points_won = _percent(row.get("second_serve_points_won"), 0.53) or 0.53
    ace_rate = _percent(row.get("ace_rate"), 0.08) or 0.08
    double_fault_rate = _percent(row.get("double_fault_rate"), 0.03) or 0.03
    return_points_won = _percent(row.get("return_points_won"), 0.37) or 0.37
    break_rate = _percent(row.get("break_rate"), 0.22) or 0.22
    hold_rate = _percent(row.get("hold_rate"), 0.82) or 0.82
    hard_win_rate = _percent(row.get("hard_win_rate"), 0.60) or 0.60
    clay_win_rate = _percent(row.get("clay_win_rate"), 0.55) or 0.55
    grass_win_rate = _percent(row.get("grass_win_rate"), 0.57) or 0.57

    serve_power = int(
        row.get("serve_power", _scale(ace_rate * 0.55 + first_serve_points_won * 0.45, 0.30, 0.46))
    )
    serve_accuracy = int(row.get("serve_accuracy", _scale(first_serve_in, 0.50, 0.72)))
    second_serve_reliability = int(
        row.get(
            "second_serve_reliability",
            _scale(
            second_serve_points_won * 0.75 + (1.0 - double_fault_rate) * 0.25, 0.45, 0.70
            ),
        )
    )
    return_quality = int(
        row.get("return_quality", _scale(return_points_won * 0.75 + break_rate * 0.25, 0.28, 0.40))
    )
    forehand_quality = int(
        row.get("forehand_quality", _scale(hold_rate * 0.50 + first_serve_points_won * 0.50, 0.58, 0.84))
    )
    backhand_quality = int(
        row.get(
            "backhand_quality",
            _scale(return_points_won * 0.55 + second_serve_points_won * 0.45, 0.34, 0.52),
        )
    )
    movement = int(row.get("movement", _scale((return_points_won + clay_win_rate) / 2, 0.33, 0.66)))
    anticipation = int(
        row.get("anticipation", _scale((return_points_won + break_rate) / 2, 0.22, 0.38))
    )
    rally_tolerance = int(
        row.get("rally_tolerance", _scale((clay_win_rate + second_serve_points_won) / 2, 0.40, 0.66))
    )
    net_play = int(row.get("net_play", _scale((grass_win_rate + first_serve_points_won) / 2, 0.50, 0.82)))
    composure = int(
        row.get("composure", _scale((hold_rate + break_rate + second_serve_points_won) / 3, 0.44, 0.67))
    )
    pressure_handling = int(
        row.get(
            "pressure_handling",
            _scale(
                (hold_rate + break_rate + second_serve_points_won + first_serve_points_won) / 4,
                0.46,
                0.70,
            ),
        )
    )
    stamina = int(
        row.get("stamina", _scale((clay_win_rate + return_points_won + second_serve_points_won) / 3, 0.40, 0.63))
    )
    backhand_hands = int(row.get("backhand_hands", 2))
    serve_spin = int(row.get("serve_spin", _scale((second_serve_points_won + clay_win_rate) / 2, 0.45, 0.72)))
    forehand_spin = int(
        row.get("forehand_spin", _scale((clay_win_rate + rally_tolerance / 100) / 2, 0.40, 0.85))
    )
    backhand_spin = int(
        row.get("backhand_spin", _scale((return_points_won + second_serve_points_won) / 2, 0.35, 0.75))
    )
    slice_frequency = int(row.get("slice_frequency", _scale(grass_win_rate, 0.35, 0.80)))
    if backhand_hands == 1:
        backhand_spin = min(100, backhand_spin + 8)
        slice_frequency = min(100, slice_frequency + 18)

    baseline_aggression = int(row.get("baseline_aggression", _scale(first_serve_points_won, 0.58, 0.84)))
    short_ball_attack = int(row.get("short_ball_attack", _scale(first_serve_points_won + ace_rate, 0.60, 0.90)))
    net_frequency = int(row.get("net_frequency", _scale(grass_win_rate, 0.45, 0.80)))

    profile = PlayerProfile(
        player_id=str(row.get("player_id") or row.get("name", "").lower().replace(" ", "-")),
        name=str(row.get("name")),
        country=str(row.get("country", "UNK")),
        tour="ATP",
        handedness=Handedness(str(row.get("handedness", "right")).lower()),
        backhand_hands=backhand_hands,
        skills=SkillRatings(
            serve_power=serve_power,
            serve_accuracy=serve_accuracy,
            second_serve_reliability=second_serve_reliability,
            return_quality=return_quality,
            forehand_quality=forehand_quality,
            backhand_quality=backhand_quality,
            movement=movement,
            anticipation=anticipation,
            rally_tolerance=rally_tolerance,
            net_play=net_play,
            composure=composure,
            pressure_handling=int(row.get("pressure_handling", pressure_handling)),
            stamina=stamina,
        ),
        tactics=TacticalProfile(
            baseline_aggression=baseline_aggression,
            preferred_serve_direction=ServeDirection(str(row.get("preferred_serve_direction", "wide"))),
            short_ball_attack=short_ball_attack,
            net_frequency=net_frequency,
        ),
        spin=SpinProfile(
            serve_spin=int(row.get("serve_spin", serve_spin)),
            forehand_spin=int(row.get("forehand_spin", forehand_spin)),
            backhand_spin=int(row.get("backhand_spin", backhand_spin)),
            slice_frequency=int(row.get("slice_frequency", slice_frequency)),
        ),
        physical=PhysicalProfile(
            durability=_scale(hold_rate + return_points_won, 0.90, 1.30),
            recovery=_scale(second_serve_points_won + return_points_won, 0.80, 1.20),
            peak_condition=_scale(first_serve_in + hold_rate, 1.10, 1.55),
        ),
        surface_profile=SurfaceProfile(
            hard=_scale(hard_win_rate, 0.40, 0.85),
            clay=_scale(clay_win_rate, 0.35, 0.85),
            grass=_scale(grass_win_rate, 0.35, 0.85),
        ),
        derived_stats=DerivedStats(
            first_serve_in=first_serve_in,
            first_serve_points_won=first_serve_points_won,
            second_serve_points_won=second_serve_points_won,
            ace_rate=ace_rate,
            double_fault_rate=double_fault_rate,
            return_points_won=return_points_won,
            break_rate=break_rate,
            hold_rate=hold_rate,
            hard_win_rate=hard_win_rate,
            clay_win_rate=clay_win_rate,
            grass_win_rate=grass_win_rate,
            source_notes=["Generated from structured ATP-style row input."],
        ),
    )

    if overrides:
        payload = profile.to_dict()
        _deep_update(payload, overrides)
        return PlayerProfile.from_dict(payload)

    return profile


def build_profiles_from_csv(
    csv_path: str | Path,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[PlayerProfile]:
    profiles = []
    for row in load_stat_rows(csv_path):
        player_overrides = None
        if overrides is not None:
            player_overrides = overrides.get(str(row.get("player_id") or row.get("name")))
        profiles.append(build_profile_from_atp_row(row, player_overrides))
    return profiles


def export_profiles(profiles: list[PlayerProfile], output_path: str | Path) -> None:
    path = Path(output_path)
    path.write_text(json.dumps([profile.to_dict() for profile in profiles], indent=2))


def _deep_update(payload: dict[str, Any], updates: Mapping[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(payload.get(key), dict):
            _deep_update(payload[key], value)
        else:
            payload[key] = value
