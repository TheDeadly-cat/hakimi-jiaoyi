from __future__ import annotations

from copy import deepcopy
import json
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_report_extension,
)
from tests.test_strategy_correlation_cluster_temporal_date_grid_report_binding import (
    StrategyCorrelationClusterTemporalDateGridReportBindingTests,
)


class StrategyCorrelationClusterTemporalDateGridReportConsumerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.binding_case = (
            StrategyCorrelationClusterTemporalDateGridReportBindingTests(
                methodName=(
                    "test_aligned_report21_is_candidate_bound_with_date_grid_pass"
                )
            )
        )
        self.binding_case.setUp()
        self.addCleanup(self.binding_case.doCleanups)

    def _arguments(self, *, misaligned=False):
        if misaligned:
            arguments, _ = self.binding_case._misaligned_arguments()
            return arguments
        return self.binding_case.source_case._arguments()

    def _fixture(self, *, misaligned=False):
        arguments = self._arguments(misaligned=misaligned)
        report21 = arguments["report21_extension"]
        entry = report21["entries"][0]
        gate = self.binding_case._date_grid_gate(arguments)
        date_grid_binding = {
            "strategy_id": entry["strategy_id"],
            "variant_id": entry["variant_id"],
            "lane": entry["lane"],
            "expected_temporal_date_grid_gate_hash": gate["gate_hash"],
        }
        decision_blockers = []
        if report21["decision"] != "PASS":
            decision_blockers.append("base_report21_decision_blocked")
        if gate["status"] != "PASS":
            decision_blockers.append(
                "temporal_date_grid_gate_blocked:"
                + ":".join(
                    (entry["strategy_id"], entry["variant_id"], entry["lane"])
                )
            )
        extension = seal_strict_canonical_document(
            {
                "schema_version": EXTENSION_SCHEMA_VERSION,
                "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
                "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
                "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
                "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
                "source_base_report_hash": arguments[
                    "expected_base_report_hash"
                ],
                "base_report21_extension": report21,
                "base_report21_extension_hash": report21["extension_hash"],
                "registry_bindings_required": True,
                "stability_bindings_required": True,
                "temporal_stability_bindings_required": True,
                "temporal_date_grid_gate_required": True,
                "external_temporal_date_grid_bindings_required": True,
                "entries": [
                    {
                        "strategy_id": entry["strategy_id"],
                        "variant_id": entry["variant_id"],
                        "lane": entry["lane"],
                        "temporal_date_grid_gate": gate,
                        "temporal_date_grid_gate_hash": gate["gate_hash"],
                    }
                ],
                "decision": "PASS" if not decision_blockers else "BLOCK",
                "decision_blockers": decision_blockers,
                "consumer_only": True,
                "requires_new_report_schema": True,
                "writer_available": False,
                "current_admission_allowed": False,
                "current_writer_activation_allowed": False,
                "permissions": {
                    "paper_authorized": False,
                    "live_order_allowed": False,
                },
            },
            "extension_hash",
        )
        return extension, arguments, date_grid_binding

    def _verify(
        self,
        values,
        document=None,
        *,
        date_grid_bindings=None,
        expected_report21_hash=None,
    ):
        extension, arguments, date_grid_binding = values
        return (
            verify_strategy_correlation_cluster_temporal_date_grid_report_extension(
                extension if document is None else document,
                expected_base_report_hash=arguments["expected_base_report_hash"],
                expected_global_independence_extension_hash=arguments[
                    "expected_global_independence_extension_hash"
                ],
                expected_cluster_stability_extension_hash=arguments[
                    "expected_cluster_stability_extension_hash"
                ],
                expected_report21_extension_hash=(
                    arguments["expected_report21_extension_hash"]
                    if expected_report21_hash is None
                    else expected_report21_hash
                ),
                expected_registry_bindings=arguments[
                    "expected_registry_bindings"
                ],
                expected_stability_bindings=arguments[
                    "expected_stability_bindings"
                ],
                expected_temporal_stability_bindings=arguments[
                    "expected_temporal_stability_bindings"
                ],
                expected_temporal_date_grid_bindings=(
                    [date_grid_binding]
                    if date_grid_bindings is None
                    else date_grid_bindings
                ),
            )
        )

    def test_report21_remains_valid_without_date_grid_payload(self):
        _, arguments, _ = self._fixture()
        report21 = arguments["report21_extension"]
        self.assertEqual(report21["decision"], "PASS")
        self.assertNotIn(
            "date_grid",
            json.dumps(report21, sort_keys=True).lower(),
        )

    def test_valid_report22_passes_contract_and_decision(self):
        values = self._fixture()
        verification = self._verify(values)
        self.assertEqual(values[0]["decision"], "PASS")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(verification["date_grid_gate_count"], 1)
        self.assertEqual(verification["date_grid_gate_pass_count"], 1)
        self.assertFalse(verification["writer_available"])

    def test_misaligned_report22_is_valid_contract_with_block_decision(self):
        values = self._fixture(misaligned=True)
        gate = values[0]["entries"][0]["temporal_date_grid_gate"]
        verification = self._verify(values)
        self.assertEqual(
            values[0]["base_report21_extension"]["decision"],
            "PASS",
        )
        self.assertEqual(gate["status"], "BLOCK")
        self.assertEqual(values[0]["decision"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(verification["date_grid_gate_pass_count"], 0)

    def test_resealed_pass_cannot_override_blocked_date_grid_gate(self):
        values = self._fixture(misaligned=True)
        attacked = deepcopy(values[0])
        attacked["decision"] = "PASS"
        attacked["decision_blockers"] = []
        attacked = seal_strict_canonical_document(
            attacked,
            "extension_hash",
        )
        verification = self._verify(values, attacked)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertEqual(verification["decision"], "BLOCK")

    def test_missing_or_wrong_date_grid_binding_blocks_contract(self):
        values = self._fixture()
        missing = self._verify(values, date_grid_bindings=[])
        wrong_binding = deepcopy(values[2])
        wrong_binding["expected_temporal_date_grid_gate_hash"] = "e" * 64
        wrong = self._verify(values, date_grid_bindings=[wrong_binding])
        self.assertEqual(missing["status"], "BLOCK")
        self.assertIn(
            "temporal_date_grid_identity_set_mismatch",
            missing["blockers"],
        )
        self.assertEqual(wrong["status"], "BLOCK")
        self.assertTrue(
            any(
                item.startswith("temporal_date_grid_gate_hash_mismatch:")
                for item in wrong["blockers"]
            )
        )

    def test_duplicate_date_grid_binding_is_rejected(self):
        values = self._fixture()
        verification = self._verify(
            values,
            date_grid_bindings=[values[2], deepcopy(values[2])],
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn(
            "temporal_date_grid_bindings_invalid",
            verification["blockers"],
        )

    def test_report21_hash_and_identity_drift_block_contract(self):
        values = self._fixture()
        wrong_hash = self._verify(
            values,
            expected_report21_hash="d" * 64,
        )
        drifted = deepcopy(values[0])
        drifted["entries"][0]["strategy_id"] = "DRIFT"
        drifted = seal_strict_canonical_document(
            drifted,
            "extension_hash",
        )
        identity_drift = self._verify(values, drifted)
        self.assertEqual(wrong_hash["status"], "BLOCK")
        self.assertIn(
            "report21_extension_hash_mismatch",
            wrong_hash["blockers"],
        )
        self.assertEqual(identity_drift["status"], "BLOCK")
        self.assertIn(
            "temporal_date_grid_identity_set_mismatch",
            identity_drift["blockers"],
        )

    def test_resealed_gate_type_alias_is_independently_rejected(self):
        values = self._fixture()
        attacked = deepcopy(values[0])
        gate = attacked["entries"][0]["temporal_date_grid_gate"]
        gate["consumer_only"] = 1
        gate = seal_strict_canonical_document(gate, "gate_hash")
        attacked["entries"][0]["temporal_date_grid_gate"] = gate
        attacked["entries"][0]["temporal_date_grid_gate_hash"] = gate[
            "gate_hash"
        ]
        attacked = seal_strict_canonical_document(
            attacked,
            "extension_hash",
        )
        binding = deepcopy(values[2])
        binding["expected_temporal_date_grid_gate_hash"] = gate["gate_hash"]
        verification = self._verify(
            values,
            attacked,
            date_grid_bindings=[binding],
        )
        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(
                item.startswith("temporal_date_grid_gate_invalid:")
                for item in verification["blockers"]
            )
        )

    def test_entry_excludes_external_replay_assets_and_raw_dates(self):
        entry = self._fixture()[0]["entries"][0]
        self.assertEqual(
            set(entry),
            {
                "strategy_id",
                "variant_id",
                "lane",
                "temporal_date_grid_gate",
                "temporal_date_grid_gate_hash",
            },
        )
        def nested_keys(value):
            if type(value) is dict:
                for key, nested in value.items():
                    yield key
                    yield from nested_keys(nested)
            elif type(value) is list:
                for nested in value:
                    yield from nested_keys(nested)

        keys = set(nested_keys(entry))
        self.assertNotIn("source_uncertainty_audit", keys)
        self.assertNotIn("correlation_matrix", keys)
        self.assertNotIn("selection_cells", keys)
        self.assertNotIn("price_rows", keys)

    def test_root_alias_authority_and_exports_fail_closed(self):
        values = self._fixture()
        alias = deepcopy(values[0])
        alias["target_report_schema_version"] = 22.0
        alias = seal_strict_canonical_document(alias, "extension_hash")
        authority = deepcopy(values[0])
        authority["permissions"]["live_order_allowed"] = True
        authority = seal_strict_canonical_document(
            authority,
            "extension_hash",
        )
        alias_verification = self._verify(values, alias)
        authority_verification = self._verify(values, authority)
        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(authority_verification["status"], "BLOCK")
        self.assertIn(
            "research_authority_violation",
            authority_verification["blockers"],
        )
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_report_consumer as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("build_report22", exports)
        self.assertNotIn("write_report22", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
