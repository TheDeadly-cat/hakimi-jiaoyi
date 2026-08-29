from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_protocol import (
    PROTOCOL_SCHEMA,
    PROTOCOL_VERIFICATION_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_protocol_registration,
    verify_strategy_correlation_cross_lag_protocol_registration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests.test_strategy_correlation_cross_lag_preregistration_adapter_binding import (
    StrategyCorrelationCrossLagPreregistrationAdapterBindingTests,
)


class StrategyCorrelationCrossLagProtocolRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = StrategyCorrelationCrossLagPreregistrationAdapterBindingTests()
        self.fixture.setUp()
        self.binding = self.fixture._build()

    def _values(self):
        values = self.fixture._values()
        return {
            "preregistration_adapter_binding": self.binding,
            **values,
            "expected_preregistration_adapter_binding_hash": self.binding["binding_hash"],
        }

    def _build(self, **overrides):
        values = self._values()
        values.update(overrides)
        return build_strategy_correlation_cross_lag_protocol_registration(
            values.pop("preregistration_adapter_binding"),
            **values,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_protocol_registration(
            document,
            values.pop("preregistration_adapter_binding"),
            **values,
        )

    def _assert_locked(self, document):
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_valid_registration_freezes_contracts_without_sequence_claim(self):
        registration = self._build()
        self.assertEqual(registration["schema_version"], PROTOCOL_SCHEMA)
        self.assertEqual(registration["verification_schema_version"], PROTOCOL_VERIFICATION_SCHEMA)
        self.assertEqual(registration["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(registration["registration_state"], "REGISTERED_CANDIDATE_NOT_SEQUENCE_ATTESTED")
        self.assertEqual(registration["maturity_state"], "CANDIDATE_PROTOCOL_REGISTERED_NOT_FORMAL")
        self.assertEqual(
            registration["blockers"],
            [
                "CROSS_LAG_PROTOCOL_SEQUENCE_ORDER_NOT_ATTESTED",
                "CROSS_LAG_EVALUATION_NOT_BOUND",
            ],
        )
        self.assertTrue(all(registration["facts"].values()))
        self._assert_locked(registration)

    def test_valid_registration_exactly_verifies(self):
        registration = self._build()
        self.assertTrue(self._verify(registration))

    def test_registration_contains_no_observed_result_fields(self):
        registration = self._build()
        forbidden = {
            "evaluation_hash",
            "consumer_receipt_hash",
            "gate_decision",
            "gate_reason",
            "dependent_test_count",
            "lag_test_count",
            "cross_stratum_pair_count",
            "max_adjusted_absolute_lower",
            "lag_results",
        }
        self.assertFalse(forbidden.intersection(registration))

    def test_missing_is_distinct_from_invalid_supplied(self):
        missing = self._build(preregistration_adapter_binding=None)
        invalid = self._build(preregistration_adapter_binding=[])
        self.assertEqual(missing["registration_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["registration_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_hash_mismatches_fail_closed(self):
        fields = [
            "expected_preregistration_adapter_binding_hash",
            "expected_strata_protocol_registration_hash",
            "expected_registry_assignment_adapter_hash",
            "expected_direction_contract_hash",
            "expected_registry_asset_hash",
            "expected_classification_source_hash",
            "expected_stratum_assignment_hash",
        ]
        for field in fields:
            with self.subTest(field=field):
                self.assertEqual(self._build(**{field: "f" * 64})["registration_state"], "UNKNOWN")

    def test_resealed_nondefault_p1b_hash_tamper_fails_closed(self):
        binding = copy.deepcopy(self.binding)
        self.assertNotEqual(binding["analytic_policy_hash"], "d" * 64)
        binding["analytic_policy_hash"] = "d" * 64
        binding.pop("binding_hash")
        binding = seal_strict_canonical_document(binding, "binding_hash")
        registration = self._build(
            preregistration_adapter_binding=binding,
            expected_preregistration_adapter_binding_hash=binding["binding_hash"],
        )
        self.assertEqual(registration["registration_state"], "UNKNOWN")

    def test_p1b_blocker_drift_fails_closed(self):
        binding = copy.deepcopy(self.binding)
        binding["blockers"] = []
        binding.pop("binding_hash")
        binding = seal_strict_canonical_document(binding, "binding_hash")
        registration = self._build(
            preregistration_adapter_binding=binding,
            expected_preregistration_adapter_binding_hash=binding["binding_hash"],
        )
        self.assertEqual(registration["registration_state"], "UNKNOWN")

    def test_context_replay_mismatch_fails_closed(self):
        source = copy.deepcopy(self.fixture.preregistration)
        source["symbols"] = list(reversed(source["symbols"]))
        registration = self._build(source_preregistration=source)
        self.assertEqual(registration["registration_state"], "UNKNOWN")

    def test_authority_aliases_in_source_fail_closed(self):
        for value in (0, "", "false", True):
            with self.subTest(value=value):
                binding = copy.deepcopy(self.binding)
                binding["authority"]["paper_authorized"] = value
                binding.pop("binding_hash")
                binding = seal_strict_canonical_document(binding, "binding_hash")
                registration = self._build(
                    preregistration_adapter_binding=binding,
                    expected_preregistration_adapter_binding_hash=binding["binding_hash"],
                )
                self.assertEqual(registration["registration_state"], "UNKNOWN")

    def test_extra_untrusted_source_field_is_not_reflected(self):
        binding = copy.deepcopy(self.binding)
        binding["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        binding.pop("binding_hash")
        binding = seal_strict_canonical_document(binding, "binding_hash")
        registration = self._build(
            preregistration_adapter_binding=binding,
            expected_preregistration_adapter_binding_hash=binding["binding_hash"],
        )
        self.assertEqual(registration["registration_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", str(registration))

    def test_p1b_verifier_exception_fails_closed(self):
        with patch(
            "exchange_terminal.services.strategy_correlation_cross_lag_protocol.verify_strategy_correlation_cross_lag_preregistration_adapter_binding",
            side_effect=RuntimeError("adversarial verifier fault"),
        ):
            registration = self._build()
        self.assertEqual(registration["registration_state"], "UNKNOWN")
        self._assert_locked(registration)

    def test_resealed_registration_policy_tamper_does_not_verify(self):
        registration = self._build()
        tampered = copy.deepcopy(registration)
        self.assertEqual(tampered["family_alpha"], "0.05")
        tampered["family_alpha"] = "0.1"
        tampered.pop("protocol_registration_hash")
        tampered = seal_strict_canonical_document(tampered, "protocol_registration_hash")
        self.assertFalse(self._verify(tampered))

    def test_resealed_registration_authority_escalation_does_not_verify(self):
        registration = self._build()
        tampered = copy.deepcopy(registration)
        tampered["authority"]["sequence_order_attested"] = True
        tampered.pop("protocol_registration_hash")
        tampered = seal_strict_canonical_document(tampered, "protocol_registration_hash")
        self.assertFalse(self._verify(tampered))

    def test_non_mapping_registration_never_verifies(self):
        self.assertFalse(self._verify([]))


if __name__ == "__main__":
    unittest.main()
