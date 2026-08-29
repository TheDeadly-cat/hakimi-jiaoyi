from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9
    as candidate_v9,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1
    as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


ROOT = Path(__file__).resolve().parents[1]


def _build() -> dict:
    return subject.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1()


def _reseal(document: dict) -> dict:
    unsigned = deepcopy(document)
    unsigned.pop("preregistration_hash", None)
    return seal_strict_canonical_document(unsigned, "preregistration_hash")


class GeometryBudgetMultiWindowHttpMountPreregistrationV1Tests(
    unittest.TestCase
):
    def test_exact_document_is_blocked_and_verifiable(self) -> None:
        document = _build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
                document
            )
        )

    def test_candidate_contract_and_source_are_exactly_pinned(self) -> None:
        document = _build()["candidate_contract"]
        self.assertEqual(
            sha256(Path(candidate_v9.__file__).read_bytes()).hexdigest(),
            subject.CANDIDATE_V9_IMPLEMENTATION_SHA256,
        )
        self.assertEqual(document["contract_hash"], candidate_v9.CONTRACT_HASH)
        self.assertEqual(
            document["request_schema_version"], candidate_v9.REQUEST_SCHEMA_VERSION
        )
        self.assertEqual(
            document["response_schema_version"], candidate_v9.RESPONSE_SCHEMA_VERSION
        )
        self.assertEqual(document["interface_status"], "UNREGISTERED_CANDIDATE")

    def test_source_baseline_pins_match_current_protected_files(self) -> None:
        paths = {
            "strict_canonical_sha256": (
                ROOT / "exchange_terminal/services/strict_canonical_json_hash.py"
            ),
            "server_sha256": ROOT / "exchange_terminal/server.py",
            "http_contract_sha256": (
                ROOT / "exchange_terminal/services/http_contract.py"
            ),
        }
        pins = _build()["source_baseline_pins"]
        for key, path in paths.items():
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), pins[key], key)

    def test_proposed_transport_has_no_handler_or_registration(self) -> None:
        transport = _build()["proposed_transport"]
        self.assertEqual(transport["method"], "POST")
        self.assertEqual(transport["route"], subject.PROPOSED_ROUTE)
        self.assertIsNone(transport["handler"])
        self.assertIsNone(transport["endpoint"])
        self.assertIs(transport["registered"], False)
        self.assertIs(transport["externally_callable"], False)

    def test_required_transport_is_local_read_only_and_no_store(self) -> None:
        controls = _build()["required_transport_controls"]
        self.assertIs(controls["loopback_only"], True)
        self.assertIs(controls["same_origin_required"], True)
        self.assertEqual(controls["cache_control"], "no-store")
        self.assertIs(controls["read_only"], True)
        self.assertIs(controls["runtime_reads_allowed"], False)
        self.assertIs(controls["runtime_mutations_allowed"], False)
        self.assertIs(controls["database_reads_allowed"], False)
        self.assertIs(controls["cache_reads_allowed"], False)
        self.assertIs(controls["external_network_access_allowed"], False)

    def test_auth_csrf_rate_limit_and_body_limit_are_unregistered(self) -> None:
        controls = _build()["unregistered_controls"]
        for key in ("authentication", "csrf", "rate_limit", "request_body_limit"):
            self.assertIs(controls[key]["required"], True, key)
            self.assertIs(controls[key]["registered"], False, key)
        self.assertIsNone(controls["authentication"]["mechanism"])
        self.assertIsNone(controls["csrf"]["policy_id"])
        self.assertIsNone(controls["request_body_limit"]["maximum_bytes"])

    def test_trusted_provider_is_absent_and_client_sources_are_denied(self) -> None:
        provider = _build()["unregistered_controls"][
            "trusted_candidate_context_provider"
        ]
        self.assertIs(provider["required"], True)
        self.assertIs(provider["registered"], False)
        self.assertIs(provider["client_supplied_allowed"], False)
        self.assertIs(provider["runtime_asset_reads_allowed"], False)
        self.assertIs(provider["database_reads_allowed"], False)
        self.assertIs(provider["cache_reads_allowed"], False)
        self.assertIs(provider["external_network_access_allowed"], False)
        self.assertIsNone(provider["candidate_document_provider_id"])
        self.assertIsNone(provider["verification_context_provider_id"])

    def test_logging_handler_reviews_and_route_are_unregistered(self) -> None:
        controls = _build()["unregistered_controls"]
        self.assertIs(controls["request_log_redaction"]["registered"], False)
        self.assertIs(
            controls["request_log_redaction"]["request_body_logging_allowed"],
            False,
        )
        self.assertIs(controls["handler_implementation"]["registered"], False)
        self.assertIsNone(controls["handler_implementation"]["handler_id"])
        self.assertIs(controls["consumer_binding_review"]["completed"], False)
        self.assertIs(controls["independent_mount_review"]["completed"], False)
        self.assertIs(controls["route_registration"]["registered"], False)

    def test_authority_is_permanently_locked(self) -> None:
        authority = _build()["authority"]
        self.assertIs(authority["descriptive_only"], True)
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_neutral_axis_order_is_preserved(self) -> None:
        stages = _build()["stages"]
        self.assertEqual(
            [stage["axis"] for stage in stages],
            ["SOURCE", "GAP", "MATURITY", "PERMISSION"],
        )
        self.assertEqual(stages[-1]["state"], "NONE")

    def test_proposed_route_is_absent_from_registered_sources(self) -> None:
        server = (ROOT / "exchange_terminal/server.py").read_text(encoding="utf-8")
        contract = (
            ROOT / "exchange_terminal/services/http_contract.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(subject.PROPOSED_ROUTE, server)
        self.assertNotIn(subject.PROPOSED_ROUTE, contract)
        self.assertNotIn(subject.CANDIDATE_V9_MODULE, server)
        self.assertNotIn(subject.CANDIDATE_V9_MODULE, contract)

    def test_resealed_route_registration_promotion_is_rejected(self) -> None:
        document = _build()
        document["unregistered_controls"]["route_registration"][
            "registered"
        ] = True
        self.assertFalse(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
                _reseal(document)
            )
        )

    def test_resealed_client_supplied_source_promotion_is_rejected(self) -> None:
        document = _build()
        document["unregistered_controls"]["trusted_candidate_context_provider"][
            "client_supplied_allowed"
        ] = True
        self.assertFalse(
            subject.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
                _reseal(document)
            )
        )

    def test_builds_are_deterministic_and_independent(self) -> None:
        first = _build()
        second = _build()
        self.assertEqual(first, second)
        first["blockers"].append("MUTATED")
        self.assertNotEqual(first, second)
        self.assertEqual(second["blockers"], list(subject.MOUNT_BLOCKERS))


if __name__ == "__main__":
    unittest.main()
