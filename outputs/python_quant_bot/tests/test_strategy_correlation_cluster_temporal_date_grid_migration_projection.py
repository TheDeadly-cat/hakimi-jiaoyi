from __future__ import annotations

from copy import deepcopy
import json
import unittest

from tests import (
    test_strategy_correlation_cluster_temporal_date_grid_migration_assessment
    as _assessment_test,
)

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_projection
    as _projection,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    MODE_LIST,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_projection import (
    PUBLIC_SUMMARY_SCHEMA_VERSION,
    STATE_DRY_RUN_VERIFIED,
    STATE_NOT_SUPPLIED,
    STATE_PLAN_LISTED,
    STATE_UNKNOWN,
    build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary,
    verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary,
)


class StrategyCorrelationClusterTemporalDateGridMigrationProjectionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        fixture_class = (
            _assessment_test.
            StrategyCorrelationClusterTemporalDateGridMigrationAssessmentTests
        )
        self.fixture = fixture_class(
            methodName="test_list_mode_plans_three_steps_without_report_or_execution"
        )
        self.fixture.setUp()

    def _list_context(self):
        registration = self.fixture._registration()
        arguments = {
            "candidate_registration": registration,
            "mode": MODE_LIST,
            "expected_candidate_registration_hash": registration["registration_hash"],
        }
        return arguments, self.fixture._assess(arguments)

    def _dry_run_context(self, *, misaligned: bool):
        arguments = self.fixture._dry_run_arguments(misaligned=misaligned)
        return arguments, self.fixture._assess(arguments)

    def _build(self, arguments, assessment):
        return build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
            assessment,
            **arguments,
        )

    def _verify(self, document, arguments, assessment):
        return verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
            document,
            assessment,
            **arguments,
        )

    def test_not_supplied_is_distinct_from_unknown(self):
        not_supplied = (
            build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary()
        )
        unknown = (
            build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                {}
            )
        )

        self.assertEqual(not_supplied["source"]["state"], STATE_NOT_SUPPLIED)
        self.assertEqual(unknown["source"]["state"], STATE_UNKNOWN)
        self.assertEqual(
            verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                not_supplied
            )["status"],
            "PASS",
        )
        self.assertEqual(
            verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary(
                unknown,
                {},
            )["status"],
            "PASS",
        )

    def test_valid_list_is_plan_listed_without_execution(self):
        arguments, assessment = self._list_context()
        summary = self._build(arguments, assessment)

        self.assertEqual(summary["source"]["state"], STATE_PLAN_LISTED)
        self.assertEqual(summary["source"]["assessment_mode"], "LIST")
        self.assertEqual(summary["source"]["report22_contract"], "NOT_EVALUATED")
        self.assertEqual(summary["gap"]["execution"], "NOT_EXECUTED")
        self.assertEqual(summary["maturity"]["state"], "PLAN_LISTED_NOT_EXECUTED")
        self.assertEqual(self._verify(summary, arguments, assessment)["status"], "PASS")

    def test_valid_dry_run_pass_is_descriptive_only(self):
        arguments, assessment = self._dry_run_context(misaligned=False)
        summary = self._build(arguments, assessment)

        self.assertEqual(summary["source"]["state"], STATE_DRY_RUN_VERIFIED)
        self.assertEqual(summary["source"]["report22_decision"], "PASS")
        self.assertEqual(summary["gap"]["execution"], "NOT_EXECUTED")
        self.assertFalse(summary["permission"]["migration_execution_allowed"])
        self.assertFalse(summary["permission"]["current_admission_allowed"])
        self.assertEqual(self._verify(summary, arguments, assessment)["status"], "PASS")

    def test_valid_dry_run_preserves_report22_block(self):
        arguments, assessment = self._dry_run_context(misaligned=True)
        summary = self._build(arguments, assessment)

        self.assertEqual(summary["source"]["state"], STATE_DRY_RUN_VERIFIED)
        self.assertEqual(summary["source"]["report22_decision"], "BLOCK")
        self.assertEqual(summary["maturity"]["state"], "DRY_RUN_VERIFIED_NOT_EXECUTED")
        self.assertEqual(self._verify(summary, arguments, assessment)["status"], "PASS")

    def test_invalid_assessment_maps_to_unknown(self):
        arguments, assessment = self._dry_run_context(misaligned=False)
        tampered = deepcopy(assessment)
        tampered["executed"] = 1

        summary = self._build(arguments, tampered)

        self.assertEqual(summary["source"]["state"], STATE_UNKNOWN)
        self.assertEqual(summary["source"]["report22_decision"], "UNKNOWN")
        self.assertFalse(summary["permission"]["migration_execution_allowed"])

    def test_resealed_execution_or_current_claim_is_rejected(self):
        arguments, assessment = self._dry_run_context(misaligned=False)
        summary = self._build(arguments, assessment)
        resealed = deepcopy(summary)
        resealed["gap"]["execution"] = "EXECUTED"
        resealed["permission"]["current_admission_allowed"] = True

        verification = self._verify(resealed, arguments, assessment)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["exact_reconstruction"])
        self.assertFalse(verification["current_admission_allowed"])

    def test_native_bool_integer_alias_is_rejected(self):
        arguments, assessment = self._dry_run_context(misaligned=False)
        summary = self._build(arguments, assessment)
        aliased = deepcopy(summary)
        aliased["permission"]["descriptive_only"] = 1

        verification = self._verify(aliased, arguments, assessment)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertFalse(verification["exact_reconstruction"])

    def test_extra_authority_field_is_rejected(self):
        arguments, assessment = self._list_context()
        summary = self._build(arguments, assessment)
        escalated = deepcopy(summary)
        escalated["permission"]["ready"] = True

        self.assertEqual(
            self._verify(escalated, arguments, assessment)["status"],
            "BLOCK",
        )

    def test_projection_is_exactly_redacted_and_neutral(self):
        arguments, assessment = self._dry_run_context(misaligned=False)
        assessment_before = deepcopy(assessment)
        arguments_before = deepcopy(arguments)
        summary = self._build(arguments, assessment)
        payload = json.dumps(summary, sort_keys=True)

        self.assertEqual(
            list(summary),
            [
                "schema_version",
                "contract_fingerprint",
                "axis_order",
                "source",
                "gap",
                "maturity",
                "permission",
                "redaction",
            ],
        )
        self.assertEqual(summary["schema_version"], PUBLIC_SUMMARY_SCHEMA_VERSION)
        self.assertEqual(
            summary["axis_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertTrue(all(value is False for value in summary["redaction"].values()))
        self.assertNotIn("READY", payload.upper())
        self.assertNotIn("assessment_hash", summary)
        self.assertNotIn("candidate_registration", summary)
        self.assertNotIn("report22_extension", summary)
        self.assertNotIn("facts", summary)
        self.assertNotIn("blockers", summary)
        self.assertNotIn("plan", summary)
        for key, value in assessment.items():
            if "hash" in key and type(value) is str and value:
                self.assertNotIn(value, payload)
        self.assertEqual(assessment, assessment_before)
        self.assertEqual(arguments, arguments_before)

    def test_exports_have_no_route_writer_migration_or_current_operation(self):
        public_callables = sorted(
            name
            for name, value in vars(_projection).items()
            if not name.startswith("_")
            and callable(value)
            and getattr(value, "__module__", None) == _projection.__name__
        )

        self.assertEqual(
            public_callables,
            [
                "build_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
                "verify_strategy_correlation_cluster_temporal_date_grid_migration_public_summary",
            ],
        )
        for name in public_callables:
            self.assertNotIn("route", name)
            self.assertNotIn("writer", name)
            self.assertNotIn("current", name)
            self.assertNotIn("activate", name)
            self.assertNotIn("execute", name)


if __name__ == "__main__":
    unittest.main()
