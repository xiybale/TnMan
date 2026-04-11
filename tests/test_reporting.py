from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.models import MatchConfig, Surface
from tennis_pro_manager.reporting import format_batch_report, format_match_report
from tennis_pro_manager.roster import load_roster
from tennis_pro_manager.simulator import MatchSimulator


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roster = load_roster()
        cls.simulator = MatchSimulator(cls.roster)

    def test_match_report_includes_pattern_summary(self) -> None:
        result = self.simulator.simulate_match(
            "rafael-nadal",
            "stefanos-tsitsipas",
            MatchConfig(surface=Surface.CLAY, best_of_sets=3, seed=33),
        )
        report = format_match_report(result, self.roster, shot_limit=5)

        self.assertIn("Pattern Summary", report)
        self.assertIn("Rally bands:", report)
        self.assertIn("serve mix:", report)
        self.assertIn("targeting:", report)

    def test_batch_report_includes_extended_metrics(self) -> None:
        summary = self.simulator.simulate_batch(
            "hubert-hurkacz",
            "novak-djokovic",
            MatchConfig(surface=Surface.GRASS, best_of_sets=3, seed=90),
            iterations=6,
        )
        report = format_batch_report(summary, self.roster)

        self.assertIn("Rally bands:", report)
        self.assertIn("break", report)
        self.assertIn("svc pts won", report)
        self.assertIn("ret pts won", report)
        self.assertIn("df on 2nd serve", report)


if __name__ == "__main__":
    unittest.main()
