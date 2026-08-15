from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from exchange_terminal.services.configuration_projection import (
    CONFIGURATION_RESEARCH_PROJECTION_SCHEMA,
    build_full_configuration_projection,
)


class ConfigurationProjectionTests(unittest.TestCase):
    def test_config_snapshot_is_neutral_and_does_not_leak_saved_secret_fields(self) -> None:
        payload = {
            "ok": True,
            "status": "READY",
            "summary": "研究和模拟盘已就绪",
            "score": 92.5,
            "items": [
                {
                    "id": "paper_engine",
                    "name": "模拟盘执行",
                    "status": "READY",
                    "detail": "本地 runtime config C:\\secret",
                    "action": "可运行模拟",
                    "configured": True,
                    "paper_authorized": True,
                },
                {"id": "live_wall", "status": "PROTECTED", "locked": True},
            ],
            "checklist": [{"label": "实盘真实下单", "status": "LOCKED", "detail": "保持硬锁"}],
            "providers": {
                "api": {
                    "saved": {
                        "exchange": "okx",
                        "mode": "paper",
                        "api_key_env": "OKX_API_KEY",
                        "secret": "should-not-project",
                        "password": "should-not-project",
                    },
                    "live_enabled": True,
                }
            },
            "paper_authorized": True,
            "live_order_allowed": True,
            "execution_allowed": True,
        }
        before = deepcopy(payload)

        result = build_full_configuration_projection(payload)

        self.assertEqual(payload, before)
        self.assertEqual(result["projection_schema_version"], CONFIGURATION_RESEARCH_PROJECTION_SCHEMA)
        self.assertNotIn("READY", result["status"])
        self.assertEqual(result["raw_status"], "READY")
        self.assertEqual(result["items"][0]["status"], "研究配置已核对")
        self.assertEqual(result["items"][0]["raw_status"], "READY")
        self.assertNotIn("runtime", result["items"][0]["detail"].lower())
        self.assertEqual(result["items"][1]["status"], "硬锁保持")
        self.assertEqual(result["checklist"][0]["status"], "硬锁保持")
        self.assertNotIn("secret", result["providers"]["api"]["saved"])
        self.assertNotIn("password", result["providers"]["api"]["saved"])
        self.assertFalse(result["providers"]["api"]["live_enabled"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["execution_allowed"])
        self.assertIn("snapshot.paper_authorized", result["authority_sanitized_paths"])

    def test_negative_and_optional_statuses_remain_explainable_without_ready_colors(self) -> None:
        result = build_full_configuration_projection(
            {
                "status": "BLOCKED",
                "items": [
                    {"id": "ai", "status": "MISSING"},
                    {"id": "futu", "status": "OPTIONAL"},
                    {"id": "guardian", "status": "STOPPED"},
                    {"id": "watch", "status": "WATCH"},
                ],
                "checklist": [{"label": "数据", "status": "PASS"}],
            }
        )

        self.assertEqual(result["status"], "存在边界阻断")
        self.assertEqual([row["status"] for row in result["items"]], [
            "边界待复核",
            "可选配置缺口",
            "尚未运行",
            "研究观察中",
        ])
        self.assertEqual(result["checklist"][0]["status"], "研究配置已核对")
        self.assertFalse(result["live_trading_allowed"])

    def test_invalid_payload_fails_closed(self) -> None:
        result = build_full_configuration_projection(None)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "配置状态未核验")
        self.assertEqual(result["raw_status"], "UNKNOWN")
        self.assertTrue(result["research_only"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_config_routes_finish_through_projection(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")

        self.assertIn("build_full_configuration_projection(", server_source)
        self.assertIn("full_configuration_snapshot(", server_source)
        self.assertIn("apply_full_research_config(", server_source)


if __name__ == "__main__":
    unittest.main()
