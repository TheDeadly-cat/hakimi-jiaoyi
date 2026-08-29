from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_temporal_date_grid_migration_candidate_v1 as candidate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_migration_assessment import (
    MODE_LIST,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_temporal_date_grid_migration_assessment as assessment_fixtures,
)


class StrategyCorrelationClusterTemporalDateGridMigrationCrossRuntimeBindingV1Tests(
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
        self.request = {"schema_version": candidate.REQUEST_SCHEMA_VERSION}
        self.root = Path(__file__).resolve().parents[1]
        self.binding_path = self.root / (
            "exchange_terminal/static/"
            "evidence_report22_date_grid_migration_http_binding.js"
        )

    def _list_response(self):
        registration = self.fixture._registration()
        arguments = {
            "candidate_registration": registration,
            "mode": MODE_LIST,
            "expected_candidate_registration_hash": registration["registration_hash"],
        }
        assessment = self.fixture._assess(arguments)
        context = {
            "schema_version": candidate.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }
        return candidate.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request,
            migration_assessment=assessment,
            verification_context=context,
        )

    def _dry_response(self, *, misaligned: bool):
        arguments = self.fixture._dry_run_arguments(misaligned=misaligned)
        assessment = self.fixture._assess(arguments)
        context = {
            "schema_version": candidate.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }
        return candidate.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request,
            migration_assessment=assessment,
            verification_context=context,
        )

    def _unknown_response(self):
        arguments = self.fixture._dry_run_arguments(misaligned=False)
        assessment = self.fixture._assess(arguments)
        assessment["executed"] = 1
        context = {
            "schema_version": candidate.VERIFICATION_CONTEXT_SCHEMA_VERSION,
            **arguments,
        }
        return candidate.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
            self.request,
            migration_assessment=assessment,
            verification_context=context,
        )

    def _node_present(self, responses):
        script = r"""
const fs = require('node:fs');
const binding = require(process.argv[1]);
const responses = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = responses.map((response) => {
  const model = binding.presentReport22DateGridMigrationFromHttpCandidate(response);
  return {
    verified: binding.verifyReport22DateGridMigrationHttpCandidateResponse(response),
    variant: model.variant,
    state: model.state,
    decision: model.decision,
    binding_status: model.httpBinding.status,
    response_hash_verified: model.httpBinding.response_hash_verified,
    current_admission_allowed: model.httpBinding.current_admission_allowed,
    serialized_model: JSON.stringify(model),
  };
});
process.stdout.write(JSON.stringify(result));
"""
        completed = subprocess.run(
            ["node", "-e", script, str(self.binding_path)],
            cwd=self.root,
            input=json.dumps(responses, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=True,
            timeout=20,
        )
        return json.loads(completed.stdout)

    def test_python_responses_verify_and_map_to_node_states(self) -> None:
        responses = [
            candidate.build_strategy_correlation_cluster_temporal_date_grid_migration_http_candidate_response_v1(
                self.request
            ),
            self._unknown_response(),
            self._list_response(),
            self._dry_response(misaligned=False),
            self._dry_response(misaligned=True),
        ]
        results = self._node_present(responses)

        self.assertEqual(
            [(item["state"], item["decision"]) for item in results],
            [
                ("NOT_SUPPLIED", "NOT_SUPPLIED"),
                ("UNKNOWN", "UNKNOWN"),
                ("PLAN_LISTED", "NOT_EVALUATED"),
                ("DRY_RUN_VERIFIED", "PASS"),
                ("DRY_RUN_VERIFIED", "BLOCK"),
            ],
        )
        for result in results:
            self.assertTrue(result["verified"])
            self.assertEqual(result["variant"], "report22-date-grid")
            self.assertEqual(result["binding_status"], "VERIFIED_HTTP_CANDIDATE")
            self.assertTrue(result["response_hash_verified"])
            self.assertFalse(result["current_admission_allowed"])

    def test_hash_tamper_and_resealed_authority_drift_fail_closed_in_node(self) -> None:
        response = self._dry_response(misaligned=False)
        hash_tampered = copy.deepcopy(response)
        hash_tampered["response_hash"] = "0" * 64
        authority_drift = copy.deepcopy(response)
        authority_drift["payload"]["permission"]["paper_authorized"] = True
        authority_drift = seal_strict_canonical_document(
            authority_drift,
            "response_hash",
        )

        results = self._node_present([hash_tampered, authority_drift])

        for result in results:
            self.assertFalse(result["verified"])
            self.assertEqual(result["variant"], "unverified-contract")
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(result["binding_status"], "UNKNOWN")
            self.assertFalse(result["response_hash_verified"])
            self.assertFalse(result["current_admission_allowed"])

    def test_cross_runtime_models_remain_neutral_and_redacted(self) -> None:
        result = self._node_present([self._dry_response(misaligned=False)])[0]
        serialized = result["serialized_model"].upper()

        self.assertNotIn("READY", serialized)
        self.assertNotIn("ASSESSMENT_HASH", serialized)
        self.assertNotIn("REPORT22_EXTENSION_HASH", serialized)
        self.assertNotIn("PAPER_AUTHORIZED\":TRUE", serialized)
        self.assertNotIn("LIVE_ORDER_ALLOWED\":TRUE", serialized)


if __name__ == "__main__":
    unittest.main()
