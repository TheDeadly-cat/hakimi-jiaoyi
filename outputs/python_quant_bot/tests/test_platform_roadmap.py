from __future__ import annotations

import unittest

from exchange_terminal.services.platform_roadmap import build_six_lane_roadmap


class PlatformRoadmapTests(unittest.TestCase):
    def test_strategy_doctor_distinguishes_existing_evidence_from_future_wfo(self) -> None:
        roadmap = build_six_lane_roadmap(
            [{"id": "strategy_lab", "maturity": 80}],
            {"score": 80},
            {"score": 80, "counts": {"online": 1}},
            {"live_trading_hard_block": True},
            now_ms=lambda: 1,
        )

        lane = next(
            item for item in roadmap["lanes"]
            if item["id"] == "freqtrade_dry_run_doctor"
        )
        landed = " ".join(lane["landed"])
        next_steps = " ".join(lane["next"])
        gaps = " ".join(lane["gaps"])

        self.assertIn("Fixed-parameter chronological slices", landed)
        self.assertIn("Configured, stress and severe fee/slippage evidence", landed)
        self.assertIn("Preregister a rolling-refit walk-forward contract", next_steps)
        self.assertIn("observed venue schedules and liquidity-depth evidence", next_steps)
        self.assertIn("not rolling-refit WFO", gaps)
        self.assertIn("modeled costs do not prove realized execution costs", gaps)
        self.assertNotIn("Add walk-forward validation.", lane["next"])
        self.assertNotIn("Add fee/slippage sensitivity bands.", lane["next"])
        self.assertIn("Live trading remains hard-blocked", roadmap["safety"])


if __name__ == "__main__":
    unittest.main()
