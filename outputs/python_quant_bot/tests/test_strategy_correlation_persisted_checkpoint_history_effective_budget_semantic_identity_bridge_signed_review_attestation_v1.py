import base64
import copy
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_effective_budget_semantic_identity_bridge_signed_review_attestation_v1
    as bridge,
)
from tests.test_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1 import (
    StrategyCorrelationPersistedCheckpointHistoryCoverageEffectiveBudgetProvenanceBindingV1Tests
    as UpstreamBindingTests,
)


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _reseal(document, hash_field):
    mutated = copy.deepcopy(document)
    mutated.pop(hash_field, None)
    mutated[hash_field] = _digest(mutated)
    return mutated


class StrategyCorrelationPersistedCheckpointHistoryEffectiveBudgetSemanticIdentityBridgeSignedReviewAttestationV1Tests(
    unittest.TestCase
):
    reviewer_id = "synthetic-reviewer-adr0363"
    review_process_id = "synthetic-local-review-process-adr0363"
    claim_id = "correlation-semantic-identity-bridge-adr0363"
    review_nonce = "synthetic-review-nonce-adr0363"
    review_rationale = (
        "The history and budget artifacts express the same bounded research intent while "
        "retaining distinct technical window identities; this is a signed review claim only."
    )

    @classmethod
    def setUpClass(cls):
        UpstreamBindingTests.setUpClass()
        cls.source_preregistration = UpstreamBindingTests.preregistration
        cls.source_context = UpstreamBindingTests.preregistration_context
        cls.source_hash = cls.source_preregistration["preregistration_hash"]

        cls.private_key = Ed25519PrivateKey.generate()
        public_key = cls.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        cls.public_key_base64 = base64.b64encode(public_key).decode("ascii")

        cls.registration = bridge.build_strategy_correlation_semantic_identity_bridge_reviewer_key_registration_v1(
            cls.reviewer_id,
            cls.review_process_id,
            cls.public_key_base64,
        )
        if cls.registration is None:
            raise AssertionError("reviewer key registration did not build")
        cls.registration_hash = cls.registration["registration_hash"]

        cls.claim = bridge.build_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
            cls.source_preregistration,
            cls.claim_id,
            cls.review_rationale,
            expected_source_preregistration_hash=cls.source_hash,
            source_preregistration_verification_context=cls.source_context,
        )
        if cls.claim is None:
            raise AssertionError("semantic identity bridge claim did not build")
        cls.claim_hash = cls.claim["bridge_claim_hash"]

        cls.unsigned = bridge.build_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
            cls.registration,
            cls.claim,
            cls.source_preregistration,
            cls.review_nonce,
            expected_reviewer_key_registration_hash=cls.registration_hash,
            expected_bridge_claim_hash=cls.claim_hash,
            expected_source_preregistration_hash=cls.source_hash,
            source_preregistration_verification_context=cls.source_context,
        )
        if cls.unsigned is None:
            raise AssertionError("unsigned attestation did not build")
        cls.unsigned_hash = cls.unsigned["unsigned_attestation_hash"]

        signature = cls.private_key.sign(bytes.fromhex(cls.unsigned_hash))
        cls.signature_base64 = base64.b64encode(signature).decode("ascii")
        cls.signed = bridge.assemble_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_attestation_v1(
            cls.unsigned,
            cls.registration,
            cls.claim,
            cls.source_preregistration,
            cls.review_nonce,
            cls.public_key_base64,
            cls.signature_base64,
            expected_unsigned_attestation_hash=cls.unsigned_hash,
            expected_reviewer_key_registration_hash=cls.registration_hash,
            expected_bridge_claim_hash=cls.claim_hash,
            expected_source_preregistration_hash=cls.source_hash,
            source_preregistration_verification_context=cls.source_context,
        )
        if cls.signed is None:
            raise AssertionError("signed attestation did not assemble")
        cls.signed_hash = cls.signed["signed_attestation_hash"]

        cls.evidence = cls._evaluate()
        cls.evidence_hash = cls.evidence["evidence_hash"]

    @classmethod
    def _evaluate(
        cls,
        *,
        signed=None,
        unsigned=None,
        registration=None,
        claim=None,
        source_preregistration=None,
        review_nonce=None,
        expected_signed_hash=None,
        expected_unsigned_hash=None,
        expected_registration_hash=None,
        expected_claim_hash=None,
        expected_source_hash=None,
    ):
        return bridge.evaluate_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
            cls.signed if signed is None else signed,
            cls.unsigned if unsigned is None else unsigned,
            cls.registration if registration is None else registration,
            cls.claim if claim is None else claim,
            cls.source_preregistration
            if source_preregistration is None
            else source_preregistration,
            cls.review_nonce if review_nonce is None else review_nonce,
            expected_signed_attestation_hash=cls.signed_hash
            if expected_signed_hash is None
            else expected_signed_hash,
            expected_unsigned_attestation_hash=cls.unsigned_hash
            if expected_unsigned_hash is None
            else expected_unsigned_hash,
            expected_reviewer_key_registration_hash=cls.registration_hash
            if expected_registration_hash is None
            else expected_registration_hash,
            expected_bridge_claim_hash=cls.claim_hash
            if expected_claim_hash is None
            else expected_claim_hash,
            expected_source_preregistration_hash=cls.source_hash
            if expected_source_hash is None
            else expected_source_hash,
            source_preregistration_verification_context=cls.source_context,
        )

    def test_signed_claim_reaches_only_governance_unproven_state(self):
        self.assertEqual(self.evidence["status"], bridge.POSITIVE_STATE)
        self.assertTrue(self.evidence["facts"]["review_claim_integrity_verified"])
        self.assertFalse(
            self.evidence["facts"]["semantic_study_identity_equivalence_verified"]
        )
        self.assertIn(
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            self.evidence["blockers"],
        )
        self.assertTrue(
            bridge.verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
                self.evidence,
                self.signed,
                self.unsigned,
                self.registration,
                self.claim,
                self.source_preregistration,
                self.review_nonce,
                expected_evidence_hash=self.evidence_hash,
                expected_signed_attestation_hash=self.signed_hash,
                expected_unsigned_attestation_hash=self.unsigned_hash,
                expected_reviewer_key_registration_hash=self.registration_hash,
                expected_bridge_claim_hash=self.claim_hash,
                expected_source_preregistration_hash=self.source_hash,
                source_preregistration_verification_context=self.source_context,
            )
        )

    def test_claim_exactly_binds_distinct_source_identities(self):
        for field in (
            "history_study_identity_hash",
            "history_window_order_hash",
            "budget_window_order_hash",
            "budget_symbol_order_hash",
            "budget_cluster_partition_hash",
        ):
            self.assertEqual(self.claim[field], self.source_preregistration[field])
        self.assertNotEqual(
            self.claim["history_window_order_hash"],
            self.claim["budget_window_order_hash"],
        )
        self.assertFalse(self.claim["source_window_order_hashes_equal"])
        self.assertEqual(self.claim["relationship_claim"], bridge.RELATIONSHIP_CLAIM)

    def test_registration_redacts_raw_identity_and_public_key(self):
        rendered = json.dumps(self.registration, sort_keys=True)
        self.assertNotIn(self.reviewer_id, rendered)
        self.assertNotIn(self.review_process_id, rendered)
        self.assertNotIn(self.public_key_base64, rendered)
        self.assertEqual(
            self.registration["reviewer_id_sha256"],
            hashlib.sha256(self.reviewer_id.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            self.registration["review_process_id_sha256"],
            hashlib.sha256(self.review_process_id.encode("utf-8")).hexdigest(),
        )

    def test_resealed_signature_tamper_is_unknown(self):
        signature = bytearray(base64.b64decode(self.signed["signature_base64"]))
        signature[0] ^= 1
        tampered = copy.deepcopy(self.signed)
        tampered["signature_base64"] = base64.b64encode(signature).decode("ascii")
        tampered = _reseal(tampered, "signed_attestation_hash")
        evidence = self._evaluate(
            signed=tampered,
            expected_signed_hash=tampered["signed_attestation_hash"],
        )
        self.assertEqual(evidence["status"], bridge.UNKNOWN_STATE)

    def test_resealed_source_preregistration_tamper_is_unknown(self):
        tampered = copy.deepcopy(self.source_preregistration)
        tampered["budget_window_order_hash"] = "0" * 64
        tampered = _reseal(tampered, "preregistration_hash")
        evidence = self._evaluate(
            source_preregistration=tampered,
            expected_source_hash=tampered["preregistration_hash"],
        )
        self.assertEqual(evidence["status"], bridge.UNKNOWN_STATE)

    def test_resealed_relationship_claim_tamper_is_rejected(self):
        tampered = copy.deepcopy(self.claim)
        tampered["relationship_claim"] = "SEMANTIC_EQUIVALENCE_CONFIRMED"
        tampered["relationship_claim_sha256"] = hashlib.sha256(
            tampered["relationship_claim"].encode("utf-8")
        ).hexdigest()
        tampered = _reseal(tampered, "bridge_claim_hash")
        self.assertFalse(
            bridge.verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
                tampered,
                self.source_preregistration,
                expected_bridge_claim_hash=tampered["bridge_claim_hash"],
                expected_source_preregistration_hash=self.source_hash,
                source_preregistration_verification_context=self.source_context,
            )
        )

    def test_nonce_mismatch_is_rejected(self):
        self.assertFalse(
            bridge.verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
                self.unsigned,
                self.registration,
                self.claim,
                self.source_preregistration,
                "different-synthetic-review-nonce-adr0363",
                expected_unsigned_attestation_hash=self.unsigned_hash,
                expected_reviewer_key_registration_hash=self.registration_hash,
                expected_bridge_claim_hash=self.claim_hash,
                expected_source_preregistration_hash=self.source_hash,
                source_preregistration_verification_context=self.source_context,
            )
        )

    def test_resealed_authority_promotion_is_rejected(self):
        tampered = copy.deepcopy(self.evidence)
        tampered["authority"]["effective_budget_activation_allowed"] = True
        tampered = _reseal(tampered, "evidence_hash")
        self.assertFalse(
            bridge.verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
                tampered,
                self.signed,
                self.unsigned,
                self.registration,
                self.claim,
                self.source_preregistration,
                self.review_nonce,
                expected_evidence_hash=tampered["evidence_hash"],
                expected_signed_attestation_hash=self.signed_hash,
                expected_unsigned_attestation_hash=self.unsigned_hash,
                expected_reviewer_key_registration_hash=self.registration_hash,
                expected_bridge_claim_hash=self.claim_hash,
                expected_source_preregistration_hash=self.source_hash,
                source_preregistration_verification_context=self.source_context,
            )
        )

    def test_public_evidence_is_redacted_and_all_authority_is_locked(self):
        rendered = json.dumps(self.evidence, sort_keys=True)
        for secret_or_raw_value in (
            self.reviewer_id,
            self.review_process_id,
            self.review_nonce,
            self.review_rationale,
            self.public_key_base64,
            self.signature_base64,
        ):
            self.assertNotIn(secret_or_raw_value, rendered)
        self.assertTrue(self.evidence["authority"]["research_evidence_only"])
        for field, value in self.evidence["authority"].items():
            if field != "research_evidence_only":
                self.assertIs(value, False, field)
        self.assertFalse(self.evidence["facts"]["mounted"])
        self.assertFalse(self.evidence["facts"]["review_governance_verified"])
        self.assertFalse(self.evidence["facts"]["reviewer_independence_verified"])


if __name__ == "__main__":
    unittest.main()
