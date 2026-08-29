from copy import deepcopy
import json
import unittest

from tests import test_strategy_correlation_cluster_stability_report_consumer as report20_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    evaluate_strategy_correlation_cluster_temporal_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)


class StrategyCorrelationClusterTemporalStabilityReportConsumerTests(
    unittest.TestCase
):
    def setUp(self):
        self.report20_case = (
            report20_fixtures.StrategyCorrelationClusterStabilityReportConsumerTests(
                methodName="runTest"
            )
        )
        self.report20_case.setUp()

    def tearDown(self):
        self.report20_case.tearDown()

    def _fixture(self, *, low_effective_sample=False):
        report20, report19, registry_binding, stability_binding = (
            self.report20_case._fixture(
                low_effective_sample=low_effective_sample
            )
        )
        base_entry = report20["entries"][0]
        source_entry = report20["base_global_independence_extension"]["entries"][0]
        identity = {
            "strategy_id": base_entry["strategy_id"],
            "variant_id": base_entry["variant_id"],
            "lane": base_entry["lane"],
        }
        temporal_gate = evaluate_strategy_correlation_cluster_temporal_stability_gate(
            stability_binding["source_uncertainty_audit"],
            base_entry["stability_gate"],
            complete_link_gate=source_entry["complete_link_gate"],
            preregistration=source_entry["source_preregistration"],
            correlation_matrix=stability_binding["correlation_matrix"],
            selection_cells=stability_binding["selection_cells"],
            **identity,
        )
        temporal_binding = {
            **identity,
            "source_uncertainty_audit": stability_binding[
                "source_uncertainty_audit"
            ],
            "correlation_matrix": stability_binding["correlation_matrix"],
            "selection_cells": stability_binding["selection_cells"],
            "expected_temporal_stability_gate_hash": temporal_gate["gate_hash"],
        }
        decision_blockers = []
        if report20["decision"] != "PASS":
            decision_blockers.append("base_cluster_stability_decision_blocked")
        if temporal_gate["status"] != "PASS":
            decision_blockers.append(
                "cluster_temporal_stability_gate_blocked:"
                + ":".join(identity.values())
            )
        extension = {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": report20["base_report_hash"],
            "base_cluster_stability_extension": report20,
            "base_cluster_stability_extension_hash": report20["extension_hash"],
            "registry_bindings_required": True,
            "stability_bindings_required": True,
            "temporal_stability_gate_required": True,
            "external_temporal_stability_bindings_required": True,
            "entries": [
                {
                    **identity,
                    "temporal_stability_gate": temporal_gate,
                    "temporal_stability_gate_hash": temporal_gate["gate_hash"],
                }
            ],
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "consumer_only": True,
            "requires_new_report_schema": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": {"paper_authorized": False, "live_order_allowed": False},
        }
        extension = seal_strict_canonical_document(extension, "extension_hash")
        return (
            extension,
            report20,
            report19,
            registry_binding,
            stability_binding,
            temporal_binding,
        )

    def _verify(
        self,
        values,
        document=None,
        *,
        expected_report20_hash=None,
        temporal_bindings=None,
    ):
        extension, report20, report19, registry_binding, stability_binding, temporal_binding = values
        return verify_strategy_correlation_cluster_temporal_stability_report_extension(
            extension if document is None else document,
            expected_base_report_hash=report20["base_report_hash"],
            expected_global_independence_extension_hash=report19["extension_hash"],
            expected_cluster_stability_extension_hash=(
                report20["extension_hash"]
                if expected_report20_hash is None
                else expected_report20_hash
            ),
            expected_registry_bindings=[registry_binding],
            expected_stability_bindings=[stability_binding],
            expected_temporal_stability_bindings=(
                [temporal_binding]
                if temporal_bindings is None
                else temporal_bindings
            ),
        )

    def test_report20_remains_valid_without_temporal_evidence(self):
        _, report20, _, _, _, _ = self._fixture()
        self.assertEqual(report20["decision"], "PASS")
        self.assertNotIn("temporal", json.dumps(report20, sort_keys=True).lower())

    def test_valid_report21_passes_contract_and_decision(self):
        values = self._fixture()
        verification = self._verify(values)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(verification["temporal_stability_gate_count"], 1)
        self.assertEqual(verification["temporal_stability_gate_pass_count"], 1)
        self.assertIs(verification["writer_available"], False)

    def test_full_window_block_preserves_valid_contract_and_block_decision(self):
        values = self._fixture(low_effective_sample=True)
        extension = values[0]
        verification = self._verify(values)
        self.assertEqual(extension["base_cluster_stability_extension"]["decision"], "BLOCK")
        self.assertEqual(extension["entries"][0]["temporal_stability_gate"]["status"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(verification["temporal_stability_gate_pass_count"], 0)

    def test_entry_payload_excludes_external_replay_assets(self):
        entry = self._fixture()[0]["entries"][0]
        self.assertEqual(
            set(entry),
            {
                "strategy_id",
                "variant_id",
                "lane",
                "temporal_stability_gate",
                "temporal_stability_gate_hash",
            },
        )
        self.assertNotIn("source_uncertainty_audit", entry)
        self.assertNotIn("correlation_matrix", entry)
        self.assertNotIn("selection_cells", entry)

    def test_missing_external_binding_blocks_contract(self):
        values = self._fixture()
        verification = self._verify(values, temporal_bindings=[])
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "cluster_temporal_stability_identity_set_mismatch",
            verification["blockers"],
        )

    def test_wrong_caller_supplied_gate_hash_blocks_contract(self):
        values = self._fixture()
        binding = deepcopy(values[5])
        binding["expected_temporal_stability_gate_hash"] = "e" * 64
        verification = self._verify(values, temporal_bindings=[binding])
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                blocker.startswith("cluster_temporal_stability_gate_hash_mismatch:")
                for blocker in verification["blockers"]
            )
        )

    def test_identity_drift_blocks_before_gate_decision(self):
        values = self._fixture()
        document = deepcopy(values[0])
        document["entries"][0]["strategy_id"] = "DRIFT"
        document = seal_strict_canonical_document(document, "extension_hash")
        verification = self._verify(values, document)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "cluster_temporal_stability_identity_set_mismatch",
            verification["blockers"],
        )

    def test_resealed_temporal_gate_type_alias_is_independently_rejected(self):
        values = self._fixture()
        document = deepcopy(values[0])
        gate = document["entries"][0]["temporal_stability_gate"]
        gate["current_admission_allowed"] = 0
        gate = seal_strict_canonical_document(gate, "gate_hash")
        document["entries"][0]["temporal_stability_gate"] = gate
        document["entries"][0]["temporal_stability_gate_hash"] = gate["gate_hash"]
        document = seal_strict_canonical_document(document, "extension_hash")
        binding = deepcopy(values[5])
        binding["expected_temporal_stability_gate_hash"] = gate["gate_hash"]
        verification = self._verify(
            values,
            document,
            temporal_bindings=[binding],
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                blocker.startswith("cluster_temporal_stability_gate_invalid:")
                for blocker in verification["blockers"]
            )
        )

    def test_external_report20_hash_mismatch_blocks_contract(self):
        values = self._fixture()
        verification = self._verify(values, expected_report20_hash="d" * 64)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "cluster_stability_extension_hash_mismatch",
            verification["blockers"],
        )

    def test_root_native_alias_and_authority_escalation_are_rejected(self):
        values = self._fixture()
        alias = deepcopy(values[0])
        alias["target_report_schema_version"] = 21.0
        alias = seal_strict_canonical_document(alias, "extension_hash")
        escalated = deepcopy(values[0])
        escalated["permissions"]["live_order_allowed"] = True
        escalated = seal_strict_canonical_document(escalated, "extension_hash")
        alias_verification = self._verify(values, alias)
        escalated_verification = self._verify(values, escalated)
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation", escalated_verification["blockers"]
        )

    def test_duplicate_external_binding_is_rejected(self):
        values = self._fixture()
        verification = self._verify(
            values,
            temporal_bindings=[values[5], deepcopy(values[5])],
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("temporal_stability_bindings_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
