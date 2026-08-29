from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1
    as subject,
)


class StrategyCorrelationClusterPortfolioRiskSessionFreshnessPresentationReviewV1Tests(
    unittest.TestCase
):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.document = subject.build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1()

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_status_is_candidate_bound_but_not_mounted(self):
        self.assertEqual(self.document["status"], "CANDIDATE_BOUND_NOT_MOUNTED")
        self.assertTrue(
            self.document["review"]["static_consumer_binding_review_complete"]
        )
        self.assertFalse(self.document["review"]["frontend_dom_mount_review_complete"])
        self.assertFalse(self.document["review"]["browser_visual_review_complete"])
        self.assertFalse(self.document["review"]["independent_review_complete"])
        self.assertEqual(self.document["blockers"], list(subject.REVIEW_BLOCKERS))

    def test_source_contract_hash_pins_match_current_files(self):
        paths = {
            "evaluation": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_session_freshness_v1.py",
            "projection": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1.py",
            "javascript": self.root
            / "exchange_terminal/static/evidence_portfolio_risk_session_freshness_card_v1.js",
            "stylesheet": self.root
            / "exchange_terminal/static/evidence_portfolio_risk_session_freshness_card_v1.css",
        }
        self.assertEqual(
            self._sha256(paths["evaluation"]),
            subject.SESSION_FRESHNESS_EVALUATION_SHA256,
        )
        self.assertEqual(
            self._sha256(paths["projection"]), subject.PUBLIC_PROJECTION_SHA256
        )
        self.assertEqual(
            self._sha256(paths["javascript"]), subject.CARD_JAVASCRIPT_SHA256
        )
        self.assertEqual(
            self._sha256(paths["stylesheet"]), subject.CARD_STYLESHEET_SHA256
        )

    def test_executable_evidence_hash_pins_match_current_files(self):
        paths = {
            "freshness": self.root
            / "tests/test_strategy_correlation_cluster_portfolio_risk_session_freshness_v1.py",
            "cross_runtime": self.root
            / "tests/test_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1.py",
            "node_card": self.root
            / "exchange_terminal/static/evidence_portfolio_risk_session_freshness_card_v1.test.js",
            "suite_v17": self.root
            / "exchange_terminal/static/evidence_presentation_suite_v17.test.js",
        }
        self.assertEqual(
            self._sha256(paths["freshness"]), subject.SESSION_FRESHNESS_TEST_SHA256
        )
        self.assertEqual(
            self._sha256(paths["cross_runtime"]),
            subject.PYTHON_CROSS_RUNTIME_TEST_SHA256,
        )
        self.assertEqual(
            self._sha256(paths["node_card"]), subject.NODE_CARD_TEST_SHA256
        )
        self.assertEqual(
            self._sha256(paths["suite_v17"]),
            subject.PRESENTATION_SUITE_V17_SHA256,
        )

    def test_reviewed_frontend_mount_source_hashes_match(self):
        app = self.root / "exchange_terminal/static/app.js"
        index = self.root / "exchange_terminal/static/index.html"
        pins = self.document["source_contract_pins"][
            "reviewed_frontend_mount_sources"
        ]
        self.assertEqual(self._sha256(app), subject.APP_JAVASCRIPT_SHA256)
        self.assertEqual(self._sha256(index), subject.INDEX_HTML_SHA256)
        self.assertEqual(pins["app_javascript_sha256"], subject.APP_JAVASCRIPT_SHA256)
        self.assertEqual(pins["index_html_sha256"], subject.INDEX_HTML_SHA256)

    def test_pinned_frontend_sources_do_not_mount_candidate(self):
        app = (self.root / "exchange_terminal/static/app.js").read_text(
            encoding="utf-8"
        )
        index = (self.root / "exchange_terminal/static/index.html").read_text(
            encoding="utf-8"
        )
        for text in (app, index):
            self.assertNotIn("HakimiPortfolioRiskSessionFreshnessCardV1", text)
            self.assertNotIn(
                "evidence_portfolio_risk_session_freshness_card_v1",
                text,
            )
        self.assertTrue(
            self.document["facts"]["current_frontend_sources_do_not_mount_candidate"]
        )
        self.assertFalse(self.document["facts"]["frontend_dom_mounted"])

    def test_schema_fingerprint_and_state_matrix_are_exact(self):
        pins = self.document["source_contract_pins"]
        self.assertEqual(
            pins["session_freshness_evaluation"]["schema_version"],
            subject.SESSION_FRESHNESS_EVALUATION_SCHEMA,
        )
        self.assertEqual(
            pins["public_projection"]["schema_version"],
            subject.PUBLIC_PROJECTION_SCHEMA,
        )
        self.assertEqual(
            pins["public_projection"]["static_fingerprint"],
            subject.PUBLIC_PROJECTION_STATIC_FINGERPRINT,
        )
        contract = self.document["binding_contract"]
        self.assertEqual(
            contract["axis_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(
            contract["state_matrix"],
            [
                "NOT_SUPPLIED",
                "UNKNOWN",
                "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP",
                "SESSION_LAG_POLICY_GAP_PRESENT",
                "UNVERIFIED_FRESHNESS_EVIDENCE_GAP",
            ],
        )

    def test_binding_contract_is_fail_closed_and_cross_runtime(self):
        contract = self.document["binding_contract"]
        self.assertTrue(contract["complete_source_hash_lineage_required"])
        self.assertTrue(contract["commonjs_contract_available"])
        self.assertTrue(contract["browser_global_vm_contract_available"])
        self.assertTrue(contract["python_to_node_contract_available"])
        self.assertEqual(contract["invalid_projection_fallback"], "UNKNOWN")
        self.assertEqual(contract["permission_fallback"], "UNAUTHORIZED")

    def test_test_definitions_are_pinned_without_execution_results(self):
        evidence = self.document["executable_evidence_pins"]
        self.assertFalse(evidence["test_execution_results_embedded"])
        self.assertFalse(evidence["historical_test_totals_embedded"])
        self.assertTrue(self.document["facts"]["executable_evidence_sources_pinned"])
        self.assertTrue(self.document["facts"]["cross_runtime_contract_available"])

    def test_static_review_is_not_browser_runtime_or_external_trust(self):
        review = self.document["review"]
        facts = self.document["facts"]
        self.assertTrue(review["frontend_mount_source_review_complete"])
        self.assertFalse(review["actual_http_transport_review_complete"])
        self.assertFalse(review["browser_visual_review_complete"])
        self.assertFalse(review["runtime_asset_review_complete"])
        self.assertFalse(facts["browser_process_exercised"])
        self.assertFalse(facts["runtime_assets_accessed"])
        self.assertFalse(facts["external_time_authority_authenticated"])
        self.assertFalse(facts["freshness_externally_proven"])

    def test_authority_is_locked_and_copy_has_no_ready_signal(self):
        authority = self.document["authority"]
        self.assertTrue(authority["descriptive_only"])
        for field, value in authority.items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(self.document, sort_keys=True).upper())

    def test_build_api_accepts_no_caller_override(self):
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1
        )
        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1(
                browser_review=True
            )

    def test_exact_rebuild_is_deterministic_and_tamper_evident(self):
        rebuilt = subject.build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1()
        self.assertEqual(self.document, rebuilt)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1(
                self.document
            )
        )
        for mutation in (
            lambda value: value["review"].update(
                {"browser_visual_review_complete": True}
            ),
            lambda value: value["facts"].update({"frontend_dom_mounted": True}),
            lambda value: value["authority"].update({"mount_allowed": True}),
            lambda value: value["source_contract_pins"]["browser_card"].update(
                {"javascript_sha256": "0" * 64}
            ),
        ):
            tampered = copy.deepcopy(self.document)
            mutation(tampered)
            self.assertFalse(
                subject.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1(
                    tampered
                )
            )

    def test_schema_hash_and_public_api_are_stable(self):
        self.assertEqual(self.document["schema_version"], subject.REVIEW_SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(self.document["review_hash"], r"^[0-9a-f]{64}$")
        for function in (
            subject.build_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1,
            subject.verify_strategy_correlation_cluster_portfolio_risk_session_freshness_presentation_review_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "runtime",
                        "database",
                        "cache",
                        "route",
                        "browser",
                        "authentication_token",
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
