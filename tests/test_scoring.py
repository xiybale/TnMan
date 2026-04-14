from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.scoring import ScoreTracker


class ScoreTrackerTests(unittest.TestCase):
    def test_pressure_index_ladder_tracks_server_risk_before_break_point(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=3, initial_server="a")

        tracker.point_won_by("b")
        tracker.point_won_by("b")
        zero_thirty = tracker.snapshot(3)
        self.assertEqual(zero_thirty.point_score, "0-30")
        self.assertEqual(zero_thirty.pressure_index, 50)
        self.assertEqual(zero_thirty.pressure_label, "elevated")

        tracker.point_won_by("a")
        fifteen_thirty = tracker.snapshot(4)
        self.assertEqual(fifteen_thirty.point_score, "15-30")
        self.assertEqual(fifteen_thirty.pressure_index, 54)
        self.assertEqual(fifteen_thirty.pressure_label, "elevated")

        tracker.point_won_by("a")
        thirty_all = tracker.snapshot(5)
        self.assertEqual(thirty_all.point_score, "30-30")
        self.assertEqual(thirty_all.pressure_index, 58)
        self.assertEqual(thirty_all.pressure_label, "elevated")

        tracker.point_won_by("b")
        break_point = tracker.snapshot(6)
        self.assertEqual(break_point.point_score, "30-40")
        self.assertEqual(break_point.break_point_for, "b")
        self.assertEqual(break_point.pressure_index, 88)
        self.assertEqual(break_point.pressure_label, "high")

    def test_triple_break_point_is_higher_than_single_break_point(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=3, initial_server="a")
        tracker.current_points = {"a": 0, "b": 3}

        break_point = tracker.snapshot(1)

        self.assertEqual(break_point.point_score, "0-40")
        self.assertEqual(break_point.break_point_for, "b")
        self.assertEqual(break_point.pressure_index, 94)
        self.assertEqual(break_point.pressure_label, "high")

    def test_set_point_and_match_point_are_maximum_pressure(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=3, initial_server="a")
        tracker.current_games = {"a": 4, "b": 5}
        tracker.current_game_server = "b"
        tracker.current_points = {"a": 2, "b": 3}

        set_point = tracker.snapshot(1)
        self.assertEqual(set_point.set_point_for, "b")
        self.assertEqual(set_point.pressure_index, 100)
        self.assertEqual(set_point.pressure_label, "maximum")

        tracker.sets_won = {"a": 0, "b": 1}
        match_point = tracker.snapshot(1)
        self.assertEqual(match_point.match_point_for, "b")
        self.assertEqual(match_point.pressure_index, 100)
        self.assertEqual(match_point.pressure_label, "maximum")

    def test_deuce_game_requires_two_point_margin(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=3, initial_server="a")
        for winner in ["a", "a", "a", "b", "b", "b"]:
            tracker.point_won_by(winner)

        self.assertEqual(tracker.snapshot(7).point_score, "Deuce")

        first_advantage = tracker.point_won_by("a")
        self.assertFalse(first_advantage.game_completed)
        self.assertEqual(tracker.snapshot(8).point_score, "Ad server")

        reset_to_deuce = tracker.point_won_by("b")
        self.assertFalse(reset_to_deuce.game_completed)
        self.assertEqual(tracker.snapshot(9).point_score, "Deuce")

        tracker.point_won_by("a")
        game_point = tracker.point_won_by("a")
        self.assertTrue(game_point.game_completed)
        self.assertEqual(tracker.current_games["a"], 1)

    def test_tiebreak_serving_order_follows_tennis_rotation(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=3, initial_server="a")

        for _ in range(12):
            current_server = tracker.current_server()
            for _ in range(4):
                tracker.point_won_by(current_server)

        self.assertTrue(tracker.in_tiebreak)

        servers = []
        for _ in range(6):
            servers.append(tracker.current_server())
            tracker.point_won_by(tracker.current_server())

        self.assertEqual(servers, ["a", "b", "b", "a", "a", "b"])

    def test_best_of_five_match_stops_after_three_sets(self) -> None:
        tracker = ScoreTracker("a", "b", best_of_sets=5, initial_server="a")

        while not tracker.is_match_over:
            tracker.point_won_by("a")

        self.assertEqual(tracker.sets_won["a"], 3)
        self.assertEqual(tracker.scoreline(), "6-0 6-0 6-0")


if __name__ == "__main__":
    unittest.main()
