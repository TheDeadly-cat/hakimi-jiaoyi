from __future__ import annotations

import copy
import importlib
import unittest

from exchange_terminal.services.strategy_correlation_cluster_stability_formal_registry_adapter import (
    STATUS_CANDIDATE_RECORD_VERIFIED,
    STATUS_DRIFT,
    STATUS_DUPLICATE,
    STATUS_MISSING,
    STATUS_UNKNOWN,
    InMemoryFormalRegistryReadAdapter,
    assess_strategy_correlation_cluster_stability_formal_registry_read,
    build_strategy_correlation_cluster_stability_formal_registry_read_record,
    verify_strategy_correlation_cluster_stability_formal_registry_read_assessment,
    verify_strategy_correlation_cluster_stability_formal_registry_read_record,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_registry_projection import (
    project_strategy_correlation_cluster_stability_registry_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_projection_test_module = importlib.import_module(
    "tests.test_strategy_correlation_cluster_stability_registry_projection"
)


class StrategyCorrelationClusterStabilityFormalRegistryAdapterTests(unittest.TestCase):
    def _fixture(self):
        case_type = getattr(
            _projection_test_module,
            "StrategyCorrelationClusterStabilityRegistryProjectionTests",
        )
        case = case_type(
            methodName="test_valid_candidate_binding_projects_candidate_only"
        )
        _, protocol, asset, binding, external = case._fixture()
        record_inputs = {
            "registry_id": asset["registry_id"],
            "formal_registry_source": "synthetic-formal-registry-read-fixture",
            "formal_registry_source_version": "fixture-v1",
            "formal_registry_source_hash": "c" * 64,
            "registry_snapshot_hash": "d" * 64,
            "effective_date": "2026-08-19",
            "frozen_at": "2026-08-20T00:00:00Z",
        }
        return protocol, asset, binding, external, record_inputs

    def _record(self, *, protocol=None, asset=None, binding=None, **overrides):
        base_protocol, base_asset, base_binding, _, record_inputs = self._fixture()
        values = {**record_inputs, **overrides}
        return build_strategy_correlation_cluster_stability_formal_registry_read_record(
            base_protocol if protocol is None else protocol,
            base_asset if asset is None else asset,
            base_binding if binding is None else binding,
            **values,
        )

    def _assessment(self, adapter, *, protocol=None, asset=None, binding=None, **overrides):
        base_protocol, base_asset, base_binding, external, record_inputs = self._fixture()
        values = {
            "expected_adapter_snapshot_hash": adapter.snapshot_hash,
            **external,
            **record_inputs,
            **overrides,
        }
        values.pop("protocol_registration", None)
        return assess_strategy_correlation_cluster_stability_formal_registry_read(
            adapter,
            protocol_registration=base_protocol if protocol is None else protocol,
            registry_asset=base_asset if asset is None else asset,
            binding_assessment=base_binding if binding is None else binding,
            **values,
        )

    def _verify_assessment(
        self,
        adapter,
        assessment,
        *,
        protocol=None,
        asset=None,
        binding=None,
        **overrides,
    ):
        base_protocol, base_asset, base_binding, external, record_inputs = self._fixture()
        values = {
            "expected_adapter_snapshot_hash": adapter.snapshot_hash,
            **external,
            **record_inputs,
            **overrides,
        }
        values.pop("protocol_registration", None)
        return verify_strategy_correlation_cluster_stability_formal_registry_read_assessment(
            assessment,
            adapter=adapter,
            protocol_registration=base_protocol if protocol is None else protocol,
            registry_asset=base_asset if asset is None else asset,
            binding_assessment=base_binding if binding is None else binding,
            **values,
        )

    def test_valid_unique_record_is_candidate_verified_but_not_formal(self):
        protocol, asset, binding, external, record_inputs = self._fixture()
        record = self._record()
        candidate_bindings = dict(external)
        candidate_bindings.pop("protocol_registration", None)
        record_verification = (
            verify_strategy_correlation_cluster_stability_formal_registry_read_record(
                record,
                protocol_registration=protocol,
                registry_asset=asset,
                binding_assessment=binding,
                **candidate_bindings,
                **record_inputs,
            )
        )
        self.assertEqual(record_verification["status"], "PASS")
        adapter = InMemoryFormalRegistryReadAdapter([record])
        assessment = self._assessment(adapter)
        verification = self._verify_assessment(adapter, assessment)
        self.assertEqual(assessment["status"], STATUS_CANDIDATE_RECORD_VERIFIED)
        self.assertEqual(assessment["lookup_cardinality"], 1)
        self.assertIs(assessment["candidate_record_verified"], True)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(
            verification["decision_status"], STATUS_CANDIDATE_RECORD_VERIFIED
        )
        self._assert_not_formal(assessment)
        self._assert_not_formal(verification)

    def test_missing_record_is_explicit(self):
        adapter = InMemoryFormalRegistryReadAdapter([])
        assessment = self._assessment(adapter)
        self.assertEqual(assessment["status"], STATUS_MISSING)
        self.assertEqual(assessment["lookup_cardinality"], 0)
        self.assertIs(assessment["read_performed"], True)
        self.assertEqual(self._verify_assessment(adapter, assessment)["status"], "PASS")
        self._assert_not_formal(assessment)

    def test_duplicate_record_is_explicit_and_never_selects_one(self):
        record = self._record()
        adapter = InMemoryFormalRegistryReadAdapter([record, record])
        assessment = self._assessment(adapter)
        self.assertEqual(assessment["status"], STATUS_DUPLICATE)
        self.assertEqual(assessment["lookup_cardinality"], 2)
        self.assertIs(assessment["record_verified"], False)
        self.assertIsNone(assessment["observed_record_hash"])
        self._assert_not_formal(assessment)

    def test_formal_source_hash_drift_blocks_unique_record(self):
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(adapter, formal_registry_source_hash="e" * 64)
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self.assertEqual(assessment["record_verification_status"], "BLOCK")
        self._assert_not_formal(assessment)

    def test_registry_snapshot_hash_drift_blocks_unique_record(self):
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(adapter, registry_snapshot_hash="e" * 64)
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self._assert_not_formal(assessment)

    def test_adapter_snapshot_hash_drift_blocks_before_lookup(self):
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(
            adapter,
            expected_adapter_snapshot_hash="e" * 64,
        )
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self.assertIs(assessment["read_performed"], False)
        self.assertIsNone(assessment["lookup_cardinality"])
        self.assertIn("ADAPTER_SNAPSHOT_MISMATCH", assessment["blockers"])

    def test_candidate_asset_hash_drift_blocks_unique_record(self):
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(
            adapter,
            expected_registry_asset_hash="e" * 64,
        )
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self._assert_not_formal(assessment)

    def test_resealed_candidate_binding_attack_blocks_unique_record(self):
        _, _, binding, _, _ = self._fixture()
        attacked = copy.deepcopy(binding)
        attacked["status"] = "FORMAL_BOUND"
        attacked = seal_strict_canonical_document(attacked, "assessment_hash")
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(adapter, binding=attacked)
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self._assert_not_formal(assessment)

    def test_record_dates_must_precede_evidence_cutoff(self):
        record = self._record(effective_date="2026-08-21")
        adapter = InMemoryFormalRegistryReadAdapter([record])
        assessment = self._assessment(adapter, effective_date="2026-08-21")
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self._assert_not_formal(assessment)

    def test_constructor_isolated_from_caller_mutation(self):
        record = self._record()
        records = [record]
        adapter = InMemoryFormalRegistryReadAdapter(records)
        frozen_hash = adapter.snapshot_hash
        records[0]["status"] = "MUTATED"
        records.append(copy.deepcopy(record))
        observed = adapter.lookup(record["registry_id"])
        self.assertEqual(adapter.record_count, 1)
        self.assertEqual(adapter.snapshot_hash, frozen_hash)
        self.assertEqual(observed[0]["status"], "FROZEN_READ_RECORD")

    def test_lookup_result_is_copy_on_read(self):
        record = self._record()
        adapter = InMemoryFormalRegistryReadAdapter([record])
        first = adapter.lookup(record["registry_id"])
        first[0]["status"] = "MUTATED"
        second = adapter.lookup(record["registry_id"])
        self.assertEqual(second[0]["status"], "FROZEN_READ_RECORD")
        self.assertEqual(adapter.snapshot_hash, adapter.snapshot_hash)

    def test_resealed_authority_alias_in_record_is_drift(self):
        attacked = copy.deepcopy(self._record())
        attacked["formal_registry_bound"] = 0
        attacked = seal_strict_canonical_document(attacked, "record_hash")
        adapter = InMemoryFormalRegistryReadAdapter([attacked])
        assessment = self._assessment(adapter)
        self.assertEqual(assessment["status"], STATUS_DRIFT)
        self._assert_not_formal(assessment)

    def test_resealed_assessment_cannot_claim_formal_status(self):
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(adapter)
        attacked = copy.deepcopy(assessment)
        attacked["status"] = "FORMAL_BOUND"
        attacked["formal_registry_bound"] = True
        attacked = seal_strict_canonical_document(attacked, "assessment_hash")
        verification = self._verify_assessment(adapter, attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIs(verification["formal_registry_bound"], False)

    def test_non_adapter_input_is_unknown_without_read(self):
        protocol, asset, binding, external, record_inputs = self._fixture()
        candidate_bindings = dict(external)
        candidate_bindings.pop("protocol_registration", None)
        assessment = assess_strategy_correlation_cluster_stability_formal_registry_read(
            object(),
            expected_adapter_snapshot_hash="e" * 64,
            protocol_registration=protocol,
            registry_asset=asset,
            binding_assessment=binding,
            **candidate_bindings,
            **record_inputs,
        )
        self.assertEqual(assessment["status"], STATUS_UNKNOWN)
        self.assertIs(assessment["read_performed"], False)
        self._assert_not_formal(assessment)

    def test_nonfinite_adapter_input_is_rejected(self):
        with self.assertRaises((TypeError, ValueError)):
            InMemoryFormalRegistryReadAdapter([{"value": float("nan")}])

    def test_verified_read_record_does_not_activate_public_projection(self):
        protocol, asset, binding, external, _ = self._fixture()
        adapter = InMemoryFormalRegistryReadAdapter([self._record()])
        assessment = self._assessment(adapter)
        self.assertEqual(assessment["status"], STATUS_CANDIDATE_RECORD_VERIFIED)
        public = project_strategy_correlation_cluster_stability_registry_summary(
            asset,
            binding,
            **external,
        )
        self.assertEqual(public["projection_state"], "CANDIDATE_BOUND")
        self.assertEqual(public["gap"]["formal_registry"], "MISSING")
        self.assertIs(public["permission"]["formal_registry_bound"], False)

    def _assert_not_formal(self, value):
        self.assertIs(value["formal_persistence_verified"], False)
        self.assertIs(value["formal_registry_bound"], False)
        self.assertIs(value["formal_registry_activation_allowed"], False)
        self.assertIs(value["writer_implemented"], False)
        self.assertIs(value["current_writer_activation_allowed"], False)
        self.assertIs(value["current_admission_allowed"], False)
        self.assertIs(value["permissions"]["paper_authorized"], False)
        self.assertIs(value["permissions"]["live_order_allowed"], False)


if __name__ == "__main__":
    unittest.main()
