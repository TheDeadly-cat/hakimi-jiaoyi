import copy
import json
import unittest

from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
)
from exchange_terminal.services.strategy_correlation_strata_protocol import (
    build_strategy_correlation_strata_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_strata_protocol_projection import (
    build_strategy_correlation_strata_protocol_migration_public_summary,
    verify_strategy_correlation_strata_protocol_migration_public_summary,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)
from tests import test_strategy_correlation_strata_protocol


class StrategyCorrelationStrataProtocolProjectionTests(unittest.TestCase):
    SOURCE_HASH = "a" * 64

    @staticmethod
    def _hash(document, field):
        return strict_canonical_hash(
            {key: value for key, value in document.items() if key != field}
        )

    def _protocol(self):
        fixture = (
            test_strategy_correlation_strata_protocol
            .StrategyCorrelationStrataProtocolTests(
                methodName=(
                    "test_registration_targets_report18_protocol_v7_"
                    "without_authority"
                )
            )
        )
        _, source_v6 = fixture._source_v6()
        protocol = build_strategy_correlation_strata_protocol_registration(
            source_v6
        )
        source_v3 = protocol["source_registration"]["source_registration"]
        source_preregistration = source_v3[
            "source_protocol_registration"
        ]["preregistration"]
        return protocol, source_preregistration

    def _registry(self, *, expected_source_hash=None):
        protocol, source_preregistration = self._protocol()
        dimensions = [
            {
                "dimension_id": "asset-family",
                "strata": [
                    {
                        "stratum_id": f"family-{index}",
                        "cluster_ids": [cluster["cluster_id"]],
                    }
                    for index, cluster in enumerate(
                        source_preregistration["clusters"],
                        start=1,
                    )
                ],
            }
        ]
        registration = build_strategy_correlation_strata_preregistration(
            source_preregistration,
            dimensions,
        )
        asset = build_strategy_correlation_strata_registry_asset(
            source_preregistration,
            dimensions,
            registry_id="candidate-1",
            classification_source="external-source",
            classification_source_version="v1",
            classification_source_hash=self.SOURCE_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        bound_source_hash = expected_source_hash or self.SOURCE_HASH
        binding = assess_strategy_correlation_strata_registry_binding(
            asset,
            registration,
            source_preregistration,
            selection_cutoff_date="2026-08-02",
            expected_registry_asset_hash=asset["registry_asset_hash"],
            expected_classification_source_hash=bound_source_hash,
        )
        inputs = {
            "registry_binding": binding,
            "registry_asset": asset,
            "strata_registration": registration,
            "source_preregistration": source_preregistration,
            "selection_cutoff_date": "2026-08-02",
            "expected_registry_asset_hash": asset["registry_asset_hash"],
            "expected_classification_source_hash": bound_source_hash,
        }
        return protocol, inputs

    def test_protocol_only_projects_real_registry_gap(self):
        protocol, _ = self._protocol()
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol
            )
        )
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["protocol_target"], "PROTOCOL_V7")
        self.assertEqual(summary["source"]["report_target"], "REPORT18")
        self.assertEqual(
            summary["gap"]["status"],
            "REAL_REGISTRY_ASSET_NOT_SUPPLIED",
        )
        self.assertEqual(
            summary["maturity"]["status"],
            "PROTOCOL_PREREGISTERED",
        )

    def test_bound_candidate_remains_pending_formal_persistence(self):
        protocol, inputs = self._registry()
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol,
                **inputs,
            )
        )
        self.assertEqual(
            summary["gap"]["status"],
            "FORMAL_PERSISTENCE_AND_WRITER_PENDING",
        )
        self.assertEqual(summary["gap"]["registry_binding_status"], "BOUND")
        self.assertEqual(
            summary["maturity"]["status"],
            "REGISTRY_BOUND_CANDIDATE",
        )
        self.assertEqual(summary["maturity"]["formal_registry"], "PENDING")
        self.assertEqual(summary["maturity"]["writer"], "NOT_IMPLEMENTED")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_registry_binding_block_is_observed_without_activation(self):
        protocol, inputs = self._registry(expected_source_hash="c" * 64)
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol,
                **inputs,
            )
        )
        self.assertEqual(
            summary["gap"]["status"],
            "REGISTRY_BINDING_BLOCK_OBSERVED",
        )
        self.assertEqual(summary["gap"]["registry_binding_status"], "BLOCK")
        self.assertEqual(
            summary["maturity"]["status"],
            "PROTOCOL_PREREGISTERED",
        )

    def test_partial_registry_inputs_fail_closed_to_unknown(self):
        protocol, inputs = self._registry()
        partial = dict(inputs)
        partial.pop("expected_classification_source_hash")
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol,
                **partial,
            )
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertEqual(summary["gap"]["status"], "UNKNOWN")

    def test_registry_from_different_preregistration_is_unknown(self):
        protocol, inputs = self._registry()
        mismatched = copy.deepcopy(inputs["source_preregistration"])
        mismatched["preregistration_hash"] = "d" * 64
        inputs["source_preregistration"] = mismatched
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol,
                **inputs,
            )
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")

    def test_resealed_protocol_authority_escalation_is_unknown(self):
        protocol, _ = self._protocol()
        tampered = copy.deepcopy(protocol)
        tampered["formal_registry_activation_allowed"] = True
        tampered["registration_hash"] = self._hash(
            tampered,
            "registration_hash",
        )
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                tampered
            )
        )
        self.assertEqual(summary["source"]["status"], "UNKNOWN")
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_public_summary_is_redacted_and_exactly_rebuildable(self):
        protocol, inputs = self._registry()
        summary = (
            build_strategy_correlation_strata_protocol_migration_public_summary(
                protocol,
                **inputs,
            )
        )
        serialized = json.dumps(summary, sort_keys=True)
        source = inputs["source_preregistration"]
        for hidden in [
            *(cluster["cluster_id"] for cluster in source["clusters"]),
            inputs["registry_asset"]["registry_id"],
            inputs["registry_asset"]["registry_asset_hash"],
            self.SOURCE_HASH,
            inputs["selection_cutoff_date"],
        ]:
            self.assertNotIn(hidden, serialized)
        self.assertTrue(
            all(value is False for value in summary["redaction"].values())
        )
        self.assertEqual(
            verify_strategy_correlation_strata_protocol_migration_public_summary(
                summary,
                source_protocol_registration=protocol,
                **inputs,
            )["status"],
            "PASS",
        )
        tampered = copy.deepcopy(summary)
        tampered["permission"]["paper_authorized"] = True
        self.assertEqual(
            verify_strategy_correlation_strata_protocol_migration_public_summary(
                tampered,
                source_protocol_registration=protocol,
                **inputs,
            )["status"],
            "BLOCK",
        )


if __name__ == "__main__":
    unittest.main()
