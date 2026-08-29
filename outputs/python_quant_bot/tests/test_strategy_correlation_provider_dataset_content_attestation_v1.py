from __future__ import annotations

import base64
from contextlib import contextmanager
from copy import deepcopy
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import strategy_correlation_common_support_calendar_provider_composition_v1 as composition_source
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 as calendar_source
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as provider_source
from exchange_terminal.services.strategy_correlation_common_support_derivation_receipt_v1 import (
    build_correlation_common_support_derivation_receipt_v1,
)
from exchange_terminal.services.strategy_correlation_provider_dataset_content_attestation_v1 import (
    assemble_provider_dataset_content_attestation_receipt_v1,
    build_provider_dataset_content_attestation_registration_v1,
    build_unsigned_provider_dataset_content_attestation_v1,
    evaluate_provider_dataset_content_attestation_v1,
    verify_provider_dataset_content_attestation_registration_v1,
    verify_provider_dataset_content_attestation_v1,
)
from tests.test_strategy_correlation_common_support_calendar_provider_composition_v1 import (
    StrategyCorrelationCommonSupportCalendarProviderCompositionV1Tests,
)


def _public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


class StrategyCorrelationProviderDatasetContentAttestationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = StrategyCorrelationCommonSupportCalendarProviderCompositionV1Tests(
            methodName="test_positive_composition_is_bounded_and_inactive"
        )
        self.source.setUp()
        self.registry_private_key = Ed25519PrivateKey.generate()
        self.timestamp_private_key = Ed25519PrivateKey.generate()
        self.dataset_private_key = Ed25519PrivateKey.generate()
        self.dataset_public_key_base64 = _public_key_base64(self.dataset_private_key)
        self.calendar_bundle = deepcopy(self.source.calendar_bundle)
        self.calendar_bundle["batch_verification_context"] = {
            "signature_verification_context": {
                "attestation_receipt": {
                    "public_key_base64": _public_key_base64(
                        self.timestamp_private_key
                    ),
                },
            },
        }
        self.provider_bundle = deepcopy(self.source.provider_bundle)
        self.provider_bundle["identity_assertion_receipt"][
            "registry_public_key_base64"
        ] = _public_key_base64(self.registry_private_key)
        with self.source_verifiers():
            self.composition_document = composition_source.build_correlation_common_support_calendar_provider_composition_v1(
                self.source.derivation_receipt,
                self.source.matrix_replay,
                self.source.calendar_document,
                self.calendar_bundle,
                self.source.provider_document,
                self.provider_bundle,
            )
        self.composition_context = {
            "derivation_receipt": self.source.derivation_receipt,
            "matrix_replay": self.source.matrix_replay,
            "calendar_session_verification": self.source.calendar_document,
            "calendar_verification_bundle": self.calendar_bundle,
            "provider_identity_verification": self.source.provider_document,
            "provider_verification_bundle": self.provider_bundle,
        }
        self.registration = self.build_registration()
        self.receipt = self.build_receipt()

    @contextmanager
    def source_verifiers(self):
        with patch.object(
            calendar_source,
            "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1",
            return_value=True,
        ), patch.object(
            provider_source,
            "verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1",
            return_value=True,
        ):
            yield

    def build_registration(self, **overrides):
        values = {
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "provider_dataset_key_id": "DATASET-KEY-2026-01",
            "provider_dataset_public_key_base64": self.dataset_public_key_base64,
            "declared_at_utc": "2026-08-22T00:00:00Z",
            "valid_from_utc": "2026-08-22T00:00:00Z",
            "valid_until_utc": "2027-08-22T00:00:00Z",
        }
        values.update(overrides)
        with self.source_verifiers():
            return build_provider_dataset_content_attestation_registration_v1(
                **values
            )

    def build_receipt(
        self,
        *,
        registration=None,
        composition_document=None,
        private_key=None,
        issued_at_utc="2026-12-20T01:00:00Z",
    ):
        source_registration = registration or self.registration
        source_composition = composition_document or self.composition_document
        signing_key = private_key or self.dataset_private_key
        unsigned = build_unsigned_provider_dataset_content_attestation_v1(
            source_registration,
            source_composition,
            issued_at_utc=issued_at_utc,
        )
        signature = signing_key.sign(
            bytes.fromhex(unsigned["receipt_content_sha256"])
        )
        return assemble_provider_dataset_content_attestation_receipt_v1(
            unsigned,
            base64.b64encode(signature).decode("ascii"),
        )

    def evaluate(self, **overrides):
        values = {
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "registration": self.registration,
            "provider_dataset_public_key_base64": self.dataset_public_key_base64,
            "attestation_receipt": self.receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_attestation_hash": self.receipt["attestation_hash"],
        }
        values.update(overrides)
        with self.source_verifiers():
            return evaluate_provider_dataset_content_attestation_v1(**values)

    def verify(self, document, **overrides):
        values = {
            "composition_document": self.composition_document,
            "composition_context": self.composition_context,
            "registration": self.registration,
            "provider_dataset_public_key_base64": self.dataset_public_key_base64,
            "attestation_receipt": self.receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_attestation_hash": self.receipt["attestation_hash"],
        }
        values.update(overrides)
        with self.source_verifiers():
            return verify_provider_dataset_content_attestation_v1(
                document,
                **values,
            )

    def test_registration_binds_independent_key_role_without_authority(self) -> None:
        self.assertTrue(self.registration["facts"][
            "provider_dataset_key_role_separation_verified"
        ])
        self.assertFalse(self.registration["facts"][
            "external_provider_dataset_key_control_verified"
        ])
        self.assertFalse(self.registration["authority"][
            "provider_dataset_signing_allowed"
        ])
        self.assertEqual(self.registration["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_registration_verifier_accepts_exact_rebuild(self) -> None:
        with self.source_verifiers():
            self.assertTrue(verify_provider_dataset_content_attestation_registration_v1(
                self.registration,
                self.composition_document,
                self.composition_context,
                self.dataset_public_key_base64,
                expected_registration_hash=self.registration["registration_hash"],
            ))

    def test_registration_is_deterministic_and_redacts_public_key(self) -> None:
        self.assertEqual(self.registration, self.build_registration())
        self.assertNotIn(self.dataset_public_key_base64, repr(self.registration))

    def test_dataset_key_cannot_reuse_source_role_keys(self) -> None:
        source_keys = [
            self.provider_bundle["identity_assertion_receipt"][
                "registry_public_key_base64"
            ],
            self.calendar_bundle["batch_verification_context"][
                "signature_verification_context"
            ]["attestation_receipt"]["public_key_base64"],
        ]
        for public_key in source_keys:
            with self.subTest(public_key=public_key[:8]), self.assertRaisesRegex(
                ValueError,
                "key_role_collision",
            ):
                self.build_registration(
                    provider_dataset_public_key_base64=public_key
                )

    def test_source_role_keys_must_be_distinct(self) -> None:
        context = deepcopy(self.composition_context)
        registry_key = context["provider_verification_bundle"][
            "identity_assertion_receipt"
        ]["registry_public_key_base64"]
        context["calendar_verification_bundle"]["batch_verification_context"][
            "signature_verification_context"
        ]["attestation_receipt"]["public_key_base64"] = registry_key
        with self.assertRaisesRegex(ValueError, "source_role_public_key_collision"):
            self.build_registration(composition_context=context)

    def test_public_key_base64_and_length_are_strict(self) -> None:
        for invalid in ("not-base64", base64.b64encode(b"short").decode("ascii")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.build_registration(
                    provider_dataset_public_key_base64=invalid
                )

    def test_key_id_and_validity_window_are_strict(self) -> None:
        with self.assertRaisesRegex(ValueError, "key_id_invalid"):
            self.build_registration(provider_dataset_key_id="bad key")
        with self.assertRaisesRegex(ValueError, "validity_window_invalid"):
            self.build_registration(
                valid_from_utc="2027-08-22T00:00:00Z",
                valid_until_utc="2026-08-22T00:00:00Z",
            )

    def test_registration_expected_hash_is_required(self) -> None:
        with self.source_verifiers():
            self.assertFalse(verify_provider_dataset_content_attestation_registration_v1(
                self.registration,
                self.composition_document,
                self.composition_context,
                self.dataset_public_key_base64,
                expected_registration_hash="f" * 64,
            ))

    def test_unsigned_receipt_binds_complete_source_lineage(self) -> None:
        unsigned = build_unsigned_provider_dataset_content_attestation_v1(
            self.registration,
            self.composition_document,
            issued_at_utc="2026-12-20T01:00:00Z",
        )
        self.assertEqual(unsigned["composition_hash"], self.composition_document["composition_hash"])
        self.assertEqual(unsigned["dataset_count"], self.composition_document["dataset_count"])
        self.assertEqual(
            unsigned["dataset_provider_binding_hash"],
            self.composition_document["dataset_provider_binding_hash"],
        )

    def test_positive_signature_claim_remains_non_authoritative(self) -> None:
        result = self.evaluate()
        self.assertEqual(result["verification_state"], (
            "REGISTERED_PROVIDER_DATASET_KEY_SIGNATURE_VERIFIED_"
            "EXTERNAL_KEY_CONTROL_AND_DATA_ISSUANCE_TRUST_UNPROVEN"
        ))
        self.assertTrue(result["facts"]["provider_dataset_signature_verified"])
        self.assertTrue(result["facts"]["all_dataset_hashes_bound"])
        self.assertFalse(result["facts"]["external_provider_data_issuance_verified"])
        self.assertFalse(result["current_admission_allowed"])
        self.assertEqual(result["permissions"], {
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_output_verifier_accepts_exact_rebuild(self) -> None:
        result = self.evaluate()
        self.assertTrue(self.verify(result))

    def test_wrong_signing_key_is_rejected(self) -> None:
        receipt = self.build_receipt(private_key=Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "signature_invalid"):
            self.evaluate(
                attestation_receipt=receipt,
                expected_attestation_hash=receipt["attestation_hash"],
            )

    def test_signature_tamper_is_rejected(self) -> None:
        receipt = deepcopy(self.receipt)
        raw = bytearray(base64.b64decode(receipt["signature_base64"]))
        raw[0] ^= 1
        receipt["signature_base64"] = base64.b64encode(bytes(raw)).decode("ascii")
        with self.assertRaises(ValueError):
            self.evaluate(attestation_receipt=receipt)

    def test_signature_base64_is_strict(self) -> None:
        unsigned = build_unsigned_provider_dataset_content_attestation_v1(
            self.registration,
            self.composition_document,
            issued_at_utc="2026-12-20T01:00:00Z",
        )
        with self.assertRaisesRegex(ValueError, "signature_base64_invalid"):
            assemble_provider_dataset_content_attestation_receipt_v1(
                unsigned,
                "not-base64",
            )

    def test_receipt_source_binding_drift_is_rejected(self) -> None:
        receipt = deepcopy(self.receipt)
        receipt["dataset_provider_binding_hash"] = "f" * 64
        with self.assertRaises(ValueError):
            self.evaluate(attestation_receipt=receipt)

    def test_expected_attestation_hash_is_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "receipt_invalid"):
            self.evaluate(expected_attestation_hash="f" * 64)

    def test_issued_time_must_be_inside_registered_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "issued_time_invalid"):
            self.build_receipt(issued_at_utc="2028-01-01T00:00:00Z")

    def test_dataset_drift_invalidates_old_registration_and_receipt(self) -> None:
        replay = self.source.replay(data_hash_suffix="v2")
        derivation_receipt = build_correlation_common_support_derivation_receipt_v1(replay)
        with self.source_verifiers():
            alternate = composition_source.build_correlation_common_support_calendar_provider_composition_v1(
                derivation_receipt,
                replay,
                self.source.calendar_document,
                self.calendar_bundle,
                self.source.provider_document,
                self.provider_bundle,
            )
        context = deepcopy(self.composition_context)
        context["derivation_receipt"] = derivation_receipt
        context["matrix_replay"] = replay
        with self.assertRaisesRegex(ValueError, "registration_invalid"):
            self.evaluate(
                composition_document=alternate,
                composition_context=context,
            )

    def test_registration_authority_injection_is_rejected(self) -> None:
        registration = deepcopy(self.registration)
        registration["authority"]["provider_dataset_signing_allowed"] = True
        with self.assertRaisesRegex(ValueError, "registration_invalid"):
            self.evaluate(registration=registration)

    def test_output_redacts_key_and_signature_bytes(self) -> None:
        result = self.evaluate()
        rendered = repr(result)
        self.assertNotIn(self.dataset_public_key_base64, rendered)
        self.assertNotIn(self.receipt["signature_base64"], rendered)

    def test_coherently_resealed_output_drift_is_rejected(self) -> None:
        result = self.evaluate()
        result["dataset_count"] += 1
        self.assertFalse(self.verify(result))

    def test_evaluation_is_deterministic(self) -> None:
        self.assertEqual(self.evaluate(), self.evaluate())


if __name__ == "__main__":
    unittest.main()
