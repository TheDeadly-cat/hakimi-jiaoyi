from copy import deepcopy
import unittest

from exchange_terminal.services.strategy_correlation_strata_registry import (
    build_strategy_correlation_strata_registry_asset,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    verify_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strategy_correlation_strata_report_extension_builder import (
    INPUT_SCHEMA_VERSION,
    build_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_complete_link_report_extension_builder as report17_fixtures,
)


class StrategyCorrelationStrataReportExtensionBuilderTests(unittest.TestCase):
    SOURCE_HASH = "a" * 64

    def setUp(self):
        self.source = (
            report17_fixtures.StrategyCorrelationCompleteLinkReportExtensionBuilderTests(
                "test_verified_pass_builds_deterministic_self_verified_extension"
            )
        )
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.report17 = self.source._build(self.source._evidence(passed=True))

    def _inputs(
        self,
        report17=None,
        *,
        shared=False,
        expected_source_hash=None,
    ):
        report17 = report17 or self.report17
        values = []
        for index, entry in enumerate(report17["entries"]):
            preregistration = entry["preregistration"]
            cluster_ids = [
                cluster["cluster_id"]
                for cluster in preregistration["clusters"]
            ]
            strata = (
                [{"stratum_id": "shared", "cluster_ids": cluster_ids}]
                if shared
                else [
                    {
                        "stratum_id": f"stratum-{position}",
                        "cluster_ids": [cluster_id],
                    }
                    for position, cluster_id in enumerate(cluster_ids)
                ]
            )
            dimensions = [
                {"dimension_id": "asset-family", "strata": strata}
            ]
            registry_asset = build_strategy_correlation_strata_registry_asset(
                preregistration,
                dimensions,
                registry_id=f"synthetic-candidate-{index}",
                classification_source="synthetic-external-source",
                classification_source_version="v1",
                classification_source_hash=self.SOURCE_HASH,
                effective_date="2026-07-31",
                frozen_at="2026-08-01T00:00:00Z",
            )
            values.append(
                {
                    "schema_version": INPUT_SCHEMA_VERSION,
                    "strategy_id": entry["strategy_id"],
                    "variant_id": entry["variant_id"],
                    "lane": entry["lane"],
                    "dimensions": dimensions,
                    "registry_asset": registry_asset,
                    "selection_cutoff_date": "2026-08-02",
                    "expected_registry_asset_hash": registry_asset[
                        "registry_asset_hash"
                    ],
                    "expected_classification_source_hash": (
                        expected_source_hash or self.SOURCE_HASH
                    ),
                }
            )
        return values

    @staticmethod
    def _expected_bindings(values):
        return [
            {
                "strategy_id": value["strategy_id"],
                "variant_id": value["variant_id"],
                "lane": value["lane"],
                "selection_cutoff_date": value[
                    "selection_cutoff_date"
                ],
                "expected_registry_asset_hash": value[
                    "expected_registry_asset_hash"
                ],
                "expected_classification_source_hash": value[
                    "expected_classification_source_hash"
                ],
            }
            for value in values
        ]

    def _build(self, report17=None, inputs=None):
        report17 = report17 or self.report17
        inputs = inputs or self._inputs(report17)
        return build_strategy_correlation_strata_report_extension(
            report17,
            expected_base_report_hash=report17["base_report_hash"],
            strata_inputs=inputs,
        )

    def _verify(self, document, inputs):
        return verify_strategy_correlation_strata_report_extension(
            document,
            expected_base_report_hash=document["base_report_hash"],
            expected_registry_bindings=self._expected_bindings(inputs),
        )

    def test_verified_pass_builds_deterministic_source_bound_extension(self):
        inputs = self._inputs()
        report17_before = deepcopy(self.report17)
        inputs_before = deepcopy(inputs)

        first = self._build(inputs=inputs)
        second = self._build(inputs=inputs)
        verification = self._verify(first, inputs)

        self.assertEqual(first, second)
        self.assertEqual(verification["status"], "PASS")
        self.assertEqual(verification["decision"], "PASS")
        self.assertEqual(first["base_report_hash"], self.report17["base_report_hash"])
        self.assertEqual(
            first["base_complete_link_extension_hash"],
            self.report17["extension_hash"],
        )
        self.assertEqual(self.report17, report17_before)
        self.assertEqual(inputs, inputs_before)
        self.assertIsNot(
            first["base_complete_link_extension"],
            self.report17,
        )
        self.assertIs(first["writer_available"], False)
        self.assertIs(first["current_admission_allowed"], False)
        self.assertIs(first["current_writer_activation_allowed"], False)
        self.assertIs(first["permissions"]["paper_authorized"], False)
        self.assertIs(first["permissions"]["live_order_allowed"], False)

    def test_valid_negative_sources_remain_descriptive_block(self):
        report17_block = self.source._build(
            self.source._evidence(passed=False)
        )
        cases = (
            (
                "strata",
                self.report17,
                self._inputs(shared=True),
                "strata_gate_blocked:",
            ),
            (
                "binding",
                self.report17,
                self._inputs(expected_source_hash="c" * 64),
                "strata_registry_binding_blocked:",
            ),
            (
                "base",
                report17_block,
                self._inputs(report17_block),
                "complete_link_extension_blocked",
            ),
        )
        for label, report17, inputs, blocker_prefix in cases:
            with self.subTest(label=label):
                document = self._build(report17, inputs)
                verification = self._verify(document, inputs)
                self.assertEqual(verification["status"], "PASS")
                self.assertEqual(verification["decision"], "BLOCK")
                self.assertTrue(
                    any(
                        blocker.startswith(blocker_prefix)
                        for blocker in document["decision_blockers"]
                    )
                )

    def test_invalid_base_input_identity_or_asset_never_builds(self):
        class ListAlias(list):
            pass

        bad_base = deepcopy(self.report17)
        bad_base["extension_hash"] = "0" * 64
        bad_schema = self._inputs()
        bad_schema[0]["schema_version"] = INPUT_SCHEMA_VERSION + "-drift"
        bad_identity = self._inputs()
        bad_identity[0]["variant_id"] += "-drift"
        bad_asset = self._inputs()
        bad_asset[0]["registry_asset"]["registry_asset_hash"] = "0" * 64
        bad_hash = self._inputs()
        bad_hash[0]["expected_classification_source_hash"] = "A" * 64
        duplicate = self._inputs() * 2
        cases = (
            ("base", bad_base, self._inputs()),
            ("schema", self.report17, bad_schema),
            ("identity", self.report17, bad_identity),
            ("asset", self.report17, bad_asset),
            ("hash", self.report17, bad_hash),
            ("duplicate", self.report17, duplicate),
            ("list_alias", self.report17, ListAlias(self._inputs())),
        )
        for label, report17, inputs in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    self._build(report17, inputs)

    def test_resealed_output_alias_or_authority_escalation_is_rejected(self):
        inputs = self._inputs()
        document = self._build(inputs=inputs)
        attacks = (
            (("base_report_schema_version",), 17.0),
            (("target_report_schema_version",), 18.0),
            (("registry_binding_required",), 1),
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
                verification = self._verify(candidate, inputs)
                self.assertEqual(verification["status"], "BLOCK")
                self.assertEqual(verification["decision"], "UNKNOWN")
