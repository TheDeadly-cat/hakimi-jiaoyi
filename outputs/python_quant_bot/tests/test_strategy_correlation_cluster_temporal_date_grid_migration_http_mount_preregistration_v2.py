from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1 as review_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1 as mount_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2 as subject,
)


class StrategyCorrelationClusterTemporalDateGridMigrationHttpMountPreregistrationV2Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.source_v1 = mount_v1.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()
        self.review_v1 = review_v1.build_strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1()
        self.document = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2()

    def test_successor_is_blocked_and_binds_verified_sources(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertTrue(self.document["facts"]["predecessor_verified"])
        self.assertTrue(self.document["facts"]["predecessor_immutable"])
        self.assertTrue(self.document["facts"]["consumer_binding_review_verified"])
        self.assertTrue(
            self.document["facts"]["static_consumer_binding_review_complete"]
        )
        self.assertFalse(self.document["facts"]["mount_allowed"])

    def test_predecessor_and_review_file_pins_match_current_sources(self) -> None:
        paths = {
            "predecessor": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1.py",
            "review": self.root
            / "exchange_terminal/services/strategy_correlation_cluster_temporal_date_grid_migration_consumer_binding_review_v1.py",
        }
        actual = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        }

        self.assertEqual(actual["predecessor"], subject.SOURCE_V1_FILE_SHA256)
        self.assertEqual(actual["review"], subject.CONSUMER_REVIEW_V1_FILE_SHA256)

    def test_predecessor_and_review_artifact_hashes_are_exact(self) -> None:
        self.assertEqual(
            self.source_v1["preregistration_hash"],
            subject.SOURCE_V1_ARTIFACT_HASH,
        )
        self.assertEqual(
            self.review_v1["review_hash"],
            subject.CONSUMER_REVIEW_V1_ARTIFACT_HASH,
        )
        self.assertEqual(
            self.document["predecessor"]["artifact_hash"],
            subject.SOURCE_V1_ARTIFACT_HASH,
        )
        self.assertEqual(
            self.document["consumer_binding_review"]["artifact_hash"],
            subject.CONSUMER_REVIEW_V1_ARTIFACT_HASH,
        )

    def test_v1_remains_immutable_and_independently_blocked(self) -> None:
        before = copy.deepcopy(self.source_v1)
        subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2()
        after = mount_v1.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()

        self.assertEqual(before, after)
        self.assertEqual(after["status"], "BLOCKED")
        self.assertFalse(after["facts"]["consumer_binding_review_complete"])
        self.assertIn("CONSUMER_BINDING_REVIEW_REQUIRED", after["blockers"])

    def test_successor_inherits_candidate_projection_baselines_and_transport(self) -> None:
        for field in (
            "candidate",
            "public_projection",
            "source_baseline_pins",
            "proposed_transport",
            "required_transport_controls",
        ):
            self.assertEqual(self.document[field], self.source_v1[field])
        self.assertFalse(self.document["proposed_transport"]["registered"])
        self.assertFalse(self.document["proposed_transport"]["externally_callable"])

    def test_static_consumer_review_is_closed_without_mount_promotion(self) -> None:
        review = self.document["consumer_binding_review"]
        control = self.document["unregistered_controls"]["consumer_binding_review"]

        self.assertEqual(review["status"], "CANDIDATE_BOUND_NOT_MOUNTED")
        self.assertTrue(review["static_review_complete"])
        self.assertFalse(review["mount_authority_granted"])
        self.assertTrue(control["completed"])
        self.assertTrue(control["static_scope_only"])
        self.assertFalse(control["frontend_mounted"])

    def test_consumer_review_blocker_is_replaced_by_external_review_blockers(self) -> None:
        blockers = self.document["blockers"]

        self.assertNotIn("CONSUMER_BINDING_REVIEW_REQUIRED", blockers)
        self.assertIn("ACTUAL_HTTP_TRANSPORT_REVIEW_REQUIRED", blockers)
        self.assertIn("FRONTEND_DOM_MOUNT_NOT_REGISTERED", blockers)
        self.assertIn("BROWSER_VISUAL_REVIEW_REQUIRED", blockers)
        self.assertIn("TRUSTED_MIGRATION_EVIDENCE_PROVIDER_UNREGISTERED", blockers)
        self.assertIn("ROUTE_NOT_REGISTERED", blockers)
        self.assertEqual(blockers, list(subject.MOUNT_BLOCKERS))

    def test_external_transport_dom_and_visual_controls_remain_open(self) -> None:
        controls = self.document["unregistered_controls"]

        self.assertFalse(controls["actual_http_transport_review"]["completed"])
        self.assertFalse(controls["actual_http_transport_review"]["service_started"])
        self.assertFalse(controls["frontend_dom_mount"]["registered"])
        self.assertFalse(controls["browser_visual_review"]["completed"])
        self.assertFalse(
            controls["browser_visual_review"]["browser_process_exercised"]
        )
        self.assertFalse(
            controls["trusted_migration_evidence_provider"]["registered"]
        )
        self.assertFalse(controls["authentication"]["registered"])
        self.assertFalse(controls["rate_limit"]["registered"])
        self.assertFalse(controls["request_body_limit"]["registered"])
        self.assertFalse(controls["request_log_redaction"]["registered"])
        self.assertFalse(controls["independent_mount_review"]["completed"])
        self.assertFalse(controls["route_registration"]["registered"])

    def test_route_and_dom_mount_remain_absent_from_current_sources(self) -> None:
        server_sources = [
            self.root / "exchange_terminal/server.py",
            self.root / "exchange_terminal/services/http_contract.py",
        ]
        frontend_sources = [
            self.root / "exchange_terminal/static/app.js",
            self.root / "exchange_terminal/static/index.html",
        ]
        for path in server_sources:
            self.assertNotIn(
                mount_v1.PROPOSED_ROUTE,
                path.read_text(encoding="utf-8"),
            )
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

    def test_authority_remains_locked_and_has_no_ready_signal(self) -> None:
        authority = self.document["authority"]

        self.assertTrue(authority["descriptive_only"])
        for field, value in authority.items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(self.document, sort_keys=True).upper())

    def test_build_api_accepts_no_caller_source_or_policy_override(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2
        )

        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2(
                route="/attacker"
            )

    def test_exact_rebuild_is_deterministic_and_tamper_evident(self) -> None:
        rebuilt = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2()
        self.assertEqual(self.document, rebuilt)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2(
                self.document
            )
        )
        for mutation in (
            lambda value: value["proposed_transport"].update({"registered": True}),
            lambda value: value["facts"].update({"mount_allowed": True}),
            lambda value: value["authority"].update({"paper_authorized": True}),
            lambda value: value["consumer_binding_review"].update(
                {"artifact_hash": "0" * 64}
            ),
            lambda value: value["unregistered_controls"][
                "browser_visual_review"
            ].update({"completed": True}),
        ):
            tampered = copy.deepcopy(self.document)
            mutation(tampered)
            self.assertFalse(
                subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2(
                    tampered
                )
            )

    def test_schema_fingerprint_hash_and_public_api_are_stable(self) -> None:
        self.assertEqual(
            self.document["schema_version"],
            subject.PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.document["static_fingerprint"],
            subject.STATIC_FINGERPRINT,
        )
        self.assertRegex(self.document["preregistration_hash"], r"^[0-9a-f]{64}$")
        for function in (
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2,
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v2,
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
