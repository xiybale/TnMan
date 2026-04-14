from __future__ import annotations

from dataclasses import dataclass

from .models import CompletedSet, PointState

POINT_LABELS = {0: "0", 1: "15", 2: "30", 3: "40"}


@dataclass(slots=True)
class ScoreUpdate:
    game_completed: bool = False
    set_completed: bool = False
    match_completed: bool = False
    game_winner_id: str | None = None
    set_winner_id: str | None = None
    match_winner_id: str | None = None
    completed_set: CompletedSet | None = None


class ScoreTracker:
    def __init__(self, player_one_id: str, player_two_id: str, best_of_sets: int, initial_server: str):
        if best_of_sets not in (3, 5):
            raise ValueError("best_of_sets must be 3 or 5")
        if initial_server not in (player_one_id, player_two_id):
            raise ValueError("initial_server must be one of the match players")

        self.players = (player_one_id, player_two_id)
        self.best_of_sets = best_of_sets
        self.current_game_server = initial_server
        self.current_games = {player_one_id: 0, player_two_id: 0}
        self.current_points = {player_one_id: 0, player_two_id: 0}
        self.sets_won = {player_one_id: 0, player_two_id: 0}
        self.completed_sets: list[CompletedSet] = []
        self.in_tiebreak = False
        self.match_winner_id: str | None = None

    @property
    def sets_to_win(self) -> int:
        return self.best_of_sets // 2 + 1

    @property
    def is_match_over(self) -> bool:
        return self.match_winner_id is not None

    def other(self, player_id: str) -> str:
        return self.players[1] if player_id == self.players[0] else self.players[0]

    def current_server(self) -> str:
        if not self.in_tiebreak:
            return self.current_game_server
        points_played = sum(self.current_points.values())
        if points_played == 0:
            return self.current_game_server
        block = (points_played - 1) // 2
        return self.other(self.current_game_server) if block % 2 == 0 else self.current_game_server

    def current_receiver(self) -> str:
        return self.other(self.current_server())

    def current_game_score_text(self) -> tuple[str, str]:
        server_id = self.current_server()
        receiver_id = self.current_receiver()
        server_points = self.current_points[server_id]
        receiver_points = self.current_points[receiver_id]

        if self.in_tiebreak:
            return str(server_points), str(receiver_points)

        if server_points >= 3 and receiver_points >= 3:
            if server_points == receiver_points:
                return "40", "40"
            if server_points == receiver_points + 1:
                return "AD", "40"
            return "40", "AD"

        return POINT_LABELS[server_points], POINT_LABELS[receiver_points]

    def current_point_score_label(self) -> str:
        if self.in_tiebreak:
            return f"TB {self.current_points[self.players[0]]}-{self.current_points[self.players[1]]}"

        server_id = self.current_server()
        receiver_id = self.current_receiver()
        server_points = self.current_points[server_id]
        receiver_points = self.current_points[receiver_id]

        if server_points >= 3 and receiver_points >= 3:
            if server_points == receiver_points:
                return "Deuce"
            if server_points == receiver_points + 1:
                return "Ad server"
            return "Ad receiver"

        server_label, receiver_label = self.current_game_score_text()
        return f"{server_label}-{receiver_label}"

    def _would_win_regular_game(self, player_id: str) -> bool:
        prospective = dict(self.current_points)
        prospective[player_id] += 1
        opponent_id = self.other(player_id)
        return prospective[player_id] >= 4 and prospective[player_id] - prospective[opponent_id] >= 2

    def _would_win_tiebreak(self, player_id: str) -> bool:
        prospective = dict(self.current_points)
        prospective[player_id] += 1
        opponent_id = self.other(player_id)
        return prospective[player_id] >= 7 and prospective[player_id] - prospective[opponent_id] >= 2

    def _would_win_current_game(self, player_id: str) -> bool:
        if self.in_tiebreak:
            return self._would_win_tiebreak(player_id)
        return self._would_win_regular_game(player_id)

    def _would_win_current_set(self, player_id: str) -> bool:
        if not self._would_win_current_game(player_id):
            return False
        if self.in_tiebreak:
            return True
        prospective_games = dict(self.current_games)
        prospective_games[player_id] += 1
        opponent_id = self.other(player_id)
        return prospective_games[player_id] >= 6 and prospective_games[player_id] - prospective_games[
            opponent_id
        ] >= 2

    def _would_win_match(self, player_id: str) -> bool:
        if not self._would_win_current_set(player_id):
            return False
        return self.sets_won[player_id] + 1 >= self.sets_to_win

    def snapshot(self, point_number: int) -> PointState:
        server_id = self.current_server()
        receiver_id = self.current_receiver()
        server_display, receiver_display = self.current_game_score_text()
        server_points = self.current_points[server_id]
        receiver_points = self.current_points[receiver_id]

        break_point_for = None
        if not self.in_tiebreak and self._would_win_current_game(receiver_id):
            break_point_for = receiver_id

        set_point_for = None
        for player_id in self.players:
            if self._would_win_current_set(player_id):
                set_point_for = player_id
                break

        match_point_for = None
        for player_id in self.players:
            if self._would_win_match(player_id):
                match_point_for = player_id
                break

        is_deuce = (
            not self.in_tiebreak and server_points >= 3 and receiver_points >= 3 and server_points == receiver_points
        )

        score_before = (
            f"{self.current_games[self.players[0]]}-{self.current_games[self.players[1]]}"
            f" | {self.current_point_score_label()}"
        )
        pressure_index = self._pressure_index(
            server_display=server_display,
            receiver_display=receiver_display,
            server_points=server_points,
            receiver_points=receiver_points,
            is_tiebreak=self.in_tiebreak,
            is_deuce=is_deuce,
            break_point_for=break_point_for,
            set_point_for=set_point_for,
            match_point_for=match_point_for,
        )

        return PointState(
            point_number=point_number,
            server_id=server_id,
            receiver_id=receiver_id,
            sets_won=dict(self.sets_won),
            games=dict(self.current_games),
            server_points=server_points,
            receiver_points=receiver_points,
            server_display=server_display,
            receiver_display=receiver_display,
            point_score=self.current_point_score_label(),
            score_before=score_before,
            is_tiebreak=self.in_tiebreak,
            is_deuce=is_deuce,
            break_point_for=break_point_for,
            set_point_for=set_point_for,
            match_point_for=match_point_for,
            pressure_index=pressure_index,
            pressure_label=self._pressure_label(pressure_index),
        )

    def _pressure_index(
        self,
        *,
        server_display: str,
        receiver_display: str,
        server_points: int,
        receiver_points: int,
        is_tiebreak: bool,
        is_deuce: bool,
        break_point_for: str | None,
        set_point_for: str | None,
        match_point_for: str | None,
    ) -> int:
        if match_point_for is not None or set_point_for is not None:
            return 100

        pressure = 18
        if is_tiebreak:
            total_points = server_points + receiver_points
            pressure = max(pressure, min(90, 46 + total_points * 4))
            if abs(server_points - receiver_points) <= 1:
                pressure = min(95, pressure + 6)

        pressure = max(
            pressure,
            self._server_risk_pressure(
                server_points=server_points,
                receiver_points=receiver_points,
                is_deuce=is_deuce,
            ),
        )
        if break_point_for is not None:
            pressure = max(
                pressure,
                self._break_point_pressure(
                    server_points=server_points,
                    receiver_points=receiver_points,
                ),
            )

        return pressure

    def _server_risk_pressure(
        self,
        *,
        server_points: int,
        receiver_points: int,
        is_deuce: bool,
    ) -> int:
        if is_deuce:
            return 64

        # Losing the current point would create break-point pressure on the next ball.
        if receiver_points == 2 and server_points <= 2:
            return {
                0: 50,  # 0-30
                1: 54,  # 15-30
                2: 58,  # 30-30
            }[server_points]

        return 18

    def _break_point_pressure(
        self,
        *,
        server_points: int,
        receiver_points: int,
    ) -> int:
        if server_points >= 3 and receiver_points > server_points:
            return 90  # Ad receiver
        if receiver_points >= 3 and server_points < 3:
            return {
                0: 94,  # 0-40
                1: 91,  # 15-40
                2: 88,  # 30-40
            }[server_points]
        return 88

    def _pressure_label(self, pressure_index: int) -> str:
        if pressure_index >= 100:
            return "maximum"
        if pressure_index >= 75:
            return "high"
        if pressure_index >= 50:
            return "elevated"
        return "routine"

    def point_won_by(self, winner_id: str) -> ScoreUpdate:
        if self.is_match_over:
            raise RuntimeError("Match already completed")
        if winner_id not in self.players:
            raise ValueError("Unknown player")

        if self.in_tiebreak:
            return self._register_tiebreak_point(winner_id)
        return self._register_regular_point(winner_id)

    def _register_regular_point(self, winner_id: str) -> ScoreUpdate:
        game_server = self.current_game_server
        update = ScoreUpdate()
        self.current_points[winner_id] += 1

        if not self._would_have_regular_game_won():
            return update

        self.current_games[winner_id] += 1
        update.game_completed = True
        update.game_winner_id = winner_id
        self.current_points = {player_id: 0 for player_id in self.players}

        opponent_id = self.other(winner_id)
        if self.current_games[winner_id] >= 6 and self.current_games[winner_id] - self.current_games[opponent_id] >= 2:
            completed_set = CompletedSet(games=dict(self.current_games))
            return self._close_set(winner_id, completed_set, next_server=self.other(game_server), update=update)

        if self.current_games[self.players[0]] == 6 and self.current_games[self.players[1]] == 6:
            self.in_tiebreak = True
            self.current_game_server = self.other(game_server)
            return update

        self.current_game_server = self.other(game_server)
        return update

    def _would_have_regular_game_won(self) -> bool:
        player_one, player_two = self.players
        points_one = self.current_points[player_one]
        points_two = self.current_points[player_two]
        return (points_one >= 4 or points_two >= 4) and abs(points_one - points_two) >= 2

    def _register_tiebreak_point(self, winner_id: str) -> ScoreUpdate:
        update = ScoreUpdate()
        tiebreak_first_server = self.current_game_server
        self.current_points[winner_id] += 1
        opponent_id = self.other(winner_id)

        if self.current_points[winner_id] < 7 or self.current_points[winner_id] - self.current_points[opponent_id] < 2:
            return update

        final_games = {
            winner_id: 7,
            opponent_id: 6,
        }
        completed_set = CompletedSet(games=final_games, tiebreak_points=dict(self.current_points))
        return self._close_set(
            winner_id,
            completed_set,
            next_server=self.other(tiebreak_first_server),
            update=update,
        )

    def _close_set(
        self,
        winner_id: str,
        completed_set: CompletedSet,
        next_server: str,
        update: ScoreUpdate,
    ) -> ScoreUpdate:
        self.completed_sets.append(completed_set)
        self.sets_won[winner_id] += 1
        self.current_games = {player_id: 0 for player_id in self.players}
        self.current_points = {player_id: 0 for player_id in self.players}
        self.in_tiebreak = False
        self.current_game_server = next_server

        update.set_completed = True
        update.set_winner_id = winner_id
        update.completed_set = completed_set

        if self.sets_won[winner_id] >= self.sets_to_win:
            self.match_winner_id = winner_id
            update.match_completed = True
            update.match_winner_id = winner_id

        return update

    def scoreline(self) -> str:
        if not self.completed_sets:
            return ""
        return " ".join(
            completed_set.score_for(self.players[0], self.players[1])
            for completed_set in self.completed_sets
        )
