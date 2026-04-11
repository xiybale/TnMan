from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Surface(StrEnum):
    HARD = "hard"
    CLAY = "clay"
    GRASS = "grass"


class Handedness(StrEnum):
    RIGHT = "right"
    LEFT = "left"


class ServeDirection(StrEnum):
    WIDE = "wide"
    BODY = "body"
    T = "t"


class SpinType(StrEnum):
    FLAT = "flat"
    TOPSPIN = "topspin"
    SLICE = "slice"
    KICK = "kick"


class ShotKind(StrEnum):
    SERVE = "serve"
    RETURN = "return"
    DRIVE = "drive"
    SLICE = "slice"
    APPROACH = "approach"
    VOLLEY = "volley"
    LOB = "lob"
    SMASH = "smash"


class ShotHand(StrEnum):
    FOREHAND = "forehand"
    BACKHAND = "backhand"
    NONE = "none"


class ShotOutcome(StrEnum):
    FAULT = "fault"
    DOUBLE_FAULT = "double_fault"
    ACE = "ace"
    SERVICE_WINNER = "service_winner"
    RETURN_WINNER = "return_winner"
    WINNER = "winner"
    FORCED_ERROR = "forced_error"
    UNFORCED_ERROR = "unforced_error"
    CONTINUE = "continue"


class RallyQuality(StrEnum):
    DEFENSIVE = "defensive"
    NEUTRAL = "neutral"
    AGGRESSIVE = "aggressive"
    FINISHING = "finishing"


@dataclass(slots=True)
class SkillRatings:
    serve_power: int
    serve_accuracy: int
    second_serve_reliability: int
    return_quality: int
    forehand_quality: int
    backhand_quality: int
    movement: int
    anticipation: int
    rally_tolerance: int
    net_play: int
    composure: int
    pressure_handling: int
    stamina: int

    def normalized(self, field_name: str) -> float:
        return max(0.0, min(1.0, getattr(self, field_name) / 100.0))


@dataclass(slots=True)
class TacticalProfile:
    baseline_aggression: int
    preferred_serve_direction: ServeDirection
    short_ball_attack: int
    net_frequency: int


@dataclass(slots=True)
class SpinProfile:
    serve_spin: int
    forehand_spin: int
    backhand_spin: int
    slice_frequency: int


@dataclass(slots=True)
class PhysicalProfile:
    durability: int
    recovery: int
    peak_condition: int


@dataclass(slots=True)
class SurfaceProfile:
    hard: int
    clay: int
    grass: int

    def comfort(self, surface: Surface) -> int:
        return getattr(self, surface.value)


@dataclass(slots=True)
class DerivedStats:
    first_serve_in: float | None = None
    first_serve_points_won: float | None = None
    second_serve_points_won: float | None = None
    ace_rate: float | None = None
    double_fault_rate: float | None = None
    return_points_won: float | None = None
    break_rate: float | None = None
    hold_rate: float | None = None
    hard_win_rate: float | None = None
    clay_win_rate: float | None = None
    grass_win_rate: float | None = None
    source_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PlayerProfile:
    player_id: str
    name: str
    country: str
    tour: str
    handedness: Handedness
    backhand_hands: int
    skills: SkillRatings
    tactics: TacticalProfile
    spin: SpinProfile
    physical: PhysicalProfile
    surface_profile: SurfaceProfile
    derived_stats: DerivedStats = field(default_factory=DerivedStats)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlayerProfile":
        skill_payload = dict(payload["skills"])
        skill_payload.setdefault("pressure_handling", int(skill_payload.get("composure", 50)))
        spin_payload = payload.get("spin") or {
            "serve_spin": 55,
            "forehand_spin": 55,
            "backhand_spin": 60 if int(payload["backhand_hands"]) == 1 else 50,
            "slice_frequency": 55 if int(payload["backhand_hands"]) == 1 else 35,
        }
        return cls(
            player_id=payload["player_id"],
            name=payload["name"],
            country=payload["country"],
            tour=payload.get("tour", "ATP"),
            handedness=Handedness(payload["handedness"]),
            backhand_hands=int(payload["backhand_hands"]),
            skills=SkillRatings(**skill_payload),
            tactics=TacticalProfile(
                baseline_aggression=int(payload["tactics"]["baseline_aggression"]),
                preferred_serve_direction=ServeDirection(
                    payload["tactics"]["preferred_serve_direction"]
                ),
                short_ball_attack=int(payload["tactics"]["short_ball_attack"]),
                net_frequency=int(payload["tactics"]["net_frequency"]),
            ),
            spin=SpinProfile(**spin_payload),
            physical=PhysicalProfile(**payload["physical"]),
            surface_profile=SurfaceProfile(**payload["surface_profile"]),
            derived_stats=DerivedStats(**payload.get("derived_stats", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["handedness"] = self.handedness.value
        payload["tactics"]["preferred_serve_direction"] = self.tactics.preferred_serve_direction.value
        return payload

    def surface_comfort(self, surface: Surface) -> float:
        return self.surface_profile.comfort(surface) / 100.0


@dataclass(slots=True)
class MatchConfig:
    surface: Surface = Surface.HARD
    best_of_sets: int = 3
    initial_server: str | None = None
    seed: int = 1

    def __post_init__(self) -> None:
        if self.best_of_sets not in (3, 5):
            raise ValueError("best_of_sets must be 3 or 5")


@dataclass(slots=True)
class CompletedSet:
    games: dict[str, int]
    tiebreak_points: dict[str, int] | None = None

    def score_for(self, player_one_id: str, player_two_id: str) -> str:
        base = f"{self.games[player_one_id]}-{self.games[player_two_id]}"
        if self.tiebreak_points is None:
            return base
        return (
            f"{base}"
            f"({self.tiebreak_points[player_one_id]}-{self.tiebreak_points[player_two_id]})"
        )


@dataclass(slots=True)
class PointState:
    point_number: int
    server_id: str
    receiver_id: str
    sets_won: dict[str, int]
    games: dict[str, int]
    server_points: int
    receiver_points: int
    server_display: str
    receiver_display: str
    point_score: str
    score_before: str
    is_tiebreak: bool
    is_deuce: bool
    break_point_for: str | None = None
    set_point_for: str | None = None
    match_point_for: str | None = None
    pressure_index: int = 0
    pressure_label: str = "routine"


@dataclass(slots=True)
class ShotEvent:
    point_number: int
    shot_number: int
    score_before: str
    striker_id: str
    receiver_id: str
    shot_kind: ShotKind
    shot_hand: ShotHand
    quality: RallyQuality
    outcome: ShotOutcome
    spin_type: SpinType = SpinType.FLAT
    serve_number: int | None = None
    serve_direction: ServeDirection | None = None
    pressure: float = 0.0
    fatigue: float = 0.0
    detail: str = ""


@dataclass(slots=True)
class PointRecord:
    point_number: int
    set_number: int
    game_number_in_set: int
    server_id: str
    receiver_id: str
    winner_id: str
    score_before: str
    score_after: str
    point_score_before: str
    point_score_after: str
    sets_before: dict[str, int]
    sets_after: dict[str, int]
    games_before: dict[str, int]
    games_after: dict[str, int]
    is_tiebreak: bool
    break_point_for: str | None
    set_point_for: str | None
    match_point_for: str | None
    pressure_index: int
    pressure_label: str
    rally_length: int
    terminal_outcome: ShotOutcome
    terminal_shot_kind: ShotKind
    terminal_striker_id: str
    events: list[ShotEvent]
    game_completed: bool = False
    set_completed: bool = False
    match_completed: bool = False
    game_winner_id: str | None = None
    set_winner_id: str | None = None


@dataclass(slots=True)
class PlayerMatchStats:
    points_played: int = 0
    total_points_won: int = 0
    service_points_played: int = 0
    service_points_won: int = 0
    return_points_played: int = 0
    return_points_won: int = 0
    aces: int = 0
    service_winners: int = 0
    double_faults: int = 0
    winners: int = 0
    return_winners: int = 0
    forced_errors_drawn: int = 0
    unforced_errors: int = 0
    first_serves_in: int = 0
    first_serve_attempts: int = 0
    second_serves_in: int = 0
    second_serve_attempts: int = 0
    break_points_created: int = 0
    break_points_converted: int = 0
    break_points_faced: int = 0
    break_points_saved: int = 0
    games_served: int = 0
    service_games_won: int = 0
    total_shots: int = 0

    def absorb(self, other: "PlayerMatchStats") -> None:
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, getattr(self, field_name) + getattr(other, field_name))

    def total_winners(self) -> int:
        return self.aces + self.service_winners + self.winners + self.return_winners

    def first_serve_percentage(self) -> float:
        if self.first_serve_attempts == 0:
            return 0.0
        return self.first_serves_in / self.first_serve_attempts

    def service_points_won_percentage(self) -> float:
        if self.service_points_played == 0:
            return 0.0
        return self.service_points_won / self.service_points_played

    def return_points_won_percentage(self) -> float:
        if self.return_points_played == 0:
            return 0.0
        return self.return_points_won / self.return_points_played

    def hold_percentage(self) -> float:
        if self.games_served == 0:
            return 0.0
        return self.service_games_won / self.games_served

    def ace_rate(self) -> float:
        if self.service_points_played == 0:
            return 0.0
        return self.aces / self.service_points_played

    def double_fault_rate(self) -> float:
        if self.service_points_played == 0:
            return 0.0
        return self.double_faults / self.service_points_played

    def second_serve_double_fault_rate(self) -> float:
        if self.second_serve_attempts == 0:
            return 0.0
        return self.double_faults / self.second_serve_attempts

    def winner_to_error_ratio(self) -> float:
        if self.unforced_errors == 0:
            return float(self.total_winners())
        return self.total_winners() / self.unforced_errors


@dataclass(slots=True)
class MatchResult:
    players: tuple[str, str]
    winner_id: str
    scoreline: str
    set_scores: list[CompletedSet]
    stats: dict[str, PlayerMatchStats]
    shot_log: list[ShotEvent]
    rally_lengths: list[int]
    seed: int
    surface: Surface
    best_of_sets: int
    points: list[PointRecord] = field(default_factory=list)

    @property
    def average_rally_length(self) -> float:
        if not self.rally_lengths:
            return 0.0
        return sum(self.rally_lengths) / len(self.rally_lengths)

    @property
    def total_points(self) -> int:
        return sum(self.stats[player_id].total_points_won for player_id in self.players)


@dataclass(slots=True)
class BatchSummary:
    players: tuple[str, str]
    iterations: int
    wins: dict[str, int]
    hold_rate: dict[str, float]
    break_rate: dict[str, float]
    ace_rate: dict[str, float]
    first_serve_in_rate: dict[str, float]
    double_fault_rate: dict[str, float]
    second_serve_double_fault_rate: dict[str, float]
    service_points_won_rate: dict[str, float]
    return_points_won_rate: dict[str, float]
    winner_to_error_ratio: dict[str, float]
    average_rally_length: float
    average_points_per_match: float
    common_scorelines: dict[str, int]
    rally_band_distribution: dict[str, float]
    surface: Surface

    def win_rate(self, player_id: str) -> float:
        if self.iterations == 0:
            return 0.0
        return self.wins[player_id] / self.iterations
