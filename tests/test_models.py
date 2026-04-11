from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.models import PlayerMatchStats


class PlayerMatchStatsTests(unittest.TestCase):
    def test_double_fault_rates_use_separate_denominators(self) -> None:
        stats = PlayerMatchStats(
            service_points_played=100,
            second_serve_attempts=28,
            double_faults=4,
        )

        self.assertAlmostEqual(stats.double_fault_rate(), 0.04)
        self.assertAlmostEqual(stats.second_serve_double_fault_rate(), 4 / 28)


if __name__ == "__main__":
    unittest.main()
