from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.market_ai_projection import build_market_ai_projection


class MarketAiProjectionTests(unittest.TestCase):
    def test_ai_direction_and_price_plans_are_descriptive(self) -> None:
        report = {
            "ok": True,
            "symbol": "BTC-USDT",
            "analysis": {
                "deepseek": {
                    "preferred_direction": "LONG",
                    "long_win_rate_pct": 64,
                    "short_win_rate_pct": 36,
                    "long_take_profit": 105,
                    "long_stop_loss": 98,
                    "safe_action": "仅模拟盘验证",
                    "paper_authorized": True,
                },
                "gpt": {
                    "final_decision": "WAIT",
                    "long_win_rate_pct": 52,
                    "short_win_rate_pct": 48,
                    "short_take_profit": 95,
                    "short_stop_loss": 102,
                },
            },
            "local": {
                "preferred": "SHORT",
                "long_plan": {"direction": "LONG", "take_profit": 105, "stop_loss": 98},
                "short_plan": {"direction": "SHORT", "take_profit": 95, "stop_loss": 102},
            },
            "live_order_allowed": True,
        }
        before = deepcopy(report)

        result = build_market_ai_projection(report)

        self.assertEqual(report, before)
        deepseek = result["analysis"]["deepseek"]
        self.assertEqual(deepseek["preferred_direction"], "RESEARCH_LONG")
        self.assertEqual(deepseek["direction_label"], "研究偏多 · 非订单")
        self.assertEqual(deepseek["planning_long_take_profit"], 105)
        self.assertIsNone(deepseek["long_take_profit"])
        self.assertEqual(deepseek["probability_semantics"], "UNCALIBRATED_MODEL_ESTIMATE")
        self.assertFalse(deepseek["paper_authorized"])
        self.assertEqual(result["analysis"]["gpt"]["final_decision"], "RESEARCH_NEUTRAL")
        self.assertEqual(result["local"]["preferred"], "RESEARCH_SHORT")
        self.assertEqual(result["local"]["short_plan"]["planning_take_profit"], 95)
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])

    def test_nested_authority_and_unknown_fields_are_preserved_safely(self) -> None:
        result = build_market_ai_projection(
            {
                "analysis": {
                    "deepseek": {
                        "preferred_direction": "SELL",
                        "nested": {"execution_allowed": True, "keep": [1, 2]},
                    }
                },
                "future_extension": {"keep": True},
            }
        )
        report = result["analysis"]["deepseek"]
        self.assertEqual(report["preferred_direction"], "RESEARCH_SHORT")
        self.assertFalse(report["nested"]["execution_allowed"])
        self.assertEqual(report["nested"]["keep"], [1, 2])
        self.assertEqual(result["future_extension"], {"keep": True})
        self.assertIn(
            "market_ai.analysis.deepseek.nested.execution_allowed",
            result["authority_sanitized_paths"],
        )

    def test_post_route_uses_projection(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "server.py"
        ).read_text(encoding="utf-8")
        start = source.index('if parsed.path == "/api/ai/market/dual-analysis":')
        end = source.index('if parsed.path == "/api/ai/runtime-keys":', start)
        route = source[start:end]
        self.assertIn("build_market_ai_projection", route)
        self.assertNotIn("json_response(self, market_dual_ai_analysis(payload))", route)


if __name__ == "__main__":
    unittest.main()
