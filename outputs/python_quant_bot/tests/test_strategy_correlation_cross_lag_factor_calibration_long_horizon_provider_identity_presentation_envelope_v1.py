from __future__ import annotations

import unittest
from copy import deepcopy

from exchange_terminal.application.strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1 import (
    AXIS_ORDER,
    POSITIVE_DISPLAY_STATE,
    PRESENTATION_STATUS,
    SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_verifier_v1 as assertion_source_tests,
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


def _all_strings(value):
    if type(value) is str:
        return [value]
    if type(value) is dict:
        found = []
        for item in value.values():
            found.extend(_all_strings(item))
        return found
    if type(value) is list:
        found = []
        for item in value:
            found.extend(_all_strings(item))
        return found
    return []


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityPresentationEnvelopeV1Tests(
    unittest.TestCase
):
    def setUp(self):
        source_class = assertion_source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonProviderIdentityAssertionVerifierV1Tests
        self.source_case = source_class(
            methodName=next(name for name in dir(source_class) if name.startswith("test_"))
        )
        self.source_case.setUp()
        self.addCleanup(self.source_case.doCleanups)
        self.source = self.source_case._build()
        self.context = {
            "expected_identity_assertion_hash": self.source_case.receipt[
                "assertion_hash"
            ],
            "expected_provider_identity_registration_hash": (
                self.source_case.registration["registration_hash"]
            ),
            "identity_assertion_receipt": self.source_case.receipt,
            "provider_identity_registration_v1": self.source_case.registration,
            "provider_identity_registration_verification_context": (
                self.source_case.registration_context
            ),
        }

    def _build(self, *, source=_UNSET, context=_UNSET, expected_hash=_UNSET):
        source = self.source if source is _UNSET else source
        context = self.context if context is _UNSET else context
        expected_hash = (
            source.get("verification_hash")
            if expected_hash is _UNSET and type(source) is dict
            else expected_hash
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1(
            source,
            context,
            expected_provider_identity_assertion_verification_hash=expected_hash,
        )

    def _verify(self, document):
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_presentation_envelope_v1(
            document,
            self.source,
            self.context,
            expected_provider_identity_assertion_verification_hash=self.source[
                "verification_hash"
            ],
        )

    def test_positive_source_maps_to_external_trust_gap(self):
        document = self._build()
        self.assertEqual(document["display_state"], POSITIVE_DISPLAY_STATE)
        self.assertEqual(document["presentation_status"], PRESENTATION_STATUS)
        self.assertEqual(document["axis_order"], list(AXIS_ORDER))
        self.assertTrue(document["facts"]["cryptographic_identity_assertion_verified"])
        self.assertFalse(document["facts"]["provider_identity_verified"])
        self.assertTrue(self._verify(document))

    def test_axis_states_are_ordered_and_monotone(self):
        document = self._build()
        self.assertEqual([axis["axis"] for axis in document["axes"]], list(AXIS_ORDER))
        self.assertEqual(
            [axis["state"] for axis in document["axes"]],
            [
                "CRYPTOGRAPHIC_PROOF_BOUND",
                "EXTERNAL_TRUST_TIME_REPLAY_UNPROVEN",
                "DETACHED_CANDIDATE",
                "LOCKED",
            ],
        )

    def test_expected_source_hash_is_fail_closed(self):
        invalid = self._build(expected_hash="invalid")
        mismatch = self._build(expected_hash="0" * 64)
        self.assertEqual(
            invalid["blockers"], ["EXPECTED_SOURCE_VERIFICATION_HASH_INVALID"]
        )
        self.assertEqual(mismatch["blockers"], ["SOURCE_VERIFICATION_HASH_MISMATCH"])

    def test_context_requires_exact_fields(self):
        missing = deepcopy(self.context)
        missing.pop("identity_assertion_receipt")
        extra = deepcopy(self.context)
        extra["ready"] = True
        for context in (missing, extra, None):
            self.assertEqual(
                self._build(context=context)["blockers"],
                ["SOURCE_VERIFICATION_CONTEXT_INVALID"],
            )

    def test_source_is_reverified_not_trusted_by_label(self):
        tampered = deepcopy(self.source)
        tampered["membership_proof_count"] = 1
        document = self._build(source=tampered, expected_hash=self.source["verification_hash"])
        self.assertEqual(document["blockers"], ["SOURCE_VERIFICATION_NOT_VERIFIED"])

    def test_private_receipt_tamper_is_rejected_through_context(self):
        context = deepcopy(self.context)
        context["identity_assertion_receipt"]["provider_subject_id"] = "FORGED"
        document = self._build(context=context)
        self.assertEqual(document["blockers"], ["SOURCE_VERIFICATION_NOT_VERIFIED"])

    def test_cross_binding_hash_drift_is_rejected(self):
        context = deepcopy(self.context)
        context["expected_identity_assertion_hash"] = "0" * 64
        document = self._build(context=context)
        self.assertEqual(document["blockers"], ["SOURCE_VERIFICATION_NOT_VERIFIED"])

    def test_summary_contains_aggregates_only(self):
        summary = self._build()["summary"]
        self.assertEqual(summary["provider_id"], self.source["provider_id"])
        self.assertEqual(summary["membership_tree_size"], 4)
        self.assertEqual(summary["membership_proof_count"], 2)
        self.assertEqual(summary["membership_leaf_index"], 0)

    def test_lineage_hashes_are_complete(self):
        lineage = self._build()["lineage"]
        self.assertEqual(len(lineage), 9)
        for key, value in lineage.items():
            self.assertEqual(len(value), 64, key)
            self.assertEqual(value, value.lower(), key)

    def test_public_envelope_redacts_private_crypto_material(self):
        forbidden = {
            "membership_proof",
            "registry_public_key_base64",
            "registry_signature_base64",
            "sibling_sha256",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(self._build())))

    def test_copy_has_no_ready_profit_buy_or_sell_claim(self):
        joined = " ".join(_all_strings(self._build())).upper()
        for token in (" READY ", " PROFIT ", " BUY ", " SELL "):
            self.assertNotIn(token, f" {joined} ")

    def test_authority_is_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)

    def test_build_is_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["presentation_hash"], second["presentation_hash"])

    def test_verifier_rejects_tamper_extra_fields_and_non_objects(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["display_state"] = "IDENTITY_VERIFIED"
        extra = deepcopy(document)
        extra["ready"] = True
        self.assertFalse(self._verify(tampered))
        self.assertFalse(self._verify(extra))
        self.assertFalse(self._verify(None))

    def test_contract_identity_and_exact_keys(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            set(document),
            {
                "authority",
                "axes",
                "axis_order",
                "blockers",
                "display_state",
                "facts",
                "lineage",
                "presentation_hash",
                "presentation_status",
                "schema_version",
                "source_schema_version",
                "source_state",
                "source_static_fingerprint",
                "source_verification_state",
                "static_fingerprint",
                "summary",
            },
        )
        self.assertEqual(
            set(document["axes"][0]),
            {"axis", "detail", "headline", "signal", "state"},
        )


if __name__ == "__main__":
    unittest.main()
