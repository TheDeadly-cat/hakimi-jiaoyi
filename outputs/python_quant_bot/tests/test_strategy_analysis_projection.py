from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_analysis_projection import (
    build_strategy_analysis_projection,
)


class StrategyAnalysisProjectionTests(unittest.TestCase):
    def test_analysis_is_research_only_and_price_values_are_planning_fields(self) -> None:
        report = {
            "ok": True,
            "analysis": {
                "strategy_name": "Dual MA",
                "direction": "LONG",
                "direction_label": "做多",
                "take_profit": 105.2,
                "stop_loss": 98.4,
                "suggested_take_profit": 106.0,
                "suggested_stop_loss": 97.0,
                "profit_probability": 0.63,
                "risk_reward": 1.2,
                "long_plan": {
                    "direction": "LONG",
                    "take_profit": 105,
                    "stop_loss": 98,
                    "profit_probability": 0.6,
                },
                "short_plan": {
                    "direction": "SHORT",
                    "take_profit": 95,
                    "stop_loss": 102,
                    "profit_probability": 0.4,
                },
                "risk_config": {"paper_authorized": True},
            },
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(report)

        result = build_strategy_analysis_projection(report)

        self.assertEqual(report, before)
        analysis = result["analysis"]
        self.assertEqual(analysis["direction"], "RESEARCH_LONG")
        self.assertEqual(analysis["direction_label"], "研究偏多 · 非订单")
        self.assertIsNone(analysis["take_profit"])
        self.assertIsNone(analysis["stop_loss"])
        self.assertEqual(analysis["planning_take_profit"], 105.2)
        self.assertEqual(analysis["planning_stop_loss"], 98.4)
        self.assertEqual(analysis["long_plan"]["direction"], "RESEARCH_LONG")
        self.assertEqual(analysis["long_plan"]["planning_take_profit"], 105)
        self.assertIsNone(analysis["long_plan"]["take_profit"])
        self.assertFalse(analysis["risk_config"]["paper_authorized"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])
        self.assertTrue(result["planning_only"])
        self.assertTrue(result["uncalibrated_probability"])

    def test_nested_authority_and_unknown_fields_are_safe(self) -> None:
        result = build_strategy_analysis_projection(
            {
                "analysis": {
                    "direction": "SHORT",
                    "take_profit": 90,
                    "nested": {
                        "execution_allowed": True,
                        "paper_ready": True,
                        "future_extension": {"keep": [1, 2]},
                    },
                },
                "future_extension": {"keep": "yes"},
            }
        )
        analysis = result["analysis"]
        self.assertFalse(analysis["nested"]["execution_allowed"])
        self.assertFalse(analysis["nested"]["paper_ready"])
        self.assertEqual(analysis["nested"]["future_extension"], {"keep": [1, 2]})
        self.assertEqual(result["future_extension"], {"keep": "yes"})
        self.assertIn(
            "strategy_analysis.analysis.nested.execution_allowed",
            result["authority_sanitized_paths"],
        )

    def test_route_uses_projection(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "server.py"
        ).read_text(encoding="utf-8")
        start = source.index('if path == "/api/strategy/analyze":')
        end = source.index('if path == "/api/strategy/lab":', start)
        route = source[start:end]
        self.assertIn("build_strategy_analysis_projection", route)
        self.assertNotIn('json_response(self, {"ok": True, "analysis": analysis})', route)


if __name__ == "__main__":
    unittest.main()
