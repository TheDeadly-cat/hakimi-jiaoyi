from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from exchange_terminal.services.strategy_correlation_cross_lag_direction_contract import (
    build_strategy_correlation_cross_lag_direction_contract,
)
from exchange_terminal.services.strategy_correlation_cross_lag_preregistration_adapter_binding import (
    BINDING_SCHEMA,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cross_lag_preregistration_adapter_binding,
    verify_strategy_correlation_cross_lag_preregistration_adapter_binding,
)
from exchange_terminal.services.strategy_correlation_cross_lag_registry_assignment_adapter import (
    build_strategy_correlation_cross_lag_registry_assignment_adapter,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
)
from exchange_terminal.services.strategy_correlation_strata_protocol import (
    build_strategy_correlation_strata_protocol_registration,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from tests.test_strategy_correlation_strata_protocol import (
    StrategyCorrelationStrataProtocolTests,
)
from tests.test_strategy_correlation_strata_registry import (
    StrategyCorrelationStrataRegistryTests,
)


class StrategyCorrelationCrossLagPreregistrationAdapterBindingTests(unittest.TestCase):
    CLASSIFICATION_HASH = "c" * 64

    def setUp(self):
        protocol_fixture = StrategyCorrelationStrataProtocolTests()
        _, source_v6 = protocol_fixture._source_v6()
        self.protocol = build_strategy_correlation_strata_protocol_registration(source_v6)
        self.preregistration = (
            self.protocol["source_registration"]["source_registration"]
            ["source_protocol_registration"]["preregistration"]
        )
        self.dimension_id = "cross-lag-protocol-strata"
        strata = []
        self.assignment = {}
        for index, cluster in enumerate(self.preregistration["clusters"], start=1):
            stratum_id = f"protocol-stratum-{index:02d}"
            strata.append({"stratum_id": stratum_id, "cluster_ids": [cluster["cluster_id"]]})
            for identity in cluster["members"]:
                self.assignment[identity] = stratum_id
        self.assignment = {identity: self.assignment[identity] for identity in sorted(self.assignment)}
        self.assignment_hash = strict_canonical_hash(self.assignment)
        self.dimensions = [{"dimension_id": self.dimension_id, "strata": strata}]
        self.strata_registration = build_strategy_correlation_strata_preregistration(
            self.preregistration,
            self.dimensions,
        )
        self.asset = build_strategy_correlation_strata_registry_asset(
            self.preregistration,
            self.dimensions,
            registry_id="cross-lag-protocol-registry-candidate-1",
            classification_source="synthetic-protocol-classification",
            classification_source_version="2026-07-31",
            classification_source_hash=self.CLASSIFICATION_HASH,
            effective_date="2026-07-31",
            frozen_at="2026-08-01T00:00:00Z",
        )
        self.selection_cutoff_date = "2026-08-02"
        self.first_observation_timestamp = "2026-08-02T00:00:00Z"
        self.assessment = assess_strategy_correlation_strata_registry_binding(
            self.asset,
            self.strata_registration,
            self.preregistration,
            selection_cutoff_date=self.selection_cutoff_date,
            expected_registry_asset_hash=self.asset["registry_asset_hash"],
            expected_classification_source_hash=self.CLASSIFICATION_HASH,
        )
        self.direction = build_strategy_correlation_cross_lag_direction_contract()
        self.adapter = build_strategy_correlation_cross_lag_registry_assignment_adapter(
            self.asset,
            self.assessment,
            source_preregistration=self.preregistration,
            strata_registration=self.strata_registration,
            dimension_id=self.dimension_id,
            selection_cutoff_date=self.selection_cutoff_date,
            first_observation_timestamp=self.first_observation_timestamp,
            expected_registry_asset_hash=self.asset["registry_asset_hash"],
            expected_classification_source_hash=self.CLASSIFICATION_HASH,
            expected_stratum_assignment_hash=self.assignment_hash,
        )

    def _values(self):
        return {
            "strata_protocol_registration": self.protocol,
            "registry_assignment_adapter": self.adapter,
            "direction_contract": self.direction,
            "source_preregistration": self.preregistration,
            "strata_registration": self.strata_registration,
            "registry_asset": self.asset,
            "registry_binding_assessment": self.assessment,
            "dimension_id": self.dimension_id,
            "selection_cutoff_date": self.selection_cutoff_date,
            "first_observation_timestamp": self.first_observation_timestamp,
            "expected_strata_protocol_registration_hash": self.protocol["registration_hash"],
            "expected_registry_assignment_adapter_hash": self.adapter["adapter_hash"],
            "expected_direction_contract_hash": self.direction["contract_hash"],
            "expected_registry_asset_hash": self.asset["registry_asset_hash"],
            "expected_classification_source_hash": self.CLASSIFICATION_HASH,
            "expected_stratum_assignment_hash": self.assignment_hash,
        }

    def _build(self, **overrides):
        values = self._values()
        values.update(overrides)
        return build_strategy_correlation_cross_lag_preregistration_adapter_binding(
            values.pop("strata_protocol_registration"),
            values.pop("registry_assignment_adapter"),
            values.pop("direction_contract"),
            **values,
        )

    def _verify(self, document, **overrides):
        values = self._values()
        values.update(overrides)
        return verify_strategy_correlation_cross_lag_preregistration_adapter_binding(
            document,
            values.pop("strata_protocol_registration"),
            values.pop("registry_assignment_adapter"),
            values.pop("direction_contract"),
            **values,
        )

    def _assert_locked(self, document):
        self.assertTrue(document["authority"]["descriptive_only"])
        for key, value in document["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_valid_same_source_binding_is_candidate_not_formal(self):
        binding = self._build()
        self.assertEqual(binding["schema_version"], BINDING_SCHEMA)
        self.assertEqual(binding["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(binding["binding_state"], "PREREGISTRATION_ADAPTER_VERIFIED_CANDIDATE")
        self.assertEqual(binding["maturity_state"], "CANDIDATE_PROTOCOL_AND_REGISTRY_BOUND_NOT_FORMAL")
        self.assertEqual(binding["cluster_preregistration_hash"], self.preregistration["preregistration_hash"])
        self.assertTrue(all(binding["facts"].values()))
        self.assertEqual(binding["blockers"], ["CROSS_LAG_C2_PROTOCOL_NOT_IMPLEMENTED"])
        self._assert_locked(binding)

    def test_valid_binding_exactly_verifies_and_redacts_identity_mapping(self):
        binding = self._build()
        self.assertTrue(self._verify(binding))
        self.assertNotIn("stratum_assignment", binding)
        self.assertNotIn("identity_set", binding)

    def test_missing_is_distinct_from_invalid_supplied(self):
        missing = self._build(
            strata_protocol_registration=None,
            registry_assignment_adapter=None,
            direction_contract=None,
        )
        invalid = self._build(
            strata_protocol_registration=[],
            registry_assignment_adapter=[],
            direction_contract=[],
        )
        self.assertEqual(missing["binding_state"], "NOT_SUPPLIED")
        self.assertEqual(invalid["binding_state"], "UNKNOWN")
        self._assert_locked(missing)
        self._assert_locked(invalid)

    def test_expected_hash_mismatches_fail_closed(self):
        for field in (
            "expected_strata_protocol_registration_hash",
            "expected_registry_assignment_adapter_hash",
            "expected_direction_contract_hash",
            "expected_registry_asset_hash",
            "expected_classification_source_hash",
            "expected_stratum_assignment_hash",
        ):
            with self.subTest(field=field):
                self.assertEqual(self._build(**{field: "f" * 64})["binding_state"], "UNKNOWN")

    def test_unrelated_but_valid_registry_source_is_rejected(self):
        other = StrategyCorrelationStrataRegistryTests()
        other.setUp()
        preregistration, _, registration, asset = other._source()
        assessment = other._assessment(preregistration, registration, asset)
        assignment = {"AAA": "sector-a", "BBB": "sector-b"}
        assignment_hash = strict_canonical_hash(assignment)
        adapter = build_strategy_correlation_cross_lag_registry_assignment_adapter(
            asset,
            assessment,
            source_preregistration=preregistration,
            strata_registration=registration,
            dimension_id="sector",
            selection_cutoff_date="2026-08-02",
            first_observation_timestamp="2026-08-02T00:00:00Z",
            expected_registry_asset_hash=asset["registry_asset_hash"],
            expected_classification_source_hash=other.SOURCE_HASH,
            expected_stratum_assignment_hash=assignment_hash,
        )
        binding = self._build(
            registry_assignment_adapter=adapter,
            source_preregistration=preregistration,
            strata_registration=registration,
            registry_asset=asset,
            registry_binding_assessment=assessment,
            dimension_id="sector",
            expected_registry_assignment_adapter_hash=adapter["adapter_hash"],
            expected_registry_asset_hash=asset["registry_asset_hash"],
            expected_classification_source_hash=other.SOURCE_HASH,
            expected_stratum_assignment_hash=assignment_hash,
        )
        self.assertEqual(binding["binding_state"], "UNKNOWN")

    def test_coherently_resealed_protocol_adapter_and_direction_tamper_fail_closed(self):
        variants = []
        protocol = copy.deepcopy(self.protocol)
        protocol["cluster_preregistration_hash"] = "d" * 64
        protocol.pop("registration_hash")
        protocol = seal_strict_canonical_document(protocol, "registration_hash")
        variants.append(("strata_protocol_registration", protocol, "expected_strata_protocol_registration_hash", protocol["registration_hash"]))
        adapter = copy.deepcopy(self.adapter)
        adapter["source_preregistration_hash"] = "d" * 64
        adapter.pop("adapter_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_hash")
        variants.append(("registry_assignment_adapter", adapter, "expected_registry_assignment_adapter_hash", adapter["adapter_hash"]))
        direction = copy.deepcopy(self.direction)
        direction["lag_direction_convention"] = "POSITIVE_LAG_MEANS_LEFT_FOLLOWS_RIGHT"
        direction.pop("contract_hash")
        direction = seal_strict_canonical_document(direction, "contract_hash")
        variants.append(("direction_contract", direction, "expected_direction_contract_hash", direction["contract_hash"]))
        for source_field, source, hash_field, source_hash in variants:
            with self.subTest(source_field=source_field):
                binding = self._build(**{source_field: source, hash_field: source_hash})
                self.assertEqual(binding["binding_state"], "UNKNOWN")

    def test_underlying_temporal_replay_mismatch_fails_closed(self):
        binding = self._build(first_observation_timestamp="2026-07-31T23:59:59Z")
        self.assertEqual(binding["binding_state"], "UNKNOWN")

    def test_authority_aliases_fail_closed(self):
        for value in (0, "", "false", True):
            with self.subTest(value=value):
                protocol = copy.deepcopy(self.protocol)
                protocol["permissions"]["paper_authorized"] = value
                protocol.pop("registration_hash")
                protocol = seal_strict_canonical_document(protocol, "registration_hash")
                binding = self._build(
                    strata_protocol_registration=protocol,
                    expected_strata_protocol_registration_hash=protocol["registration_hash"],
                )
                self.assertEqual(binding["binding_state"], "UNKNOWN")

    def test_adapter_blocker_drift_fails_closed(self):
        adapter = copy.deepcopy(self.adapter)
        adapter["blockers"] = []
        adapter.pop("adapter_hash")
        adapter = seal_strict_canonical_document(adapter, "adapter_hash")
        binding = self._build(
            registry_assignment_adapter=adapter,
            expected_registry_assignment_adapter_hash=adapter["adapter_hash"],
        )
        self.assertEqual(binding["binding_state"], "UNKNOWN")

    def test_extra_untrusted_source_field_is_not_reflected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["untrusted"] = "PRIVATE-DO-NOT-REFLECT"
        protocol.pop("registration_hash")
        protocol = seal_strict_canonical_document(protocol, "registration_hash")
        binding = self._build(
            strata_protocol_registration=protocol,
            expected_strata_protocol_registration_hash=protocol["registration_hash"],
        )
        self.assertEqual(binding["binding_state"], "UNKNOWN")
        self.assertNotIn("PRIVATE-DO-NOT-REFLECT", str(binding))

    def test_protocol_verifier_exception_fails_closed(self):
        with patch(
            "exchange_terminal.services.strategy_correlation_cross_lag_preregistration_adapter_binding.verify_strategy_correlation_strata_protocol_registration",
            side_effect=RuntimeError("adversarial verifier fault"),
        ):
            binding = self._build()
        self.assertEqual(binding["binding_state"], "UNKNOWN")
        self._assert_locked(binding)

    def test_resealed_binding_tamper_does_not_verify(self):
        binding = self._build()
        tampered = copy.deepcopy(binding)
        self.assertFalse(tampered["authority"]["formal_preregistration_bound"])
        tampered["authority"]["formal_preregistration_bound"] = True
        tampered.pop("binding_hash")
        tampered = seal_strict_canonical_document(tampered, "binding_hash")
        self.assertFalse(self._verify(tampered))

    def test_non_mapping_binding_never_verifies(self):
        self.assertFalse(self._verify([]))

    def test_output_contains_no_returns_observations_or_local_paths(self):
        binding = self._build()
        encoded = str(binding).lower()
        for forbidden in ("return_series", "aligned_observations", "local_path", "file://", "http://"):
            self.assertNotIn(forbidden, encoded)

    def test_protocol_and_adapter_hashes_are_both_bound(self):
        binding = self._build()
        self.assertEqual(binding["strata_protocol_registration_hash"], self.protocol["registration_hash"])
        self.assertEqual(binding["registry_assignment_adapter_hash"], self.adapter["adapter_hash"])
        self.assertEqual(binding["direction_contract_hash"], self.direction["contract_hash"])


if __name__ == "__main__":
    unittest.main()
