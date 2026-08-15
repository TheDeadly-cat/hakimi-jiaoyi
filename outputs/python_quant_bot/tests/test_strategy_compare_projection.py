from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_compare_projection import (
    build_strategy_compare_projection,
)


class StrategyCompareProjectionTests(unittest.TestCase):
    def test_comparison_is_descriptive_and_preserves_raw_evidence(self) -> None:
        report = {
            "ok": True,
            "symbol": "BTC-USDT",
            "regime": {"regime": "震荡市", "trend_pct": 0.4},
            "rows": [
                {
                    "id": "dual_ma",
                    "name": "Dual MA",
                    "action": "BUY",
                    "reason": "快均线上穿慢均线",
                    "probability_pct": 63.5,
                    "score": 72.2,
                    "enabled_condition": "评分>60 且风控正常",
                    "stop_condition": "触发止损",
                }
            ],
            "future_extension": {"keep": [1, 2]},
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(report)

        result = build_strategy_compare_projection(report)

        self.assertEqual(report, before)
        self.assertEqual(result["future_extension"], report["future_extension"])
        row = result["rows"][0]
        self.assertEqual(row["raw_action"], "BUY")
        self.assertEqual(row["action"], "研究假设：偏多 · 非订单")
        self.assertEqual(row["raw_reason"], "快均线上穿慢均线")
        self.assertIn("非订单", row["reason"])
        self.assertEqual(row["score"], 72.2)
        self.assertEqual(row["probability_pct"], 63.5)
        self.assertEqual(row["score_semantics"], "DEVELOPMENT_HEURISTIC_NOT_SELECTION")
        self.assertEqual(row["probability_semantics"], "UNCALIBRATED_MODEL_ESTIMATE")
        self.assertFalse(row["selection_allowed"])
        self.assertFalse(row["order_allowed"])
        self.assertTrue(result["comparison_only"])
        self.assertEqual(
            result["comparison_schema"],
            "strategy-compare-research-projection-v1",
        )
        self.assertFalse(result["parameter_selection_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])

    def test_nested_authority_is_sealed(self) -> None:
        result = build_strategy_compare_projection(
            {
                "rows": [
                    {
                        "action": "SELL",
                        "nested": {
                            "execution_allowed": True,
                            "paper_ready": "true",
                        },
                    }
                ],
                "metadata": {"trade_allowed": 1},
            }
        )

        self.assertEqual(result["rows"][0]["raw_action"], "SELL")
        self.assertFalse(result["rows"][0]["nested"]["execution_allowed"])
        self.assertFalse(result["rows"][0]["nested"]["paper_ready"])
        self.assertFalse(result["metadata"]["trade_allowed"])
        self.assertIn(
            "strategy_compare.rows[0].nested.execution_allowed",
            result["authority_sanitized_paths"],
        )

    def test_unknown_or_missing_rows_do_not_create_selection(self) -> None:
        result = build_strategy_compare_projection(
            {"future": {"status": "READY"}, "rows": None}
        )

        self.assertEqual(result["rows"], [])
        self.assertEqual(result["future"]["status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["future"]["raw_status"], "READY")
        self.assertFalse(result["selection_allowed"])

    def test_route_uses_projection_instead_of_direct_compare_response(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "server.py"
        ).read_text(encoding="utf-8")
        route_start = server_source.index('if path == "/api/strategy/compare":')
        route_end = server_source.index(
            'if path in {"/api/strategy/doctor", "/api/strategy/doctor/preview"}:',
            route_start,
        )
        route_source = server_source[route_start:route_end]
        self.assertIn("build_strategy_compare_projection", route_source)
        self.assertNotIn("json_response(self, strategy_compare(", route_source)


if __name__ == "__main__":
    unittest.main()
