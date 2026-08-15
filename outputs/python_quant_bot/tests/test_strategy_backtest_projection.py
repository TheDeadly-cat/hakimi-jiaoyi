from __future__ import annotations

from copy import deepcopy
import json
from types import MappingProxyType
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_backtest_projection import (
    build_strategy_backtest_preview_error,
    build_strategy_backtest_preview_projection,
)


class StrategyBacktestProjectionTests(unittest.TestCase):
    def test_preview_preserves_unknown_fields_without_mutating_input(self) -> None:
        report = {
            "ok": True,
            "symbol": "AAPL",
            "current": {"total_return_pct": 2.5},
            "risk_control_surface": {
                "schema_version": "backtest-risk-control-surface-v1",
                "status": "PEAK_ONLY",
                "parameter_selection_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "future_extension": {"label": "keep-me", "values": [1, 2, 3]},
            "preview": False,
            "pipeline_run": {"run_id": "should-not-leak"},
            "research_only": False,
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(report)

        result = build_strategy_backtest_preview_projection(report)

        self.assertEqual(report, before)
        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["future_extension"], report["future_extension"])
        self.assertEqual(
            result["risk_control_surface"], report["risk_control_surface"]
        )
        self.assertTrue(result["preview"])
        self.assertIsNone(result["pipeline_run"])
        self.assertTrue(result["historical_backtest_only"])
        self.assertFalse(result["profitability_proven"])
        self.assertFalse(result["performance_claim_allowed"])
        self.assertFalse(result["parameter_selection_allowed"])
        self.assertFalse(result["automatic_paper_activation_allowed"])
        self.assertFalse(result["execution_allowed"])
        self.assertTrue(result["research_only"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_nested_authority_is_recursively_neutralized_and_reported(self) -> None:
        immutable_claim = MappingProxyType({
            "Paper_Authorized": "true",
            "source_authority": "OFFICIAL",
        })
        report = {
            "ok": True,
            "current": {
                "live-order-allowed": True,
                "details": [
                    immutable_claim,
                    (
                        {"canTrade": 1, "metric": 7},
                        {"可下单": True, "已授权": 0},
                        {"实盘－授权": None},
                    ),
                ],
            },
            "candidates": [
                {
                    "order_allowed": True,
                    "automatic_paper_activation_allowed": True,
                }
            ],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

        result = build_strategy_backtest_preview_projection(report)

        self.assertTrue(immutable_claim["Paper_Authorized"])
        self.assertTrue(report["current"]["live-order-allowed"])
        self.assertFalse(result["current"]["live-order-allowed"])
        self.assertFalse(result["current"]["details"][0]["Paper_Authorized"])
        self.assertEqual(
            result["current"]["details"][0]["source_authority"],
            "OFFICIAL",
        )
        self.assertIsInstance(result["current"]["details"][1], tuple)
        self.assertFalse(result["current"]["details"][1][0]["canTrade"])
        self.assertFalse(result["current"]["details"][1][1]["可下单"])
        self.assertFalse(result["current"]["details"][1][1]["已授权"])
        self.assertFalse(result["current"]["details"][1][2]["实盘－授权"])
        self.assertFalse(result["candidates"][0]["order_allowed"])
        self.assertFalse(
            result["candidates"][0]["automatic_paper_activation_allowed"]
        )
        self.assertEqual(result["current"]["details"][1][0]["metric"], 7)
        self.assertIn(
            "report.current.live-order-allowed",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "report.current.details[0].Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "report.current.details[1][1].可下单",
            result["authority_sanitized_paths"],
        )

    def test_postcondition_returns_fixed_safe_error_without_source_echo(self) -> None:
        unsafe_source = {
            "nested": {"canTrade": True},
            "source_secret": "must-not-be-returned",
        }
        with patch(
            "exchange_terminal.services.strategy_backtest_projection."
            "sanitize_authority_claims",
            return_value=(unsafe_source, []),
        ):
            result = build_strategy_backtest_preview_projection(
                {"safe": "input-also-must-not-be-returned"}
            )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["error"],
            "strategy_backtest_preview_authority_postcondition_failed",
        )
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("must-not-be-returned", serialized)
        self.assertNotIn("input-also-must-not-be-returned", serialized)
        self.assertNotIn("canTrade", serialized)
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_false_nested_authority_does_not_add_warning_field(self) -> None:
        result = build_strategy_backtest_preview_projection(
            {
                "ok": False,
                "current": {"paper_authorized": False},
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        )

        self.assertNotIn("authority_sanitized_paths", result)
        self.assertFalse(result["current"]["paper_authorized"])

    def test_error_contract_is_fail_closed(self) -> None:
        result = build_strategy_backtest_preview_error("invalid strategy")

        self.assertEqual(
            result,
            {
                "ok": False,
                "error": "invalid strategy",
                "preview": True,
                "pipeline_run": None,
                "historical_backtest_only": True,
                "profitability_proven": False,
                "performance_claim_allowed": False,
                "parameter_selection_allowed": False,
                "automatic_paper_activation_allowed": False,
                "execution_allowed": False,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
