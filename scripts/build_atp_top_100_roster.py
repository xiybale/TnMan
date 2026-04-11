from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tennis_pro_manager.ingest import build_profile_from_atp_row
from tennis_pro_manager.tennis_abstract import ChartingSnapshot, load_charting_cache

SNAPSHOT_DATE = date(2026, 4, 9)
SNAPSHOT_SOURCE = "https://www.atptour.com/Rankings/Singles"

TOP_100_SNAPSHOT = [
    {"rank": 1, "name": "Carlos Alcaraz"},
    {"rank": 2, "name": "Jannik Sinner"},
    {"rank": 3, "name": "Alexander Zverev"},
    {"rank": 4, "name": "Novak Djokovic"},
    {"rank": 5, "name": "Lorenzo Musetti"},
    {"rank": 6, "name": "Alex de Minaur"},
    {"rank": 7, "name": "Felix Auger-Aliassime"},
    {"rank": 8, "name": "Taylor Fritz"},
    {"rank": 9, "name": "Ben Shelton"},
    {"rank": 10, "name": "Daniil Medvedev"},
    {"rank": 11, "name": "Alexander Bublik"},
    {"rank": 12, "name": "Casper Ruud"},
    {"rank": 13, "name": "Flavio Cobolli"},
    {"rank": 14, "name": "Jiri Lehecka"},
    {"rank": 15, "name": "Karen Khachanov"},
    {"rank": 16, "name": "Andrey Rublev"},
    {"rank": 17, "name": "Alejandro Davidovich Fokina"},
    {"rank": 18, "name": "Frances Tiafoe"},
    {"rank": 19, "name": "Luciano Darderi"},
    {"rank": 20, "name": "Francisco Cerundolo"},
    {"rank": 21, "name": "Tommy Paul"},
    {"rank": 22, "name": "Learner Tien"},
    {"rank": 23, "name": "Valentin Vacherot"},
    {"rank": 24, "name": "Cameron Norrie"},
    {"rank": 25, "name": "Jack Draper"},
    {"rank": 26, "name": "Jakub Mensik"},
    {"rank": 27, "name": "Arthur Rinderknech"},
    {"rank": 28, "name": "Arthur Fils"},
    {"rank": 29, "name": "Holger Rune"},
    {"rank": 30, "name": "Tallon Griekspoor"},
    {"rank": 31, "name": "Tomas Martin Etcheverry"},
    {"rank": 32, "name": "Corentin Moutet"},
    {"rank": 33, "name": "Brandon Nakashima"},
    {"rank": 34, "name": "Ugo Humbert"},
    {"rank": 35, "name": "Alex Michelsen"},
    {"rank": 36, "name": "Gabriel Diallo"},
    {"rank": 37, "name": "Jaume Munar"},
    {"rank": 38, "name": "Denis Shapovalov"},
    {"rank": 39, "name": "Alejandro Tabilo"},
    {"rank": 40, "name": "Joao Fonseca"},
    {"rank": 41, "name": "Jenson Brooksby"},
    {"rank": 42, "name": "Sebastian Korda"},
    {"rank": 43, "name": "Adrian Mannarino"},
    {"rank": 44, "name": "Terence Atmane"},
    {"rank": 45, "name": "Alexei Popyrin"},
    {"rank": 46, "name": "Zizou Bergs"},
    {"rank": 47, "name": "Fabian Marozsan"},
    {"rank": 48, "name": "Nuno Borges"},
    {"rank": 49, "name": "Stefanos Tsitsipas"},
    {"rank": 50, "name": "Sebastian Baez"},
    {"rank": 51, "name": "Marton Fucsovics"},
    {"rank": 52, "name": "Daniel Altmaier"},
    {"rank": 53, "name": "Kamil Majchrzak"},
    {"rank": 54, "name": "Marin Cilic"},
    {"rank": 55, "name": "Tomas Machac"},
    {"rank": 56, "name": "Ethan Quinn"},
    {"rank": 57, "name": "Giovanni Mpetshi Perricard"},
    {"rank": 58, "name": "Miomir Kecmanovic"},
    {"rank": 59, "name": "Ignacio Buse"},
    {"rank": 60, "name": "Mariano Navone"},
    {"rank": 61, "name": "Yannick Hanfmann"},
    {"rank": 62, "name": "Botic van de Zandschulp"},
    {"rank": 63, "name": "Lorenzo Sonego"},
    {"rank": 64, "name": "Reilly Opelka"},
    {"rank": 65, "name": "Raphael Collignon"},
    {"rank": 66, "name": "Marcos Giron"},
    {"rank": 67, "name": "Camilo Ugo Carabelli"},
    {"rank": 68, "name": "Arthur Cazaux"},
    {"rank": 69, "name": "Juan Manuel Cerundolo"},
    {"rank": 70, "name": "Vit Kopriva"},
    {"rank": 71, "name": "Valentin Royer"},
    {"rank": 72, "name": "Hubert Hurkacz"},
    {"rank": 73, "name": "Mattia Bellucci"},
    {"rank": 74, "name": "Damir Dzumhur"},
    {"rank": 75, "name": "Jan-Lennard Struff"},
    {"rank": 76, "name": "Alexander Shevchenko"},
    {"rank": 77, "name": "Roman Andres Burruchaga"},
    {"rank": 78, "name": "Sebastian Ofner"},
    {"rank": 79, "name": "Eliot Spizzirri"},
    {"rank": 80, "name": "Roberto Bautista Agut"},
    {"rank": 81, "name": "Hamad Medjedovic"},
    {"rank": 82, "name": "Zachary Svajda"},
    {"rank": 83, "name": "Thiago Agustin Tirante"},
    {"rank": 84, "name": "Aleksandar Vukic"},
    {"rank": 85, "name": "Aleksandar Kovacevic"},
    {"rank": 86, "name": "Filip Misolic"},
    {"rank": 87, "name": "Francisco Comesana"},
    {"rank": 88, "name": "Pablo Carreno Busta"},
    {"rank": 89, "name": "Rafael Jodar"},
    {"rank": 90, "name": "Quentin Halys"},
    {"rank": 91, "name": "Matteo Berrettini"},
    {"rank": 92, "name": "Alexander Blockx"},
    {"rank": 93, "name": "Grigor Dimitrov"},
    {"rank": 94, "name": "Alexandre Muller"},
    {"rank": 95, "name": "James Duckworth"},
    {"rank": 96, "name": "Patrick Kypson"},
    {"rank": 97, "name": "Jacob Fearnley"},
    {"rank": 98, "name": "Stan Wawrinka"},
    {"rank": 99, "name": "Jesper de Jong"},
    {"rank": 100, "name": "Cristian Garin"},
]

ONE_HANDED_BACKHANDS = {
    "daniel altmaier",
    "denis shapovalov",
    "filip misolic",
    "grigor dimitrov",
    "lorenzo musetti",
    "sebastian ofner",
    "stan wawrinka",
    "stefanos tsitsipas",
}

HAND_OVERRIDES = {
    "rafael jodar": "right",
}

CLAY_LEANING_COUNTRIES = {"ARG", "BRA", "CHI", "ESP", "ITA", "PER", "POR", "URU"}
HARD_LEANING_COUNTRIES = {"AUS", "CAN", "GBR", "USA"}
GRASS_LEANING_COUNTRIES = {"AUS", "GBR", "USA"}

TOP_100_NORMALIZATION_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    ("skills", "serve_power"): (70, 96),
    ("skills", "serve_accuracy"): (70, 92),
    ("skills", "second_serve_reliability"): (68, 92),
    ("skills", "return_quality"): (68, 92),
    ("skills", "forehand_quality"): (72, 96),
    ("skills", "backhand_quality"): (66, 92),
    ("skills", "movement"): (68, 93),
    ("skills", "anticipation"): (68, 92),
    ("skills", "rally_tolerance"): (66, 93),
    ("skills", "net_play"): (60, 88),
    ("skills", "composure"): (65, 90),
    ("skills", "pressure_handling"): (65, 90),
    ("skills", "stamina"): (68, 92),
    ("tactics", "baseline_aggression"): (58, 90),
    ("tactics", "short_ball_attack"): (55, 90),
    ("tactics", "net_frequency"): (30, 78),
    ("spin", "serve_spin"): (55, 88),
    ("spin", "forehand_spin"): (58, 90),
    ("spin", "backhand_spin"): (55, 88),
    ("spin", "slice_frequency"): (35, 80),
    ("physical", "durability"): (65, 92),
    ("physical", "recovery"): (65, 90),
    ("physical", "peak_condition"): (68, 94),
    ("surface_profile", "hard"): (65, 92),
    ("surface_profile", "clay"): (65, 92),
    ("surface_profile", "grass"): (65, 92),
}

TOP_100_RANK_BIAS_BY_GROUP = {
    "skills": 0.28,
    "physical": 0.20,
    "surface_profile": 0.18,
    "tactics": 0.15,
    "spin": 0.0,
}

AUTO_GENERATED_NOTE_PREFIX = "ATP top-100 snapshot from "
TOP_100_NORMALIZATION_NOTE = "Normalized to a top-100-only in-game rating scale."
TENNIS_ABSTRACT_NOTE = "Blended with current Tennis Abstract Match Charting Project data."
DEFAULT_TENNIS_ABSTRACT_CACHE = (
    PROJECT_ROOT / "data" / "external" / "tennis_abstract_charting.json"
)


@dataclass(slots=True)
class MatchAggregate:
    matches: int = 0
    wins: int = 0
    service_points: int = 0
    first_in: int = 0
    first_won: int = 0
    second_won: int = 0
    aces: int = 0
    double_faults: int = 0
    return_points: int = 0
    return_won: int = 0
    surface_matches: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    surface_wins: dict[str, int] = field(default_factory=lambda: defaultdict(int))


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("-", " ")
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _slugify(value: str) -> str:
    return _normalize_name(value).replace(" ", "-")


def _parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _blend(prior: float, observed: float | None, weight: float) -> float:
    if observed is None:
        return prior
    bounded = _clamp(weight, 0.0, 1.0)
    return prior * (1.0 - bounded) + observed * bounded


def _scale_to_rating(value: float, lower: float, upper: float) -> int:
    if upper <= lower:
        return 50
    clipped = _clamp((value - lower) / (upper - lower), 0.0, 1.0)
    return int(round(clipped * 100))


def _game_win_probability(point_win_probability: float) -> float:
    point_win_probability = _clamp(point_win_probability, 0.001, 0.999)
    point_loss_probability = 1.0 - point_win_probability
    pre_deuce = point_win_probability**4 * (
        1
        + 4 * point_loss_probability
        + 10 * point_loss_probability**2
    )
    deuce_probability = 20 * point_win_probability**3 * point_loss_probability**3
    deuce_win_probability = (point_win_probability**2) / (
        1 - 2 * point_win_probability * point_loss_probability
    )
    return _clamp(pre_deuce + deuce_probability * deuce_win_probability, 0.0, 1.0)


def _build_metadata_index(players_csv_path: Path) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    with players_csv_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            full_name = f"{row['name_first']} {row['name_last']}".strip()
            row["full_name"] = full_name
            index[_normalize_name(full_name)] = row
    return index


def _aggregate_match_stats(matches_csv_path: Path) -> dict[str, MatchAggregate]:
    aggregates: dict[str, MatchAggregate] = defaultdict(MatchAggregate)
    with matches_csv_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            surface = (row.get("surface") or "").strip().lower()
            winner_name = row["winner_name"]
            loser_name = row["loser_name"]

            winner = aggregates[_normalize_name(winner_name)]
            loser = aggregates[_normalize_name(loser_name)]
            winner.matches += 1
            winner.wins += 1
            loser.matches += 1
            if surface in {"hard", "clay", "grass"}:
                winner.surface_matches[surface] += 1
                winner.surface_wins[surface] += 1
                loser.surface_matches[surface] += 1

            _accumulate_stat_line(winner, row, "w", "l")
            _accumulate_stat_line(loser, row, "l", "w")
    return aggregates


def _accumulate_stat_line(
    aggregate: MatchAggregate,
    row: dict[str, str],
    player_prefix: str,
    opponent_prefix: str,
) -> None:
    service_points = _parse_int(row.get(f"{player_prefix}_svpt"))
    first_in = _parse_int(row.get(f"{player_prefix}_1stIn"))
    first_won = _parse_int(row.get(f"{player_prefix}_1stWon"))
    second_won = _parse_int(row.get(f"{player_prefix}_2ndWon"))
    aces = _parse_int(row.get(f"{player_prefix}_ace"))
    double_faults = _parse_int(row.get(f"{player_prefix}_df"))
    opponent_service_points = _parse_int(row.get(f"{opponent_prefix}_svpt"))
    opponent_first_won = _parse_int(row.get(f"{opponent_prefix}_1stWon"))
    opponent_second_won = _parse_int(row.get(f"{opponent_prefix}_2ndWon"))

    if None in (
        service_points,
        first_in,
        first_won,
        second_won,
        aces,
        double_faults,
        opponent_service_points,
        opponent_first_won,
        opponent_second_won,
    ):
        return

    aggregate.service_points += service_points
    aggregate.first_in += first_in
    aggregate.first_won += first_won
    aggregate.second_won += second_won
    aggregate.aces += aces
    aggregate.double_faults += double_faults
    aggregate.return_points += opponent_service_points
    aggregate.return_won += opponent_service_points - opponent_first_won - opponent_second_won


def _age_from_dob(dob: str | None) -> int | None:
    if not dob or len(dob) != 8:
        return None
    year = int(dob[0:4])
    month = int(dob[4:6])
    day = int(dob[6:8])
    birthday = date(year, month, day)
    return SNAPSHOT_DATE.year - birthday.year - (
        (SNAPSHOT_DATE.month, SNAPSHOT_DATE.day) < (birthday.month, birthday.day)
    )


def _surface_prior(rank_strength: float, base: float, bonus: float) -> float:
    return _clamp(base + rank_strength * bonus, 0.34, 0.88)


def _build_profile_row(
    player_name: str,
    rank: int,
    metadata: dict[str, str],
    aggregate: MatchAggregate | None,
    charting_snapshot: ChartingSnapshot | None,
) -> dict[str, object]:
    normalized_name = _normalize_name(player_name)
    height = int(metadata["height"]) if metadata.get("height") else 185
    age = _age_from_dob(metadata.get("dob")) or 25
    country = metadata.get("ioc", "UNK") or "UNK"
    hand_code = metadata.get("hand", "R")
    handedness = (
        HAND_OVERRIDES.get(normalized_name)
        or ("left" if hand_code == "L" else "right")
    )
    backhand_hands = 1 if normalized_name in ONE_HANDED_BACKHANDS else 2

    rank_strength = (100 - rank) / 99 if rank < 100 else 0.0
    height_bias = _clamp((height - 185) / 18, -1.0, 1.0)
    youth_bias = _clamp((24 - age) / 8, -0.5, 0.5)
    veteran_bias = _clamp((age - 29) / 10, 0.0, 0.6)
    clay_bias = 0.035 if country in CLAY_LEANING_COUNTRIES else 0.0
    hard_bias = 0.03 if country in HARD_LEANING_COUNTRIES else 0.0
    grass_bias = 0.025 if country in GRASS_LEANING_COUNTRIES else 0.0
    lefty_bonus = 0.012 if handedness == "left" else 0.0
    one_hander_bonus = 0.010 if backhand_hands == 1 else 0.0

    first_serve_in_prior = _clamp(0.60 + 0.02 * rank_strength - 0.008 * max(height_bias, 0.0), 0.55, 0.70)
    first_serve_points_won_prior = _clamp(
        0.68 + 0.06 * rank_strength + 0.06 * max(height_bias, 0.0) + lefty_bonus,
        0.63,
        0.83,
    )
    second_serve_points_won_prior = _clamp(
        0.48 + 0.07 * rank_strength + clay_bias + one_hander_bonus - 0.004 * youth_bias,
        0.44,
        0.63,
    )
    ace_rate_prior = _clamp(
        0.04 + 0.04 * rank_strength + 0.055 * max(height_bias, 0.0) + lefty_bonus,
        0.02,
        0.18,
    )
    double_fault_rate_prior = _clamp(
        0.034 - 0.006 * rank_strength + 0.004 * max(height_bias, 0.0) + 0.003 * youth_bias,
        0.018,
        0.055,
    )
    return_points_won_prior = _clamp(
        0.34 + 0.05 * rank_strength - 0.015 * max(height_bias, 0.0) + clay_bias - lefty_bonus / 2,
        0.32,
        0.44,
    )

    hard_win_rate_prior = _surface_prior(rank_strength, 0.47 + hard_bias - clay_bias / 2, 0.22)
    clay_win_rate_prior = _surface_prior(rank_strength, 0.45 + clay_bias + one_hander_bonus / 2, 0.20)
    grass_win_rate_prior = _surface_prior(
        rank_strength,
        0.42 + grass_bias + 0.03 * max(height_bias, 0.0) + lefty_bonus / 2,
        0.17,
    )

    first_serve_in_actual = None
    first_serve_points_won_actual = None
    second_serve_points_won_actual = None
    ace_rate_actual = None
    double_fault_rate_actual = None
    return_points_won_actual = None
    hard_win_rate_actual = None
    clay_win_rate_actual = None
    grass_win_rate_actual = None
    stats_note = "Generated from ranking-based priors only."

    if aggregate is not None:
        if aggregate.service_points > 0 and aggregate.first_in > 0:
            second_serve_points = aggregate.service_points - aggregate.first_in
            first_serve_in_actual = aggregate.first_in / aggregate.service_points
            first_serve_points_won_actual = aggregate.first_won / aggregate.first_in
            if second_serve_points > 0:
                second_serve_points_won_actual = aggregate.second_won / second_serve_points
            ace_rate_actual = aggregate.aces / aggregate.service_points
            double_fault_rate_actual = aggregate.double_faults / aggregate.service_points
        if aggregate.return_points > 0:
            return_points_won_actual = aggregate.return_won / aggregate.return_points
        if aggregate.matches > 0:
            stats_note = (
                f"Blended with 2024 ATP tour-level match stats from {aggregate.matches} match(es)."
            )
        if aggregate.surface_matches.get("hard"):
            hard_win_rate_actual = aggregate.surface_wins["hard"] / aggregate.surface_matches["hard"]
        if aggregate.surface_matches.get("clay"):
            clay_win_rate_actual = aggregate.surface_wins["clay"] / aggregate.surface_matches["clay"]
        if aggregate.surface_matches.get("grass"):
            grass_win_rate_actual = aggregate.surface_wins["grass"] / aggregate.surface_matches["grass"]

    service_sample = aggregate.service_points if aggregate is not None else 0
    return_sample = aggregate.return_points if aggregate is not None else 0
    match_sample = aggregate.matches if aggregate is not None else 0

    first_serve_in = _blend(first_serve_in_prior, first_serve_in_actual, service_sample / 900.0)
    first_serve_points_won = _blend(
        first_serve_points_won_prior,
        first_serve_points_won_actual,
        service_sample / 900.0,
    )
    second_serve_points_won = _blend(
        second_serve_points_won_prior,
        second_serve_points_won_actual,
        service_sample / 900.0,
    )
    ace_rate = _blend(ace_rate_prior, ace_rate_actual, service_sample / 1200.0)
    double_fault_rate = _blend(
        double_fault_rate_prior,
        double_fault_rate_actual,
        service_sample / 1200.0,
    )
    return_points_won = _blend(
        return_points_won_prior,
        return_points_won_actual,
        return_sample / 1200.0,
    )

    hard_win_rate = _blend(hard_win_rate_prior, hard_win_rate_actual, match_sample / 18.0)
    clay_win_rate = _blend(clay_win_rate_prior, clay_win_rate_actual, match_sample / 18.0)
    grass_win_rate = _blend(grass_win_rate_prior, grass_win_rate_actual, match_sample / 18.0)

    if charting_snapshot is not None:
        service_weight = min(charting_snapshot.service_points / 18000.0, 1.0) * 0.35
        return_weight = min(charting_snapshot.return_points / 18000.0, 1.0) * 0.35
        first_serve_in = _blend(first_serve_in, charting_snapshot.first_serve_in, service_weight)
        first_serve_points_won = _blend(
            first_serve_points_won,
            charting_snapshot.first_serve_points_won,
            service_weight,
        )
        second_serve_points_won = _blend(
            second_serve_points_won,
            charting_snapshot.second_serve_points_won,
            service_weight,
        )
        ace_rate = _blend(ace_rate, charting_snapshot.ace_rate, service_weight)
        return_points_won = _blend(
            return_points_won,
            charting_snapshot.return_points_won,
            return_weight,
        )

    service_point_win_rate = first_serve_in * first_serve_points_won + (
        1.0 - first_serve_in
    ) * second_serve_points_won
    hold_rate = _game_win_probability(service_point_win_rate)
    break_rate = _game_win_probability(return_points_won)

    if charting_snapshot is not None:
        preferred_serve_direction = charting_snapshot.preferred_serve_direction
    elif handedness == "left":
        preferred_serve_direction = "wide"
    elif height >= 196:
        preferred_serve_direction = "t"
    else:
        preferred_serve_direction = "wide"

    row = {
        "player_id": _slugify(player_name),
        "name": player_name,
        "country": country,
        "handedness": handedness,
        "backhand_hands": backhand_hands,
        "first_serve_in": round(first_serve_in, 4),
        "first_serve_points_won": round(first_serve_points_won, 4),
        "second_serve_points_won": round(second_serve_points_won, 4),
        "ace_rate": round(ace_rate, 4),
        "double_fault_rate": round(double_fault_rate, 4),
        "return_points_won": round(return_points_won, 4),
        "hold_rate": round(hold_rate, 4),
        "break_rate": round(break_rate, 4),
        "hard_win_rate": round(hard_win_rate, 4),
        "clay_win_rate": round(clay_win_rate, 4),
        "grass_win_rate": round(grass_win_rate, 4),
        "preferred_serve_direction": preferred_serve_direction,
    }
    if charting_snapshot is not None:
        if charting_snapshot.net_approach_rate is not None:
            row["net_frequency"] = _scale_to_rating(charting_snapshot.net_approach_rate, 0.03, 0.14)
        if charting_snapshot.net_points_won is not None:
            row["net_play"] = _scale_to_rating(charting_snapshot.net_points_won, 0.56, 0.76)
    row["source_notes"] = [
        f"ATP top-100 snapshot from {SNAPSHOT_DATE.isoformat()} ({SNAPSHOT_SOURCE}).",
        "Structured metadata from Jeff Sackmann's atp_players.csv.",
        "Structured performance inputs from Jeff Sackmann's 2024 ATP tour-level match stats.",
        stats_note,
        f"Current ATP rank at snapshot: {rank}.",
    ]
    if charting_snapshot is not None:
        row["source_notes"].append(TENNIS_ABSTRACT_NOTE)
        row["source_notes"].append(
            f"Tennis Abstract charting snapshot fetched on {charting_snapshot.fetched_at}: "
            f"{charting_snapshot.source_url}"
        )
    return row


def _load_existing_roster(roster_path: Path) -> list[dict[str, object]]:
    if not roster_path.exists():
        return []
    return json.loads(roster_path.read_text())


def _is_auto_generated_entry(entry: dict[str, object]) -> bool:
    notes = (
        entry.get("derived_stats", {}).get("source_notes", [])
        if isinstance(entry.get("derived_stats"), dict)
        else []
    )
    return bool(notes) and str(notes[0]).startswith(AUTO_GENERATED_NOTE_PREFIX)


def _ensure_pressure_handling(entry: dict[str, object]) -> None:
    skills = entry.get("skills")
    if not isinstance(skills, dict):
        return
    if "pressure_handling" not in skills:
        skills["pressure_handling"] = int(skills.get("composure", 50))


def _get_nested(entry: dict[str, object], path: tuple[str, str]) -> int:
    parent = entry[path[0]]
    if not isinstance(parent, dict):
        raise TypeError(f"Expected dict at {path[0]}")
    return int(parent[path[1]])


def _set_nested(entry: dict[str, object], path: tuple[str, str], value: int) -> None:
    parent = entry[path[0]]
    if not isinstance(parent, dict):
        raise TypeError(f"Expected dict at {path[0]}")
    parent[path[1]] = int(value)


def _percentiles(values: list[int]) -> list[float]:
    count = len(values)
    if count <= 1:
        return [0.5 for _ in values]
    ordered = sorted((value, index) for index, value in enumerate(values))
    result = [0.5 for _ in values]
    start = 0
    while start < count:
        end = start
        while end + 1 < count and ordered[end + 1][0] == ordered[start][0]:
            end += 1
        percentile = ((start + end) / 2) / (count - 1)
        for position in range(start, end + 1):
            _, original_index = ordered[position]
            result[original_index] = percentile
        start = end + 1
    return result


def _normalize_generated_payloads(entries: list[dict[str, object]]) -> None:
    if not entries:
        return

    for entry in entries:
        _ensure_pressure_handling(entry)

    for path, (lower, upper) in TOP_100_NORMALIZATION_RANGES.items():
        values = [_get_nested(entry, path) for entry in entries]
        percentiles = _percentiles(values)
        group_weight = TOP_100_RANK_BIAS_BY_GROUP.get(path[0], 0.0)
        for entry, percentile in zip(entries, percentiles, strict=True):
            snapshot_rank = int(entry.get("_snapshot_rank", 100))
            rank_strength = (100 - snapshot_rank) / 99 if snapshot_rank < 100 else 0.0
            adjusted_percentile = percentile * (1.0 - group_weight) + rank_strength * group_weight
            normalized = int(round(lower + adjusted_percentile * (upper - lower)))
            _set_nested(entry, path, normalized)

    for entry in entries:
        notes = entry.get("derived_stats", {}).get("source_notes", [])
        if isinstance(notes, list) and TOP_100_NORMALIZATION_NOTE not in notes:
            notes.append(TOP_100_NORMALIZATION_NOTE)
        entry.pop("_snapshot_rank", None)


def build_roster(
    players_csv_path: Path,
    matches_csv_path: Path,
    roster_path: Path,
    output_path: Path,
    charting_cache_path: Path | None = None,
) -> tuple[int, int, int]:
    metadata_index = _build_metadata_index(players_csv_path)
    aggregates = _aggregate_match_stats(matches_csv_path)
    charting_by_player_id = (
        load_charting_cache(charting_cache_path)
        if charting_cache_path is not None and charting_cache_path.exists()
        else {}
    )
    existing_entries = _load_existing_roster(roster_path)
    existing_by_id = {entry["player_id"]: entry for entry in existing_entries}
    output_entries: list[dict[str, object]] = []
    generated_payloads: list[dict[str, object]] = []

    kept_existing = 0
    generated_new = 0
    included_ids: set[str] = set()

    for snapshot_entry in TOP_100_SNAPSHOT:
        player_name = snapshot_entry["name"]
        rank = snapshot_entry["rank"]
        player_id = _slugify(player_name)
        included_ids.add(player_id)

        existing_entry = existing_by_id.get(player_id)
        if existing_entry is not None and not _is_auto_generated_entry(existing_entry):
            _ensure_pressure_handling(existing_entry)
            output_entries.append(existing_entry)
            kept_existing += 1
            continue

        metadata = metadata_index.get(_normalize_name(player_name))
        if metadata is None:
            raise KeyError(f"Missing player metadata for {player_name}")

        row = _build_profile_row(
            player_name=player_name,
            rank=rank,
            metadata=metadata,
            aggregate=aggregates.get(_normalize_name(player_name)),
            charting_snapshot=charting_by_player_id.get(player_id),
        )
        profile = build_profile_from_atp_row(row)
        payload = profile.to_dict()
        payload["derived_stats"]["source_notes"] = row["source_notes"]
        payload["_snapshot_rank"] = rank
        generated_payloads.append(payload)
        output_entries.append(payload)
        generated_new += 1

    _normalize_generated_payloads(generated_payloads)

    for entry in existing_entries:
        if entry["player_id"] not in included_ids:
            _ensure_pressure_handling(entry)
            output_entries.append(entry)

    output_path.write_text(json.dumps(output_entries, indent=2) + "\n")
    return kept_existing, generated_new, len(output_entries)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an ATP top-100 roster snapshot.")
    parser.add_argument("--players-csv", required=True, type=Path)
    parser.add_argument("--matches-csv", required=True, type=Path)
    parser.add_argument(
        "--roster-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "players" / "atp_profiles.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "players" / "atp_profiles.json",
    )
    parser.add_argument(
        "--ta-charting-cache",
        type=Path,
        default=DEFAULT_TENNIS_ABSTRACT_CACHE,
        help="Optional Tennis Abstract charting cache generated by fetch_tennis_abstract_charting.py.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    kept_existing, generated_new, total = build_roster(
        players_csv_path=args.players_csv,
        matches_csv_path=args.matches_csv,
        roster_path=args.roster_path,
        output_path=args.output,
        charting_cache_path=args.ta_charting_cache,
    )
    print(
        f"built roster: kept {kept_existing} existing profile(s), "
        f"generated {generated_new} new profile(s), total {total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
