from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.portfolio_forward_projection import (
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V5_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V6_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION,
    build_portfolio_forward_status_projection,
)
from exchange_terminal.services.portfolio_forward_statistical_maturity import (
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
    PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
)


class PortfolioForwardProjectionTests(unittest.TestCase):
    def test_current_alias_is_v7_and_legacy_v6_cannot_project_maturity(self) -> None:
        self.assertEqual(
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION,
        )
        with patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_forward_observation_dashboard",
            return_value={"status": "UP_TO_DATE", "blockers": []},
        ), patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_portfolio_forward_statistical_maturity",
            return_value={"status": "BLOCK"},
        ) as maturity_builder:
            result = build_portfolio_forward_status_projection(
                {"status": "PASS"},
                observed_now_ms=456,
                live_trading_hard_block=True,
                active_candidate={"candidate_hash": "legacy-must-not-route"},
                dashboard_schema_version=(
                    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V6_SCHEMA_VERSION
                ),
            )

        dashboard = result["incremental_observation"]
        self.assertEqual(
            dashboard["schema_version"],
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V6_SCHEMA_VERSION,
        )
        self.assertEqual(dashboard["status"], "BLOCK")
        self.assertIn(
            "portfolio_forward_dashboard_legacy_maturity_not_current",
            dashboard["blockers"],
        )
        self.assertIsNone(maturity_builder.call_args.kwargs["active_candidate"])
        self.assertEqual(
            maturity_builder.call_args.kwargs["maturity_schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V2_SCHEMA_VERSION,
        )

    def test_dashboard_v7_is_explicit_and_routes_only_to_maturity_v3(self) -> None:
        operational = {
            "schema_version": "portfolio-forward-dashboard-v4",
            "status": "UP_TO_DATE",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        maturity = {
            "schema_version": PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
            "status": "REVIEW_REQUIRED",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_forward_observation_dashboard",
            return_value=operational,
        ), patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_portfolio_forward_statistical_maturity",
            return_value=maturity,
        ) as maturity_builder:
            result = build_portfolio_forward_status_projection(
                {"status": "BLOCK"},
                observed_now_ms=456,
                live_trading_hard_block=True,
                active_candidate={"candidate_hash": "candidate"},
                dashboard_schema_version=(
                    PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION
                ),
            )

        dashboard = result["incremental_observation"]
        self.assertEqual(
            dashboard["schema_version"],
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION,
        )
        self.assertEqual(
            dashboard["statistical_maturity"]["schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        )
        self.assertEqual(
            maturity_builder.call_args.kwargs["maturity_schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        )

    def test_unknown_dashboard_route_is_v7_shaped_and_fail_closed(self) -> None:
        operational = {
            "schema_version": "portfolio-forward-dashboard-v4",
            "status": "UP_TO_DATE",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        maturity = {
            "schema_version": PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
            "status": "BLOCK",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        with patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_forward_observation_dashboard",
            return_value=operational,
        ), patch(
            "exchange_terminal.services.portfolio_forward_projection."
            "build_portfolio_forward_statistical_maturity",
            return_value=maturity,
        ) as maturity_builder:
            result = build_portfolio_forward_status_projection(
                {"status": "BLOCK"},
                observed_now_ms=456,
                live_trading_hard_block=True,
                active_candidate={"candidate_hash": "must-not-route"},
                dashboard_schema_version="portfolio-forward-dashboard-v999",
            )

        self.assertEqual(
            result["incremental_observation"]["schema_version"],
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V7_SCHEMA_VERSION,
        )
        self.assertEqual(result["incremental_observation"]["status"], "BLOCK")
        self.assertIn(
            "portfolio_forward_dashboard_schema_unsupported",
            result["incremental_observation"]["blockers"],
        )
        self.assertEqual(
            result["incremental_observation"]["statistical_maturity"]["status"],
            "BLOCK",
        )
        self.assertIsNone(maturity_builder.call_args.kwargs["active_candidate"])
        self.assertEqual(
            maturity_builder.call_args.kwargs["maturity_schema_version"],
            PORTFOLIO_FORWARD_STATISTICAL_MATURITY_V3_SCHEMA_VERSION,
        )

    def test_projection_is_pure_overrides_authority_and_forwards_evidence(self) -> None:
        payload = {
            "status": "BLOCK",
            "blockers": ["candidate_missing"],
            "read_only": False,
            "paper_authorized": True,
            "live_order_allowed": True,
            "nested": [{"ｃａｎ－ｔｒａｄｅ": True}],
            "incremental_observation": {"status": "READY", "live_order_allowed": True},
        }
        evidence = {"status": "BLOCK", "blockers": ["attempt_evidence_invalid"]}
        dashboard = {
            "schema_version": "portfolio-forward-dashboard-v4",
            "status": "UP_TO_DATE",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        maturity = {
            "schema_version": "portfolio-forward-statistical-maturity-v1",
            "status": "BLOCK",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        candidate = {"candidate_hash": "candidate"}
        observer = {"candidate_hash": "candidate"}
        performance = {"candidate_hash": "candidate"}
        backup = {"schema_version": "portfolio-forward-backup-status-v2"}
        watchdog = {"schema_version": "portfolio-forward-watchdog-v3"}
        before = copy.deepcopy(payload)

        with patch(
            "exchange_terminal.services.portfolio_forward_projection.build_forward_observation_dashboard",
            return_value=dashboard,
        ) as builder, patch(
            "exchange_terminal.services.portfolio_forward_projection.build_portfolio_forward_statistical_maturity",
            return_value=maturity,
        ) as maturity_builder:
            result = build_portfolio_forward_status_projection(
                payload,
                observed_now_ms=456,
                live_trading_hard_block=True,
                observer_artifact_evidence=evidence,
                active_candidate=candidate,
                observer_status=observer,
                performance_status=performance,
                backup_status=backup,
                watchdog_status=watchdog,
                backup_read_status="READABLE",
                watchdog_read_status="READABLE",
            )

        self.assertEqual(payload, before)
        self.assertIs(result["read_only"], True)
        self.assertIs(result["paper_authorized"], False)
        self.assertIs(result["live_order_allowed"], False)
        self.assertIs(payload["nested"][0]["ｃａｎ－ｔｒａｄｅ"], True)
        self.assertIs(result["nested"][0]["ｃａｎ－ｔｒａｄｅ"], False)
        self.assertEqual(authority_violations(result), [])
        self.assertEqual(
            result["incremental_observation"],
            {
                **dashboard,
                "schema_version": PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
                "statistical_maturity": maturity,
            },
        )
        self.assertEqual(result["incremental_observation"]["status"], "UP_TO_DATE")
        self.assertEqual(result["incremental_observation"]["statistical_maturity"]["status"], "BLOCK")
        projected_status = builder.call_args.args[0]
        self.assertIsNot(projected_status, payload)
        self.assertIs(projected_status["read_only"], True)
        self.assertIs(projected_status["paper_authorized"], False)
        self.assertIs(projected_status["live_order_allowed"], False)
        self.assertEqual(builder.call_args.kwargs["now_ms"], 456)
        self.assertIs(builder.call_args.kwargs["live_trading_hard_block"], True)
        self.assertEqual(builder.call_args.kwargs["observer_artifact_evidence"], evidence)
        self.assertEqual(maturity_builder.call_args.kwargs["active_candidate"], candidate)
        self.assertEqual(maturity_builder.call_args.kwargs["observer_status"], observer)
        self.assertEqual(maturity_builder.call_args.kwargs["performance_status"], performance)
        self.assertEqual(maturity_builder.call_args.kwargs["backup_status"], backup)
        self.assertEqual(maturity_builder.call_args.kwargs["watchdog_status"], watchdog)
        self.assertEqual(maturity_builder.call_args.kwargs["backup_read_status"], "READABLE")
        self.assertEqual(maturity_builder.call_args.kwargs["watchdog_read_status"], "READABLE")
        self.assertEqual(maturity_builder.call_args.kwargs["observed_now_ms"], 456)
        self.assertEqual(
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_V5_SCHEMA_VERSION,
            "portfolio-forward-dashboard-v5",
        )

    def test_real_dashboard_projection_remains_fail_closed(self) -> None:
        payload = {
            "status": "BLOCK",
            "blockers": ["candidate_missing"],
            "scheduler": {},
            "experiment_registry": {},
        }

        result = build_portfolio_forward_status_projection(
            payload,
            observed_now_ms=1_700_000_000_000,
            live_trading_hard_block=True,
        )

        dashboard = result["incremental_observation"]
        self.assertEqual(
            dashboard["schema_version"],
            PORTFOLIO_FORWARD_INCREMENTAL_DASHBOARD_SCHEMA_VERSION,
        )
        self.assertEqual(dashboard["status"], "BLOCK")
        self.assertIn("candidate_missing", dashboard["blockers"])
        self.assertIs(dashboard["read_only"], True)
        self.assertIs(dashboard["observation_only"], True)
        self.assertIs(dashboard["simulation_only"], True)
        self.assertIs(dashboard["paper_authorized"], False)
        self.assertIs(dashboard["live_order_allowed"], False)
        self.assertIs(dashboard["live_trading_hard_block"], True)
        self.assertEqual(dashboard["statistical_maturity"]["status"], "BLOCK")
        self.assertIs(dashboard["statistical_maturity"]["paper_authorized"], False)
        self.assertIs(dashboard["statistical_maturity"]["live_order_allowed"], False)

    def test_residual_authority_after_sanitization_returns_a_fixed_block_shell(self) -> None:
        operational = {
            "schema_version": "portfolio-forward-dashboard-v4",
            "status": "UP_TO_DATE",
        }
        with patch(
            "exchange_terminal.services.portfolio_forward_projection.build_forward_observation_dashboard",
            return_value=operational,
        ), patch(
            "exchange_terminal.services.portfolio_forward_projection.sanitize_authority_claims",
            return_value=({"nested": {"canTrade": True}}, []),
        ):
            result = build_portfolio_forward_status_projection(
                {"status": "READY", "private": "must-not-survive"},
                observed_now_ms=456,
                live_trading_hard_block=True,
            )

        self.assertEqual(result["status"], "BLOCK")
        self.assertNotIn("private", result)
        self.assertEqual(authority_violations(result), [])
        self.assertEqual(
            result["incremental_observation"]["statistical_maturity"]["status"],
            "BLOCK",
        )


if __name__ == "__main__":
    unittest.main()
