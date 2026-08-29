import unittest
from copy import deepcopy
from decimal import getcontext, setcontext
from unittest.mock import patch

from exchange_terminal.services import (
    strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1 as source_module,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1 import (
    ANCHOR_ADAPTER_INTERFACE,
    EXTERNAL_ATTESTATION_SCHEMA,
    MISSING_EXTERNAL_ATTESTATION_POLICY,
    OBSERVATION_BATCH_SCHEMA,
    PROTOCOL_ID,
    REQUIRED_ATTESTATION_BINDINGS,
    REQUIRED_ATTESTATION_STATE,
    REQUIRED_BATCH_BINDINGS,
    REQUIRED_TIME_RULES,
    SCHEMA_VERSION,
    SELF_ATTESTED_ANCHOR_POLICY,
    STATIC_FINGERPRINT,
    UNSUPPORTED_ANCHOR_ADAPTER_POLICY,
    build_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1,
    verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1,
)
from tests import (
    test_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1 as source_tests,
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


class StrategyCorrelationCrossLagFactorCalibrationLongHorizonObservationProtocolV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.addCleanup(setcontext, getcontext().copy())
        self.case = (
            source_tests.StrategyCorrelationCrossLagFactorCalibrationLongHorizonPreregistrationV1Tests(
                methodName="test_positive_source_declares_not_evaluated_protocol"
            )
        )
        self.case.setUp()
        self.source = self.case._build()
        self.context = self._capture_context(self.source)

    def _capture_context(self, source, **source_overrides):
        captured = {}
        original = (
            source_module.build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1
        )

        def spy(*args, **kwargs):
            captured.update(kwargs)
            return original(*args, **kwargs)

        with patch.object(
            source_module,
            "build_strategy_correlation_cross_lag_factor_calibration_long_horizon_preregistration_v1",
            spy,
        ):
            self.assertTrue(self.case._verify(source, **source_overrides))
        return captured

    def _build(
        self,
        source=_DEFAULT,
        context=_DEFAULT,
        expected_hash=_DEFAULT,
    ):
        source = self.source if source is _DEFAULT else source
        context = self.context if context is _DEFAULT else context
        expected_hash = (
            self.source["preregistration_hash"]
            if expected_hash is _DEFAULT
            else expected_hash
        )
        return build_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
            source,
            context,
            expected_preregistration_hash=expected_hash,
        )

    def _verify(
        self,
        document,
        source=_DEFAULT,
        context=_DEFAULT,
        expected_hash=_DEFAULT,
    ):
        source = self.source if source is _DEFAULT else source
        context = self.context if context is _DEFAULT else context
        expected_hash = (
            self.source["preregistration_hash"]
            if expected_hash is _DEFAULT
            else expected_hash
        )
        return verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_observation_protocol_v1(
            document,
            source,
            context,
            expected_preregistration_hash=expected_hash,
        )

    def test_positive_source_declares_protocol_without_observations(self):
        document = self._build()
        self.assertEqual(document["source_state"], "VERIFIED")
        self.assertEqual(
            document["protocol_state"], "PROTOCOL_DECLARED_NO_OBSERVATIONS"
        )
        self.assertTrue(document["facts"]["source_preregistration_verified"])
        self.assertTrue(document["facts"]["observation_protocol_pinned"])
        self.assertTrue(self._verify(document))

    def test_contract_identity_is_exact(self):
        document = self._build()
        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["protocol_id"], PROTOCOL_ID)

    def test_source_bindings_are_exact(self):
        document = self._build()
        self.assertEqual(
            document["source_preregistration_hash"],
            self.source["preregistration_hash"],
        )
        self.assertEqual(
            document["source_report_consumer_v7_hash"],
            self.source["source_report_consumer_v7_hash"],
        )
        self.assertEqual(
            document["source_external_time_anchor_reference_hash"],
            self.source["source_external_time_anchor_reference_hash"],
        )
        self.assertEqual(
            document["future_evaluation_id"], self.source["future_evaluation_id"]
        )

    def test_observation_batch_contract_is_pinned(self):
        document = self._build()
        self.assertEqual(document["observation_batch_schema"], OBSERVATION_BATCH_SCHEMA)
        self.assertEqual(
            document["required_batch_bindings"], list(REQUIRED_BATCH_BINDINGS)
        )

    def test_external_attestation_contract_is_pinned(self):
        document = self._build()
        self.assertEqual(
            document["external_attestation_schema"], EXTERNAL_ATTESTATION_SCHEMA
        )
        self.assertEqual(document["anchor_adapter_interface"], ANCHOR_ADAPTER_INTERFACE)
        self.assertEqual(
            document["required_attestation_bindings"],
            list(REQUIRED_ATTESTATION_BINDINGS),
        )
        self.assertEqual(
            document["required_attestation_state"], REQUIRED_ATTESTATION_STATE
        )

    def test_fail_closed_anchor_policies_are_exact(self):
        document = self._build()
        self.assertEqual(
            document["missing_external_attestation_policy"],
            MISSING_EXTERNAL_ATTESTATION_POLICY,
        )
        self.assertEqual(
            document["unsupported_anchor_adapter_policy"],
            UNSUPPORTED_ANCHOR_ADAPTER_POLICY,
        )
        self.assertEqual(
            document["self_attested_anchor_policy"], SELF_ATTESTED_ANCHOR_POLICY
        )

    def test_time_rules_are_preregistered(self):
        document = self._build()
        self.assertEqual(document["required_time_rules"], list(REQUIRED_TIME_RULES))
        self.assertEqual(
            document["evaluation_not_before_date"],
            self.source["evaluation_not_before_date"],
        )

    def test_long_horizon_support_is_inherited_exactly(self):
        document = self._build()
        self.assertEqual(document["evaluated_lags"], list(range(1, 13)))
        self.assertEqual(document["maximum_evaluated_lag"], 12)
        self.assertEqual(document["minimum_rows_per_fold"], 20)
        self.assertEqual(document["minimum_pairs_at_maximum_lag"], 8)

    def test_protocol_contains_no_observations_attestation_or_results(self):
        document = self._build()
        forbidden = {
            "external_attestation",
            "factor_return",
            "observation_batch",
            "observations",
            "pnl",
            "profit",
            "result",
            "results",
            "returns",
            "rows",
            "sharpe",
        }
        self.assertTrue(forbidden.isdisjoint(_all_keys(document)))
        self.assertFalse(document["facts"]["observation_batch_present"])
        self.assertFalse(document["facts"]["external_attestation_present"])
        self.assertFalse(document["facts"]["result_available"])

    def test_authority_is_permanently_locked(self):
        document = self._build()
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertFalse(value, key)
        self.assertFalse(document["facts"]["external_authenticity_proven"])

    def test_expected_preregistration_hash_is_bound(self):
        document = self._build(expected_hash="0" * 64)
        self.assertEqual(document["protocol_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_PREREGISTRATION_HASH_MISMATCH"]
        )

    def test_source_context_requires_exact_fields(self):
        missing = deepcopy(self.context)
        missing.pop("expected_calibration_observations_hash")
        extra = deepcopy(self.context)
        extra["authority"] = "forged"
        for context in (missing, extra):
            document = self._build(context=context)
            self.assertEqual(document["protocol_state"], "UNKNOWN")
            self.assertEqual(
                document["blockers"], ["SOURCE_VERIFICATION_CONTEXT_FIELDS_INVALID"]
            )

    def test_source_context_expected_hash_tamper_is_rejected(self):
        context = deepcopy(self.context)
        context["expected_calibration_observations_hash"] = "0" * 64
        document = self._build(context=context)
        self.assertEqual(document["protocol_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_PREREGISTRATION_NOT_VERIFIED"]
        )

    def test_resealed_source_tamper_is_rejected(self):
        source = deepcopy(self.source)
        source["future_evaluation_id"] = "LH12-FORGED000000000000"
        source = seal_strict_canonical_document(
            {key: value for key, value in source.items() if key != "preregistration_hash"},
            "preregistration_hash",
        )
        document = self._build(
            source=source,
            expected_hash=source["preregistration_hash"],
        )
        self.assertEqual(document["protocol_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_PREREGISTRATION_NOT_VERIFIED"]
        )

    def test_blocked_source_is_monotone_and_verifiable(self):
        overrides = self.case._block_context()
        source = self.case._build(**overrides)
        context = self._capture_context(source, **overrides)
        document = self._build(
            source=source,
            context=context,
            expected_hash=source["preregistration_hash"],
        )
        self.assertEqual(document["source_state"], "BLOCKED")
        self.assertEqual(document["protocol_state"], "UNKNOWN")
        self.assertEqual(
            document["blockers"], ["SOURCE_PREREGISTRATION_NOT_DECLARED"]
        )
        self.assertTrue(
            self._verify(
                document,
                source=source,
                context=context,
                expected_hash=source["preregistration_hash"],
            )
        )

    def test_missing_and_unsupported_sources_are_distinct(self):
        missing = self._build(source=None)
        unsupported = self._build(source={"schema_version": "legacy-v0"})
        self.assertEqual(missing["protocol_state"], "UNKNOWN")
        self.assertEqual(unsupported["protocol_state"], "UNKNOWN")
        self.assertNotEqual(missing["blockers"], unsupported["blockers"])

    def test_build_is_deterministic_and_side_effect_free(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["protocol_hash"], second["protocol_hash"])

    def test_verifier_rejects_tamper_and_extra_keys(self):
        document = self._build()
        tampered = deepcopy(document)
        tampered["minimum_rows_per_fold"] = 19
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
                "anchor_adapter_interface",
                "authority",
                "blockers",
                "evaluated_lags",
                "evaluation_not_before_date",
                "external_attestation_schema",
                "facts",
                "future_evaluation_id",
                "maximum_evaluated_lag",
                "minimum_pairs_at_maximum_lag",
                "minimum_rows_per_fold",
                "missing_external_attestation_policy",
                "observation_batch_schema",
                "protocol_hash",
                "protocol_id",
                "protocol_state",
                "required_attestation_bindings",
                "required_attestation_state",
                "required_batch_bindings",
                "required_time_rules",
                "schema_version",
                "self_attested_anchor_policy",
                "source_evaluation_status",
                "source_external_time_anchor_reference_hash",
                "source_preregistration_hash",
                "source_preregistration_schema",
                "source_report_consumer_v7_hash",
                "source_state",
                "static_fingerprint",
                "unsupported_anchor_adapter_policy",
            },
        )


if __name__ == "__main__":
    unittest.main()
