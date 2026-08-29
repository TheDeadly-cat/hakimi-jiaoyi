from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_multiplicity_projection as projection,
)
from exchange_terminal.services.strategy_lab_projection import (
    build_strategy_lab_projection,
)


class StrategyCorrelationMultiplicityProjectionTests(unittest.TestCase):
    @staticmethod
    def _protocol() -> dict[str, object]:
        return {"schema_version": "strategy-matrix-protocol-v5"}

    @staticmethod
    def _source(**overrides: object) -> dict[str, object]:
        source: dict[str, object] = {
            "schema_version": (
                "strategy-correlation-multiplicity-report-evidence-v1"
            ),
            "status": "PASS",
            "decision_status": "PASS",
            "expected_family_size": 7,
            "observed_family_size": 7,
            "gate_status": "PASS",
            "uncertainty_status": "PASS",
            "multiplicity_status": "PASS",
            "required_matrix_report_schema_version": 8,
            "formal_registry_bound": False,
            "current_report_schema_bound": False,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "parameter_selection_allowed": False,
            "performance_claim_allowed": False,
            "profitability_proven": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
            "blockers": [],
        }
        source.update(overrides)
        return source

    def test_unknown_summary_is_versioned_and_authority_free(self) -> None:
        summary = projection.build_strategy_correlation_multiplicity_public_summary(
            None,
            protocol={},
            report_schema_version=None,
        )
        self.assertEqual(
            summary["schema_version"],
            "strategy-correlation-multiplicity-public-summary-v1",
        )
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["gap_category"], "SOURCE_INVALID")
        self.assertIsNone(summary["expected_family_size"])
        self.assertFalse(summary["current_writer_activation_allowed"])
        self.assertFalse(summary["paper_authorized"])
        self.assertFalse(summary["live_order_allowed"])

    def test_verified_family_summary_exposes_only_aggregate_budget(self) -> None:
        source = self._source()
        with patch.object(
            projection,
            "verify_strategy_correlation_multiplicity_report_evidence",
            return_value={
                "status": "PASS",
                "evidence_status": "PASS",
                "blockers": [],
            },
        ):
            summary = projection.build_strategy_correlation_multiplicity_public_summary(
                source,
                protocol=self._protocol(),
                report_schema_version=16,
            )
        self.assertEqual(summary["status"], "OBSERVED_NO_FAMILY_WISE_BLOCK")
        self.assertEqual(summary["decision_status"], "PASS")
        self.assertEqual(summary["expected_family_size"], 7)
        self.assertEqual(summary["observed_family_size"], 7)
        self.assertAlmostEqual(summary["per_pair_alpha"], 0.05 / 7, places=15)
        self.assertEqual(summary["gap_category"], "NONE_OBSERVED")
        self.assertEqual(
            projection.verify_strategy_correlation_multiplicity_public_summary(
                summary
            )["status"],
            "PASS",
        )
        tampered = deepcopy(summary)
        tampered["per_pair_alpha"] = 0.05
        self.assertEqual(
            projection.verify_strategy_correlation_multiplicity_public_summary(
                tampered
            )["status"],
            "BLOCK",
        )

    def test_blocked_family_decision_stays_descriptive_block(self) -> None:
        source = self._source(
            decision_status="BLOCK",
            multiplicity_status="BLOCK",
            blockers=["private_pair_identity"],
        )
        with patch.object(
            projection,
            "verify_strategy_correlation_multiplicity_report_evidence",
            return_value={
                "status": "PASS",
                "evidence_status": "PASS",
                "blockers": [],
            },
        ):
            summary = projection.build_strategy_correlation_multiplicity_public_summary(
                source,
                protocol=self._protocol(),
                report_schema_version=16,
            )
        self.assertEqual(summary["status"], "OBSERVED_FAMILY_WISE_BLOCK")
        self.assertEqual(
            summary["gap_category"],
            "FAMILY_WISE_MULTIPLICITY_BLOCK",
        )
        self.assertFalse(summary["parameter_selection_allowed"])
        self.assertFalse(summary["performance_claim_allowed"])


class StrategyLabMultiplicityProjectionTests(unittest.TestCase):
    def test_lab_redacts_raw_family_evidence_and_keeps_parent_schema(self) -> None:
        source = StrategyCorrelationMultiplicityProjectionTests._source()
        sensitive = {
            **source,
            "protocol_hash": "a" * 64,
            "replayed_gate": {"symbol": "AAPL"},
            "multiplicity_audit": {"pairs": [{"left_symbol": "AAPL"}]},
            "family_binding_assessment": {"cluster_id": "private-cluster"},
        }
        report = {
            "schema_version": 16,
            "research_governance": {
                "protocol": {"schema_version": "strategy-matrix-protocol-v5"},
            },
            "correlation_multiplicity_evidence": sensitive,
            "rows": [{
                "label": "planning",
                "multiplicity_evidence": sensitive,
            }],
        }
        original = deepcopy(report)
        with patch.object(
            projection,
            "verify_strategy_correlation_multiplicity_report_evidence",
            return_value={
                "status": "PASS",
                "evidence_status": "PASS",
                "blockers": [],
            },
        ):
            public = build_strategy_lab_projection(report)

        summary = public["correlation_multiplicity_summary"]
        self.assertEqual(
            public["lab_schema"],
            "strategy-lab-research-projection-v1",
        )
        self.assertEqual(public["rows"], [])
        self.assertNotIn("research_governance", public)
        self.assertEqual(summary["status"], "OBSERVED_NO_FAMILY_WISE_BLOCK")
        self.assertEqual(report, original)
        serialized = json.dumps(public, sort_keys=True)
        for forbidden in (
            "correlation_multiplicity_evidence",
            "multiplicity_evidence",
            "multiplicity_audit",
            "family_binding_assessment",
            "private-cluster",
            "AAPL",
            "protocol_hash",
            "left_symbol",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
