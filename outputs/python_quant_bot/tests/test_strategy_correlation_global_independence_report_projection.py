import copy
import json
import unittest

from tests import test_strategy_correlation_global_independence_report_consumer as global_fixtures
from tests import test_strategy_correlation_strata_report_consumer as strata_fixtures
from exchange_terminal.services.strategy_correlation_global_independence_report_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    build_strategy_correlation_global_independence_report_public_summary,
    verify_strategy_correlation_global_independence_report_public_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationGlobalIndependenceReportProjectionTests(
    unittest.TestCase
):
    @staticmethod
    def _global_case():
        return global_fixtures.StrategyCorrelationGlobalIndependenceReportConsumerTests(
            "test_independent_singletons_pass_contract_and_decision"
        )

    @staticmethod
    def _strata_case():
        return strata_fixtures.StrategyCorrelationStrataReportConsumerTests(
            "test_consumer_accepts_bound_pass_without_enabling_writer"
        )

    def _fixture(self, *, cycle=False):
        case = self._global_case()
        base_extension, expected_binding = case._fixture(cycle=cycle)
        extension = case._extension(base_extension)
        return extension, expected_binding, extension["base_report_hash"]

    def _base_block_fixture(self, **kwargs):
        base_extension, expected_binding = self._strata_case()._fixture(
            **kwargs
        )
        extension = self._global_case()._extension(base_extension)
        return extension, expected_binding, extension["base_report_hash"]

    @staticmethod
    def _reseal(document):
        document["extension_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in document.items()
                if key != "extension_hash"
            }
        )

    @staticmethod
    def _build(document, expected_binding, expected_base_hash):
        return (
            build_strategy_correlation_global_independence_report_public_summary(
                document,
                expected_base_report_hash=expected_base_hash,
                expected_registry_bindings=[expected_binding],
            )
        )

    def test_independent_pass_projects_count_only_research_evidence(self):
        document, expected, base_hash = self._fixture()
        summary = self._build(document, expected, base_hash)
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["entry_count"], 1)
        self.assertEqual(
            summary["gap"]["status"],
            "GLOBAL_INDEPENDENCE_OBSERVED",
        )
        self.assertEqual(summary["gap"]["decision"], "PASS")
        self.assertEqual(
            summary["gap"]["global_independence_blocked_entry_count"],
            0,
        )
        self.assertEqual(summary["maturity"]["status"], "CONSUMER_EVIDENCE_PASS")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_block_sources_preserve_root_gap_class_without_identity(self):
        cycle = self._fixture(cycle=True)
        strata = self._base_block_fixture(shared_stratum=True)
        registry = self._base_block_fixture(expected_source_hash="c" * 64)
        complete_link = self._base_block_fixture(base_blocked=True)
        cases = (
            (cycle, "GLOBAL_INDEPENDENCE_BLOCK_OBSERVED"),
            (strata, "PREREGISTERED_STRATA_BLOCK_OBSERVED"),
            (registry, "REGISTRY_BINDING_BLOCK_OBSERVED"),
            (complete_link, "BASE_COMPLETE_LINK_BLOCK_OBSERVED"),
        )
        for (document, expected, base_hash), expected_gap in cases:
            with self.subTest(expected_gap=expected_gap):
                summary = self._build(document, expected, base_hash)
                self.assertEqual(summary["source"]["status"], "OBSERVED")
                self.assertEqual(summary["gap"]["decision"], "BLOCK")
                self.assertEqual(summary["gap"]["status"], expected_gap)
                self.assertEqual(
                    summary["maturity"]["status"],
                    "CONSUMER_EVIDENCE_BLOCK",
                )

    def test_invalid_external_or_type_aliased_source_projects_unknown(self):
        document, expected, base_hash = self._fixture()
        hostile = copy.deepcopy(document)
        hostile["target_report_schema_version"] = 19.0
        self._reseal(hostile)
        cases = (
            self._build(hostile, expected, base_hash),
            self._build(document, expected, "0" * 64),
            build_strategy_correlation_global_independence_report_public_summary(
                document,
                expected_base_report_hash=base_hash,
                expected_registry_bindings=[],
            ),
        )
        for summary in cases:
            with self.subTest(summary=summary):
                self.assertEqual(summary["source"]["status"], "UNKNOWN")
                self.assertEqual(summary["gap"]["status"], "SOURCE_INVALID")
                self.assertEqual(summary["gap"]["decision"], "UNKNOWN")
                self.assertFalse(summary["permission"]["paper_authorized"])
                self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_pass_block_and_unknown_summaries_are_redacted(self):
        passing = self._fixture()
        blocked = self._fixture(cycle=True)
        unknown_document = copy.deepcopy(passing[0])
        unknown_document["extension_hash"] = "0" * 64
        summaries = (
            self._build(*passing),
            self._build(*blocked),
            self._build(unknown_document, passing[1], passing[2]),
        )
        private_keys = {
            "extension_hash",
            "base_report_hash",
            "strategy_id",
            "variant_id",
            "lane",
            "base_strata_extension",
            "source_preregistration",
            "strata_registration",
            "complete_link_gate",
            "strata_gate",
            "global_independence_gate",
            "registry_asset",
            "registry_binding",
            "decision_blockers",
        }
        private_values = (
            "RAW_EXCESS",
            "candidate-1",
            "external-source",
            "cluster-aaa",
            "cluster-bbb",
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
        document, expected, base_hash = self._fixture()
        summary = self._build(document, expected, base_hash)

        def verify(value):
            return verify_strategy_correlation_global_independence_report_public_summary(
                value,
                source_extension=document,
                expected_base_report_hash=base_hash,
                expected_registry_bindings=[expected],
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
