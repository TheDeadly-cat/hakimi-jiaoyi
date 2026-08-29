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

from exchange_terminal.services import strategy_correlation_provider_dataset_content_attestation_v1 as attestation_source
from exchange_terminal.services import strategy_correlation_provider_dataset_key_lifecycle_gate_v1 as subject
from tests.test_strategy_correlation_provider_dataset_content_attestation_v1 import (
    StrategyCorrelationProviderDatasetContentAttestationV1Tests,
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


class StrategyCorrelationProviderDatasetKeyLifecycleGateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = StrategyCorrelationProviderDatasetContentAttestationV1Tests(
            methodName="test_positive_signature_claim_remains_non_authoritative"
        )
        self.source.setUp()
        self.attestation_document = self.source.evaluate()
        self.attestation_context = {
            "composition_document": self.source.composition_document,
            "composition_context": self.source.composition_context,
            "registration": self.source.registration,
            "provider_dataset_public_key_base64": (
                self.source.dataset_public_key_base64
            ),
            "attestation_receipt": self.source.receipt,
            "expected_registration_hash": self.source.registration[
                "registration_hash"
            ],
            "expected_attestation_hash": self.source.receipt["attestation_hash"],
        }
        self.governance_private_key = Ed25519PrivateKey.generate()
        self.governance_public_key_base64 = _public_key_base64(
            self.governance_private_key
        )
        self.registration = self.build_registration()
        self.receipt = self.build_receipt()

    def build_registration(self, **overrides):
        values = {
            "attestation_document": self.attestation_document,
            "attestation_context": self.attestation_context,
            "governance_key_id": "DATASET-LIFECYCLE-GOV-2026-01",
            "governance_public_key_base64": self.governance_public_key_base64,
            "key_epoch": 1,
            "previous_provider_dataset_key_id": "DATASET-KEY-2025-09",
            "previous_provider_dataset_key_commitment": _hash(
                "previous-provider-dataset-key"
            ),
            "rotation_policy_id": "DATASET-ROTATION-POLICY-01",
            "rotation_policy_hash": _hash("rotation-policy-v1"),
            "revocation_registry_id": "DATASET-REVOCATION-REGISTRY-01",
            "custody_policy_id": "DATASET-CUSTODY-POLICY-01",
            "custody_policy_hash": _hash("custody-policy-v1"),
            "declared_at_utc": "2026-08-22T00:00:00Z",
            "max_receipt_age_seconds": 7200,
            "max_revocation_snapshot_age_seconds": 7200,
            "max_receipt_issue_delay_seconds": 1800,
        }
        values.update(overrides)
        with self.source.source_verifiers():
            return subject.build_provider_dataset_key_lifecycle_registration_v1(
                **values
            )

    def build_receipt(
        self,
        *,
        registration=None,
        private_key=None,
        revocation_snapshot_hash=None,
        revocation_snapshot_at_utc="2026-12-20T02:00:00Z",
        provider_dataset_key_revoked=False,
        provider_key_binding_claimed=True,
        provider_dataset_key_custody_claimed=True,
        custody_domains_separated=True,
        audit_completed_at_utc="2026-12-20T02:05:00Z",
        issued_at_utc="2026-12-20T02:10:00Z",
    ):
        source_registration = registration or self.registration
        signing_key = private_key or self.governance_private_key
        unsigned = subject.build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1(
            source_registration,
            revocation_snapshot_hash=(
                revocation_snapshot_hash or _hash("revocation-snapshot-2026-12-20")
            ),
            revocation_snapshot_at_utc=revocation_snapshot_at_utc,
            provider_dataset_key_revoked=provider_dataset_key_revoked,
            provider_key_binding_claimed=provider_key_binding_claimed,
            provider_dataset_key_custody_claimed=(
                provider_dataset_key_custody_claimed
            ),
            custody_domains_separated=custody_domains_separated,
            audit_completed_at_utc=audit_completed_at_utc,
            issued_at_utc=issued_at_utc,
        )
        signature = signing_key.sign(bytes.fromhex(unsigned["receipt_content_sha256"]))
        return subject.assemble_provider_dataset_key_lifecycle_governance_receipt_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    def evaluate(self, **overrides):
        values = {
            "attestation_document": self.attestation_document,
            "attestation_context": self.attestation_context,
            "lifecycle_registration": self.registration,
            "governance_public_key_base64": self.governance_public_key_base64,
            "lifecycle_receipt": self.receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_lifecycle_receipt_hash": self.receipt[
                "lifecycle_receipt_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        values.update(overrides)
        with self.source.source_verifiers():
            return subject.evaluate_provider_dataset_key_lifecycle_gate_v1(**values)

    def verify(self, document, **overrides):
        values = {
            "attestation_document": self.attestation_document,
            "attestation_context": self.attestation_context,
            "lifecycle_registration": self.registration,
            "governance_public_key_base64": self.governance_public_key_base64,
            "lifecycle_receipt": self.receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_lifecycle_receipt_hash": self.receipt[
                "lifecycle_receipt_hash"
            ],
            "reference_time_utc": "2026-12-20T03:00:00Z",
        }
        values.update(overrides)
        with self.source.source_verifiers():
            return subject.verify_provider_dataset_key_lifecycle_gate_v1(
                document,
                **values,
            )

    def test_registration_binds_attestation_key_lineage_and_distinct_governance_role(self) -> None:
        self.assertEqual(
            self.registration["source_attestation_verification_hash"],
            self.attestation_document["verification_hash"],
        )
        self.assertEqual(self.registration["excluded_source_role_key_count"], 3)
        self.assertEqual(
            self.registration["governance_key_role"], subject.GOVERNANCE_KEY_ROLE
        )
        self.assertTrue(
            self.registration["facts"]["governance_key_role_separation_verified"]
        )
        self.assertFalse(any(self.registration["authority"].values()))

    def test_registration_verifier_accepts_exact_rebuild(self) -> None:
        with self.source.source_verifiers():
            self.assertTrue(
                subject.verify_provider_dataset_key_lifecycle_registration_v1(
                    self.registration,
                    self.attestation_document,
                    self.attestation_context,
                    self.governance_public_key_base64,
                    expected_registration_hash=self.registration[
                        "registration_hash"
                    ],
                )
            )

    def test_registration_is_deterministic_and_redacts_governance_key(self) -> None:
        self.assertEqual(self.registration, self.build_registration())
        self.assertNotIn("governance_public_key_base64", self.registration)

    def test_governance_key_cannot_reuse_dataset_or_source_role_keys(self) -> None:
        collision_keys = (
            self.source.dataset_public_key_base64,
            self.source.provider_bundle["identity_assertion_receipt"][
                "registry_public_key_base64"
            ],
            self.source.calendar_bundle["batch_verification_context"][
                "signature_verification_context"
            ]["attestation_receipt"]["public_key_base64"],
        )
        for public_key in collision_keys:
            with self.subTest(public_key=public_key[:8]):
                with self.assertRaisesRegex(ValueError, "governance_key_role_collision"):
                    self.build_registration(
                        governance_public_key_base64=public_key
                    )

    def test_governance_key_id_and_policy_boundaries_are_strict(self) -> None:
        with self.assertRaisesRegex(ValueError, "governance_key_id_invalid"):
            self.build_registration(governance_key_id="bad key")
        with self.assertRaisesRegex(ValueError, "policy_role_collision"):
            self.build_registration(
                custody_policy_id="DATASET-ROTATION-POLICY-01"
            )
        with self.assertRaisesRegex(ValueError, "policy_hash_invalid"):
            self.build_registration(custody_policy_hash=_hash("rotation-policy-v1"))

    def test_epoch_zero_and_rotation_chain_rules_are_strict(self) -> None:
        genesis = self.build_registration(
            key_epoch=0,
            previous_provider_dataset_key_id=subject.GENESIS_COMMITMENT,
            previous_provider_dataset_key_commitment=subject.GENESIS_COMMITMENT,
        )
        self.assertEqual(genesis["key_epoch"], 0)
        with self.assertRaisesRegex(ValueError, "genesis_commitment_invalid"):
            self.build_registration(key_epoch=0)
        with self.assertRaisesRegex(ValueError, "rotation_commitment_invalid"):
            self.build_registration(
                previous_provider_dataset_key_commitment=self.source.registration[
                    "provider_dataset_public_key_sha256"
                ]
            )

    def test_freshness_limits_reject_bool_alias_and_out_of_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "freshness_policy_invalid"):
            self.build_registration(max_receipt_age_seconds=True)
        with self.assertRaisesRegex(ValueError, "freshness_policy_invalid"):
            self.build_registration(max_receipt_issue_delay_seconds=0)

    def test_unsigned_receipt_binds_complete_lifecycle_claim(self) -> None:
        self.assertEqual(
            self.receipt["registration_hash"], self.registration["registration_hash"]
        )
        self.assertEqual(self.receipt["key_epoch"], 1)
        self.assertFalse(self.receipt["provider_dataset_key_revoked"])
        self.assertTrue(self.receipt["provider_key_binding_claimed"])
        self.assertTrue(self.receipt["provider_dataset_key_custody_claimed"])
        self.assertTrue(self.receipt["custody_domains_separated"])

    def test_positive_gate_reduces_gap_without_promoting_external_trust(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["verification_state"], subject.VERIFICATION_STATE)
        self.assertTrue(result["facts"]["fresh_non_revocation_claim_verified"])
        self.assertFalse(result["facts"]["external_governance_authority_verified"])
        self.assertFalse(
            result["facts"]["external_provider_dataset_key_control_verified"]
        )
        self.assertFalse(any(result["authority"].values()))
        self.assertEqual(result["permissions"], {"paper_authorized": False, "live_order_allowed": False})

    def test_output_verifier_accepts_exact_rebuild(self) -> None:
        result = self.evaluate()
        self.assertTrue(self.verify(result))

    def test_wrong_governance_signing_key_is_rejected(self) -> None:
        receipt = self.build_receipt(private_key=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "governance_signature_invalid"):
            self.evaluate(
                lifecycle_receipt=receipt,
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_signature_base64_is_strict(self) -> None:
        unsigned = subject.build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1(
            self.registration,
            revocation_snapshot_hash=_hash("strict-base64"),
            revocation_snapshot_at_utc="2026-12-20T02:00:00Z",
            provider_dataset_key_revoked=False,
            provider_key_binding_claimed=True,
            provider_dataset_key_custody_claimed=True,
            custody_domains_separated=True,
            audit_completed_at_utc="2026-12-20T02:05:00Z",
            issued_at_utc="2026-12-20T02:10:00Z",
        )
        with self.assertRaisesRegex(ValueError, "signature_base64_invalid"):
            subject.assemble_provider_dataset_key_lifecycle_governance_receipt_v1(
                unsigned,
                "not-base64",
            )

    def test_expected_registration_and_receipt_pins_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "registration_invalid"):
            self.evaluate(expected_registration_hash="0" * 64)
        with self.assertRaisesRegex(ValueError, "receipt_invalid"):
            self.evaluate(expected_lifecycle_receipt_hash="0" * 64)

    def test_signed_revocation_is_fail_closed(self) -> None:
        receipt = self.build_receipt(provider_dataset_key_revoked=True)
        with self.assertRaisesRegex(ValueError, "provider_dataset_key_revoked"):
            self.evaluate(
                lifecycle_receipt=receipt,
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_signed_provider_binding_denial_is_fail_closed(self) -> None:
        receipt = self.build_receipt(provider_key_binding_claimed=False)
        with self.assertRaisesRegex(ValueError, "binding_claim_denied"):
            self.evaluate(
                lifecycle_receipt=receipt,
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_signed_custody_denial_is_fail_closed(self) -> None:
        receipt = self.build_receipt(provider_dataset_key_custody_claimed=False)
        with self.assertRaisesRegex(ValueError, "custody_claim_denied"):
            self.evaluate(
                lifecycle_receipt=receipt,
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_signed_custody_domain_collision_is_fail_closed(self) -> None:
        receipt = self.build_receipt(custody_domains_separated=False)
        with self.assertRaisesRegex(ValueError, "domain_separation_denied"):
            self.evaluate(
                lifecycle_receipt=receipt,
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_stale_governance_receipt_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "receipt_age_exceeded"):
            self.evaluate(reference_time_utc="2026-12-20T05:00:00Z")

    def test_stale_revocation_snapshot_is_rejected_independently(self) -> None:
        registration = self.build_registration(
            max_receipt_age_seconds=14400,
            max_revocation_snapshot_age_seconds=1800,
        )
        receipt = self.build_receipt(registration=registration)
        with self.assertRaisesRegex(ValueError, "revocation_snapshot_age_exceeded"):
            self.evaluate(
                lifecycle_registration=registration,
                lifecycle_receipt=receipt,
                expected_registration_hash=registration["registration_hash"],
                expected_lifecycle_receipt_hash=receipt["lifecycle_receipt_hash"],
            )

    def test_reference_time_must_be_inside_dataset_key_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "reference_time_invalid"):
            self.evaluate(reference_time_utc="2027-08-23T00:00:00Z")

    def test_source_attestation_verifier_is_required(self) -> None:
        with patch.object(
            attestation_source,
            "verify_provider_dataset_content_attestation_v1",
            return_value=False,
        ):
            with self.assertRaisesRegex(ValueError, "source_attestation_invalid"):
                subject.build_provider_dataset_key_lifecycle_registration_v1(
                    self.attestation_document,
                    self.attestation_context,
                    governance_key_id="DATASET-LIFECYCLE-GOV-2026-01",
                    governance_public_key_base64=self.governance_public_key_base64,
                    key_epoch=1,
                    previous_provider_dataset_key_id="DATASET-KEY-2025-09",
                    previous_provider_dataset_key_commitment=_hash("previous-key"),
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

    def test_source_attestation_drift_is_rejected(self) -> None:
        changed = deepcopy(self.attestation_document)
        changed["provider_dataset_key_id"] = "DATASET-KEY-DRIFTED"
        with self.assertRaisesRegex(ValueError, "source_attestation_invalid"):
            self.build_registration(attestation_document=changed)

    def test_output_redacts_public_key_and_signature_bytes(self) -> None:
        result = self.evaluate()
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotIn(self.governance_public_key_base64, serialized)
        self.assertNotIn(self.receipt["signature_base64"], serialized)

    def test_coherently_resealed_output_drift_is_rejected(self) -> None:
        changed = deepcopy(self.evaluate())
        changed["facts"]["external_governance_authority_verified"] = True
        _seal(changed, "verification_hash")
        self.assertFalse(self.verify(changed))

    def test_evaluation_is_deterministic(self) -> None:
        self.assertEqual(self.evaluate(), self.evaluate())

    def test_production_api_never_accepts_private_key(self) -> None:
        public_functions = (
            subject.build_provider_dataset_key_lifecycle_registration_v1,
            subject.verify_provider_dataset_key_lifecycle_registration_v1,
            subject.build_unsigned_provider_dataset_key_lifecycle_governance_receipt_v1,
            subject.assemble_provider_dataset_key_lifecycle_governance_receipt_v1,
            subject.evaluate_provider_dataset_key_lifecycle_gate_v1,
            subject.verify_provider_dataset_key_lifecycle_gate_v1,
        )
        for function in public_functions:
            with self.subTest(function=function.__name__):
                names = tuple(inspect.signature(function).parameters)
                self.assertFalse(any("private" in name.lower() for name in names))


if __name__ == "__main__":
    unittest.main()
