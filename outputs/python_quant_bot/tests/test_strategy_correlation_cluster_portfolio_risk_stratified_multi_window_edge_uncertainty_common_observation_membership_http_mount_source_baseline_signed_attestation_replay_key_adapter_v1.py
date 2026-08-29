from __future__ import annotations

import json
import unittest
from copy import deepcopy

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_atomic_reserve_protocol_v1 import (
    build_nonce_atomic_reserve_request_v1,
    build_nonce_registry_synthetic_state_v1,
    simulate_nonce_atomic_reserve_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_replay_snapshot_gate_v1 import (
    build_nonce_replay_snapshot_v1,
    evaluate_nonce_replay_snapshot_gate_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1 import (
    build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1,
    verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1,
)
from tests.test_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1 import (
    _signed_fixture,
)


class SignedAttestationReplayKeyAdapterV1Tests(unittest.TestCase):
    def _adapt(self, fixture: dict, **overrides: object) -> dict:
        values = {
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
        return build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
            **values
        )

    def test_valid_source_maps_three_authoritative_commitments(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture)
        replay_key = adapter["replay_key"]
        self.assertEqual(adapter["status"], "PASS")
        self.assertEqual(adapter["mapping_status"], "ADAPTED")
        self.assertEqual(adapter["facts"]["field_mapping_count"], 3)
        self.assertEqual(
            replay_key["signed_attestation_hash"],
            fixture["evidence"]["source_lineage"]["signed_attestation_hash"],
        )
        self.assertEqual(
            replay_key["reviewer_key_sha256"],
            fixture["registration"]["key_binding"]["public_key_sha256"],
        )
        self.assertEqual(
            replay_key["review_nonce_hash"],
            fixture["evidence"]["source_lineage"]["review_nonce_hash"],
        )

    def test_exact_adapter_verifier_accepts_only_rebuilt_document(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture)
        self.assertTrue(
            verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
                adapter,
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

    def test_output_redacts_raw_key_signature_and_identity(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture)
        serialized = json.dumps(adapter, sort_keys=True)
        self.assertNotIn(fixture["public_key_base64"], serialized)
        self.assertNotIn(fixture["signature_base64"], serialized)
        self.assertFalse(adapter["facts"]["raw_reviewer_identifiers_embedded"])
        self.assertFalse(adapter["facts"]["public_key_material_embedded"])
        self.assertFalse(adapter["facts"]["signature_material_embedded"])

    def test_inputs_are_not_mutated(self) -> None:
        fixture = _signed_fixture()
        names = ("registration", "signed", "evidence", "request", "claim", "intake", "source")
        before = {name: deepcopy(fixture[name]) for name in names}
        self._adapt(fixture)
        self.assertEqual(before, {name: fixture[name] for name in names})

    def test_tampered_source_evidence_is_unknown(self) -> None:
        fixture = _signed_fixture()
        tampered = deepcopy(fixture["evidence"])
        tampered["source_lineage"]["review_nonce_hash"] = "a" * 64
        adapter = self._adapt(fixture, signed_attestation_evidence=tampered)
        self.assertEqual(adapter["status"], "UNKNOWN")
        self.assertIsNone(adapter["replay_key"])

    def test_tampered_registration_is_unknown(self) -> None:
        fixture = _signed_fixture()
        tampered = deepcopy(fixture["registration"])
        tampered["key_binding"]["public_key_sha256"] = "a" * 64
        adapter = self._adapt(fixture, registration=tampered)
        self.assertEqual(adapter["mapping_status"], "UNKNOWN")

    def test_expected_signed_hash_substitution_is_unknown(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture, expected_signed_attestation_hash="a" * 64)
        self.assertEqual(adapter["status"], "UNKNOWN")

    def test_review_nonce_substitution_is_unknown(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture, review_nonce_hash="a" * 64)
        self.assertEqual(adapter["status"], "UNKNOWN")

    def test_registration_hash_substitution_is_unknown(self) -> None:
        fixture = _signed_fixture()
        adapter = self._adapt(fixture, expected_registration_hash="a" * 64)
        self.assertEqual(adapter["status"], "UNKNOWN")

    def test_resealed_source_authentication_promotion_is_unknown(self) -> None:
        fixture = _signed_fixture()
        promoted = deepcopy(fixture["evidence"])
        promoted["facts"]["source_baseline_authenticated"] = True
        promoted.pop("evidence_hash")
        promoted = seal_strict_canonical_document(promoted, "evidence_hash")
        adapter = self._adapt(fixture, signed_attestation_evidence=promoted)
        self.assertEqual(adapter["status"], "UNKNOWN")
        self.assertFalse(adapter["facts"]["source_evidence_exactly_verified"])

    def test_extra_signed_field_is_unknown(self) -> None:
        fixture = _signed_fixture()
        expanded = deepcopy(fixture["signed"])
        expanded["route_registered"] = True
        adapter = self._adapt(fixture, signed_attestation=expanded)
        self.assertEqual(adapter["status"], "UNKNOWN")

    def test_mapping_is_deterministic(self) -> None:
        fixture = _signed_fixture()
        self.assertEqual(self._adapt(fixture), self._adapt(fixture))

    def test_replay_snapshot_consumes_adapter_output_and_blocks_exact_replay(self) -> None:
        fixture = _signed_fixture()
        replay_key = self._adapt(fixture)["replay_key"]
        snapshot = build_nonce_replay_snapshot_v1(entries=[replay_key])
        receipt = evaluate_nonce_replay_snapshot_gate_v1(
            candidate_replay_key=replay_key,
            replay_snapshot=snapshot,
        )
        self.assertEqual(receipt["gate_status"], "BLOCK")

    def test_atomic_reserve_consumes_adapter_output_without_authority_promotion(self) -> None:
        fixture = _signed_fixture()
        replay_key = self._adapt(fixture)["replay_key"]
        state = build_nonce_registry_synthetic_state_v1(
            reserved_replay_key_hashes=[],
            sequence=0,
            previous_registry_head_hash=None,
        )
        request = build_nonce_atomic_reserve_request_v1(
            candidate_replay_key=replay_key,
            expected_registry_head_hash=state["registry_head_hash"],
            request_nonce_hash="a" * 64,
        )
        transition = simulate_nonce_atomic_reserve_v1(
            registry_state=state,
            reserve_request=request,
        )["transition_receipt"]
        self.assertEqual(transition["outcome"], "RESERVED_IN_RETURNED_STATE")
        self.assertEqual(transition["gate_status"], "UNKNOWN")
        self.assertFalse(transition["durable_commit_verified"])


if __name__ == "__main__":
    unittest.main()
