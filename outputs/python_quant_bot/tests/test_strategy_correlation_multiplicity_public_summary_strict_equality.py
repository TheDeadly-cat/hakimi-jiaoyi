"""Type-strict public contract for correlation multiplicity summaries."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_multiplicity_projection as projection,
)


class StrategyCorrelationMultiplicityPublicSummaryStrictEqualityTests(
    unittest.TestCase
):
    @staticmethod
    def _protocol():
        return {"schema_version": "strategy-matrix-protocol-v5"}

    @staticmethod
    def _source():
        return {
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

    def test_source_bound_and_standalone_aliases_are_blocked(self):
        source = self._source()
        protocol = self._protocol()
        source_verification = {
            "status": "PASS",
            "evidence_status": "PASS",
            "blockers": [],
        }
        with patch.object(
            projection,
            "verify_strategy_correlation_multiplicity_report_evidence",
            return_value=source_verification,
        ):
            summary = projection.build_strategy_correlation_multiplicity_public_summary(
                source,
                protocol=protocol,
                report_schema_version=16,
            )
            verification_modes = (
                ("standalone", {}),
                (
                    "source_bound",
                    {
                        "source_evidence": source,
                        "protocol": protocol,
                        "report_schema_version": 16,
                    },
                ),
            )
            for _, kwargs in verification_modes:
                self.assertEqual(
                    projection
                    .verify_strategy_correlation_multiplicity_public_summary(
                        summary,
                        **kwargs,
                    )["status"],
                    "PASS",
                )

            aliases = [
                (field, int(summary[field]))
                for field in (
                    "external_authenticity_proven",
                    "profitability_proven",
                    "performance_claim_allowed",
                    "parameter_selection_allowed",
                    "formal_registry_bound",
                    "current_report_schema_bound",
                    "requires_current_consumer_activation",
                    "current_writer_activation_allowed",
                    "current_admission_allowed",
                    "paper_authorized",
                    "live_order_allowed",
                )
            ]
            aliases.extend((
                (
                    "required_report_schema_version",
                    float(summary["required_report_schema_version"]),
                ),
                (
                    "required_matrix_report_schema_version",
                    float(summary["required_matrix_report_schema_version"]),
                ),
            ))

            attacks = 0
            for mode, kwargs in verification_modes:
                for field, alias in aliases:
                    candidate = deepcopy(summary)
                    candidate[field] = alias
                    with self.subTest(mode=mode, field=field):
                        verification = (
                            projection
                            .verify_strategy_correlation_multiplicity_public_summary(
                                candidate,
                                **kwargs,
                            )
                        )
                        self.assertEqual(verification["status"], "BLOCK")
                        self.assertIn(
                            "strategy_correlation_multiplicity_public_summary_fixed_value:"
                            + field,
                            verification["blockers"],
                        )
                        if mode == "source_bound":
                            self.assertIn(
                                "strategy_correlation_multiplicity_public_summary_source_mismatch",
                                verification["blockers"],
                            )
                    attacks += 1

            self.assertEqual(len(aliases), 13)
            self.assertEqual(attacks, 26)


if __name__ == "__main__":
    unittest.main()
