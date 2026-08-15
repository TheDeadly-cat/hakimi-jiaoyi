from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
import unittest
from unittest.mock import patch

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.strategy_war_room_projection import (
    build_strategy_war_room_projection,
)


class StrategyWarRoomProjectionTests(unittest.TestCase):
    def test_projection_is_descriptive_and_does_not_mutate_source(self) -> None:
        report = {
            "ok": True,
            "summary": "BTC-USDT · 可模拟执行",
            "mission_status": "READY",
            "mission_label": "可模拟执行",
            "paper_ready": True,
            "live_ready": True,
            "bot": {"id": "trend_follower", "role": "OWNER", "active_bot": "trend_follower"},
            "cards": [
                {"name": "作战结论", "value": "可模拟执行", "status": "READY", "detail": "OWNER"},
                {"name": "策略动作", "value": "BUY", "status": "PASS", "detail": "信号"},
            ],
            "matrix": [{"name": "策略体检", "status": "PASS", "score": 80, "detail": "通过"}],
            "timeline": [{"step": "5", "name": "模拟执行", "status": "READY", "detail": "可模拟执行"}],
            "execution_log": [{"level": "PASS", "title": "执行权", "detail": "只有 OWNER 才能向模拟执行层提交动作。"}],
            "anchor_plan": [{"name": "锚点", "action": "BUY", "status": "READY", "detail": "确认"}],
            "top_strategies": [{"id": "dual_ma", "action": "SELL", "reason": "规则"}],
            "entry_ladder": [{"name": "侦察仓", "price": 100, "size_pct": 25, "rule": "信号确认后开小仓"}],
            "exit_ladder": [{"name": "止损线", "price": 95, "size_pct": 100, "rule": "只减仓/平仓"}],
            "no_trade": ["没有 OWNER 时阻断模拟执行"],
        }
        before = deepcopy(report)

        result = build_strategy_war_room_projection(report)

        self.assertEqual(report, before)
        self.assertEqual(result["raw_mission_status"], "READY")
        self.assertEqual(result["mission_status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["mission_label"], "研究条件齐全 · 仍需人工复核")
        self.assertFalse(result["paper_ready"])
        self.assertFalse(result["live_ready"])
        self.assertTrue(result["research_only"])
        self.assertTrue(result["descriptive_only"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertEqual(result["bot"]["role"], "RESEARCH_ONLY")
        self.assertIsNone(result["bot"]["active_bot"])
        self.assertNotIn("可模拟执行", result["mission_label"])

    def test_actions_statuses_and_ladders_are_neutralized(self) -> None:
        result = build_strategy_war_room_projection(
            {
                "mission_status": "BLOCK",
                "mission_label": "暂不交易",
                "cards": [{"value": "SELL", "status": "BLOCK"}],
                "matrix": [{"status": "WATCH"}],
                "timeline": [{"status": "DONE", "name": "模拟执行"}],
                "execution_log": [{"level": "PASS", "detail": "执行机器人 OWNER"}],
                "anchor_plan": [{"action": "BUY", "status": "READY"}],
                "top_strategies": [{"action": "SELL"}],
                "entry_ladder": [{"name": "首层", "rule": "可开仓"}],
                "exit_ladder": [{"name": "止盈", "rule": "执行"}],
            }
        )

        self.assertEqual(result["mission_status"], "RESEARCH_BLOCKED")
        self.assertEqual(result["cards"][0]["status"], "RESEARCH_BLOCKED")
        self.assertEqual(result["cards"][0]["value"], "研究假设：偏空 · 非订单")
        self.assertEqual(result["matrix"][0]["status"], "RESEARCH_OBSERVE")
        self.assertEqual(result["timeline"][0]["status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["anchor_plan"][0]["action"], "研究假设：偏多 · 非订单")
        self.assertEqual(result["top_strategies"][0]["action"], "研究假设：偏空 · 非订单")
        self.assertTrue(result["entry_ladder"][0]["planning_only"])
        self.assertFalse(result["entry_ladder"][0]["order_allowed"])
        self.assertTrue(result["entry_ladder"][0]["name"].startswith("观察区间"))
        self.assertTrue(result["entry_ladder"][0]["rule"].startswith("仅观察"))
        self.assertNotIn("可开仓", result["entry_ladder"][0]["rule"])

    def test_nested_authority_is_fail_closed_and_paths_are_reported(self) -> None:
        result = build_strategy_war_room_projection(
            {
                "paper_authorized": True,
                "live_order_allowed": True,
                "analysis": {"execution_allowed": "true", "paper_ready": 1},
                "cards": [{"value": "HOLD", "status": "INFO"}],
            }
        )

        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["analysis"]["execution_allowed"])
        self.assertFalse(result["analysis"]["paper_ready"])
        self.assertIn("war_room.paper_authorized", result["authority_sanitized_paths"])
        self.assertIn("war_room.analysis.execution_allowed", result["authority_sanitized_paths"])
        self.assertEqual(result["cards"][0]["status"], "RESEARCH_OBSERVE")

    def test_unknown_fields_are_preserved_and_malformed_lists_do_not_raise(self) -> None:
        report = {
            "future_extension": {"keep": [1, 2, 3]},
            "cards": "not-a-list",
            "matrix": None,
            "mission_status": "NEW_STATUS",
        }

        result = build_strategy_war_room_projection(report)

        self.assertEqual(result["future_extension"], report["future_extension"])
        self.assertEqual(result["cards"], [])
        self.assertEqual(result["matrix"], [])
        self.assertEqual(result["mission_status"], "RESEARCH_OBSERVE")
        self.assertEqual(result["raw_mission_status"], "NEW_STATUS")

    def test_shared_authority_contract_preserves_raw_metadata_and_paths(self) -> None:
        immutable_claims = MappingProxyType(
            {
                "directionSignalAllowed": "true",
                "performanceClaimProven": True,
                "roleAssignmentAllowed": True,
            }
        )
        audit_tuple = (
            {"parameterSelectionAuthority": True},
            {"Paper_Authorized": "yes"},
        )
        report = {
            "ok": True,
            "mission_status": "READY",
            "armed": 1,
            "raw_armed": True,
            "source_authority": "OFFICIAL",
            "claims": immutable_claims,
            "audit": audit_tuple,
            "bot": {"role": "OWNER", "active_bot": "trend_follower"},
            "cards": [{"value": "HOLD", "status": "READY"}],
        }

        result = build_strategy_war_room_projection(report)

        self.assertIs(report["claims"], immutable_claims)
        self.assertIs(report["audit"], audit_tuple)
        self.assertEqual(report["bot"]["role"], "OWNER")
        self.assertFalse(result["armed"])
        self.assertIs(result["raw_armed"], True)
        self.assertEqual(result["source_authority"], "OFFICIAL")
        self.assertFalse(result["claims"]["directionSignalAllowed"])
        self.assertFalse(result["claims"]["performanceClaimProven"])
        self.assertFalse(result["claims"]["roleAssignmentAllowed"])
        self.assertIsInstance(result["audit"], tuple)
        self.assertFalse(result["audit"][0]["parameterSelectionAuthority"])
        self.assertFalse(result["audit"][1]["Paper_Authorized"])
        self.assertEqual(result["raw_mission_status"], "READY")
        self.assertEqual(result["bot"]["raw_role"], "OWNER")
        self.assertIn("war_room.armed", result["authority_sanitized_paths"])
        self.assertIn(
            "war_room.claims.directionSignalAllowed",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "war_room.audit[1].Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertEqual(authority_violations(result), [])

    def test_postcondition_fails_closed_without_leaking_source_fields(self) -> None:
        with patch(
            "exchange_terminal.services.strategy_war_room_projection.sanitize_authority_claims",
            side_effect=lambda value, **_: (deepcopy(value), []),
        ):
            result = build_strategy_war_room_projection(
                {
                    "ok": True,
                    "armed": True,
                    "private_original": "must-not-leak",
                }
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "authority_projection_postcondition_failed")
        self.assertNotIn("armed", result)
        self.assertNotIn("private_original", result)
        self.assertEqual(authority_violations(result), [])

    def test_server_route_uses_the_projection_boundary(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")
        route_start = server_source.index('if path == "/api/strategy/war-room":')
        route_end = server_source.index('if path == "/api/strategy/backtest/preview":', route_start)
        route_source = server_source[route_start:route_end]
        self.assertIn("build_strategy_war_room_projection", route_source)
        self.assertNotIn("json_response(self, strategy_war_room(", route_source)


if __name__ == "__main__":
    unittest.main()
