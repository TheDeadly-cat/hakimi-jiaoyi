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

from exchange_terminal.services import strategy_correlation_provider_dataset_key_lifecycle_gate_v1 as lifecycle_gate
from exchange_terminal.services import strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1 as subject
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1
    as provider_binding_fixtures,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


class StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationLifecycleBindingGateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = provider_binding_fixtures.StrategyCorrelationUncertaintyMultiWindowObservationMembershipProviderAttestationBindingGateV1Tests(
            methodName="test_provider_signed_disjoint_memberships_pass_locally"
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)

    @staticmethod
    def _attestation_context(provider_window: dict[str, object]) -> dict[str, object]:
        return {
            "composition_document": provider_window["composition_document"],
            "composition_context": provider_window["composition_context"],
            "registration": provider_window["registration"],
            "provider_dataset_public_key_base64": provider_window[
                "dataset_public_key_base64"
            ],
            "attestation_receipt": provider_window["attestation_receipt"],
            "expected_registration_hash": provider_window["registration"][
                "registration_hash"
            ],
            "expected_attestation_hash": provider_window[
                "attestation_receipt"
            ]["attestation_hash"],
        }

    def _lifecycle_window(
        self,
        window_id: str,
        provider_window: dict[str, object],
        governance_private_key: Ed25519PrivateKey,
        *,
        revoked: bool = False,
        reference_time_utc: str = "2026-12-20T03:00:00Z",
    ) -> dict[str, object]:
        governance_public_key_base64 = _public_key_base64(
            governance_private_key
        )
        attestation_document = provider_window["verification_document"]
        attestation_context = self._attestation_context(provider_window)
        registration = lifecycle_gate.build_provider_dataset_key_lifecycle_registration_v1(
            attestation_document,
            attestation_context,
            governance_key_id="DATASET-LIFECYCLE-GOV-2026-01",
            governance_public_key_base64=governance_public_key_base64,
            key_epoch=1,
            previous_provider_dataset_key_id="DATASET-KEY-2025-09",
            previous_provider_dataset_key_commitment=_hash(
                "previous-provider-dataset-key"
            ),
            rotation_policy_id="DATASET-ROTATION-POLICY-01",
            rotation_policy_hash=_hash("rotation-policy-v1"),
            revocation_registry_id="DATASET-REVOCATION-REGISTRY-01",
            custody_policy_id="DATASET-CUSTODY-POLICY-01",
            custody_policy_hash=_hash("custody-policy-v1"),
            declared_at_utc="2026-08-22T00:00:00Z",
            max_receipt_age_seconds=7200,
            max_revocation_snapshot_age_seconds=7200,
            max_receipt_issue_delay_seconds=1800,
        )
        unsigned = lifecycle_gate.build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1(
            registration,
            revocation_snapshot_hash=_hash("revocation-snapshot-2026-12-20"),
            revocation_snapshot_at_utc="2026-12-20T02:00:00Z",
            provider_dataset_key_revoked=revoked,
            provider_key_binding_claimed=True,
            provider_dataset_key_custody_claimed=True,
            custody_domains_separated=True,
            audit_completed_at_utc="2026-12-20T02:05:00Z",
            issued_at_utc="2026-12-20T02:10:00Z",
        )
        signature = governance_private_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        receipt = lifecycle_gate.assemble_provider_dataset_key_lifecycle_governance_receipt_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )
        gate_document = None
        if not revoked:
            gate_document = lifecycle_gate.evaluate_provider_dataset_key_lifecycle_gate_v1(
                attestation_document,
                attestation_context,
                registration,
                governance_public_key_base64,
                receipt,
                expected_registration_hash=registration["registration_hash"],
                expected_lifecycle_receipt_hash=receipt[
                    "lifecycle_receipt_hash"
                ],
                reference_time_utc=reference_time_utc,
            )
        return {
            "window_id": window_id,
            "attestation_document": attestation_document,
            "attestation_context": attestation_context,
            "registration": registration,
            "governance_public_key_base64": governance_public_key_base64,
            "receipt": receipt,
            "gate_document": gate_document,
            "reference_time_utc": reference_time_utc,
        }

    @staticmethod
    def _expected_binding(lifecycle_window: dict[str, object]) -> dict[str, object]:
        document = lifecycle_window["gate_document"]
        return {
            "custody_policy_hash": document["custody_policy_hash"],
            "custody_policy_id": document["custody_policy_id"],
            "governance_key_id": document["governance_key_id"],
            "governance_public_key_sha256": document[
                "governance_public_key_sha256"
            ],
            "governance_receipt_issued_at_utc": document[
                "governance_receipt_issued_at_utc"
            ],
            "key_epoch": document["key_epoch"],
            "lifecycle_governance_receipt_hash": document[
                "lifecycle_governance_receipt_hash"
            ],
            "lifecycle_registration_hash": document[
                "lifecycle_registration_hash"
            ],
            "lifecycle_verification_hash": document["verification_hash"],
            "previous_provider_dataset_key_commitment": document[
                "previous_provider_dataset_key_commitment"
            ],
            "previous_provider_dataset_key_id": document[
                "previous_provider_dataset_key_id"
            ],
            "provider_dataset_key_id": document["provider_dataset_key_id"],
            "provider_dataset_public_key_sha256": document[
                "provider_dataset_public_key_sha256"
            ],
            "provider_id_hash": document["provider_id_hash"],
            "reference_time_utc": document["reference_time_utc"],
            "revocation_registry_id": document["revocation_registry_id"],
            "revocation_snapshot_at_utc": document[
                "revocation_snapshot_at_utc"
            ],
            "revocation_snapshot_hash": document["revocation_snapshot_hash"],
            "rotation_policy_hash": document["rotation_policy_hash"],
            "rotation_policy_id": document["rotation_policy_id"],
            "source_attestation_hash": document["source_attestation_hash"],
            "source_attestation_verification_hash": document[
                "source_attestation_verification_hash"
            ],
            "source_dataset_registration_hash": document[
                "source_dataset_registration_hash"
            ],
            "window_id": lifecycle_window["window_id"],
        }

    @staticmethod
    def _bundle(lifecycle_window: dict[str, object]) -> dict[str, object]:
        return {
            "attestation_context": lifecycle_window["attestation_context"],
            "attestation_document": lifecycle_window["attestation_document"],
            "governance_public_key_base64": lifecycle_window[
                "governance_public_key_base64"
            ],
            "lifecycle_gate_document": lifecycle_window["gate_document"],
            "lifecycle_receipt": lifecycle_window["receipt"],
            "lifecycle_registration": lifecycle_window["registration"],
            "window_id": lifecycle_window["window_id"],
        }

    def _context(self, *, duplicate_windows: bool = False) -> dict[str, object]:
        provider_context = self.source._context(
            second_day_offset=0 if duplicate_windows else 365
        )
        provider_gate = self.source._evaluate(provider_context)
        governance_key = Ed25519PrivateKey.generate()
        lifecycle_windows = [
            self._lifecycle_window(
                window_id,
                provider_window,
                governance_key,
            )
            for window_id, provider_window in zip(
                provider_context["windows"],
                provider_context["provider_windows"],
                strict=True,
            )
        ]
        expected_bindings = [
            self._expected_binding(window) for window in lifecycle_windows
        ]
        preregistration = subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_preregistration_v1(
            provider_context["binding_preregistration"],
            provider_context["overlap_preregistration"],
            provider_context["multi_preregistration"],
            expected_bindings,
            registration_sequence=4,
        )
        self.assertIsNotNone(preregistration)
        return {
            **provider_context,
            "provider_gate": provider_gate,
            "lifecycle_windows": lifecycle_windows,
            "lifecycle_preregistration": preregistration,
            "lifecycle_bundles": [
                self._bundle(window) for window in lifecycle_windows
            ],
        }

    def _evaluate(self, context: dict[str, object]) -> dict[str, object]:
        result = subject.evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
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
            expected_preregistration_hash=context["lifecycle_preregistration"][
                "preregistration_hash"
            ],
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
        self.assertIsInstance(result, dict)
        return result

    def test_fresh_lifecycle_claims_pass_locally(self) -> None:
        context = self._context()
        gate = self._evaluate(context)

        self.assertEqual(context["provider_gate"]["status"], "PASS")
        self.assertEqual(gate["status"], "PASS")
        self.assertTrue(gate["facts"]["dataset_key_lifecycle_verified"])
        self.assertTrue(gate["facts"]["fresh_nonrevocation_claims_verified"])
        self.assertEqual(gate["summary"]["distinct_dataset_key_count"], 1)
        self.assertEqual(gate["summary"]["distinct_governance_key_count"], 1)

    def test_revoked_signed_receipt_is_unknown(self) -> None:
        context = self._context()
        window = context["lifecycle_windows"][0]
        revoked = self._lifecycle_window(
            window["window_id"],
            context["provider_windows"][0],
            Ed25519PrivateKey.generate(),
            revoked=True,
        )
        bundle = self._bundle(revoked)
        bundle["lifecycle_gate_document"] = window["gate_document"]
        context["lifecycle_bundles"][0] = bundle

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0121_LIFECYCLE_GATE_EXACT_REBUILD_FAILED"],
        )

    def test_wrong_governance_signature_is_unknown(self) -> None:
        context = self._context()
        receipt = context["lifecycle_bundles"][0]["lifecycle_receipt"]
        raw = bytearray(base64.b64decode(receipt["signature_base64"]))
        raw[0] ^= 1
        receipt["signature_base64"] = base64.b64encode(bytes(raw)).decode(
            "ascii"
        )

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")

    def test_lifecycle_gate_document_drift_is_unknown(self) -> None:
        context = self._context()
        context["lifecycle_bundles"][0]["lifecycle_gate_document"]["key_epoch"] += 1

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0121_LIFECYCLE_GATE_EXACT_REBUILD_FAILED"],
        )

    def test_upstream_verifier_cannot_promote_missing_positive_fact(self) -> None:
        context = self._context()
        context["lifecycle_bundles"][0]["lifecycle_gate_document"]["facts"][
            "fresh_non_revocation_claim_verified"
        ] = False

        with patch.object(
            lifecycle_gate,
            "verify_provider_dataset_key_lifecycle_gate_v1",
            return_value=True,
        ):
            gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")
        self.assertEqual(
            gate["gate_blockers"],
            ["ADR0121_LIFECYCLE_FACTS_INVALID"],
        )

    def test_source_attestation_splice_is_unknown(self) -> None:
        context = self._context()
        context["lifecycle_bundles"][0]["attestation_document"] = context[
            "lifecycle_bundles"
        ][1]["attestation_document"]

        gate = self._evaluate(context)

        self.assertEqual(gate["status"], "UNKNOWN")

    def test_reordered_or_missing_lifecycle_bundles_are_unknown(self) -> None:
        context = self._context()
        context["lifecycle_bundles"] = list(
            reversed(context["lifecycle_bundles"])
        )
        self.assertEqual(self._evaluate(context)["status"], "UNKNOWN")

        context = self._context()
        context["lifecycle_bundles"] = context["lifecycle_bundles"][:1]
        self.assertEqual(self._evaluate(context)["status"], "UNKNOWN")

    def test_same_dataset_key_governance_drift_rejects_preregistration(self) -> None:
        context = self._context()
        bindings = deepcopy(
            context["lifecycle_preregistration"]["expected_lifecycle_bindings"]
        )
        bindings[1]["rotation_policy_hash"] = _hash("drifted-policy")

        self.assertIsNone(
            subject.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_preregistration_v1(
                context["binding_preregistration"],
                context["overlap_preregistration"],
                context["multi_preregistration"],
                bindings,
                registration_sequence=5,
            )
        )

    def test_provider_binding_block_is_preserved(self) -> None:
        context = self._context(duplicate_windows=True)

        gate = self._evaluate(context)

        self.assertEqual(context["provider_gate"]["status"], "BLOCK")
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(
            gate["gate_blockers"],
            ["PROVIDER_ATTESTATION_BINDING_GATE_V1_BLOCKED"],
        )

    def test_verifier_rejects_resealed_authority_promotion(self) -> None:
        context = self._context()
        gate = self._evaluate(context)
        arguments = {
            "expected_gate_hash": gate["gate_hash"],
            "expected_preregistration_hash": context[
                "lifecycle_preregistration"
            ]["preregistration_hash"],
            "expected_provider_binding_gate_hash": context["provider_gate"][
                "gate_hash"
            ],
            "expected_provider_binding_preregistration_hash": context[
                "binding_preregistration"
            ]["preregistration_hash"],
            "expected_overlap_gate_hash": context["overlap_gate"]["gate_hash"],
            "expected_overlap_preregistration_hash": context[
                "overlap_preregistration"
            ]["preregistration_hash"],
            "expected_overlap_evidence_hash": context["overlap_evidence"][
                "evidence_hash"
            ],
            "expected_multi_window_gate_hash": context["multi_gate"][
                "gate_hash"
            ],
            "expected_multi_window_preregistration_hash": context[
                "multi_preregistration"
            ]["preregistration_hash"],
            "expected_window_audit_hashes": context["audit_hashes"],
        }
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
                gate,
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
                **arguments,
            )
        )
        forged = deepcopy(gate)
        forged["authority"]["writer_allowed"] = True
        unsigned = deepcopy(forged)
        unsigned.pop("gate_hash")
        forged = seal_strict_canonical_document(unsigned, "gate_hash")
        arguments["expected_gate_hash"] = forged["gate_hash"]
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
                forged,
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
                **arguments,
            )
        )

    def test_output_redacts_governance_material_and_keeps_external_trust_false(self) -> None:
        context = self._context()
        gate = self._evaluate(context)
        rendered = json.dumps(gate, sort_keys=True)
        first = context["lifecycle_windows"][0]

        self.assertNotIn(first["governance_public_key_base64"], rendered)
        self.assertNotIn(first["receipt"]["signature_base64"], rendered)
        self.assertNotIn('"lifecycle_receipt":', rendered)
        self.assertFalse(gate["facts"]["external_governance_authority_verified"])
        self.assertFalse(
            gate["facts"]["external_provider_dataset_key_control_verified"]
        )
        self.assertFalse(
            gate["facts"]["external_revocation_registry_durability_verified"]
        )
        self.assertFalse(
            gate["facts"]["lifecycle_receipt_replay_registry_checked"]
        )
        self.assertFalse(gate["facts"]["content_issuance_replay_verified"])

    def test_source_pins_match_reviewed_implementations(self) -> None:
        services = Path(__file__).resolve().parents[1] / "exchange_terminal" / "services"
        expected = {
            "strategy_correlation_provider_dataset_key_lifecycle_gate_v1.py": subject.LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256,
            "strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1.py": subject.PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256,
        }
        for filename, expected_hash in expected.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    sha256((services / filename).read_bytes()).hexdigest(),
                    expected_hash,
                )


if __name__ == "__main__":
    unittest.main()
