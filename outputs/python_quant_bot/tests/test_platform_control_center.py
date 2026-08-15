from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.platform_control_center import (
    build_market_data_health_projection,
    build_platform_control_center_projection,
)


class PlatformControlCenterProjectionTests(unittest.TestCase):
    def test_market_health_envelope_is_pure_and_cannot_be_promoted_by_payload(self) -> None:
        health = {
            "ok": True,
            "status": "READY",
            "data_truth": {
                "schema_version": "market-data-truth-v1",
                "status": "READY",
                "paper_authorized": True,
                "authority_aliases": {
                    "Paper_Authorized": True,
                    "canTrade": "false",
                    "live-order-allowed": None,
                },
            },
            "read_only": False,
            "paper_authorized": True,
            "live_trading_hard_block": False,
            "live_order_allowed": True,
            "live_trading_allowed": True,
        }
        before = copy.deepcopy(health)

        result = build_market_data_health_projection(
            health,
            runtime_read_only=True,
            live_trading_hard_block=True,
        )

        self.assertEqual(health, before)
        self.assertIs(result["read_only"], True)
        self.assertIs(result["paper_authorized"], False)
        self.assertIs(result["live_trading_hard_block"], True)
        self.assertIs(result["live_order_allowed"], False)
        self.assertIs(result["live_trading_allowed"], False)
        self.assertFalse(result["data_truth"]["paper_authorized"])
        self.assertFalse(result["data_truth"]["authority_aliases"]["Paper_Authorized"])
        self.assertFalse(result["data_truth"]["authority_aliases"]["canTrade"])
        self.assertFalse(result["data_truth"]["authority_aliases"]["live-order-allowed"])
        self.assertTrue(health["data_truth"]["paper_authorized"])
        self.assertIn("health.data_truth.paper_authorized", result["authority_sanitized_paths"])
        self.assertIn(
            "health.data_truth.authority_aliases.Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "health.data_truth.authority_aliases.canTrade",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "health.data_truth.authority_aliases.live-order-allowed",
            result["authority_sanitized_paths"],
        )

    def test_control_center_projection_preserves_contract_without_mutating_inputs(self) -> None:
        market_truth = {
            "schema_version": "market-data-truth-v1",
            "status": "STALE",
            "symbol": "BTC-USDT",
        }
        inputs = {
            "paper": {
                "symbol": "BTC-USDT",
                "strategy": {"id": "portfolio_rs_v2"},
                "armed": True,
                "equity": 1000.0,
                "paper_authorized": True,
                "live_order_allowed": True,
            },
            "risk": {
                "pretrade": {"status": "RUNTIME_READ_ONLY"},
                "paper_authorized": True,
                "live_order_allowed": True,
                "authority_aliases": {
                    "Paper_Authorized": True,
                    "canTrade": "false",
                    "live-order-allowed": None,
                },
            },
            "pipeline": {"latest": {"status": "REVIEW", "run_id": "run-1"}},
            "executor": {"live_order_allowed": True},
            "paper_ledger": {
                "backend": "sqlite",
                "account_version": 4,
                "restart_ready": True,
            },
            "mutation_journal": {"ok": True},
            "latest_order": {
                "order_id": "order-1",
                "signal_id": "signal-1",
                "risk_request_id": "risk-1",
                "market_snapshot_id": "snapshot-1",
                "symbol": "BTC-USDT",
                "side": "BUY",
                "state": "FILLED",
                "updated_at": 123,
                "quantity": 99,
                "price": 88,
                "api_key": "must-not-project",
                "live_order_allowed": True,
            },
            "data_health": {
                "status": "STALE",
                "data_truth": market_truth,
                "paper_authorized": True,
                "live_order_allowed": True,
            },
            "market_truth": market_truth,
            "data_revision": {
                "status": "REVIEW",
                "latest_revision_review_count": 3,
                "latest_cross_source": [
                    {"status": "REVIEW"},
                    {"status": "PASS"},
                    {"status": "REVIEW"},
                ],
            },
            "forward_validation": {"status": "BLOCK", "live_order_allowed": True},
            "small_capital_plan": {"status": "NEEDS_EVIDENCE", "execution_allowed": True},
            "audit": {"event_count": 7},
            "recent_audit": [{
                "type": "example",
                "execution_allowed": True,
                "Paper_Authorized": True,
            }],
        }
        before = copy.deepcopy(inputs)

        result = build_platform_control_center_projection(
            runtime_read_only=True,
            live_trading_hard_block=True,
            effective_paper_authorized=False,
            default_strategy_id="fallback-strategy",
            updated_at=456,
            **inputs,
        )

        self.assertEqual(inputs, before)
        self.assertIs(result["read_only"], True)
        self.assertIs(result["live_trading_hard_block"], True)
        self.assertIs(result["live_order_allowed"], False)
        self.assertIs(result["paper_authorized"], False)
        self.assertFalse(result["paper"]["paper_authorized"])
        self.assertFalse(result["risk"]["paper_authorized"])
        self.assertFalse(result["risk"]["authority_aliases"]["Paper_Authorized"])
        self.assertFalse(result["risk"]["authority_aliases"]["canTrade"])
        self.assertFalse(result["risk"]["authority_aliases"]["live-order-allowed"])
        self.assertFalse(result["executor"]["live_order_allowed"])
        self.assertFalse(result["data_health"]["paper_authorized"])
        self.assertFalse(result["recent_audit"][0]["execution_allowed"])
        self.assertFalse(result["recent_audit"][0]["Paper_Authorized"])
        self.assertTrue(result["paper"]["armed"])
        self.assertTrue(result["paper_armed"])
        self.assertIn("paper.paper_authorized", result["authority_sanitized_paths"])
        self.assertIn("executor.live_order_allowed", result["authority_sanitized_paths"])
        self.assertIn("recent_audit[0].execution_allowed", result["authority_sanitized_paths"])
        self.assertIn(
            "risk.authority_aliases.Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "risk.authority_aliases.canTrade",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "risk.authority_aliases.live-order-allowed",
            result["authority_sanitized_paths"],
        )
        self.assertIn(
            "recent_audit[0].Paper_Authorized",
            result["authority_sanitized_paths"],
        )
        self.assertEqual(result["market_truth"], market_truth)
        self.assertEqual(result["data_health"]["data_truth"], market_truth)
        self.assertEqual(
            result["latest_order"],
            {
                "order_id": "order-1",
                "signal_id": "signal-1",
                "risk_request_id": "risk-1",
                "market_snapshot_id": "snapshot-1",
                "symbol": "BTC-USDT",
                "side": "BUY",
                "state": "FILLED",
                "updated_at": 123,
            },
        )
        self.assertEqual(
            result["summary"],
            {
                "symbol": "BTC-USDT",
                "strategy_id": "portfolio_rs_v2",
                "paper_armed": True,
                "paper_authorized": False,
                "paper_equity": 1000.0,
                "risk_status": "RUNTIME_READ_ONLY",
                "pipeline_status": "REVIEW",
                "pipeline_run_id": "run-1",
                "data_status": "STALE",
                "data_revision_status": "REVIEW",
                "revision_review_count": 3,
                "cross_source_review_count": 2,
                "audit_events": 7,
                "paper_ledger_backend": "sqlite",
                "paper_ledger_version": 4,
                "paper_ledger_restart_ready": True,
                "mutation_journal_status": "READY",
                "small_capital_plan_status": "NEEDS_EVIDENCE",
            },
        )
        self.assertEqual(result["updated_at"], 456)


if __name__ == "__main__":
    unittest.main()
