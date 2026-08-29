from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v7 as budget_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v6 as v6_tests


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class StrategyCorrelationClusterEffectiveBetBudgetV7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v6 = v6_tests.StrategyCorrelationClusterEffectiveBetBudgetV6Tests(
            methodName="test_v6_binds_current_head_snapshot_and_v5_budget"
        )
        self.v6.setUp()
        self.clock_private = Ed25519PrivateKey.generate()
        self.clock_spki = _spki(self.clock_private)
        self.clock_provider_kwargs = {
            "provider_id": "synthetic.evaluation.clock.provider.v1",
            "key_id": "synthetic.evaluation.clock.key.v1",
            "public_key_spki_sha256": hashlib.sha256(self.clock_spki).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "account_scope_hash": self.v6.policy["source"]["account_scope_hash"],
            "implementation_claim_sha256": _hash("synthetic-clock-implementation"),
        }
        self.clock_provider = (
            budget_v7.build_evaluation_clock_provider_preregistration_v1(
                **self.clock_provider_kwargs
            )
        )
        self.clock_bundle = self.build_clock_bundle(
            evaluated_at=self.v6.observed_at + 500,
            counter=41,
            label="current-clock",
        )

    def assert_authority_locked(self, authority) -> None:
        self.assertTrue(authority["descriptive_only"])
        self.assertFalse(
            any(
                value
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def build_clock_bundle(
        self,
        *,
        evaluated_at: int,
        counter: int,
        label: str,
        subject_overrides=None,
        provider=None,
        provider_kwargs=None,
        public_spki=None,
        signing_key=None,
    ):
        provider = self.clock_provider if provider is None else provider
        provider_kwargs = (
            self.clock_provider_kwargs
            if provider_kwargs is None
            else provider_kwargs
        )
        public_spki = self.clock_spki if public_spki is None else public_spki
        signing_key = self.clock_private if signing_key is None else signing_key
        subject = {
            "subject_policy_hash": self.v6.policy["policy_hash"],
            "subject_transition_hash": self.v6.transition["transition_hash"],
            "subject_current_state_hash": self.v6.transition["next_state_hash"],
            "subject_snapshot_claim_hash": self.v6.bundle["claim"][
                "snapshot_claim_hash"
            ],
        }
        subject.update(subject_overrides or {})
        claim_kwargs = {
            "clock_provider_preregistration_kwargs": provider_kwargs,
            "attestation_id_hash": _hash(label),
            "clock_counter": counter,
            "evaluated_at_unix_ms": evaluated_at,
            **subject,
        }
        claim = budget_v7.build_evaluation_time_claim_v1(
            provider,
            **claim_kwargs,
        )
        signature = signing_key.sign(bytes.fromhex(claim["clock_claim_hash"]))
        public_key_spki_base64 = _b64(public_spki)
        signature_base64 = _b64(signature)
        signed = budget_v7.build_signed_evaluation_time_attestation_v1(
            claim,
            provider,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_clock_claim_hash=claim["clock_claim_hash"],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "public_key_spki_base64": public_key_spki_base64,
            "signature_base64": signature_base64,
            "expected_clock_claim_hash": claim["clock_claim_hash"],
            "expected_signed_clock_attestation_hash": signed[
                "signed_clock_attestation_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = budget_v7.evaluate_signed_evaluation_time_attestation_v1(
            signed,
            claim,
            provider,
            **evaluation_kwargs,
        )
        return {
            "provider": provider,
            "provider_kwargs": provider_kwargs,
            "claim": claim,
            "signed": signed,
            "evidence": evidence,
            "evaluation_kwargs": evaluation_kwargs,
        }

    def call_parts(self, clock_bundle=None):
        clock_bundle = self.clock_bundle if clock_bundle is None else clock_bundle
        args = (
            clock_bundle["evidence"],
            clock_bundle["signed"],
            clock_bundle["claim"],
            clock_bundle["provider"],
            self.v6.transition,
            self.v6.previous_state,
            self.v6.policy,
            self.v6.bundle["evidence"],
            self.v6.bundle["signed"],
            self.v6.bundle["claim"],
            self.v6.base.provider,
            self.v6.base.preregistration,
            self.v6.base.matrix,
            self.v6.base.audit,
        )
        kwargs = dict(self.v6.base.increase_kwargs)
        kwargs.update(
            {
                "expected_clock_evidence_hash": clock_bundle["evidence"][
                    "clock_evidence_hash"
                ],
                "clock_evaluation_kwargs": clock_bundle["evaluation_kwargs"],
                "expected_transition_hash": self.v6.transition["transition_hash"],
                "transition_evaluation_kwargs": self.v6.transition_kwargs,
                "expected_current_state_hash": self.v6.transition["next_state_hash"],
                "expected_snapshot_evidence_hash": self.v6.bundle["evidence"][
                    "snapshot_evidence_hash"
                ],
                "snapshot_evaluation_kwargs": self.v6.bundle["evaluation_kwargs"],
            }
        )
        return args, kwargs

    def evaluate_v7(self, clock_bundle=None, **overrides):
        args, kwargs = self.call_parts(clock_bundle)
        kwargs.update(overrides)
        return budget_v7.evaluate_strategy_correlation_cluster_effective_bet_budget_v7(
            *args,
            **kwargs,
        )

    def test_reproduces_v6_caller_backdated_time_gap(self):
        backdated = self.v6.evaluate_v6(
            evaluated_at_unix_ms=self.v6.observed_at + 500
        )
        later = self.v6.evaluate_v6(
            evaluated_at_unix_ms=self.v6.observed_at + 5_000
        )
        self.assertEqual("PASS", backdated["status"])
        self.assertEqual("BLOCKED", later["status"])
        self.assertEqual(
            backdated["source"]["snapshot_claim_hash"],
            later["source"]["snapshot_claim_hash"],
        )
        self.assertFalse(backdated["facts"]["trusted_evaluation_clock_verified"])
        self.assertFalse(backdated["facts"]["runtime_assets_accessed"])

    def test_clock_provider_is_exact_blocked_and_authority_locked(self):
        self.assertTrue(
            budget_v7.verify_evaluation_clock_provider_preregistration_v1(
                self.clock_provider,
                **self.clock_provider_kwargs,
            )
        )
        self.assertEqual("BLOCKED", self.clock_provider["status"])
        self.assertFalse(
            self.clock_provider["facts"]["time_source_truth_verified"]
        )
        self.assert_authority_locked(self.clock_provider["authority"])

    def test_clock_claim_binds_exact_budget_subject(self):
        claim = self.clock_bundle["claim"]
        kwargs = self.clock_bundle["evaluation_kwargs"]
        self.assertTrue(
            budget_v7.verify_evaluation_time_claim_v1(
                claim,
                self.clock_provider,
                expected_clock_claim_hash=claim["clock_claim_hash"],
                **kwargs["claim_build_kwargs"],
            )
        )
        self.assertEqual(
            self.v6.transition["next_state_hash"],
            claim["subject"]["current_state_hash"],
        )
        self.assertEqual(
            self.v6.bundle["claim"]["snapshot_claim_hash"],
            claim["subject"]["snapshot_claim_hash"],
        )

    def test_signed_clock_candidate_is_exact_and_authority_locked(self):
        signed = self.clock_bundle["signed"]
        kwargs = self.clock_bundle["evaluation_kwargs"]
        self.assertTrue(
            budget_v7.verify_signed_evaluation_time_attestation_v1(
                signed,
                self.clock_bundle["claim"],
                self.clock_provider,
                expected_signed_clock_attestation_hash=signed[
                    "signed_clock_attestation_hash"
                ],
                public_key_spki_base64=kwargs["public_key_spki_base64"],
                signature_base64=kwargs["signature_base64"],
                expected_clock_claim_hash=kwargs["expected_clock_claim_hash"],
                claim_build_kwargs=kwargs["claim_build_kwargs"],
            )
        )
        self.assertEqual("CANDIDATE", signed["status"])
        self.assert_authority_locked(signed["authority"])

    def test_clock_signature_evidence_pass_is_not_clock_truth(self):
        evidence = self.clock_bundle["evidence"]
        self.assertEqual("PASS", evidence["status"])
        self.assertTrue(
            evidence["facts"]["preregistered_clock_key_signature_verified"]
        )
        self.assertFalse(evidence["facts"]["clock_provider_identity_verified"])
        self.assertFalse(evidence["facts"]["time_source_truth_verified"])
        self.assertFalse(evidence["facts"]["clock_counter_continuity_verified"])
        self.assert_authority_locked(evidence["authority"])

    def test_v7_accepts_time_only_from_exact_signed_claim(self):
        result = self.evaluate_v7()
        signature = inspect.signature(
            budget_v7.evaluate_strategy_correlation_cluster_effective_bet_budget_v7
        )
        self.assertNotIn("evaluated_at_unix_ms", signature.parameters)
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertEqual(
            self.v6.observed_at + 500,
            result["clock_summary"]["evaluated_at_unix_ms"],
        )
        self.assertFalse(result["facts"]["caller_evaluation_time_input_accepted"])
        self.assertTrue(result["facts"]["signed_evaluation_time_bound_to_budget"])
        self.assertFalse(result["facts"]["trusted_evaluation_clock_verified"])
        self.assert_authority_locked(result["authority"])

    def test_signed_stale_time_preserves_v6_freshness_block(self):
        stale = self.build_clock_bundle(
            evaluated_at=self.v6.observed_at + 5_000,
            counter=42,
            label="stale-clock",
        )
        self.assertEqual("PASS", stale["evidence"]["status"])
        result = self.evaluate_v7(stale)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("V6_EFFECTIVE_BUDGET_PASS", result["blockers"])

    def test_clock_subject_drift_blocks_v7(self):
        cases = {
            "policy": {"subject_policy_hash": _hash("wrong-policy")},
            "transition": {"subject_transition_hash": _hash("wrong-transition")},
            "head": {"subject_current_state_hash": _hash("wrong-head")},
            "snapshot": {"subject_snapshot_claim_hash": _hash("wrong-snapshot")},
        }
        for label, override in cases.items():
            with self.subTest(label=label):
                bundle = self.build_clock_bundle(
                    evaluated_at=self.v6.observed_at + 500,
                    counter=41,
                    label=f"subject-{label}",
                    subject_overrides=override,
                )
                self.assertEqual("PASS", bundle["evidence"]["status"])
                result = self.evaluate_v7(bundle)
                self.assertEqual("BLOCKED", result["status"])
                self.assertIn("CLOCK_SUBJECT_BINDING_EXACT", result["blockers"])

    def test_clock_account_scope_drift_blocks_v7(self):
        provider_kwargs = {
            **self.clock_provider_kwargs,
            "account_scope_hash": _hash("wrong-account-scope"),
        }
        provider = budget_v7.build_evaluation_clock_provider_preregistration_v1(
            **provider_kwargs
        )
        bundle = self.build_clock_bundle(
            evaluated_at=self.v6.observed_at + 500,
            counter=41,
            label="wrong-scope",
            provider=provider,
            provider_kwargs=provider_kwargs,
        )
        self.assertEqual("PASS", bundle["evidence"]["status"])
        result = self.evaluate_v7(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("CLOCK_ACCOUNT_SCOPE_BINDING_EXACT", result["blockers"])

    def test_wrong_signing_key_is_blocked(self):
        wrong_key = Ed25519PrivateKey.generate()
        bundle = self.build_clock_bundle(
            evaluated_at=self.v6.observed_at + 500,
            counter=41,
            label="wrong-signer",
            signing_key=wrong_key,
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v7(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_CLOCK_KEY_SIGNATURE_PASS", result["blockers"])

    def test_tampered_clock_claim_is_rejected(self):
        bundle = copy.deepcopy(self.clock_bundle)
        bundle["claim"]["clock_reading"]["evaluated_at_unix_ms"] += 1
        result = self.evaluate_v7(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_CLOCK_EVIDENCE_EXACT", result["blockers"])

    def test_provider_preregistration_drift_is_rejected(self):
        provider = copy.deepcopy(self.clock_provider)
        provider["status"] = "PASS"
        with self.assertRaises(ValueError):
            budget_v7.build_evaluation_time_claim_v1(
                provider,
                **self.clock_bundle["evaluation_kwargs"]["claim_build_kwargs"],
            )

    def test_exact_verifiers_reject_resealed_promotions(self):
        provider = copy.deepcopy(self.clock_provider)
        del provider["clock_provider_hash"]
        provider["status"] = "PASS"
        provider = seal_strict_canonical_document(provider, "clock_provider_hash")
        self.assertFalse(
            budget_v7.verify_evaluation_clock_provider_preregistration_v1(
                provider,
                **self.clock_provider_kwargs,
            )
        )

        claim = copy.deepcopy(self.clock_bundle["claim"])
        original_claim_hash = claim.pop("clock_claim_hash")
        claim["status"] = "PASS"
        claim = seal_strict_canonical_document(claim, "clock_claim_hash")
        self.assertFalse(
            budget_v7.verify_evaluation_time_claim_v1(
                claim,
                self.clock_provider,
                expected_clock_claim_hash=original_claim_hash,
                **self.clock_bundle["evaluation_kwargs"]["claim_build_kwargs"],
            )
        )

        evidence = copy.deepcopy(self.clock_bundle["evidence"])
        original_evidence_hash = evidence.pop("clock_evidence_hash")
        evidence["status"] = "BLOCKED"
        evidence = seal_strict_canonical_document(evidence, "clock_evidence_hash")
        self.assertFalse(
            budget_v7.verify_signed_evaluation_time_evidence_v1(
                evidence,
                self.clock_bundle["signed"],
                self.clock_bundle["claim"],
                self.clock_provider,
                expected_clock_evidence_hash=original_evidence_hash,
                **self.clock_bundle["evaluation_kwargs"],
            )
        )

    def test_v7_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v7()
        args, kwargs = self.call_parts()
        self.assertTrue(
            budget_v7.verify_strategy_correlation_cluster_effective_bet_budget_v7(
                result,
                *args,
                expected_budget_v7_hash=result["budget_v7_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        original_hash = tampered.pop("budget_v7_hash")
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v7_hash")
        self.assertFalse(
            budget_v7.verify_strategy_correlation_cluster_effective_bet_budget_v7(
                tampered,
                *args,
                expected_budget_v7_hash=original_hash,
                **kwargs,
            )
        )

    def test_boolean_time_and_counter_aliases_are_rejected(self):
        claim_kwargs = self.clock_bundle["evaluation_kwargs"]["claim_build_kwargs"]
        with self.assertRaises(ValueError):
            budget_v7.build_evaluation_time_claim_v1(
                self.clock_provider,
                **{**claim_kwargs, "clock_counter": True},
            )
        with self.assertRaises(ValueError):
            budget_v7.build_evaluation_time_claim_v1(
                self.clock_provider,
                **{**claim_kwargs, "evaluated_at_unix_ms": True},
            )

    def test_malformed_base64_and_signature_length_are_rejected(self):
        kwargs = self.clock_bundle["evaluation_kwargs"]
        with self.assertRaises(ValueError):
            budget_v7.build_signed_evaluation_time_attestation_v1(
                self.clock_bundle["claim"],
                self.clock_provider,
                public_key_spki_base64="not-base64!",
                signature_base64=kwargs["signature_base64"],
                expected_clock_claim_hash=kwargs["expected_clock_claim_hash"],
                claim_build_kwargs=kwargs["claim_build_kwargs"],
            )
        with self.assertRaises(ValueError):
            budget_v7.build_signed_evaluation_time_attestation_v1(
                self.clock_bundle["claim"],
                self.clock_provider,
                public_key_spki_base64=kwargs["public_key_spki_base64"],
                signature_base64=_b64(b"short"),
                expected_clock_claim_hash=kwargs["expected_clock_claim_hash"],
                claim_build_kwargs=kwargs["claim_build_kwargs"],
            )

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        before = copy.deepcopy(
            {
                "clock": self.clock_bundle,
                "transition": self.v6.transition,
                "state": self.v6.previous_state,
                "policy": self.v6.policy,
                "snapshot": self.v6.bundle,
            }
        )
        first = self.evaluate_v7()
        second = self.evaluate_v7()
        self.assertEqual(first, second)
        self.assertEqual(before["clock"], self.clock_bundle)
        self.assertEqual(before["transition"], self.v6.transition)
        self.assertEqual(before["state"], self.v6.previous_state)
        self.assertEqual(before["policy"], self.v6.policy)
        self.assertEqual(before["snapshot"], self.v6.bundle)

        def keys(value):
            if isinstance(value, dict):
                result = set(value)
                for child in value.values():
                    result.update(keys(child))
                return result
            if isinstance(value, list):
                result = set()
                for child in value:
                    result.update(keys(child))
                return result
            return set()

        output_keys = keys(first)
        self.assertNotIn("positions", output_keys)
        self.assertNotIn("public_key_spki_base64", output_keys)
        self.assertNotIn("signature_base64", output_keys)
        self.assertNotIn("signature", output_keys)

    def test_production_has_no_private_key_clock_io_network_or_runtime_access(self):
        source = Path(budget_v7.__file__).read_text(encoding="utf-8")
        forbidden = (
            "Ed25519PrivateKey",
            "private_key",
            "time.time",
            "datetime.now",
            "Path(",
            "open(",
            "requests.",
            "urllib.",
            "sqlite3",
            ".env",
            "runtime/",
            "runtime\\\\",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
