from __future__ import annotations

import unittest
from copy import deepcopy

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1 import (
    IDENTITY_ATTESTATION_RECEIPT_ENCODING,
    IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM,
    REGISTRATION_BLOCKERS,
    REGISTRATION_PROTOCOL_ID,
    REGISTRATION_STATE,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1 as anchor_registration_source_tests,
)


_UNSET = object()


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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAdapterRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self):
        source_class = anchor_registration_source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterRegistrationV1Tests
        self.source_case = source_class(
            methodName=next(name for name in dir(source_class) if name.startswith("test_"))
        )
        self.source_case.setUp()
        self.addCleanup(self.source_case.doCleanups)
        self.source = self.source_case._build()
        self.anchor_context = self.source_case._kwargs()
        self.values = {
            "declared_at_utc": "2026-09-16T00:00:00Z",
            "identity_adapter_id": "PROVIDER-IDENTITY-ADAPTER-1",
            "identity_adapter_implementation_sha256": "1" * 64,
            "identity_adapter_static_fingerprint": (
                "20260923-provider-identity-adapter-1"
            ),
            "identity_attestation_receipt_encoding": (
                IDENTITY_ATTESTATION_RECEIPT_ENCODING
            ),
            "identity_attestation_signature_algorithm": (
                IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM
            ),
            "identity_registry_id": "EXTERNAL-IDENTITY-REGISTRY-1",
            "identity_registry_snapshot_id": "SNAPSHOT-20260915-1",
            "identity_registry_snapshot_sha256": "2" * 64,
            "identity_registry_trust_root_sha256": "3" * 64,
            "provider_identity_document_sha256": "4" * 64,
            "provider_subject_id": "PROVIDER-SUBJECT-1",
        }

    def _build(
        self,
        *,
        source=_UNSET,
        anchor_context=_UNSET,
        expected_hash=_UNSET,
        **overrides,
    ):
        source = self.source if source is _UNSET else source
        values = dict(self.values)
        values.update(overrides)
        expected_hash = (
            source.get("registration_hash")
            if expected_hash is _UNSET and type(source) is dict
            else expected_hash
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
            source,
            self.source_case.protocol,
            self.source_case.preregistration,
            self.source_case.context,
            self.anchor_context if anchor_context is _UNSET else anchor_context,
            expected_anchor_registration_hash=expected_hash,
            **values,
        )

    def _verify(self, document):
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_adapter_registration_v1(
            document,
            self.source,
            self.source_case.protocol,
            self.source_case.preregistration,
            self.source_case.context,
            self.anchor_context,
            expected_anchor_registration_hash=self.source["registration_hash"],
            **self.values,
        )

    def test_registration_pins_identity_adapter_without_proving_identity(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(document["registration_state"], REGISTRATION_STATE)
        self.assertEqual(document["blockers"], list(REGISTRATION_BLOCKERS))
        self.assertTrue(document["facts"]["identity_adapter_values_pinned"])
        self.assertTrue(
            document["facts"]["identity_trust_root_role_separated"]
        )
        self.assertFalse(document["facts"]["provider_identity_verified"])
        self.assertTrue(self._verify(document))

    def test_value_binding_hash_covers_source_and_identity_roles(self):
        document = self._build()
        binding = {
            "declared_at_utc": self.values["declared_at_utc"],
            "future_evaluation_id": self.source["future_evaluation_id"],
            "identity_adapter_id": self.values["identity_adapter_id"],
            "identity_adapter_implementation_sha256": self.values[
                "identity_adapter_implementation_sha256"
            ],
            "identity_adapter_static_fingerprint": self.values[
                "identity_adapter_static_fingerprint"
            ],
            "identity_attestation_receipt_encoding": self.values[
                "identity_attestation_receipt_encoding"
            ],
            "identity_attestation_signature_algorithm": self.values[
                "identity_attestation_signature_algorithm"
            ],
            "identity_registry_id": self.values["identity_registry_id"],
            "identity_registry_snapshot_id": self.values[
                "identity_registry_snapshot_id"
            ],
            "identity_registry_snapshot_sha256": self.values[
                "identity_registry_snapshot_sha256"
            ],
            "identity_registry_trust_root_sha256": self.values[
                "identity_registry_trust_root_sha256"
            ],
            "provider_id": self.source["provider_id"],
            "provider_identity_document_sha256": self.values[
                "provider_identity_document_sha256"
            ],
            "provider_receipt_trust_root_sha256": self.source[
                "trust_root_sha256"
            ],
            "provider_subject_id": self.values["provider_subject_id"],
            "registration_protocol_id": REGISTRATION_PROTOCOL_ID,
            "source_anchor_adapter_registration_hash": self.source[
                "registration_hash"
            ],
            "source_observation_protocol_hash": self.source[
                "source_observation_protocol_hash"
            ],
            "source_preregistration_hash": self.source[
                "source_preregistration_hash"
            ],
        }
        self.assertEqual(
            document["identity_adapter_value_binding_hash"],
            strict_canonical_hash(binding),
        )

    def test_provider_receipt_and_identity_registry_trust_roots_must_differ(self):
        document = self._build(
            identity_registry_trust_root_sha256=self.source["trust_root_sha256"]
        )
        self.assertEqual(
            document["blockers"], ["IDENTITY_TRUST_ROOT_ROLE_COLLISION"]
        )

    def test_expected_source_hash_is_fail_closed(self):
        invalid = self._build(expected_hash="invalid")
        mismatch = self._build(expected_hash="0" * 64)
        self.assertEqual(
            invalid["blockers"], ["EXPECTED_ANCHOR_REGISTRATION_HASH_INVALID"]
        )
        self.assertEqual(
            mismatch["blockers"], ["SOURCE_ANCHOR_REGISTRATION_HASH_MISMATCH"]
        )

    def test_anchor_context_requires_exact_fields(self):
        missing = deepcopy(self.anchor_context)
        missing.pop("provider_id")
        extra = deepcopy(self.anchor_context)
        extra["ready"] = True
        for context in (missing, extra, None):
            document = self._build(anchor_context=context)
            self.assertEqual(
                document["blockers"],
                ["ANCHOR_REGISTRATION_VERIFICATION_CONTEXT_INVALID"],
            )

    def test_resealed_source_tamper_is_reverified(self):
        tampered = deepcopy(self.source)
        tampered["provider_id"] = "OTHER-PROVIDER"
        tampered = seal_strict_canonical_document(
            {key: value for key, value in tampered.items() if key != "registration_hash"},
            "registration_hash",
        )
        document = self._build(
            source=tampered,
            expected_hash=tampered["registration_hash"],
        )
        self.assertEqual(
            document["blockers"], ["SOURCE_ANCHOR_REGISTRATION_NOT_VERIFIED"]
        )

    def test_independently_valid_source_requires_its_matching_context(self):
        other_context = self.source_case._kwargs(provider_id="OTHER-PROVIDER")
        other_source = self.source_case._build(provider_id="OTHER-PROVIDER")
        mismatch = self._build(
            source=other_source,
            expected_hash=other_source["registration_hash"],
        )
        matched = self._build(
            source=other_source,
            anchor_context=other_context,
            expected_hash=other_source["registration_hash"],
        )
        self.assertEqual(
            mismatch["blockers"], ["SOURCE_ANCHOR_REGISTRATION_NOT_VERIFIED"]
        )
        self.assertEqual(matched["registration_state"], REGISTRATION_STATE)
        self.assertEqual(matched["provider_id"], "OTHER-PROVIDER")

    def test_identifiers_are_strict_ascii_tokens(self):
        for key in (
            "identity_adapter_id",
            "identity_adapter_static_fingerprint",
            "identity_registry_id",
            "identity_registry_snapshot_id",
            "provider_subject_id",
        ):
            document = self._build(**{key: "bad value"})
            self.assertEqual(
                document["blockers"], ["IDENTITY_REGISTRATION_IDENTIFIER_INVALID"]
            )

    def test_hash_bindings_require_strict_sha256(self):
        for key in (
            "identity_adapter_implementation_sha256",
            "identity_registry_snapshot_sha256",
            "identity_registry_trust_root_sha256",
            "provider_identity_document_sha256",
        ):
            document = self._build(**{key: "A" * 64})
            self.assertEqual(
                document["blockers"],
                ["IDENTITY_REGISTRATION_HASH_BINDING_INVALID"],
            )

    def test_identity_attestation_algorithm_and_encoding_are_exact(self):
        algorithm = self._build(identity_attestation_signature_algorithm="RSA")
        encoding = self._build(
            identity_attestation_receipt_encoding="PROVIDER_OPAQUE_BYTES"
        )
        self.assertEqual(
            algorithm["blockers"],
            ["IDENTITY_ATTESTATION_SIGNATURE_ALGORITHM_UNSUPPORTED"],
        )
        self.assertEqual(
            encoding["blockers"],
            ["IDENTITY_ATTESTATION_RECEIPT_ENCODING_UNSUPPORTED"],
        )

    def test_declaration_chronology_is_fail_closed(self):
        before_anchor = self._build(declared_at_utc="2026-09-14T23:59:59Z")
        at_evaluation = self._build(declared_at_utc="2026-10-01T00:00:00Z")
        malformed = self._build(declared_at_utc="2026-09-16T00:00:00+00:00")
        self.assertEqual(
            before_anchor["blockers"],
            ["IDENTITY_ADAPTER_DECLARATION_BEFORE_ANCHOR_REGISTRATION"],
        )
        self.assertEqual(
            at_evaluation["blockers"],
            ["IDENTITY_ADAPTER_DECLARATION_NOT_BEFORE_EVALUATION"],
        )
        self.assertEqual(
            malformed["blockers"], ["IDENTITY_ADAPTER_DECLARATION_TIME_INVALID"]
        )

    def test_public_document_has_no_key_bytes_assertions_or_receipts(self):
        forbidden = {
            "attestation_receipt",
            "external_identity_assertion",
            "private_key",
            "public_key_base64",
            "rows",
            "signature_base64",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(self._build())))

    def test_authority_and_external_facts_remain_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        for key in (
            "evaluation_activated",
            "external_identity_assertion_observed",
            "external_identity_signature_verified",
            "external_registration_time_verified",
            "identity_adapter_implementation_verified",
            "provider_identity_verified",
            "result_available",
        ):
            self.assertFalse(document["facts"][key], key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["registration_hash"], second["registration_hash"])

    def test_verifier_rejects_tamper_extra_fields_and_non_objects(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["registration_state"] = "PROVIDER_IDENTITY_VERIFIED"
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_and_schema_keys_are_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["registration_protocol_id"], REGISTRATION_PROTOCOL_ID)
        self.assertEqual(
            set(document),
            {
                "authority",
                "blockers",
                "declared_at_utc",
                "evaluation_not_before_date",
                "facts",
                "future_evaluation_id",
                "identity_adapter_id",
                "identity_adapter_implementation_sha256",
                "identity_adapter_static_fingerprint",
                "identity_adapter_value_binding_hash",
                "identity_attestation_receipt_encoding",
                "identity_attestation_signature_algorithm",
                "identity_registry_id",
                "identity_registry_snapshot_id",
                "identity_registry_snapshot_sha256",
                "identity_registry_trust_root_sha256",
                "provider_id",
                "provider_identity_document_sha256",
                "provider_receipt_trust_root_sha256",
                "provider_subject_id",
                "registration_hash",
                "registration_protocol_id",
                "registration_reason",
                "registration_state",
                "schema_version",
                "source_anchor_adapter_id",
                "source_anchor_adapter_registration_hash",
                "source_anchor_adapter_registration_schema",
                "source_observation_protocol_hash",
                "source_preregistration_hash",
                "source_state",
                "static_fingerprint",
            },
        )


if __name__ == "__main__":
    unittest.main()
