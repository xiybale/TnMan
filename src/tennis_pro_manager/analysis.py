from __future__ import annotations

from dataclasses import dataclass

from .models import MatchResult, PlayerProfile, ShotEvent, ShotHand, ShotKind, ShotOutcome

RALLY_BANDS: tuple[tuple[str, int, int | None], ...] = (
    ("1-2", 1, 2),
    ("3-6", 3, 6),
    ("7-10", 7, 10),
    ("11+", 11, None),
)


@dataclass(slots=True)
class PlayerPatternSummary:
    serve_directions: dict[str, int]
    serve_spins: dict[str, int]
    targeted_wings: dict[str, int]
    shot_spins: dict[str, int]
    winners_by_hand: dict[str, int]
    forced_errors_drawn_by_hand: dict[str, int]
    unforced_errors_by_hand: dict[str, int]


@dataclass(slots=True)
class MatchPatternSummary:
    rally_bands: dict[str, int]
    players: dict[str, PlayerPatternSummary]


def rally_band_counts(rally_lengths: list[int]) -> dict[str, int]:
    counts = {label: 0 for label, _, _ in RALLY_BANDS}
    for rally_length in rally_lengths:
        counts[_rally_band_label(rally_length)] += 1
    return counts


def rally_band_distribution(rally_lengths: list[int]) -> dict[str, float]:
    counts = rally_band_counts(rally_lengths)
    total = sum(counts.values())
    if total == 0:
        return {label: 0.0 for label in counts}
    return {label: count / total for label, count in counts.items()}


def build_match_pattern_summary(
    result: MatchResult,
    roster: dict[str, PlayerProfile],
) -> MatchPatternSummary:
    players = {
        player_id: PlayerPatternSummary(
            serve_directions={label: 0 for label in ("wide", "body", "t")},
            serve_spins={label: 0 for label in ("flat", "slice", "kick", "topspin")},
            targeted_wings={label: 0 for label in ("forehand", "backhand")},
            shot_spins={label: 0 for label in ("flat", "slice", "kick", "topspin")},
            winners_by_hand={label: 0 for label in ("forehand", "backhand", "none")},
            forced_errors_drawn_by_hand={label: 0 for label in ("forehand", "backhand", "none")},
            unforced_errors_by_hand={label: 0 for label in ("forehand", "backhand", "none")},
        )
        for player_id in result.players
    }

    for event in result.shot_log:
        summary = players[event.striker_id]
        target = infer_target_wing(event, roster)
        if target != ShotHand.NONE:
            summary.targeted_wings[target.value] += 1

        if event.shot_kind == ShotKind.SERVE:
            if event.serve_direction is not None:
                summary.serve_directions[event.serve_direction.value] += 1
            summary.serve_spins[event.spin_type.value] += 1
        else:
            summary.shot_spins[event.spin_type.value] += 1

        if event.outcome in (ShotOutcome.WINNER, ShotOutcome.RETURN_WINNER):
            summary.winners_by_hand[event.shot_hand.value] += 1
        elif event.outcome == ShotOutcome.FORCED_ERROR:
            summary.forced_errors_drawn_by_hand[event.shot_hand.value] += 1
        elif event.outcome == ShotOutcome.UNFORCED_ERROR:
            summary.unforced_errors_by_hand[event.shot_hand.value] += 1

    return MatchPatternSummary(
        rally_bands=rally_band_counts(result.rally_lengths),
        players=players,
    )


def infer_target_wing(event: ShotEvent, roster: dict[str, PlayerProfile]) -> ShotHand:
    striker = roster[event.striker_id]
    receiver = roster[event.receiver_id]
    if event.shot_kind == ShotKind.SERVE:
        if event.serve_direction is None:
            return ShotHand.NONE
        return ShotHand.BACKHAND if _serve_targets_backhand(striker, receiver, event.serve_direction.value) else ShotHand.FOREHAND

    if event.shot_hand == ShotHand.NONE:
        return ShotHand.NONE

    if event.shot_hand == ShotHand.FOREHAND:
        return ShotHand.BACKHAND if striker.handedness != receiver.handedness else ShotHand.FOREHAND
    return ShotHand.BACKHAND if striker.handedness == receiver.handedness else ShotHand.FOREHAND


def _serve_targets_backhand(
    striker: PlayerProfile,
    receiver: PlayerProfile,
    serve_direction: str,
) -> bool:
    if serve_direction == "body":
        return receiver.backhand_hands == 1
    if serve_direction == "wide":
        return striker.handedness != receiver.handedness
    return striker.handedness == receiver.handedness


def _rally_band_label(rally_length: int) -> str:
    for label, minimum, maximum in RALLY_BANDS:
        if rally_length < minimum:
            continue
        if maximum is None or rally_length <= maximum:
            return label
    return RALLY_BANDS[-1][0]
