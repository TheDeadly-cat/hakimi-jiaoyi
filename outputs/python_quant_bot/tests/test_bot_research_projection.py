from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.bot_research_projection import (
    build_bot_center_projection,
    build_bot_scheduler_projection,
    build_bot_scheduler_result_projection,
    build_strategy_robot_profiles_projection,
)


class BotResearchProjectionTests(unittest.TestCase):
    def test_center_masks_roles_paper_and_allocation_numbers(self) -> None:
        report = {
            "ok": True,
            "symbol": "BTC-USDT",
            "summary": "原始执行权摘要",
            "paper": {"armed": True, "paper_authorized": True, "risk_status": "PASS"},
            "recommended": ["trend_follower"],
            "scheduler": {
                "active_bot": "trend_follower",
                "active_name": "趋势机器人",
                "mode": "paper",
                "locked": True,
                "candidates": [
                    {
                        "id": "trend_follower",
                        "role": "OWNER",
                        "recommended": True,
                        "can_execute": True,
                        "status": "PASS",
                    }
                ],
            },
            "blueprints": [
                {
                    "id": "trend_follower",
                    "execution_role": "OWNER",
                    "recommended": True,
                    "status": "ONLINE",
                    "nested": {"live_order_allowed": True},
                }
            ],
            "allocations": [{"bucket": "趋势机器人", "pct": 25, "reason": "原始比例"}],
        }
        before = deepcopy(report)

        result = build_bot_center_projection(report)

        self.assertEqual(report, before)
        self.assertFalse(result["paper"]["armed"])
        self.assertFalse(result["paper"]["paper_authorized"])
        self.assertIsNone(result["scheduler"]["active_bot"])
        self.assertFalse(result["scheduler"]["locked"])
        self.assertEqual(result["scheduler"]["mode"], "research_observe")
        candidate = result["scheduler"]["candidates"][0]
        self.assertEqual(candidate["role"], "RESEARCH_PRIMARY")
        self.assertFalse(candidate["can_execute"])
        self.assertFalse(candidate["recommended"])
        blueprint = result["blueprints"][0]
        self.assertEqual(blueprint["execution_role"], "RESEARCH_PRIMARY")
        self.assertFalse(blueprint["nested"]["live_order_allowed"])
        self.assertIsNone(result["allocations"][0]["pct"])
        self.assertEqual(result["allocations"][0]["raw_pct"], 25)
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertTrue(result["live_trading_hard_block"])

    def test_scheduler_projection_keeps_raw_evidence_without_authority(self) -> None:
        result = build_bot_scheduler_projection(
            {
                "active_bot": "grid",
                "mode": "paper",
                "locked": True,
                "candidates": [
                    {
                        "id": "grid",
                        "role": "OWNER",
                        "recommended": True,
                        "can_execute": True,
                        "status": "READY",
                        "nested": {"paper_ready": True},
                    }
                ],
                "conflicts": [{"level": "WARN", "message": "切换冲突"}],
            }
        )
        candidate = result["candidates"][0]
        self.assertEqual(candidate["raw_role"], "OWNER")
        self.assertEqual(candidate["role"], "RESEARCH_PRIMARY")
        self.assertFalse(candidate["can_execute"])
        self.assertFalse(candidate["nested"]["paper_ready"])
        self.assertEqual(result["conflicts"][0]["level"], "RESEARCH_NOTE")
        self.assertFalse(result["role_assignment_allowed"])
        self.assertTrue(result["authority_sanitized_paths"])

    def test_robot_profiles_turn_actions_into_research_observations(self) -> None:
        result = build_strategy_robot_profiles_projection(
            {
                "symbol": "BTC-USDT",
                "summary": "原始档案",
                "rows": [
                    {
                        "id": "dual_ma",
                        "owner": True,
                        "status": "PASS",
                        "status_label": "可模拟",
                        "market_action": "BUY",
                        "readiness": 83,
                        "probability_pct": 64,
                        "start_condition": "评分>60",
                        "stop_condition": "触发止损",
                        "nested": {"execution_allowed": True},
                    }
                ],
            }
        )
        row = result["rows"][0]
        self.assertFalse(row["owner"])
        self.assertEqual(row["research_role"], "RESEARCH_PRIMARY")
        self.assertEqual(row["market_action"], "研究假设：偏多 · 非订单")
        self.assertEqual(row["status_label"], "研究观察条件较完整")
        self.assertIn("研究观察", row["start_condition"])
        self.assertIn("非订单", row["reason"])
        self.assertFalse(row["nested"]["execution_allowed"])
        self.assertFalse(result["parameter_selection_allowed"])

    def test_routes_use_projection_and_mutation_result_is_sealed(self) -> None:
        result = build_bot_scheduler_result_projection(
            {
                "ok": True,
                "scheduler": {
                    "active_bot": "grid",
                    "candidates": [{"role": "OWNER", "can_execute": True}],
                },
                "paper_authorized": True,
            }
        )
        self.assertEqual(result["summary"], "研究角色变更结果 · 仅记录观察标签，不生成订单")
        self.assertFalse(result["paper_authorized"])
        self.assertIsNone(result["scheduler"]["active_bot"])
        self.assertFalse(result["scheduler"]["candidates"][0]["can_execute"])

        server_source = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "server.py"
        ).read_text(encoding="utf-8")
        for path, builder in (
            ("/api/strategy/robot-profiles", "build_strategy_robot_profiles_projection"),
            ("/api/bot/center", "build_bot_center_projection"),
            ("/api/bot/scheduler", "build_bot_scheduler_projection"),
            ("/api/bot/assign", "build_bot_scheduler_result_projection"),
            ("/api/bot/release", "build_bot_scheduler_result_projection"),
        ):
            route_start = server_source.index(f'if path == "{path}":')
            route_end = server_source.find("\n            if path ==", route_start + 1)
            route_source = server_source[route_start:route_end if route_end >= 0 else route_start + 900]
            self.assertIn(builder, route_source)


if __name__ == "__main__":
    unittest.main()
