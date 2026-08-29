from __future__ import annotations

import copy
import hashlib
import inspect
import unittest
from pathlib import Path

from exchange_terminal.services import (
    strategy_correlation_provider_evidence_http_mount_preregistration_v1 as subject,
)


class StrategyCorrelationProviderEvidenceHttpMountPreregistrationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = (
            subject.build_strategy_correlation_provider_evidence_http_mount_preregistration_v1()
        )

    def test_policy_is_preregistered_but_mount_remains_blocked(self) -> None:
        self.assertEqual(self.document["status"], "BLOCKED")
        self.assertTrue(self.document["facts"]["policy_preregistered"])
        self.assertFalse(self.document["facts"]["mount_controls_complete"])
        self.assertFalse(self.document["facts"]["route_registered"])
        self.assertFalse(self.document["facts"]["mount_allowed"])
        self.assertEqual(self.document["blockers"], list(subject.MOUNT_BLOCKERS))

    def test_source_hash_pins_match_current_source_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = {
            "adapter": root
            / "exchange_terminal/interfaces/http/strategy_correlation_provider_evidence_candidate_v1.py",
            "server": root / "exchange_terminal/server.py",
            "http_contract": root / "exchange_terminal/services/http_contract.py",
        }
        actual = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in paths.items()
        }

        self.assertEqual(actual["adapter"], subject.CANDIDATE_ADAPTER_SHA256)
        self.assertEqual(actual["server"], subject.SERVER_BASELINE_SHA256)
        self.assertEqual(actual["http_contract"], subject.HTTP_CONTRACT_BASELINE_SHA256)

    def test_route_and_method_are_fixed_but_unregistered(self) -> None:
        transport = self.document["proposed_transport"]

        self.assertEqual(transport["method"], "POST")
        self.assertEqual(
            transport["route"],
            "/api/v1/research/strategy-correlation/provider-evidence",
        )
        self.assertFalse(transport["registered"])
        self.assertFalse(transport["externally_callable"])

    def test_transport_requires_existing_fail_closed_baseline_controls(self) -> None:
        controls = self.document["required_transport_controls"]

        self.assertTrue(controls["loopback_only"])
        self.assertTrue(controls["same_origin_required"])
        self.assertEqual(controls["cache_control"], "no-store")
        self.assertEqual(controls["x_content_type_options"], "nosniff")
        self.assertEqual(controls["x_frame_options"], "DENY")
        self.assertEqual(controls["referrer_policy"], "no-referrer")
        self.assertEqual(controls["cross_origin_opener_policy"], "same-origin")
        self.assertFalse(controls["runtime_reads_allowed"])
        self.assertFalse(controls["runtime_mutations_allowed"])
        self.assertFalse(controls["cache_reads_allowed"])
        self.assertFalse(controls["cache_writes_allowed"])

    def test_security_registrations_are_explicitly_absent(self) -> None:
        controls = self.document["unregistered_controls"]

        self.assertFalse(controls["authentication"]["registered"])
        self.assertIsNone(controls["authentication"]["mechanism"])
        self.assertFalse(controls["rate_limit"]["registered"])
        self.assertIsNone(controls["rate_limit"]["requests_per_window"])
        self.assertFalse(controls["request_body_limit"]["registered"])
        self.assertIsNone(controls["request_body_limit"]["maximum_bytes"])
        self.assertFalse(controls["trusted_context_provider"]["registered"])
        self.assertFalse(controls["request_log_redaction"]["registered"])
        self.assertFalse(controls["independent_mount_review"]["completed"])
        self.assertFalse(controls["route_registration"]["registered"])

    def test_client_context_and_request_logging_are_forbidden(self) -> None:
        required = self.document["required_transport_controls"]
        unregistered = self.document["unregistered_controls"]

        self.assertFalse(required["verification_context_client_supplied_allowed"])
        self.assertFalse(required["request_body_logging_allowed"])
        self.assertFalse(
            unregistered["trusted_context_provider"]["client_supplied_allowed"]
        )
        self.assertFalse(
            unregistered["request_log_redaction"]["request_body_logging_allowed"]
        )

    def test_all_authority_fields_prevent_mount_or_trading(self) -> None:
        authority = self.document["authority"]

        self.assertTrue(authority["descriptive_only"])
        for field in (
            "mount_allowed",
            "registration_allowed",
            "externally_callable",
            "current_admission_allowed",
            "current_pointer_written",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertFalse(authority[field])

    def test_build_api_accepts_no_caller_policy_overrides(self) -> None:
        signature = inspect.signature(
            subject.build_strategy_correlation_provider_evidence_http_mount_preregistration_v1
        )

        self.assertEqual(list(signature.parameters), [])
        with self.assertRaises(TypeError):
            subject.build_strategy_correlation_provider_evidence_http_mount_preregistration_v1(
                route="/attacker"
            )

    def test_exact_rebuild_is_deterministic_and_verifiable(self) -> None:
        rebuilt = (
            subject.build_strategy_correlation_provider_evidence_http_mount_preregistration_v1()
        )

        self.assertEqual(self.document, rebuilt)
        self.assertTrue(
            subject.verify_strategy_correlation_provider_evidence_http_mount_preregistration_v1(
                self.document
            )
        )

    def test_route_or_registration_tamper_is_rejected(self) -> None:
        for mutate in (
            lambda document: document["proposed_transport"].update(
                {"route": "/attacker"}
            ),
            lambda document: document["proposed_transport"].update(
                {"registered": True}
            ),
            lambda document: document["authority"].update({"mount_allowed": True}),
            lambda document: document["unregistered_controls"]["authentication"].update(
                {"registered": True, "mechanism": "forged"}
            ),
        ):
            with self.subTest(mutate=mutate):
                tampered = copy.deepcopy(self.document)
                mutate(tampered)
                self.assertFalse(
                    subject.verify_strategy_correlation_provider_evidence_http_mount_preregistration_v1(
                        tampered
                    )
                )

    def test_schema_fingerprint_and_hash_shape_are_stable(self) -> None:
        self.assertEqual(
            self.document["schema_version"],
            subject.PREREGISTRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            self.document["static_fingerprint"], subject.STATIC_FINGERPRINT
        )
        self.assertRegex(self.document["preregistration_hash"], r"^[0-9a-f]{64}$")

    def test_public_api_has_no_private_key_or_runtime_parameter(self) -> None:
        for function in (
            subject.build_strategy_correlation_provider_evidence_http_mount_preregistration_v1,
            subject.verify_strategy_correlation_provider_evidence_http_mount_preregistration_v1,
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
