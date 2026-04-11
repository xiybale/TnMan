from __future__ import annotations

import statistics
import unittest

from tennis_pro_manager.models import Handedness
from tennis_pro_manager.roster import load_roster


class RosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roster = load_roster()

    def test_roster_contains_at_least_one_hundred_players(self) -> None:
        self.assertGreaterEqual(len(self.roster), 100)

    def test_current_top_hundred_examples_exist(self) -> None:
        for player_id in (
            "learner-tien",
            "rafael-jodar",
            "jacob-fearnley",
            "camilo-ugo-carabelli",
            "giovanni-mpetshi-perricard",
        ):
            self.assertIn(player_id, self.roster)

    def test_handedness_and_backhand_flags_are_available(self) -> None:
        self.assertEqual(self.roster["jack-draper"].handedness, Handedness.LEFT)
        self.assertEqual(self.roster["denis-shapovalov"].backhand_hands, 1)
        self.assertEqual(self.roster["stefanos-tsitsipas"].backhand_hands, 1)
        self.assertEqual(self.roster["rafael-jodar"].handedness, Handedness.RIGHT)

    def test_auto_generated_profiles_are_scaled_for_top_hundred_context(self) -> None:
        auto_players = [
            player
            for player in self.roster.values()
            if player.derived_stats.source_notes
            and player.derived_stats.source_notes[0].startswith("ATP top-100 snapshot")
        ]

        flattened = []
        for player in auto_players:
            flattened.extend(
                [
                    player.skills.serve_power,
                    player.skills.serve_accuracy,
                    player.skills.second_serve_reliability,
                    player.skills.return_quality,
                    player.skills.forehand_quality,
                    player.skills.backhand_quality,
                    player.skills.movement,
                    player.skills.anticipation,
                    player.skills.rally_tolerance,
                    player.skills.net_play,
                    player.skills.composure,
                    player.skills.pressure_handling,
                    player.skills.stamina,
                ]
            )

        self.assertGreaterEqual(statistics.median(flattened), 76)
        self.assertGreaterEqual(min(flattened), 60)
        self.assertGreaterEqual(
            sum(value >= 70 for value in flattened) / len(flattened),
            0.9,
        )


if __name__ == "__main__":
    unittest.main()
