import base64
import hashlib
import unittest
from copy import deepcopy
from decimal import getcontext, setcontext
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1 as service_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1 import (
    POSITIVE_STATE,
    RECEIPT_STATIC_FINGERPRINT,
    SCHEMA_VERSION,
    SIGNATURE_MESSAGE_FORMAT,
    STATIC_FINGERPRINT,
    evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    EXTERNAL_ATTESTATION_SCHEMA,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1 as source_tests,
)


_DEFAULT = object()


def _all_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_all_keys(child))
        return keys
    if isinstance(value, list):
        keys = set()
        for child in value:
            keys.update(_all_keys(child))
        return keys
    return set()


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterSignatureVerifierV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterRegistrationV1Tests(
                methodName="test_valid_values_are_declared_but_not_time_attested"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.trust_root_sha256 = hashlib.sha256(self.public_key).hexdigest()
        self.registration_context = self.case._kwargs(
            trust_root_sha256=self.trust_root_sha256
        )
        self.registration = self.case._build(
            trust_root_sha256=self.trust_root_sha256
        )
        self.protocol = self.case.protocol
        self.preregistration = self.case.preregistration
        self.source_context = self.case.context
        self.receipt = self._receipt()

    def _receipt(self, private_key=None, public_key=None, **overrides):
        private_key = self.private_key if private_key is None else private_key
        public_key = self.public_key if public_key is None else public_key
        payload = {
            "adapter_id": self.registration["adapter_id"],
            "adapter_static_fingerprint": self.registration[
                "adapter_static_fingerprint"
            ],
            "batch_first_observation_date": "2026-10-01",
            "batch_last_observation_date": "2026-10-20",
            "future_evaluation_id": self.registration["future_evaluation_id"],
            "observation_batch_hash": "d" * 64,
            "provider_id": self.registration["provider_id"],
            "provider_receipt_id": "RECEIPT-0001",
            "provider_timestamp_utc": "2026-10-21T00:00:00Z",
            "receipt_encoding": self.registration["receipt_encoding"],
            "registration_hash": self.registration["registration_hash"],
            "schema_version": EXTERNAL_ATTESTATION_SCHEMA,
            "signature_algorithm": "ED25519",
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "source_external_time_anchor_reference_hash": self.registration[
                "source_external_time_anchor_reference_hash"
            ],
            "static_fingerprint": RECEIPT_STATIC_FINGERPRINT,
            "trust_root_sha256": self.registration["trust_root_sha256"],
        }
        payload.update(overrides)
        content_hash = strict_canonical_hash(payload)
        signature = private_key.sign(bytes.fromhex(content_hash))
        receipt = {
            **payload,
            "public_key_base64": base64.b64encode(public_key).decode("ascii"),
            "receipt_content_sha256": content_hash,
            "signature_base64": base64.b64encode(signature).decode("ascii"),
            "signature_sha256": hashlib.sha256(signature).hexdigest(),
        }
        return seal_strict_canonical_document(receipt, "attestation_hash")

    def _build(
        self,
        registration=_DEFAULT,
        protocol=_DEFAULT,
        preregistration=_DEFAULT,
        source_context=_DEFAULT,
        registration_context=_DEFAULT,
        receipt=_DEFAULT,
        expected_registration_hash=_DEFAULT,
        expected_attestation_hash=_DEFAULT,
    ):
        registration = self.registration if registration is _DEFAULT else registration
        protocol = self.protocol if protocol is _DEFAULT else protocol
        preregistration = (
            self.preregistration
            if preregistration is _DEFAULT
            else preregistration
        )
        source_context = (
            self.source_context if source_context is _DEFAULT else source_context
        )
        registration_context = (
            self.registration_context
            if registration_context is _DEFAULT
            else registration_context
        )
        receipt = self.receipt if receipt is _DEFAULT else receipt
        expected_registration_hash = (
            self.registration["registration_hash"]
            if expected_registration_hash is _DEFAULT
            else expected_registration_hash
        )
        expected_attestation_hash = (
            self.receipt["attestation_hash"]
            if expected_attestation_hash is _DEFAULT
            else expected_attestation_hash
        )
        return evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
            registration,
            protocol,
            preregistration,
            source_context,
            registration_context,
            receipt,
            expected_registration_hash=expected_registration_hash,
            expected_attestation_hash=expected_attestation_hash,
        )

    def _verify(self, document, **overrides):
        values = {
            "registration": self.registration,
            "protocol": self.protocol,
            "preregistration": self.preregistration,
            "source_context": self.source_context,
            "registration_context": self.registration_context,
            "receipt": self.receipt,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_attestation_hash": self.receipt["attestation_hash"],
        }
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_signature_verifier_v1(
            document,
            values["registration"],
            values["protocol"],
            values["preregistration"],
            values["source_context"],
            values["registration_context"],
            values["receipt"],
            expected_registration_hash=values["expected_registration_hash"],
            expected_attestation_hash=values["expected_attestation_hash"],
        )

    def test_valid_signature_is_verified_but_not_admitted(self):
        document = self._build()
        self.assertEqual(document["verification_state"], POSITIVE_STATE)
        self.assertTrue(document["facts"]["receipt_signature_verified"])
        self.assertTrue(document["facts"]["provider_key_possession_verified"])
        self.assertFalse(document["facts"]["provider_identity_verified"])
        self.assertFalse(document["facts"]["observation_admitted"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["signature_message_format"], SIGNATURE_MESSAGE_FORMAT)

    def test_all_source_hashes_are_bound(self):
        document = self._build()
        self.assertEqual(
            document["source_registration_hash"],
            self.registration["registration_hash"],
        )
        self.assertEqual(document["attestation_hash"], self.receipt["attestation_hash"])
        self.assertEqual(
            document["observation_batch_hash"], self.receipt["observation_batch_hash"]
        )

    def test_receipt_content_hash_is_exact(self):
        document = self._build()
        signed_payload = {
            key: value
            for key, value in self.receipt.items()
            if key
            not in {
                "attestation_hash",
                "public_key_base64",
                "receipt_content_sha256",
                "signature_base64",
                "signature_sha256",
            }
        }
        self.assertEqual(
            document["receipt_content_sha256"], strict_canonical_hash(signed_payload)
        )

    def test_message_tamper_with_resealed_receipt_is_rejected(self):
        receipt = deepcopy(self.receipt)
        receipt["observation_batch_hash"] = "e" * 64
        signed_payload = {
            key: value
            for key, value in receipt.items()
            if key
            not in {
                "attestation_hash",
                "public_key_base64",
                "receipt_content_sha256",
                "signature_base64",
                "signature_sha256",
            }
        }
        receipt["receipt_content_sha256"] = strict_canonical_hash(signed_payload)
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "attestation_hash"},
            "attestation_hash",
        )
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["verification_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["ATTESTATION_SIGNATURE_INVALID"])

    def test_signature_tamper_is_rejected(self):
        receipt = deepcopy(self.receipt)
        signature = bytearray(base64.b64decode(receipt["signature_base64"]))
        signature[0] ^= 1
        receipt["signature_base64"] = base64.b64encode(signature).decode("ascii")
        receipt["signature_sha256"] = hashlib.sha256(signature).hexdigest()
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "attestation_hash"},
            "attestation_hash",
        )
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["ATTESTATION_SIGNATURE_INVALID"])

    def test_public_key_substitution_is_rejected(self):
        wrong = Ed25519PrivateKey.generate()
        wrong_public = wrong.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        receipt = self._receipt(private_key=wrong, public_key=wrong_public)
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["PUBLIC_KEY_TRUST_ROOT_MISMATCH"])

    def test_signature_hash_mismatch_is_rejected(self):
        receipt = deepcopy(self.receipt)
        receipt["signature_sha256"] = "0" * 64
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "attestation_hash"},
            "attestation_hash",
        )
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["SIGNATURE_HASH_INVALID"])

    def test_base64_grammar_and_lengths_are_strict(self):
        for key, value in (
            ("public_key_base64", "not-base64"),
            ("public_key_base64", base64.b64encode(b"short").decode("ascii")),
            ("signature_base64", base64.b64encode(b"short").decode("ascii")),
        ):
            receipt = deepcopy(self.receipt)
            receipt[key] = value
            receipt = seal_strict_canonical_document(
                {k: v for k, v in receipt.items() if k != "attestation_hash"},
                "attestation_hash",
            )
            document = self._build(
                receipt=receipt,
                expected_attestation_hash=receipt["attestation_hash"],
            )
            self.assertEqual(
                document["blockers"], ["ATTESTATION_CRYPTO_ENCODING_INVALID"]
            )

    def test_dependency_absence_is_fail_closed(self):
        with patch.object(service_module, "Ed25519PublicKey", None):
            document = self._build()
        self.assertEqual(document["verification_state"], "UNKNOWN")
        self.assertEqual(document["blockers"], ["CRYPTOGRAPHY_DEPENDENCY_UNAVAILABLE"])

    def test_registered_algorithm_downgrade_is_rejected(self):
        context = self.case._kwargs(
            trust_root_sha256=self.trust_root_sha256,
            signature_algorithm="ECDSA_P256_SHA256",
        )
        registration = self.case._build(
            trust_root_sha256=self.trust_root_sha256,
            signature_algorithm="ECDSA_P256_SHA256",
        )
        receipt = self._receipt(signature_algorithm="ECDSA_P256_SHA256")
        document = self._build(
            registration=registration,
            registration_context=context,
            receipt=receipt,
            expected_registration_hash=registration["registration_hash"],
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(
            document["blockers"], ["REGISTERED_ALGORITHM_NOT_SUPPORTED_BY_ADAPTER"]
        )

    def test_source_binding_tamper_is_rejected(self):
        for key, value in (
            ("provider_id", "OTHER-PROVIDER"),
            ("adapter_id", "OTHER-ADAPTER"),
            ("registration_hash", "0" * 64),
            ("future_evaluation_id", "OTHER-EVALUATION"),
        ):
            receipt = self._receipt(**{key: value})
            document = self._build(
                receipt=receipt,
                expected_attestation_hash=receipt["attestation_hash"],
            )
            self.assertEqual(document["blockers"], ["ATTESTATION_SOURCE_BINDINGS_INVALID"])

    def test_observation_batch_hash_is_strict(self):
        receipt = self._receipt(observation_batch_hash="D" * 64)
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["OBSERVATION_BATCH_HASH_INVALID"])

    def test_first_observation_must_not_precede_evaluation_date(self):
        receipt = self._receipt(batch_first_observation_date="2026-09-30")
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["OBSERVATION_DATE_WINDOW_INVALID"])

    def test_observation_dates_must_be_ordered(self):
        receipt = self._receipt(
            batch_first_observation_date="2026-10-20",
            batch_last_observation_date="2026-10-19",
        )
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["OBSERVATION_DATE_WINDOW_INVALID"])

    def test_provider_timestamp_must_follow_last_observation(self):
        receipt = self._receipt(provider_timestamp_utc="2026-10-19T23:59:59Z")
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["PROVIDER_TIMESTAMP_ORDER_INVALID"])

    def test_time_grammar_is_strict(self):
        for key, value in (
            ("batch_first_observation_date", "2026-10-01T00:00:00Z"),
            ("batch_last_observation_date", "not-a-date"),
            ("provider_timestamp_utc", "2026-10-21T00:00:00+00:00"),
        ):
            receipt = self._receipt(**{key: value})
            document = self._build(
                receipt=receipt,
                expected_attestation_hash=receipt["attestation_hash"],
            )
            self.assertEqual(document["blockers"], ["ATTESTATION_TIME_FIELDS_INVALID"])

    def test_provider_receipt_id_is_strict(self):
        receipt = self._receipt(provider_receipt_id="bad receipt")
        document = self._build(
            receipt=receipt,
            expected_attestation_hash=receipt["attestation_hash"],
        )
        self.assertEqual(document["blockers"], ["PROVIDER_RECEIPT_ID_INVALID"])

    def test_expected_hashes_are_bound(self):
        wrong_registration = self._build(expected_registration_hash="0" * 64)
        wrong_attestation = self._build(expected_attestation_hash="0" * 64)
        self.assertEqual(
            wrong_registration["blockers"], ["SOURCE_REGISTRATION_HASH_MISMATCH"]
        )
        self.assertEqual(wrong_attestation["blockers"], ["ATTESTATION_HASH_MISMATCH"])

    def test_registration_context_requires_exact_fields(self):
        missing = deepcopy(self.registration_context)
        missing.pop("trust_root_sha256")
        extra = deepcopy(self.registration_context)
        extra["authority"] = "forged"
        for context in (missing, extra):
            document = self._build(registration_context=context)
            self.assertEqual(
                document["blockers"], ["REGISTRATION_VERIFICATION_CONTEXT_INVALID"]
            )

    def test_resealed_registration_tamper_is_rejected(self):
        registration = deepcopy(self.registration)
        registration["provider_id"] = "OTHER-PROVIDER"
        registration = seal_strict_canonical_document(
            {
                key: value
                for key, value in registration.items()
                if key != "registration_hash"
            },
            "registration_hash",
        )
        document = self._build(
            registration=registration,
            expected_registration_hash=registration["registration_hash"],
        )
        self.assertEqual(document["blockers"], ["SOURCE_REGISTRATION_NOT_VERIFIED"])

    def test_output_redacts_public_key_and_signature_bytes(self):
        document = self._build()
        self.assertTrue(
            {
                "public_key_base64",
                "signature_base64",
                "external_attestation",
                "observation_batch",
                "rows",
                "returns",
                "result",
                "results",
            }.isdisjoint(_all_keys(document))
        )

    def test_authority_and_unproven_facts_remain_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key in (
            "batch_content_verified",
            "external_authenticity_proven",
            "external_registration_time_verified",
            "observation_admitted",
            "provider_identity_verified",
            "replay_registry_checked",
            "result_available",
        ):
            self.assertFalse(document["facts"][key], key)

    def test_build_is_deterministic_for_same_receipt(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["verification_hash"], second["verification_hash"])

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["verification_state"] = "VERIFIED_EXTERNAL_ATTESTATION"
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(
            set(document),
            {
                "adapter_id",
                "adapter_static_fingerprint",
                "attestation_hash",
                "authority",
                "batch_first_observation_date",
                "batch_last_observation_date",
                "blockers",
                "facts",
                "future_evaluation_id",
                "observation_batch_hash",
                "provider_id",
                "provider_receipt_id",
                "provider_timestamp_utc",
                "receipt_content_sha256",
                "receipt_schema_version",
                "schema_version",
                "signature_message_format",
                "signature_sha256",
                "source_external_time_anchor_reference_hash",
                "source_registration_hash",
                "source_registration_schema",
                "source_state",
                "static_fingerprint",
                "trust_root_sha256",
                "verification_hash",
                "verification_state",
            },
        )


if __name__ == "__main__":
    unittest.main()
