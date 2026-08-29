from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1 as subject,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1 as mount_contract,
)


class StrategyCorrelationClusterTemporalDateGridMigrationConsumerBindingReviewV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.document = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1()

    def test_status_is_candidate_bound_but_never_mounted(self) -> None:
        self.assertEqual(self.document["status"], "CANDIDATE_BOUND_NOT_MOUNTED")
        self.assertTrue(
            self.document["review"]["static_consumer_binding_review_complete"]
        )
        self.assertFalse(
            self.document["review"]["actual_http_transport_review_complete"]
        )
        self.assertFalse(
            self.document["review"]["frontend_dom_mount_review_complete"]
        )
        self.assertFalse(self.document["review"]["browser_visual_review_complete"])
        self.assertEqual(self.document["blockers"], list(subject.REVIEW_BLOCKERS))

    def test_source_contract_hash_pins_match_current_files(self) -> None:
        paths = {
            "http_candidate": self.root
            / "exchange_terminal/interfaces/http/strategy_correlation_cluster_temporal_date_grid_migration_candidate_v1.py",
            "public_projection": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_temporal_date_grid_migration_projection.py",
            "mount_preregistration": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1.py",
            "lockboard": self.root
            / "exchange_terminal/static/evidence_report22_date_grid_migration_lockboard.js",
            "http_binding": self.root
            / "exchange_terminal/static/evidence_report22_date_grid_migration_http_binding.js",
        }
        actual = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        }

        self.assertEqual(actual["http_candidate"], subject.HTTP_CANDIDATE_SHA256)
        self.assertEqual(actual["public_projection"], subject.PUBLIC_PROJECTION_SHA256)
        self.assertEqual(
            actual["mount_preregistration"],
            subject.MOUNT_PREREGISTRATION_SHA256,
        )
        self.assertEqual(actual["lockboard"], subject.LOCKBOARD_SHA256)
        self.assertEqual(actual["http_binding"], subject.HTTP_BINDING_SHA256)

    def test_executable_evidence_hash_pins_match_current_files(self) -> None:
        paths = {
            "node_binding_test": self.root
            / "exchange_terminal/static/evidence_report22_date_grid_migration_http_binding.test.js",
            "suite_v15": self.root
            / "exchange_terminal/static/evidence_presentation_suite_v15.test.js",
            "python_cross_runtime_test": self.root
            / "tests/test_strategy_correlation_cluster_temporal_date_grid_migration_cross_runtime_binding_v1.py",
        }
        actual = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        }

        self.assertEqual(
            actual["node_binding_test"],
            subject.NODE_BINDING_TEST_SHA256,
        )
        self.assertEqual(
            actual["suite_v15"],
            subject.PRESENTATION_SUITE_V15_SHA256,
        )
        self.assertEqual(
            actual["python_cross_runtime_test"],
            subject.PYTHON_CROSS_RUNTIME_TEST_SHA256,
        )

    def test_source_schema_and_fingerprint_contracts_are_exact(self) -> None:
        pins = self.document["source_contract_pins"]

        self.assertEqual(
            pins["http_candidate"]["schema_version"],
            subject.HTTP_CANDIDATE_RESPONSE_SCHEMA,
        )
        self.assertEqual(
            pins["http_candidate"]["static_fingerprint"],
            subject.HTTP_CANDIDATE_STATIC_FINGERPRINT,
        )
        self.assertEqual(
            pins["public_projection"]["schema_version"],
            subject.PUBLIC_SUMMARY_SCHEMA,
        )
        self.assertEqual(
            pins["public_projection"]["static_fingerprint"],
            subject.PUBLIC_SUMMARY_STATIC_FINGERPRINT,
        )
        self.assertEqual(
            pins["mount_preregistration_v1"]["schema_version"],
            subject.MOUNT_PREREGISTRATION_SCHEMA,
        )

    def test_binding_contract_has_exact_states_and_fail_closed_fallback(self) -> None:
        contract = self.document["binding_contract"]

        self.assertEqual(
            contract["canonical_hash_contract"],
            "SHA256_UTF8_SORTED_KEYS_COMPACT_JSON",
        )
        self.assertEqual(
            contract["axis_order"],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(
            contract["state_matrix"],
            [
                "NOT_SUPPLIED",
                "UNKNOWN",
                "PLAN_LISTED",
                "DRY_RUN_REPORT22_PASS",
                "DRY_RUN_REPORT22_BLOCK",
            ],
        )
        self.assertTrue(contract["commonjs_contract_available"])
        self.assertTrue(contract["browser_global_vm_contract_available"])
        self.assertTrue(contract["verified_payload_only"])
        self.assertEqual(contract["invalid_response_fallback"], "UNKNOWN")

    def test_test_sources_are_bound_without_embedding_execution_results(self) -> None:
        evidence = self.document["executable_evidence_pins"]

        self.assertFalse(evidence["test_execution_results_embedded"])
        self.assertFalse(evidence["historical_test_totals_embedded"])
        self.assertTrue(self.document["facts"]["executable_evidence_sources_pinned"])
        self.assertTrue(self.document["facts"]["cross_runtime_contract_available"])

    def test_mount_preregistration_remains_independently_blocked(self) -> None:
        mount = mount_contract.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()

        self.assertEqual(mount["status"], "BLOCKED")
        self.assertFalse(mount["facts"]["consumer_binding_review_complete"])
        self.assertFalse(mount["facts"]["mount_allowed"])
        self.assertTrue(self.document["facts"]["mount_preregistration_v1_blocked"])

    def test_route_and_dom_binding_remain_absent(self) -> None:
        server_sources = [
            self.root / "exchange_terminal/server.py",
            self.root / "exchange_terminal/services/http_contract.py",
        ]
        frontend_sources = [
            self.root / "exchange_terminal/static/app.js",
            self.root / "exchange_terminal/static/index.html",
        ]
        for path in server_sources:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(mount_contract.PROPOSED_ROUTE, text)
        for path in frontend_sources:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "evidence_report22_date_grid_migration_http_binding",
                text,
            )
            self.assertNotIn(
                "HakimiReport22DateGridMigrationHttpBinding",
                text,
            )

    def test_facts_distinguish_vm_contract_from_real_browser_evidence(self) -> None:
        facts = self.document["facts"]

        self.assertTrue(
            self.document["binding_contract"][
                "browser_global_vm_contract_available"
            ]
        )
        self.assertFalse(facts["actual_http_transport_exercised"])
        self.assertFalse(facts["frontend_dom_mounted"])
        self.assertFalse(facts["browser_process_exercised"])
        self.assertFalse(facts["runtime_assets_accessed"])
        self.assertFalse(facts["route_registered"])

    def test_authority_is_locked_and_copy_has_no_ready_signal(self) -> None:
        authority = self.document["authority"]

        self.assertTrue(authority["descriptive_only"])
        for field, value in authority.items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(self.document, sort_keys=True).upper())

    def test_build_api_accepts_no_caller_evidence_or_policy_override(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1
        )

        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(
                browser_review=True
            )

    def test_exact_rebuild_is_deterministic_and_tamper_evident(self) -> None:
        rebuilt = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1()
        self.assertEqual(self.document, rebuilt)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(
                self.document
            )
        )
        for mutation in (
            lambda value: value["review"].update(
                {"browser_visual_review_complete": True}
            ),
            lambda value: value["facts"].update({"frontend_dom_mounted": True}),
            lambda value: value["authority"].update({"mount_allowed": True}),
            lambda value: value["source_contract_pins"]["node_http_binding"].update(
                {"sha256": "0" * 64}
            ),
        ):
            tampered = copy.deepcopy(self.document)
            mutation(tampered)
            self.assertFalse(
                subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1(
                    tampered
                )
            )

    def test_schema_fingerprint_hash_and_public_api_are_stable(self) -> None:
        self.assertEqual(self.document["schema_version"], subject.REVIEW_SCHEMA_VERSION)
        self.assertEqual(self.document["static_fingerprint"], subject.STATIC_FINGERPRINT)
        self.assertRegex(self.document["review_hash"], r"^[0-9a-f]{64}$")
        for function in (
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1,
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1,
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
