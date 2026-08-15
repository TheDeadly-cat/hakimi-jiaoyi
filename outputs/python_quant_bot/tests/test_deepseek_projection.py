from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.deepseek_projection import build_deepseek_projection


class DeepseekProjectionTests(unittest.TestCase):
    def test_strategy_and_opportunity_fields_are_research_only(self) -> None:
        report = {
            "ok": True,
            "analysis": {
                "direction": "LONG",
                "confidence_pct": 76,
                "take_profit": 105,
                "stop_loss": 98,
                "deepseek_take_profit": 106,
                "actionability": "ALLOW_STRATEGY_EVALUATION",
                "paper_authorized": True,
                "opportunities": [
                    {
                        "direction": "SHORT",
                        "confidence_pct": 65,
                        "entry_hint": "below resistance",
                        "take_profit_hint": 95,
                        "stop_loss_hint": 102,
                    }
                ],
            },
        }
        before = deepcopy(report)

        result = build_deepseek_projection(report)

        self.assertEqual(report, before)
        analysis = result["analysis"]
        self.assertEqual(analysis["direction"], "RESEARCH_LONG")
        self.assertIsNone(analysis["confidence_pct"])
        self.assertEqual(analysis["raw_confidence_pct"], 76)
        self.assertEqual(analysis["planning_take_profit"], 105)
        self.assertIsNone(analysis["take_profit"])
        self.assertEqual(analysis["planning_deepseek_take_profit"], 106)
        self.assertIsNone(analysis["deepseek_take_profit"])
        self.assertEqual(analysis["actionability"], "RESEARCH_REVIEW_REQUIRED")
        opportunity = analysis["opportunities"][0]
        self.assertEqual(opportunity["direction"], "RESEARCH_SHORT")
        self.assertEqual(opportunity["planning_entry_hint"], "below resistance")
        self.assertIsNone(opportunity["take_profit_hint"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_nested_authority_is_fail_closed_and_unknown_fields_survive(self) -> None:
        result = build_deepseek_projection(
            {
                "analysis": {"nested": {"execution_allowed": True, "future": [1, 2]}},
                "extension": {"keep": "yes"},
            }
        )
        self.assertFalse(result["analysis"]["nested"]["execution_allowed"])
        self.assertEqual(result["extension"], {"keep": "yes"})
        self.assertIn("deepseek.analysis.nested.execution_allowed", result["authority_sanitized_paths"])

    def test_routes_use_the_projection(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")
        start = source.index('if path == "/api/ai/deepseek/analyze":')
        end = source.index('if path == "/api/ai/deepseek/code-worker/drafts":', start)
        route = source[start:end]
        self.assertIn("build_deepseek_projection", route)
        self.assertNotIn("json_response(self, deepseek_strategy_analysis(", route)

    def test_projection_schema_and_hard_wall_are_explicit(self) -> None:
        result = build_deepseek_projection({"safe_action": "paper only", "live_ready": True})
        self.assertEqual(result["research_projection_schema"], "deepseek-research-projection-v1")
        self.assertEqual(result["raw_safe_action"], "paper only")
        self.assertEqual(result["safe_action"], "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK")
        self.assertFalse(result["live_ready"])
        self.assertTrue(result["live_trading_hard_block"])


if __name__ == "__main__":
    unittest.main()
