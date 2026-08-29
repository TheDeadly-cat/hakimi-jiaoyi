from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    verify_strategy_correlation_cluster_temporal_date_grid_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_extension_builder import (
    INPUT_SCHEMA_VERSION,
    build_strategy_correlation_cluster_temporal_date_grid_report_extension,
)
from tests.test_strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    StrategyCorrelationClusterTemporalDateGridReportConsumerTests,
)


class StrategyCorrelationClusterTemporalDateGridReportExtensionBuilderTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.source = (
            StrategyCorrelationClusterTemporalDateGridReportConsumerTests(
                methodName="test_valid_report22_passes_contract_and_decision"
            )
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)

    @staticmethod
    def _input(values):
        _, arguments, date_grid_binding = values
        temporal_binding = arguments["expected_temporal_stability_bindings"][0]
        return {
            "schema_version": INPUT_SCHEMA_VERSION,
            **deepcopy(temporal_binding),
            "expected_temporal_date_grid_gate_hash": date_grid_binding[
                "expected_temporal_date_grid_gate_hash"
            ],
        }

    def _build(self, values, *, inputs=None):
        _, arguments, _ = values
        return build_strategy_correlation_cluster_temporal_date_grid_report_extension(
            arguments["report21_extension"],
            expected_base_report_hash=arguments["expected_base_report_hash"],
            expected_global_independence_extension_hash=arguments[
                "expected_global_independence_extension_hash"
            ],
            expected_cluster_stability_extension_hash=arguments[
                "expected_cluster_stability_extension_hash"
            ],
            expected_report21_extension_hash=arguments[
                "expected_report21_extension_hash"
            ],
            expected_registry_bindings=arguments["expected_registry_bindings"],
            expected_stability_bindings=arguments[
                "expected_stability_bindings"
            ],
            temporal_date_grid_inputs=(
                [self._input(values)] if inputs is None else inputs
            ),
        )

    def _verify(self, document, values, inputs):
        _, arguments, _ = values
        temporal_bindings = [
            {
                key: deepcopy(value)
                for key, value in item.items()
                if key
                not in {
                    "schema_version",
                    "expected_temporal_date_grid_gate_hash",
                }
            }
            for item in inputs
        ]
        date_grid_bindings = [
            {
                "strategy_id": item["strategy_id"],
                "variant_id": item["variant_id"],
                "lane": item["lane"],
                "expected_temporal_date_grid_gate_hash": item[
                    "expected_temporal_date_grid_gate_hash"
                ],
            }
            for item in inputs
        ]
        return (
            verify_strategy_correlation_cluster_temporal_date_grid_report_extension(
                document,
                expected_base_report_hash=arguments[
                    "expected_base_report_hash"
                ],
                expected_global_independence_extension_hash=arguments[
                    "expected_global_independence_extension_hash"
                ],
                expected_cluster_stability_extension_hash=arguments[
                    "expected_cluster_stability_extension_hash"
                ],
                expected_report21_extension_hash=arguments[
                    "expected_report21_extension_hash"
                ],
                expected_registry_bindings=arguments[
                    "expected_registry_bindings"
                ],
                expected_stability_bindings=arguments[
                    "expected_stability_bindings"
                ],
                expected_temporal_stability_bindings=temporal_bindings,
                expected_temporal_date_grid_bindings=date_grid_bindings,
            )
        )

    def test_rebuilds_pass_fixture_exactly_and_deterministically(self):
        values = self.source._fixture()
        inputs = [self._input(values)]
        first = self._build(values, inputs=inputs)
        second = self._build(values, inputs=deepcopy(inputs))
        self.assertTrue(strict_json_contract_equal(first, values[0]))
        self.assertTrue(strict_json_contract_equal(first, second))
        verification = self._verify(first, values, inputs)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")

    def test_builds_misaligned_fixture_as_block_decision(self):
        values = self.source._fixture(misaligned=True)
        inputs = [self._input(values)]
        document = self._build(values, inputs=inputs)
        verification = self._verify(document, values, inputs)
        self.assertEqual(document["decision"], "BLOCK")
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "BLOCK")

    def test_wrong_temporal_or_date_grid_expected_hash_is_rejected(self):
        values = self.source._fixture()
        temporal_wrong = self._input(values)
        temporal_wrong["expected_temporal_stability_gate_hash"] = "a" * 64
        date_wrong = self._input(values)
        date_wrong["expected_temporal_date_grid_gate_hash"] = "b" * 64
        with self.assertRaisesRegex(
            ValueError,
            "base_report21_extension_invalid",
        ):
            self._build(values, inputs=[temporal_wrong])
        with self.assertRaisesRegex(
            ValueError,
            "temporal_date_grid_expected_gate_hash_mismatch",
        ):
            self._build(values, inputs=[date_wrong])

    def test_missing_duplicate_and_extra_identity_sets_are_rejected(self):
        values = self.source._fixture()
        valid = self._input(values)
        duplicate = [valid, deepcopy(valid)]
        extra = deepcopy(valid)
        extra["strategy_id"] = "EXTRA"
        cases = ([], duplicate, [valid, extra])
        for inputs in cases:
            with self.subTest(count=len(inputs)), self.assertRaises(ValueError):
                self._build(values, inputs=inputs)

    def test_native_container_aliases_and_input_extras_are_rejected(self):
        values = self.source._fixture()
        valid = self._input(values)

        class ListAlias(list):
            pass

        class DictAlias(dict):
            pass

        extra = deepcopy(valid)
        extra["extra"] = False
        with self.assertRaises(ValueError):
            self._build(values, inputs=ListAlias([valid]))
        with self.assertRaises(ValueError):
            self._build(values, inputs=[DictAlias(valid)])
        with self.assertRaises(ValueError):
            self._build(values, inputs=[extra])

    def test_builder_does_not_mutate_report_or_external_inputs(self):
        values = self.source._fixture()
        inputs = [self._input(values)]
        report_before = deepcopy(values[1]["report21_extension"])
        inputs_before = deepcopy(inputs)
        self._build(values, inputs=inputs)
        self.assertTrue(
            strict_json_contract_equal(
                values[1]["report21_extension"],
                report_before,
            )
        )
        self.assertTrue(strict_json_contract_equal(inputs, inputs_before))

    def test_resealed_output_aliases_are_rejected(self):
        values = self.source._fixture()
        inputs = [self._input(values)]
        document = self._build(values, inputs=inputs)
        attacks = (
            (("target_report_schema_version",), 22.0),
            (("temporal_date_grid_gate_required",), 1),
            (("consumer_only",), 1),
            (("writer_available",), 0),
            (("permissions", "paper_authorized"), 0),
        )
        for path, value in attacks:
            with self.subTest(path=path):
                candidate = deepcopy(document)
                target = candidate
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                candidate = seal_strict_canonical_document(
                    candidate,
                    "extension_hash",
                )
                verification = self._verify(candidate, values, inputs)
                self.assertEqual(verification["status"], "BLOCK")

    def test_exports_have_no_writer_io_migration_or_current_switch(self):
        from exchange_terminal.services import (
            strategy_correlation_cluster_temporal_date_grid_report_extension_builder as module,
        )

        exports = set(module.__all__)
        self.assertNotIn("write_report22", exports)
        self.assertNotIn("save_report22", exports)
        self.assertNotIn("migrate_report22", exports)
        self.assertNotIn("switch_current_pointer", exports)


if __name__ == "__main__":
    unittest.main()
