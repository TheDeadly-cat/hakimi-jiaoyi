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
    strategy_correlation_cluster_effective_bet_budget_v8 as budget_v8,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v7 as v7_tests


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class StrategyCorrelationClusterEffectiveBetBudgetV8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v7 = v7_tests.StrategyCorrelationClusterEffectiveBetBudgetV7Tests(
            methodName="test_v7_accepts_time_only_from_exact_signed_claim"
        )
        self.v7.setUp()
        self.store_private = Ed25519PrivateKey.generate()
        self.store_spki = _spki(self.store_private)
        self.store_provider_kwargs = {
            "provider_id": "synthetic.atomic.head.store.provider.v1",
            "key_id": "synthetic.atomic.head.store.key.v1",
            "public_key_spki_sha256": hashlib.sha256(self.store_spki).hexdigest(),
            "trust_domain": "synthetic.test-only",
            "account_scope_hash": self.v7.v6.policy["source"]["account_scope_hash"],
            "store_epoch_hash": _hash("synthetic-store-epoch"),
            "implementation_claim_sha256": _hash("synthetic-store-implementation"),
        }
        self.store_provider = (
            budget_v8.build_atomic_head_store_provider_preregistration_v1(
                **self.store_provider_kwargs
            )
        )
        self.previous_state_kwargs = {
            "atomic_store_provider_kwargs": self.store_provider_kwargs,
            "policy_hash": self.v7.v6.policy["policy_hash"],
            "state_revision": 17,
            "commit_index": 100,
            "clock_counter": 40,
            "clock_evidence_hash": _hash("previous-clock-evidence"),
            "snapshot_state_hash": self.v7.v6.previous_state["state_hash"],
            "snapshot_claim_hash": self.v7.v6.previous_state["state"][
                "last_snapshot_claim_hash"
            ],
            "transition_hash": _hash("previous-snapshot-transition"),
        }
        self.previous_state = budget_v8.build_atomic_head_state_v1(
            self.store_provider,
            **self.previous_state_kwargs,
        )
        self.atomic_bundle = self.build_atomic_bundle(self.v7.clock_bundle)

    def assert_authority_locked(self, authority) -> None:
        self.assertTrue(authority["descriptive_only"])
        self.assertFalse(
            any(
                value
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def build_atomic_bundle(
        self,
        clock_bundle,
        *,
        next_snapshot_state_hash=None,
        next_snapshot_claim_hash=None,
        next_transition_hash=None,
        provider=None,
        provider_kwargs=None,
        signing_key=None,
        public_spki=None,
        label="current-atomic-commit",
    ):
        provider = self.store_provider if provider is None else provider
        provider_kwargs = (
            self.store_provider_kwargs
            if provider_kwargs is None
            else provider_kwargs
        )
        signing_key = self.store_private if signing_key is None else signing_key
        public_spki = self.store_spki if public_spki is None else public_spki
        previous_state_kwargs = {
            **self.previous_state_kwargs,
            "atomic_store_provider_kwargs": provider_kwargs,
        }
        claim_kwargs = {
            "expected_previous_atomic_head_state_hash": self.previous_state[
                "atomic_head_state_hash"
            ],
            "previous_atomic_head_state_build_kwargs": previous_state_kwargs,
            "operation_id_hash": _hash(label),
            "next_clock_evidence_hash": clock_bundle["evidence"][
                "clock_evidence_hash"
            ],
            "next_snapshot_state_hash": next_snapshot_state_hash
            or self.v7.v6.transition["next_state_hash"],
            "next_snapshot_claim_hash": next_snapshot_claim_hash
            or self.v7.v6.bundle["claim"]["snapshot_claim_hash"],
            "next_transition_hash": next_transition_hash
            or self.v7.v6.transition["transition_hash"],
        }
        claim = budget_v8.build_atomic_head_commit_claim_v1(
            self.previous_state,
            provider,
            **claim_kwargs,
        )
        signature = signing_key.sign(bytes.fromhex(claim["atomic_commit_claim_hash"]))
        public_key_spki_base64 = _b64(public_spki)
        signature_base64 = _b64(signature)
        signed = budget_v8.build_signed_atomic_head_commit_receipt_v1(
            claim,
            self.previous_state,
            provider,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_atomic_commit_claim_hash=claim["atomic_commit_claim_hash"],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "public_key_spki_base64": public_key_spki_base64,
            "signature_base64": signature_base64,
            "expected_atomic_commit_claim_hash": claim["atomic_commit_claim_hash"],
            "expected_signed_atomic_commit_receipt_hash": signed[
                "signed_atomic_commit_receipt_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = budget_v8.evaluate_signed_atomic_head_commit_receipt_v1(
            signed,
            claim,
            self.previous_state,
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

    def call_parts(self, atomic_bundle=None, clock_bundle=None):
        atomic_bundle = self.atomic_bundle if atomic_bundle is None else atomic_bundle
        clock_bundle = self.v7.clock_bundle if clock_bundle is None else clock_bundle
        args = (
            atomic_bundle["evidence"],
            atomic_bundle["signed"],
            atomic_bundle["claim"],
            self.previous_state,
            atomic_bundle["provider"],
            clock_bundle["evidence"],
            clock_bundle["signed"],
            clock_bundle["claim"],
            clock_bundle["provider"],
            self.v7.v6.transition,
            self.v7.v6.previous_state,
            self.v7.v6.policy,
            self.v7.v6.bundle["evidence"],
            self.v7.v6.bundle["signed"],
            self.v7.v6.bundle["claim"],
            self.v7.v6.base.provider,
            self.v7.v6.base.preregistration,
            self.v7.v6.base.matrix,
            self.v7.v6.base.audit,
        )
        kwargs = dict(self.v7.v6.base.increase_kwargs)
        kwargs.update(
            {
                "expected_atomic_commit_evidence_hash": atomic_bundle["evidence"][
                    "atomic_commit_evidence_hash"
                ],
                "atomic_commit_evaluation_kwargs": atomic_bundle[
                    "evaluation_kwargs"
                ],
                "expected_clock_evidence_hash": clock_bundle["evidence"][
                    "clock_evidence_hash"
                ],
                "clock_evaluation_kwargs": clock_bundle["evaluation_kwargs"],
                "expected_transition_hash": self.v7.v6.transition[
                    "transition_hash"
                ],
                "transition_evaluation_kwargs": self.v7.v6.transition_kwargs,
                "expected_snapshot_evidence_hash": self.v7.v6.bundle["evidence"][
                    "snapshot_evidence_hash"
                ],
                "snapshot_evaluation_kwargs": self.v7.v6.bundle[
                    "evaluation_kwargs"
                ],
            }
        )
        return args, kwargs

    def evaluate_v8(self, atomic_bundle=None, clock_bundle=None, **overrides):
        args, kwargs = self.call_parts(atomic_bundle, clock_bundle)
        kwargs.update(overrides)
        return budget_v8.evaluate_strategy_correlation_cluster_effective_bet_budget_v8(
            *args,
            **kwargs,
        )

    def test_reproduces_v7_unbounded_clock_counter_gap(self):
        normal = self.v7.evaluate_v7()
        high_clock = self.v7.build_clock_bundle(
            evaluated_at=self.v7.v6.observed_at + 500,
            counter=900,
            label="counter-gap",
        )
        high = self.v7.evaluate_v7(high_clock)
        self.assertEqual("PASS", normal["status"])
        self.assertEqual("PASS", high["status"])
        self.assertEqual(41, normal["clock_summary"]["clock_counter"])
        self.assertEqual(900, high["clock_summary"]["clock_counter"])
        self.assertEqual(
            normal["source"]["current_state_hash"],
            high["source"]["current_state_hash"],
        )
        self.assertFalse(high["facts"]["clock_counter_continuity_verified"])
        self.assertFalse(high["facts"]["atomic_current_head_persistence_verified"])

    def test_store_provider_is_exact_blocked_and_authority_locked(self):
        self.assertTrue(
            budget_v8.verify_atomic_head_store_provider_preregistration_v1(
                self.store_provider,
                **self.store_provider_kwargs,
            )
        )
        self.assertEqual("BLOCKED", self.store_provider["status"])
        self.assertFalse(
            self.store_provider["facts"]["atomic_compare_and_swap_verified"]
        )
        self.assert_authority_locked(self.store_provider["authority"])

    def test_previous_atomic_state_is_exact_candidate(self):
        self.assertTrue(
            budget_v8.verify_atomic_head_state_v1(
                self.previous_state,
                self.store_provider,
                expected_atomic_head_state_hash=self.previous_state[
                    "atomic_head_state_hash"
                ],
                **self.previous_state_kwargs,
            )
        )
        self.assertEqual(40, self.previous_state["state"]["clock_counter"])
        self.assertEqual(100, self.previous_state["state"]["commit_index"])
        self.assert_authority_locked(self.previous_state["authority"])

    def test_commit_claim_derives_exact_next_state_and_counter(self):
        claim = self.atomic_bundle["claim"]
        state = claim["next_state_candidate"]
        self.assertEqual(41, state["state"]["clock_counter"])
        self.assertEqual(101, state["state"]["commit_index"])
        self.assertEqual(18, state["state"]["state_revision"])
        self.assertEqual(
            self.v7.v6.transition["next_state_hash"],
            state["state"]["snapshot_state_hash"],
        )
        self.assertTrue(
            budget_v8.verify_atomic_head_commit_claim_v1(
                claim,
                self.previous_state,
                self.store_provider,
                expected_atomic_commit_claim_hash=claim[
                    "atomic_commit_claim_hash"
                ],
                **self.atomic_bundle["evaluation_kwargs"]["claim_build_kwargs"],
            )
        )

    def test_signed_commit_evidence_pass_is_not_atomic_persistence(self):
        evidence = self.atomic_bundle["evidence"]
        self.assertEqual("PASS", evidence["status"])
        self.assertTrue(
            evidence["facts"][
                "preregistered_atomic_store_key_signature_verified"
            ]
        )
        self.assertTrue(
            evidence["facts"]["clock_counter_increment_arithmetic_verified"]
        )
        self.assertFalse(evidence["facts"]["atomic_compare_and_swap_verified"])
        self.assertFalse(evidence["facts"]["durability_verified"])
        self.assert_authority_locked(evidence["authority"])

    def test_v8_derives_snapshot_head_and_counter_from_signed_receipt(self):
        result = self.evaluate_v8()
        signature = inspect.signature(
            budget_v8.evaluate_strategy_correlation_cluster_effective_bet_budget_v8
        )
        self.assertNotIn("expected_current_state_hash", signature.parameters)
        self.assertNotIn("clock_counter", signature.parameters)
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertEqual(41, result["atomic_state_summary"]["clock_counter"])
        self.assertTrue(result["facts"]["atomic_state_bound_to_budget_subject"])
        self.assertTrue(
            result["facts"]["clock_counter_bound_to_signed_clock_evidence"]
        )
        self.assertFalse(
            result["facts"]["caller_expected_snapshot_state_hash_input_accepted"]
        )
        self.assertFalse(result["facts"]["caller_clock_counter_input_accepted"])
        self.assertFalse(result["facts"]["atomic_compare_and_swap_verified"])
        self.assert_authority_locked(result["authority"])

    def test_counter_jump_signed_by_clock_is_blocked_by_atomic_state(self):
        high_clock = self.v7.build_clock_bundle(
            evaluated_at=self.v7.v6.observed_at + 500,
            counter=900,
            label="counter-jump",
        )
        self.assertEqual("PASS", self.v7.evaluate_v7(high_clock)["status"])
        atomic_bundle = self.build_atomic_bundle(
            high_clock,
            label="counter-jump-commit",
        )
        result = self.evaluate_v8(atomic_bundle, high_clock)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("CLOCK_COUNTER_CONTINUITY_BINDING_EXACT", result["blockers"])

    def test_atomic_snapshot_head_drift_blocks_v8(self):
        atomic_bundle = self.build_atomic_bundle(
            self.v7.clock_bundle,
            next_snapshot_state_hash=_hash("wrong-snapshot-state"),
            label="wrong-snapshot-head",
        )
        result = self.evaluate_v8(atomic_bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("ATOMIC_STATE_BUDGET_SUBJECT_BINDING_EXACT", result["blockers"])

    def test_atomic_transition_or_snapshot_claim_drift_blocks_v8(self):
        cases = {
            "transition": {"next_transition_hash": _hash("wrong-transition")},
            "snapshot": {"next_snapshot_claim_hash": _hash("wrong-snapshot")},
        }
        for label, overrides in cases.items():
            with self.subTest(label=label):
                atomic_bundle = self.build_atomic_bundle(
                    self.v7.clock_bundle,
                    label=f"wrong-{label}",
                    **overrides,
                )
                result = self.evaluate_v8(atomic_bundle)
                self.assertEqual("BLOCKED", result["status"])
                self.assertIn(
                    "ATOMIC_STATE_BUDGET_SUBJECT_BINDING_EXACT",
                    result["blockers"],
                )

    def test_atomic_store_account_scope_drift_blocks_v8(self):
        provider_kwargs = {
            **self.store_provider_kwargs,
            "account_scope_hash": _hash("wrong-store-account"),
        }
        provider = budget_v8.build_atomic_head_store_provider_preregistration_v1(
            **provider_kwargs
        )
        previous_kwargs = {
            **self.previous_state_kwargs,
            "atomic_store_provider_kwargs": provider_kwargs,
        }
        previous = budget_v8.build_atomic_head_state_v1(
            provider,
            **previous_kwargs,
        )
        original_previous = self.previous_state
        original_kwargs = self.previous_state_kwargs
        try:
            self.previous_state = previous
            self.previous_state_kwargs = previous_kwargs
            bundle = self.build_atomic_bundle(
                self.v7.clock_bundle,
                provider=provider,
                provider_kwargs=provider_kwargs,
                label="wrong-store-scope",
            )
            result = self.evaluate_v8(bundle)
        finally:
            self.previous_state = original_previous
            self.previous_state_kwargs = original_kwargs
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("ATOMIC_STORE_ACCOUNT_SCOPE_BINDING_EXACT", result["blockers"])

    def test_wrong_atomic_store_signing_key_is_blocked(self):
        wrong_key = Ed25519PrivateKey.generate()
        bundle = self.build_atomic_bundle(
            self.v7.clock_bundle,
            signing_key=wrong_key,
            label="wrong-store-signer",
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v8(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_ATOMIC_STORE_KEY_SIGNATURE_PASS", result["blockers"])

    def test_signed_stale_clock_preserves_v7_block(self):
        stale_clock = self.v7.build_clock_bundle(
            evaluated_at=self.v7.v6.observed_at + 5_000,
            counter=41,
            label="stale-clock-v8",
        )
        atomic_bundle = self.build_atomic_bundle(
            stale_clock,
            label="stale-clock-commit",
        )
        result = self.evaluate_v8(atomic_bundle, stale_clock)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("V7_EFFECTIVE_BUDGET_PASS", result["blockers"])

    def test_tampered_commit_claim_is_rejected(self):
        bundle = copy.deepcopy(self.atomic_bundle)
        bundle["claim"]["transition_summary"]["next_clock_counter"] = 900
        result = self.evaluate_v8(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_ATOMIC_COMMIT_EVIDENCE_EXACT", result["blockers"])

    def test_boolean_state_aliases_and_provider_drift_are_rejected(self):
        with self.assertRaises(ValueError):
            budget_v8.build_atomic_head_state_v1(
                self.store_provider,
                **{**self.previous_state_kwargs, "clock_counter": True},
            )
        provider = copy.deepcopy(self.store_provider)
        provider["status"] = "PASS"
        with self.assertRaises(ValueError):
            budget_v8.build_atomic_head_state_v1(
                provider,
                **self.previous_state_kwargs,
            )

    def test_exact_verifiers_reject_resealed_promotions(self):
        provider = copy.deepcopy(self.store_provider)
        provider.pop("atomic_store_provider_hash")
        provider["status"] = "PASS"
        provider = seal_strict_canonical_document(
            provider,
            "atomic_store_provider_hash",
        )
        self.assertFalse(
            budget_v8.verify_atomic_head_store_provider_preregistration_v1(
                provider,
                **self.store_provider_kwargs,
            )
        )

        state = copy.deepcopy(self.previous_state)
        original_state_hash = state.pop("atomic_head_state_hash")
        state["status"] = "PASS"
        state = seal_strict_canonical_document(state, "atomic_head_state_hash")
        self.assertFalse(
            budget_v8.verify_atomic_head_state_v1(
                state,
                self.store_provider,
                expected_atomic_head_state_hash=original_state_hash,
                **self.previous_state_kwargs,
            )
        )

        evidence = copy.deepcopy(self.atomic_bundle["evidence"])
        original_evidence_hash = evidence.pop("atomic_commit_evidence_hash")
        evidence["status"] = "BLOCKED"
        evidence = seal_strict_canonical_document(
            evidence,
            "atomic_commit_evidence_hash",
        )
        self.assertFalse(
            budget_v8.verify_signed_atomic_head_commit_evidence_v1(
                evidence,
                self.atomic_bundle["signed"],
                self.atomic_bundle["claim"],
                self.previous_state,
                self.store_provider,
                expected_atomic_commit_evidence_hash=original_evidence_hash,
                **self.atomic_bundle["evaluation_kwargs"],
            )
        )

    def test_v8_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v8()
        args, kwargs = self.call_parts()
        self.assertTrue(
            budget_v8.verify_strategy_correlation_cluster_effective_bet_budget_v8(
                result,
                *args,
                expected_budget_v8_hash=result["budget_v8_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        original_hash = tampered.pop("budget_v8_hash")
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v8_hash")
        self.assertFalse(
            budget_v8.verify_strategy_correlation_cluster_effective_bet_budget_v8(
                tampered,
                *args,
                expected_budget_v8_hash=original_hash,
                **kwargs,
            )
        )

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        before = copy.deepcopy(
            {
                "atomic": self.atomic_bundle,
                "state": self.previous_state,
                "clock": self.v7.clock_bundle,
                "transition": self.v7.v6.transition,
                "snapshot": self.v7.v6.bundle,
            }
        )
        first = self.evaluate_v8()
        second = self.evaluate_v8()
        self.assertEqual(first, second)
        self.assertEqual(before["atomic"], self.atomic_bundle)
        self.assertEqual(before["state"], self.previous_state)
        self.assertEqual(before["clock"], self.v7.clock_bundle)
        self.assertEqual(before["transition"], self.v7.v6.transition)
        self.assertEqual(before["snapshot"], self.v7.v6.bundle)

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

    def test_production_has_no_private_key_state_io_network_or_runtime_access(self):
        source = Path(budget_v8.__file__).read_text(encoding="utf-8")
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
