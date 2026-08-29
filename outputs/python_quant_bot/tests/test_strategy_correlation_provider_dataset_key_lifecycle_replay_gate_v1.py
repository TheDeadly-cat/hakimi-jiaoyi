from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import inspect
import json
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_provider_dataset_key_lifecycle_gate_v1 as lifecycle_source
from exchange_terminal.services import strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1 as subject
from tests.test_strategy_correlation_provider_dataset_key_lifecycle_gate_v1 import (
    StrategyCorrelationProviderDatasetKeyLifecycleGateV1Tests,
)


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seal(value: dict[str, object], hash_field: str) -> dict[str, object]:
    body = {key: item for key, item in value.items() if key != hash_field}
    value[hash_field] = hashlib.sha256(
        json.dumps(
            body,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return value


class StrategyCorrelationProviderDatasetKeyLifecycleReplayGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = StrategyCorrelationProviderDatasetKeyLifecycleGateV1Tests(
            methodName="test_positive_gate_reduces_gap_without_promoting_external_trust"
        )
        self.source.setUp()
        self.lifecycle_document = self.source.evaluate()
        self.lifecycle_context = {
            "attestation_document": self.source.attestation_document,
            "attestation_context": self.source.attestation_context,
            "lifecycle_registration": self.source.registration,
            "governance_public_key_base64": (
                self.source.governance_public_key_base64
            ),
            "lifecycle_receipt": self.source.receipt,
            "expected_registration_hash": self.source.registration[
                "registration_hash"
            ],
            "expected_lifecycle_receipt_hash": self.source.receipt[
                "lifecycle_receipt_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        self.registry_private_key = Ed25519PrivateKey.generate()
        self.registry_public_key_base64 = _public_key_base64(
            self.registry_private_key
        )
        self.auditor_private_key = Ed25519PrivateKey.generate()
        self.auditor_public_key_base64 = _public_key_base64(
            self.auditor_private_key
        )
        self.registration = self.build_registration()
        self.other_receipt_hash = _hash("other-lifecycle-receipt")
        self.old_root = subject.hash_lifecycle_replay_leaf_v1(
            self.other_receipt_hash
        )
        self.source_leaf = subject.hash_lifecycle_replay_leaf_v1(
            self.source.receipt["lifecycle_receipt_hash"]
        )
        self.new_root = subject.hash_lifecycle_replay_node_v1(
            self.old_root,
            self.source_leaf,
        )
        self.inclusion_proof = [self.old_root]
        self.consistency_proof = [self.source_leaf]
        (
            self.pinned_checkpoint,
            self.checkpoint,
            self.occurrence_audit,
        ) = self.build_bundle(self.registration)

    def source_verifiers(self):
        return self.source.source.source_verifiers()

    def build_registration(self, **overrides):
        values = {
            "lifecycle_document": self.lifecycle_document,
            "lifecycle_context": self.lifecycle_context,
            "replay_registry_id": "LIFECYCLE-REPLAY-REGISTRY-01",
            "replay_registry_namespace": "STRATEGY-CORRELATION.DATASET-LIFECYCLE.V1",
            "adapter_id": "LIFECYCLE-REPLAY-ADAPTER-01",
            "adapter_implementation_hash": _hash("replay-adapter-v1"),
            "replay_registry_key_id": "LIFECYCLE-REPLAY-REGISTRY-KEY-01",
            "replay_registry_public_key_base64": self.registry_public_key_base64,
            "occurrence_auditor_id": "LIFECYCLE-OCCURRENCE-AUDITOR-01",
            "occurrence_auditor_key_id": "LIFECYCLE-OCCURRENCE-AUDITOR-KEY-01",
            "occurrence_auditor_public_key_base64": self.auditor_public_key_base64,
            "declared_at_utc": "2026-08-22T01:00:00Z",
            "max_checkpoint_age_seconds": 7200,
            "max_scan_age_seconds": 7200,
            "max_occurrence_receipt_issue_delay_seconds": 1800,
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.build_provider_dataset_key_lifecycle_replay_registration_v1(
                **values
            )

    def build_pinned(self, registration=None, **overrides):
        source_registration = registration or self.registration
        values = {
            "tree_size": 1,
            "root_hash": self.old_root,
            "checkpoint_hash": _hash("previous-signed-checkpoint"),
        }
        values.update(overrides)
        return subject.build_pinned_lifecycle_replay_checkpoint_v1(
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
        issued_at_utc="2026-12-20T02:20:00Z",
    ):
        source_registration = registration or self.registration
        source_pinned = pinned_checkpoint or self.pinned_checkpoint
        signing_key = private_key or self.registry_private_key
        unsigned = subject.build_unsigned_lifecycle_replay_checkpoint_v1(
            source_registration,
            source_pinned,
            tree_size=2,
            root_hash=root_hash or self.new_root,
            issued_at_utc=issued_at_utc,
        )
        signature = signing_key.sign(bytes.fromhex(unsigned["receipt_content_sha256"]))
        return subject.assemble_lifecycle_replay_checkpoint_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
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
        scan_completed_at_utc="2026-12-20T02:30:00Z",
        audit_issued_at_utc="2026-12-20T02:40:00Z",
        reference_time_utc="2026-12-20T03:00:00Z",
    ):
        source_registration = registration or self.registration
        source_checkpoint = checkpoint or self.checkpoint
        source_inclusion = (
            self.inclusion_proof if inclusion_proof is None else inclusion_proof
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
        signing_key = private_key or self.auditor_private_key
        unsigned = subject.build_unsigned_lifecycle_replay_occurrence_audit_v1(
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
            index_snapshot_root_hash=_hash("complete-index-snapshot"),
            scan_completed_at_utc=scan_completed_at_utc,
            audit_issued_at_utc=audit_issued_at_utc,
            reference_time_utc=reference_time_utc,
        )
        signature = signing_key.sign(bytes.fromhex(unsigned["receipt_content_sha256"]))
        return subject.assemble_lifecycle_replay_occurrence_audit_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    def build_bundle(self, registration):
        pinned = self.build_pinned(registration=registration)
        checkpoint = self.build_checkpoint(
            registration=registration,
            pinned_checkpoint=pinned,
        )
        audit = self.build_audit(
            registration=registration,
            checkpoint=checkpoint,
        )
        return pinned, checkpoint, audit

    def evaluate(self, **overrides):
        values = {
            "lifecycle_document": self.lifecycle_document,
            "lifecycle_context": self.lifecycle_context,
            "replay_registration": self.registration,
            "replay_registry_public_key_base64": self.registry_public_key_base64,
            "occurrence_auditor_public_key_base64": self.auditor_public_key_base64,
            "pinned_checkpoint": self.pinned_checkpoint,
            "checkpoint": self.checkpoint,
            "inclusion_proof": self.inclusion_proof,
            "consistency_proof": self.consistency_proof,
            "occurrence_audit": self.occurrence_audit,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_pinned_checkpoint_hash": self.pinned_checkpoint["pin_hash"],
            "expected_checkpoint_hash": self.checkpoint["checkpoint_hash"],
            "expected_occurrence_audit_hash": self.occurrence_audit[
                "occurrence_audit_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
                **values
            )

    def verify(self, document, **overrides):
        values = {
            "lifecycle_document": self.lifecycle_document,
            "lifecycle_context": self.lifecycle_context,
            "replay_registration": self.registration,
            "replay_registry_public_key_base64": self.registry_public_key_base64,
            "occurrence_auditor_public_key_base64": self.auditor_public_key_base64,
            "pinned_checkpoint": self.pinned_checkpoint,
            "checkpoint": self.checkpoint,
            "inclusion_proof": self.inclusion_proof,
            "consistency_proof": self.consistency_proof,
            "occurrence_audit": self.occurrence_audit,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_pinned_checkpoint_hash": self.pinned_checkpoint["pin_hash"],
            "expected_checkpoint_hash": self.checkpoint["checkpoint_hash"],
            "expected_occurrence_audit_hash": self.occurrence_audit[
                "occurrence_audit_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        values.update(overrides)
        with self.source_verifiers():
            return subject.verify_provider_dataset_key_lifecycle_replay_gate_v1(
                document,
                **values,
            )

    def test_registration_binds_source_and_two_new_roles(self) -> None:
        self.assertEqual(
            self.registration["source_lifecycle_verification_hash"],
            self.lifecycle_document["verification_hash"],
        )
        self.assertEqual(self.registration["excluded_upstream_key_count"], 4)
        self.assertEqual(
            self.registration["replay_registry_key_role"],
            subject.REPLAY_REGISTRY_KEY_ROLE,
        )
        self.assertEqual(
            self.registration["occurrence_auditor_key_role"],
            subject.OCCURRENCE_AUDITOR_KEY_ROLE,
        )
        self.assertFalse(any(self.registration["authority"].values()))

    def test_registration_verifier_accepts_exact_rebuild(self) -> None:
        with self.source_verifiers():
            self.assertTrue(
                subject.verify_provider_dataset_key_lifecycle_replay_registration_v1(
                    self.registration,
                    self.lifecycle_document,
                    self.lifecycle_context,
                    self.registry_public_key_base64,
                    self.auditor_public_key_base64,
                    expected_registration_hash=self.registration[
                        "registration_hash"
                    ],
                )
            )

    def test_registration_is_deterministic_and_redacts_keys(self) -> None:
        self.assertEqual(self.registration, self.build_registration())
        serialized = json.dumps(self.registration, sort_keys=True)
        self.assertNotIn(self.registry_public_key_base64, serialized)
        self.assertNotIn(self.auditor_public_key_base64, serialized)

    def test_registry_key_cannot_reuse_any_upstream_role(self) -> None:
        upstream_keys = (
            self.source.source.dataset_public_key_base64,
            self.source.governance_public_key_base64,
            self.source.source.provider_bundle["identity_assertion_receipt"][
                "registry_public_key_base64"
            ],
            self.source.source.calendar_bundle["batch_verification_context"][
                "signature_verification_context"
            ]["attestation_receipt"]["public_key_base64"],
        )
        for public_key in upstream_keys:
            with self.subTest(public_key=public_key[:8]):
                with self.assertRaisesRegex(ValueError, "public_key_role_collision"):
                    self.build_registration(
                        replay_registry_public_key_base64=public_key
                    )

    def test_auditor_key_cannot_reuse_upstream_or_registry_role(self) -> None:
        collision_keys = (
            self.source.source.dataset_public_key_base64,
            self.source.governance_public_key_base64,
            self.registry_public_key_base64,
        )
        for public_key in collision_keys:
            with self.subTest(public_key=public_key[:8]):
                with self.assertRaisesRegex(ValueError, "public_key_role_collision"):
                    self.build_registration(
                        occurrence_auditor_public_key_base64=public_key
                    )

    def test_key_id_role_collisions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "key_id_role_collision"):
            self.build_registration(
                occurrence_auditor_key_id="LIFECYCLE-REPLAY-REGISTRY-KEY-01"
            )
        with self.assertRaisesRegex(ValueError, "key_id_role_collision"):
            self.build_registration(
                replay_registry_key_id=self.source.registration[
                    "provider_dataset_key_id"
                ]
            )

    def test_registration_hashes_and_freshness_limits_are_strict(self) -> None:
        with self.assertRaisesRegex(ValueError, "implementation_hash_invalid"):
            self.build_registration(adapter_implementation_hash="bad")
        with self.assertRaisesRegex(ValueError, "freshness_policy_invalid"):
            self.build_registration(max_checkpoint_age_seconds=True)
        with self.assertRaisesRegex(ValueError, "freshness_policy_invalid"):
            self.build_registration(max_scan_age_seconds=0)

    def test_pinned_checkpoint_supports_strict_genesis_and_non_genesis(self) -> None:
        genesis = subject.build_pinned_lifecycle_replay_checkpoint_v1(
            self.registration,
            tree_size=0,
            root_hash=subject.GENESIS_ROOT_HASH,
            checkpoint_hash=subject.GENESIS_COMMITMENT,
        )
        self.assertEqual(genesis["tree_size"], 0)
        self.assertEqual(self.pinned_checkpoint["tree_size"], 1)
        with self.assertRaisesRegex(ValueError, "genesis_invalid"):
            subject.build_pinned_lifecycle_replay_checkpoint_v1(
                self.registration,
                tree_size=0,
                root_hash=self.old_root,
                checkpoint_hash=subject.GENESIS_COMMITMENT,
            )

    def test_checkpoint_binds_prior_pin_and_registry(self) -> None:
        self.assertEqual(
            self.checkpoint["pinned_checkpoint_hash"],
            self.pinned_checkpoint["pin_hash"],
        )
        self.assertEqual(self.checkpoint["previous_tree_size"], 1)
        self.assertEqual(self.checkpoint["tree_size"], 2)
        self.assertEqual(
            self.checkpoint["replay_registry_key_id"],
            self.registration["replay_registry_key_id"],
        )

    def test_checkpoint_wrong_signing_key_is_rejected(self) -> None:
        checkpoint = self.build_checkpoint(private_key=Ed25519PrivateKey.generate())
        audit = self.build_audit(checkpoint=checkpoint)
        with self.assertRaisesRegex(ValueError, "checkpoint_signature_invalid"):
            self.evaluate(
                checkpoint=checkpoint,
                occurrence_audit=audit,
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_checkpoint_expected_hash_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "checkpoint_invalid"):
            self.evaluate(expected_checkpoint_hash="0" * 64)

    def test_non_genesis_merkle_inclusion_is_verified(self) -> None:
        result = self.evaluate()
        self.assertTrue(result["facts"]["lifecycle_receipt_inclusion_verified"])
        self.assertEqual(result["occurrence_leaf_index"], 1)

    def test_coherently_signed_inclusion_proof_tamper_is_rejected(self) -> None:
        bad_proof = [self.source_leaf]
        audit = self.build_audit(inclusion_proof=bad_proof)
        with self.assertRaisesRegex(ValueError, "inclusion_proof_invalid"):
            self.evaluate(
                inclusion_proof=bad_proof,
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_non_genesis_append_only_consistency_is_verified(self) -> None:
        result = self.evaluate()
        self.assertTrue(result["facts"]["append_only_consistency_verified"])
        self.assertEqual(result["previous_checkpoint_tree_size"], 1)

    def test_coherently_signed_consistency_proof_tamper_is_rejected(self) -> None:
        bad_proof = [self.old_root]
        audit = self.build_audit(consistency_proof=bad_proof)
        with self.assertRaisesRegex(ValueError, "consistency_proof_invalid"):
            self.evaluate(
                consistency_proof=bad_proof,
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_occurrence_audit_binds_full_scan_and_exactly_one_claim(self) -> None:
        self.assertEqual(self.occurrence_audit["scan_start_index"], 0)
        self.assertEqual(self.occurrence_audit["scan_end_index_exclusive"], 2)
        self.assertEqual(self.occurrence_audit["index_snapshot_record_count"], 2)
        self.assertEqual(self.occurrence_audit["occurrence_count"], 1)
        self.assertEqual(self.occurrence_audit["occurrence_leaf_indices"], [1])

    def test_occurrence_audit_wrong_signing_key_is_rejected(self) -> None:
        audit = self.build_audit(private_key=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "occurrence_signature_invalid"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_signed_duplicate_occurrence_claim_is_fail_closed(self) -> None:
        audit = self.build_audit(
            occurrence_count=2,
            occurrence_leaf_indices=[0, 1],
        )
        with self.assertRaisesRegex(ValueError, "exactly_one_occurrence_claim_invalid"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_signed_incomplete_scan_claim_is_fail_closed(self) -> None:
        audit = self.build_audit(
            scan_start_index=1,
            scan_end_index_exclusive=2,
            index_snapshot_record_count=1,
        )
        with self.assertRaisesRegex(ValueError, "complete_scan_claim_invalid"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_signed_wrong_occurrence_index_claim_is_fail_closed(self) -> None:
        audit = self.build_audit(occurrence_leaf_indices=[0])
        with self.assertRaisesRegex(ValueError, "exactly_one_occurrence_claim_invalid"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_stale_checkpoint_is_rejected(self) -> None:
        registration = self.build_registration(max_checkpoint_age_seconds=1800)
        pinned, checkpoint, audit = self.build_bundle(registration)
        with self.assertRaisesRegex(ValueError, "checkpoint_age_exceeded"):
            self.evaluate(
                replay_registration=registration,
                pinned_checkpoint=pinned,
                checkpoint=checkpoint,
                occurrence_audit=audit,
                expected_registration_hash=registration["registration_hash"],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_stale_scan_is_rejected(self) -> None:
        registration = self.build_registration(max_scan_age_seconds=1200)
        pinned, checkpoint, audit = self.build_bundle(registration)
        with self.assertRaisesRegex(ValueError, "scan_age_exceeded"):
            self.evaluate(
                replay_registration=registration,
                pinned_checkpoint=pinned,
                checkpoint=checkpoint,
                occurrence_audit=audit,
                expected_registration_hash=registration["registration_hash"],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
            )

    def test_reference_time_must_match_source_lifecycle_gate(self) -> None:
        audit = self.build_audit(reference_time_utc="2026-12-20T03:30:00Z")
        with self.assertRaisesRegex(ValueError, "reference_time_mismatch"):
            self.evaluate(
                occurrence_audit=audit,
                expected_occurrence_audit_hash=audit["occurrence_audit_hash"],
                reference_time_utc="2026-12-20T03:30:00Z",
            )

    def test_source_lifecycle_verifier_is_required(self) -> None:
        with patch.object(
            lifecycle_source,
            "verify_provider_dataset_key_lifecycle_gate_v1",
            return_value=False,
        ):
            with self.assertRaisesRegex(ValueError, "source_invalid"):
                subject.build_provider_dataset_key_lifecycle_replay_registration_v1(
                    self.lifecycle_document,
                    self.lifecycle_context,
                    replay_registry_id="LIFECYCLE-REPLAY-REGISTRY-01",
                    replay_registry_namespace="STRATEGY-CORRELATION.DATASET-LIFECYCLE.V1",
                    adapter_id="LIFECYCLE-REPLAY-ADAPTER-01",
                    adapter_implementation_hash=_hash("adapter"),
                    replay_registry_key_id="LIFECYCLE-REPLAY-REGISTRY-KEY-01",
                    replay_registry_public_key_base64=self.registry_public_key_base64,
                    occurrence_auditor_id="LIFECYCLE-OCCURRENCE-AUDITOR-01",
                    occurrence_auditor_key_id="LIFECYCLE-OCCURRENCE-AUDITOR-KEY-01",
                    occurrence_auditor_public_key_base64=self.auditor_public_key_base64,
                    declared_at_utc="2026-08-22T01:00:00Z",
                    max_checkpoint_age_seconds=7200,
                    max_scan_age_seconds=7200,
                    max_occurrence_receipt_issue_delay_seconds=1800,
                )

    def test_positive_output_keeps_global_claims_and_authority_false(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["verification_state"], subject.VERIFICATION_STATE)
        self.assertTrue(result["facts"]["signed_replay_registry_evidence_checked"])
        self.assertFalse(
            result["facts"]["global_lifecycle_receipt_uniqueness_verified"]
        )
        self.assertFalse(result["facts"]["future_replay_absence_verified"])
        self.assertFalse(any(result["authority"].values()))
        self.assertEqual(result["permissions"], {"paper_authorized": False, "live_order_allowed": False})

    def test_output_verifier_accepts_exact_rebuild(self) -> None:
        result = self.evaluate()
        self.assertTrue(self.verify(result))

    def test_output_redaction_coherent_reseal_and_determinism(self) -> None:
        result = self.evaluate()
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(self.registry_public_key_base64, serialized)
        self.assertNotIn(self.auditor_public_key_base64, serialized)
        self.assertNotIn(self.checkpoint["signature_base64"], serialized)
        self.assertNotIn(self.occurrence_audit["signature_base64"], serialized)
        changed = deepcopy(result)
        changed["facts"]["global_lifecycle_receipt_uniqueness_verified"] = True
        _seal(changed, "verification_hash")
        self.assertFalse(self.verify(changed))
        self.assertEqual(result, self.evaluate())

    def test_production_api_never_accepts_private_key(self) -> None:
        public_functions = (
            subject.build_provider_dataset_key_lifecycle_replay_registration_v1,
            subject.verify_provider_dataset_key_lifecycle_replay_registration_v1,
            subject.build_pinned_lifecycle_replay_checkpoint_v1,
            subject.build_unsigned_lifecycle_replay_checkpoint_v1,
            subject.assemble_lifecycle_replay_checkpoint_v1,
            subject.build_unsigned_lifecycle_replay_occurrence_audit_v1,
            subject.assemble_lifecycle_replay_occurrence_audit_v1,
            subject.evaluate_provider_dataset_key_lifecycle_replay_gate_v1,
            subject.verify_provider_dataset_key_lifecycle_replay_gate_v1,
        )
        for function in public_functions:
            with self.subTest(function=function.__name__):
                names = tuple(inspect.signature(function).parameters)
                self.assertFalse(any("private" in name.lower() for name in names))


if __name__ == "__main__":
    unittest.main()
