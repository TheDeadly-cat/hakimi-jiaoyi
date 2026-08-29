from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1 import (
    PROJECTION_SCHEMA_VERSION,
    PROJECTION_VERIFICATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    build_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1,
    verify_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_portfolio_risk_session_freshness_v1
    as freshness_tests,
)


_DEFAULT = object()


class StrategyCorrelationClusterPortfolioRiskSessionFreshnessProjectionV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.case = (
            freshness_tests.StrategyCorrelationClusterPortfolioRiskSessionFreshnessV1Tests(
                methodName="test_cutoff_session_at_exact_close_has_zero_lag"
            )
        )
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.clock = self.case._clock()
        self.evaluation = self.case._evaluate(clock=self.clock)

    def _projection(self, evaluation=_DEFAULT, *, clock=_DEFAULT):
        evaluation = self.evaluation if evaluation is _DEFAULT else evaluation
        clock = self.clock if clock is _DEFAULT else clock
        with self.case.native_case.fixture.source_verifiers():
            return build_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1(
                evaluation,
                self.case.registration,
                registration_inputs=self.case.registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=clock["attestation_hash"],
            )

    def _verify(self, projection, evaluation=_DEFAULT, *, clock=_DEFAULT):
        evaluation = self.evaluation if evaluation is _DEFAULT else evaluation
        clock = self.clock if clock is _DEFAULT else clock
        with self.case.native_case.fixture.source_verifiers():
            return verify_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1(
                projection,
                evaluation,
                self.case.registration,
                registration_inputs=self.case.registration_inputs,
                trusted_clock_attestation=clock,
                expected_trusted_clock_attestation_hash=clock["attestation_hash"],
            )

    @staticmethod
    def _all_keys(value):
        keys = set()
        if type(value) is dict:
            keys.update(value)
            for item in value.values():
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskSessionFreshnessProjectionV1Tests._all_keys(
                        item
                    )
                )
        elif type(value) is list:
            for item in value:
                keys.update(
                    StrategyCorrelationClusterPortfolioRiskSessionFreshnessProjectionV1Tests._all_keys(
                        item
                    )
                )
        return keys

    def test_not_supplied_is_explicit_and_unauthorized(self):
        projection = self._projection(None)
        self.assertEqual(projection["status"], "NOT_SUPPLIED")
        self.assertEqual(
            [item["state"] for item in projection["pipeline"]],
            ["NOT_SUPPLIED", "NOT_SUPPLIED", "UNMOUNTED_CANDIDATE", "UNAUTHORIZED"],
        )
        self.assertEqual(projection["summary"]["evaluation_decision"], "NOT_SUPPLIED")

    def test_within_policy_remains_an_external_authority_gap(self):
        projection = self._projection()
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(projection["pipeline"][0]["state"], "VERIFIED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
        )
        self.assertEqual(projection["summary"]["max_completed_session_lag"], 0)
        self.assertEqual(
            projection["summary"]["preregistered_max_completed_session_lag"], 1
        )
        self.assertFalse(
            projection["summary"]["external_clock_authority_authenticated"]
        )
        self.assertFalse(projection["summary"]["freshness_externally_proven"])

    def test_exact_stale_evaluation_projects_policy_gap(self):
        clock = self.case._clock("2026-12-22T00:00:00Z")
        evaluation = self.case._evaluate(clock=clock)
        projection = self._projection(evaluation, clock=clock)
        self.assertEqual(projection["status"], "OBSERVED")
        self.assertEqual(
            projection["pipeline"][1]["state"],
            "SESSION_LAG_POLICY_GAP_PRESENT",
        )
        self.assertEqual(projection["summary"]["evaluation_status"], "BLOCK")
        self.assertEqual(projection["summary"]["max_completed_session_lag"], 2)
        self.assertFalse(projection["summary"]["local_policy_condition_satisfied"])

    def test_exact_invalid_source_evidence_projects_unknown(self):
        clock = self.case._clock(source_count=1, minimum_sources=1)
        evaluation = self.case._evaluate(clock=clock)
        projection = self._projection(evaluation, clock=clock)
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertEqual(projection["pipeline"][0]["state"], "UNKNOWN")
        self.assertEqual(projection["pipeline"][1]["state"], "UNKNOWN")
        self.assertIsNone(projection["summary"]["max_completed_session_lag"])

    def test_resealed_evaluation_tamper_projects_unknown(self):
        tampered = deepcopy(self.evaluation)
        tampered["decision"] = "READY"
        tampered.pop("evaluation_hash")
        tampered = seal_strict_canonical_document(tampered, "evaluation_hash")
        projection = self._projection(tampered)
        self.assertEqual(projection["status"], "UNKNOWN")
        self.assertFalse(projection["source"]["evaluation_exactly_verified"])

    def test_projection_redacts_private_sources_and_calendar_detail(self):
        projection = self._projection()
        forbidden = {
            "price_rows",
            "completed_price_input",
            "matrix_replay",
            "observation_batch",
            "sources",
            "endpoint",
            "by_calendar",
            "calendar_id",
            "calendar_id_hash",
            "raw_correlations",
        }
        self.assertFalse(self._all_keys(projection) & forbidden)
        encoded = json.dumps(projection, ensure_ascii=True, sort_keys=True)
        self.assertNotIn("clock-1.invalid", encoded)

    def test_authority_and_natural_forward_chain_remain_locked(self):
        projection = self._projection()
        self.assertTrue(projection["authority"]["descriptive_only"])
        for key, value in projection["authority"].items():
            if key != "descriptive_only":
                self.assertIs(value, False)
        self.assertFalse(projection["facts"]["runtime_consumer_mounted"])
        self.assertFalse(projection["facts"]["natural_forward_chain_changed"])
        self.assertFalse(
            projection["facts"]["external_time_authority_authenticated"]
        )

    def test_verifier_requires_exact_rebuild(self):
        projection = self._projection()
        verification = self._verify(projection)
        self.assertEqual(verification["status"], "PASS")
        self.assertTrue(verification["projection_exactly_verified"])
        tampered = deepcopy(projection)
        tampered["pipeline"][3]["state"] = "AUTHORIZED"
        self.assertEqual(self._verify(tampered)["status"], "BLOCK")

    def test_python_projection_is_consumed_by_node_view_model(self):
        projection = self._projection()
        card_path = (
            Path(__file__).resolve().parents[1]
            / "exchange_terminal"
            / "static"
            / "evidence_portfolio_risk_session_freshness_card_v1.js"
        )
        script = (
            "const fs=require('node:fs');"
            "const card=require(process.argv[1]);"
            "const input=JSON.parse(fs.readFileSync(0,'utf8'));"
            "const view=card.buildSessionFreshnessViewModel(input);"
            "process.stdout.write(JSON.stringify({valid:view.validContract,"
            "source:view.sourceState,gap:view.gapState,permission:view.permissionState}));"
        )
        completed = subprocess.run(
            ["node", "-e", script, str(card_path)],
            input=json.dumps(projection, ensure_ascii=True),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(
            result,
            {
                "valid": True,
                "source": "VERIFIED",
                "gap": "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
                "permission": "UNAUTHORIZED",
            },
        )

    def test_schema_fingerprint_and_verification_schema_are_locked(self):
        projection = self._projection()
        verification = self._verify(projection)
        self.assertEqual(projection["schema_version"], PROJECTION_SCHEMA_VERSION)
        self.assertEqual(projection["static_fingerprint"], STATIC_FINGERPRINT)
        self.assertEqual(
            verification["schema_version"], PROJECTION_VERIFICATION_SCHEMA_VERSION
        )


if __name__ == "__main__":
    unittest.main()
