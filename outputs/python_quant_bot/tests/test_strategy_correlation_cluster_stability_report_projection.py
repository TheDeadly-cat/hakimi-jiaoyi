import copy
import json
import unittest

from tests import test_strategy_correlation_cluster_stability_report_consumer as source_fixtures
from exchange_terminal.services.strategy_correlation_cluster_stability_report_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    build_strategy_correlation_cluster_stability_report_public_summary,
    verify_strategy_correlation_cluster_stability_report_public_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


class StrategyCorrelationClusterStabilityReportProjectionTests(
    unittest.TestCase
):
    def setUp(self):
        self.source = (
            source_fixtures.StrategyCorrelationClusterStabilityReportConsumerTests(
                "test_valid_report20_passes_contract_and_decision"
            )
        )
        self.source.setUp()

    def tearDown(self):
        self.source.tearDown()

    @staticmethod
    def _arguments(values):
        _, report19, registry_binding, stability_binding = values
        return {
            "expected_base_report_hash": report19["base_report_hash"],
            "expected_global_independence_extension_hash": report19[
                "extension_hash"
            ],
            "expected_registry_bindings": [registry_binding],
            "expected_stability_bindings": [stability_binding],
        }

    def _build(self, values, document=None, **argument_overrides):
        arguments = self._arguments(values)
        arguments.update(argument_overrides)
        return build_strategy_correlation_cluster_stability_report_public_summary(
            values[0] if document is None else document,
            **arguments,
        )

    def test_stable_pass_projects_count_only_research_evidence(self):
        values = self.source._fixture()
        summary = self._build(values)
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["stability_gate_count"], 1)
        self.assertTrue(
            summary["source"][
                "base_global_independence_extension_hash_bound"
            ]
        )
        self.assertEqual(summary["gap"]["status"], "CLUSTER_STABILITY_OBSERVED")
        self.assertEqual(summary["gap"]["decision"], "PASS")
        self.assertEqual(summary["gap"]["stability_gate_pass_count"], 1)
        self.assertEqual(summary["gap"]["stability_gate_blocked_count"], 0)
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_low_effective_sample_is_descriptive_stability_block(self):
        values = self.source._fixture(low_effective_sample=True)
        summary = self._build(values)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["gap"]["decision"], "BLOCK")
        self.assertEqual(
            summary["gap"]["status"],
            "CLUSTER_STABILITY_BLOCK_OBSERVED",
        )
        self.assertEqual(summary["gap"]["stability_gate_pass_count"], 0)
        self.assertEqual(summary["gap"]["stability_gate_blocked_count"], 1)
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_EVIDENCE_BLOCK")

    def test_invalid_external_or_type_aliased_source_projects_unknown(self):
        values = self.source._fixture()
        hostile = copy.deepcopy(values[0])
        hostile["target_report_schema_version"] = 20.0
        hostile = seal_strict_canonical_document(hostile, "extension_hash")
        cases = (
            self._build(values, hostile),
            self._build(
                values,
                expected_global_independence_extension_hash="d" * 64,
            ),
            self._build(values, expected_stability_bindings=[]),
        )
        for summary in cases:
            with self.subTest(summary=summary):
                self.assertEqual(summary["source"]["status"], "UNKNOWN")
                self.assertEqual(summary["gap"]["status"], "SOURCE_INVALID")
                self.assertEqual(summary["gap"]["decision"], "UNKNOWN")
                self.assertFalse(summary["permission"]["paper_authorized"])
                self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_pass_block_and_unknown_summaries_are_redacted(self):
        passing = self.source._fixture()
        blocked = self.source._fixture(low_effective_sample=True)
        unknown_document = copy.deepcopy(passing[0])
        unknown_document["extension_hash"] = "0" * 64
        summaries = (
            self._build(passing),
            self._build(blocked),
            self._build(passing, unknown_document),
        )
        private_keys = {
            "extension_hash",
            "base_report_hash",
            "strategy_id",
            "variant_id",
            "lane",
            "base_global_independence_extension",
            "source_uncertainty_audit",
            "correlation_matrix",
            "selection_cells",
            "stability_gate",
            "registry_asset",
            "registry_binding",
            "decision_blockers",
        }
        private_values = (
            "RAW_EXCESS",
            "cluster-aaa",
            "cluster-bbb",
            "cluster-ccc",
            "candidate-1",
            "external-source",
        )

        def keys(value):
            if type(value) is dict:
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif type(value) is list:
                for child in value:
                    yield from keys(child)

        for summary in summaries:
            with self.subTest(status=summary["source"]["status"]):
                self.assertFalse(private_keys.intersection(keys(summary)))
                serialized = json.dumps(summary, sort_keys=True)
                for value in private_values:
                    self.assertNotIn(value, serialized)
                self.assertTrue(
                    all(value is False for value in summary["redaction"].values())
                )

    def test_public_verifier_exactly_rebuilds_and_rejects_type_aliases(self):
        values = self.source._fixture()
        summary = self._build(values)
        arguments = self._arguments(values)

        def verify(value):
            return verify_strategy_correlation_cluster_stability_report_public_summary(
                value,
                source_extension=values[0],
                **arguments,
            )

        self.assertEqual(verify(summary)["status"], "PASS")

        def aliases(value, path=()):
            if type(value) is dict:
                for key, child in value.items():
                    yield from aliases(child, path + (key,))
            elif type(value) is list:
                for index, child in enumerate(value):
                    yield from aliases(child, path + (index,))
            elif type(value) is bool:
                yield path, int(value)
            elif type(value) is int:
                yield path, float(value)

        attacks = list(aliases(summary))
        self.assertGreater(len(attacks), 0)
        for path, replacement in attacks:
            with self.subTest(path=path):
                hostile = copy.deepcopy(summary)
                target = hostile
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                self.assertEqual(verify(hostile)["status"], "BLOCK")

        hostile = copy.deepcopy(summary)
        hostile["extension_hash"] = "0" * 64
        self.assertEqual(verify(hostile)["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
