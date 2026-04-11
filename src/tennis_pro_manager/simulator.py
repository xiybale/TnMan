from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .analysis import rally_band_distribution
from .models import (
    BatchSummary,
    MatchConfig,
    MatchResult,
    PlayerMatchStats,
    PointRecord,
    PlayerProfile,
    PointState,
    RallyQuality,
    ServeDirection,
    ShotEvent,
    ShotHand,
    ShotKind,
    ShotOutcome,
    SpinType,
    Surface,
)
from .scoring import ScoreTracker


@dataclass(slots=True)
class SurfaceTuning:
    serve_in_adjustment: float
    serve_boost: float
    return_boost: float
    rally_extension: float
    movement_bonus: float


@dataclass(slots=True)
class PointSimulationResult:
    winner_id: str
    events: list[ShotEvent]
    rally_length: int


SURFACE_TUNING = {
    Surface.HARD: SurfaceTuning(
        serve_in_adjustment=0.0,
        serve_boost=0.0,
        return_boost=0.0,
        rally_extension=0.0,
        movement_bonus=0.0,
    ),
    Surface.CLAY: SurfaceTuning(
        serve_in_adjustment=-0.01,
        serve_boost=-0.03,
        return_boost=0.02,
        rally_extension=0.08,
        movement_bonus=0.05,
    ),
    Surface.GRASS: SurfaceTuning(
        serve_in_adjustment=0.01,
        serve_boost=0.05,
        return_boost=-0.02,
        rally_extension=-0.07,
        movement_bonus=-0.03,
    ),
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _n(value: int) -> float:
    return _clamp(value / 100.0, 0.0, 1.0)


class MatchSimulator:
    def __init__(self, roster: dict[str, PlayerProfile]):
        self.roster = roster

    def simulate_match(
        self,
        player_one: str | PlayerProfile,
        player_two: str | PlayerProfile,
        config: MatchConfig,
    ) -> MatchResult:
        player_one_profile = self._resolve_player(player_one)
        player_two_profile = self._resolve_player(player_two)
        if player_one_profile.player_id == player_two_profile.player_id:
            raise ValueError("Match requires two distinct players")

        initial_server = config.initial_server or player_one_profile.player_id
        tracker = ScoreTracker(
            player_one_profile.player_id,
            player_two_profile.player_id,
            best_of_sets=config.best_of_sets,
            initial_server=initial_server,
        )
        players = {
            player_one_profile.player_id: player_one_profile,
            player_two_profile.player_id: player_two_profile,
        }
        stats = {player_id: PlayerMatchStats() for player_id in players}
        rng = random.Random(config.seed)
        shot_log: list[ShotEvent] = []
        rally_lengths: list[int] = []
        points: list[PointRecord] = []

        point_number = 1
        while not tracker.is_match_over:
            point_state = tracker.snapshot(point_number)
            server_id = point_state.server_id
            receiver_id = point_state.receiver_id

            if point_state.break_point_for == receiver_id:
                stats[receiver_id].break_points_created += 1
                stats[server_id].break_points_faced += 1

            point_result = self._simulate_point(
                point_state,
                players[server_id],
                players[receiver_id],
                stats,
                rng,
                config.surface,
            )

            stats[server_id].points_played += 1
            stats[receiver_id].points_played += 1
            stats[server_id].service_points_played += 1
            stats[receiver_id].return_points_played += 1
            stats[point_result.winner_id].total_points_won += 1

            if point_result.winner_id == server_id:
                stats[server_id].service_points_won += 1
            else:
                stats[receiver_id].return_points_won += 1

            if point_state.break_point_for == receiver_id:
                if point_result.winner_id == receiver_id:
                    stats[receiver_id].break_points_converted += 1
                else:
                    stats[server_id].break_points_saved += 1

            shot_log.extend(point_result.events)
            rally_lengths.append(point_result.rally_length)

            update = tracker.point_won_by(point_result.winner_id)
            if update.game_completed:
                stats[server_id].games_served += 1
                if update.game_winner_id == server_id:
                    stats[server_id].service_games_won += 1

            points.append(
                self._build_point_record(
                    match_players=players,
                    point_state=point_state,
                    winner_id=point_result.winner_id,
                    events=point_result.events,
                    rally_length=point_result.rally_length,
                    tracker=tracker,
                    game_completed=update.game_completed,
                    set_completed=update.set_completed,
                    match_completed=update.match_completed,
                    game_winner_id=update.game_winner_id,
                    set_winner_id=update.set_winner_id,
                    completed_set=update.completed_set,
                )
            )

            point_number += 1

        winner_id = tracker.match_winner_id
        if winner_id is None:
            raise RuntimeError("Match ended without a winner")

        return MatchResult(
            players=(player_one_profile.player_id, player_two_profile.player_id),
            winner_id=winner_id,
            scoreline=tracker.scoreline(),
            set_scores=list(tracker.completed_sets),
            stats=stats,
            shot_log=shot_log,
            rally_lengths=rally_lengths,
            seed=config.seed,
            surface=config.surface,
            best_of_sets=config.best_of_sets,
            points=points,
        )

    def simulate_batch(
        self,
        player_one: str | PlayerProfile,
        player_two: str | PlayerProfile,
        config: MatchConfig,
        iterations: int,
    ) -> BatchSummary:
        if iterations <= 0:
            raise ValueError("iterations must be positive")

        player_one_profile = self._resolve_player(player_one)
        player_two_profile = self._resolve_player(player_two)
        aggregate = {
            player_one_profile.player_id: PlayerMatchStats(),
            player_two_profile.player_id: PlayerMatchStats(),
        }
        wins = {player_one_profile.player_id: 0, player_two_profile.player_id: 0}
        scoreline_counts: Counter[str] = Counter()
        total_rally_length = 0.0
        total_points = 0
        all_rally_lengths: list[int] = []

        for offset in range(iterations):
            match_config = MatchConfig(
                surface=config.surface,
                best_of_sets=config.best_of_sets,
                initial_server=config.initial_server or player_one_profile.player_id,
                seed=config.seed + offset,
            )
            result = self.simulate_match(player_one_profile, player_two_profile, match_config)
            wins[result.winner_id] += 1
            scoreline_counts[result.scoreline] += 1
            total_rally_length += result.average_rally_length
            total_points += result.total_points
            all_rally_lengths.extend(result.rally_lengths)
            for player_id in aggregate:
                aggregate[player_id].absorb(result.stats[player_id])

        hold_rate = {player_id: aggregate[player_id].hold_percentage() for player_id in aggregate}
        break_rate = {
            player_one_profile.player_id: 1.0 - aggregate[player_two_profile.player_id].hold_percentage(),
            player_two_profile.player_id: 1.0 - aggregate[player_one_profile.player_id].hold_percentage(),
        }
        ace_rate = {player_id: aggregate[player_id].ace_rate() for player_id in aggregate}
        first_serve_in_rate = {
            player_id: aggregate[player_id].first_serve_percentage() for player_id in aggregate
        }
        double_fault_rate = {
            player_id: aggregate[player_id].double_fault_rate() for player_id in aggregate
        }
        second_serve_double_fault_rate = {
            player_id: aggregate[player_id].second_serve_double_fault_rate() for player_id in aggregate
        }
        service_points_won_rate = {
            player_id: aggregate[player_id].service_points_won_percentage() for player_id in aggregate
        }
        return_points_won_rate = {
            player_id: aggregate[player_id].return_points_won_percentage() for player_id in aggregate
        }
        winner_to_error_ratio = {
            player_id: aggregate[player_id].winner_to_error_ratio() for player_id in aggregate
        }

        return BatchSummary(
            players=(player_one_profile.player_id, player_two_profile.player_id),
            iterations=iterations,
            wins=wins,
            hold_rate=hold_rate,
            break_rate=break_rate,
            ace_rate=ace_rate,
            first_serve_in_rate=first_serve_in_rate,
            double_fault_rate=double_fault_rate,
            second_serve_double_fault_rate=second_serve_double_fault_rate,
            service_points_won_rate=service_points_won_rate,
            return_points_won_rate=return_points_won_rate,
            winner_to_error_ratio=winner_to_error_ratio,
            average_rally_length=total_rally_length / iterations,
            average_points_per_match=total_points / iterations,
            common_scorelines=dict(scoreline_counts.most_common(5)),
            rally_band_distribution=rally_band_distribution(all_rally_lengths),
            surface=config.surface,
        )

    def _resolve_player(self, player: str | PlayerProfile) -> PlayerProfile:
        if isinstance(player, PlayerProfile):
            return player
        try:
            return self.roster[player]
        except KeyError as exc:
            raise KeyError(f"Unknown player id: {player}") from exc

    def _build_point_record(
        self,
        *,
        match_players: dict[str, PlayerProfile],
        point_state: PointState,
        winner_id: str,
        events: list[ShotEvent],
        rally_length: int,
        tracker: ScoreTracker,
        game_completed: bool,
        set_completed: bool,
        match_completed: bool,
        game_winner_id: str | None,
        set_winner_id: str | None,
        completed_set,
    ) -> PointRecord:
        player_one_id, player_two_id = match_players
        set_number = sum(point_state.sets_won.values()) + 1
        game_number_in_set = sum(point_state.games.values()) + 1
        sets_after = dict(tracker.sets_won)

        if set_completed and completed_set is not None:
            games_after = dict(completed_set.games)
            score_after = completed_set.score_for(player_one_id, player_two_id)
            point_score_after = "Match" if match_completed else "Set"
        else:
            games_after = dict(tracker.current_games)
            score_after = tracker.snapshot(point_state.point_number + 1).score_before
            point_score_after = "Game" if game_completed else tracker.current_point_score_label()

        terminal_event = events[-1]
        return PointRecord(
            point_number=point_state.point_number,
            set_number=set_number,
            game_number_in_set=game_number_in_set,
            server_id=point_state.server_id,
            receiver_id=point_state.receiver_id,
            winner_id=winner_id,
            score_before=point_state.score_before,
            score_after=score_after,
            point_score_before=point_state.point_score,
            point_score_after=point_score_after,
            sets_before=dict(point_state.sets_won),
            sets_after=sets_after,
            games_before=dict(point_state.games),
            games_after=games_after,
            is_tiebreak=point_state.is_tiebreak,
            break_point_for=point_state.break_point_for,
            set_point_for=point_state.set_point_for,
            match_point_for=point_state.match_point_for,
            pressure_index=point_state.pressure_index,
            pressure_label=point_state.pressure_label,
            rally_length=rally_length,
            terminal_outcome=terminal_event.outcome,
            terminal_shot_kind=terminal_event.shot_kind,
            terminal_striker_id=terminal_event.striker_id,
            events=list(events),
            game_completed=game_completed,
            set_completed=set_completed,
            match_completed=match_completed,
            game_winner_id=game_winner_id,
            set_winner_id=set_winner_id,
        )

    def _simulate_point(
        self,
        point_state: PointState,
        server: PlayerProfile,
        receiver: PlayerProfile,
        stats: dict[str, PlayerMatchStats],
        rng: random.Random,
        surface: Surface,
    ) -> PointSimulationResult:
        tuning = SURFACE_TUNING[surface]
        events: list[ShotEvent] = []
        shot_number = 1
        rally_length = 0

        server_fatigue = self._fatigue(stats[server.player_id], server)
        receiver_fatigue = self._fatigue(stats[receiver.player_id], receiver)
        server_pressure = self._pressure(point_state, server.player_id)
        receiver_pressure = self._pressure(point_state, receiver.player_id)

        first_direction = self._choose_serve_direction(server, receiver, rng, serve_number=1)
        first_spin = self._choose_serve_spin(server, first_direction, serve_number=1, rng=rng)
        stats[server.player_id].first_serve_attempts += 1
        stats[server.player_id].total_shots += 1
        first_serve_in = self._first_serve_in_probability(
            server,
            surface,
            server_fatigue,
            server_pressure,
            tuning,
            first_spin,
        )

        if rng.random() > first_serve_in:
            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=server.player_id,
                    receiver_id=receiver.player_id,
                    shot_kind=ShotKind.SERVE,
                    shot_hand=ShotHand.NONE,
                    quality=RallyQuality.NEUTRAL,
                    outcome=ShotOutcome.FAULT,
                    spin_type=first_spin,
                    serve_number=1,
                    serve_direction=first_direction,
                    pressure=server_pressure,
                    fatigue=server_fatigue,
                    detail="First serve missed",
                )
            )
            shot_number += 1
            second_direction = self._choose_serve_direction(server, receiver, rng, serve_number=2)
            second_spin = self._choose_serve_spin(server, second_direction, serve_number=2, rng=rng)
            stats[server.player_id].second_serve_attempts += 1
            stats[server.player_id].total_shots += 1
            second_serve_in = self._second_serve_in_probability(
                server,
                surface,
                server_fatigue,
                server_pressure,
                tuning,
                second_spin,
            )

            if rng.random() > second_serve_in:
                stats[server.player_id].double_faults += 1
                events.append(
                    ShotEvent(
                        point_number=point_state.point_number,
                        shot_number=shot_number,
                        score_before=point_state.score_before,
                        striker_id=server.player_id,
                        receiver_id=receiver.player_id,
                        shot_kind=ShotKind.SERVE,
                        shot_hand=ShotHand.NONE,
                        quality=RallyQuality.DEFENSIVE,
                        outcome=ShotOutcome.DOUBLE_FAULT,
                        spin_type=second_spin,
                        serve_number=2,
                        serve_direction=second_direction,
                        pressure=server_pressure,
                        fatigue=server_fatigue,
                        detail="Second serve missed",
                    )
                )
                return PointSimulationResult(receiver.player_id, events, rally_length)

            stats[server.player_id].second_serves_in += 1
            serve_number = 2
            serve_direction = second_direction
            serve_threat = self._serve_threat(
                server,
                receiver,
                surface,
                tuning,
                serve_direction=serve_direction,
                serve_spin=second_spin,
                first_serve=False,
                server_fatigue=server_fatigue,
                receiver_fatigue=receiver_fatigue,
            )
        else:
            stats[server.player_id].first_serves_in += 1
            serve_number = 1
            serve_direction = first_direction
            serve_threat = self._serve_threat(
                server,
                receiver,
                surface,
                tuning,
                serve_direction=serve_direction,
                serve_spin=first_spin,
                first_serve=True,
                server_fatigue=server_fatigue,
                receiver_fatigue=receiver_fatigue,
            )

        serve_quality = self._quality_band(0.58 + serve_threat)
        serve_spin = first_spin if serve_number == 1 else second_spin
        ace_chance = self._ace_probability(
            server,
            serve_threat,
            serve_number,
            server_pressure,
            tuning,
            serve_spin,
            serve_direction,
        )
        service_winner_chance = self._service_winner_probability(
            serve_threat,
            serve_number,
            serve_spin,
            serve_direction,
        )
        terminal_roll = rng.random()

        if terminal_roll < ace_chance:
            stats[server.player_id].aces += 1
            rally_length = 1
            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=server.player_id,
                    receiver_id=receiver.player_id,
                    shot_kind=ShotKind.SERVE,
                    shot_hand=ShotHand.NONE,
                    quality=serve_quality,
                    outcome=ShotOutcome.ACE,
                    spin_type=serve_spin,
                    serve_number=serve_number,
                    serve_direction=serve_direction,
                    pressure=server_pressure,
                    fatigue=server_fatigue,
                    detail="Unreturned serve",
                )
            )
            return PointSimulationResult(server.player_id, events, rally_length)

        if terminal_roll < ace_chance + service_winner_chance:
            stats[server.player_id].service_winners += 1
            rally_length = 1
            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=server.player_id,
                    receiver_id=receiver.player_id,
                    shot_kind=ShotKind.SERVE,
                    shot_hand=ShotHand.NONE,
                    quality=serve_quality,
                    outcome=ShotOutcome.SERVICE_WINNER,
                    spin_type=serve_spin,
                    serve_number=serve_number,
                    serve_direction=serve_direction,
                    pressure=server_pressure,
                    fatigue=server_fatigue,
                    detail="Serve forces a direct point",
                )
            )
            return PointSimulationResult(server.player_id, events, rally_length)

        events.append(
            ShotEvent(
                point_number=point_state.point_number,
                shot_number=shot_number,
                score_before=point_state.score_before,
                striker_id=server.player_id,
                receiver_id=receiver.player_id,
                shot_kind=ShotKind.SERVE,
                shot_hand=ShotHand.NONE,
                quality=serve_quality,
                outcome=ShotOutcome.CONTINUE,
                spin_type=serve_spin,
                serve_number=serve_number,
                serve_direction=serve_direction,
                pressure=server_pressure,
                fatigue=server_fatigue,
                detail="Serve lands in play",
            )
        )
        rally_length += 1
        shot_number += 1

        stats[receiver.player_id].total_shots += 1
        return_hand = self._groundstroke_hand(receiver, server, rng, bias=0.48)
        return_spin, return_spin_intensity = self._choose_rally_spin(
            receiver,
            ShotKind.RETURN,
            return_hand,
            rng,
        )
        return_in = self._return_in_probability(
            receiver,
            server,
            surface,
            tuning,
            serve_threat,
            serve_direction,
            serve_spin,
            first_serve=serve_number == 1,
            fatigue=receiver_fatigue,
            pressure=receiver_pressure,
        )
        if rng.random() > return_in:
            stats[server.player_id].forced_errors_drawn += 1
            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=receiver.player_id,
                    receiver_id=server.player_id,
                    shot_kind=ShotKind.RETURN,
                    shot_hand=return_hand,
                    quality=RallyQuality.DEFENSIVE,
                    outcome=ShotOutcome.FORCED_ERROR,
                    spin_type=return_spin,
                    pressure=receiver_pressure,
                    fatigue=receiver_fatigue,
                    detail="Return misses under serve pressure",
                )
            )
            return PointSimulationResult(server.player_id, events, rally_length)

        return_quality = self._quality_band(0.54 + _n(receiver.skills.return_quality) - serve_threat * 0.25)
        return_winner = self._return_winner_probability(
            receiver,
            server,
            serve_number == 1,
            serve_direction,
            serve_spin,
        )
        if rng.random() < return_winner:
            stats[receiver.player_id].return_winners += 1
            rally_length += 1
            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=receiver.player_id,
                    receiver_id=server.player_id,
                    shot_kind=ShotKind.RETURN,
                    shot_hand=return_hand,
                    quality=RallyQuality.FINISHING,
                    outcome=ShotOutcome.RETURN_WINNER,
                    spin_type=return_spin,
                    pressure=receiver_pressure,
                    fatigue=receiver_fatigue,
                    detail="Aggressive return winner",
                )
            )
            return PointSimulationResult(receiver.player_id, events, rally_length)

        events.append(
            ShotEvent(
                point_number=point_state.point_number,
                shot_number=shot_number,
                score_before=point_state.score_before,
                striker_id=receiver.player_id,
                receiver_id=server.player_id,
                shot_kind=ShotKind.RETURN,
                shot_hand=return_hand,
                quality=return_quality,
                outcome=ShotOutcome.CONTINUE,
                spin_type=return_spin,
                pressure=receiver_pressure,
                fatigue=receiver_fatigue,
                detail="Return neutralizes the serve",
            )
        )
        rally_length += 1
        shot_number += 1

        attacker = server
        defender = receiver
        incoming_pressure = _clamp(max(serve_threat, 0.0) * 0.22, 0.0, 0.25)
        incoming_spin_type = return_spin
        incoming_spin_intensity = return_spin_intensity
        net_player_id: str | None = None

        while shot_number <= 40:
            attacker_fatigue = self._fatigue(stats[attacker.player_id], attacker)
            defender_fatigue = self._fatigue(stats[defender.player_id], defender)
            attacker_pressure = self._pressure(point_state, attacker.player_id)

            shot_kind, shot_hand = self._select_rally_shot(
                attacker,
                defender,
                incoming_pressure,
                net_player_id,
                rng,
            )
            shot_spin, shot_spin_intensity = self._choose_rally_spin(
                attacker,
                shot_kind,
                shot_hand,
                rng,
            )
            stats[attacker.player_id].total_shots += 1
            quality, outcome, next_pressure = self._resolve_rally_shot(
                attacker,
                defender,
                surface,
                tuning,
                shot_kind,
                shot_hand,
                shot_spin,
                shot_spin_intensity,
                incoming_pressure,
                incoming_spin_type,
                incoming_spin_intensity,
                attacker_fatigue,
                defender_fatigue,
                attacker_pressure,
                net_player_id,
                rng,
            )

            events.append(
                ShotEvent(
                    point_number=point_state.point_number,
                    shot_number=shot_number,
                    score_before=point_state.score_before,
                    striker_id=attacker.player_id,
                    receiver_id=defender.player_id,
                    shot_kind=shot_kind,
                    shot_hand=shot_hand,
                    quality=quality,
                    outcome=outcome,
                    spin_type=shot_spin,
                    pressure=attacker_pressure,
                    fatigue=attacker_fatigue,
                )
            )

            if outcome == ShotOutcome.WINNER:
                stats[attacker.player_id].winners += 1
                rally_length += 1
                return PointSimulationResult(attacker.player_id, events, rally_length)

            if outcome == ShotOutcome.FORCED_ERROR:
                stats[attacker.player_id].forced_errors_drawn += 1
                rally_length += 1
                return PointSimulationResult(attacker.player_id, events, rally_length)

            if outcome == ShotOutcome.UNFORCED_ERROR:
                stats[attacker.player_id].unforced_errors += 1
                rally_length += 1
                return PointSimulationResult(defender.player_id, events, rally_length)

            rally_length += 1

            if shot_kind == ShotKind.APPROACH:
                net_player_id = attacker.player_id
            elif shot_kind == ShotKind.LOB:
                net_player_id = None

            incoming_pressure = next_pressure
            incoming_spin_type = shot_spin
            incoming_spin_intensity = shot_spin_intensity
            attacker, defender = defender, attacker
            shot_number += 1

        # Fail-safe for very long points.
        server_edge = _n(server.skills.rally_tolerance) + _n(server.skills.stamina) - self._fatigue(
            stats[server.player_id], server
        )
        receiver_edge = _n(receiver.skills.rally_tolerance) + _n(receiver.skills.stamina) - self._fatigue(
            stats[receiver.player_id], receiver
        )
        if server_edge >= receiver_edge:
            stats[server.player_id].forced_errors_drawn += 1
            winner_id = server.player_id
        else:
            stats[receiver.player_id].forced_errors_drawn += 1
            winner_id = receiver.player_id
        winner = server if winner_id == server.player_id else receiver
        loser = receiver if winner_id == server.player_id else server
        stats[winner.player_id].total_shots += 1
        winner_hand = (
            ShotHand.FOREHAND
            if winner.skills.forehand_quality >= winner.skills.backhand_quality
            else ShotHand.BACKHAND
        )
        events.append(
            ShotEvent(
                point_number=point_state.point_number,
                shot_number=shot_number,
                score_before=point_state.score_before,
                striker_id=winner.player_id,
                receiver_id=loser.player_id,
                shot_kind=ShotKind.DRIVE,
                shot_hand=winner_hand,
                quality=RallyQuality.AGGRESSIVE,
                outcome=ShotOutcome.FORCED_ERROR,
                spin_type=incoming_spin_type,
                pressure=self._pressure(point_state, winner.player_id),
                fatigue=self._fatigue(stats[winner.player_id], winner),
                detail="Extended rally breaks down under pressure",
            )
        )
        rally_length += 1
        return PointSimulationResult(winner_id, events, rally_length)

    def _pressure(self, point_state: PointState, player_id: str) -> float:
        pressure = point_state.pressure_index / 100.0
        if pressure >= 1.0:
            return 1.0

        if point_state.break_point_for is not None:
            if player_id == point_state.server_id:
                pressure += 0.06
            elif point_state.break_point_for == player_id:
                pressure += 0.02

        if point_state.set_point_for is not None:
            if point_state.set_point_for == player_id:
                pressure += 0.02
            else:
                pressure += 0.05

        if point_state.match_point_for is not None:
            if point_state.match_point_for == player_id:
                pressure += 0.03
            else:
                pressure += 0.08

        return _clamp(pressure, 0.0, 1.0)

    def _pressure_resilience(self, player: PlayerProfile) -> float:
        return _n(player.skills.pressure_handling) * 0.68 + _n(player.skills.composure) * 0.32

    def _pressure_penalty_rate(
        self,
        player: PlayerProfile,
        pressure: float,
        base_penalty: float,
        minimum_penalty: float,
    ) -> float:
        resilience = self._pressure_resilience(player)
        adjusted_penalty = base_penalty * (1.0 - 0.72 * resilience)
        return pressure * max(minimum_penalty, adjusted_penalty)

    def _fatigue(self, stats: PlayerMatchStats, player: PlayerProfile) -> float:
        endurance = (
            player.skills.stamina + player.physical.durability + player.physical.peak_condition
        ) / 300.0
        load = stats.points_played * 0.0018 + stats.total_shots * 0.0009
        return _clamp(load * (1.25 - endurance), 0.0, 0.20)

    def _surface_comfort_delta(self, player: PlayerProfile, surface: Surface) -> float:
        return (player.surface_profile.comfort(surface) - 50) / 100.0

    def _choose_serve_direction(
        self,
        server: PlayerProfile,
        receiver: PlayerProfile,
        rng: random.Random,
        serve_number: int,
    ) -> ServeDirection:
        preferred = server.tactics.preferred_serve_direction
        preferred_weight = 0.56
        if preferred == ServeDirection.WIDE and server.handedness != receiver.handedness:
            preferred_weight += 0.06
        if preferred == ServeDirection.T and server.handedness == receiver.handedness:
            preferred_weight += 0.04
        if serve_number == 2 and server.spin.serve_spin >= 65:
            preferred_weight += 0.03 if preferred != ServeDirection.T else -0.02
        if rng.random() < _clamp(preferred_weight, 0.40, 0.78):
            return preferred

        alternatives = [direction for direction in ServeDirection if direction != preferred]
        if serve_number == 2 and server.spin.serve_spin >= 65:
            if ServeDirection.BODY in alternatives and rng.random() < 0.45:
                return ServeDirection.BODY
            if ServeDirection.WIDE in alternatives and rng.random() < 0.35:
                return ServeDirection.WIDE
        return rng.choice(alternatives)

    def _choose_serve_spin(
        self,
        server: PlayerProfile,
        serve_direction: ServeDirection,
        serve_number: int,
        rng: random.Random,
    ) -> SpinType:
        spin_bias = _n(server.spin.serve_spin)
        if serve_number == 2:
            if rng.random() < 0.46 + spin_bias * 0.30:
                return SpinType.KICK
            if serve_direction == ServeDirection.WIDE and rng.random() < 0.18 + spin_bias * 0.14:
                return SpinType.SLICE
            return SpinType.FLAT

        if serve_direction == ServeDirection.WIDE and rng.random() < 0.24 + spin_bias * 0.26:
            return SpinType.SLICE
        if rng.random() < 0.42 - spin_bias * 0.10 + _n(server.skills.serve_power) * 0.10:
            return SpinType.FLAT
        if rng.random() < 0.16 + spin_bias * 0.12:
            return SpinType.KICK
        return SpinType.SLICE

    def _first_serve_in_probability(
        self,
        server: PlayerProfile,
        surface: Surface,
        fatigue: float,
        pressure: float,
        tuning: SurfaceTuning,
        serve_spin: SpinType,
    ) -> float:
        serve_accuracy = _n(server.skills.serve_accuracy)
        comfort = self._surface_comfort_delta(server, surface)
        return _clamp(
            0.47
            + 0.24 * serve_accuracy
            + 0.04 * _n(server.skills.composure)
            + 0.05 * _n(server.skills.pressure_handling)
            + tuning.serve_in_adjustment
            + comfort * 0.03
            + self._serve_spin_in_modifier(serve_spin, serve_number=1, surface=surface)
            - fatigue * 0.18
            - self._pressure_penalty_rate(server, pressure, base_penalty=0.10, minimum_penalty=0.02),
            0.43,
            0.78,
        )

    def _second_serve_in_probability(
        self,
        server: PlayerProfile,
        surface: Surface,
        fatigue: float,
        pressure: float,
        tuning: SurfaceTuning,
        serve_spin: SpinType,
    ) -> float:
        reliability = _n(server.skills.second_serve_reliability)
        return _clamp(
            0.71
            + 0.18 * reliability
            + 0.04 * _n(server.skills.serve_accuracy)
            + 0.02 * _n(server.skills.pressure_handling)
            + tuning.serve_in_adjustment * 0.5
            + self._surface_comfort_delta(server, surface) * 0.02
            + self._serve_spin_in_modifier(serve_spin, serve_number=2, surface=surface)
            - fatigue * 0.10
            - self._pressure_penalty_rate(server, pressure, base_penalty=0.14, minimum_penalty=0.03),
            0.68,
            0.95,
        )

    def _serve_threat(
        self,
        server: PlayerProfile,
        receiver: PlayerProfile,
        surface: Surface,
        tuning: SurfaceTuning,
        *,
        serve_direction: ServeDirection,
        serve_spin: SpinType,
        first_serve: bool,
        server_fatigue: float,
        receiver_fatigue: float,
    ) -> float:
        threat = (
            0.44 * _n(server.skills.serve_power)
            + 0.18 * _n(server.skills.serve_accuracy)
            + 0.10 * _n(server.tactics.baseline_aggression)
            + 0.08 * self._surface_comfort_delta(server, surface)
            + tuning.serve_boost
            + self._directional_serve_bonus(server, receiver, serve_direction, serve_spin)
            + self._serve_spin_threat_modifier(serve_spin, surface)
            - 0.22 * _n(receiver.skills.return_quality)
            - 0.10 * _n(receiver.skills.anticipation)
            - server_fatigue * 0.22
            + receiver_fatigue * 0.10
        )
        if not first_serve:
            threat -= 0.06
        return _clamp(threat, -0.10, 0.55)

    def _ace_probability(
        self,
        server: PlayerProfile,
        serve_threat: float,
        serve_number: int,
        pressure: float,
        tuning: SurfaceTuning,
        serve_spin: SpinType,
        serve_direction: ServeDirection,
    ) -> float:
        ace = 0.005 + max(serve_threat, 0.0) * 0.16 + max(tuning.serve_boost, 0.0) * 0.20
        if serve_spin == SpinType.FLAT:
            ace += 0.018
        elif serve_spin == SpinType.SLICE:
            ace += 0.010 if serve_direction == ServeDirection.WIDE else 0.004
        elif serve_spin == SpinType.KICK:
            ace -= 0.006
        if serve_number == 2:
            ace *= 0.45
        ace -= self._pressure_penalty_rate(server, pressure, base_penalty=0.03, minimum_penalty=0.004)
        return _clamp(ace, 0.0, 0.18)

    def _service_winner_probability(
        self,
        serve_threat: float,
        serve_number: int,
        serve_spin: SpinType,
        serve_direction: ServeDirection,
    ) -> float:
        winner = 0.025 + max(serve_threat, 0.0) * 0.11
        if serve_spin == SpinType.SLICE and serve_direction == ServeDirection.WIDE:
            winner += 0.012
        if serve_spin == SpinType.KICK:
            winner += 0.005
        if serve_number == 2:
            winner *= 0.80
        return _clamp(winner, 0.01, 0.20)

    def _return_in_probability(
        self,
        receiver: PlayerProfile,
        server: PlayerProfile,
        surface: Surface,
        tuning: SurfaceTuning,
        serve_threat: float,
        serve_direction: ServeDirection,
        serve_spin: SpinType,
        *,
        first_serve: bool,
        fatigue: float,
        pressure: float,
    ) -> float:
        targeted_backhand = self._serve_targets_backhand(server, receiver, serve_direction)
        backhand_penalty = 0.0
        if targeted_backhand and receiver.backhand_hands == 1 and serve_spin in (SpinType.KICK, SpinType.SLICE):
            backhand_penalty += 0.025
        if serve_direction == ServeDirection.WIDE and server.handedness != receiver.handedness:
            backhand_penalty += 0.012
        return _clamp(
            0.54
            + 0.22 * _n(receiver.skills.return_quality)
            + 0.06 * _n(receiver.skills.anticipation)
            + 0.04 * _n(receiver.skills.movement)
            + 0.03 * _n(receiver.skills.pressure_handling)
            + tuning.return_boost
            - max(serve_threat, 0.0) * (0.18 if first_serve else 0.10)
            - backhand_penalty
            - fatigue * 0.12
            - self._pressure_penalty_rate(
                receiver,
                pressure,
                base_penalty=0.05,
                minimum_penalty=0.01,
            )
            + self._surface_comfort_delta(receiver, surface) * 0.03,
            0.35,
            0.96,
        )

    def _return_winner_probability(
        self,
        receiver: PlayerProfile,
        server: PlayerProfile,
        first_serve: bool,
        serve_direction: ServeDirection,
        serve_spin: SpinType,
    ) -> float:
        bonus = 0.0 if first_serve else 0.015
        if serve_direction == ServeDirection.BODY and receiver.backhand_hands == 2:
            bonus += 0.004
        if serve_spin == SpinType.FLAT:
            bonus += 0.004
        if serve_spin == SpinType.KICK and receiver.backhand_hands == 1:
            bonus -= 0.006
        return _clamp(
            0.004
            + max(_n(receiver.skills.return_quality) - _n(server.skills.serve_power), 0.0) * 0.05
            + _n(receiver.tactics.baseline_aggression) * 0.02
            + bonus,
            0.0,
            0.08,
        )

    def _select_rally_shot(
        self,
        attacker: PlayerProfile,
        defender: PlayerProfile,
        incoming_pressure: float,
        net_player_id: str | None,
        rng: random.Random,
    ) -> tuple[ShotKind, ShotHand]:
        if attacker.player_id == net_player_id:
            kind = ShotKind.SMASH if incoming_pressure > 0.28 and rng.random() < 0.18 else ShotKind.VOLLEY
            hand = ShotHand.FOREHAND if rng.random() < 0.60 else ShotHand.BACKHAND
            return kind, hand

        if net_player_id == defender.player_id and incoming_pressure > 0.16 and rng.random() < 0.20:
            return ShotKind.LOB, self._groundstroke_hand(attacker, defender, rng, bias=0.40)

        aggression = _n(attacker.tactics.baseline_aggression)
        attack = _n(attacker.tactics.short_ball_attack)
        net_frequency = _n(attacker.tactics.net_frequency)
        slice_bias = _n(attacker.spin.slice_frequency) * 0.10 + (0.08 if attacker.backhand_hands == 1 else 0.0)
        roll = rng.random()
        approach_cutoff = 0.10 + incoming_pressure * 0.12 + net_frequency * 0.10 + attack * 0.04
        if attacker.backhand_hands == 1:
            approach_cutoff += 0.03
        if roll < approach_cutoff:
            return ShotKind.APPROACH, self._groundstroke_hand(attacker, defender, rng, bias=0.54)

        slice_cutoff = approach_cutoff + 0.08 + slice_bias - aggression * 0.03
        if roll < slice_cutoff:
            return ShotKind.SLICE, ShotHand.BACKHAND
        return ShotKind.DRIVE, self._groundstroke_hand(attacker, defender, rng, bias=0.52)

    def _groundstroke_hand(
        self,
        player: PlayerProfile,
        defender: PlayerProfile,
        rng: random.Random,
        bias: float,
    ) -> ShotHand:
        forehand_bias = _clamp(
            bias
            + (player.skills.forehand_quality - player.skills.backhand_quality) / 250.0
            + (0.03 if player.backhand_hands == 1 else 0.0)
            + (
                0.03
                if player.handedness != defender.handedness
                and player.skills.forehand_quality >= player.skills.backhand_quality
                else 0.0
            ),
            0.35,
            0.70,
        )
        return ShotHand.FOREHAND if rng.random() < forehand_bias else ShotHand.BACKHAND

    def _choose_rally_spin(
        self,
        player: PlayerProfile,
        shot_kind: ShotKind,
        shot_hand: ShotHand,
        rng: random.Random,
    ) -> tuple[SpinType, float]:
        if shot_kind == ShotKind.SLICE:
            return SpinType.SLICE, self._spin_intensity(player, SpinType.SLICE, ShotHand.BACKHAND)
        if shot_kind == ShotKind.LOB:
            return SpinType.TOPSPIN, self._spin_intensity(player, SpinType.TOPSPIN, shot_hand)
        if shot_kind in (ShotKind.VOLLEY, ShotKind.SMASH):
            return SpinType.FLAT, self._spin_intensity(player, SpinType.FLAT, shot_hand)
        if shot_kind == ShotKind.APPROACH and shot_hand == ShotHand.BACKHAND:
            if player.backhand_hands == 1 or rng.random() < 0.22 + _n(player.spin.slice_frequency) * 0.18:
                return SpinType.SLICE, self._spin_intensity(player, SpinType.SLICE, shot_hand)

        wing_spin = player.spin.forehand_spin if shot_hand == ShotHand.FOREHAND else player.spin.backhand_spin
        if shot_hand == ShotHand.BACKHAND and player.backhand_hands == 1:
            if rng.random() < 0.18 + _n(player.spin.slice_frequency) * 0.20:
                return SpinType.SLICE, self._spin_intensity(player, SpinType.SLICE, shot_hand)

        if rng.random() < 0.34 + _n(wing_spin) * 0.40:
            return SpinType.TOPSPIN, self._spin_intensity(player, SpinType.TOPSPIN, shot_hand)
        return SpinType.FLAT, self._spin_intensity(player, SpinType.FLAT, shot_hand)

    def _resolve_rally_shot(
        self,
        attacker: PlayerProfile,
        defender: PlayerProfile,
        surface: Surface,
        tuning: SurfaceTuning,
        shot_kind: ShotKind,
        shot_hand: ShotHand,
        shot_spin: SpinType,
        shot_spin_intensity: float,
        incoming_pressure: float,
        incoming_spin_type: SpinType,
        incoming_spin_intensity: float,
        attacker_fatigue: float,
        defender_fatigue: float,
        attacker_pressure: float,
        net_player_id: str | None,
        rng: random.Random,
    ) -> tuple[RallyQuality, ShotOutcome, float]:
        shot_skill = self._shot_skill(attacker, shot_kind, shot_hand)
        target_backhand = self._targets_backhand(attacker, defender, shot_hand)
        intent = (
            0.32 * _n(attacker.tactics.baseline_aggression)
            + 0.20 * _n(attacker.tactics.short_ball_attack)
            + 0.12 * max(incoming_pressure, 0.0)
        )
        if shot_kind in (ShotKind.APPROACH, ShotKind.VOLLEY, ShotKind.SMASH):
            intent += 0.18
        if shot_kind == ShotKind.SLICE:
            intent -= 0.05
        if shot_spin == SpinType.FLAT:
            intent += 0.04
        elif shot_spin == SpinType.TOPSPIN:
            intent += 0.01 + shot_spin_intensity * 0.02
        elif shot_spin == SpinType.SLICE:
            intent -= 0.02

        comfort = self._surface_comfort_delta(attacker, surface)
        defense = (
            0.40 * _n(defender.skills.movement)
            + 0.26 * _n(defender.skills.anticipation)
            + 0.18 * _n(defender.skills.rally_tolerance)
            + tuning.movement_bonus
            + self._surface_comfort_delta(defender, surface) * 0.08
            + self._defender_backhand_modifier(defender, target_backhand, shot_spin, shot_spin_intensity)
            - defender_fatigue * 0.18
        )
        execution = (
            0.46 * shot_skill
            + 0.14 * _n(attacker.skills.movement)
            + 0.12 * _n(attacker.skills.anticipation)
            + 0.12 * _n(attacker.skills.rally_tolerance)
            + comfort * 0.10
            + intent * 0.14
            + self._attacker_spin_modifier(
                attacker,
                shot_kind,
                shot_hand,
                shot_spin,
                shot_spin_intensity,
                incoming_spin_type,
                incoming_spin_intensity,
                surface,
            )
            - attacker_fatigue * 0.26
            - incoming_pressure * 0.10
            - self._pressure_penalty_rate(
                attacker,
                attacker_pressure,
                base_penalty=0.08,
                minimum_penalty=0.02,
            )
        )

        edge = execution - defense
        quality = self._quality_band(execution + intent * 0.25 + tuning.rally_extension * 0.2)
        winner_probability = 0.01 + max(edge, 0.0) * 0.18 + max(intent - 0.45, 0.0) * 0.08
        forced_error_probability = 0.015 + max(edge, 0.0) * 0.11 + max(incoming_pressure, 0.0) * 0.08
        unforced_error_probability = (
            0.024
            + max(intent - execution, 0.0) * 0.12
            + max(0.58 - shot_skill, 0.0) * 0.09
            + self._pressure_penalty_rate(
                attacker,
                attacker_pressure,
                base_penalty=0.05,
                minimum_penalty=0.01,
            )
        )

        if shot_kind in (ShotKind.VOLLEY, ShotKind.SMASH):
            winner_probability += 0.03
        if shot_kind == ShotKind.LOB and net_player_id == defender.player_id:
            winner_probability += 0.02
        if shot_kind == ShotKind.SLICE:
            unforced_error_probability -= 0.01
        if shot_spin == SpinType.FLAT:
            winner_probability += 0.02
            unforced_error_probability += 0.02
        elif shot_spin == SpinType.TOPSPIN:
            forced_error_probability += 0.01 + shot_spin_intensity * 0.02
            unforced_error_probability -= 0.01
        elif shot_spin == SpinType.SLICE:
            forced_error_probability += 0.01
            unforced_error_probability -= 0.012

        winner_probability = _clamp(winner_probability, 0.01, 0.45)
        forced_error_probability = _clamp(forced_error_probability, 0.01, 0.35)
        unforced_error_probability = _clamp(unforced_error_probability, 0.01, 0.32)

        total_terminal = winner_probability + forced_error_probability + unforced_error_probability
        if total_terminal > 0.82:
            scale = 0.82 / total_terminal
            winner_probability *= scale
            forced_error_probability *= scale
            unforced_error_probability *= scale

        roll = rng.random()
        if roll < winner_probability:
            return quality, ShotOutcome.WINNER, 0.0
        if roll < winner_probability + forced_error_probability:
            return quality, ShotOutcome.FORCED_ERROR, 0.0
        if roll < winner_probability + forced_error_probability + unforced_error_probability:
            return quality, ShotOutcome.UNFORCED_ERROR, 0.0

        next_pressure = _clamp(
            0.04
            + max(edge, -0.1) * 0.35
            + max(intent, 0.0) * 0.14
            + max(tuning.rally_extension, 0.0) * 0.10,
            -0.05,
            0.45,
        )
        return quality, ShotOutcome.CONTINUE, next_pressure

    def _shot_skill(self, player: PlayerProfile, shot_kind: ShotKind, shot_hand: ShotHand) -> float:
        if shot_kind in (ShotKind.VOLLEY, ShotKind.SMASH):
            return _n(player.skills.net_play) * 0.80 + _n(player.skills.forehand_quality) * 0.20
        if shot_kind == ShotKind.LOB:
            return (
                _n(player.skills.forehand_quality)
                + _n(player.skills.backhand_quality)
                + _n(player.skills.composure)
            ) / 3
        if shot_kind == ShotKind.SLICE:
            base = (_n(player.skills.backhand_quality) * 0.70) + (_n(player.skills.rally_tolerance) * 0.30)
            if player.backhand_hands == 1:
                base += 0.04
            base += _n(player.spin.slice_frequency) * 0.03
            return _clamp(base, 0.0, 1.0)
        if shot_hand == ShotHand.FOREHAND:
            return _n(player.skills.forehand_quality)
        base = _n(player.skills.backhand_quality)
        base += 0.02 if player.backhand_hands == 2 else -0.01
        return _clamp(base, 0.0, 1.0)

    def _serve_spin_in_modifier(
        self,
        serve_spin: SpinType,
        serve_number: int,
        surface: Surface,
    ) -> float:
        if serve_spin == SpinType.FLAT:
            return -0.012 if serve_number == 1 else -0.030
        if serve_spin == SpinType.SLICE:
            return 0.003 if surface == Surface.GRASS else -0.002
        if serve_spin == SpinType.KICK:
            return 0.010 if serve_number == 1 else 0.030 + (0.010 if surface == Surface.CLAY else 0.0)
        return 0.0

    def _serve_spin_threat_modifier(self, serve_spin: SpinType, surface: Surface) -> float:
        if serve_spin == SpinType.FLAT:
            return 0.03
        if serve_spin == SpinType.SLICE:
            return 0.02 + (0.01 if surface == Surface.GRASS else 0.0)
        if serve_spin == SpinType.KICK:
            return -0.006 + (0.02 if surface == Surface.CLAY else 0.0)
        return 0.0

    def _directional_serve_bonus(
        self,
        server: PlayerProfile,
        receiver: PlayerProfile,
        serve_direction: ServeDirection,
        serve_spin: SpinType,
    ) -> float:
        bonus = 0.0
        if serve_direction == ServeDirection.WIDE:
            bonus += 0.03 if server.handedness != receiver.handedness else 0.015
            if serve_spin == SpinType.SLICE:
                bonus += 0.02
        elif serve_direction == ServeDirection.T:
            bonus += 0.02 if server.handedness == receiver.handedness else 0.01
            if serve_spin == SpinType.FLAT:
                bonus += 0.01
        else:
            bonus += 0.012
            if receiver.backhand_hands == 1:
                bonus += 0.008
            if serve_spin == SpinType.KICK:
                bonus += 0.006
        if self._serve_targets_backhand(server, receiver, serve_direction):
            if receiver.backhand_hands == 1 and serve_spin in (SpinType.SLICE, SpinType.KICK):
                bonus += 0.010
        return bonus

    def _serve_targets_backhand(
        self,
        server: PlayerProfile,
        receiver: PlayerProfile,
        serve_direction: ServeDirection,
    ) -> bool:
        if serve_direction == ServeDirection.BODY:
            return receiver.backhand_hands == 1
        if serve_direction == ServeDirection.WIDE:
            return server.handedness != receiver.handedness
        return server.handedness == receiver.handedness

    def _targets_backhand(
        self,
        attacker: PlayerProfile,
        defender: PlayerProfile,
        shot_hand: ShotHand,
    ) -> bool:
        if shot_hand == ShotHand.NONE:
            return False
        if shot_hand == ShotHand.FOREHAND:
            return attacker.handedness != defender.handedness
        return attacker.handedness == defender.handedness

    def _spin_intensity(
        self,
        player: PlayerProfile,
        spin_type: SpinType,
        shot_hand: ShotHand,
    ) -> float:
        if spin_type == SpinType.KICK:
            source = player.spin.serve_spin
        elif spin_type == SpinType.SLICE:
            source = max(
                player.spin.slice_frequency,
                player.spin.backhand_spin if shot_hand == ShotHand.BACKHAND else 45,
            )
        elif spin_type == SpinType.TOPSPIN:
            source = player.spin.forehand_spin if shot_hand == ShotHand.FOREHAND else player.spin.backhand_spin
        else:
            wing_spin = player.spin.forehand_spin if shot_hand == ShotHand.FOREHAND else player.spin.backhand_spin
            source = max(30, 100 - int(wing_spin * 0.55))
        return _clamp(source / 100.0, 0.25, 1.0)

    def _attacker_spin_modifier(
        self,
        attacker: PlayerProfile,
        shot_kind: ShotKind,
        shot_hand: ShotHand,
        shot_spin: SpinType,
        shot_spin_intensity: float,
        incoming_spin_type: SpinType,
        incoming_spin_intensity: float,
        surface: Surface,
    ) -> float:
        modifier = 0.0
        if shot_spin == SpinType.TOPSPIN:
            modifier += 0.015 + shot_spin_intensity * 0.03
            if surface == Surface.CLAY:
                modifier += 0.015
        elif shot_spin == SpinType.SLICE:
            modifier += 0.010 + _n(attacker.spin.slice_frequency) * 0.02
        elif shot_spin == SpinType.FLAT:
            modifier += 0.006
        elif shot_spin == SpinType.KICK:
            modifier += 0.010 + shot_spin_intensity * 0.02

        if shot_hand == ShotHand.BACKHAND:
            if attacker.backhand_hands == 1:
                if shot_spin == SpinType.SLICE:
                    modifier += 0.03
                elif shot_spin == SpinType.TOPSPIN:
                    modifier -= 0.018
                if incoming_spin_type in (SpinType.TOPSPIN, SpinType.KICK):
                    modifier -= 0.045 * incoming_spin_intensity
            else:
                modifier += 0.015
                if incoming_spin_type in (SpinType.TOPSPIN, SpinType.KICK):
                    modifier += 0.010 * incoming_spin_intensity

        if shot_kind == ShotKind.APPROACH and attacker.backhand_hands == 1:
            modifier += 0.010

        return modifier

    def _defender_backhand_modifier(
        self,
        defender: PlayerProfile,
        target_backhand: bool,
        shot_spin: SpinType,
        shot_spin_intensity: float,
    ) -> float:
        if not target_backhand:
            return 0.0
        if defender.backhand_hands == 1:
            if shot_spin in (SpinType.TOPSPIN, SpinType.KICK):
                return -0.045 * shot_spin_intensity
            if shot_spin == SpinType.SLICE and _n(defender.spin.slice_frequency) >= 0.60:
                return 0.008
            return -0.004
        if shot_spin in (SpinType.TOPSPIN, SpinType.KICK):
            return 0.012 * shot_spin_intensity
        return 0.0

    def _quality_band(self, value: float) -> RallyQuality:
        if value >= 0.86:
            return RallyQuality.FINISHING
        if value >= 0.72:
            return RallyQuality.AGGRESSIVE
        if value >= 0.56:
            return RallyQuality.NEUTRAL
        return RallyQuality.DEFENSIVE
