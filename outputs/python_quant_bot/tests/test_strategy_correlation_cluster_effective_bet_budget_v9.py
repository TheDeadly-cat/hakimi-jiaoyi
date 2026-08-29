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
    strategy_correlation_cluster_effective_bet_budget_v9 as budget_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v8 as v8_tests


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class StrategyCorrelationClusterEffectiveBetBudgetV9Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v8 = v8_tests.StrategyCorrelationClusterEffectiveBetBudgetV8Tests(
            methodName="test_v8_derives_snapshot_head_and_counter_from_signed_receipt"
        )
        self.v8.setUp()
        self.checkpoint_kwargs = {
            "atomic_store_provider_kwargs": self.v8.store_provider_kwargs,
            "checkpoint_revision": 5,
            "predecessor_checkpoint_hash": _hash("checkpoint-genesis"),
            "minimum_commit_index": 100,
            "minimum_clock_counter": 40,
            "minimum_state_revision": 17,
            "accepted_atomic_head_state_hash": self.v8.previous_state[
                "atomic_head_state_hash"
            ],
            "accepted_atomic_commit_evidence_hash": _hash(
                "previous-atomic-commit-evidence"
            ),
        }
        self.checkpoint = budget_v9.build_authenticated_latest_head_checkpoint_v1(
            self.v8.store_provider,
            **self.checkpoint_kwargs,
        )
        self.read_bundle = self.build_read_bundle(
            self.v8.atomic_bundle,
            self.v8.v7.clock_bundle,
            self.checkpoint,
            self.checkpoint_kwargs,
            label="latest-read-101",
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

    def build_read_bundle(
        self,
        atomic_bundle,
        clock_bundle,
        checkpoint,
        checkpoint_kwargs,
        *,
        label,
        observation_overrides=None,
        signing_key=None,
    ):
        signing_key = self.v8.store_private if signing_key is None else signing_key
        atomic_state = atomic_bundle["claim"]["next_state_candidate"]
        state = atomic_state["state"]
        observation = {
            "observed_atomic_commit_evidence_hash": atomic_bundle["evidence"][
                "atomic_commit_evidence_hash"
            ],
            "observed_atomic_head_state_hash": atomic_state[
                "atomic_head_state_hash"
            ],
            "observed_commit_index": state["commit_index"],
            "observed_clock_counter": state["clock_counter"],
            "observed_state_revision": state["state_revision"],
        }
        observation.update(observation_overrides or {})
        claim_kwargs = {
            "expected_latest_head_checkpoint_hash": checkpoint[
                "latest_head_checkpoint_hash"
            ],
            "latest_head_checkpoint_build_kwargs": checkpoint_kwargs,
            "query_id_hash": _hash(label),
            "query_clock_evidence_hash": clock_bundle["evidence"][
                "clock_evidence_hash"
            ],
            "query_evaluated_at_unix_ms": clock_bundle["claim"][
                "clock_reading"
            ]["evaluated_at_unix_ms"],
            **observation,
        }
        claim = budget_v9.build_authenticated_latest_head_read_claim_v1(
            checkpoint,
            self.v8.store_provider,
            **claim_kwargs,
        )
        signature = signing_key.sign(bytes.fromhex(claim["latest_head_read_claim_hash"]))
        public_key_spki_base64 = _b64(self.v8.store_spki)
        signature_base64 = _b64(signature)
        signed = budget_v9.build_signed_authenticated_latest_head_read_v1(
            claim,
            checkpoint,
            self.v8.store_provider,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_latest_head_read_claim_hash=claim[
                "latest_head_read_claim_hash"
            ],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "public_key_spki_base64": public_key_spki_base64,
            "signature_base64": signature_base64,
            "expected_latest_head_read_claim_hash": claim[
                "latest_head_read_claim_hash"
            ],
            "expected_signed_latest_head_read_hash": signed[
                "signed_latest_head_read_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = budget_v9.evaluate_signed_authenticated_latest_head_read_v1(
            signed,
            claim,
            checkpoint,
            self.v8.store_provider,
            **evaluation_kwargs,
        )
        return {
            "checkpoint": checkpoint,
            "checkpoint_kwargs": checkpoint_kwargs,
            "claim": claim,
            "signed": signed,
            "evidence": evidence,
            "evaluation_kwargs": evaluation_kwargs,
        }

    def call_parts(
        self,
        read_bundle=None,
        atomic_bundle=None,
        clock_bundle=None,
        checkpoint=None,
    ):
        read_bundle = self.read_bundle if read_bundle is None else read_bundle
        atomic_bundle = self.v8.atomic_bundle if atomic_bundle is None else atomic_bundle
        clock_bundle = self.v8.v7.clock_bundle if clock_bundle is None else clock_bundle
        checkpoint = self.checkpoint if checkpoint is None else checkpoint
        v8_args, v8_kwargs = self.v8.call_parts(atomic_bundle, clock_bundle)
        args = (
            read_bundle["evidence"],
            read_bundle["signed"],
            read_bundle["claim"],
            checkpoint,
            *v8_args,
        )
        kwargs = dict(v8_kwargs)
        kwargs.update(
            {
                "expected_latest_head_read_evidence_hash": read_bundle["evidence"][
                    "latest_head_read_evidence_hash"
                ],
                "latest_head_read_evaluation_kwargs": read_bundle[
                    "evaluation_kwargs"
                ],
            }
        )
        return args, kwargs

    def evaluate_v9(
        self,
        read_bundle=None,
        atomic_bundle=None,
        clock_bundle=None,
        checkpoint=None,
        **overrides,
    ):
        args, kwargs = self.call_parts(
            read_bundle,
            atomic_bundle,
            clock_bundle,
            checkpoint,
        )
        kwargs.update(overrides)
        return budget_v9.evaluate_strategy_correlation_cluster_effective_bet_budget_v9(
            *args,
            **kwargs,
        )

    def build_newer_chain(self):
        old_previous = self.v8.previous_state
        old_kwargs = self.v8.previous_state_kwargs
        new_clock = self.v8.v7.build_clock_bundle(
            evaluated_at=self.v8.v7.v6.observed_at + 501,
            counter=42,
            label="latest-read-clock-102",
        )
        current_state = self.v8.atomic_bundle["claim"]["next_state_candidate"]
        current_kwargs = {
            "atomic_store_provider_kwargs": self.v8.store_provider_kwargs,
            "policy_hash": self.v8.v7.v6.policy["policy_hash"],
            "state_revision": 18,
            "commit_index": 101,
            "clock_counter": 41,
            "clock_evidence_hash": self.v8.v7.clock_bundle["evidence"][
                "clock_evidence_hash"
            ],
            "snapshot_state_hash": self.v8.v7.v6.transition["next_state_hash"],
            "snapshot_claim_hash": self.v8.v7.v6.bundle["claim"][
                "snapshot_claim_hash"
            ],
            "transition_hash": self.v8.v7.v6.transition["transition_hash"],
        }
        checkpoint_101 = self.read_bundle["claim"]["next_checkpoint_candidate"]
        checkpoint_101_kwargs = {
            "atomic_store_provider_kwargs": self.v8.store_provider_kwargs,
            "checkpoint_revision": 6,
            "predecessor_checkpoint_hash": self.checkpoint[
                "latest_head_checkpoint_hash"
            ],
            "minimum_commit_index": 101,
            "minimum_clock_counter": 41,
            "minimum_state_revision": 18,
            "accepted_atomic_head_state_hash": self.v8.atomic_bundle["claim"][
                "next_state_candidate"
            ]["atomic_head_state_hash"],
            "accepted_atomic_commit_evidence_hash": self.v8.atomic_bundle[
                "evidence"
            ]["atomic_commit_evidence_hash"],
        }
        self.v8.previous_state = current_state
        self.v8.previous_state_kwargs = current_kwargs
        try:
            new_atomic = self.v8.build_atomic_bundle(
                new_clock,
                label="latest-receipt-102",
            )
            new_read = self.build_read_bundle(
                new_atomic,
                new_clock,
                checkpoint_101,
                checkpoint_101_kwargs,
                label="latest-read-102",
            )
            new_result = self.evaluate_v9(
                new_read,
                new_atomic,
                new_clock,
                checkpoint_101,
            )
        finally:
            self.v8.previous_state = old_previous
            self.v8.previous_state_kwargs = old_kwargs
        return {
            "clock": new_clock,
            "atomic": new_atomic,
            "read": new_read,
            "result": new_result,
            "checkpoint_101": checkpoint_101,
            "checkpoint_101_kwargs": checkpoint_101_kwargs,
        }

    def test_reproduces_v8_old_receipt_selection_gap(self):
        old_before = self.v8.evaluate_v8()
        newer = self.build_newer_chain()
        old_after = self.v8.evaluate_v8()
        self.assertEqual("PASS", old_before["status"])
        self.assertEqual("PASS", newer["result"]["status"])
        self.assertEqual(101, old_after["atomic_state_summary"]["commit_index"])
        self.assertEqual(
            102,
            newer["result"]["latest_head_summary"]["commit_index"],
        )
        self.assertEqual("PASS", old_after["status"])
        self.assertFalse(old_after["facts"]["atomic_current_head_persistence_verified"])

    def test_checkpoint_is_exact_candidate_and_authority_locked(self):
        self.assertTrue(
            budget_v9.verify_authenticated_latest_head_checkpoint_v1(
                self.checkpoint,
                self.v8.store_provider,
                expected_latest_head_checkpoint_hash=self.checkpoint[
                    "latest_head_checkpoint_hash"
                ],
                **self.checkpoint_kwargs,
            )
        )
        self.assertEqual("CANDIDATE", self.checkpoint["status"])
        self.assertEqual(100, self.checkpoint["checkpoint"]["minimum_commit_index"])
        self.assert_authority_locked(self.checkpoint["authority"])

    def test_read_claim_advances_monotonic_checkpoint(self):
        claim = self.read_bundle["claim"]
        next_checkpoint = claim["next_checkpoint_candidate"]
        self.assertEqual(1, claim["observation"]["commit_delta_from_floor"])
        self.assertEqual(101, next_checkpoint["checkpoint"]["minimum_commit_index"])
        self.assertEqual(41, next_checkpoint["checkpoint"]["minimum_clock_counter"])
        self.assertEqual(18, next_checkpoint["checkpoint"]["minimum_state_revision"])
        self.assertTrue(claim["facts"]["same_index_equivocation_rejected"])

    def test_signed_read_evidence_pass_is_not_latest_head_truth(self):
        evidence = self.read_bundle["evidence"]
        self.assertEqual("PASS", evidence["status"])
        self.assertTrue(
            evidence["facts"]["preregistered_store_key_signature_verified"]
        )
        self.assertTrue(evidence["facts"]["rollback_floor_arithmetic_verified"])
        self.assertFalse(evidence["facts"]["latest_head_source_truth_verified"])
        self.assert_authority_locked(evidence["authority"])

    def test_v9_binds_signed_read_to_v8_and_keeps_admission_blocked(self):
        result = self.evaluate_v9()
        signature = inspect.signature(
            budget_v9.evaluate_strategy_correlation_cluster_effective_bet_budget_v9
        )
        self.assertNotIn("observed_commit_index", signature.parameters)
        self.assertNotIn("expected_atomic_head_state_hash", signature.parameters)
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertEqual(101, result["latest_head_summary"]["commit_index"])
        self.assertTrue(
            result["facts"]["latest_head_observation_bound_to_budget"]
        )
        self.assertFalse(result["facts"]["latest_atomic_head_verified"])
        self.assertFalse(
            result["facts"]["caller_receipt_without_read_evidence_accepted"]
        )
        self.assert_authority_locked(result["authority"])

    def test_new_checkpoint_rejects_old_signed_read_replay(self):
        newer = self.build_newer_chain()
        checkpoint_102 = newer["read"]["claim"]["next_checkpoint_candidate"]
        result = self.evaluate_v9(checkpoint=checkpoint_102)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_LATEST_HEAD_READ_EVIDENCE_EXACT", result["blockers"])

    def test_read_claim_rejects_commit_below_floor(self):
        newer = self.build_newer_chain()
        checkpoint_102 = newer["read"]["claim"]["next_checkpoint_candidate"]
        checkpoint_102_kwargs = {
            "atomic_store_provider_kwargs": self.v8.store_provider_kwargs,
            "checkpoint_revision": 7,
            "predecessor_checkpoint_hash": newer["checkpoint_101"][
                "latest_head_checkpoint_hash"
            ],
            "minimum_commit_index": 102,
            "minimum_clock_counter": 42,
            "minimum_state_revision": 19,
            "accepted_atomic_head_state_hash": newer["atomic"]["claim"][
                "next_state_candidate"
            ]["atomic_head_state_hash"],
            "accepted_atomic_commit_evidence_hash": newer["atomic"]["evidence"][
                "atomic_commit_evidence_hash"
            ],
        }
        with self.assertRaises(ValueError):
            self.build_read_bundle(
                self.v8.atomic_bundle,
                self.v8.v7.clock_bundle,
                checkpoint_102,
                checkpoint_102_kwargs,
                label="rollback-101",
            )

    def test_same_index_equivocation_is_rejected(self):
        next_checkpoint = self.read_bundle["claim"]["next_checkpoint_candidate"]
        next_kwargs = {
            "atomic_store_provider_kwargs": self.v8.store_provider_kwargs,
            "checkpoint_revision": 6,
            "predecessor_checkpoint_hash": self.checkpoint[
                "latest_head_checkpoint_hash"
            ],
            "minimum_commit_index": 101,
            "minimum_clock_counter": 41,
            "minimum_state_revision": 18,
            "accepted_atomic_head_state_hash": self.v8.atomic_bundle["claim"][
                "next_state_candidate"
            ]["atomic_head_state_hash"],
            "accepted_atomic_commit_evidence_hash": self.v8.atomic_bundle[
                "evidence"
            ]["atomic_commit_evidence_hash"],
        }
        with self.assertRaises(ValueError):
            self.build_read_bundle(
                self.v8.atomic_bundle,
                self.v8.v7.clock_bundle,
                next_checkpoint,
                next_kwargs,
                label="same-index-equivocation",
                observation_overrides={
                    "observed_atomic_head_state_hash": _hash("equivocated-state")
                },
            )

    def test_counter_or_revision_delta_mismatch_is_rejected(self):
        for field, value in (
            ("observed_clock_counter", 99),
            ("observed_state_revision", 99),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.build_read_bundle(
                        self.v8.atomic_bundle,
                        self.v8.v7.clock_bundle,
                        self.checkpoint,
                        self.checkpoint_kwargs,
                        label=f"wrong-{field}",
                        observation_overrides={field: value},
                    )

    def test_read_observation_drift_blocks_v9(self):
        bundle = copy.deepcopy(self.read_bundle)
        bundle["claim"]["observation"]["atomic_head_state_hash"] = _hash(
            "wrong-observed-state"
        )
        result = self.evaluate_v9(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_LATEST_HEAD_READ_EVIDENCE_EXACT", result["blockers"])

    def test_wrong_read_signing_key_is_blocked(self):
        wrong_key = Ed25519PrivateKey.generate()
        bundle = self.build_read_bundle(
            self.v8.atomic_bundle,
            self.v8.v7.clock_bundle,
            self.checkpoint,
            self.checkpoint_kwargs,
            label="wrong-read-key",
            signing_key=wrong_key,
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v9(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_LATEST_HEAD_READ_KEY_SIGNATURE_PASS", result["blockers"])

    def test_signed_stale_clock_preserves_v8_block(self):
        stale_clock = self.v8.v7.build_clock_bundle(
            evaluated_at=self.v8.v7.v6.observed_at + 5_000,
            counter=41,
            label="stale-read-clock",
        )
        stale_atomic = self.v8.build_atomic_bundle(
            stale_clock,
            label="stale-read-atomic",
        )
        stale_read = self.build_read_bundle(
            stale_atomic,
            stale_clock,
            self.checkpoint,
            self.checkpoint_kwargs,
            label="stale-latest-read",
        )
        result = self.evaluate_v9(stale_read, stale_atomic, stale_clock)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("V8_EFFECTIVE_BUDGET_PASS", result["blockers"])

    def test_boolean_checkpoint_alias_and_provider_drift_are_rejected(self):
        with self.assertRaises(ValueError):
            budget_v9.build_authenticated_latest_head_checkpoint_v1(
                self.v8.store_provider,
                **{**self.checkpoint_kwargs, "minimum_commit_index": True},
            )
        provider = copy.deepcopy(self.v8.store_provider)
        provider["status"] = "PASS"
        with self.assertRaises(ValueError):
            budget_v9.build_authenticated_latest_head_checkpoint_v1(
                provider,
                **self.checkpoint_kwargs,
            )

    def test_exact_verifiers_reject_resealed_promotions(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        original_checkpoint_hash = checkpoint.pop("latest_head_checkpoint_hash")
        checkpoint["status"] = "PASS"
        checkpoint = seal_strict_canonical_document(
            checkpoint,
            "latest_head_checkpoint_hash",
        )
        self.assertFalse(
            budget_v9.verify_authenticated_latest_head_checkpoint_v1(
                checkpoint,
                self.v8.store_provider,
                expected_latest_head_checkpoint_hash=original_checkpoint_hash,
                **self.checkpoint_kwargs,
            )
        )

        evidence = copy.deepcopy(self.read_bundle["evidence"])
        original_evidence_hash = evidence.pop("latest_head_read_evidence_hash")
        evidence["status"] = "BLOCKED"
        evidence = seal_strict_canonical_document(
            evidence,
            "latest_head_read_evidence_hash",
        )
        self.assertFalse(
            budget_v9.verify_signed_authenticated_latest_head_read_evidence_v1(
                evidence,
                self.read_bundle["signed"],
                self.read_bundle["claim"],
                self.checkpoint,
                self.v8.store_provider,
                expected_latest_head_read_evidence_hash=original_evidence_hash,
                **self.read_bundle["evaluation_kwargs"],
            )
        )

    def test_v9_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v9()
        args, kwargs = self.call_parts()
        self.assertTrue(
            budget_v9.verify_strategy_correlation_cluster_effective_bet_budget_v9(
                result,
                *args,
                expected_budget_v9_hash=result["budget_v9_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        original_hash = tampered.pop("budget_v9_hash")
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v9_hash")
        self.assertFalse(
            budget_v9.verify_strategy_correlation_cluster_effective_bet_budget_v9(
                tampered,
                *args,
                expected_budget_v9_hash=original_hash,
                **kwargs,
            )
        )

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        before = copy.deepcopy(
            {
                "read": self.read_bundle,
                "checkpoint": self.checkpoint,
                "atomic": self.v8.atomic_bundle,
                "clock": self.v8.v7.clock_bundle,
            }
        )
        first = self.evaluate_v9()
        second = self.evaluate_v9()
        self.assertEqual(first, second)
        self.assertEqual(before["read"], self.read_bundle)
        self.assertEqual(before["checkpoint"], self.checkpoint)
        self.assertEqual(before["atomic"], self.v8.atomic_bundle)
        self.assertEqual(before["clock"], self.v8.v7.clock_bundle)

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

    def test_production_has_no_private_key_read_io_network_or_runtime_access(self):
        source = Path(budget_v9.__file__).read_text(encoding="utf-8")
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
