from __future__ import annotations

import copy
import unittest

from exchange_terminal.services import (
    strategy_correlation_expected_gate_hash_timing_receipt as receipt_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_expected_gate_hash_timing_receipt import (
    ANCHOR_PAYLOAD_SCHEMA_VERSION,
    AUTHORITY_GAPS,
    RECEIPT_SCHEMA_VERSION,
    STABILITY_GATE_STAGE,
    STATUS_CANDIDATE_RECEIPT,
    TEMPORAL_GATE_STAGE,
    verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate,
)


class StrategyCorrelationExpectedGateHashTimingReceiptTests(unittest.TestCase):
    def _binding(self, gate_stage):
        binding = {
            "strategy_id": "strategy-a",
            "variant_id": "variant-1",
            "lane": "research",
            "source_uncertainty_audit": {
                "schema_version": "synthetic-uncertainty-audit-v1",
                "audit_hash": "a" * 64,
            },
            "correlation_matrix": {
                "schema_version": "synthetic-correlation-matrix-v1",
                "values": [[1.0]],
            },
            "selection_cells": [
                {"cell_id": "synthetic-cell-1", "selected": True}
            ],
        }
        if gate_stage == STABILITY_GATE_STAGE:
            binding["expected_stability_gate_hash"] = "b" * 64
        else:
            binding["expected_temporal_stability_gate_hash"] = "c" * 64
        return binding

    @staticmethod
    def _commitments(binding, gate_stage):
        identity = {
            "strategy_id": binding["strategy_id"],
            "variant_id": binding["variant_id"],
            "lane": binding["lane"],
        }
        source_link = {
            **identity,
            "source_uncertainty_audit_hash": strict_canonical_hash(
                binding["source_uncertainty_audit"]
            ),
            "correlation_matrix_hash": strict_canonical_hash(
                binding["correlation_matrix"]
            ),
            "selection_cells_hash": strict_canonical_hash(
                binding["selection_cells"]
            ),
        }
        gate_hash_field = (
            "expected_stability_gate_hash"
            if gate_stage == STABILITY_GATE_STAGE
            else "expected_temporal_stability_gate_hash"
        )
        gate_commitment = {
            **identity,
            "expected_gate_hash": binding[gate_hash_field],
        }
        return (
            strict_canonical_hash([identity]),
            strict_canonical_hash([source_link]),
            strict_canonical_hash([gate_commitment]),
        )

    def _fixture(self, gate_stage=STABILITY_GATE_STAGE, **overrides):
        binding = self._binding(gate_stage)
        identity_hash, source_hash, gate_hash = self._commitments(
            binding, gate_stage
        )
        values = {
            "gate_stage": gate_stage,
            "expected_receipt_id": "synthetic-timing-receipt-1",
            "expected_anchor_provider": "synthetic-external-anchor",
            "expected_anchor_namespace": "hakimi-research-v1",
            "expected_anchor_id": "anchor-event-1",
            "expected_declared_at": "2026-08-19T23:59:58Z",
            "expected_anchored_at": "2026-08-19T23:59:59Z",
            "expected_evidence_not_before": "2026-08-20T00:00:00Z",
            "expected_base_artifact_hash": "d" * 64,
            "expected_protocol_registration_hash": "e" * 64,
            "expected_identity_set_hash": identity_hash,
            "expected_source_linkage_hash": source_hash,
            "expected_gate_commitment_hash": gate_hash,
            "expected_external_anchor_receipt_hash": "f" * 64,
        }
        values.update(overrides)
        anchor_payload = {
            "schema_version": ANCHOR_PAYLOAD_SCHEMA_VERSION,
            "gate_stage": values["gate_stage"],
            "receipt_id": values["expected_receipt_id"],
            "anchor_provider": values["expected_anchor_provider"],
            "anchor_namespace": values["expected_anchor_namespace"],
            "declared_at": values["expected_declared_at"],
            "evidence_not_before": values["expected_evidence_not_before"],
            "base_artifact_hash": values["expected_base_artifact_hash"],
            "protocol_registration_hash": values[
                "expected_protocol_registration_hash"
            ],
            "identity_set_hash": identity_hash,
            "source_linkage_hash": source_hash,
            "expected_gate_commitment_hash": gate_hash,
        }
        document = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "status": STATUS_CANDIDATE_RECEIPT,
            "decision": "BLOCK",
            "gate_stage": values["gate_stage"],
            "receipt_id": values["expected_receipt_id"],
            "declaration": {
                "declared_at": values["expected_declared_at"],
                "evidence_not_before": values["expected_evidence_not_before"],
                "base_artifact_hash": values["expected_base_artifact_hash"],
                "protocol_registration_hash": values[
                    "expected_protocol_registration_hash"
                ],
                "identity_set_hash": identity_hash,
                "source_linkage_hash": source_hash,
                "expected_gate_commitment_hash": gate_hash,
            },
            "external_anchor": {
                "provider": values["expected_anchor_provider"],
                "namespace": values["expected_anchor_namespace"],
                "anchor_id": values["expected_anchor_id"],
                "anchored_at": values["expected_anchored_at"],
                "anchor_payload_hash": strict_canonical_hash(anchor_payload),
                "external_anchor_receipt_hash": values[
                    "expected_external_anchor_receipt_hash"
                ],
            },
            "identity_count": 1,
            "authority_gaps": list(AUTHORITY_GAPS),
            "candidate_only": True,
            "consumer_only": True,
            "external_assets_embedded": False,
            "requires_external_anchor_adapter": True,
            "receipt_producer_implemented": False,
            "anchor_receipt_verifier_implemented": False,
            "external_anchor_authenticity_verified": False,
            "immutable_persistence_verified": False,
            "anchor_uniqueness_verified": False,
            "anchor_freshness_verified": False,
            "rollback_resistance_verified": False,
            "timing_authority_verified": False,
            "preregistration_authority_verified": False,
            "formal_registry_bound": False,
            "formal_registry_activation_allowed": False,
            "writer_implemented": False,
            "current_writer_activation_allowed": False,
            "current_admission_allowed": False,
            "permissions": {
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        document = seal_strict_canonical_document(document, "receipt_hash")
        arguments = {
            **values,
            "expected_gate_bindings": [binding],
            "expected_candidate_receipt_hash": document["receipt_hash"],
        }
        return document, arguments

    @staticmethod
    def _verify(document, arguments):
        return verify_strategy_correlation_expected_gate_hash_timing_receipt_candidate(
            document,
            **arguments,
        )

    def _assert_locked(self, value):
        self.assertEqual(value["decision"], "BLOCK")
        for field in (
            "receipt_producer_implemented",
            "anchor_receipt_verifier_implemented",
            "external_anchor_authenticity_verified",
            "immutable_persistence_verified",
            "anchor_uniqueness_verified",
            "anchor_freshness_verified",
            "rollback_resistance_verified",
            "timing_authority_verified",
            "preregistration_authority_verified",
            "formal_registry_bound",
            "formal_registry_activation_allowed",
            "writer_implemented",
            "current_writer_activation_allowed",
            "current_admission_allowed",
        ):
            self.assertIs(value[field], False)
        self.assertIs(value["permissions"]["paper_authorized"], False)
        self.assertIs(value["permissions"]["live_order_allowed"], False)

    def test_both_gate_stages_verify_candidate_structure_only(self):
        for gate_stage in (STABILITY_GATE_STAGE, TEMPORAL_GATE_STAGE):
            with self.subTest(gate_stage=gate_stage):
                document, arguments = self._fixture(gate_stage)
                verification = self._verify(document, arguments)
                self.assertEqual(verification["status"], "PASS")
                self.assertIs(verification["candidate_receipt_verified"], True)
                self.assertEqual(verification["identity_count"], 1)
                self._assert_locked(verification)

    def test_post_hoc_candidate_never_becomes_timing_authority(self):
        document, arguments = self._fixture()
        verification = self._verify(document, arguments)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            verification["authority_gaps"], list(AUTHORITY_GAPS)
        )
        self._assert_locked(document)
        self._assert_locked(verification)

    def test_declaration_after_anchor_is_blocked(self):
        document, arguments = self._fixture(
            expected_declared_at="2026-08-19T23:59:59Z",
            expected_anchored_at="2026-08-19T23:59:58Z",
        )
        verification = self._verify(document, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("DECLARATION_AFTER_ANCHOR", verification["blockers"])
        self._assert_locked(verification)

    def test_anchor_at_evidence_boundary_is_blocked(self):
        document, arguments = self._fixture(
            expected_anchored_at="2026-08-20T00:00:00Z"
        )
        verification = self._verify(document, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("ANCHOR_NOT_BEFORE_EVIDENCE", verification["blockers"])

    def test_noncanonical_timestamp_is_blocked(self):
        document, arguments = self._fixture(
            expected_declared_at="2026-08-19T23:59:58+00:00"
        )
        verification = self._verify(document, arguments)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("DECLARED_AT_INVALID", verification["blockers"])

    def test_independent_identity_hash_drift_is_blocked(self):
        document, arguments = self._fixture()
        arguments["expected_identity_set_hash"] = "0" * 64
        verification = self._verify(document, arguments)
        self.assertIn("IDENTITY_SET_HASH_MISMATCH", verification["blockers"])

    def test_independent_source_linkage_drift_is_blocked(self):
        document, arguments = self._fixture()
        arguments["expected_source_linkage_hash"] = "1" * 64
        verification = self._verify(document, arguments)
        self.assertIn("SOURCE_LINKAGE_HASH_MISMATCH", verification["blockers"])

    def test_independent_gate_commitment_drift_is_blocked(self):
        document, arguments = self._fixture()
        arguments["expected_gate_commitment_hash"] = "2" * 64
        verification = self._verify(document, arguments)
        self.assertIn("GATE_COMMITMENT_HASH_MISMATCH", verification["blockers"])

    def test_external_anchor_receipt_hash_substitution_is_blocked(self):
        document, arguments = self._fixture()
        arguments["expected_external_anchor_receipt_hash"] = "3" * 64
        verification = self._verify(document, arguments)
        self.assertIn("RECEIPT_REBUILD_MISMATCH", verification["blockers"])

    def test_duplicate_binding_identity_is_rejected(self):
        document, arguments = self._fixture()
        arguments["expected_gate_bindings"].append(
            copy.deepcopy(arguments["expected_gate_bindings"][0])
        )
        verification = self._verify(document, arguments)
        self.assertIn("GATE_BINDINGS_INVALID", verification["blockers"])

    def test_extra_binding_field_is_rejected(self):
        document, arguments = self._fixture()
        arguments["expected_gate_bindings"][0]["declared_at"] = (
            "2026-08-19T23:59:58Z"
        )
        verification = self._verify(document, arguments)
        self.assertIn("GATE_BINDINGS_INVALID", verification["blockers"])

    def test_resealed_authority_escalation_is_rejected(self):
        document, arguments = self._fixture()
        attacked = copy.deepcopy(document)
        attacked["timing_authority_verified"] = True
        attacked = seal_strict_canonical_document(attacked, "receipt_hash")
        arguments["expected_candidate_receipt_hash"] = attacked["receipt_hash"]
        verification = self._verify(attacked, arguments)
        self.assertIn("RECEIPT_REBUILD_MISMATCH", verification["blockers"])
        self.assertIn(
            "CANDIDATE_RECEIPT_HASH_MISMATCH", verification["blockers"]
        )
        self.assertIn(
            "RECEIPT_AUTHORITY_NOT_LOCKED", verification["blockers"]
        )
        self._assert_locked(verification)

    def test_native_false_alias_is_rejected(self):
        document, arguments = self._fixture()
        attacked = copy.deepcopy(document)
        attacked["writer_implemented"] = 0
        attacked = seal_strict_canonical_document(attacked, "receipt_hash")
        arguments["expected_candidate_receipt_hash"] = attacked["receipt_hash"]
        verification = self._verify(attacked, arguments)
        self.assertIn("RECEIPT_AUTHORITY_NOT_LOCKED", verification["blockers"])

    def test_extra_receipt_field_is_rejected(self):
        document, arguments = self._fixture()
        attacked = copy.deepcopy(document)
        attacked["compatibility_alias"] = False
        attacked = seal_strict_canonical_document(attacked, "receipt_hash")
        arguments["expected_candidate_receipt_hash"] = attacked["receipt_hash"]
        verification = self._verify(attacked, arguments)
        self.assertIn("RECEIPT_REBUILD_MISMATCH", verification["blockers"])

    def test_caller_supplied_receipt_hash_drift_is_blocked(self):
        document, arguments = self._fixture()
        arguments["expected_candidate_receipt_hash"] = "4" * 64
        verification = self._verify(document, arguments)
        self.assertIn(
            "CANDIDATE_RECEIPT_HASH_MISMATCH", verification["blockers"]
        )

    def test_no_receipt_builder_or_activation_export_exists(self):
        exports = set(receipt_module.__all__)
        self.assertNotIn("build_expected_gate_hash_timing_receipt", exports)
        self.assertNotIn("persist_expected_gate_hash_timing_receipt", exports)
        self.assertNotIn("activate_report20_writer", exports)
        self.assertNotIn("activate_report21_writer", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
