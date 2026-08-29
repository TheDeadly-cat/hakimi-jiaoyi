from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest
from pathlib import Path

from exchange_terminal.services import (
    strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1 as subject,
)


class StrategyCorrelationClusterTemporalDateGridMigrationHttpMountPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()

    def test_policy_is_preregistered_but_mount_remains_blocked(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertTrue(self.document["facts"]["policy_preregistered"])
        self.assertTrue(self.document["facts"]["candidate_contract_available"])
        self.assertTrue(
            self.document["facts"]["public_projection_contract_available"]
        )
        self.assertFalse(self.document["facts"]["mount_controls_complete"])
        self.assertFalse(self.document["facts"]["route_registered"])
        self.assertFalse(self.document["facts"]["mount_allowed"])
        self.assertEqual(self.document["blockers"], list(subject.MOUNT_BLOCKERS))

    def test_source_hash_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            "candidate": root
            / "exchange_terminal/interfaces/http/strategy_correlation_cluster_temporal_date_grid_migration_candidate_v1.py",
            "projection": root
            / "exchange_terminal/services/strategy_correlation_cluster_temporal_date_grid_migration_projection.py",
            "server": root / "exchange_terminal/server.py",
            "http_contract": root / "exchange_terminal/services/http_contract.py",
        }
        actual = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        }

        self.assertEqual(actual["candidate"], subject.CANDIDATE_ADAPTER_SHA256)
        self.assertEqual(actual["projection"], subject.PUBLIC_PROJECTION_SHA256)
        self.assertEqual(actual["server"], subject.SERVER_BASELINE_SHA256)
        self.assertEqual(
            actual["http_contract"],
            subject.HTTP_CONTRACT_BASELINE_SHA256,
        )

    def test_candidate_and_projection_contracts_are_pinned(self) -> None:
        self.assertEqual(
            self.document["candidate"],
            {
                "adapter_schema_version": subject.CANDIDATE_RESPONSE_SCHEMA_VERSION,
                "adapter_static_fingerprint": subject.CANDIDATE_STATIC_FINGERPRINT,
                "adapter_sha256": subject.CANDIDATE_ADAPTER_SHA256,
            },
        )
        self.assertEqual(
            self.document["public_projection"],
            {
                "summary_schema_version": subject.PUBLIC_SUMMARY_SCHEMA_VERSION,
                "summary_static_fingerprint": (
                    subject.PUBLIC_SUMMARY_STATIC_FINGERPRINT
                ),
                "projection_sha256": subject.PUBLIC_PROJECTION_SHA256,
            },
        )

    def test_route_and_method_are_fixed_but_unregistered(self) -> None:
        transport = self.document["proposed_transport"]

        self.assertEqual(transport["method"], "POST")
        self.assertEqual(
            transport["route"],
            "/api/v1/research/strategy-correlation/"
            "report22-date-grid-migration-evidence",
        )
        self.assertFalse(transport["registered"])
        self.assertFalse(transport["externally_callable"])

    def test_route_is_absent_from_server_and_http_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sources = [
            root / "exchange_terminal/server.py",
            root / "exchange_terminal/services/http_contract.py",
        ]
        for source in sources:
            text = source.read_text(encoding="utf-8")
            self.assertNotIn(subject.PROPOSED_ROUTE, text)
            self.assertNotIn(
                "strategy_correlation_cluster_temporal_date_grid_migration_candidate_v1",
                text,
            )

    def test_required_transport_controls_are_fail_closed(self) -> None:
        controls = self.document["required_transport_controls"]

        self.assertTrue(controls["loopback_only"])
        self.assertTrue(controls["same_origin_required"])
        self.assertTrue(controls["read_only"])
        self.assertTrue(controls["schema_only_request"])
        self.assertTrue(controls["public_summary_only_response"])
        self.assertEqual(controls["cache_control"], "no-store")
        self.assertEqual(controls["x_content_type_options"], "nosniff")
        self.assertEqual(controls["x_frame_options"], "DENY")
        self.assertEqual(controls["referrer_policy"], "no-referrer")
        self.assertEqual(controls["cross_origin_opener_policy"], "same-origin")
        self.assertFalse(controls["runtime_reads_allowed"])
        self.assertFalse(controls["runtime_mutations_allowed"])
        self.assertFalse(controls["cache_reads_allowed"])
        self.assertFalse(controls["cache_writes_allowed"])

    def test_private_inputs_and_request_logging_are_forbidden(self) -> None:
        controls = self.document["required_transport_controls"]
        provider = self.document["unregistered_controls"][
            "trusted_migration_evidence_provider"
        ]
        logging = self.document["unregistered_controls"]["request_log_redaction"]

        self.assertFalse(controls["request_body_logging_allowed"])
        self.assertFalse(controls["migration_assessment_client_supplied_allowed"])
        self.assertFalse(controls["verification_context_client_supplied_allowed"])
        self.assertFalse(provider["client_supplied_allowed"])
        self.assertFalse(provider["runtime_asset_reads_allowed"])
        self.assertFalse(logging["request_body_logging_allowed"])

    def test_all_required_security_controls_are_explicitly_unregistered(self) -> None:
        controls = self.document["unregistered_controls"]

        self.assertFalse(controls["authentication"]["registered"])
        self.assertIsNone(controls["authentication"]["mechanism"])
        self.assertFalse(controls["rate_limit"]["registered"])
        self.assertIsNone(controls["rate_limit"]["requests_per_window"])
        self.assertFalse(controls["request_body_limit"]["registered"])
        self.assertIsNone(controls["request_body_limit"]["maximum_bytes"])
        self.assertFalse(
            controls["trusted_migration_evidence_provider"]["registered"]
        )
        self.assertIsNone(
            controls["trusted_migration_evidence_provider"][
                "assessment_provider_id"
            ]
        )
        self.assertFalse(controls["request_log_redaction"]["registered"])
        self.assertFalse(controls["consumer_binding_review"]["completed"])
        self.assertFalse(controls["consumer_binding_review"]["frontend_mounted"])
        self.assertFalse(controls["independent_mount_review"]["completed"])
        self.assertFalse(controls["route_registration"]["registered"])

    def test_all_authority_fields_prevent_mount_migration_or_trading(self) -> None:
        authority = self.document["authority"]

        self.assertTrue(authority["descriptive_only"])
        for field, value in authority.items():
            if field != "descriptive_only":
                self.assertIs(value, False)
        self.assertNotIn("READY", json.dumps(self.document, sort_keys=True).upper())

    def test_build_api_accepts_no_caller_policy_overrides(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1
        )

        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(
                route="/attacker"
            )

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1()

        self.assertEqual(self.document, rebuilt)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(
                self.document
            )
        )

    def test_route_control_hash_and_authority_tamper_are_rejected(self) -> None:
        mutators = (
            lambda document: document["proposed_transport"].update(
                {"route": "/attacker"}
            ),
            lambda document: document["proposed_transport"].update(
                {"registered": True}
            ),
            lambda document: document["source_baseline_pins"].update(
                {"server_sha256": "0" * 64}
            ),
            lambda document: document["public_projection"].update(
                {"projection_sha256": "0" * 64}
            ),
            lambda document: document["authority"].update({"mount_allowed": True}),
            lambda document: document["unregistered_controls"][
                "trusted_migration_evidence_provider"
            ].update({"registered": True}),
        )
        for mutate in mutators:
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(self.document)
                mutate(tampered)
                self.assertFalse(
                    subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(
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
            subject.build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1,
            subject.verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1,
        ):
            parameters = set(inspect.signature(function).parameters)
            self.assertTrue(
                parameters.isdisjoint(
                    {
                        "private_key",
                        "runtime",
                        "database",
                        "cache",
                        "authentication_token",
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
