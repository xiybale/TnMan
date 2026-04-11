from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class CliTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "tpm.py", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_inspect_player_command(self) -> None:
        result = self._run("inspect-player", "jannik-sinner")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Jannik Sinner", result.stdout)
        self.assertIn("pressure handling", result.stdout)
        self.assertIn("Spin Profile", result.stdout)
        self.assertIn("Surface Comfort", result.stdout)

    def test_simulate_match_command(self) -> None:
        result = self._run(
            "simulate-match",
            "novak-djokovic",
            "carlos-alcaraz",
            "--surface",
            "hard",
            "--seed",
            "11",
            "--shots",
            "5",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Tennis Pro Manager Match Report", result.stdout)
        self.assertIn("Shot Log Preview", result.stdout)

    def test_simulate_batch_command(self) -> None:
        result = self._run(
            "simulate-batch",
            "hubert-hurkacz",
            "casper-ruud",
            "--surface",
            "grass",
            "--iterations",
            "5",
            "--seed",
            "5",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Tennis Pro Manager Batch Report", result.stdout)
        self.assertIn("Win Rates", result.stdout)

    def test_calibrate_command(self) -> None:
        result = self._run(
            "calibrate",
            "--config",
            str(FIXTURES / "calibration_scenarios.json"),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Tennis Pro Manager Calibration Report", result.stdout)
        self.assertIn("quick-smoke", result.stdout)
        self.assertIn("[PASS]", result.stdout)


if __name__ == "__main__":
    unittest.main()
