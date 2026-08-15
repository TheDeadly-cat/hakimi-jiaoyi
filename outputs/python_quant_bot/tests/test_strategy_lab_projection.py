from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_lab_projection import (
    build_strategy_lab_projection,
)


class StrategyLabProjectionTests(unittest.TestCase):
    def test_planning_values_are_explicit_and_legacy_operational_keys_fail_closed(self) -> None:
        report = {
            "ok": True,
            "symbol": "BTC-USDT",
            "strategy": {"id": "dual_ma", "params": {"position_pct": 0.25}},
            "rows": [
                {
                    "preset": "balanced",
                    "position_pct": 55,
                    "take_profit": 102.4,
                    "stop_loss": 97.8,
                    "score": 71.5,
                    "note": "development note",
                }
            ],
            "future_extension": {"keep": [1, 2]},
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(report)

        result = build_strategy_lab_projection(report)

        self.assertEqual(report, before)
        self.assertEqual(result["future_extension"], report["future_extension"])
        row = result["rows"][0]
        self.assertIsNone(row["position_pct"])
        self.assertIsNone(row["take_profit"])
        self.assertIsNone(row["stop_loss"])
        self.assertIsNone(row["score"])
        self.assertEqual(
            row["planning_candidate"],
            {
                "position_pct": 55,
                "take_profit": 102.4,
                "stop_loss": 97.8,
                "score": 71.5,
            },
        )
        self.assertTrue(row["planning_only"])
        self.assertFalse(row["apply_to_risk_form_allowed"])
        self.assertEqual(row["score_semantics"], "DEVELOPMENT_HEURISTIC_NOT_RANKING")
        self.assertTrue(result["research_only"])
        self.assertTrue(result["descriptive_only"])
        self.assertTrue(result["planning_only"])
        self.assertFalse(result["parameter_selection_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])
        self.assertEqual(
            result["evidence_contract"],
            {
                "schema_version": "strategy-lab-evidence-boundary-v1",
                "mode": "DEVELOPMENT_HEURISTIC_PLANNING_ONLY",
                "parameter_stability_status": "NOT_CONNECTED",
                "cost_sensitivity_status": "NOT_CONNECTED",
                "chronological_slice_status": "NOT_CONNECTED",
                "research_report_source": "FROZEN_RESEARCH_REPORT_NOT_CONNECTED",
                "interpretation": "DESCRIPTIVE_PLANNING_ONLY",
                "research_only": True,
                "descriptive_only": True,
                "development_heuristic_only": True,
                "profitability_proven": False,
                "performance_claim_allowed": False,
                "parameter_selection_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        )

    def test_nested_authority_is_sanitized_without_losing_research_fields(self) -> None:
        result = build_strategy_lab_projection(
            {
                "rows": [
                    {
                        "position_pct": 20,
                        "nested": {
                            "execution_allowed": True,
                            "paper_ready": "true",
                        },
                    }
                ],
                "metadata": {"order_allowed": 1, "label": "keep"},
            }
        )

        self.assertFalse(result["rows"][0]["nested"]["execution_allowed"])
        self.assertFalse(result["rows"][0]["nested"]["paper_ready"])
        self.assertFalse(result["metadata"]["order_allowed"])
        self.assertEqual(result["metadata"]["label"], "keep")
        self.assertIn(
            "strategy_lab.rows[0].nested.execution_allowed",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "strategy_lab.metadata.order_allowed",
            result["authority_sanitized_paths"],
        )

    def test_non_finite_planning_values_become_unknown(self) -> None:
        result = build_strategy_lab_projection(
            {"rows": [{"position_pct": float("nan"), "score": "not-a-number"}]}
        )

        self.assertEqual(
            result["rows"][0]["planning_candidate"],
            {
                "position_pct": None,
                "take_profit": None,
                "stop_loss": None,
                "score": None,
            },
        )

    def test_route_uses_projection_instead_of_direct_lab_response(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "server.py"
        ).read_text(encoding="utf-8")
        route_start = server_source.index('if path == "/api/strategy/lab":')
        route_end = server_source.index('if path == "/api/strategy/war-room":', route_start)
        route_source = server_source[route_start:route_end]
        self.assertIn("build_strategy_lab_projection", route_source)
        self.assertNotIn("json_response(self, strategy_lab(", route_source)


if __name__ == "__main__":
    unittest.main()
