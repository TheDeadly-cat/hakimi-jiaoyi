from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    verify_strategy_correlation_global_independence_report_extension,
)
from exchange_terminal.services.strategy_correlation_global_independence_report_extension_builder import (
    build_strategy_correlation_global_independence_report_extension,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_strata_report_extension_builder as report18_fixtures,
)


class StrategyCorrelationGlobalIndependenceReportExtensionBuilderTests(
    unittest.TestCase
):
    def setUp(self):
        self.source = (
            report18_fixtures.StrategyCorrelationStrataReportExtensionBuilderTests(
                "test_verified_pass_builds_deterministic_source_bound_extension"
            )
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.inputs = self.source._inputs()
        self.expected_bindings = self.source._expected_bindings(self.inputs)
        self.report18 = self.source._build(inputs=self.inputs)

    def _build(self, report18=None, expected_bindings=None):
        report18 = report18 or self.report18
        expected_bindings = (
            self.expected_bindings
            if expected_bindings is None
            else expected_bindings
        )
        return build_strategy_correlation_global_independence_report_extension(
            report18,
            expected_base_report_hash=report18["base_report_hash"],
            expected_registry_bindings=expected_bindings,
        )

    def _verify(self, document, expected_bindings=None):
        expected_bindings = (
            self.expected_bindings
            if expected_bindings is None
            else expected_bindings
        )
        return verify_strategy_correlation_global_independence_report_extension(
            document,
            expected_base_report_hash=document["base_report_hash"],
            expected_registry_bindings=expected_bindings,
        )

    def _cycle_inputs(self):
        values = self.source._inputs()
        for index, value in enumerate(values):
            preregistration = self.source.report17["entries"][index][
                "preregistration"
            ]
            cluster_ids = [
                item["cluster_id"]
                for item in preregistration["clusters"]
            ]
            self.assertEqual(len(cluster_ids), 3)
            left, middle, right = cluster_ids
            dimensions = [
                {
                    "dimension_id": "dimension-left-middle",
                    "strata": [
                        {
                            "stratum_id": "left-middle",
                            "cluster_ids": [left, middle],
                        },
                        {
                            "stratum_id": "right-only",
                            "cluster_ids": [right],
                        },
                    ],
                },
                {
                    "dimension_id": "dimension-left-right",
                    "strata": [
                        {
                            "stratum_id": "left-right",
                            "cluster_ids": [left, right],
                        },
                        {
                            "stratum_id": "middle-only",
                            "cluster_ids": [middle],
                        },
                    ],
                },
                {
                    "dimension_id": "dimension-middle-right",
                    "strata": [
                        {
                            "stratum_id": "middle-right",
                            "cluster_ids": [middle, right],
                        },
                        {
                            "stratum_id": "left-only",
                            "cluster_ids": [left],
                        },
                    ],
                },
            ]
            registry_asset = build_strategy_correlation_strata_registry_asset(
                preregistration,
                dimensions,
                registry_id=f"cycle-candidate-{index}",
                classification_source="synthetic-external-source",
                classification_source_version="v1",
                classification_source_hash=self.source.SOURCE_HASH,
                effective_date="2026-07-31",
                frozen_at="2026-08-01T00:00:00Z",
            )
            value["dimensions"] = dimensions
            value["registry_asset"] = registry_asset
            value["expected_registry_asset_hash"] = registry_asset[
                "registry_asset_hash"
            ]
        return values

    def test_verified_pass_builds_deterministic_self_verified_extension(self):
        report18_before = deepcopy(self.report18)
        bindings_before = deepcopy(self.expected_bindings)

        first = self._build()
        second = self._build()
        verification = self._verify(first)

        self.assertEqual(first, second)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(self.report18, report18_before)
        self.assertEqual(self.expected_bindings, bindings_before)
        self.assertIsNot(first["base_strata_extension"], self.report18)
        self.assertIs(first["writer_available"], False)
        self.assertIs(first["current_admission_allowed"], False)
        self.assertIs(first["current_writer_activation_allowed"], False)
        self.assertIs(first["permissions"]["paper_authorized"], False)
        self.assertIs(first["permissions"]["live_order_allowed"], False)

    def test_global_and_inherited_blocks_remain_descriptive(self):
        cycle_inputs = self._cycle_inputs()
        cycle_bindings = self.source._expected_bindings(cycle_inputs)
        cycle_report18 = self.source._build(inputs=cycle_inputs)
        shared_inputs = self.source._inputs(shared=True)
        shared_bindings = self.source._expected_bindings(shared_inputs)
        shared_report18 = self.source._build(inputs=shared_inputs)
        binding_inputs = self.source._inputs(expected_source_hash="c" * 64)
        binding_bindings = self.source._expected_bindings(binding_inputs)
        binding_report18 = self.source._build(inputs=binding_inputs)
        cases = (
            (
                "global_cycle",
                cycle_report18,
                cycle_bindings,
                "global_independence_gate_blocked:",
            ),
            (
                "base_strata",
                shared_report18,
                shared_bindings,
                "strata_extension_blocked",
            ),
            (
                "registry_binding",
                binding_report18,
                binding_bindings,
                "strata_extension_blocked",
            ),
        )
        for label, report18, bindings, blocker_prefix in cases:
            with self.subTest(label=label):
                document = self._build(report18, bindings)
                verification = self._verify(document, bindings)
                self.assertEqual(verification["status"], "PASS")
                self.assertEqual(verification["decision"], "BLOCK")
                self.assertTrue(
                    any(
                        blocker.startswith(blocker_prefix)
                        for blocker in document["decision_blockers"]
                    )
                )

    def test_invalid_base_hash_binding_or_container_never_builds(self):
        class DictAlias(dict):
            pass

        class ListAlias(list):
            pass

        bad_extension = deepcopy(self.report18)
        bad_extension["extension_hash"] = "0" * 64
        bad_nested = deepcopy(self.report18)
        bad_nested["entries"][0]["strata_gate"]["gate_hash"] = "0" * 64
        bad_bindings = deepcopy(self.expected_bindings)
        bad_bindings[0]["expected_classification_source_hash"] = "c" * 64
        cases = (
            ("base_alias", DictAlias(self.report18), self.expected_bindings),
            ("extension_hash", bad_extension, self.expected_bindings),
            ("nested_gate", bad_nested, self.expected_bindings),
            ("binding_drift", self.report18, bad_bindings),
            ("binding_list_alias", self.report18, ListAlias(self.expected_bindings)),
        )
        for label, report18, bindings in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    self._build(report18, bindings)
        with self.assertRaises(ValueError):
            build_strategy_correlation_global_independence_report_extension(
                self.report18,
                expected_base_report_hash="0" * 64,
                expected_registry_bindings=self.expected_bindings,
            )

    def test_resealed_output_numeric_aliases_are_rejected(self):
        document = self._build()
        attacks = (
            (("base_report_schema_version",), 18.0),
            (("target_report_schema_version",), 19.0),
            (("registry_binding_required",), 1),
            (("global_independence_required",), 1),
            (("consumer_only",), 1),
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
                verification = self._verify(candidate)
                self.assertEqual(verification["status"], "BLOCK")
