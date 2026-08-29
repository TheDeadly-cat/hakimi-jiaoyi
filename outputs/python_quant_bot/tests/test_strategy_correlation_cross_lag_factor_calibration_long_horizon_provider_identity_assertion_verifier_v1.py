from __future__ import annotations

import base64
import hashlib
import unittest
from copy import deepcopy
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
import exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as service_module
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 import (
    ASSERTION_RECEIPT_SCHEMA_VERSION,
    MERKLE_HASH_FORMAT,
    POSITIVE_STATE,
    RECEIPT_STATIC_FINGERPRINT,
    SCHEMA_VERSION,
    SIGNATURE_MESSAGE_FORMAT,
    STATIC_FINGERPRINT,
    VERIFIED_BLOCKERS,
    evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1 as registration_source_tests,
)


_UNSET = object()


def _leaf(document_sha256):
    return hashlib.sha256(b"\x00" + bytes.fromhex(document_sha256)).hexdigest()


def _parent(left_sha256, right_sha256):
    return hashlib.sha256(
        b"\x01" + bytes.fromhex(left_sha256) + bytes.fromhex(right_sha256)
    ).hexdigest()


def _all_keys(value):
    if type(value) is dict:
        found = set(value)
        for item in value.values():
            found.update(_all_keys(item))
        return found
    if type(value) is list:
        found = set()
        for item in value:
            found.update(_all_keys(item))
        return found
    return set()


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionVerifierV1Tests(
    unittest.TestCase
):
    def setUp(self):
        source_class = registration_source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAdapterRegistrationV1Tests
        self.source_case = source_class(
            methodName=next(name for name in dir(source_class) if name.startswith("test_"))
        )
        self.source_case.setUp()
        self.addCleanup(self.source_case.doCleanups)

        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        self.identity_registry_trust_root = hashlib.sha256(self.public_key).hexdigest()

        document_hashes = ["4" * 64, "5" * 64, "6" * 64, "7" * 64]
        leaves = [_leaf(value) for value in document_hashes]
        left_parent = _parent(leaves[0], leaves[1])
        right_parent = _parent(leaves[2], leaves[3])
        self.snapshot_root = _parent(left_parent, right_parent)
        self.membership_proof = [
            {"direction": "RIGHT", "sibling_sha256": leaves[1]},
            {"direction": "RIGHT", "sibling_sha256": right_parent},
        ]

        self.registration = self.source_case._build(
            identity_registry_snapshot_sha256=self.snapshot_root,
            identity_registry_trust_root_sha256=self.identity_registry_trust_root,
        )
        registration_values = dict(self.source_case.values)
        registration_values.update(
            {
                "expected_anchor_registration_hash": self.source_case.source[
                    "registration_hash"
                ],
                "identity_registry_snapshot_sha256": self.snapshot_root,
                "identity_registry_trust_root_sha256": (
                    self.identity_registry_trust_root
                ),
            }
        )
        self.registration_context = {
            "anchor_adapter_registration_v1": self.source_case.source,
            "anchor_registration_verification_context": (
                self.source_case.anchor_context
            ),
            "long_horizon_preregistration_v1": (
                self.source_case.source_case.preregistration
            ),
            "observation_protocol_v1": self.source_case.source_case.protocol,
            "provider_identity_registration_values": registration_values,
            "source_verification_context": self.source_case.source_case.context,
        }
        self.receipt = self._receipt()

    def _receipt(self, *, private_key=None, public_key=None, **overrides):
        private_key = self.private_key if private_key is None else private_key
        public_key = self.public_key if public_key is None else public_key
        payload = {
            "asserted_at_utc": "2026-09-17T00:00:00Z",
            "future_evaluation_id": self.registration["future_evaluation_id"],
            "identity_adapter_id": self.registration["identity_adapter_id"],
            "identity_assertion_id": "IDENTITY-ASSERTION-0001",
            "identity_registry_id": self.registration["identity_registry_id"],
            "identity_registry_snapshot_id": self.registration[
                "identity_registry_snapshot_id"
            ],
            "identity_registry_snapshot_sha256": self.registration[
                "identity_registry_snapshot_sha256"
            ],
            "identity_registry_trust_root_sha256": self.registration[
                "identity_registry_trust_root_sha256"
            ],
            "membership_leaf_index": 0,
            "membership_proof": deepcopy(self.membership_proof),
            "membership_tree_size": 4,
            "merkle_hash_format": MERKLE_HASH_FORMAT,
            "provider_id": self.registration["provider_id"],
            "provider_identity_document_sha256": self.registration[
                "provider_identity_document_sha256"
            ],
            "provider_identity_registration_hash": self.registration[
                "registration_hash"
            ],
            "provider_receipt_trust_root_sha256": self.registration[
                "provider_receipt_trust_root_sha256"
            ],
            "provider_subject_id": self.registration["provider_subject_id"],
            "receipt_encoding": self.registration[
                "identity_attestation_receipt_encoding"
            ],
            "schema_version": ASSERTION_RECEIPT_SCHEMA_VERSION,
            "signature_algorithm": self.registration[
                "identity_attestation_signature_algorithm"
            ],
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "static_fingerprint": RECEIPT_STATIC_FINGERPRINT,
            "valid_until_utc": "2026-10-31T23:59:59Z",
        }
        payload.update(overrides)
        content_hash = strict_canonical_hash(payload)
        signature = private_key.sign(bytes.fromhex(content_hash))
        receipt = {
            **payload,
            "assertion_content_sha256": content_hash,
            "registry_public_key_base64": base64.b64encode(public_key).decode(
                "ascii"
            ),
            "registry_signature_base64": base64.b64encode(signature).decode(
                "ascii"
            ),
            "registry_signature_sha256": hashlib.sha256(signature).hexdigest(),
        }
        return seal_strict_canonical_document(receipt, "assertion_hash")

    def _build(
        self,
        *,
        registration=_UNSET,
        context=_UNSET,
        receipt=_UNSET,
        expected_registration_hash=_UNSET,
        expected_assertion_hash=_UNSET,
    ):
        registration = self.registration if registration is _UNSET else registration
        context = self.registration_context if context is _UNSET else context
        receipt = self.receipt if receipt is _UNSET else receipt
        expected_registration_hash = (
            registration.get("registration_hash")
            if expected_registration_hash is _UNSET and type(registration) is dict
            else expected_registration_hash
        )
        expected_assertion_hash = (
            receipt.get("assertion_hash")
            if expected_assertion_hash is _UNSET and type(receipt) is dict
            else expected_assertion_hash
        )
        return evaluate_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
            registration,
            context,
            receipt,
            expected_provider_identity_registration_hash=(
                expected_registration_hash
            ),
            expected_identity_assertion_hash=expected_assertion_hash,
        )

    def _verify(self, document):
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1(
            document,
            self.registration,
            self.registration_context,
            self.receipt,
            expected_provider_identity_registration_hash=self.registration[
                "registration_hash"
            ],
            expected_identity_assertion_hash=self.receipt["assertion_hash"],
        )

    def test_signature_and_snapshot_membership_verify_without_external_identity(self):
        document = self._build()
        self.assertEqual(
            document["identity_assertion_verification_state"], POSITIVE_STATE
        )
        self.assertEqual(document["blockers"], list(VERIFIED_BLOCKERS))
        self.assertTrue(document["facts"]["identity_registry_signature_verified"])
        self.assertTrue(document["facts"]["snapshot_membership_verified"])
        self.assertFalse(document["facts"]["provider_identity_verified"])
        self.assertTrue(self._verify(document))

    def test_expected_hashes_are_fail_closed(self):
        invalid_registration = self._build(expected_registration_hash="invalid")
        invalid_assertion = self._build(expected_assertion_hash="invalid")
        wrong_registration = self._build(expected_registration_hash="0" * 64)
        wrong_assertion = self._build(expected_assertion_hash="0" * 64)
        self.assertEqual(
            invalid_registration["blockers"],
            ["EXPECTED_PROVIDER_IDENTITY_REGISTRATION_HASH_INVALID"],
        )
        self.assertEqual(
            invalid_assertion["blockers"],
            ["EXPECTED_IDENTITY_ASSERTION_HASH_INVALID"],
        )
        self.assertEqual(
            wrong_registration["blockers"],
            ["SOURCE_PROVIDER_IDENTITY_REGISTRATION_HASH_MISMATCH"],
        )
        self.assertEqual(
            wrong_assertion["blockers"], ["IDENTITY_ASSERTION_HASH_MISMATCH"]
        )

    def test_registration_context_and_values_require_exact_fields(self):
        missing = deepcopy(self.registration_context)
        missing.pop("source_verification_context")
        extra = deepcopy(self.registration_context)
        extra["ready"] = True
        values_missing = deepcopy(self.registration_context)
        values_missing["provider_identity_registration_values"].pop(
            "provider_subject_id"
        )
        values_extra = deepcopy(self.registration_context)
        values_extra["provider_identity_registration_values"]["ready"] = True
        for context in (missing, extra, None):
            self.assertEqual(
                self._build(context=context)["blockers"],
                ["PROVIDER_IDENTITY_REGISTRATION_VERIFICATION_CONTEXT_INVALID"],
            )
        for context in (values_missing, values_extra):
            self.assertEqual(
                self._build(context=context)["blockers"],
                ["PROVIDER_IDENTITY_REGISTRATION_VALUES_INVALID"],
            )

    def test_registration_is_reverified_not_trusted_by_label(self):
        tampered = deepcopy(self.registration)
        tampered["provider_subject_id"] = "FORGED-SUBJECT"
        tampered = seal_strict_canonical_document(
            {key: value for key, value in tampered.items() if key != "registration_hash"},
            "registration_hash",
        )
        document = self._build(
            registration=tampered,
            expected_registration_hash=tampered["registration_hash"],
        )
        self.assertEqual(
            document["blockers"],
            ["SOURCE_PROVIDER_IDENTITY_REGISTRATION_NOT_VERIFIED"],
        )

    def test_receipt_requires_exact_fields_and_seal(self):
        missing = deepcopy(self.receipt)
        missing.pop("membership_proof")
        extra = deepcopy(self.receipt)
        extra["ready"] = True
        tampered = deepcopy(self.receipt)
        tampered["asserted_at_utc"] = "2026-09-18T00:00:00Z"
        self.assertEqual(
            self._build(receipt=missing)["blockers"],
            ["IDENTITY_ASSERTION_RECEIPT_FIELDS_INVALID"],
        )
        self.assertEqual(
            self._build(receipt=extra)["blockers"],
            ["IDENTITY_ASSERTION_RECEIPT_FIELDS_INVALID"],
        )
        self.assertEqual(
            self._build(receipt=tampered)["blockers"],
            ["IDENTITY_ASSERTION_RECEIPT_SEAL_INVALID"],
        )

    def test_source_binding_tamper_is_rejected_even_when_resigned(self):
        for key, value in (
            ("provider_id", "OTHER-PROVIDER"),
            ("provider_subject_id", "OTHER-SUBJECT"),
            ("identity_registry_snapshot_id", "OTHER-SNAPSHOT"),
            ("provider_identity_registration_hash", "0" * 64),
        ):
            receipt = self._receipt(**{key: value})
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_SOURCE_BINDINGS_INVALID"],
            )

    def test_assertion_id_is_strict(self):
        receipt = self._receipt(identity_assertion_id="bad assertion")
        self.assertEqual(
            self._build(receipt=receipt)["blockers"],
            ["IDENTITY_ASSERTION_ID_INVALID"],
        )

    def test_chronology_is_strict_and_valid_at_evaluation(self):
        cases = (
            {"asserted_at_utc": "2026-09-15T23:59:59Z"},
            {"asserted_at_utc": "2026-10-01T00:00:00Z"},
            {"valid_until_utc": "2026-09-30T23:59:59Z"},
            {"valid_until_utc": "2026-09-16T23:59:59Z"},
        )
        for overrides in cases:
            receipt = self._receipt(**overrides)
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_CHRONOLOGY_INVALID"],
            )
        malformed = self._receipt(asserted_at_utc="2026-09-17T00:00:00+00:00")
        self.assertEqual(
            self._build(receipt=malformed)["blockers"],
            ["IDENTITY_ASSERTION_TIME_FIELDS_INVALID"],
        )

    def test_merkle_tree_shape_is_strict(self):
        cases = (
            {"membership_tree_size": 3},
            {"membership_tree_size": 0},
            {"membership_leaf_index": 4},
            {"membership_leaf_index": True},
            {"membership_proof": self.membership_proof[:1]},
        )
        for overrides in cases:
            receipt = self._receipt(**overrides)
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_MERKLE_TREE_SHAPE_INVALID"],
            )

    def test_merkle_direction_and_sibling_hash_are_strict(self):
        direction = deepcopy(self.membership_proof)
        direction[0]["direction"] = "LEFT"
        sibling = deepcopy(self.membership_proof)
        sibling[0]["sibling_sha256"] = "A" * 64
        extra = deepcopy(self.membership_proof)
        extra[0]["ready"] = True
        for proof in (direction, sibling, extra):
            receipt = self._receipt(membership_proof=proof)
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_MERKLE_PROOF_INVALID"],
            )

    def test_snapshot_membership_tamper_is_rejected_after_valid_signature(self):
        proof = deepcopy(self.membership_proof)
        proof[1]["sibling_sha256"] = "8" * 64
        receipt = self._receipt(membership_proof=proof)
        document = self._build(receipt=receipt)
        self.assertEqual(
            document["blockers"],
            ["IDENTITY_ASSERTION_SNAPSHOT_MEMBERSHIP_INVALID"],
        )
        self.assertTrue(document["facts"]["identity_registry_signature_verified"])
        self.assertFalse(document["facts"]["snapshot_membership_verified"])

    def test_receipt_identity_is_exact(self):
        cases = (
            {"schema_version": "legacy"},
            {"static_fingerprint": "legacy"},
            {"signature_algorithm": "RSA"},
            {"receipt_encoding": "PROVIDER_OPAQUE_BYTES"},
            {"signature_message_format": "RAW"},
            {"merkle_hash_format": "PLAIN_SHA256"},
        )
        for overrides in cases:
            receipt = self._receipt(**overrides)
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_RECEIPT_IDENTITY_INVALID"],
            )

    def test_content_hash_tamper_is_rejected(self):
        receipt = deepcopy(self.receipt)
        receipt["assertion_content_sha256"] = "0" * 64
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "assertion_hash"},
            "assertion_hash",
        )
        self.assertEqual(
            self._build(receipt=receipt)["blockers"],
            ["IDENTITY_ASSERTION_CONTENT_HASH_MISMATCH"],
        )

    def test_registry_public_key_substitution_is_rejected(self):
        wrong_private = Ed25519PrivateKey.generate()
        wrong_public = wrong_private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        receipt = self._receipt(private_key=wrong_private, public_key=wrong_public)
        self.assertEqual(
            self._build(receipt=receipt)["blockers"],
            ["IDENTITY_REGISTRY_PUBLIC_KEY_MISMATCH"],
        )

    def test_signature_tamper_is_rejected(self):
        receipt = deepcopy(self.receipt)
        signature = bytearray(base64.b64decode(receipt["registry_signature_base64"]))
        signature[0] ^= 1
        receipt["registry_signature_base64"] = base64.b64encode(signature).decode(
            "ascii"
        )
        receipt["registry_signature_sha256"] = hashlib.sha256(signature).hexdigest()
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "assertion_hash"},
            "assertion_hash",
        )
        self.assertEqual(
            self._build(receipt=receipt)["blockers"],
            ["IDENTITY_ASSERTION_SIGNATURE_INVALID"],
        )

    def test_signature_hash_mismatch_is_rejected(self):
        receipt = deepcopy(self.receipt)
        receipt["registry_signature_sha256"] = "0" * 64
        receipt = seal_strict_canonical_document(
            {key: value for key, value in receipt.items() if key != "assertion_hash"},
            "assertion_hash",
        )
        self.assertEqual(
            self._build(receipt=receipt)["blockers"],
            ["IDENTITY_ASSERTION_SIGNATURE_HASH_MISMATCH"],
        )

    def test_crypto_base64_grammar_and_lengths_are_strict(self):
        for key, value in (
            ("registry_public_key_base64", "not-base64"),
            ("registry_public_key_base64", base64.b64encode(b"short").decode("ascii")),
            ("registry_signature_base64", base64.b64encode(b"short").decode("ascii")),
        ):
            receipt = deepcopy(self.receipt)
            receipt[key] = value
            receipt = seal_strict_canonical_document(
                {k: v for k, v in receipt.items() if k != "assertion_hash"},
                "assertion_hash",
            )
            self.assertEqual(
                self._build(receipt=receipt)["blockers"],
                ["IDENTITY_ASSERTION_CRYPTO_ENCODING_INVALID"],
            )

    def test_dependency_absence_is_fail_closed(self):
        with patch.object(service_module, "Ed25519PublicKey", None):
            document = self._build()
        self.assertEqual(
            document["blockers"], ["CRYPTOGRAPHY_DEPENDENCY_UNAVAILABLE"]
        )

    def test_public_output_redacts_key_signature_and_proof_siblings(self):
        document = self._build()
        forbidden = {
            "membership_proof",
            "registry_public_key_base64",
            "registry_signature_base64",
            "sibling_sha256",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))
        self.assertEqual(document["membership_proof_count"], 2)
        self.assertEqual(
            document["membership_proof_hash"],
            strict_canonical_hash(self.membership_proof),
        )

    def test_authority_and_external_truth_remain_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key in (
            "evaluation_activated",
            "external_identity_registry_authenticity_proven",
            "external_registration_time_verified",
            "provider_identity_verified",
            "replay_registry_checked",
            "result_available",
        ):
            self.assertFalse(document["facts"][key], key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["verification_hash"], second["verification_hash"])

    def test_verifier_rejects_tamper_extra_fields_and_non_objects(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["identity_assertion_verification_state"] = "IDENTITY_VERIFIED"
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_and_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["signature_message_format"], SIGNATURE_MESSAGE_FORMAT)
        self.assertEqual(document["merkle_hash_format"], MERKLE_HASH_FORMAT)
        self.assertEqual(
            set(document),
            {
                "asserted_at_utc",
                "assertion_content_sha256",
                "assertion_hash",
                "assertion_id",
                "authority",
                "blockers",
                "facts",
                "future_evaluation_id",
                "identity_adapter_id",
                "identity_assertion_verification_state",
                "identity_registry_id",
                "identity_registry_snapshot_id",
                "identity_registry_snapshot_sha256",
                "identity_registry_trust_root_sha256",
                "membership_leaf_index",
                "membership_proof_count",
                "membership_proof_hash",
                "membership_tree_size",
                "merkle_hash_format",
                "provider_id",
                "provider_identity_document_sha256",
                "provider_receipt_trust_root_sha256",
                "provider_subject_id",
                "receipt_encoding",
                "registry_signature_sha256",
                "schema_version",
                "signature_algorithm",
                "signature_message_format",
                "source_provider_identity_registration_hash",
                "source_provider_identity_registration_schema",
                "source_state",
                "static_fingerprint",
                "valid_until_utc",
                "verification_hash",
                "verification_reason",
            },
        )


if __name__ == "__main__":
    unittest.main()
