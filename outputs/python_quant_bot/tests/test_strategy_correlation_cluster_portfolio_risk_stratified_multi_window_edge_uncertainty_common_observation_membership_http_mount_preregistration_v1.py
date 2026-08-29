from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1
    as preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _build() -> dict:
    return preregistration.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1()


def _reseal(document: dict) -> dict:
    result = copy.deepcopy(document)
    result.pop("preregistration_hash", None)
    return seal_strict_canonical_document(result, "preregistration_hash")


class MembershipHttpMountPreregistrationV1Tests(unittest.TestCase):
    def test_exact_document_is_blocked_and_verifiable(self) -> None:
        document = _build()
        self.assertEqual(document["status"], "BLOCKED")
        self.assertTrue(
            preregistration.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(
                document
            )
        )

    def test_proposed_transport_is_descriptive_and_unregistered(self) -> None:
        transport = _build()["proposed_transport"]
        self.assertEqual(transport["method"], "POST")
        self.assertEqual(transport["route"], preregistration.PROPOSED_ROUTE)
        self.assertIs(transport["registered"], False)
        self.assertIs(transport["externally_callable"], False)

    def test_required_transport_controls_are_read_only_and_no_store(self) -> None:
        controls = _build()["required_transport_controls"]
        self.assertIs(controls["loopback_only"], True)
        self.assertIs(controls["same_origin_required"], True)
        self.assertEqual(controls["cache_control"], "no-store")
        self.assertIs(controls["read_only"], True)
        self.assertIs(controls["runtime_reads_allowed"], False)
        self.assertIs(controls["runtime_mutations_allowed"], False)

    def test_auth_rate_limit_and_body_limit_are_unregistered(self) -> None:
        controls = _build()["unregistered_controls"]
        for key in ("authentication", "rate_limit", "request_body_limit"):
            self.assertIs(controls[key]["required"], True)
            self.assertIs(controls[key]["registered"], False)
        self.assertIsNone(controls["authentication"]["mechanism"])
        self.assertIsNone(controls["request_body_limit"]["maximum_bytes"])

    def test_trusted_context_provider_is_absent_and_client_input_denied(self) -> None:
        provider = _build()["unregistered_controls"][
            "trusted_candidate_context_provider"
        ]
        self.assertIs(provider["required"], True)
        self.assertIs(provider["registered"], False)
        self.assertIs(provider["client_supplied_allowed"], False)
        self.assertIs(provider["runtime_asset_reads_allowed"], False)
        self.assertIsNone(provider["candidate_document_provider_id"])
        self.assertIsNone(provider["verification_context_provider_id"])

    def test_request_logging_requires_unregistered_redaction_policy(self) -> None:
        control = _build()["unregistered_controls"]["request_log_redaction"]
        self.assertIs(control["required"], True)
        self.assertIs(control["registered"], False)
        self.assertIsNone(control["policy_id"])
        self.assertIs(control["request_body_logging_allowed"], False)

    def test_consumer_and_independent_reviews_are_incomplete(self) -> None:
        controls = _build()["unregistered_controls"]
        self.assertIs(controls["consumer_binding_review"]["completed"], False)
        self.assertIs(controls["consumer_binding_review"]["frontend_mounted"], False)
        self.assertIs(controls["independent_mount_review"]["completed"], False)
        self.assertIs(controls["route_registration"]["registered"], False)

    def test_route_candidate_and_source_pins_are_exact(self) -> None:
        document = _build()
        self.assertEqual(
            document["route_contract"]["implementation_sha256"],
            preregistration.ROUTE_CONTRACT_V1_SHA256,
        )
        self.assertEqual(
            document["candidate"]["implementation_sha256"],
            preregistration.CANDIDATE_V11_SHA256,
        )
        self.assertEqual(
            document["source_baseline_pins"]["server_sha256"],
            preregistration.SERVER_BASELINE_SHA256,
        )
        self.assertEqual(
            document["source_baseline_pins"]["http_contract_sha256"],
            preregistration.HTTP_CONTRACT_BASELINE_SHA256,
        )

    def test_authority_is_permanently_locked(self) -> None:
        authority = _build()["authority"]
        self.assertIs(authority["descriptive_only"], True)
        for key, value in authority.items():
            if key != "descriptive_only":
                self.assertIs(value, False, key)

    def test_resealed_route_registration_promotion_is_rejected(self) -> None:
        document = _build()
        document["unregistered_controls"]["route_registration"]["registered"] = True
        document = _reseal(document)
        self.assertFalse(
            preregistration.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(
                document
            )
        )

    def test_resealed_client_supplied_context_promotion_is_rejected(self) -> None:
        document = _build()
        document["unregistered_controls"]["trusted_candidate_context_provider"][
            "client_supplied_allowed"
        ] = True
        document = _reseal(document)
        self.assertFalse(
            preregistration.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(
                document
            )
        )

    def test_builds_are_deterministic_and_independent(self) -> None:
        first = _build()
        second = _build()
        self.assertEqual(first, second)
        first["blockers"].append("MUTATED")
        self.assertNotEqual(first, second)
        self.assertEqual(second["blockers"], list(preregistration.MOUNT_BLOCKERS))


if __name__ == "__main__":
    unittest.main()
