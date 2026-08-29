from __future__ import annotations

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from exchange_terminal.services import strategy_correlation_uncertainty_projection as projection


class StrategyCorrelationUncertaintyProjectionTests(unittest.TestCase):
    def _source(self, **overrides: object) -> dict[str, object]:
        source: dict[str, object] = {
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
            "audit_hash": "a" * 64,
            "policy_hash": "b" * 64,
            "blockers": [],
            "pairs": [{
                "left_symbol": "AAPL",
                "right_symbol": "MSFT",
                "left_cluster_id": "mega_cap",
                "correlation": 0.92,
                "absolute_correlation_interval_lower": 0.84,
            }],
            "matrix_replay": {
                "completed_price_input": {"sensitive": True},
                "replay_hash": "c" * 64,
            },
        }
        source.update(overrides)
        return source

    def _build_verified(self, source: dict[str, object]) -> dict[str, object]:
        with patch.object(
            projection,
            "verify_strategy_correlation_uncertainty_audit",
            return_value={"status": "PASS", "blockers": []},
        ):
            return projection.build_strategy_correlation_uncertainty_public_summary(
                source
            )

    def test_valid_source_is_exactly_redacted_and_descriptive_only(self) -> None:
        source = self._source()
        summary = self._build_verified(source)
        self.assertEqual(
            summary["schema_version"],
            "strategy-correlation-uncertainty-public-summary-v1",
        )
        self.assertEqual(summary["status"], "OBSERVED_NO_UNCERTAINTY_BLOCK")
        self.assertEqual(summary["gap_category"], "NONE_OBSERVED")
        self.assertEqual(summary["pair_count"], 10)
        self.assertEqual(summary["cross_cluster_pair_count"], 7)
        self.assertEqual(summary["maturity"], "DESCRIPTIVE_ONLY")
        self.assertEqual(summary["permission"], "RESEARCH_ONLY")
        self.assertTrue(summary["requires_new_report_schema"])
        for field in (
            "external_authenticity_proven",
            "profitability_proven",
            "performance_claim_allowed",
            "parameter_selection_allowed",
            "current_writer_activation_allowed",
            "current_admission_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertIs(summary[field], False)
        serialized = json.dumps(summary, sort_keys=True)
        for forbidden in (
            "AAPL",
            "MSFT",
            "mega_cap",
            "audit_hash",
            "policy_hash",
            "matrix_replay",
            "replay_hash",
            "left_symbol",
            "blockers",
        ):
            self.assertNotIn(forbidden, serialized)
        for forbidden_key in (
            '"pairs":',
            '"left_cluster_id":',
            '"right_cluster_id":',
            '"correlation":',
            '"absolute_correlation":',
            '"absolute_correlation_interval_lower":',
            '"absolute_correlation_interval_upper":',
        ):
            self.assertNotIn(forbidden_key, serialized)
        self.assertEqual(
            projection.verify_strategy_correlation_uncertainty_public_summary(
                summary
            )["status"],
            "PASS",
        )

    def test_block_categories_are_aggregated_without_pair_disclosure(self) -> None:
        cases = (
            (
                {"confirmed_high_cross_cluster_count": 1},
                "CROSS_CLUSTER_CONFIRMED_HIGH",
            ),
            (
                {"ambiguous_cross_cluster_count": 1},
                "CROSS_CLUSTER_AMBIGUOUS",
            ),
            (
                {"insufficient_effective_sample_pair_count": 1},
                "EFFECTIVE_SAMPLE_INSUFFICIENT",
            ),
            (
                {
                    "confirmed_high_cross_cluster_count": 1,
                    "ambiguous_cross_cluster_count": 1,
                },
                "MULTIPLE_CROSS_CLUSTER_UNCERTAINTY_GAPS",
            ),
        )
        for count_overrides, expected_gap in cases:
            with self.subTest(expected_gap=expected_gap):
                summary = self._build_verified(
                    self._source(status="BLOCK", **count_overrides)
                )
                self.assertEqual(
                    summary["status"],
                    "OBSERVED_UNCERTAINTY_BLOCK",
                )
                self.assertEqual(summary["gap_category"], expected_gap)
                self.assertEqual(
                    projection.verify_strategy_correlation_uncertainty_public_summary(
                        summary
                    )["status"],
                    "PASS",
                )

    def test_invalid_source_returns_fixed_unknown_without_echo(self) -> None:
        source = self._source()
        summary = projection.build_strategy_correlation_uncertainty_public_summary(
            source
        )
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertEqual(summary["gap_category"], "SOURCE_INVALID")
        for field in projection._COUNT_FIELDS:
            self.assertIsNone(summary[field])
        self.assertNotIn("AAPL", json.dumps(summary, sort_keys=True))
        self.assertEqual(
            projection.verify_strategy_correlation_uncertainty_public_summary(
                summary
            )["status"],
            "PASS",
        )

    def test_verified_source_still_fails_closed_on_drift_or_pseudo_counts(self) -> None:
        cases = (
            {"confidence_level": 0.90},
            {"pair_count": "10"},
            {"pair_count": True},
            {"cross_cluster_pair_count": 11},
            {"current_admission_allowed": True},
            {"permissions": {"paper_authorized": True, "live_order_allowed": False}},
            {
                "status": "PASS",
                "ambiguous_cross_cluster_count": 1,
            },
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                summary = self._build_verified(self._source(**overrides))
                self.assertEqual(summary["status"], "UNKNOWN")
                self.assertEqual(summary["gap_category"], "SOURCE_INVALID")

    def test_public_summary_verifier_rejects_tamper_and_authority_aliases(self) -> None:
        baseline = self._build_verified(self._source())
        cases = []
        extra = deepcopy(baseline)
        extra["left_symbol"] = "AAPL"
        cases.append(extra)
        pseudo = deepcopy(baseline)
        pseudo["pair_count"] = "10"
        cases.append(pseudo)
        impossible = deepcopy(baseline)
        impossible["cross_cluster_pair_count"] = 11
        cases.append(impossible)
        authority = deepcopy(baseline)
        authority["paper_authorized"] = True
        cases.append(authority)
        false_clear = deepcopy(baseline)
        false_clear["ambiguous_cross_cluster_count"] = 1
        cases.append(false_clear)
        for document in cases:
            with self.subTest(document=document):
                verification = (
                    projection.verify_strategy_correlation_uncertainty_public_summary(
                        document
                    )
                )
                self.assertEqual(verification["status"], "BLOCK")
                self.assertFalse(verification["current_writer_activation_allowed"])
                self.assertFalse(verification["current_admission_allowed"])
                self.assertFalse(verification["paper_authorized"])
                self.assertFalse(verification["live_order_allowed"])

    def test_source_bound_verification_rejects_coherent_public_rewrite(self) -> None:
        source = self._source()
        baseline = self._build_verified(source)
        rewritten = deepcopy(baseline)
        rewritten["status"] = "OBSERVED_UNCERTAINTY_BLOCK"
        rewritten["gap_category"] = "SOURCE_EVIDENCE_BLOCK"
        with patch.object(
            projection,
            "verify_strategy_correlation_uncertainty_audit",
            return_value={"status": "PASS", "blockers": []},
        ):
            verification = (
                projection.verify_strategy_correlation_uncertainty_public_summary(
                    rewritten,
                    source_audit=source,
                )
            )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "strategy_correlation_uncertainty_public_summary_source_mismatch",
            verification["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
