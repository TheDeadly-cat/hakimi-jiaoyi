from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_projection
from exchange_terminal.services.strategy_lab_projection import (
    build_strategy_lab_projection,
)


class StrategyLabUncertaintyProjectionTests(unittest.TestCase):
    def _source(self) -> dict[str, object]:
        return {
            "schema_version": "strategy-correlation-uncertainty-audit-v2",
            "status": "PASS",
            "uncertainty_policy": (
                "FISHER_Z_95_WITH_LAG1_EFFECTIVE_N_DESCRIPTIVE_V1"
            ),
            "effective_sample_method": "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1",
            "lookback_observations": 60,
            "required_price_rows": 61,
            "minimum_pair_overlap": 40,
            "minimum_effective_observations": 12.0,
            "confidence_level": 0.95,
            "absolute_pearson_threshold": 0.75,
            "pair_count": 10,
            "cross_cluster_pair_count": 7,
            "confirmed_high_cross_cluster_count": 0,
            "ambiguous_cross_cluster_count": 0,
            "insufficient_effective_sample_pair_count": 0,
            "external_authenticity_proven": False,
            "profitability_proven": False,
            "performance_claim_allowed": False,
            "parameter_selection_allowed": False,
            "requires_new_report_schema": True,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "pairs": [{
                "left_symbol": "AAPL",
                "right_symbol": "MSFT",
                "correlation": 0.91,
            }],
            "matrix_replay": {"replay_hash": "a" * 64},
            "audit_hash": "b" * 64,
            "policy_hash": "c" * 64,
            "blockers": ["sensitive_internal_blocker"],
        }

    def test_disconnected_projection_exposes_versioned_unknown_summary(self) -> None:
        projection = build_strategy_lab_projection({})
        summary = projection["correlation_uncertainty_summary"]
        self.assertEqual(
            summary["schema_version"],
            "strategy-correlation-uncertainty-public-summary-v1",
        )
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["gap_category"], "SOURCE_INVALID")
        self.assertEqual(summary["maturity"], "DESCRIPTIVE_ONLY")
        self.assertEqual(summary["permission"], "RESEARCH_ONLY")
        self.assertNotIn("correlation_uncertainty_audit", projection)

    def test_projection_builds_redacted_summary_then_removes_raw_audit(self) -> None:
        source = self._source()
        report = {
            "correlation_uncertainty_audit": source,
            "rows": [{
                "correlation_uncertainty_audit": source,
                "label": "planning",
            }],
        }
        with patch.object(
            strategy_correlation_uncertainty_projection,
            "verify_strategy_correlation_uncertainty_audit",
            return_value={"status": "PASS", "blockers": []},
        ):
            projection = build_strategy_lab_projection(report)
        summary = projection["correlation_uncertainty_summary"]
        self.assertEqual(summary["status"], "OBSERVED_NO_UNCERTAINTY_BLOCK")
        self.assertEqual(summary["gap_category"], "NONE_OBSERVED")
        self.assertEqual(summary["pair_count"], 10)
        self.assertEqual(summary["cross_cluster_pair_count"], 7)
        self.assertEqual(report["correlation_uncertainty_audit"], source)
        serialized = json.dumps(projection, sort_keys=True)
        for forbidden in (
            "correlation_uncertainty_audit",
            "AAPL",
            "MSFT",
            "replay_hash",
            "audit_hash",
            "policy_hash",
            "sensitive_internal_blocker",
        ):
            self.assertNotIn(forbidden, serialized)
        for forbidden_key in (
            '"pairs":',
            '"matrix_replay":',
            '"left_symbol":',
            '"right_symbol":',
            '"correlation":',
            '"blockers":',
        ):
            self.assertNotIn(forbidden_key, serialized)
        for field in (
            "current_writer_activation_allowed",
            "current_admission_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertIs(summary[field], False)

    def test_invalid_raw_audit_is_removed_and_cannot_escape_unknown(self) -> None:
        source = self._source()
        projection = build_strategy_lab_projection({
            "correlation_uncertainty_audit": source,
        })
        summary = projection["correlation_uncertainty_summary"]
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["gap_category"], "SOURCE_INVALID")
        self.assertNotIn("AAPL", json.dumps(projection, sort_keys=True))
        self.assertNotIn("correlation_uncertainty_audit", projection)


if __name__ == "__main__":
    unittest.main()
