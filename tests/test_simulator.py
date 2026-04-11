from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.models import Handedness, MatchConfig, PlayerProfile, SpinType, Surface
from tennis_pro_manager.roster import load_roster
from tennis_pro_manager.simulator import SURFACE_TUNING, MatchSimulator


class SimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roster = load_roster()
        cls.simulator = MatchSimulator(cls.roster)

    def _clone_player(self, base_id: str, new_id: str, **updates: object) -> PlayerProfile:
        payload = deepcopy(self.roster[base_id].to_dict())
        payload["player_id"] = new_id
        payload["name"] = str(updates.pop("name", payload["name"]))

        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(payload.get(key), dict):
                payload[key].update(value)
            else:
                payload[key] = value

        return PlayerProfile.from_dict(payload)

    def test_match_simulation_is_deterministic_for_same_seed(self) -> None:
        config = MatchConfig(surface=Surface.HARD, best_of_sets=3, seed=17)
        first = self.simulator.simulate_match("novak-djokovic", "jannik-sinner", config)
        second = self.simulator.simulate_match("novak-djokovic", "jannik-sinner", config)

        self.assertEqual(first.winner_id, second.winner_id)
        self.assertEqual(first.scoreline, second.scoreline)
        self.assertEqual(
            [(event.shot_kind, event.outcome) for event in first.shot_log[:20]],
            [(event.shot_kind, event.outcome) for event in second.shot_log[:20]],
        )

    def test_match_stats_reconcile(self) -> None:
        config = MatchConfig(surface=Surface.CLAY, best_of_sets=3, seed=9)
        result = self.simulator.simulate_match("carlos-alcaraz", "casper-ruud", config)
        alcaraz = result.stats["carlos-alcaraz"]
        ruud = result.stats["casper-ruud"]

        self.assertGreater(result.total_points, 0)
        self.assertEqual(result.total_points, alcaraz.total_points_won + ruud.total_points_won)
        self.assertEqual(alcaraz.service_points_played, ruud.return_points_played)
        self.assertEqual(ruud.service_points_played, alcaraz.return_points_played)
        self.assertTrue(result.scoreline)

    def test_big_server_profile_is_more_effective_on_grass_than_clay(self) -> None:
        grass = self.simulator.simulate_batch(
            "hubert-hurkacz",
            "novak-djokovic",
            MatchConfig(surface=Surface.GRASS, best_of_sets=3, seed=100),
            iterations=30,
        )
        clay = self.simulator.simulate_batch(
            "hubert-hurkacz",
            "novak-djokovic",
            MatchConfig(surface=Surface.CLAY, best_of_sets=3, seed=100),
            iterations=30,
        )

        self.assertGreater(grass.hold_rate["hubert-hurkacz"], clay.hold_rate["hubert-hurkacz"])
        self.assertGreater(grass.ace_rate["hubert-hurkacz"], clay.ace_rate["hubert-hurkacz"])

    def test_clay_specialist_gains_value_on_clay(self) -> None:
        clay = self.simulator.simulate_batch(
            "casper-ruud",
            "hubert-hurkacz",
            MatchConfig(surface=Surface.CLAY, best_of_sets=3, seed=200),
            iterations=30,
        )
        grass = self.simulator.simulate_batch(
            "casper-ruud",
            "hubert-hurkacz",
            MatchConfig(surface=Surface.GRASS, best_of_sets=3, seed=200),
            iterations=30,
        )

        self.assertGreater(clay.win_rate("casper-ruud"), grass.win_rate("casper-ruud"))

    def test_bublik_hurkacz_hard_is_competitive(self) -> None:
        summary = self.simulator.simulate_batch(
            "alexander-bublik",
            "hubert-hurkacz",
            MatchConfig(surface=Surface.HARD, best_of_sets=3, seed=6),
            iterations=60,
        )

        self.assertGreater(summary.win_rate("alexander-bublik"), 0.15)
        self.assertLess(summary.win_rate("alexander-bublik"), 0.85)
        self.assertGreater(summary.first_serve_in_rate["alexander-bublik"], 0.62)
        self.assertGreater(summary.first_serve_in_rate["hubert-hurkacz"], 0.62)

    def test_left_handed_server_gets_matchup_value(self) -> None:
        righty_hurkacz = self._clone_player(
            "hubert-hurkacz",
            "righty-hurkacz",
            name="Righty Hurkacz",
            handedness=Handedness.RIGHT.value,
        )
        lefty_hurkacz = self._clone_player(
            "hubert-hurkacz",
            "lefty-hurkacz",
            name="Lefty Hurkacz",
            handedness=Handedness.LEFT.value,
        )
        local_roster = {
            **self.roster,
            righty_hurkacz.player_id: righty_hurkacz,
            lefty_hurkacz.player_id: lefty_hurkacz,
        }
        simulator = MatchSimulator(local_roster)
        righty_bonus = simulator._directional_serve_bonus(  # noqa: SLF001
            righty_hurkacz,
            self.roster["novak-djokovic"],
            righty_hurkacz.tactics.preferred_serve_direction,
            SpinType.SLICE,
        )
        lefty_bonus = simulator._directional_serve_bonus(  # noqa: SLF001
            lefty_hurkacz,
            self.roster["novak-djokovic"],
            lefty_hurkacz.tactics.preferred_serve_direction,
            SpinType.SLICE,
        )

        self.assertGreater(lefty_bonus, righty_bonus)

    def test_one_handed_backhand_is_more_vulnerable_to_heavy_spin(self) -> None:
        one_hander = self._clone_player(
            "stefanos-tsitsipas",
            "one-handed-test",
            name="One Hander Test",
            backhand_hands=1,
        )
        two_hander = self._clone_player(
            "stefanos-tsitsipas",
            "two-handed-test",
            name="Two Hander Test",
            backhand_hands=2,
        )
        local_roster = {
            **self.roster,
            one_hander.player_id: one_hander,
            two_hander.player_id: two_hander,
        }
        simulator = MatchSimulator(local_roster)
        one_hand_modifier = simulator._defender_backhand_modifier(  # noqa: SLF001
            one_hander,
            True,
            SpinType.TOPSPIN,
            1.0,
        )
        two_hand_modifier = simulator._defender_backhand_modifier(  # noqa: SLF001
            two_hander,
            True,
            SpinType.TOPSPIN,
            1.0,
        )

        self.assertLess(one_hand_modifier, two_hand_modifier)

    def test_spin_types_appear_in_shot_log(self) -> None:
        result = self.simulator.simulate_match(
            "rafael-nadal",
            "stefanos-tsitsipas",
            MatchConfig(surface=Surface.CLAY, best_of_sets=3, seed=33),
        )
        spin_types = {event.spin_type for event in result.shot_log}

        self.assertIn(SpinType.TOPSPIN, spin_types)
        self.assertTrue(spin_types.intersection({SpinType.SLICE, SpinType.KICK}))

    def test_pressure_handling_reduces_big_point_execution_penalty(self) -> None:
        low_pressure = self._clone_player(
            "novak-djokovic",
            "low-pressure-test",
            name="Low Pressure Test",
            skills={"pressure_handling": 10, "composure": 50},
        )
        high_pressure = self._clone_player(
            "novak-djokovic",
            "high-pressure-test",
            name="High Pressure Test",
            skills={"pressure_handling": 90, "composure": 50},
        )

        low_probability = self.simulator._first_serve_in_probability(  # noqa: SLF001
            low_pressure,
            Surface.HARD,
            fatigue=0.0,
            pressure=1.0,
            tuning=SURFACE_TUNING[Surface.HARD],
            serve_spin=SpinType.FLAT,
        )
        high_probability = self.simulator._first_serve_in_probability(  # noqa: SLF001
            high_pressure,
            Surface.HARD,
            fatigue=0.0,
            pressure=1.0,
            tuning=SURFACE_TUNING[Surface.HARD],
            serve_spin=SpinType.FLAT,
        )

        self.assertGreater(high_probability, low_probability)


if __name__ == "__main__":
    unittest.main()
