from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
import unittest
from unittest.mock import patch

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.market_anomaly_projection import (
    MARKET_ANOMALY_RESEARCH_PROJECTION_SCHEMA,
    build_market_anomaly_detail_projection,
    build_market_anomaly_radar_projection,
    build_market_trend_cockpit_projection,
)


class MarketAnomalyProjectionTests(unittest.TestCase):
    def test_radar_is_neutral_and_does_not_mutate_input(self) -> None:
        payload = {
            "ok": True,
            "summary": "raw radar",
            "rows": [
                {
                    "symbol": "BTC-USDT",
                    "direction": "偏多",
                    "tone": "up",
                    "safe_action": "观察 / 仅研究",
                    "paper_authorized": True,
                    "nested": {"execution_allowed": "true"},
                }
            ],
            "cards": [{"label": "趋势", "preferred": "偏空", "tone": "down"}],
            "live_order_allowed": True,
        }
        before = deepcopy(payload)

        result = build_market_anomaly_radar_projection(payload)

        self.assertEqual(payload, before)
        self.assertEqual(result["projection_schema_version"], MARKET_ANOMALY_RESEARCH_PROJECTION_SCHEMA)
        self.assertEqual(result["rows"][0]["direction"], "研究观察")
        self.assertEqual(result["rows"][0]["raw_direction"], "偏多")
        self.assertEqual(result["rows"][0]["tone"], "flat")
        self.assertEqual(result["rows"][0]["raw_tone"], "up")
        self.assertEqual(result["cards"][0]["preferred"], "研究观察")
        self.assertEqual(result["cards"][0]["raw_preferred"], "偏空")
        self.assertFalse(result["rows"][0]["nested"]["execution_allowed"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["direction_signal_allowed"])
        self.assertIn("payload.rows[0].paper_authorized", result["authority_sanitized_paths"])

    def test_detail_and_trend_neutralize_nested_sections(self) -> None:
        payload = {
            "ok": True,
            "anomaly": {"direction": "偏多", "tone": "up"},
            "trend": {
                "preferred": "偏空",
                "cards": [{"tone": "down", "direction": "偏空"}],
                "paper_authorized": True,
            },
            "source_control": {
                "cards": [{"tone": "up", "live_trading_allowed": True}],
                "rows": [{"status": "READY", "tone": "up"}],
            },
        }

        detail = build_market_anomaly_detail_projection(payload)
        trend = build_market_trend_cockpit_projection(payload["trend"])

        self.assertEqual(detail["anomaly"]["direction"], "研究观察")
        self.assertEqual(detail["trend"]["preferred"], "研究观察")
        self.assertEqual(detail["trend"]["cards"][0]["tone"], "flat")
        self.assertFalse(detail["trend"]["paper_authorized"])
        self.assertFalse(detail["source_control"]["cards"][0]["live_trading_allowed"])
        self.assertEqual(detail["source_control"]["rows"][0]["status"], "研究观察")
        self.assertEqual(detail["source_control"]["rows"][0]["raw_status"], "READY")
        self.assertEqual(trend["preferred"], "研究观察")
        self.assertEqual(trend["raw_preferred"], "偏空")

    def test_invalid_payload_fails_closed(self) -> None:
        for builder in (
            build_market_anomaly_radar_projection,
            build_market_anomaly_detail_projection,
            build_market_trend_cockpit_projection,
        ):
            result = builder(None)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertTrue(result["research_only"])
            self.assertFalse(result["paper_authorized"])
            self.assertFalse(result["live_order_allowed"])
            self.assertFalse(result["direction_signal_allowed"])

    def test_shared_authority_contract_preserves_raw_metadata_and_paths(self) -> None:
        immutable_claims = MappingProxyType(
            {
                "Paper_Authorized": "yes",
                "claims": (
                    {"armed": 1, "directionSignalAllowed": "true"},
                    {
                        "performanceClaimProven": True,
                        "roleAssignmentAllowed": True,
                    },
                ),
                "raw_armed": True,
                "source_authority": "OFFICIAL",
            }
        )
        payload = {
            "ok": True,
            "status": "READY",
            "parameterSelectionAuthority": True,
            "evidence": immutable_claims,
        }

        result = build_market_anomaly_radar_projection(payload)

        self.assertIs(payload["evidence"], immutable_claims)
        self.assertEqual(immutable_claims["Paper_Authorized"], "yes")
        self.assertEqual(immutable_claims["claims"][0]["armed"], 1)
        self.assertFalse(result["parameterSelectionAuthority"])
        self.assertFalse(result["evidence"]["Paper_Authorized"])
        self.assertIsInstance(result["evidence"]["claims"], tuple)
        self.assertFalse(result["evidence"]["claims"][0]["armed"])
        self.assertFalse(result["evidence"]["claims"][0]["directionSignalAllowed"])
        self.assertFalse(result["evidence"]["claims"][1]["performanceClaimProven"])
        self.assertFalse(result["evidence"]["claims"][1]["roleAssignmentAllowed"])
        self.assertIs(result["evidence"]["raw_armed"], True)
        self.assertEqual(result["evidence"]["source_authority"], "OFFICIAL")
        self.assertEqual(result["raw_status"], "READY")
        self.assertIn(
            "payload.evidence.claims[0].directionSignalAllowed",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "payload.evidence.Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertEqual(authority_violations(result), [])

    def test_postcondition_fails_closed_without_leaking_source_fields(self) -> None:
        with patch(
            "exchange_terminal.services.market_anomaly_projection.sanitize_authority_claims",
            side_effect=lambda value, **_: (deepcopy(value), []),
        ):
            result = build_market_anomaly_radar_projection(
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

    def test_read_only_routes_finish_through_projection(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "json_response(self, build_market_anomaly_radar_projection(",
            server_source,
        )
        self.assertIn(
            "json_response(self, build_market_anomaly_detail_projection(",
            server_source,
        )
        self.assertIn(
            "json_response(self, build_market_trend_cockpit_projection(",
            server_source,
        )


if __name__ == "__main__":
    unittest.main()
