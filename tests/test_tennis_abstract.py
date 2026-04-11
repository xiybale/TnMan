from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tennis_pro_manager.tennis_abstract import (
    charting_player_slug,
    charting_player_url,
    parse_charting_page,
    player_id_from_name,
)


class TennisAbstractTests(unittest.TestCase):
    def test_name_helpers_match_project_conventions(self) -> None:
        self.assertEqual(charting_player_slug("Alexander Bublik"), "AlexanderBublik")
        self.assertEqual(charting_player_slug("Joao Fonseca"), "JoaoFonseca")
        self.assertEqual(player_id_from_name("Joao Fonseca"), "joao-fonseca")
        self.assertEqual(
            charting_player_url("Hubert Hurkacz"),
            "https://www.tennisabstract.com/charting/HubertHurkacz.html",
        )

    def test_parse_charting_page_extracts_core_metrics(self) -> None:
        page_html = """
        <html><body>
        <p>It comprises shot-by-shot records of <a href="#">108 matches</a>.</p>
        <script>
        var serve = '<table><tr><td align="left">All Serves</td><td align="right">1000</td><td align="right"><span>650  (65%)</span></td><td align="right"><span>120  (12%)</span></td><td align="right"><span>10  (1%)</span></td><td align="right"><span>140  (14%)</span></td><td align="right"><span>360  (36%)</span></td><td align="right"><span>410  (41%)</span></td><td align="right"><span>190  (19%)</span></td><td align="right"><span>400  (40%)</span></td></tr><tr><td align="left">First Serves</td><td align="right">620</td><td align="right"><span>470  (76%)</span></td><td align="right"><span>110  (18%)</span></td><td align="right"><span>9  (1%)</span></td><td align="right"><span>110  (18%)</span></td><td align="right"><span>330  (53%)</span></td><td align="right"><span>300  (48%)</span></td><td align="right"><span>60  (10%)</span></td><td align="right"><span>260  (42%)</span></td></tr><tr><td align="left">Second Serves</td><td align="right">380</td><td align="right"><span>190  (50%)</span></td><td align="right"><span>10  (3%)</span></td><td align="right"><span>1  (0%)</span></td><td align="right"><span>20  (5%)</span></td><td align="right"><span>70  (18%)</span></td><td align="right"><span>110  (29%)</span></td><td align="right"><span>120  (32%)</span></td><td align="right"><span>150  (39%)</span></td></tr></table>';
        var return1 = '<table><tr><td align="left">Total</td><td align="right">980</td><td align="right"><span>360  (37%)</span></td><td align="right"><span>700  (71%)</span></td><td align="right"><span>310  (44%)</span></td><td align="right"><span>650  (93%)</span></td><td align="right"><span>320  (49%)</span></td><td align="right"><span>20  (2%)</span></td><td align="left">3.7</td></tr></table>';
        var netpts1 = '<table><tr><td align="left">All Net Approaches</td><td align="right">120</td><td align="right"><span>82  (68%)</span></td><td align="right"><span>25  (21%)</span></td><td align="right"><span>18  (15%)</span></td><td align="right"><span>8  (7%)</span></td><td align="right"><span>10  (8%)</span></td><td align="right"><span>4  (3%)</span></td><td align="left">4.9</td></tr></table>';
        </script>
        </body></html>
        """

        snapshot = parse_charting_page(
            page_html,
            player_name="Alexander Bublik",
            source_url="https://www.tennisabstract.com/charting/AlexanderBublik.html",
            fetched_at="2026-04-10",
        )

        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.player_id, "alexander-bublik")
        self.assertEqual(snapshot.charted_matches, 108)
        self.assertAlmostEqual(snapshot.first_serve_in, 0.62)
        self.assertAlmostEqual(snapshot.first_serve_points_won, 0.76)
        self.assertAlmostEqual(snapshot.second_serve_points_won, 0.50)
        self.assertAlmostEqual(snapshot.ace_rate, 0.12)
        self.assertAlmostEqual(snapshot.return_points_won, 0.37)
        self.assertEqual(snapshot.preferred_serve_direction, "wide")
        self.assertAlmostEqual(snapshot.net_approach_rate, 120 / 1980)
        self.assertAlmostEqual(snapshot.net_points_won or 0.0, 0.68)


if __name__ == "__main__":
    unittest.main()
