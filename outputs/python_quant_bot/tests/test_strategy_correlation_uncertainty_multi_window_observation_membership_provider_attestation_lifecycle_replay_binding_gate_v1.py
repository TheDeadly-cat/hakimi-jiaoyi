from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1
    as lifecycle_replay,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1
    as lifecycle_binding_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleReplayBindingGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = lifecycle_binding_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleBindingGateV1Tests(
            methodName="test_fresh_lifecycle_claims_pass_locally"
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.registry_private_key = Ed25519PrivateKey.generate()
        self.registry_public_key_base64 = _public_key_base64(
            self.registry_private_key
        )
        self.auditor_private_key = Ed25519PrivateKey.generate()
        self.auditor_public_key_base64 = _public_key_base64(
            self.auditor_private_key
        )
        self.context = self._context()

    @staticmethod
    def _lifecycle_context(bundle: dict[str, object]) -> dict[str, object]:
        document = bundle["lifecycle_gate_document"]
        registration = bundle["lifecycle_registration"]
        receipt = bundle["lifecycle_receipt"]
        return {
            "attestation_document": bundle["attestation_document"],
            "attestation_context": bundle["attestation_context"],
            "lifecycle_registration": registration,
            "governance_public_key_base64": bundle[
                "governance_public_key_base64"
            ],
            "lifecycle_receipt": receipt,
            "expected_registration_hash": registration["registration_hash"],
            "expected_lifecycle_receipt_hash": receipt[
                "lifecycle_receipt_hash"
            ],
            "reference_time_utc": document["reference_time_utc"],
        }

    def _registration(self, bundle: dict[str, object]) -> dict[str, object]:
        return lifecycle_replay.build_provider_dataset_key_lifecycle_replay_registration_v1(
            bundle["lifecycle_gate_document"],
            self._lifecycle_context(bundle),
            replay_registry_id="MULTI-WINDOW-LIFECYCLE-REPLAY-REGISTRY-01",
            replay_registry_namespace=(
                "STRATEGY-CORRELATION.MULTI-WINDOW-LIFECYCLE.V1"
            ),
            adapter_id="MULTI-WINDOW-LIFECYCLE-REPLAY-ADAPTER-01",
            adapter_implementation_hash=_hash("adr0352-replay-adapter-v1"),
            replay_registry_key_id=(
                "MULTI-WINDOW-LIFECYCLE-REPLAY-REGISTRY-KEY-01"
            ),
            replay_registry_public_key_base64=self.registry_public_key_base64,
            occurrence_auditor_id=(
                "MULTI-WINDOW-LIFECYCLE-OCCURRENCE-AUDITOR-01"
            ),
            occurrence_auditor_key_id=(
                "MULTI-WINDOW-LIFECYCLE-OCCURRENCE-AUDITOR-KEY-01"
            ),
            occurrence_auditor_public_key_base64=self.auditor_public_key_base64,
            declared_at_utc="2026-08-22T01:00:00Z",
            max_checkpoint_age_seconds=7200,
            max_scan_age_seconds=7200,
            max_occurrence_receipt_issue_delay_seconds=1800,
        )

    @staticmethod
    def _expected_binding(
        window_id: str,
        lifecycle_bundle: dict[str, object],
        replay_bundle: dict[str, object],
    ) -> dict[str, object]:
        lifecycle_document = lifecycle_bundle["lifecycle_gate_document"]
        registration = replay_bundle["replay_registration"]
        pinned = replay_bundle["pinned_checkpoint"]
        checkpoint = replay_bundle["checkpoint"]
        audit = replay_bundle["occurrence_audit"]
        replay_gate = replay_bundle["replay_gate_document"]
        attestation_registration = lifecycle_bundle["attestation_context"][
            "registration"
        ]
        upstream_keys = sorted(
            {
                lifecycle_document["provider_dataset_public_key_sha256"],
                lifecycle_document["governance_public_key_sha256"],
                attestation_registration[
                    "identity_registry_public_key_sha256"
                ],
                attestation_registration[
                    "timestamp_adapter_public_key_sha256"
                ],
            }
        )
        return {
            "adapter_id": registration["adapter_id"],
            "adapter_implementation_hash": registration[
                "adapter_implementation_hash"
            ],
            "audit_issued_at_utc": audit["audit_issued_at_utc"],
            "checkpoint_hash": replay_gate["checkpoint_hash"],
            "checkpoint_issued_at_utc": checkpoint["issued_at_utc"],
            "checkpoint_root_hash": replay_gate["checkpoint_root_hash"],
            "checkpoint_tree_size": replay_gate["checkpoint_tree_size"],
            "consistency_proof_hash": audit["consistency_proof_hash"],
            "declared_at_utc": registration["declared_at_utc"],
            "excluded_upstream_public_key_set_hash": strict_canonical_hash(
                upstream_keys
            ),
            "inclusion_proof_hash": audit["inclusion_proof_hash"],
            "index_snapshot_record_count": audit[
                "index_snapshot_record_count"
            ],
            "index_snapshot_root_hash": audit["index_snapshot_root_hash"],
            "lifecycle_receipt_hash": replay_gate[
                "source_lifecycle_receipt_hash"
            ],
            "lifecycle_verification_hash": replay_gate[
                "source_lifecycle_verification_hash"
            ],
            "max_checkpoint_age_seconds": registration[
                "max_checkpoint_age_seconds"
            ],
            "max_occurrence_receipt_issue_delay_seconds": registration[
                "max_occurrence_receipt_issue_delay_seconds"
            ],
            "max_scan_age_seconds": registration["max_scan_age_seconds"],
            "occurrence_audit_hash": replay_gate["occurrence_audit_hash"],
            "occurrence_auditor_id": registration["occurrence_auditor_id"],
            "occurrence_auditor_key_id": registration[
                "occurrence_auditor_key_id"
            ],
            "occurrence_auditor_public_key_sha256": registration[
                "occurrence_auditor_public_key_sha256"
            ],
            "occurrence_count_claim": replay_gate[
                "occurrence_count_claim"
            ],
            "occurrence_leaf_index": replay_gate["occurrence_leaf_index"],
            "pinned_checkpoint_hash": pinned["pin_hash"],
            "previous_checkpoint_hash": checkpoint[
                "previous_checkpoint_hash"
            ],
            "previous_checkpoint_root_hash": replay_gate[
                "previous_checkpoint_root_hash"
            ],
            "previous_checkpoint_tree_size": replay_gate[
                "previous_checkpoint_tree_size"
            ],
            "reference_time_utc": replay_gate["reference_time_utc"],
            "replay_registration_hash": replay_gate[
                "replay_registration_hash"
            ],
            "replay_registry_id": replay_gate["replay_registry_id"],
            "replay_registry_key_id": registration[
                "replay_registry_key_id"
            ],
            "replay_registry_namespace": registration[
                "replay_registry_namespace"
            ],
            "replay_registry_public_key_sha256": registration[
                "replay_registry_public_key_sha256"
            ],
            "scan_completed_at_utc": replay_gate["scan_completed_at_utc"],
            "scan_end_index_exclusive": audit[
                "scan_end_index_exclusive"
            ],
            "scan_start_index": audit["scan_start_index"],
            "window_id": window_id,
        }

    def _preregister(
        self,
        context: dict[str, object],
        bindings: list[dict[str, object]],
    ) -> dict[str, object] | None:
        return subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_preregistration_v1(
            context["lifecycle_preregistration"],
            context["binding_preregistration"],
            context["overlap_preregistration"],
            context["multi_preregistration"],
            bindings,
            registration_sequence=(
                context["lifecycle_preregistration"]["registration_sequence"]
                + 1
            ),
        )

    def _context(self, *, duplicate_windows: bool = False) -> dict[str, object]:
        context = self.source._context(duplicate_windows=duplicate_windows)
        lifecycle_gate = self.source._evaluate(context)
        lifecycle_bundles = context["lifecycle_bundles"]
        receipt_hashes = [
            bundle["lifecycle_receipt"]["lifecycle_receipt_hash"]
            for bundle in lifecycle_bundles
        ]
        self.assertEqual(len(receipt_hashes), 2)
        old_root = lifecycle_replay.hash_lifecycle_replay_leaf_v1(
            _hash("shared-prior-lifecycle-receipt")
        )
        source_leaves = [
            lifecycle_replay.hash_lifecycle_replay_leaf_v1(value)
            for value in receipt_hashes
        ]
        left_subtree = lifecycle_replay.hash_lifecycle_replay_node_v1(
            old_root,
            source_leaves[0],
        )
        checkpoint_root = lifecycle_replay.hash_lifecycle_replay_node_v1(
            left_subtree,
            source_leaves[1],
        )
        consistency_proof = list(source_leaves)
        replay_bundles = []
        expected_bindings = []
        for position, (window_id, lifecycle_bundle) in enumerate(
            zip(
                context["windows"],
                lifecycle_bundles,
                strict=True,
            )
        ):
            registration = self._registration(lifecycle_bundle)
            pinned = lifecycle_replay.build_pinned_lifecycle_replay_checkpoint_v1(
                registration,
                tree_size=1,
                root_hash=old_root,
                checkpoint_hash=_hash("shared-previous-signed-checkpoint"),
            )
            unsigned_checkpoint = lifecycle_replay.build_unsigned_lifecycle_replay_checkpoint_v1(
                registration,
                pinned,
                tree_size=3,
                root_hash=checkpoint_root,
                issued_at_utc="2026-12-20T02:20:00Z",
            )
            checkpoint_signature = self.registry_private_key.sign(
                bytes.fromhex(unsigned_checkpoint["receipt_content_sha256"])
            )
            checkpoint = lifecycle_replay.assemble_lifecycle_replay_checkpoint_v1(
                unsigned_checkpoint,
                base64.b64encode(checkpoint_signature).decode("ascii"),
            )
            leaf_index = position + 1
            inclusion_proof = (
                [old_root, source_leaves[1]]
                if position == 0
                else [left_subtree]
            )
            unsigned_audit = lifecycle_replay.build_unsigned_lifecycle_replay_occurrence_audit_v1(
                registration,
                checkpoint,
                inclusion_proof,
                consistency_proof,
                occurrence_leaf_index=leaf_index,
                scan_start_index=0,
                scan_end_index_exclusive=3,
                index_snapshot_record_count=3,
                occurrence_count=1,
                occurrence_leaf_indices=[leaf_index],
                index_snapshot_root_hash=_hash(
                    "shared-complete-index-snapshot"
                ),
                scan_completed_at_utc="2026-12-20T02:30:00Z",
                audit_issued_at_utc="2026-12-20T02:40:00Z",
                reference_time_utc="2026-12-20T03:00:00Z",
            )
            audit_signature = self.auditor_private_key.sign(
                bytes.fromhex(unsigned_audit["receipt_content_sha256"])
            )
            audit = lifecycle_replay.assemble_lifecycle_replay_occurrence_audit_v1(
                unsigned_audit,
                base64.b64encode(audit_signature).decode("ascii"),
            )
            lifecycle_context = self._lifecycle_context(lifecycle_bundle)
            replay_gate = lifecycle_replay.evaluate_provider_dataset_key_lifecycle_replay_gate_v1(
                lifecycle_bundle["lifecycle_gate_document"],
                lifecycle_context,
                registration,
                self.registry_public_key_base64,
                self.auditor_public_key_base64,
                pinned,
                checkpoint,
                inclusion_proof,
                consistency_proof,
                audit,
                expected_registration_hash=registration["registration_hash"],
                expected_pinned_checkpoint_hash=pinned["pin_hash"],
                expected_checkpoint_hash=checkpoint["checkpoint_hash"],
                expected_occurrence_audit_hash=audit[
                    "occurrence_audit_hash"
                ],
                reference_time_utc="2026-12-20T03:00:00Z",
            )
            replay_bundle = {
                "checkpoint": checkpoint,
                "consistency_proof": consistency_proof,
                "inclusion_proof": inclusion_proof,
                "occurrence_audit": audit,
                "occurrence_auditor_public_key_base64": (
                    self.auditor_public_key_base64
                ),
                "pinned_checkpoint": pinned,
                "replay_gate_document": replay_gate,
                "replay_registration": registration,
                "replay_registry_public_key_base64": (
                    self.registry_public_key_base64
                ),
                "window_id": window_id,
            }
            replay_bundles.append(replay_bundle)
            expected_bindings.append(
                self._expected_binding(
                    window_id,
                    lifecycle_bundle,
                    replay_bundle,
                )
            )
        preregistration = self._preregister(context, expected_bindings)
        self.assertIsNotNone(preregistration)
        return {
            **context,
            "lifecycle_gate": lifecycle_gate,
            "replay_bindings": expected_bindings,
            "replay_bundles": replay_bundles,
            "replay_preregistration": preregistration,
        }

    def _evaluate(self, context: dict[str, object]) -> dict[str, object]:
        gate = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
            context["replay_preregistration"],
            context["lifecycle_gate"],
            context["lifecycle_preregistration"],
            context["provider_gate"],
            context["binding_preregistration"],
            context["overlap_gate"],
            context["overlap_preregistration"],
            context["overlap_evidence"],
            context["multi_gate"],
            context["multi_preregistration"],
            context["window_audits"],
            context["provider_bundles"],
            context["lifecycle_bundles"],
            context["replay_bundles"],
            expected_preregistration_hash=context["replay_preregistration"][
                "preregistration_hash"
            ],
            expected_lifecycle_binding_gate_hash=context["lifecycle_gate"][
                "gate_hash"
            ],
            expected_lifecycle_binding_preregistration_hash=context[
                "lifecycle_preregistration"
            ]["preregistration_hash"],
            expected_provider_binding_gate_hash=context["provider_gate"][
                "gate_hash"
            ],
            expected_provider_binding_preregistration_hash=context[
                "binding_preregistration"
            ]["preregistration_hash"],
            expected_overlap_gate_hash=context["overlap_gate"]["gate_hash"],
            expected_overlap_preregistration_hash=context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            expected_overlap_evidence_hash=context["overlap_evidence"][
                "evidence_hash"
            ],
            expected_multi_window_gate_hash=context["multi_gate"]["gate_hash"],
            expected_multi_window_preregistration_hash=context[
                "multi_preregistration"
            ]["preregistration_hash"],
            expected_window_audit_hashes=context["audit_hashes"],
        )
        self.assertIsInstance(gate, dict)
        return gate

    def _verify(
        self,
        gate: dict[str, object],
        context: dict[str, object],
        *,
        expected_gate_hash: str | None = None,
    ) -> bool:
        return subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_replay_binding_gate_v1(
            gate,
            context["replay_preregistration"],
            context["lifecycle_gate"],
            context["lifecycle_preregistration"],
            context["provider_gate"],
            context["binding_preregistration"],
            context["overlap_gate"],
            context["overlap_preregistration"],
            context["overlap_evidence"],
            context["multi_gate"],
            context["multi_preregistration"],
            context["window_audits"],
            context["provider_bundles"],
            context["lifecycle_bundles"],
            context["replay_bundles"],
            expected_gate_hash=expected_gate_hash or gate["gate_hash"],
            expected_preregistration_hash=context["replay_preregistration"][
                "preregistration_hash"
            ],
            expected_lifecycle_binding_gate_hash=context["lifecycle_gate"][
                "gate_hash"
            ],
            expected_lifecycle_binding_preregistration_hash=context[
                "lifecycle_preregistration"
            ]["preregistration_hash"],
            expected_provider_binding_gate_hash=context["provider_gate"][
                "gate_hash"
            ],
            expected_provider_binding_preregistration_hash=context[
                "binding_preregistration"
            ]["preregistration_hash"],
            expected_overlap_gate_hash=context["overlap_gate"]["gate_hash"],
            expected_overlap_preregistration_hash=context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            expected_overlap_evidence_hash=context["overlap_evidence"][
                "evidence_hash"
            ],
            expected_multi_window_gate_hash=context["multi_gate"]["gate_hash"],
            expected_multi_window_preregistration_hash=context[
                "multi_preregistration"
            ]["preregistration_hash"],
            expected_window_audit_hashes=context["audit_hashes"],
        )

    def test_existing_adr0351_pass_still_has_no_replay_evidence(self) -> None:
        lifecycle_gate = self.context["lifecycle_gate"]

        self.assertEqual(lifecycle_gate["status"], "PASS")
        self.assertFalse(
            lifecycle_gate["facts"][
                "lifecycle_receipt_replay_registry_checked"
            ]
        )
        self.assertFalse(
            any("replay" in key.lower() for key in lifecycle_gate)
        )

    def test_common_registry_view_passes_locally(self) -> None:
        gate = self._evaluate(self.context)

        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(
            gate["facts"]["signed_lifecycle_replay_evidence_checked"]
        )
        self.assertTrue(gate["facts"]["common_registry_view_bound"])
        self.assertEqual(gate["summary"]["registry_view_count"], 1)
        self.assertEqual(
            gate["summary"]["distinct_occurrence_leaf_index_count"],
            2,
        )
        self.assertFalse(
            gate["facts"]["global_lifecycle_receipt_uniqueness_verified"]
        )

    def test_preregistration_rejects_split_view_and_duplicate_leaf(self) -> None:
        split_view = deepcopy(self.context["replay_bindings"])
        split_view[1]["checkpoint_root_hash"] = _hash("split-view-root")
        self.assertIsNone(self._preregister(self.context, split_view))

        duplicate_leaf = deepcopy(self.context["replay_bindings"])
        duplicate_leaf[1]["occurrence_leaf_index"] = duplicate_leaf[0][
            "occurrence_leaf_index"
        ]
        self.assertIsNone(self._preregister(self.context, duplicate_leaf))

    def test_missing_or_reordered_replay_bundles_are_unknown(self) -> None:
        context = deepcopy(self.context)
        context["replay_bundles"] = list(reversed(context["replay_bundles"]))
        self.assertEqual(self._evaluate(context)["status"], "UNKNOWN")

        context = deepcopy(self.context)
        context["replay_bundles"] = context["replay_bundles"][:1]
        self.assertEqual(self._evaluate(context)["status"], "UNKNOWN")

    def test_wrong_registry_signature_is_unknown(self) -> None:
        context = deepcopy(self.context)
        signature = context["replay_bundles"][0]["checkpoint"][
            "signature_base64"
        ]
        raw = bytearray(base64.b64decode(signature))
        raw[0] ^= 1
        context["replay_bundles"][0]["checkpoint"][
            "signature_base64"
        ] = base64.b64encode(bytes(raw)).decode("ascii")

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0122_LIFECYCLE_REPLAY_GATE_EXACT_REBUILD_FAILED"],
        )

    def test_replay_gate_source_splice_is_unknown(self) -> None:
        context = deepcopy(self.context)
        context["replay_bundles"][0]["replay_gate_document"] = context[
            "replay_bundles"
        ][1]["replay_gate_document"]

        self.assertEqual(self._evaluate(context)["status"], "UNKNOWN")

    def test_upstream_replay_verifier_cannot_promote_missing_fact(self) -> None:
        context = deepcopy(self.context)
        context["replay_bundles"][0]["replay_gate_document"]["facts"][
            "complete_scan_claim_verified"
        ] = False

        with patch.object(
            lifecycle_replay,
            "verify_provider_dataset_key_lifecycle_replay_gate_v1",
            return_value=True,
        ):
            gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0122_LIFECYCLE_REPLAY_FACTS_INVALID"],
        )

    def test_lifecycle_binding_block_is_preserved(self) -> None:
        context = self._context(duplicate_windows=True)

        gate = self._evaluate(context)

        self.assertEqual(context["lifecycle_gate"]["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["gate_blockers"],
            ["LIFECYCLE_BINDING_GATE_V1_BLOCKED"],
        )

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        gate = self._evaluate(self.context)
        self.assertTrue(self._verify(gate, self.context))

        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")

        self.assertFalse(
            self._verify(
                forged,
                self.context,
                expected_gate_hash=forged["gate_hash"],
            )
        )

    def test_output_redacts_raw_replay_material_and_external_claims(self) -> None:
        gate = self._evaluate(self.context)
        rendered = json.dumps(gate, sort_keys=True)
        first = self.context["replay_bundles"][0]

        self.assertNotIn(self.registry_public_key_base64, rendered)
        self.assertNotIn(self.auditor_public_key_base64, rendered)
        self.assertNotIn(first["checkpoint"]["signature_base64"], rendered)
        self.assertNotIn('"inclusion_proof"', rendered)
        self.assertNotIn('"consistency_proof"', rendered)
        self.assertFalse(
            gate["facts"]["external_replay_registry_authority_verified"]
        )
        self.assertFalse(
            gate["facts"]["durable_checkpoint_publication_verified"]
        )
        self.assertFalse(
            gate["facts"]["multi_observer_split_view_absence_verified"]
        )
        self.assertFalse(gate["facts"]["content_issuance_replay_verified"])

    def test_source_pins_match_reviewed_implementations(self) -> None:
        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        expected = {
            "strategy_correlation_provider_dataset_key_lifecycle_replay_gate_v1.py": subject.LIFECYCLE_REPLAY_V1_IMPLEMENTATION_SHA256,
            "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1.py": subject.LIFECYCLE_BINDING_V1_IMPLEMENTATION_SHA256,
        }
        for filename, expected_hash in expected.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    sha256((services / filename).read_bytes()).hexdigest(),
                    expected_hash,
                )


if __name__ == "__main__":
    unittest.main()
