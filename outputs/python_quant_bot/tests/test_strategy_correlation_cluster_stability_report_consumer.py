from copy import deepcopy
import json
import math
import unittest
from unittest.mock import patch

from tests import test_strategy_correlation_global_independence_report_consumer as report19_fixtures
from tests import test_strategy_correlation_uncertainty_audit as uncertainty_fixtures

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_gate import (
    build_correlation_cluster_preregistration,
    build_correlation_matrix_contract,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    evaluate_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_stability_report_extension,
)
from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    verify_strategy_correlation_global_independence_report_extension,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)


class StrategyCorrelationClusterStabilityReportConsumerTests(unittest.TestCase):
    def setUp(self):
        self.uncertainty_fixture = uncertainty_fixtures.StrategyCorrelationUncertaintyAuditTests(
            methodName="runTest"
        )
        self.uncertainty_fixture.setUp()

    def tearDown(self):
        self.uncertainty_fixture.tearDown()

    def _source_inputs(self, *, low_effective_sample=False):
        clusters = [
            {"cluster_id": "cluster-aaa", "members": ["AAA"]},
            {"cluster_id": "cluster-bbb", "members": ["BBB"]},
            {"cluster_id": "cluster-ccc", "members": ["CCC"]},
        ]
        preregistration = build_correlation_cluster_preregistration(clusters)
        if low_effective_sample:
            returns = {
                "AAA": [math.sin(2.0 * math.pi * i / 60.0) for i in range(60)],
                "BBB": [math.cos(2.0 * math.pi * i / 60.0) for i in range(60)],
                "CCC": [math.sin(4.0 * math.pi * i / 60.0) for i in range(60)],
            }
        else:
            returns = {
                "AAA": self.uncertainty_fixture._normal(501),
                "BBB": self.uncertainty_fixture._normal(502),
                "CCC": self.uncertainty_fixture._normal(503),
            }
        replay = self.uncertainty_fixture._replay(returns, clusters)
        replay["preregistration"] = preregistration
        source_audit = build_strategy_correlation_uncertainty_audit(replay)
        correlations = {
            (pair["left_symbol"], pair["right_symbol"]): pair["correlation"]
            for pair in source_audit["pairs"]
        }
        overlaps = {
            (pair["left_symbol"], pair["right_symbol"]): pair[
                "overlap_observations"
            ]
            for pair in source_audit["pairs"]
        }
        matrix = build_correlation_matrix_contract(
            ["AAA", "BBB", "CCC"],
            correlations,
            overlap_observations=overlaps,
        )
        return preregistration, source_audit, matrix

    def _fixture(self, *, low_effective_sample=False):
        preregistration, source_audit, matrix = self._source_inputs(
            low_effective_sample=low_effective_sample
        )
        captured: dict[str, object] = {}
        original_evaluate = report19_fixtures.evaluate_correlation_cluster_gate_v2

        def capture_evaluate(
            source_preregistration,
            correlation_matrix,
            selection_cells,
            **identity,
        ):
            captured["selection_cells"] = deepcopy(selection_cells)
            return original_evaluate(
                source_preregistration,
                correlation_matrix,
                selection_cells,
                **identity,
            )

        report19_fixture = (
            report19_fixtures.StrategyCorrelationGlobalIndependenceReportConsumerTests(
                methodName="runTest"
            )
        )
        with patch.object(
            report19_fixtures,
            "build_correlation_matrix_contract",
            return_value=matrix,
        ), patch.object(
            report19_fixtures,
            "evaluate_correlation_cluster_gate_v2",
            side_effect=capture_evaluate,
        ):
            report18, registry_binding = report19_fixture._fixture(cycle=False)
        report19 = report19_fixture._extension(report18)
        report19_verification = verify_strategy_correlation_global_independence_report_extension(
            report19,
            expected_base_report_hash=report19["base_report_hash"],
            expected_registry_bindings=[registry_binding],
        )
        self.assertEqual(report19_verification["status"], "PASS")
        self.assertEqual(report19_verification["decision"], "PASS")
        entry = report19["entries"][0]
        self.assertTrue(
            strict_json_contract_equal(entry["source_preregistration"], preregistration)
        )
        selection_cells = captured["selection_cells"]
        stability_gate = evaluate_strategy_correlation_cluster_stability_gate(
            source_audit,
            entry["complete_link_gate"],
            preregistration=entry["source_preregistration"],
            correlation_matrix=matrix,
            selection_cells=selection_cells,
            strategy_id=entry["strategy_id"],
            variant_id=entry["variant_id"],
            lane=entry["lane"],
        )
        stability_binding = {
            "strategy_id": entry["strategy_id"],
            "variant_id": entry["variant_id"],
            "lane": entry["lane"],
            "source_uncertainty_audit": source_audit,
            "correlation_matrix": matrix,
            "selection_cells": selection_cells,
            "expected_stability_gate_hash": stability_gate["gate_hash"],
        }
        decision_blockers = (
            []
            if stability_gate["status"] == "PASS"
            else [
                "cluster_stability_gate_blocked:"
                + ":".join(
                    (entry["strategy_id"], entry["variant_id"], entry["lane"])
                )
            ]
        )
        extension = {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": report19["base_report_hash"],
            "base_global_independence_extension": report19,
            "base_global_independence_extension_hash": report19["extension_hash"],
            "registry_binding_required": True,
            "stability_gate_required": True,
            "external_stability_bindings_required": True,
            "entries": [
                {
                    "strategy_id": entry["strategy_id"],
                    "variant_id": entry["variant_id"],
                    "lane": entry["lane"],
                    "stability_gate": stability_gate,
                    "stability_gate_hash": stability_gate["gate_hash"],
                }
            ],
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "consumer_only": True,
            "requires_new_report_schema": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": {"paper_authorized": False, "live_order_allowed": False},
        }
        extension = seal_strict_canonical_document(extension, "extension_hash")
        return extension, report19, registry_binding, stability_binding

    def _verify(
        self,
        values,
        document=None,
        *,
        expected_global_hash=None,
        stability_bindings=None,
    ):
        extension, report19, registry_binding, stability_binding = values
        return verify_strategy_correlation_cluster_stability_report_extension(
            extension if document is None else document,
            expected_base_report_hash=report19["base_report_hash"],
            expected_global_independence_extension_hash=(
                report19["extension_hash"]
                if expected_global_hash is None
                else expected_global_hash
            ),
            expected_registry_bindings=[registry_binding],
            expected_stability_bindings=(
                [stability_binding]
                if stability_bindings is None
                else stability_bindings
            ),
        )

    def test_report19_passes_without_any_stability_evidence(self):
        _, report19, _, _ = self._fixture()
        serialized = json.dumps(report19, sort_keys=True)

        self.assertEqual(report19["decision"], "PASS")
        self.assertNotIn("stability", serialized.lower())

    def test_valid_report20_passes_contract_and_decision(self):
        values = self._fixture()
        verification = self._verify(values)

        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(verification["stability_gate_count"], 1)
        self.assertEqual(verification["stability_gate_pass_count"], 1)
        self.assertFalse(verification["writer_available"])

    def test_low_effective_sample_blocks_decision_but_not_contract(self):
        values = self._fixture(low_effective_sample=True)
        extension = values[0]
        verification = self._verify(values)

        self.assertEqual(extension["base_global_independence_extension"]["decision"], "PASS")
        self.assertEqual(extension["entries"][0]["stability_gate"]["status"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(verification["stability_gate_pass_count"], 0)

    def test_missing_external_binding_blocks_contract(self):
        values = self._fixture()
        verification = self._verify(values, stability_bindings=[])

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("cluster_stability_identity_set_mismatch", verification["blockers"])

    def test_wrong_caller_supplied_gate_hash_blocks_contract(self):
        values = self._fixture()
        binding = deepcopy(values[3])
        binding["expected_stability_gate_hash"] = "e" * 64

        verification = self._verify(values, stability_bindings=[binding])

        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(blocker.startswith("cluster_stability_gate_hash_mismatch:") for blocker in verification["blockers"])
        )

    def test_identity_drift_blocks_before_gate_decision(self):
        values = self._fixture()
        document = deepcopy(values[0])
        document["entries"][0]["strategy_id"] = "DRIFT"
        document = seal_strict_canonical_document(document, "extension_hash")

        verification = self._verify(values, document)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("cluster_stability_identity_set_mismatch", verification["blockers"])

    def test_resealed_gate_type_alias_is_independently_rejected(self):
        values = self._fixture()
        document = deepcopy(values[0])
        gate = document["entries"][0]["stability_gate"]
        gate["consumer_only"] = 1
        gate = seal_strict_canonical_document(gate, "gate_hash")
        document["entries"][0]["stability_gate"] = gate
        document["entries"][0]["stability_gate_hash"] = gate["gate_hash"]
        document = seal_strict_canonical_document(document, "extension_hash")
        binding = deepcopy(values[3])
        binding["expected_stability_gate_hash"] = gate["gate_hash"]

        verification = self._verify(
            values,
            document,
            stability_bindings=[binding],
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertTrue(
            any(blocker.startswith("cluster_stability_gate_invalid:") for blocker in verification["blockers"])
        )

    def test_external_report19_hash_mismatch_blocks_contract(self):
        values = self._fixture()
        verification = self._verify(values, expected_global_hash="d" * 64)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("global_independence_extension_hash_mismatch", verification["blockers"])

    def test_root_native_alias_and_authority_escalation_are_rejected(self):
        values = self._fixture()
        alias = deepcopy(values[0])
        alias["target_report_schema_version"] = 20.0
        alias = seal_strict_canonical_document(alias, "extension_hash")
        escalated = deepcopy(values[0])
        escalated["permissions"]["live_order_allowed"] = True
        escalated = seal_strict_canonical_document(escalated, "extension_hash")

        alias_verification = self._verify(values, alias)
        escalated_verification = self._verify(values, escalated)

        self.assertEqual(alias_verification["status"], "BLOCK")
        self.assertEqual(escalated_verification["status"], "BLOCK")
        self.assertIn("research_authority_violation", escalated_verification["blockers"])

    def test_duplicate_external_binding_is_rejected(self):
        values = self._fixture()
        verification = self._verify(
            values,
            stability_bindings=[values[3], deepcopy(values[3])],
        )

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("stability_bindings_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
