from __future__ import annotations

import base64
import copy
import json
import sys
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1
    as preregistration,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_intake_v1
    as review,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1
    as signed_review,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


def _review_chain() -> tuple[dict, dict, dict, dict]:
    source = preregistration.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1()
    request = review.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
        source
    )
    claim = {
        "schema_version": review.CLAIM_SCHEMA_VERSION,
        "review_request_hash": request["review_request_hash"],
        "reviewer_claim_id": "external-reviewer-1",
        "reviewer_process_id": "isolated-source-review-1",
        "independence_claimed": True,
        "observed_source_hashes": copy.deepcopy(
            request["review_target"]["source_baseline_pins"]
        ),
        "rubric_results": {key: True for key in review.REVIEW_RUBRIC_KEYS},
    }
    intake = review.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
        request, claim, source
    )
    return source, request, claim, intake


def _key_material() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, base64.b64encode(public_key).decode("ascii")


def _signed_fixture() -> dict:
    source, request, claim, intake = _review_chain()
    private_key, public_key_base64 = _key_material()
    registration = signed_review.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1(
        reviewer_claim_id=claim["reviewer_claim_id"],
        reviewer_process_id=claim["reviewer_process_id"],
        key_id="source-review-key-1",
        public_key_base64=public_key_base64,
    )
    nonce_hash = "9" * 64
    unsigned = signed_review.build_unsigned_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_attestation_v1(
        registration,
        request,
        claim,
        intake,
        source,
        public_key_base64,
        expected_registration_hash=registration["registration_hash"],
        review_nonce_hash=nonce_hash,
    )
    signature = private_key.sign(bytes.fromhex(unsigned["unsigned_attestation_hash"]))
    signature_base64 = base64.b64encode(signature).decode("ascii")
    signed = signed_review.assemble_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
        unsigned, signature_base64
    )
    evidence = signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
        registration,
        signed,
        request,
        claim,
        intake,
        source,
        public_key_base64,
        expected_registration_hash=registration["registration_hash"],
        expected_signed_attestation_hash=signed["signed_attestation_hash"],
        review_nonce_hash=nonce_hash,
    )
    return {
        "source": source,
        "request": request,
        "claim": claim,
        "intake": intake,
        "private_key": private_key,
        "public_key_base64": public_key_base64,
        "registration": registration,
        "nonce_hash": nonce_hash,
        "unsigned": unsigned,
        "signature_base64": signature_base64,
        "signed": signed,
        "evidence": evidence,
    }


class MembershipSourceBaselineSignedReviewV1Tests(unittest.TestCase):
    def test_key_registration_is_exact_redacted_and_untrusted(self) -> None:
        fixture = _signed_fixture()
        registration = fixture["registration"]
        self.assertTrue(
            signed_review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1(
                registration,
                fixture["claim"],
                fixture["public_key_base64"],
                expected_registration_hash=registration["registration_hash"],
            )
        )
        rendered = json.dumps(registration, sort_keys=True)
        self.assertNotIn(fixture["claim"]["reviewer_claim_id"], rendered)
        self.assertNotIn(fixture["public_key_base64"], rendered)
        self.assertIs(registration["facts"]["registration_governance_verified"], False)

    def test_unsigned_attestation_exactly_binds_review_chain(self) -> None:
        fixture = _signed_fixture()
        binding = fixture["unsigned"]["binding"]
        self.assertEqual(binding["review_request_hash"], fixture["request"]["review_request_hash"])
        self.assertEqual(binding["claim_intake_hash"], fixture["intake"]["intake_hash"])
        self.assertEqual(binding["review_nonce_hash"], fixture["nonce_hash"])
        self.assertIs(fixture["unsigned"]["facts"]["signature_present"], False)

    def test_valid_signature_is_verified_without_trust_promotion(self) -> None:
        fixture = _signed_fixture()
        evidence = fixture["evidence"]
        self.assertEqual(evidence["verification_state"], signed_review.VERIFICATION_STATE)
        self.assertIs(evidence["facts"]["detached_signature_verified"], True)
        self.assertIs(evidence["facts"]["source_baseline_authenticated"], False)
        self.assertIs(evidence["facts"]["independent_review_complete"], False)
        self.assertIs(evidence["authority"]["mount_allowed"], False)
        self.assertTrue(
            signed_review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1(
                evidence,
                fixture["registration"],
                fixture["signed"],
                fixture["request"],
                fixture["claim"],
                fixture["intake"],
                fixture["source"],
                fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"],
                expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"],
                review_nonce_hash=fixture["nonce_hash"],
            )
        )

    def test_wrong_public_key_is_rejected(self) -> None:
        fixture = _signed_fixture()
        _, wrong_public_key = _key_material()
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
                fixture["registration"], fixture["signed"], fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], wrong_public_key,
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
            )

    def test_tampered_review_claim_is_rejected(self) -> None:
        fixture = _signed_fixture()
        claim = copy.deepcopy(fixture["claim"])
        claim["reviewer_process_id"] = "different-process"
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
                fixture["registration"], fixture["signed"], fixture["request"], claim, fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
            )

    def test_review_nonce_substitution_is_rejected(self) -> None:
        fixture = _signed_fixture()
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
                fixture["registration"], fixture["signed"], fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash="8" * 64
            )

    def test_signature_tampering_is_rejected(self) -> None:
        fixture = _signed_fixture()
        raw = bytearray(base64.b64decode(fixture["signature_base64"]))
        raw[0] ^= 1
        tampered_signature = base64.b64encode(bytes(raw)).decode("ascii")
        tampered_signed = signed_review.assemble_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
            fixture["unsigned"], tampered_signature
        )
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
                fixture["registration"], tampered_signed, fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=tampered_signed["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
            )

    def test_registration_hash_substitution_is_rejected(self) -> None:
        fixture = _signed_fixture()
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.build_unsigned_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_attestation_v1(
                fixture["registration"], fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash="0" * 64, review_nonce_hash=fixture["nonce_hash"]
            )

    def test_extra_signed_field_is_rejected(self) -> None:
        fixture = _signed_fixture()
        signed = copy.deepcopy(fixture["signed"])
        signed["compatibility"] = True
        with self.assertRaises(signed_review.SourceBaselineSignedReviewContractError):
            signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
                fixture["registration"], signed, fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
            )

    def test_evidence_embeds_no_raw_identity_key_or_signature(self) -> None:
        fixture = _signed_fixture()
        rendered = json.dumps(fixture["evidence"], sort_keys=True)
        self.assertNotIn(fixture["claim"]["reviewer_claim_id"], rendered)
        self.assertNotIn(fixture["public_key_base64"], rendered)
        self.assertNotIn(fixture["signature_base64"], rendered)
        self.assertIs(fixture["evidence"]["facts"]["signature_material_embedded"], False)

    def test_resealed_authentication_promotion_fails_exact_verifier(self) -> None:
        fixture = _signed_fixture()
        evidence = copy.deepcopy(fixture["evidence"])
        evidence["facts"]["source_baseline_authenticated"] = True
        evidence.pop("evidence_hash")
        evidence = seal_strict_canonical_document(evidence, "evidence_hash")
        self.assertFalse(
            signed_review.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1(
                evidence, fixture["registration"], fixture["signed"], fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
                expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
            )
        )

    def test_inputs_are_not_mutated(self) -> None:
        fixture = _signed_fixture()
        keys = ("registration", "signed", "request", "claim", "intake", "source")
        before = {key: copy.deepcopy(fixture[key]) for key in keys}
        signed_review.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
            fixture["registration"], fixture["signed"], fixture["request"], fixture["claim"], fixture["intake"], fixture["source"], fixture["public_key_base64"],
            expected_registration_hash=fixture["registration"]["registration_hash"], expected_signed_attestation_hash=fixture["signed"]["signed_attestation_hash"], review_nonce_hash=fixture["nonce_hash"]
        )
        for key in keys:
            self.assertEqual(fixture[key], before[key], key)


if __name__ == "__main__":
    unittest.main()
