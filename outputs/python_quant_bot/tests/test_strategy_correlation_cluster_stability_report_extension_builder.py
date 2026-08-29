from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_stability import (
    evaluate_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
    verify_strategy_correlation_cluster_stability_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_report_extension_builder import (
    INPUT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_stability_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_stability_report_consumer as report20_fixtures,
)
from tests import (
    test_strategy_correlation_global_independence_report_extension_builder as report19_fixtures,
)


class StrategyCorrelationClusterStabilityReportExtensionBuilderTests(
    unittest.TestCase
):
    def setUp(self):
        self.source = (
            report20_fixtures.StrategyCorrelationClusterStabilityReportConsumerTests(
                "test_valid_report20_passes_contract_and_decision"
            )
        )
        self.source.setUp()
        self.addCleanup(self.source.tearDown)

    @staticmethod
    def _input(binding):
        return {"schema_version": INPUT_SCHEMA_VERSION, **deepcopy(binding)}

    def _build(self, values, *, stability_inputs=None):
        _, report19, registry_binding, stability_binding = values
        return build_strategy_correlation_cluster_stability_report_extension(
            report19,
            expected_base_report_hash=report19["base_report_hash"],
            expected_global_independence_extension_hash=report19[
                "extension_hash"
            ],
            expected_registry_bindings=[registry_binding],
            stability_inputs=(
                [self._input(stability_binding)]
                if stability_inputs is None
                else stability_inputs
            ),
        )

    def _verify(self, document, values, stability_inputs):
        _, report19, registry_binding, _ = values
        expected_stability_bindings = [
            {
                key: deepcopy(value)
                for key, value in item.items()
                if key != "schema_version"
            }
            for item in stability_inputs
        ]
        return verify_strategy_correlation_cluster_stability_report_extension(
            document,
            expected_base_report_hash=report19["base_report_hash"],
            expected_global_independence_extension_hash=report19[
                "extension_hash"
            ],
            expected_registry_bindings=[registry_binding],
            expected_stability_bindings=expected_stability_bindings,
        )

    def test_rebuilds_existing_pass_fixture_exactly_and_deterministically(self):
        values = self.source._fixture()
        expected, report19, _, stability_binding = values
        inputs = [self._input(stability_binding)]
        report19_before = deepcopy(report19)
        inputs_before = deepcopy(inputs)

        first = self._build(values, stability_inputs=inputs)
        second = self._build(values, stability_inputs=inputs)
        verification = self._verify(first, values, inputs)

        self.assertEqual(first, expected)
        self.assertEqual(first, second)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(report19, report19_before)
        self.assertEqual(inputs, inputs_before)
        self.assertIsNot(
            first["base_global_independence_extension"],
            report19,
        )
        self.assertIs(first["writer_available"], False)
        self.assertIs(first["current_admission_allowed"], False)
        self.assertIs(first["current_writer_activation_allowed"], False)
        self.assertIs(first["permissions"]["paper_authorized"], False)
        self.assertIs(first["permissions"]["live_order_allowed"], False)

    def test_low_sample_and_real_upstream_chain_remain_descriptive_block(self):
        low_values = self.source._fixture(low_effective_sample=True)
        low_expected, _, _, low_binding = low_values
        low_inputs = [self._input(low_binding)]
        low_document = self._build(low_values, stability_inputs=low_inputs)
        self.assertEqual(low_document, low_expected)
        self.assertEqual(low_document["decision"], "BLOCK")

        chain = (
            report19_fixtures.StrategyCorrelationGlobalIndependenceReportExtensionBuilderTests(
                "test_verified_pass_builds_deterministic_self_verified_extension"
            )
        )
        chain.setUp()
        self.addCleanup(chain.doCleanups)
        cycle_inputs = chain._cycle_inputs()
        registry_bindings = chain.source._expected_bindings(cycle_inputs)
        report18 = chain.source._build(inputs=cycle_inputs)
        report19 = chain._build(report18, registry_bindings)
        report19_entry = report19["entries"][0]
        report17_entry = chain.source.report17["entries"][0]
        evidence = chain.source.source._evidence(passed=True)
        gate = evaluate_strategy_correlation_cluster_stability_gate(
            evidence["uncertainty_audit"],
            report19_entry["complete_link_gate"],
            preregistration=report19_entry["source_preregistration"],
            correlation_matrix=report17_entry["correlation_matrix"],
            selection_cells=report17_entry["selection_cells"],
            strategy_id=report19_entry["strategy_id"],
            variant_id=report19_entry["variant_id"],
            lane=report19_entry["lane"],
        )
        stability_input = {
            "schema_version": INPUT_SCHEMA_VERSION,
            "strategy_id": report19_entry["strategy_id"],
            "variant_id": report19_entry["variant_id"],
            "lane": report19_entry["lane"],
            "source_uncertainty_audit": evidence["uncertainty_audit"],
            "correlation_matrix": report17_entry["correlation_matrix"],
            "selection_cells": report17_entry["selection_cells"],
            "expected_stability_gate_hash": gate["gate_hash"],
        }
        chained = build_strategy_correlation_cluster_stability_report_extension(
            report19,
            expected_base_report_hash=report19["base_report_hash"],
            expected_global_independence_extension_hash=report19[
                "extension_hash"
            ],
            expected_registry_bindings=registry_bindings,
            stability_inputs=[stability_input],
        )
        self.assertEqual(chained["decision"], "BLOCK")
        self.assertIn(
            "base_global_independence_decision_blocked",
            chained["decision_blockers"],
        )

    def test_invalid_base_binding_input_or_expected_hash_never_builds(self):
        class DictAlias(dict):
            pass

        class ListAlias(list):
            pass

        values = self.source._fixture()
        _, report19, registry_binding, stability_binding = values
        inputs = [self._input(stability_binding)]
        bad_base = deepcopy(report19)
        bad_base["extension_hash"] = "0" * 64
        bad_schema = deepcopy(inputs)
        bad_schema[0]["schema_version"] += "-drift"
        bad_identity = deepcopy(inputs)
        bad_identity[0]["variant_id"] += "-drift"
        bad_audit = deepcopy(inputs)
        bad_audit[0]["source_uncertainty_audit"]["audit_hash"] = "0" * 64
        bad_gate_hash = deepcopy(inputs)
        bad_gate_hash[0]["expected_stability_gate_hash"] = "0" * 64
        cases = (
            ("base_alias", DictAlias(report19), [registry_binding], inputs),
            ("base_hash", bad_base, [registry_binding], inputs),
            ("schema", report19, [registry_binding], bad_schema),
            ("identity", report19, [registry_binding], bad_identity),
            ("audit", report19, [registry_binding], bad_audit),
            ("gate_hash", report19, [registry_binding], bad_gate_hash),
            ("input_list_alias", report19, [registry_binding], ListAlias(inputs)),
        )
        for label, base, registry_bindings, candidate_inputs in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    build_strategy_correlation_cluster_stability_report_extension(
                        base,
                        expected_base_report_hash=report19["base_report_hash"],
                        expected_global_independence_extension_hash=report19[
                            "extension_hash"
                        ],
                        expected_registry_bindings=registry_bindings,
                        stability_inputs=candidate_inputs,
                    )
        with self.assertRaises(ValueError):
            build_strategy_correlation_cluster_stability_report_extension(
                report19,
                expected_base_report_hash=report19["base_report_hash"],
                expected_global_independence_extension_hash="0" * 64,
                expected_registry_bindings=[registry_binding],
                stability_inputs=inputs,
            )

    def test_resealed_output_numeric_aliases_are_rejected(self):
        values = self.source._fixture()
        _, _, _, stability_binding = values
        inputs = [self._input(stability_binding)]
        document = self._build(values, stability_inputs=inputs)
        attacks = (
            (("base_report_schema_version",), 19.0),
            (("target_report_schema_version",), 20.0),
            (("registry_binding_required",), 1),
            (("stability_gate_required",), 1),
            (("external_stability_bindings_required",), 1),
            (("consumer_only",), 1),
            (("requires_new_report_schema",), 1),
            (("writer_available",), 0),
            (("current_admission_allowed",), 0),
            (("current_writer_activation_allowed",), 0),
            (("permissions", "paper_authorized"), 0),
            (("permissions", "live_order_allowed"), 0),
        )
        for path, value in attacks:
            with self.subTest(path=path):
                candidate = deepcopy(document)
                target = candidate
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                candidate.pop("extension_hash", None)
                candidate = seal_strict_canonical_document(
                    candidate,
                    "extension_hash",
                )
                verification = self._verify(candidate, values, inputs)
                self.assertEqual(verification["status"], "BLOCK")
