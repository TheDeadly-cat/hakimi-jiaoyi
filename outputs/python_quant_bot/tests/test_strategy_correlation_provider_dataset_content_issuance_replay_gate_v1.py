from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import inspect
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_attestation_v1 as content_source,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as lifecycle_replay_source,
)
from tests import (
    test_strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as lifecycle_replay_tests,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical_hash(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StrategyCorrelationProviderDatasetContentIssuanceReplayGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = (
            lifecycle_replay_tests.StrategyCorrelationProviderDatasetKeyLifecycleReplayGateV1Tests(
                methodName="runTest"
            )
        )
        self.source.setUp()
        self.attestation_document = self.source.source.attestation_document
        self.attestation_context = self.source.source.attestation_context
        self.lifecycle_replay_document = self.source.evaluate()
        self.lifecycle_replay_context = {
            "lifecycle_document": self.source.lifecycle_document,
            "lifecycle_context": self.source.lifecycle_context,
            "replay_registration": self.source.registration,
            "replay_registry_public_key_base64": (
                self.source.registry_public_key_base64
            ),
            "occurrence_auditor_public_key_base64": (
                self.source.auditor_public_key_base64
            ),
            "pinned_checkpoint": self.source.pinned_checkpoint,
            "checkpoint": self.source.checkpoint,
            "inclusion_proof": self.source.inclusion_proof,
            "consistency_proof": self.source.consistency_proof,
            "occurrence_audit": self.source.occurrence_audit,
            "expected_registration_hash": self.source.registration[
                "registration_hash"
            ],
            "expected_pinned_checkpoint_hash": self.source.pinned_checkpoint[
                "pin_hash"
            ],
            "expected_checkpoint_hash": self.source.checkpoint[
                "checkpoint_hash"
            ],
            "expected_occurrence_audit_hash": self.source.occurrence_audit[
                "occurrence_audit_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        self.registration = self.build_registration()
        self.other_leaf = (
            subject.hash_provider_dataset_content_issuance_leaf_v1(
                _hash("other-attestation"),
                _hash("other-future-evaluation"),
            )
        )
        self.source_leaf = (
            subject.hash_provider_dataset_content_issuance_leaf_v1(
                self.attestation_document["source_attestation_hash"],
                self.attestation_context["composition_document"][
                    "future_evaluation_id_hash"
                ],
            )
        )
        self.old_root = self.other_leaf
        self.new_root = (
            subject.hash_provider_dataset_content_issuance_node_v1(
                self.old_root,
                self.source_leaf,
            )
        )
        self.inclusion_proof = [self.old_root]
        self.consistency_proof = [self.source_leaf]
        self.pinned_checkpoint = self.build_pinned(
            registration=self.registration
        )
        self.checkpoint = self.build_checkpoint(
            registration=self.registration,
            pinned_checkpoint=self.pinned_checkpoint,
        )
        self.occurrence_audit = self.build_audit(
            registration=self.registration,
            checkpoint=self.checkpoint,
        )

    def source_verifiers(self):
        return self.source.source_verifiers()

    def build_registration(self, **overrides):
        values = {
            "attestation_document": self.attestation_document,
            "attestation_context": self.attestation_context,
            "lifecycle_replay_document": self.lifecycle_replay_document,
            "lifecycle_replay_context": self.lifecycle_replay_context,
            "content_replay_registry_namespace": (
                "STRATEGY-CORRELATION.DATASET-CONTENT-ISSUANCE.V1"
            ),
            "adapter_id": "DATASET-CONTENT-ISSUANCE-REPLAY-ADAPTER-01",
            "adapter_implementation_hash": _hash(
                "dataset-content-issuance-replay-adapter-v1"
            ),
            "declared_at_utc": "2026-12-20T02:42:00Z",
            "max_checkpoint_age_seconds": 1800,
            "max_scan_age_seconds": 900,
            "max_occurrence_receipt_issue_delay_seconds": 300,
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.build_provider_dataset_content_issuance_replay_registration_v1(
                **values
            )

    def build_pinned(self, registration=None, **overrides):
        source_registration = registration or self.registration
        values = {
            "tree_size": 1,
            "root_hash": self.old_root,
            "checkpoint_hash": _hash(
                "previous-content-issuance-checkpoint"
            ),
        }
        values.update(overrides)
        return subject.build_pinned_provider_dataset_content_issuance_checkpoint_v1(
            source_registration,
            **values,
        )

    def build_checkpoint(
        self,
        *,
        registration=None,
        pinned_checkpoint=None,
        private_key=None,
        root_hash=None,
        issued_at_utc="2026-12-20T02:45:00Z",
    ):
        source_registration = registration or self.registration
        source_pinned = pinned_checkpoint or self.pinned_checkpoint
        signing_key = private_key or self.source.registry_private_key
        unsigned = (
            subject.build_unsigned_provider_dataset_content_issuance_checkpoint_v1(
                source_registration,
                source_pinned,
                tree_size=2,
                root_hash=root_hash or self.new_root,
                issued_at_utc=issued_at_utc,
            )
        )
        signature = signing_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        return (
            subject.assemble_provider_dataset_content_issuance_checkpoint_v1(
                unsigned,
                base64.b64encode(signature).decode("ascii"),
            )
        )

    def build_audit(
        self,
        *,
        registration=None,
        checkpoint=None,
        inclusion_proof=None,
        consistency_proof=None,
        private_key=None,
        occurrence_leaf_index=1,
        scan_start_index=0,
        scan_end_index_exclusive=2,
        index_snapshot_record_count=2,
        occurrence_count=1,
        occurrence_leaf_indices=None,
        index_snapshot_root_hash=None,
        scan_completed_at_utc="2026-12-20T02:50:00Z",
        audit_issued_at_utc="2026-12-20T02:55:00Z",
        reference_time_utc="2026-12-20T03:00:00Z",
    ):
        source_registration = registration or self.registration
        source_checkpoint = checkpoint or self.checkpoint
        source_inclusion = (
            self.inclusion_proof
            if inclusion_proof is None
            else inclusion_proof
        )
        source_consistency = (
            self.consistency_proof
            if consistency_proof is None
            else consistency_proof
        )
        indices = (
            [occurrence_leaf_index]
            if occurrence_leaf_indices is None
            else occurrence_leaf_indices
        )
        signing_key = private_key or self.source.auditor_private_key
        unsigned = subject.build_unsigned_provider_dataset_content_issuance_occurrence_audit_v1(
            source_registration,
            source_checkpoint,
            source_inclusion,
            source_consistency,
            occurrence_leaf_index=occurrence_leaf_index,
            scan_start_index=scan_start_index,
            scan_end_index_exclusive=scan_end_index_exclusive,
            index_snapshot_record_count=index_snapshot_record_count,
            occurrence_count=occurrence_count,
            occurrence_leaf_indices=indices,
            index_snapshot_root_hash=(
                source_checkpoint["root_hash"]
                if index_snapshot_root_hash is None
                else index_snapshot_root_hash
            ),
            scan_completed_at_utc=scan_completed_at_utc,
            audit_issued_at_utc=audit_issued_at_utc,
            reference_time_utc=reference_time_utc,
        )
        signature = signing_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        return subject.assemble_provider_dataset_content_issuance_occurrence_audit_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    def evaluation_values(self):
        return {
            "attestation_document": self.attestation_document,
            "attestation_context": self.attestation_context,
            "lifecycle_replay_document": self.lifecycle_replay_document,
            "lifecycle_replay_context": self.lifecycle_replay_context,
            "replay_registration": self.registration,
            "pinned_checkpoint": self.pinned_checkpoint,
            "checkpoint": self.checkpoint,
            "inclusion_proof": self.inclusion_proof,
            "consistency_proof": self.consistency_proof,
            "occurrence_audit": self.occurrence_audit,
            "expected_registration_hash": self.registration[
                "registration_hash"
            ],
            "expected_pinned_checkpoint_hash": self.pinned_checkpoint[
                "pin_hash"
            ],
            "expected_checkpoint_hash": self.checkpoint["checkpoint_hash"],
            "expected_occurrence_audit_hash": self.occurrence_audit[
                "occurrence_audit_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }

    def evaluate(self, **overrides):
        values = self.evaluation_values()
        values.update(overrides)
        with self.source_verifiers():
            return subject.evaluate_provider_dataset_content_issuance_replay_gate_v1(
                **values
            )

    def verify(self, document, **overrides):
        values = self.evaluation_values()
        values.update(overrides)
        with self.source_verifiers():
            return subject.verify_provider_dataset_content_issuance_replay_gate_v1(
                document,
                **values,
            )

    def test_existing_attestation_gap_accepts_same_receipt_twice(self) -> None:
        with self.source_verifiers():
            first = (
                content_source.evaluate_provider_dataset_content_attestation_v1(
                    **self.attestation_context
                )
            )
            second = (
                content_source.evaluate_provider_dataset_content_attestation_v1(
                    **self.attestation_context
                )
            )
        self.assertEqual(first, second)
        self.assertFalse(first["facts"]["replay_registry_checked"])
        replay_fields = [
            key
            for key in first
            if any(
                token in key
                for token in (
                    "issuance",
                    "sequence",
                    "occurrence",
                    "checkpoint",
                    "nonce",
                )
            )
        ]
        self.assertEqual(replay_fields, [])

    def test_registration_reuses_roles_and_binds_both_sources(self) -> None:
        self.assertEqual(
            self.registration["source_attestation_verification_hash"],
            self.attestation_document["verification_hash"],
        )
        self.assertEqual(
            self.registration["source_lifecycle_replay_verification_hash"],
            self.lifecycle_replay_document["verification_hash"],
        )
        self.assertEqual(
            self.registration["replay_registry_key_id"],
            self.source.registration["replay_registry_key_id"],
        )
        self.assertEqual(
            self.registration["occurrence_auditor_key_id"],
            self.source.registration["occurrence_auditor_key_id"],
        )
        self.assertTrue(
            self.registration["facts"][
                "existing_replay_registry_key_role_reused"
            ]
        )
        self.assertFalse(any(self.registration["authority"].values()))

    def test_registration_requires_distinct_content_namespace(self) -> None:
        with self.assertRaisesRegex(ValueError, "identifier_invalid"):
            self.build_registration(
                content_replay_registry_namespace=self.source.registration[
                    "replay_registry_namespace"
                ]
            )

    def test_registration_cannot_weaken_source_freshness(self) -> None:
        with self.assertRaisesRegex(ValueError, "freshness_policy_invalid"):
            self.build_registration(
                max_occurrence_receipt_issue_delay_seconds=1801
            )

    def test_registration_must_follow_source_replay_audit(self) -> None:
        with self.assertRaisesRegex(ValueError, "registration_time_invalid"):
            self.build_registration(
                declared_at_utc="2026-12-20T02:39:59Z"
            )

    def test_content_source_verifier_is_required(self) -> None:
        with patch.object(
            content_source,
            "verify_provider_dataset_content_attestation_v1",
            return_value=False,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "attestation_source_invalid",
            ):
                self.build_registration()

    def test_lifecycle_replay_source_verifier_is_required(self) -> None:
        with patch.object(
            lifecycle_replay_source,
            "verify_provider_dataset_key_lifecycle_replay_gate_v1",
            return_value=False,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "lifecycle_source_invalid",
            ):
                self.build_registration()

    def test_positive_output_is_local_and_non_authoritative(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["verification_state"], subject.VERIFICATION_STATE)
        self.assertTrue(
            result["facts"]["content_identity_inclusion_verified"]
        )
        self.assertTrue(
            result["facts"][
                "exactly_one_content_identity_occurrence_claim_verified"
            ]
        )
        self.assertFalse(
            result["facts"]["external_provider_data_issuance_verified"]
        )
        self.assertFalse(
            result["facts"]["runtime_consumption_replay_enforcement_verified"]
        )
        self.assertFalse(any(result["authority"].values()))
        self.assertEqual(
            result["permissions"],
            {"paper_authorized": False, "live_order_allowed": False},
        )

    def test_output_is_deterministic_and_verifier_accepts_exact(self) -> None:
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        self.assertTrue(self.verify(first))

    def test_all_expected_artifact_hashes_are_required(self) -> None:
        names = (
            "expected_registration_hash",
            "expected_pinned_checkpoint_hash",
            "expected_checkpoint_hash",
            "expected_occurrence_audit_hash",
        )
        for name in names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.evaluate(**{name: "0" * 64})

    def test_inclusion_proof_tamper_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "inclusion_proof_invalid"):
            self.evaluate(inclusion_proof=[_hash("wrong-inclusion")])

    def test_consistency_proof_tamper_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "consistency_proof_invalid"):
            self.evaluate(consistency_proof=[_hash("wrong-consistency")])

    def test_checkpoint_wrong_signing_key_is_rejected(self) -> None:
        checkpoint = self.build_checkpoint(
            private_key=Ed25519PrivateKey.generate()
        )
        with self.assertRaisesRegex(ValueError, "checkpoint_signature_invalid"):
            self.evaluate(
                checkpoint=checkpoint,
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
            )

    def test_occurrence_wrong_signing_key_is_rejected(self) -> None:
        audit = self.build_audit(
            private_key=Ed25519PrivateKey.generate()
        )
        with self.assertRaisesRegex(
            ValueError,
            "occurrence_signature_invalid",
        ):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_signed_duplicate_occurrence_claim_is_rejected(self) -> None:
        audit = self.build_audit(
            occurrence_count=2,
            occurrence_leaf_indices=[0, 1],
        )
        with self.assertRaisesRegex(
            ValueError,
            "exactly_one_occurrence_claim_invalid",
        ):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_signed_incomplete_scan_claim_is_rejected(self) -> None:
        audit = self.build_audit(
            scan_start_index=1,
            scan_end_index_exclusive=2,
            index_snapshot_record_count=1,
        )
        with self.assertRaisesRegex(ValueError, "complete_scan_claim_invalid"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_signed_index_snapshot_must_match_checkpoint_root(self) -> None:
        audit = self.build_audit(
            index_snapshot_root_hash=_hash("detached-index-root")
        )
        with self.assertRaisesRegex(ValueError, "index_snapshot_mismatch"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_stale_checkpoint_is_rejected(self) -> None:
        registration = self.build_registration(
            max_checkpoint_age_seconds=600
        )
        pinned = self.build_pinned(registration=registration)
        checkpoint = self.build_checkpoint(
            registration=registration,
            pinned_checkpoint=pinned,
        )
        audit = self.build_audit(
            registration=registration,
            checkpoint=checkpoint,
        )
        with self.assertRaisesRegex(ValueError, "checkpoint_age_exceeded"):
            self.evaluate(
                replay_registration=registration,
                pinned_checkpoint=pinned,
                checkpoint=checkpoint,
                occurrence_audit=audit,
                expected_registration_hash=registration[
                    "registration_hash"
                ],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_stale_scan_is_rejected(self) -> None:
        checkpoint = self.build_checkpoint(
            issued_at_utc="2026-12-20T02:43:00Z"
        )
        audit = self.build_audit(
            checkpoint=checkpoint,
            scan_completed_at_utc="2026-12-20T02:44:00Z",
            audit_issued_at_utc="2026-12-20T02:48:00Z",
        )
        with self.assertRaisesRegex(ValueError, "scan_age_exceeded"):
            self.evaluate(
                checkpoint=checkpoint,
                occurrence_audit=audit,
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_occurrence_issue_delay_is_bounded(self) -> None:
        audit = self.build_audit(
            scan_completed_at_utc="2026-12-20T02:49:00Z",
            audit_issued_at_utc="2026-12-20T02:55:00Z",
        )
        with self.assertRaisesRegex(ValueError, "issue_delay_exceeded"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
            )

    def test_reference_time_must_match_source_replay_gate(self) -> None:
        with self.assertRaisesRegex(ValueError, "reference_time_mismatch"):
            self.evaluate(reference_time_utc="2026-12-20T03:00:01Z")

    def test_authority_injection_is_rejected(self) -> None:
        audit = deepcopy(self.occurrence_audit)
        audit["paper_authorized"] = True
        with self.assertRaisesRegex(ValueError, "authority_invalid"):
            self.evaluate(occurrence_audit=audit)

    def test_leaf_identity_is_stable_and_evaluation_specific(self) -> None:
        attestation_hash = self.attestation_document[
            "source_attestation_hash"
        ]
        evaluation_hash = self.attestation_context["composition_document"][
            "future_evaluation_id_hash"
        ]
        first = subject.hash_provider_dataset_content_issuance_leaf_v1(
            attestation_hash,
            evaluation_hash,
        )
        second = subject.hash_provider_dataset_content_issuance_leaf_v1(
            attestation_hash,
            evaluation_hash,
        )
        changed = subject.hash_provider_dataset_content_issuance_leaf_v1(
            attestation_hash,
            _hash("different-future-evaluation"),
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_bool_tree_size_alias_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "tree_size_invalid"):
            subject.build_pinned_provider_dataset_content_issuance_checkpoint_v1(
                self.registration,
                tree_size=True,
                root_hash=self.old_root,
                checkpoint_hash=_hash("checkpoint"),
            )

    def test_production_api_never_accepts_private_key(self) -> None:
        functions = (
            subject.build_provider_dataset_content_issuance_replay_registration_v1,
            subject.verify_provider_dataset_content_issuance_replay_registration_v1,
            subject.build_pinned_provider_dataset_content_issuance_checkpoint_v1,
            subject.build_unsigned_provider_dataset_content_issuance_checkpoint_v1,
            subject.assemble_provider_dataset_content_issuance_checkpoint_v1,
            subject.build_unsigned_provider_dataset_content_issuance_occurrence_audit_v1,
            subject.assemble_provider_dataset_content_issuance_occurrence_audit_v1,
            subject.evaluate_provider_dataset_content_issuance_replay_gate_v1,
            subject.verify_provider_dataset_content_issuance_replay_gate_v1,
        )
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(
                    any(
                        "private" in name.lower()
                        for name in inspect.signature(function).parameters
                    )
                )

    def test_output_redacts_payloads_and_coherent_reseal_is_rejected(self) -> None:
        result = self.evaluate()
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(
            self.source.registry_public_key_base64,
            serialized,
        )
        self.assertNotIn(
            self.source.auditor_public_key_base64,
            serialized,
        )
        self.assertNotIn(self.checkpoint["signature_base64"], serialized)
        self.assertNotIn(self.occurrence_audit["signature_base64"], serialized)
        self.assertNotIn("inclusion_proof", result)
        self.assertNotIn("consistency_proof", result)

        tampered = deepcopy(result)
        tampered["facts"][
            "external_provider_data_issuance_verified"
        ] = True
        body = {
            key: value
            for key, value in tampered.items()
            if key != "verification_hash"
        }
        tampered["verification_hash"] = _canonical_hash(body)
        self.assertFalse(self.verify(tampered))


if __name__ == "__main__":
    unittest.main()
