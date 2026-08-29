from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.application.source_baseline_nonce_anti_replay_namespace_preregistration_v1 import (
    SOURCE_NAMESPACE,
    TARGET_RECEIPT_SCHEMA_VERSION,
    build_source_baseline_nonce_anti_replay_namespace_preregistration_v1,
    build_source_baseline_nonce_anti_replay_request_candidate_v1,
    verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1,
    verify_source_baseline_nonce_anti_replay_request_candidate_v1,
)
from exchange_terminal.interfaces.anti_replay_registry import (
    AntiReplayCompareAndConsumeCommandV1,
    AntiReplayRegistryOutcomeV1,
)
from exchange_terminal.interfaces.anti_replay_registry_v2 import (
    AntiReplayCompareAndConsumeCommandV2,
    AntiReplayCompareAndConsumeResultV2,
    AntiReplayRegistryPortV2,
    build_anti_replay_compare_and_consume_request_v2,
    build_anti_replay_consumption_key_v2,
    verify_anti_replay_compare_and_consume_request_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_atomic_reserve_protocol_v1 import (
    build_nonce_atomic_reserve_request_v1,
    build_nonce_registry_synthetic_state_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1 import (
    _signed_fixture,
)


class SourceBaselineNonceAntiReplayRegistryPortV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _signed_fixture()
        fixture = self.fixture
        self.adapter = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
            fixture["registration"],
            fixture["signed"],
            fixture["evidence"],
            fixture["request"],
            fixture["claim"],
            fixture["intake"],
            fixture["source"],
            fixture["public_key_base64"],
            expected_registration_hash=fixture["registration"]["registration_hash"],
            expected_signed_attestation_hash=fixture["signed"][
                "signed_attestation_hash"
            ],
            review_nonce_hash=fixture["nonce_hash"],
        )
        self.registry_state = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=[],
            sequence=0,
            previous_registry_head_hash=None,
        )
        self.reserve_request = build_nonce_atomic_reserve_request_v1(
            candidate_replay_key=self.adapter["replay_key"],
            expected_registry_head_hash=self.registry_state["registry_head_hash"],
            request_nonce_hash="a" * 64,
        )
        self.preregistration = (
            build_source_baseline_nonce_anti_replay_namespace_preregistration_v1()
        )
        self.candidate = self._candidate()

    def _candidate(self, **overrides: object) -> dict:
        fixture = self.fixture
        values = {
            "namespace_preregistration_document": self.preregistration,
            "adapter_document": self.adapter,
            "reserve_request_document": self.reserve_request,
            "registration": fixture["registration"],
            "signed_attestation": fixture["signed"],
            "signed_attestation_evidence": fixture["evidence"],
            "review_request_document": fixture["request"],
            "review_claim": fixture["claim"],
            "claim_intake_document": fixture["intake"],
            "mount_preregistration_document": fixture["source"],
            "public_key_base64": fixture["public_key_base64"],
            "expected_registration_hash": fixture["registration"][
                "registration_hash"
            ],
            "expected_signed_attestation_hash": fixture["signed"][
                "signed_attestation_hash"
            ],
            "review_nonce_hash": fixture["nonce_hash"],
        }
        values.update(overrides)
        return build_source_baseline_nonce_anti_replay_request_candidate_v1(**values)

    def test_v1_rejects_source_baseline_namespace(self) -> None:
        scope_hash = "b" * 64
        consumption_key = strict_canonical_hash(
            {
                "anti_replay_namespace": SOURCE_NAMESPACE,
                "anti_replay_scope_hash": scope_hash,
            }
        )
        with self.assertRaisesRegex(ValueError, "namespace must match"):
            AntiReplayCompareAndConsumeCommandV1(
                anti_replay_scope_hash=scope_hash,
                attestation_hash="c" * 64,
                challenge_hash="d" * 64,
                consumption_key=consumption_key,
                issuance_preregistration_hash="e" * 64,
                policy_hash="f" * 64,
                request_hash="1" * 64,
                witness_id="synthetic-source-baseline-witness",
                witness_verification_hash="2" * 64,
                anti_replay_namespace=SOURCE_NAMESPACE,
                target_receipt_schema_version=TARGET_RECEIPT_SCHEMA_VERSION,
            )

    def test_v2_accepts_preregistered_source_baseline_namespace(self) -> None:
        command = AntiReplayCompareAndConsumeCommandV2.from_request_document(
            self.candidate["request_document"]
        )
        self.assertEqual(command.anti_replay_namespace, SOURCE_NAMESPACE)
        self.assertEqual(
            command.target_receipt_schema_version, TARGET_RECEIPT_SCHEMA_VERSION
        )

    def test_consumption_key_binds_namespace_and_scope(self) -> None:
        request = self.candidate["request_document"]
        expected = build_anti_replay_consumption_key_v2(
            anti_replay_namespace=request["anti_replay_namespace"],
            anti_replay_scope_hash=request["anti_replay_scope_hash"],
        )
        self.assertEqual(request["consumption_key"], expected)
        rebound = build_anti_replay_consumption_key_v2(
            anti_replay_namespace="other-source-baseline-namespace-v1",
            anti_replay_scope_hash=request["anti_replay_scope_hash"],
        )
        self.assertNotEqual(expected, rebound)

    def test_request_is_exact_and_command_is_frozen(self) -> None:
        request = self.candidate["request_document"]
        self.assertTrue(verify_anti_replay_compare_and_consume_request_v2(request))
        command = AntiReplayCompareAndConsumeCommandV2.from_request_document(request)
        with self.assertRaises(FrozenInstanceError):
            command.request_hash = "b" * 64

    def test_tampered_request_is_rejected(self) -> None:
        tampered = deepcopy(self.candidate["request_document"])
        tampered["actor_id_hash"] = "b" * 64
        self.assertFalse(verify_anti_replay_compare_and_consume_request_v2(tampered))
        with self.assertRaisesRegex(ValueError, "exact v2 contract"):
            AntiReplayCompareAndConsumeCommandV2.from_request_document(tampered)

    def test_preregistration_is_blocked_and_requirements_are_unverified(self) -> None:
        document = self.preregistration
        self.assertEqual(document["status"], "BLOCKED")
        self.assertFalse(document["facts"]["v1_namespace_compatible"])
        self.assertTrue(document["facts"]["port_v2_namespace_parameterized"])
        self.assertTrue(
            all(
                requirement["required"] and not requirement["verified"]
                for requirement in document["required_provider_evidence"]
            )
        )

    def test_preregistration_exact_verifier_rejects_promotion(self) -> None:
        self.assertTrue(
            verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1(
                self.preregistration
            )
        )
        promoted = deepcopy(self.preregistration)
        promoted["facts"]["external_provider_conformance_verified"] = True
        promoted.pop("namespace_preregistration_hash")
        promoted = seal_strict_canonical_document(
            promoted, "namespace_preregistration_hash"
        )
        self.assertFalse(
            verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1(
                promoted
            )
        )

    def test_exact_source_chain_builds_blocked_candidate(self) -> None:
        self.assertEqual(self.candidate["status"], "BLOCKED")
        self.assertEqual(
            self.candidate["candidate_status"], "BUILT_PROVIDER_UNBOUND"
        )
        self.assertTrue(self.candidate["facts"]["source_chain_exactly_verified"])
        self.assertFalse(self.candidate["facts"]["provider_called"])

    def test_candidate_maps_source_commitments_exactly(self) -> None:
        request = self.candidate["request_document"]
        replay_key = self.adapter["replay_key"]
        self.assertEqual(request["subject_hash"], replay_key["replay_key_hash"])
        self.assertEqual(request["challenge_hash"], replay_key["review_nonce_hash"])
        self.assertEqual(request["actor_id_hash"], replay_key["reviewer_key_sha256"])
        self.assertEqual(request["evidence_hash"], self.adapter["adapter_receipt_hash"])
        self.assertEqual(
            request["request_context_hash"],
            self.reserve_request["reserve_request_hash"],
        )

    def test_candidate_exact_verifier_accepts_rebuild(self) -> None:
        fixture = self.fixture
        self.assertTrue(
            verify_source_baseline_nonce_anti_replay_request_candidate_v1(
                self.candidate,
                self.preregistration,
                self.adapter,
                self.reserve_request,
                fixture["registration"],
                fixture["signed"],
                fixture["evidence"],
                fixture["request"],
                fixture["claim"],
                fixture["intake"],
                fixture["source"],
                fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"][
                    "registration_hash"
                ],
                expected_signed_attestation_hash=fixture["signed"][
                    "signed_attestation_hash"
                ],
                review_nonce_hash=fixture["nonce_hash"],
            )
        )

    def test_tampered_adapter_is_unknown(self) -> None:
        tampered = deepcopy(self.adapter)
        tampered["source_signed_attestation_hash"] = "b" * 64
        result = self._candidate(adapter_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["request_document"])

    def test_tampered_reserve_request_is_unknown(self) -> None:
        tampered = deepcopy(self.reserve_request)
        tampered["request_nonce_hash"] = "b" * 64
        result = self._candidate(reserve_request_document=tampered)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_resealed_preregistration_promotion_is_unknown(self) -> None:
        promoted = deepcopy(self.preregistration)
        promoted["facts"]["registry_identity_verified"] = True
        promoted.pop("namespace_preregistration_hash")
        promoted = seal_strict_canonical_document(
            promoted, "namespace_preregistration_hash"
        )
        result = self._candidate(namespace_preregistration_document=promoted)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_consumed_result_requires_exactly_bound_receipt(self) -> None:
        request = self.candidate["request_document"]
        receipt = {
            "schema_version": request["target_receipt_schema_version"],
            "anti_replay_namespace": request["anti_replay_namespace"],
            "namespace_preregistration_hash": request[
                "namespace_preregistration_hash"
            ],
            "request_hash": request["request_hash"],
            "consumption_key": request["consumption_key"],
            "durable_commit_verified": False,
        }
        result = AntiReplayCompareAndConsumeResultV2(
            outcome=AntiReplayRegistryOutcomeV1.CONSUMED,
            anti_replay_namespace=request["anti_replay_namespace"],
            namespace_preregistration_hash=request[
                "namespace_preregistration_hash"
            ],
            request_hash=request["request_hash"],
            consumption_key=request["consumption_key"],
            target_receipt_schema_version=request[
                "target_receipt_schema_version"
            ],
            registry_id="synthetic-registry-v2",
            registry_revision=1,
            receipt_document=receipt,
        )
        receipt["request_hash"] = "b" * 64
        self.assertNotEqual(result.receipt_document["request_hash"], "b" * 64)
        with self.assertRaises(TypeError):
            result.receipt_document["request_hash"] = "c" * 64

    def test_rejected_result_cannot_embed_receipt(self) -> None:
        request = self.candidate["request_document"]
        with self.assertRaisesRegex(ValueError, "must not include"):
            AntiReplayCompareAndConsumeResultV2(
                outcome=AntiReplayRegistryOutcomeV1.DUPLICATE_REJECTED,
                anti_replay_namespace=request["anti_replay_namespace"],
                namespace_preregistration_hash=request[
                    "namespace_preregistration_hash"
                ],
                request_hash=request["request_hash"],
                consumption_key=request["consumption_key"],
                target_receipt_schema_version=request[
                    "target_receipt_schema_version"
                ],
                registry_id="synthetic-registry-v2",
                registry_revision=1,
                receipt_document={"schema_version": "unexpected"},
            )

    def test_structural_port_match_does_not_promote_conformance(self) -> None:
        class StructuralPort:
            def compare_and_consume(self, command: object) -> object:
                raise AssertionError("must not be called")

        self.assertIsInstance(StructuralPort(), AntiReplayRegistryPortV2)
        self.assertFalse(
            self.preregistration["facts"]["external_provider_conformance_verified"]
        )
        self.assertFalse(self.candidate["facts"]["provider_called"])

    def test_candidate_redacts_raw_material_and_keeps_authority_locked(self) -> None:
        serialized = json.dumps(self.candidate, sort_keys=True)
        self.assertNotIn(self.fixture["public_key_base64"], serialized)
        self.assertNotIn(self.fixture["signature_base64"], serialized)
        for field in (
            "provider_call_allowed",
            "writer_allowed",
            "route_registration_allowed",
            "ui_consumer_mount_allowed",
            "current_admission_allowed",
            "paper_authorized",
            "live_order_allowed",
        ):
            self.assertFalse(self.candidate["authority"][field], field)


if __name__ == "__main__":
    unittest.main()
