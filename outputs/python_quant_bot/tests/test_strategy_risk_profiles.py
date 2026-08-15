from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.strategy_risk_profiles import strategy_research_risk_profile


class StrategyRiskProfileTests(unittest.TestCase):
    def test_trend_profile_keeps_the_right_tail_open(self) -> None:
        profile = strategy_research_risk_profile("turtle", {
            "position_pct": 35,
            "take_profit_pct": 8,
            "stop_loss_pct": 4,
            "fee_rate": 0.0005,
            "slippage_bps": 2,
        })

        self.assertEqual(profile["profile_id"], "TREND_STRUCTURE_EXIT")
        self.assertEqual(profile["risk"]["take_profit_pct"], 0.0)
        self.assertEqual(profile["risk"]["stop_loss_pct"], 8.0)
        self.assertEqual(profile["risk"]["leverage"], 1.0)

    def test_trend_pullback_uses_the_same_bounded_research_profile(self) -> None:
        profile = strategy_research_risk_profile("trend_pullback", {
            "position_pct": 20,
            "take_profit_pct": 6,
            "stop_loss_pct": 4,
            "fee_rate": 0.0005,
            "slippage_bps": 2,
        })

        self.assertEqual(profile["profile_id"], "TREND_STRUCTURE_EXIT")
        self.assertEqual(profile["risk"]["position_pct"], 20.0)
        self.assertEqual(profile["risk"]["take_profit_pct"], 0.0)
        self.assertEqual(profile["risk"]["stop_loss_pct"], 8.0)
        self.assertEqual(profile["risk"]["leverage"], 1.0)

    def test_squeeze_breakout_keeps_structure_exit_and_emergency_stop(self) -> None:
        profile = strategy_research_risk_profile("squeeze_breakout", {"position_pct": 20})

        self.assertEqual(profile["profile_id"], "TREND_STRUCTURE_EXIT")
        self.assertEqual(profile["risk"]["take_profit_pct"], 0.0)
        self.assertEqual(profile["risk"]["stop_loss_pct"], 8.0)

    def test_mean_reversion_profile_remains_bounded(self) -> None:
        profile = strategy_research_risk_profile("bollinger", {"position_pct": 35})

        self.assertEqual(profile["profile_id"], "MEAN_REVERSION_BOUNDED_EXIT")
        self.assertEqual(profile["risk"]["take_profit_pct"], 6.0)
        self.assertEqual(profile["risk"]["stop_loss_pct"], 4.0)

    def test_risk_hash_is_deterministic_and_strategy_bound(self) -> None:
        first = strategy_research_risk_profile("turtle", {"position_pct": 35})
        second = strategy_research_risk_profile("turtle", {"position_pct": 35})
        other = strategy_research_risk_profile("rsi", {"position_pct": 35})

        self.assertEqual(first["risk_hash"], second["risk_hash"])
        self.assertNotEqual(first["risk_hash"], other["risk_hash"])


if __name__ == "__main__":
    unittest.main()
