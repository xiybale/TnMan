from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.models import MatchConfig, Surface
from tennis_pro_manager.roster import load_roster
from tennis_pro_manager.simulator import MatchSimulator
from tennis_pro_manager.web_payloads import (
    build_compare_payload,
    build_match_report_payload,
    build_player_directory_payload,
)


class WebPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roster = load_roster()
        cls.simulator = MatchSimulator(cls.roster)

    def test_match_results_include_point_records(self) -> None:
        result = self.simulator.simulate_match(
            "novak-djokovic",
            "carlos-alcaraz",
            MatchConfig(surface=Surface.HARD, best_of_sets=3, seed=21),
        )

        self.assertEqual(len(result.points), result.total_points)
        self.assertTrue(all(point.events for point in result.points))

    def test_match_report_payload_contains_set_and_game_timeline(self) -> None:
        result = self.simulator.simulate_match(
            "jannik-sinner",
            "carlos-alcaraz",
            MatchConfig(surface=Surface.HARD, best_of_sets=3, seed=12),
        )
        payload = build_match_report_payload(result, self.roster)

        self.assertIn("meta", payload)
        self.assertIn("sets", payload)
        self.assertTrue(payload["sets"])
        first_set = payload["sets"][0]
        self.assertIn("gamesTimeline", first_set)
        self.assertTrue(first_set["gamesTimeline"])
        first_game = first_set["gamesTimeline"][0]
        self.assertIn("points", first_game)
        self.assertTrue(first_game["points"])
        self.assertIn("shots", first_game["points"][0])

    def test_set_stats_roll_up_to_match_totals(self) -> None:
        result = self.simulator.simulate_match(
            "novak-djokovic",
            "hubert-hurkacz",
            MatchConfig(surface=Surface.GRASS, best_of_sets=3, seed=31),
        )
        payload = build_match_report_payload(result, self.roster)

        for player_id in result.players:
            match_stats = payload["matchStats"][player_id]
            rolled_up = {
                "totalPointsWon": 0,
                "servicePointsPlayed": 0,
                "aces": 0,
                "doubleFaults": 0,
                "totalShots": 0,
            }
            for set_payload in payload["sets"]:
                set_stats = set_payload["stats"][player_id]
                for field_name in rolled_up:
                    rolled_up[field_name] += set_stats[field_name]

            self.assertEqual(rolled_up["totalPointsWon"], match_stats["totalPointsWon"])
            self.assertEqual(
                rolled_up["servicePointsPlayed"],
                match_stats["servicePointsPlayed"],
            )
            self.assertEqual(rolled_up["aces"], match_stats["aces"])
            self.assertEqual(rolled_up["doubleFaults"], match_stats["doubleFaults"])
            self.assertEqual(rolled_up["totalShots"], match_stats["totalShots"])

    def test_compare_payload_includes_edges_and_tags(self) -> None:
        payload = build_compare_payload(
            self.roster["rafael-nadal"],
            self.roster["stefanos-tsitsipas"],
            surface=Surface.CLAY,
        )

        self.assertIn("surfaceEdge", payload)
        self.assertIn("skillDeltas", payload)
        self.assertTrue(payload["skillDeltas"])
        self.assertIn("matchupTags", payload)

    def test_player_directory_payload_supports_query(self) -> None:
        payload = build_player_directory_payload(self.roster, query="djoko", surface=Surface.HARD)

        self.assertEqual(len(payload["players"]), 1)
        self.assertEqual(payload["players"][0]["playerId"], "novak-djokovic")


if __name__ == "__main__":
    unittest.main()
