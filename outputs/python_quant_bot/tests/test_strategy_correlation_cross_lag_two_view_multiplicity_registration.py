from __future__ import annotations

from copy import deepcopy
import inspect
import unittest

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cross_lag_two_view_multiplicity_registration import (
    CORRECTION_METHOD,
    DEPENDENCE_THRESHOLD,
    FAMILY_ALPHA,
    LAGS,
    REGISTRATION_SCHEMA,
    STATIC_FINGERPRINT,
    VIEWS,
    build_strategy_correlation_cross_lag_two_view_multiplicity_registration,
    verify_strategy_correlation_cross_lag_two_view_multiplicity_registration,
)
from tests.test_strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    StrategyCorrelationCrossLagFactorConditionalDiagnosticTests as F0Cases,
)


class _DictSubclass(dict):
    pass


class StrategyCorrelationCrossLagTwoViewMultiplicityRegistrationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.fixture = F0Cases("runTest")
        self.fixture.setUp()
        context = self.fixture._common_factor_case(direct_residual=False)
        self.strata = context["preregistered_strata"]
        self.strata_hash = context["expected_stratum_assignment_hash"]

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def _build(self, strata=None, expected_hash=None):
        source = self.strata if strata is None else strata
        expected = self.strata_hash if expected_hash is None else expected_hash
        return build_strategy_correlation_cross_lag_two_view_multiplicity_registration(
            source,
            expected_stratum_assignment_hash=expected,
        )

    def _verify(self, document, strata=None, expected_strata_hash=None, expected_hash=None):
        source = self.strata if strata is None else strata
        strata_hash = self.strata_hash if expected_strata_hash is None else expected_strata_hash
        registration_hash = (
            document.get("registration_hash")
            if expected_hash is None and type(document) is dict
            else expected_hash
        )
        return verify_strategy_correlation_cross_lag_two_view_multiplicity_registration(
            document,
            source,
            expected_stratum_assignment_hash=strata_hash,
            expected_registration_hash=registration_hash,
        )

    @staticmethod
    def _reseal(document):
        return seal_strict_canonical_document(document, "registration_hash")

    def test_valid_registration_derives_exact_two_view_family(self) -> None:
        document = self._build()
        self.assertTrue(self._verify(document))
        self.assertEqual(document["source_state"], "REGISTERED")
        self.assertEqual(document["cross_stratum_pair_count"], 1)
        self.assertEqual(document["lag_count"], 4)
        self.assertEqual(document["per_view_test_count"], 4)
        self.assertEqual(document["view_count"], 2)
        self.assertEqual(document["global_test_count"], 8)
        self.assertEqual(document["views"], list(VIEWS))
        self.assertEqual(document["lags"], list(LAGS))

    def test_registration_api_has_no_rows_returns_or_evaluation_inputs(self) -> None:
        signature = inspect.signature(
            build_strategy_correlation_cross_lag_two_view_multiplicity_registration
        )
        self.assertEqual(
            tuple(signature.parameters),
            ("preregistered_strata", "expected_stratum_assignment_hash"),
        )
        forbidden = {"rows", "returns", "observations", "evaluation", "factor", "residual"}
        self.assertFalse(forbidden & set(signature.parameters))

    def test_different_partition_derives_exact_pair_and_test_counts(self) -> None:
        strata = {"A": "S1", "B": "S1", "C": "S2", "D": "S3"}
        document = self._build(strata, strict_canonical_hash(strata))
        self.assertEqual(document["cross_stratum_pair_count"], 5)
        self.assertEqual(document["per_view_test_count"], 20)
        self.assertEqual(document["global_test_count"], 40)
        self.assertTrue(
            self._verify(
                document,
                strata,
                expected_strata_hash=strict_canonical_hash(strata),
            )
        )

    def test_invalid_strata_have_fixed_exact_unknown_closure(self) -> None:
        variants = (
            {"A": "S1", "B": "S1"},
            {"A": "S1"},
            _DictSubclass(self.strata),
            {"A": "S1", "bad space": "S2"},
            {"A": "S1", "B": "bad space"},
        )
        for strata in variants:
            expected = strict_canonical_hash(dict(strata)) if len(strata) else "0" * 64
            document = self._build(strata, expected)
            with self.subTest(strata=strata):
                self.assertEqual(document["source_state"], "UNKNOWN")
                self.assertEqual(document["blockers"], ["TWO_VIEW_REGISTRATION_INVALID"])
                self.assertTrue(
                    self._verify(
                        document,
                        strata,
                        expected_strata_hash=expected,
                    )
                )

    def test_expected_strata_hash_mismatch_is_unknown(self) -> None:
        document = self._build(expected_hash="0" * 64)
        self.assertEqual(document["source_state"], "UNKNOWN")
        self.assertIsNone(document["stratum_assignment_hash"])
        self.assertTrue(
            self._verify(
                document,
                expected_strata_hash="0" * 64,
            )
        )

    def test_wrong_expected_registration_hash_rejects(self) -> None:
        document = self._build()
        self.assertFalse(self._verify(document, expected_hash="0" * 64))
        self.assertFalse(self._verify(document, expected_hash=True))

    def test_contract_identity_and_policy_are_exact(self) -> None:
        document = self._build()
        self.assertEqual(document["schema_version"], REGISTRATION_SCHEMA)
        self.assertEqual(document["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(document["correction_method"], CORRECTION_METHOD)
        self.assertEqual(document["family_alpha"], FAMILY_ALPHA)
        self.assertEqual(document["dependence_threshold"], DEPENDENCE_THRESHOLD)

    def test_identity_order_and_strata_are_hash_bound_without_label_echo(self) -> None:
        document = self._build()
        self.assertEqual(document["stratum_assignment_hash"], self.strata_hash)
        self.assertEqual(
            document["identity_order_hash"],
            strict_canonical_hash(sorted(self.strata)),
        )
        self.assertNotIn("identities", document)
        self.assertNotIn("strata", document)
        scalar_strings = {
            value
            for value in document.values()
            if type(value) is str
        }
        for private in (*self.strata.keys(), *self.strata.values()):
            self.assertNotIn(private, scalar_strings)

    def test_structural_registration_fact_does_not_attest_time(self) -> None:
        document = self._build()
        self.assertTrue(
            document["facts"]["registration_built_from_pre_evaluation_inputs"]
        )
        self.assertTrue(document["facts"]["global_two_view_family_registered"])
        self.assertFalse(document["facts"]["registration_timing_attested"])
        self.assertFalse(document["authority"]["registration_timing_attested"])

    def test_all_authority_remains_locked(self) -> None:
        document = self._build()
        self.assertIs(document["authority"]["descriptive_only"], True)
        self.assertTrue(
            all(
                value is False
                for key, value in document["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_resealed_view_lag_and_count_tamper_reject(self) -> None:
        document = self._build()
        variants = []
        changed = deepcopy(document)
        changed["views"] = list(reversed(changed["views"]))
        variants.append(changed)
        changed = deepcopy(document)
        changed["lags"] = [-1, 1]
        variants.append(changed)
        changed = deepcopy(document)
        changed["global_test_count"] += 1
        variants.append(changed)
        for changed in variants:
            tampered = self._reseal(changed)
            with self.subTest(keys=sorted(tampered)):
                self.assertFalse(self._verify(tampered))

    def test_resealed_policy_and_timing_tamper_reject(self) -> None:
        document = self._build()
        variants = []
        for key, value in (
            ("family_alpha", "0.10"),
            ("dependence_threshold", "0.70"),
            ("correction_method", "NONE"),
        ):
            changed = deepcopy(document)
            changed[key] = value
            variants.append(changed)
        changed = deepcopy(document)
        changed["facts"]["registration_timing_attested"] = True
        variants.append(changed)
        for changed in variants:
            tampered = self._reseal(changed)
            with self.subTest(value=changed):
                self.assertFalse(self._verify(tampered))

    def test_resealed_authority_alias_and_true_permission_reject(self) -> None:
        document = self._build()
        variants = []
        alias = deepcopy(document)
        alias["authority"]["ready"] = True
        variants.append(alias)
        permission = deepcopy(document)
        permission["authority"]["current_admission_allowed"] = True
        variants.append(permission)
        for changed in variants:
            self.assertFalse(self._verify(self._reseal(changed)))

    def test_non_mapping_and_subclass_documents_never_verify(self) -> None:
        document = self._build()
        self.assertFalse(self._verify(None, expected_hash=document["registration_hash"]))
        self.assertFalse(
            self._verify(
                _DictSubclass(document),
                expected_hash=document["registration_hash"],
            )
        )

    def test_registration_is_deterministic_and_uses_no_external_state(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
