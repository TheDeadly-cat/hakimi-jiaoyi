import copy
import json
import unittest

from tests import test_strategy_correlation_strata_report_consumer as source_fixtures
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    verify_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strategy_correlation_strata_report_projection import (
    PUBLIC_SUMMARY_SCHEMA,
    build_strategy_correlation_strata_report_public_summary,
    verify_strategy_correlation_strata_report_public_summary,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_canonical_hash,
)


class StrategyCorrelationStrataReportProjectionTests(unittest.TestCase):
    @staticmethod
    def _source_case():
        return source_fixtures.StrategyCorrelationStrataReportConsumerTests(
            "test_consumer_accepts_bound_pass_without_enabling_writer"
        )

    def _fixture(self, **kwargs):
        return self._source_case()._fixture(**kwargs)

    @staticmethod
    def _reseal(document):
        document["extension_hash"] = strict_canonical_hash(
            {
                key: value
                for key, value in document.items()
                if key != "extension_hash"
            }
        )

    def _build(self, document, expected):
        case = self._source_case()
        return build_strategy_correlation_strata_report_public_summary(
            document,
            expected_base_report_hash=case.BASE_HASH,
            expected_registry_bindings=[expected],
        )

    def _verify_source(self, document, expected):
        case = self._source_case()
        return verify_strategy_correlation_strata_report_extension(
            document,
            expected_base_report_hash=case.BASE_HASH,
            expected_registry_bindings=[expected],
        )

    def test_consumer_rejects_resealed_fixed_contract_type_aliases(self):
        document, expected = self._fixture()
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
        self.assertEqual(self._verify_source(document, expected)["status"], "PASS")
        for path, replacement in attacks:
            with self.subTest(path=path):
                hostile = copy.deepcopy(document)
                target = hostile
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                self._reseal(hostile)
                self.assertEqual(
                    self._verify_source(hostile, expected)["status"],
                    "BLOCK",
                )

    def test_bound_pass_projects_count_only_research_evidence(self):
        document, expected = self._fixture()
        summary = self._build(document, expected)
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA)
        self.assertEqual(summary["source"]["status"], "OBSERVED")
        self.assertEqual(summary["source"]["entry_count"], 1)
        self.assertEqual(
            summary["gap"]["status"],
            "INDEPENDENCE_AND_REGISTRY_BINDING_OBSERVED",
        )
        self.assertEqual(summary["gap"]["decision"], "PASS")
        self.assertEqual(summary["gap"]["registry_bound_entry_count"], 1)
        self.assertEqual(summary["maturity"]["registry_binding_outcome"], "ALL_BOUND")
        self.assertEqual(summary["permission"]["status"], "RESEARCH_ONLY")
        self.assertFalse(summary["permission"]["paper_authorized"])
        self.assertFalse(summary["permission"]["live_order_allowed"])

    def test_block_sources_preserve_gap_class_without_identity(self):
        cases = (
            ({"shared_stratum": True}, "PREREGISTERED_STRATA_BLOCK_OBSERVED"),
            (
                {"expected_source_hash": "c" * 64},
                "REGISTRY_BINDING_BLOCK_OBSERVED",
            ),
            ({"base_blocked": True}, "BASE_COMPLETE_LINK_BLOCK_OBSERVED"),
        )
        for fixture_kwargs, expected_gap in cases:
            with self.subTest(expected_gap=expected_gap):
                document, expected = self._fixture(**fixture_kwargs)
                summary = self._build(document, expected)
                self.assertEqual(summary["source"]["status"], "OBSERVED")
                self.assertEqual(summary["gap"]["decision"], "BLOCK")
                self.assertEqual(summary["gap"]["status"], expected_gap)
                self.assertEqual(
                    summary["maturity"]["status"],
                    "CONSUMER_EVIDENCE_BLOCK",
                )

    def test_invalid_or_type_aliased_source_projects_unknown(self):
        document, expected = self._fixture()
        hostile = copy.deepcopy(document)
        hostile["target_report_schema_version"] = 18.0
        self._reseal(hostile)
        cases = (
            self._build(hostile, expected),
            build_strategy_correlation_strata_report_public_summary(
                document,
                expected_base_report_hash=self._source_case().BASE_HASH,
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
        passing, passing_expected = self._fixture()
        blocked, blocked_expected = self._fixture(shared_stratum=True)
        unknown = copy.deepcopy(passing)
        unknown["extension_hash"] = "0" * 64
        summaries = (
            self._build(passing, passing_expected),
            self._build(blocked, blocked_expected),
            self._build(unknown, passing_expected),
        )
        markers = (
            '"extension_hash"',
            '"base_report_hash"',
            '"strategy_id"',
            '"variant_id"',
            "RAW_EXCESS",
            '"source_preregistration"',
            '"strata_registration"',
            '"complete_link_gate"',
            '"strata_gate"',
            '"registry_asset"',
            '"registry_binding"',
            self._source_case().SOURCE_HASH,
        )
        for summary in summaries:
            with self.subTest(status=summary["source"]["status"]):
                serialized = json.dumps(summary, sort_keys=True)
                for marker in markers:
                    self.assertNotIn(marker, serialized)
                self.assertTrue(
                    all(value is False for value in summary["redaction"].values())
                )

    def test_public_verifier_exactly_rebuilds_and_rejects_type_aliases(self):
        document, expected_binding = self._fixture()
        summary = self._build(document, expected_binding)
        case = self._source_case()

        def verify(value):
            return verify_strategy_correlation_strata_report_public_summary(
                value,
                source_extension=document,
                expected_base_report_hash=case.BASE_HASH,
                expected_registry_bindings=[expected_binding],
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
