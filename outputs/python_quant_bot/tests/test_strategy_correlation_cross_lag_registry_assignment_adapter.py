from __future__ import annotations

import copy
import math
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_gate import (
    evaluate_strategy_correlation_cross_lag_gate,
    verify_strategy_correlation_cross_lag_evaluation,
)
from exchange_terminal.services.strategy_correlation_cross_lag_registry_assignment_adapter import (
    ADAPTER_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_registry_assignment_adapter,
    verify_strategy_correlation_cross_lag_registry_assignment_adapter,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests.test_strategy_correlation_cross_lag_gate import (
    StrategyCorrelationCrossLagGateTests,
)
from tests.test_strategy_correlation_strata_registry import (
    StrategyCorrelationStrataRegistryTests,
)


class StrategyCorrelationCrossLagRegistryAssignmentAdapterTests(unittest.TestCase):
    def setUp(self):
        self.registry_fixture = StrategyCorrelationStrataRegistryTests()
        self.registry_fixture.setUp()
        (
            self.preregistration,
            self.dimensions,
            self.registration,
            self.asset,
        ) = self.registry_fixture._source()
        self.assessment = self.registry_fixture._assessment(
            self.preregistration,
            self.registration,
            self.asset,
        )
        self.dimension_id = "sector"
        self.selection_cutoff_date = "2026-08-02"
        self.first_observation_timestamp = "2026-08-02T00:00:00Z"
        self.assignment = {"AAA": "sector-a", "BBB": "sector-b"}
        self.assignment_hash = strict_canonical_hash(self.assignment)

    def _build(self, **overrides):
        values = {
            "registry_asset": self.asset,
            "registry_binding_assessment": self.assessment,
            "source_preregistration": self.preregistration,
            "strata_registration": self.registration,
            "dimension_id": self.dimension_id,
            "selection_cutoff_date": self.selection_cutoff_date,
            "first_observation_timestamp": self.first_observation_timestamp,
            "expected_registry_asset_hash": self.asset["registry_asset_hash"],
            "expected_classification_source_hash": self.registry_fixture.SOURCE_HASH,
            "expected_stratum_assignment_hash": self.assignment_hash,
        }
        values.update(overrides)
        return build_strategy_correlation_cross_lag_registry_assignment_adapter(
            values.pop("registry_asset"),
            values.pop("registry_binding_assessment"),
            **values,
        )

    def _assert_locked(self, adapter):
        self.assertTrue(adapter["authority"]["descriptive_only"])
        for key, value in adapter["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)
        self.assertEqual(adapter["permission_state"], "LOCKED")

    def test_valid_registry_chain_derives_exact_assignment_but_not_protocol_maturity(self):
        adapter = self._build()
        self.assertEqual(adapter["schema_version"], ADAPTER_SCHEMA)
        self.assertEqual(adapter["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(adapter["adapter_state"], "REGISTRY_ASSIGNMENT_VERIFIED_CANDIDATE")
        self.assertEqual(adapter["stratum_assignment"], self.assignment)
        self.assertEqual(adapter["stratum_assignment_hash"], self.assignment_hash)
        self.assertEqual(adapter["identity_set"], ["AAA", "BBB"])
        self.assertTrue(adapter["registry_assignment_verified"])
        self.assertFalse(adapter["protocol_registration_bound"])
        self.assertEqual(
            adapter["blockers"],
            ["CROSS_LAG_PROTOCOL_REGISTRATION_UNBOUND"],
        )
        self.assertEqual(
            adapter["analytic_policy"]["lag_direction_convention"],
            "POSITIVE_LAG_MEANS_RIGHT_IDENTITY_FOLLOWS_LEFT_IDENTITY",
        )
        self.assertTrue(adapter["analytic_policy"]["lag_direction_contract_hash"])
        self._assert_locked(adapter)

    def test_derived_assignment_is_exactly_accepted_by_cross_lag_gate(self):
        adapter = self._build()
        lag_fixture = StrategyCorrelationCrossLagGateTests()
        lag_fixture.setUp()
        source_series = lag_fixture._independent_series()
        series = {"AAA": source_series["A"], "BBB": source_series["B"]}
        rows = lag_fixture._rows(series)
        evaluation = evaluate_strategy_correlation_cross_lag_gate(
            adapter["stratum_assignment"],
            rows,
            expected_stratum_assignment_hash=adapter["stratum_assignment_hash"],
        )
        self.assertEqual(evaluation["source_state"], "OBSERVED")
        self.assertTrue(
            verify_strategy_correlation_cross_lag_evaluation(
                evaluation,
                adapter["stratum_assignment"],
                rows,
                expected_stratum_assignment_hash=adapter["stratum_assignment_hash"],
            )
        )

    def test_missing_is_distinct_from_invalid_supplied(self):
        missing = self._build(registry_asset=None, registry_binding_assessment=None)
        invalid = self._build(registry_asset=[], registry_binding_assessment=[])
        self.assertEqual(missing["adapter_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["adapter_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_hash_mismatches_fail_closed(self):
        for field in (
            "expected_registry_asset_hash",
            "expected_classification_source_hash",
            "expected_stratum_assignment_hash",
        ):
            with self.subTest(field=field):
                self.assertEqual(self._build(**{field: "f" * 64})["adapter_state"], "UNKNOWN")

    def test_unknown_dimension_and_invalid_cutoff_fail_closed(self):
        self.assertEqual(self._build(dimension_id="unknown")["adapter_state"], "UNKNOWN")
        self.assertEqual(self._build(selection_cutoff_date="2026/08/02")["adapter_state"], "UNKNOWN")

    def test_frozen_after_first_observation_and_timestamp_drift_fail_closed(self):
        self.assertEqual(
            self._build(first_observation_timestamp="2026-07-31T23:59:59Z")["adapter_state"],
            "UNKNOWN",
        )
        for value in ("2026-08-02", "2026-08-02T00:00:00+00:00", "2026-08-02T00:00:00.000Z"):
            with self.subTest(value=value):
                self.assertEqual(self._build(first_observation_timestamp=value)["adapter_state"], "UNKNOWN")

    def test_resealed_registry_asset_and_binding_tamper_fail_closed(self):
        asset = copy.deepcopy(self.asset)
        asset["effective_date"] = "2026-08-03"
        asset.pop("registry_asset_hash")
        asset = seal_strict_canonical_document(asset, "registry_asset_hash")
        self.assertEqual(
            self._build(registry_asset=asset, expected_registry_asset_hash=asset["registry_asset_hash"])["adapter_state"],
            "UNKNOWN",
        )

        assessment = copy.deepcopy(self.assessment)
        assessment["facts"]["strata_dimensions_bound"] = False
        assessment.pop("assessment_hash")
        assessment = seal_strict_canonical_document(assessment, "assessment_hash")
        self.assertEqual(
            self._build(registry_binding_assessment=assessment)["adapter_state"],
            "UNKNOWN",
        )

    def test_resealed_cluster_topology_and_symbol_drift_fail_closed(self):
        preregistration = copy.deepcopy(self.preregistration)
        preregistration["clusters"][1]["members"] = ["AAA"]
        preregistration.pop("preregistration_hash")
        preregistration = seal_strict_canonical_document(preregistration, "preregistration_hash")
        self.assertEqual(
            self._build(source_preregistration=preregistration)["adapter_state"],
            "UNKNOWN",
        )

        symbols = copy.deepcopy(self.preregistration)
        symbols["symbols"].append("CCC")
        symbols.pop("preregistration_hash")
        symbols = seal_strict_canonical_document(symbols, "preregistration_hash")
        self.assertEqual(self._build(source_preregistration=symbols)["adapter_state"], "UNKNOWN")

    def test_resealed_dimension_topology_drift_fails_closed(self):
        asset = copy.deepcopy(self.asset)
        asset["dimensions"][0]["strata"][1]["cluster_ids"] = ["cluster-aaa"]
        asset.pop("registry_asset_hash")
        asset = seal_strict_canonical_document(asset, "registry_asset_hash")
        self.assertEqual(
            self._build(registry_asset=asset, expected_registry_asset_hash=asset["registry_asset_hash"])["adapter_state"],
            "UNKNOWN",
        )

    def test_authority_aliases_fail_closed(self):
        for value in (0, "", "false"):
            with self.subTest(value=value):
                asset = copy.deepcopy(self.asset)
                asset["permissions"]["paper_authorized"] = value
                asset.pop("registry_asset_hash")
                asset = seal_strict_canonical_document(asset, "registry_asset_hash")
                self.assertEqual(
                    self._build(registry_asset=asset, expected_registry_asset_hash=asset["registry_asset_hash"])["adapter_state"],
                    "UNKNOWN",
                )

    def test_nonfinite_and_pseudo_numeric_policy_inputs_cannot_enter_adapter(self):
        for value in (math.nan, "NaN", True):
            with self.subTest(value=value):
                asset = copy.deepcopy(self.asset)
                asset["methodology"]["selection_returns_used"] = value
                self.assertEqual(
                    self._build(registry_asset=asset, expected_registry_asset_hash=self.asset["registry_asset_hash"])["adapter_state"],
                    "UNKNOWN",
                )

    def test_extra_untrusted_field_is_not_reflected(self):
        asset = copy.deepcopy(self.asset)
        asset["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        asset.pop("registry_asset_hash")
        asset = seal_strict_canonical_document(asset, "registry_asset_hash")
        adapter = self._build(registry_asset=asset, expected_registry_asset_hash=asset["registry_asset_hash"])
        self.assertEqual(adapter["adapter_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", str(adapter))

    def test_registry_verifier_exception_fails_closed(self):
        with patch(
            "exchange_terminal.services.strategy_correlation_cross_lag_registry_assignment_adapter.verify_strategy_correlation_strata_registry_asset",
            side_effect=RuntimeError("adversarial verifier fault"),
        ):
            adapter = self._build()
        self.assertEqual(adapter["adapter_state"], "UNKNOWN")
        self._assert_locked(adapter)

    def test_resealed_adapter_tamper_does_not_verify(self):
        adapter = self._build()
        tampered = copy.deepcopy(adapter)
        tampered["protocol_registration_bound"] = True
        tampered.pop("adapter_hash")
        tampered = seal_strict_canonical_document(tampered, "adapter_hash")
        self.assertFalse(
            verify_strategy_correlation_cross_lag_registry_assignment_adapter(
                tampered,
                self.asset,
                self.assessment,
                source_preregistration=self.preregistration,
                strata_registration=self.registration,
                dimension_id=self.dimension_id,
                selection_cutoff_date=self.selection_cutoff_date,
                first_observation_timestamp=self.first_observation_timestamp,
                expected_registry_asset_hash=self.asset["registry_asset_hash"],
                expected_classification_source_hash=self.registry_fixture.SOURCE_HASH,
                expected_stratum_assignment_hash=self.assignment_hash,
            )
        )

    def test_non_mapping_adapter_never_verifies(self):
        self.assertFalse(
            verify_strategy_correlation_cross_lag_registry_assignment_adapter(
                [],
                self.asset,
                self.assessment,
                source_preregistration=self.preregistration,
                strata_registration=self.registration,
                dimension_id=self.dimension_id,
                selection_cutoff_date=self.selection_cutoff_date,
                first_observation_timestamp=self.first_observation_timestamp,
                expected_registry_asset_hash=self.asset["registry_asset_hash"],
                expected_classification_source_hash=self.registry_fixture.SOURCE_HASH,
                expected_stratum_assignment_hash=self.assignment_hash,
            )
        )


if __name__ == "__main__":
    unittest.main()
