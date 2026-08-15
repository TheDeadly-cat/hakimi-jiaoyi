from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
import unittest
from unittest.mock import patch

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.market_scanner_projection import (
    MARKET_SCANNER_RESEARCH_PROJECTION_SCHEMA,
    build_market_scanner_projection,
)


class MarketScannerProjectionTests(unittest.TestCase):
    def test_scanner_is_descriptive_and_does_not_mutate_input(self) -> None:
        payload = {
            "ok": True,
            "summary": "最高机会：BTC-USDT · 突破观察",
            "rows": [
                {
                    "symbol": "BTC-USDT",
                    "strategy_id": "livermore",
                    "strategy_name": "突破观察",
                    "action": "BUY",
                    "risk": "high",
                    "score": 88.0,
                    "change24h_pct": 4.2,
                    "nested": {"paper_authorized": True},
                }
            ],
            "paper_authorized": True,
            "live_order_allowed": True,
        }
        before = deepcopy(payload)

        result = build_market_scanner_projection(payload)

        self.assertEqual(payload, before)
        self.assertEqual(
            result["projection_schema_version"],
            MARKET_SCANNER_RESEARCH_PROJECTION_SCHEMA,
        )
        self.assertEqual(result["summary"], "扫描快照已整理 · 研究观察 · 不选参、不下单")
        self.assertIn("raw_summary", result)
        row = result["rows"][0]
        self.assertEqual(row["strategy_id"], "RESEARCH_OBSERVE")
        self.assertEqual(row["raw_strategy_id"], "livermore")
        self.assertEqual(row["strategy_name"], "研究观察 · 未选参")
        self.assertEqual(row["raw_strategy_name"], "突破观察")
        self.assertEqual(row["action"], "观察 / 仅研究 / 非订单")
        self.assertEqual(row["raw_action"], "BUY")
        self.assertEqual(row["risk"], "风险观察")
        self.assertEqual(row["raw_risk"], "high")
        self.assertFalse(row["nested"]["paper_authorized"])
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])
        self.assertFalse(result["parameter_selection_allowed"])
        self.assertIn("payload.rows[0].nested.paper_authorized", result["authority_sanitized_paths"])

    def test_invalid_rows_and_payloads_fail_closed(self) -> None:
        for payload in (None, [], {"ok": True, "rows": ["not-a-row"]}, {"ok": True, "rows": {}}):
            result = build_market_scanner_projection(payload)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "UNKNOWN")
            self.assertTrue(result["research_only"])
            self.assertFalse(result["paper_authorized"])
            self.assertFalse(result["live_order_allowed"])
            self.assertFalse(result["direction_signal_allowed"])

    def test_shared_authority_contract_handles_aliases_mappings_and_tuples(self) -> None:
        immutable_claims = MappingProxyType(
            {
                "Paper_Authorized": "yes",
                "roleAssignmentAllowed": True,
                "raw_armed": True,
                "source_authority": "OFFICIAL",
            }
        )
        nested_tuple = (
            {"armed": 1, "performanceClaimProven": True},
            {"directionSignalAllowed": "true"},
        )
        payload = {
            "ok": True,
            "rows": [
                {
                    "action": "BUY",
                    "status": "READY",
                    "claims": immutable_claims,
                }
            ],
            "audit": nested_tuple,
            "parameterSelectionAuthority": True,
        }

        result = build_market_scanner_projection(payload)

        self.assertIs(payload["rows"][0]["claims"], immutable_claims)
        self.assertIs(payload["audit"], nested_tuple)
        self.assertEqual(payload["rows"][0]["action"], "BUY")
        self.assertFalse(result["parameterSelectionAuthority"])
        self.assertFalse(result["rows"][0]["claims"]["Paper_Authorized"])
        self.assertFalse(result["rows"][0]["claims"]["roleAssignmentAllowed"])
        self.assertIs(result["rows"][0]["claims"]["raw_armed"], True)
        self.assertEqual(result["rows"][0]["claims"]["source_authority"], "OFFICIAL")
        self.assertIsInstance(result["audit"], tuple)
        self.assertFalse(result["audit"][0]["armed"])
        self.assertFalse(result["audit"][0]["performanceClaimProven"])
        self.assertFalse(result["audit"][1]["directionSignalAllowed"])
        self.assertEqual(result["rows"][0]["raw_action"], "BUY")
        self.assertEqual(result["rows"][0]["raw_status"], "READY")
        self.assertIn(
            "payload.rows[0].claims.Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "payload.audit[0].performanceClaimProven",
            result["authority_sanitized_paths"],
        )
        self.assertEqual(authority_violations(result), [])

    def test_postcondition_fails_closed_without_leaking_source_fields(self) -> None:
        with patch(
            "exchange_terminal.services.market_scanner_projection.sanitize_authority_claims",
            side_effect=lambda value, **_: (deepcopy(value), []),
        ):
            result = build_market_scanner_projection(
                {
                    "ok": True,
                    "rows": [],
                    "armed": True,
                    "private_original": "must-not-leak",
                }
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "authority_projection_postcondition_failed")
        self.assertNotIn("armed", result)
        self.assertNotIn("private_original", result)
        self.assertEqual(authority_violations(result), [])

    def test_server_route_finishes_through_projection(self) -> None:
        server_source = (
            Path(__file__).resolve().parents[1] / "exchange_terminal" / "server.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "json_response(self, build_market_scanner_projection(market_scanner(",
            server_source,
        )


if __name__ == "__main__":
    unittest.main()
