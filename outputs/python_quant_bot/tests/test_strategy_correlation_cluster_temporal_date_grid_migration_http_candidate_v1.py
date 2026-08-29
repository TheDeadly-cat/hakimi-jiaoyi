from __future__ import annotations

import copy
import inspect
import json
import re
import unittest
from unittest.mock import patch

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_temporal_date_grid_migration_candidate_v1 as subject,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    MODE_LIST,
)
from tests import (
    test_strategy_correlation_cluster_temporal_date_grid_migration_assessment as assessment_fixtures,
)


class StrategyCorrelationClusterTemporalDateGridMigrationHttpCandidateV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        fixture_class = (
            assessment_fixtures.
            StrategyCorrelationClusterTemporalDateGridMigrationAssessmentTests
        )
        self.fixture = fixture_class(
            methodName="test_list_mode_plans_three_steps_without_report_or_execution"
        )
        self.fixture.setUp()
        self.request = {"schema_version": subject.REQUEST_SCHEMA_VERSION}

    def _list_case(self):
        registration = self.fixture._registration()
        arguments = {
            "candidate_registration": registration,
            "mode": MODE_LIST,
            "expected_candidate_registration_hash": registration["registration_hash"],
        }
        assessment = self.fixture._assess(arguments)
        context = {
            "schema_version": subject.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }
        return assessment, context

    def _dry_run_case(self, *, misaligned: bool):
        arguments = self.fixture._dry_run_arguments(misaligned=misaligned)
        assessment = self.fixture._assess(arguments)
        context = {
            "schema_version": subject.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }
        return assessment, context

    def _build(self, assessment, context):
        return subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request,
            migration_assessment=assessment,
            verification_context=context,
        )

    def test_not_supplied_projection_is_safe_and_distinct(self) -> None:
        response = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request
        )

        self.assertEqual(response["state"], "NOT_SUPPLIED")
        self.assertEqual(response["payload"]["source"]["state"], "NOT_SUPPLIED")
        self.assertTrue(response["facts"]["source_projection_verified"])
        self.assertFalse(response["facts"]["migration_assessment_supplied"])
        self.assertFalse(response["facts"]["source_assessment_observed"])

    def test_verified_list_is_carried_without_report22_evaluation(self) -> None:
        assessment, context = self._list_case()
        response = self._build(assessment, context)

        self.assertEqual(response["state"], "PLAN_LISTED")
        self.assertEqual(response["payload"]["source"]["assessment_mode"], "LIST")
        self.assertEqual(
            response["payload"]["source"]["report22_decision"],
            "NOT_EVALUATED",
        )
        self.assertFalse(response["facts"]["report22_evaluated"])
        self.assertIn("REPORT22_NOT_EVALUATED", response["blockers"])

    def test_dry_run_pass_and_block_are_preserved_without_execution(self) -> None:
        for misaligned, expected in ((False, "PASS"), (True, "BLOCK")):
            with self.subTest(expected=expected):
                assessment, context = self._dry_run_case(misaligned=misaligned)
                response = self._build(assessment, context)
                self.assertEqual(response["state"], "DRY_RUN_VERIFIED")
                self.assertEqual(
                    response["payload"]["source"]["report22_decision"],
                    expected,
                )
                self.assertTrue(response["facts"]["report22_evaluated"])
                self.assertFalse(response["authority"]["migration_execution_allowed"])
                self.assertFalse(response["authority"]["current_admission_allowed"])

    def test_invalid_assessment_produces_verified_unknown_payload(self) -> None:
        assessment, context = self._dry_run_case(misaligned=False)
        assessment["executed"] = 1

        response = self._build(assessment, context)

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertEqual(response["payload"]["source"]["state"], "UNKNOWN")
        self.assertTrue(response["facts"]["source_projection_verified"])
        self.assertFalse(response["facts"]["source_assessment_observed"])

    def test_request_contract_is_schema_only_and_exact(self) -> None:
        cases = [
            None,
            {},
            {"schema_version": "wrong"},
            {"schema_version": subject.REQUEST_SCHEMA_VERSION, "assessment": {}},
            {"schema_version": subject.REQUEST_SCHEMA_VERSION, "ready": True},
        ]
        for request in cases:
            with self.subTest(request=request):
                response = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
                    request
                )
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])
                self.assertFalse(response["facts"]["request_contract_valid"])

    def test_context_contract_is_mode_specific_and_fail_closed(self) -> None:
        assessment, context = self._list_case()
        invalid_contexts = [
            None,
            {},
            {**context, "unexpected": True},
            {**context, "schema_version": "wrong"},
            {**context, "mode": 1},
            {**context, "report22_extension": {}},
        ]
        for invalid in invalid_contexts:
            with self.subTest(context=invalid), patch.object(
                subject.projection_contract,
                "build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
            ) as builder:
                response = self._build(assessment, invalid)
                builder.assert_not_called()
                self.assertEqual(response["state"], "UNKNOWN")
                self.assertIsNone(response["payload"])
                self.assertEqual(
                    response["blockers"],
                    ["VERIFICATION_CONTEXT_INVALID"],
                )

    def test_unexpected_context_for_absent_assessment_fails_closed(self) -> None:
        response = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request,
            verification_context={},
        )

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])
        self.assertEqual(response["blockers"], ["VERIFICATION_CONTEXT_UNEXPECTED"])

    def test_forged_projection_authority_is_rejected_even_with_pass_verifier(self) -> None:
        assessment, context = self._dry_run_case(misaligned=False)
        arguments = {
            key: value
            for key, value in context.items()
            if key != "schema_version"
        }
        summary = subject.projection_contract.build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
            assessment,
            **arguments,
        )
        verification = subject.projection_contract.verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
            summary,
            assessment,
            **arguments,
        )
        forged = copy.deepcopy(summary)
        forged["permission"]["paper_authorized"] = True
        with patch.object(
            subject.projection_contract,
            "build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
            return_value=forged,
        ), patch.object(
            subject.projection_contract,
            "verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
            return_value=verification,
        ):
            response = self._build(assessment, context)

        self.assertEqual(response["state"], "UNKNOWN")
        self.assertIsNone(response["payload"])
        self.assertEqual(response["blockers"], ["SOURCE_PROJECTION_UNVERIFIED"])

    def test_assessment_context_hashes_and_bindings_are_not_echoed(self) -> None:
        assessment, context = self._dry_run_case(misaligned=False)
        response = self._build(assessment, context)
        serialized = json.dumps(response, sort_keys=True)
        private_hashes = set(
            re.findall(
                r"[0-9a-f]{64}",
                json.dumps(
                    {"assessment": assessment, "context": context},
                    sort_keys=True,
                ),
            )
        )

        self.assertTrue(private_hashes)
        for private_hash in private_hashes:
            self.assertNotIn(private_hash, serialized)
        self.assertFalse(response["lineage"]["migration_assessment_embedded"])
        self.assertFalse(response["lineage"]["verification_context_embedded"])
        self.assertFalse(response["lineage"]["report22_extension_embedded"])
        self.assertFalse(response["lineage"]["source_hashes_embedded"])

    def test_transport_is_unregistered_side_effect_free_and_body_log_free(self) -> None:
        assessment, context = self._list_case()
        response = self._build(assessment, context)

        self.assertEqual(
            response["transport"],
            {
                "registered": False,
                "externally_callable": False,
                "method": None,
                "route": None,
                "runtime_reads": False,
                "runtime_mutations": False,
                "cache_reads": False,
                "cache_writes": False,
                "request_body_logging": False,
            },
        )
        self.assertEqual(response["interface_status"], "UNREGISTERED_CANDIDATE")
        self.assertFalse(response["facts"]["runtime_asset_accessed"])

    def test_exact_rebuild_is_deterministic_and_rejects_transport_reseal(self) -> None:
        assessment, context = self._dry_run_case(misaligned=True)
        first = self._build(assessment, context)
        second = self._build(assessment, context)
        self.assertEqual(first, second)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
                first,
                self.request,
                migration_assessment=assessment,
                verification_context=context,
            )
        )
        tampered = copy.deepcopy(first)
        tampered["transport"]["registered"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
                tampered,
                self.request,
                migration_assessment=assessment,
                verification_context=context,
            )
        )

    def test_authority_is_research_only_and_contains_no_ready_signal(self) -> None:
        assessment, context = self._dry_run_case(misaligned=False)
        response = self._build(assessment, context)

        self.assertTrue(response["authority"]["descriptive_only"])
        for field, value in response["authority"].items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(response, sort_keys=True).upper())

    def test_schema_hash_and_public_api_are_stable_and_non_operational(self) -> None:
        assessment, context = self._list_case()
        response = self._build(assessment, context)

        self.assertEqual(response["schema_version"], subject.RESPONSE_SCHEMA_VERSION)
        self.assertEqual(response["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(response["response_hash"], r"^[0-9a-f]{64}$")
        exported_callables = [
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1,
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1,
        ]
        for function in exported_callables:
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "runtime",
                        "database",
                        "cache",
                        "private_key",
                        "authentication_token",
                        "route",
                        "method",
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
