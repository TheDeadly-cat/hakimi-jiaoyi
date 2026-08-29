from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_render_descriptor_review_intake_v1
    as review_intake,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1
    as subject,
)


def _v9_receipt(*_args: object, **_kwargs: object) -> dict[str, object]:
    return {
        "status": "PASS",
        "preregistration_exactly_verified": True,
        "preregistration_status": "BLOCKED",
        "blockers": [],
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class RenderDescriptorSignedReviewAttestationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.private_key = Ed25519PrivateKey.from_private_bytes(bytes([11]) * 32)
        self.other_private_key = Ed25519PrivateKey.from_private_bytes(bytes([12]) * 32)
        self.public_key = base64.b64encode(
            self.private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        self.other_public_key = base64.b64encode(
            self.other_private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        self.key_id = "review-key-20260822"
        self.nonce_hash = hashlib.sha256(
            b"synthetic-render-review-nonce-0202"
        ).hexdigest()
        self.v8 = {
            "preregistration_hash": "1" * 64,
            "source": {
                "evidence_summary_hashes": {
                    "registration_evidence_fixture_descriptor_sha256": "2" * 64
                }
            },
        }
        self.v9 = {
            "schema_version": review_intake.preregistration_v9.SCHEMA_VERSION,
            "static_fingerprint": review_intake.preregistration_v9.STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "contract_state": "KNOWN",
            "preregistration_hash": "3" * 64,
            "source": {"immutable_v8_preregistration_hash": "1" * 64},
            "facts": {
                "presentation_http_contract_v3_versioned": True,
                "presentation_http_transport_registered": False,
                "render_descriptor_independently_reviewed": False,
                "presentation_registration_v1_activated": False,
                "ui_mounted": False,
                "runtime_consumer_bound": False,
                "profitability_proven": False,
            },
            "authority": {
                "descriptive_only": True,
                "http_route_registration_allowed": False,
                "presentation_mount_allowed": False,
                "current_admission_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.context = {
            "preregistration_v8_document": self.v8,
            "http_candidate_response": {"response_hash": "4" * 64},
            "http_candidate_request": {"schema": "request"},
            "v8_verification_context": {"exact": True},
            "successor_implementation_sha256": {"exact": "5" * 64},
        }
        self.verifier = mock.patch.object(
            review_intake, "_VERIFY_V9", side_effect=_v9_receipt
        )
        self.verifier.start()
        self.addCleanup(self.verifier.stop)
        self.request = review_intake.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
            self.v9,
            v9_verification_context=self.context,
        )
        self.claim = {
            "schema_version": review_intake.CLAIM_SCHEMA_VERSION,
            "review_request_hash": self.request["review_request_hash"],
            "descriptor_sha256": self.request["review_target"]["descriptor_sha256"],
            "reviewer_claim_id": "external-review-claim-alpha",
            "reviewer_process_id": "external-review-process-beta",
            "independence_claimed": True,
            "rubric_results": {
                key: True for key in review_intake.REVIEW_RUBRIC_KEYS
            },
        }
        self.intake = review_intake.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
            self.request,
            self.claim,
            self.v9,
            v9_verification_context=self.context,
        )
        self.registration = self._registration()
        self.unsigned = self._unsigned()
        self.signature = base64.b64encode(
            self.private_key.sign(bytes.fromhex(self.unsigned["unsigned_attestation_hash"]))
        ).decode("ascii")
        self.signed = subject.assemble_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
            self.unsigned,
            self.signature,
        )

    def _registration(self, **overrides: object) -> dict:
        arguments = {
            "reviewer_claim_id": self.claim["reviewer_claim_id"],
            "reviewer_process_id": self.claim["reviewer_process_id"],
            "key_id": self.key_id,
            "public_key_base64": self.public_key,
        }
        arguments.update(overrides)
        return subject.build_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
            **arguments
        )

    def _unsigned(self, **overrides: object) -> dict:
        arguments = {
            "registration": self.registration,
            "review_request_document": self.request,
            "review_claim": self.claim,
            "claim_intake_document": self.intake,
            "preregistration_v9_document": self.v9,
            "public_key_base64": self.public_key,
            "key_id": self.key_id,
            "expected_registration_hash": self.registration["registration_hash"],
            "review_nonce_hash": self.nonce_hash,
            "v9_verification_context": self.context,
        }
        arguments.update(overrides)
        return subject.build_unsigned_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_attestation_v1(
            **arguments
        )

    def _evaluate(self, **overrides: object) -> dict:
        arguments = {
            "registration": self.registration,
            "signed_attestation": self.signed,
            "review_request_document": self.request,
            "review_claim": self.claim,
            "claim_intake_document": self.intake,
            "preregistration_v9_document": self.v9,
            "public_key_base64": self.public_key,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_signed_attestation_hash": self.signed["attestation_hash"],
            "review_nonce_hash": self.nonce_hash,
            "v9_verification_context": self.context,
        }
        arguments.update(overrides)
        return subject.evaluate_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
            **arguments
        )

    def test_registration_is_deterministic_redacted_and_exactly_verifiable(self) -> None:
        self.assertEqual(self.registration, self._registration())
        encoded = json.dumps(self.registration, sort_keys=True)
        self.assertNotIn(self.claim["reviewer_claim_id"], encoded)
        self.assertNotIn(self.claim["reviewer_process_id"], encoded)
        self.assertNotIn(self.public_key, encoded)
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
                self.registration,
                reviewer_claim_id=self.claim["reviewer_claim_id"],
                reviewer_process_id=self.claim["reviewer_process_id"],
                key_id=self.key_id,
                public_key_base64=self.public_key,
                expected_registration_hash=self.registration["registration_hash"],
            )
        )

    def test_registration_verifier_rejects_pin_and_shape_drift(self) -> None:
        extra = copy.deepcopy(self.registration)
        extra["compatibility_alias"] = True
        for registration, expected_hash in (
            (self.registration, "0" * 64),
            (extra, self.registration["registration_hash"]),
        ):
            with self.subTest(registration=registration):
                self.assertFalse(
                    subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
                        registration,
                        reviewer_claim_id=self.claim["reviewer_claim_id"],
                        reviewer_process_id=self.claim["reviewer_process_id"],
                        key_id=self.key_id,
                        public_key_base64=self.public_key,
                        expected_registration_hash=expected_hash,
                    )
                )

    def test_registration_rejects_malformed_key_and_identifier(self) -> None:
        cases = (
            {"public_key_base64": "not-base64"},
            {"public_key_base64": base64.b64encode(bytes(31)).decode("ascii")},
            {"key_id": " bad key "},
            {"reviewer_claim_id": " "},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    self._registration(**overrides)

    def test_unsigned_payload_is_deterministic_and_binds_full_lineage(self) -> None:
        self.assertEqual(self.unsigned, self._unsigned())
        binding = self.unsigned["review_binding"]
        self.assertEqual(binding["review_request_hash"], self.request["review_request_hash"])
        self.assertEqual(binding["claim_intake_hash"], self.intake["intake_hash"])
        self.assertEqual(binding["descriptor_sha256"], self.claim["descriptor_sha256"])
        self.assertEqual(binding["review_nonce_hash"], self.nonce_hash)
        self.assertEqual(self.unsigned["signature_contract"]["domain"], subject.SIGNATURE_DOMAIN)

    def test_unsigned_payload_rejects_request_and_intake_tamper(self) -> None:
        request = copy.deepcopy(self.request)
        request["facts"]["independent_review_complete"] = True
        intake = copy.deepcopy(self.intake)
        intake["facts"]["independent_review_complete"] = True
        for overrides in (
            {"review_request_document": request},
            {"claim_intake_document": intake},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    self._unsigned(**overrides)

    def test_unsigned_payload_rejects_claim_registration_and_nonce_drift(self) -> None:
        claim = copy.deepcopy(self.claim)
        claim["reviewer_process_id"] = "different-process"
        cases = (
            {"review_claim": claim},
            {"expected_registration_hash": "0" * 64},
            {"review_nonce_hash": "bad"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    self._unsigned(**overrides)

    def test_assembler_rejects_signature_length_and_unsigned_tamper(self) -> None:
        tampered = copy.deepcopy(self.unsigned)
        tampered["review_binding"]["descriptor_sha256"] = "9" * 64
        cases = (
            (self.unsigned, base64.b64encode(bytes(63)).decode("ascii")),
            (tampered, self.signature),
        )
        for unsigned, signature in cases:
            with self.subTest(unsigned=unsigned):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    subject.assemble_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
                        unsigned,
                        signature,
                    )

    def test_happy_path_reports_only_bounded_local_crypto_facts(self) -> None:
        evidence = self._evaluate()
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["verification_state"], subject.VERIFICATION_STATE)
        self.assertTrue(evidence["facts"]["detached_signature_verified"])
        self.assertTrue(evidence["facts"]["review_nonce_hash_bound"])
        self.assertFalse(evidence["facts"]["real_world_reviewer_identity_verified"])
        self.assertFalse(evidence["facts"]["review_nonce_uniqueness_verified"])
        self.assertFalse(evidence["facts"]["independent_review_complete"])

    def test_wrong_signer_signature_is_rejected(self) -> None:
        signature = base64.b64encode(
            self.other_private_key.sign(
                bytes.fromhex(self.unsigned["unsigned_attestation_hash"])
            )
        ).decode("ascii")
        signed = subject.assemble_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
            self.unsigned,
            signature,
        )
        with self.assertRaises(subject.RenderDescriptorSignedReviewContractError):
            self._evaluate(
                signed_attestation=signed,
                expected_signed_attestation_hash=signed["attestation_hash"],
            )

    def test_wrong_public_key_is_rejected(self) -> None:
        with self.assertRaises(subject.RenderDescriptorSignedReviewContractError):
            self._evaluate(public_key_base64=self.other_public_key)

    def test_expected_attestation_hash_and_nonce_drift_are_rejected(self) -> None:
        for overrides in (
            {"expected_signed_attestation_hash": "0" * 64},
            {"review_nonce_hash": "6" * 64},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    self._evaluate(**overrides)

    def test_signed_attestation_extra_field_and_hash_tamper_are_rejected(self) -> None:
        extra = copy.deepcopy(self.signed)
        extra["compatibility_alias"] = True
        tampered = copy.deepcopy(self.signed)
        tampered["attestation_hash"] = "7" * 64
        for signed in (extra, tampered):
            with self.subTest(signed=signed):
                with self.assertRaises(
                    subject.RenderDescriptorSignedReviewContractError
                ):
                    self._evaluate(signed_attestation=signed)

    def test_evidence_public_verifier_rebuilds_and_rejects_projection_tamper(self) -> None:
        evidence = self._evaluate()
        arguments = {
            "registration": self.registration,
            "signed_attestation": self.signed,
            "review_request_document": self.request,
            "review_claim": self.claim,
            "claim_intake_document": self.intake,
            "preregistration_v9_document": self.v9,
            "public_key_base64": self.public_key,
            "expected_registration_hash": self.registration["registration_hash"],
            "expected_signed_attestation_hash": self.signed["attestation_hash"],
            "review_nonce_hash": self.nonce_hash,
            "v9_verification_context": self.context,
        }
        self.assertTrue(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_evidence_v1(
                evidence,
                **arguments,
            )
        )
        tampered = copy.deepcopy(evidence)
        tampered["facts"]["independent_review_complete"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_evidence_v1(
                tampered,
                **arguments,
            )
        )

    def test_source_inputs_are_not_mutated(self) -> None:
        snapshot = copy.deepcopy(
            (
                self.registration,
                self.signed,
                self.request,
                self.claim,
                self.intake,
                self.v9,
                self.context,
            )
        )
        self._evaluate()
        self.assertEqual(
            snapshot,
            (
                self.registration,
                self.signed,
                self.request,
                self.claim,
                self.intake,
                self.v9,
                self.context,
            ),
        )

    def test_evidence_redacts_identity_key_and_signature_material(self) -> None:
        evidence = self._evaluate()
        encoded = json.dumps(evidence, sort_keys=True)
        self.assertNotIn(self.claim["reviewer_claim_id"], encoded)
        self.assertNotIn(self.claim["reviewer_process_id"], encoded)
        self.assertNotIn(self.public_key, encoded)
        self.assertNotIn(self.signature, encoded)
        self.assertFalse(evidence["facts"]["signature_material_embedded"])

    def test_all_review_activation_current_and_trading_authority_remain_locked(self) -> None:
        for document in (self.registration, self._evaluate()):
            self.assertTrue(document["authority"]["descriptive_only"])
            self.assertTrue(
                all(
                    value is False
                    for key, value in document["authority"].items()
                    if key != "descriptive_only"
                )
            )
            self.assertFalse(document["facts"]["independent_review_complete"])
            self.assertFalse(document["facts"]["profitability_proven"])

    def test_review_intake_implementation_pin_matches_current_file(self) -> None:
        path = (
            self.root
            / "exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_render_descriptor_review_intake_v1.py"
        )
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            subject.REVIEW_INTAKE_IMPLEMENTATION_SHA256,
        )

    def test_production_api_has_no_private_key_runtime_browser_or_promotion_literal(self) -> None:
        source = inspect.getsource(subject)
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("selenium", source.lower())
        self.assertNotIn("playwright", source.lower())
        self.assertNotIn("sqlite", source.lower())
        forbidden = "R" + "EADY"
        self.assertNotIn(forbidden, source)
        self.assertNotIn(forbidden, json.dumps(self._evaluate()).upper())


if __name__ == "__main__":
    unittest.main()
