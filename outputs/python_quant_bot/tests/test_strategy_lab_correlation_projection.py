from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import strategy_lab_projection


class StrategyLabCorrelationProjectionTests(unittest.TestCase):
    def test_disconnected_projection_exposes_versioned_unknown_summary(self) -> None:
        projection = strategy_lab_projection.build_strategy_lab_projection(None)
        summary = projection["correlation_cluster_summary"]

        self.assertEqual(projection["lab_schema"], "strategy-lab-research-projection-v1")
        self.assertEqual(
            summary["schema_version"],
            "strategy-correlation-cluster-public-summary-v1",
        )
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertFalse(summary["current_writer_activation_allowed"])
        self.assertFalse(summary["current_admission_allowed"])
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])

    def test_projection_builds_summary_from_raw_gate_then_removes_raw_gate(self) -> None:
        raw_gate = {
            "schema_version": "private-test-gate",
            "private_symbol": "SHOULD_NOT_REACH_PUBLIC_PROJECTION",
            "clusters": [{"cluster_id": "private-cluster"}],
        }
        report = {
            "rows": [],
            "correlation_cluster_replayed_gate": raw_gate,
        }
        original = deepcopy(report)
        public_summary = strategy_lab_projection.build_correlation_cluster_public_summary(None)

        with patch.object(
            strategy_lab_projection,
            "build_correlation_cluster_public_summary",
            return_value=public_summary,
        ) as summary_builder:
            projection = strategy_lab_projection.build_strategy_lab_projection(report)

        summary_builder.assert_called_once_with(raw_gate)
        self.assertEqual(report, original)
        self.assertEqual(projection["correlation_cluster_summary"], public_summary)
        self.assertNotIn("correlation_cluster_replayed_gate", projection)
        serialized = json.dumps(projection, sort_keys=True)
        self.assertNotIn("SHOULD_NOT_REACH_PUBLIC_PROJECTION", serialized)
        self.assertNotIn("private-cluster", serialized)


if __name__ == "__main__":
    unittest.main()
