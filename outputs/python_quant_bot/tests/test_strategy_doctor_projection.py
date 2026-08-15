from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.strategy_doctor_projection import (
    build_strategy_doctor_projection,
)


class StrategyDoctorProjectionTests(unittest.TestCase):
    def test_release_and_doctor_authority_are_descriptive_only(self) -> None:
        report = {
            "ok": True,
            "preview": False,
            "summary": "策略体检通过，可模拟执行",
            "paper_ready": True,
            "live_ready": True,
            "paper_authorized": True,
            "release_pipeline": {
                "paper_ready": True,
                "live_ready": True,
                "summary": "Research -> backtest -> paper",
                "stages": [
                    {"stage": "paper_run", "status": "READY", "detail": "可模拟执行"},
                    {"stage": "live_trading", "status": "BLOCKED", "detail": "实盘硬墙"},
                ],
            },
            "lifecycle": [{"stage": "回测/寻优", "status": "READY", "detail": "上线前应比较"}],
            "rows": [{"name": "执行适配", "status": "PASS", "label": "通过", "detail": "可开仓"}],
            "callbacks": [{"name": "confirm_entry", "status": "READY", "mapped": "执行机器人"}],
            "signal": {"action": "BUY", "paper_authorized": True},
        }
        before = deepcopy(report)

        result = build_strategy_doctor_projection(report)

        self.assertEqual(report, before)
        self.assertTrue(result["preview"] is False)
        self.assertEqual(result["raw_paper_ready"], True)
        self.assertFalse(result["paper_ready"])
        self.assertFalse(result["live_ready"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["execution_allowed"])
        self.assertTrue(result["research_only"])
        self.assertTrue(result["descriptive_only"])
        self.assertFalse(result["release_pipeline"]["paper_ready"])
        self.assertFalse(result["release_pipeline"]["live_ready"])
        self.assertTrue(result["release_pipeline"]["live_hard_block"])
        self.assertEqual(result["release_pipeline"]["raw_paper_ready"], True)
        self.assertEqual(result["lifecycle"][0]["status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["rows"][0]["status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["rows"][0]["label"], "研究证据已核对 · 非授权")
        self.assertEqual(result["callbacks"][0]["status"], "RESEARCH_VERIFIED")
        self.assertEqual(result["signal"]["action"], "研究假设：偏多 · 非订单")
        self.assertEqual(result["signal"]["raw_action"], "BUY")

    def test_nested_authority_and_statuses_are_sealed(self) -> None:
        result = build_strategy_doctor_projection(
            {
                "nested": {"paper_ready": 1, "live_order_allowed": "true"},
                "lifecycle": [{"status": "RUNNING"}],
                "rows": [{"status": "BLOCK"}],
                "callbacks": [{"status": "UNKNOWN"}],
                "release_pipeline": {"paper_ready": False},
            }
        )

        self.assertFalse(result["nested"]["paper_ready"])
        self.assertFalse(result["nested"]["live_order_allowed"])
        self.assertEqual(result["lifecycle"][0]["status"], "RESEARCH_REVIEW")
        self.assertEqual(result["rows"][0]["status"], "RESEARCH_BLOCKED")
        self.assertEqual(result["callbacks"][0]["status"], "RESEARCH_OBSERVE")
        self.assertIn("doctor.nested.paper_ready", result["authority_sanitized_paths"])
        self.assertIn("doctor.nested.live_order_allowed", result["authority_sanitized_paths"])

    def test_unknown_fields_and_route_boundary_are_preserved(self) -> None:
        report = {"future_extension": {"keep": [1, 2]}, "release_pipeline": None}
        result = build_strategy_doctor_projection(report)
        self.assertEqual(result["future_extension"], report["future_extension"])
        self.assertIsNone(result["release_pipeline"])
        self.assertFalse(result["paper_ready"])

        server_source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")
        route_start = server_source.index('if path in {"/api/strategy/doctor", "/api/strategy/doctor/preview"}:')
        route_end = server_source.index('if path == "/api/strategy/robot-profiles":', route_start)
        route_source = server_source[route_start:route_end]
        self.assertIn("build_strategy_doctor_projection", route_source)
        self.assertNotIn("json_response(self, report)", route_source)


if __name__ == "__main__":
    unittest.main()
