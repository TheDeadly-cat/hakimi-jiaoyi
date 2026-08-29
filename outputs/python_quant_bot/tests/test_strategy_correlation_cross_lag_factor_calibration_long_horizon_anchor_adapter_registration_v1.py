import unittest
from copy import deepcopy
from decimal import getcontext, setcontext

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1 import (
    RECEIPT_ENCODINGS,
    REGISTRATION_PROTOCOL_ID,
    SCHEMA_VERSION,
    SIGNATURE_ALGORITHMS,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 as source_tests,
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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonAnchorAdapterRegistrationV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationProtocolV1Tests(
                methodName="test_positive_source_declares_protocol_without_observations"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.protocol = self.case._build()
        self.preregistration = self.case.source
        self.context = self.case.context
        self.adapter_values = {
            "adapter_id": "PUBLIC-TIMESTAMP-ADAPTER-1",
            "adapter_static_fingerprint": "20260918-public-timestamp-adapter-1",
            "adapter_implementation_sha256": "b" * 64,
            "provider_id": "APPEND-ONLY-PROVIDER-1",
            "trust_root_sha256": "c" * 64,
            "signature_algorithm": "ED25519",
            "receipt_encoding": "RFC8785_JCS_UTF8",
            "declared_at_utc": "2026-09-15T00:00:00Z",
        }

    def _kwargs(self, **overrides):
        values = {
            "expected_observation_protocol_hash": self.protocol["protocol_hash"],
            "expected_preregistration_hash": self.preregistration[
                "preregistration_hash"
            ],
            **self.adapter_values,
        }
        values.update(overrides)
        return values

    def _build(
        self,
        protocol=_DEFAULT,
        preregistration=_DEFAULT,
        context=_DEFAULT,
        **overrides,
    ):
        protocol = self.protocol if protocol is _DEFAULT else protocol
        preregistration = (
            self.preregistration
            if preregistration is _DEFAULT
            else preregistration
        )
        context = self.context if context is _DEFAULT else context
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
            protocol,
            preregistration,
            context,
            **self._kwargs(**overrides),
        )

    def _verify(
        self,
        document,
        protocol=_DEFAULT,
        preregistration=_DEFAULT,
        context=_DEFAULT,
        **overrides,
    ):
        protocol = self.protocol if protocol is _DEFAULT else protocol
        preregistration = (
            self.preregistration
            if preregistration is _DEFAULT
            else preregistration
        )
        context = self.context if context is _DEFAULT else context
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_anchor_adapter_registration_v1(
            document,
            protocol,
            preregistration,
            context,
            **self._kwargs(**overrides),
        )

    def test_valid_values_are_declared_but_not_time_attested(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(
            document["registration_state"],
            "DECLARED_NOT_EXTERNALLY_TIME_ATTESTED",
        )
        self.assertTrue(document["facts"]["adapter_values_pinned"])
        self.assertTrue(document["facts"]["trust_root_value_pinned"])
        self.assertFalse(document["facts"]["external_registration_time_verified"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            document["registration_protocol_id"], REGISTRATION_PROTOCOL_ID
        )

    def test_adapter_provider_and_trust_root_values_are_exact(self):
        document = self._build()
        for key, value in self.adapter_values.items():
            self.assertEqual(document[key], value, key)

    def test_adapter_binding_hash_covers_every_selected_value(self):
        document = self._build()
        expected = {
            **self.adapter_values,
            "source_observation_protocol_hash": self.protocol["protocol_hash"],
            "source_preregistration_hash": self.preregistration[
                "preregistration_hash"
            ],
        }
        self.assertEqual(
            document["adapter_value_binding_hash"], strict_canonical_hash(expected)
        )
        changed = self._build(provider_id="APPEND-ONLY-PROVIDER-2")
        self.assertNotEqual(
            document["adapter_value_binding_hash"],
            changed["adapter_value_binding_hash"],
        )

    def test_source_hashes_and_dates_are_bound(self):
        document = self._build()
        self.assertEqual(
            document["source_observation_protocol_hash"],
            self.protocol["protocol_hash"],
        )
        self.assertEqual(
            document["source_preregistration_hash"],
            self.preregistration["preregistration_hash"],
        )
        self.assertEqual(
            document["source_preregistered_at_utc"],
            self.preregistration["preregistered_at_utc"],
        )
        self.assertEqual(document["evaluation_not_before_date"], "2026-10-01")

    def test_declared_time_must_not_precede_preregistration(self):
        document = self._build(declared_at_utc="2026-08-21T23:59:59Z")
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["ADAPTER_DECLARATION_BEFORE_PREREGISTRATION"]
        )

    def test_declared_time_must_be_strictly_before_evaluation_date(self):
        for value in ("2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z"):
            document = self._build(declared_at_utc=value)
            self.assertEqual(document["registration_state"], "UNKNOWN")
            self.assertEqual(
                document["blockers"],
                ["ADAPTER_DECLARATION_NOT_BEFORE_EVALUATION"],
            )

    def test_timestamp_grammar_is_strict(self):
        for value in (
            "2026-09-15T00:00:00+00:00",
            "2026-09-15 00:00:00Z",
            "2026-09-15T00:00:00.000Z",
            "not-a-time",
        ):
            document = self._build(declared_at_utc=value)
            self.assertEqual(document["registration_state"], "UNKNOWN", value)
            self.assertEqual(document["blockers"], ["ADAPTER_DECLARATION_TIME_INVALID"])

    def test_adapter_and_provider_identifiers_are_strict(self):
        for key, value in (
            ("adapter_id", ""),
            ("adapter_id", "bad adapter"),
            ("adapter_static_fingerprint", "bad fingerprint"),
            ("provider_id", "bad provider"),
        ):
            document = self._build(**{key: value})
            self.assertEqual(document["registration_state"], "UNKNOWN", key)

    def test_adapter_and_trust_root_hashes_are_strict(self):
        for key in ("adapter_implementation_sha256", "trust_root_sha256"):
            document = self._build(**{key: "A" * 64})
            self.assertEqual(document["registration_state"], "UNKNOWN", key)
            self.assertEqual(document["blockers"], ["ADAPTER_HASH_BINDINGS_INVALID"])

    def test_signature_algorithm_is_allowlisted(self):
        for value in SIGNATURE_ALGORITHMS:
            self.assertNotEqual(
                self._build(signature_algorithm=value)["registration_state"],
                "UNKNOWN",
            )
        self.assertEqual(
            self._build(signature_algorithm="HMAC_SHA256")["blockers"],
            ["SIGNATURE_ALGORITHM_UNSUPPORTED"],
        )

    def test_receipt_encoding_is_allowlisted(self):
        for value in RECEIPT_ENCODINGS:
            self.assertNotEqual(
                self._build(receipt_encoding=value)["registration_state"],
                "UNKNOWN",
            )
        self.assertEqual(
            self._build(receipt_encoding="CALLER_JSON")["blockers"],
            ["RECEIPT_ENCODING_UNSUPPORTED"],
        )

    def test_expected_observation_protocol_hash_is_bound(self):
        document = self._build(expected_observation_protocol_hash="0" * 64)
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_HASH_MISMATCH"]
        )

    def test_expected_preregistration_hash_is_bound(self):
        document = self._build(expected_preregistration_hash="0" * 64)
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"]
        )

    def test_resealed_source_protocol_tamper_is_rejected(self):
        protocol = deepcopy(self.protocol)
        protocol["anchor_adapter_interface"] = "CALLER_SELECTED_ADAPTER"
        protocol = seal_strict_canonical_document(
            {key: value for key, value in protocol.items() if key != "protocol_hash"},
            "protocol_hash",
        )
        document = self._build(
            protocol=protocol,
            expected_observation_protocol_hash=protocol["protocol_hash"],
        )
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_VERIFIED"]
        )

    def test_blocked_source_is_monotone_and_verifiable(self):
        prereg_overrides = self.case.case._block_context()
        preregistration = self.case.case._build(**prereg_overrides)
        context = self.case._capture_context(preregistration, **prereg_overrides)
        protocol = self.case._build(
            source=preregistration,
            context=context,
            expected_hash=preregistration["preregistration_hash"],
        )
        document = self._build(
            protocol=protocol,
            preregistration=preregistration,
            context=context,
            expected_observation_protocol_hash=protocol["protocol_hash"],
            expected_preregistration_hash=preregistration["preregistration_hash"],
        )
        self.assertEqual(document["source_state"], "BLOCKED")
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_DECLARED"]
        )
        self.assertTrue(
            self._verify(
                document,
                protocol=protocol,
                preregistration=preregistration,
                context=context,
                expected_observation_protocol_hash=protocol["protocol_hash"],
                expected_preregistration_hash=preregistration[
                    "preregistration_hash"
                ],
            )
        )

    def test_missing_source_is_fail_closed(self):
        document = self._build(protocol=None)
        self.assertEqual(document["registration_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_OBSERVATION_PROTOCOL_NOT_OBJECT"]
        )

    def test_document_contains_no_observation_attestation_or_result(self):
        document = self._build()
        forbidden = {
            "external_attestation",
            "observation_batch",
            "observations",
            "provider_receipt",
            "result",
            "results",
            "returns",
            "rows",
            "signature",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))
        self.assertFalse(document["facts"]["observation_batch_present"])
        self.assertFalse(document["facts"]["result_available"])

    def test_authority_is_permanently_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        self.assertFalse(document["facts"]["adapter_implementation_verified"])
        self.assertFalse(document["facts"]["external_authenticity_proven"])

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["registration_hash"], second["registration_hash"])

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["trust_root_sha256"] = "d" * 64
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
                "adapter_implementation_sha256",
                "adapter_static_fingerprint",
                "adapter_value_binding_hash",
                "authority",
                "blockers",
                "declared_at_utc",
                "evaluation_not_before_date",
                "facts",
                "future_evaluation_id",
                "provider_id",
                "receipt_encoding",
                "registration_hash",
                "registration_protocol_id",
                "registration_reason",
                "registration_state",
                "schema_version",
                "signature_algorithm",
                "source_external_time_anchor_reference_hash",
                "source_observation_protocol_hash",
                "source_observation_protocol_schema",
                "source_preregistered_at_utc",
                "source_preregistration_hash",
                "source_state",
                "static_fingerprint",
                "trust_root_sha256",
            },
        )


if __name__ == "__main__":
    unittest.main()
