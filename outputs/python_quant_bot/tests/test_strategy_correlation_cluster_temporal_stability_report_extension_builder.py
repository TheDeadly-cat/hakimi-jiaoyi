from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_extension_builder import (
    INPUT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_stability_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_temporal_stability_report_consumer as report21_fixtures,
)


class StrategyCorrelationClusterTemporalStabilityReportExtensionBuilderTests(
    unittest.TestCase
):
    def setUp(self):
        self.source = (
            report21_fixtures.StrategyCorrelationClusterTemporalStabilityReportConsumerTests(
                "test_valid_report21_passes_contract_and_decision"
            )
        )
        self.source.setUp()
        self.addCleanup(self.source.tearDown)

    @staticmethod
    def _input(binding):
        return {"schema_version": INPUT_SCHEMA_VERSION, **deepcopy(binding)}

    def _build(self, values, *, temporal_inputs=None):
        (
            _,
            report20,
            report19,
            registry_binding,
            stability_binding,
            temporal_binding,
        ) = values
        return build_strategy_correlation_cluster_temporal_stability_report_extension(
            report20,
            expected_base_report_hash=report20["base_report_hash"],
            expected_global_independence_extension_hash=report19[
                "extension_hash"
            ],
            expected_cluster_stability_extension_hash=report20[
                "extension_hash"
            ],
            expected_registry_bindings=[registry_binding],
            expected_stability_bindings=[stability_binding],
            temporal_inputs=(
                [self._input(temporal_binding)]
                if temporal_inputs is None
                else temporal_inputs
            ),
        )

    def _verify(self, document, values, temporal_inputs):
        (
            _,
            report20,
            report19,
            registry_binding,
            stability_binding,
            _,
        ) = values
        expected_temporal_bindings = [
            {
                key: deepcopy(value)
                for key, value in item.items()
                if key != "schema_version"
            }
            for item in temporal_inputs
        ]
        return verify_strategy_correlation_cluster_temporal_stability_report_extension(
            document,
            expected_base_report_hash=report20["base_report_hash"],
            expected_global_independence_extension_hash=report19[
                "extension_hash"
            ],
            expected_cluster_stability_extension_hash=report20[
                "extension_hash"
            ],
            expected_registry_bindings=[registry_binding],
            expected_stability_bindings=[stability_binding],
            expected_temporal_stability_bindings=expected_temporal_bindings,
        )

    def test_rebuilds_existing_pass_fixture_exactly_and_deterministically(self):
        values = self.source._fixture()
        expected, report20, _, _, _, temporal_binding = values
        inputs = [self._input(temporal_binding)]
        report20_before = deepcopy(report20)
        inputs_before = deepcopy(inputs)

        first = self._build(values, temporal_inputs=inputs)
        second = self._build(values, temporal_inputs=inputs)
        verification = self._verify(first, values, inputs)

        self.assertEqual(first, expected)
        self.assertEqual(first, second)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(report20, report20_before)
        self.assertEqual(inputs, inputs_before)
        self.assertIsNot(first["base_cluster_stability_extension"], report20)
        self.assertIs(first["writer_available"], False)
        self.assertIs(first["current_admission_allowed"], False)
        self.assertIs(first["current_writer_activation_allowed"], False)
        self.assertIs(first["permissions"]["paper_authorized"], False)
        self.assertIs(first["permissions"]["live_order_allowed"], False)

    def test_low_sample_inherited_and_temporal_blocks_remain_descriptive(self):
        values = self.source._fixture(low_effective_sample=True)
        expected, report20, _, _, _, temporal_binding = values
        inputs = [self._input(temporal_binding)]

        document = self._build(values, temporal_inputs=inputs)
        verification = self._verify(document, values, inputs)

        self.assertEqual(document, expected)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")
        self.assertEqual(report20["decision"], "BLOCK")
        self.assertIn(
            "base_cluster_stability_decision_blocked",
            document["decision_blockers"],
        )
        self.assertTrue(
            any(
                blocker.startswith(
                    "cluster_temporal_stability_gate_blocked:"
                )
                for blocker in document["decision_blockers"]
            )
        )

    def test_invalid_base_binding_input_or_expected_hash_never_builds(self):
        class DictAlias(dict):
            pass

        class ListAlias(list):
            pass

        values = self.source._fixture()
        _, report20, report19, registry_binding, stability_binding, temporal_binding = values
        inputs = [self._input(temporal_binding)]
        bad_base = deepcopy(report20)
        bad_base["extension_hash"] = "0" * 64
        bad_schema = deepcopy(inputs)
        bad_schema[0]["schema_version"] += "-drift"
        bad_identity = deepcopy(inputs)
        bad_identity[0]["variant_id"] += "-drift"
        bad_audit = deepcopy(inputs)
        bad_audit[0]["source_uncertainty_audit"]["audit_hash"] = "0" * 64
        bad_gate_hash = deepcopy(inputs)
        bad_gate_hash[0]["expected_temporal_stability_gate_hash"] = "0" * 64
        cases = (
            ("base_alias", DictAlias(report20), [registry_binding], [stability_binding], inputs),
            ("base_hash", bad_base, [registry_binding], [stability_binding], inputs),
            ("schema", report20, [registry_binding], [stability_binding], bad_schema),
            ("identity", report20, [registry_binding], [stability_binding], bad_identity),
            ("audit", report20, [registry_binding], [stability_binding], bad_audit),
            ("gate_hash", report20, [registry_binding], [stability_binding], bad_gate_hash),
            ("input_list_alias", report20, [registry_binding], [stability_binding], ListAlias(inputs)),
            ("registry_list_alias", report20, ListAlias([registry_binding]), [stability_binding], inputs),
            ("stability_list_alias", report20, [registry_binding], ListAlias([stability_binding]), inputs),
        )
        for label, base, registries, stability, candidate_inputs in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    build_strategy_correlation_cluster_temporal_stability_report_extension(
                        base,
                        expected_base_report_hash=report20["base_report_hash"],
                        expected_global_independence_extension_hash=report19[
                            "extension_hash"
                        ],
                        expected_cluster_stability_extension_hash=report20[
                            "extension_hash"
                        ],
                        expected_registry_bindings=registries,
                        expected_stability_bindings=stability,
                        temporal_inputs=candidate_inputs,
                    )
        with self.assertRaises(ValueError):
            build_strategy_correlation_cluster_temporal_stability_report_extension(
                report20,
                expected_base_report_hash=report20["base_report_hash"],
                expected_global_independence_extension_hash=report19[
                    "extension_hash"
                ],
                expected_cluster_stability_extension_hash="0" * 64,
                expected_registry_bindings=[registry_binding],
                expected_stability_bindings=[stability_binding],
                temporal_inputs=inputs,
            )

    def test_resealed_output_numeric_aliases_are_rejected(self):
        values = self.source._fixture()
        _, _, _, _, _, temporal_binding = values
        inputs = [self._input(temporal_binding)]
        document = self._build(values, temporal_inputs=inputs)
        attacks = (
            (("base_report_schema_version",), 20.0),
            (("target_report_schema_version",), 21.0),
            (("registry_bindings_required",), 1),
            (("stability_bindings_required",), 1),
            (("temporal_stability_gate_required",), 1),
            (("external_temporal_stability_bindings_required",), 1),
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
