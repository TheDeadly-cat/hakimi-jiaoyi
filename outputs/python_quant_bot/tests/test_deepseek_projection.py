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

    def test_provider_status_keeps_only_safe_configuration_fields(self) -> None:
        status = {"configured": True, "enabled": True, "model": "deepseek-v4-pro", "thinking": "disabled",
                  "source": "env", "api_key": "PRIVATE_SENTINEL", "base_url": "PRIVATE_SENTINEL"}
        result = build_deepseek_projection({"status": status, "provider_status": status})
        for key in ("status", "provider_status"):
            self.assertEqual(result[key], {"provider": "deepseek", "configured": True, "enabled": True,
                "model": "deepseek-v4-pro", "thinking": "disabled", "source": "env"})
        self.assertNotIn("PRIVATE_SENTINEL", str(result))
        self.assertNotIn("raw_status", result)

    def test_structured_signal_preserves_engine_receipt_but_cannot_grant_authority(self) -> None:
        signal = {"calculated": True, "availability": "CALCULATED", "engine_version": "original-engine",
                  "row_count": 99, "required_rows": 80, "execution_allowed": True,
                  "result": {"action": "BUY", "reason": "original-rule", "order_allowed": True}}
        report = {"local": {"signal": signal}, "analysis": {"signal": signal}, "signal": "SELL"}
        before = deepcopy(report)
        result = build_deepseek_projection(report)
        self.assertEqual(report, before)
        for section in ("local", "analysis"):
            projected = result[section]["signal"]
            self.assertTrue(projected["calculated"])
            self.assertEqual(projected["availability"], "CALCULATED")
            self.assertEqual(projected["engine_version"], "original-engine")
            self.assertEqual(projected["row_count"], 99)
            self.assertEqual(projected["required_rows"], 80)
            self.assertFalse(projected["execution_allowed"])
            self.assertEqual(projected["result"]["action"], "RESEARCH_LONG")
            self.assertEqual(projected["result"]["reason"], "original-rule")
            self.assertFalse(projected["result"]["order_allowed"])
            self.assertNotIn("raw_signal", result[section])
        self.assertEqual(result["signal"], "RESEARCH_SHORT")
        self.assertFalse(result["execution_allowed"])

    def test_macd_period_exception_is_limited_to_validated_configuration_paths(self) -> None:
        result = build_deepseek_projection({
            "strategy_context": {"strategy_params": {"signal": 9}},
            "local": {"signal": {"result": {"signal": "BUY", "action": "SELL"}}},
            "analysis": {"deepseek": {"strategy_params": {"signal": 9}}},
        })
        self.assertEqual(result["strategy_context"]["strategy_params"]["signal"], 9)
        self.assertEqual(result["local"]["signal"]["result"]["signal"], "RESEARCH_LONG")
        self.assertEqual(result["local"]["signal"]["result"]["action"], "RESEARCH_SHORT")
        self.assertEqual(result["analysis"]["deepseek"]["strategy_params"]["signal"], "RESEARCH_UNCERTAIN")
        for value in (True, 1, 10001, 9.0, "BUY"):
            with self.subTest(value=value):
                projected = build_deepseek_projection({"strategy_context": {"strategy_params": {"signal": value}}})
                self.assertTrue(projected["strategy_context"]["strategy_params"]["signal"].startswith("RESEARCH_"))

    def test_frozen_input_identity_and_validated_parameters_survive_projection(self) -> None:
        identity = {"first_ts": 1704153600000, "last_ts": 1712707200000,
                    "row_count": 100, "rows_sha256": "a" * 64,
                    "price_basis": "SUPPLIED_LAST_CANDLE_CLOSE", "source": "stock_sqlite_cache"}
        params = {"fast": 13, "slow": 26, "signal": 9, "position_pct": 0.25, "stop_loss_pct": 0.035}
        context = {"strategy_id": "macd", "strategy_params": params, "symbol": "HK.00836",
                   "bar": "1Dutc", "session": "regular"}
        report = {"input_identity": identity, "strategy_context": context,
                  "local": {"strategy_params": params, "signal": {"strategy_params": params}},
                  "analysis": {"strategy_params": params, "signal": {"strategy_params": params}}}
        before = deepcopy(report)
        result = build_deepseek_projection(report)
        self.assertEqual(report, before)
        self.assertEqual(result["input_identity"], identity)
        self.assertEqual(result["strategy_context"], context)
        for section in ("local", "analysis"):
            self.assertEqual(result[section]["strategy_params"], params)
            self.assertEqual(result[section]["signal"]["strategy_params"], params)
        self.assertFalse(result["parameter_selection_allowed"])
        self.assertFalse(result["order_allowed"])

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
