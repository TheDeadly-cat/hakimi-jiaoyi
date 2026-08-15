from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.trading_agents_projection import (
    build_trading_agents_projection,
    project_trading_agents_event,
)


class TradingAgentsProjectionTests(unittest.TestCase):
    def test_room_is_research_only_and_keeps_plans_non_executable(self) -> None:
        report = {
            "ok": True,
            "symbol": "BTC-USDT",
            "final": {
                "decision": "LONG_OBSERVE",
                "long_win_rate_pct": 68,
                "short_win_rate_pct": 32,
                "long_take_profit": 105,
                "long_stop_loss": 98,
                "paper_authorized": True,
                "safe_action": "paper only",
            },
            "agents": [
                {
                    "stance": "SHORT",
                    "confidence_pct": 74,
                    "take_profit": 96,
                    "stop_loss": 102,
                    "execution_allowed": True,
                }
            ],
            "meeting_transcript": [{"stance": "WAIT", "confidence_pct": 51}],
        }
        before = deepcopy(report)

        result = build_trading_agents_projection(report)

        self.assertEqual(report, before)
        self.assertEqual(result["final"]["decision"], "RESEARCH_LONG")
        self.assertEqual(result["final"]["decision_label"], "RESEARCH_LONG · DESCRIPTIVE_ONLY")
        self.assertEqual(result["final"]["planning_long_take_profit"], 105)
        self.assertIsNone(result["final"]["long_take_profit"])
        self.assertIsNone(result["final"]["long_win_rate_pct"])
        self.assertEqual(result["final"]["raw_long_win_rate_pct"], 68)
        self.assertEqual(result["final"]["raw_safe_action"], "paper only")
        self.assertEqual(result["agents"][0]["stance"], "RESEARCH_SHORT")
        self.assertIsNone(result["agents"][0]["confidence_pct"])
        self.assertFalse(result["agents"][0]["execution_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])
        self.assertEqual(result["probability_semantics"], "UNCALIBRATED_RESEARCH_WEIGHT_ONLY")

    def test_nested_authority_and_direction_fields_are_fail_closed(self) -> None:
        result = build_trading_agents_projection(
            {
                "local": {
                    "preferred": "BUY",
                    "long_plan": {"take_profit": 111, "paper_ready": True},
                },
                "future": {"keep": [1, 2]},
            }
        )
        self.assertEqual(result["local"]["preferred"], "RESEARCH_LONG")
        self.assertEqual(result["local"]["long_plan"]["planning_take_profit"], 111)
        self.assertIsNone(result["local"]["long_plan"]["take_profit"])
        self.assertFalse(result["local"]["long_plan"]["paper_ready"])
        self.assertEqual(result["future"], {"keep": [1, 2]})
        self.assertIn("trading_agents.local.long_plan.paper_ready", result["authority_sanitized_paths"])

    def test_stream_events_are_projected_before_the_client_sees_them(self) -> None:
        message = project_trading_agents_event(
            {
                "type": "message",
                "row": {"stance": "SHORT", "confidence_pct": 62, "live_order_allowed": True},
            }
        )
        self.assertEqual(message["row"]["stance"], "RESEARCH_SHORT")
        self.assertIsNone(message["row"]["confidence_pct"])
        self.assertFalse(message["row"]["live_order_allowed"])
        complete = project_trading_agents_event(
            {
                "type": "complete",
                "execution_allowed": True,
                "safe_action": "ORDER",
                "data": {"final": {"decision": "WAIT"}},
            }
        )
        self.assertEqual(complete["data"]["final"]["decision"], "RESEARCH_NEUTRAL")
        self.assertFalse(complete["data"]["paper_authorized"])
        self.assertFalse(complete["execution_allowed"])
        self.assertEqual(complete["safe_action"], "OBSERVE / RESEARCH ONLY / PAPER UNAUTHORIZED / LIVE HARD LOCK")
        self.assertIn("trading_agents_event.execution_allowed", complete["authority_sanitized_paths"])

    def test_post_route_uses_projection_for_stream_and_json(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")
        start = source.index('if parsed.path == "/api/ai/trading-agents/discuss":')
        end = source.index('except Exception as exc:', start)
        route = source[start:end]
        self.assertIn("project_trading_agents_event", route)
        self.assertIn("build_trading_agents_projection", route)
        self.assertNotIn("json_response(self, trading_agents_external_discussion(payload))", route)


if __name__ == "__main__":
    unittest.main()
