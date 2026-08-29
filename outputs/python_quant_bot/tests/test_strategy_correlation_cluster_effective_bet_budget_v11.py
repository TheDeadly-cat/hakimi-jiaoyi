from __future__ import annotations

import base64
import copy
import hashlib
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v11 as budget_v11,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v10 as v10_tests


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class StrategyCorrelationClusterEffectiveBetBudgetV11Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v10 = v10_tests.StrategyCorrelationClusterEffectiveBetBudgetV10Tests(
            methodName="test_v10_binds_quorum_to_v9_and_keeps_admission_blocked"
        )
        self.v10.setUp()
        self.sequence_rows = [
            {
                "witness_id": witness_id,
                "sequence": 7,
                "last_attestation_id_hash": _hash(f"previous-{witness_id}"),
            }
            for witness_id in ("witness-a", "witness-b", "witness-c")
        ]
        self.ownership_state_kwargs = {
            "witness_set_build_kwargs": self.v10.witness_set_kwargs,
            "ownership_epoch_hash": _hash("ownership-epoch-v1"),
            "state_revision": 3,
            "predecessor_ownership_state_hash": _hash("ownership-genesis"),
            "last_witness_quorum_evidence_hash": _hash("previous-quorum-evidence"),
            "witness_sequences": self.sequence_rows,
        }
        self.ownership_state = (
            budget_v11.build_witness_anti_replay_ownership_state_v1(
                self.v10.witness_set,
                **self.ownership_state_kwargs,
            )
        )
        self.ownership_bundle = self.build_ownership_bundle()

    def assert_authority_locked(self, authority) -> None:
        self.assertTrue(authority["descriptive_only"])
        self.assertFalse(
            any(
                value
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def build_ownership_bundle(
        self,
        *,
        quorum_bundle=None,
        previous_state=None,
        previous_state_kwargs=None,
        participating_ids=None,
        subject_overrides=None,
        signing_key_overrides=None,
        label="ownership-attestation-101",
    ):
        quorum_bundle = (
            self.v10.quorum_bundle if quorum_bundle is None else quorum_bundle
        )
        previous_state = (
            self.ownership_state if previous_state is None else previous_state
        )
        previous_state_kwargs = (
            self.ownership_state_kwargs
            if previous_state_kwargs is None
            else previous_state_kwargs
        )
        participants = (
            sorted(
                row["witness_id"]
                for row in quorum_bundle["evidence"]["witness_results"]
                if row["status"] == "PASS"
            )
            if participating_ids is None
            else list(participating_ids)
        )
        subject = {
            "witness_quorum_evidence_hash": quorum_bundle["evidence"][
                "witness_quorum_evidence_hash"
            ],
            "previous_checkpoint_hash": quorum_bundle["evidence"]["subject"][
                "previous_checkpoint_hash"
            ],
            "next_checkpoint_hash": quorum_bundle["evidence"]["subject"][
                "next_checkpoint_hash"
            ],
            "commit_index": quorum_bundle["evidence"]["subject"]["commit_index"],
        }
        subject.update(subject_overrides or {})
        claim_kwargs = {
            "expected_previous_ownership_state_hash": previous_state[
                "ownership_state_hash"
            ],
            "previous_ownership_state_build_kwargs": previous_state_kwargs,
            "attestation_id_hash": _hash(label),
            "participating_witness_ids": participants,
            **subject,
        }
        claim = budget_v11.build_witness_anti_replay_ownership_claim_v1(
            previous_state,
            self.v10.witness_set,
            **claim_kwargs,
        )
        signature_rows = []
        for witness_id in participants:
            signing_key = (signing_key_overrides or {}).get(
                witness_id,
                self.v10.witness_private[witness_id],
            )
            signature_rows.append(
                {
                    "witness_id": witness_id,
                    "public_key_spki_base64": _b64(
                        self.v10.witness_spki[witness_id]
                    ),
                    "signature_base64": _b64(
                        signing_key.sign(bytes.fromhex(claim["ownership_claim_hash"]))
                    ),
                }
            )
        signed = budget_v11.build_signed_witness_anti_replay_ownership_quorum_v1(
            claim,
            previous_state,
            self.v10.witness_set,
            signature_rows=signature_rows,
            expected_ownership_claim_hash=claim["ownership_claim_hash"],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "signature_rows": signature_rows,
            "expected_ownership_claim_hash": claim["ownership_claim_hash"],
            "expected_signed_ownership_quorum_hash": signed[
                "signed_ownership_quorum_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = (
            budget_v11.evaluate_signed_witness_anti_replay_ownership_quorum_v1(
                signed,
                claim,
                previous_state,
                self.v10.witness_set,
                **evaluation_kwargs,
            )
        )
        return {
            "previous_state": previous_state,
            "previous_state_kwargs": previous_state_kwargs,
            "claim": claim,
            "signed": signed,
            "evidence": evidence,
            "evaluation_kwargs": evaluation_kwargs,
        }

    def call_parts(
        self,
        ownership_bundle=None,
        quorum_bundle=None,
        previous_state=None,
    ):
        ownership_bundle = (
            self.ownership_bundle if ownership_bundle is None else ownership_bundle
        )
        quorum_bundle = (
            self.v10.quorum_bundle if quorum_bundle is None else quorum_bundle
        )
        previous_state = (
            ownership_bundle["previous_state"]
            if previous_state is None
            else previous_state
        )
        v10_args, v10_kwargs = self.v10.call_parts(quorum_bundle)
        args = (
            ownership_bundle["evidence"],
            ownership_bundle["signed"],
            ownership_bundle["claim"],
            previous_state,
            *v10_args,
        )
        kwargs = dict(v10_kwargs)
        kwargs.update(
            {
                "expected_ownership_evidence_hash": ownership_bundle["evidence"][
                    "ownership_evidence_hash"
                ],
                "ownership_evaluation_kwargs": ownership_bundle[
                    "evaluation_kwargs"
                ],
            }
        )
        return args, kwargs

    def evaluate_v11(
        self,
        ownership_bundle=None,
        quorum_bundle=None,
        previous_state=None,
        **overrides,
    ):
        args, kwargs = self.call_parts(
            ownership_bundle,
            quorum_bundle,
            previous_state,
        )
        kwargs.update(overrides)
        return budget_v11.evaluate_strategy_correlation_cluster_effective_bet_budget_v11(
            *args,
            **kwargs,
        )

    def test_reproduces_v10_old_quorum_replay_gap(self):
        old_before = self.v10.evaluate_v10()
        newer = self.v10.v9.build_newer_chain()
        newer_quorum = self.v10.build_quorum_bundle(
            read_bundle=newer["read"],
            atomic_bundle=newer["atomic"],
            clock_bundle=newer["clock"],
            label="newer-quorum-v11-gap",
        )
        old_after = self.v10.evaluate_v10()
        self.assertEqual("PASS", old_before["status"])
        self.assertEqual("PASS", newer["result"]["status"])
        self.assertEqual("PASS", newer_quorum["evidence"]["status"])
        self.assertEqual(102, newer_quorum["evidence"]["subject"]["commit_index"])
        self.assertEqual("PASS", old_after["status"])
        self.assertFalse(old_after["facts"]["global_latest_checkpoint_verified"])

    def test_ownership_state_is_exact_candidate(self):
        self.assertTrue(
            budget_v11.verify_witness_anti_replay_ownership_state_v1(
                self.ownership_state,
                self.v10.witness_set,
                expected_ownership_state_hash=self.ownership_state[
                    "ownership_state_hash"
                ],
                **self.ownership_state_kwargs,
            )
        )
        self.assertEqual("CANDIDATE", self.ownership_state["status"])
        self.assertFalse(
            self.ownership_state["facts"]["ownership_state_persistence_verified"]
        )
        self.assert_authority_locked(self.ownership_state["authority"])

    def test_ownership_claim_increments_only_participating_sequences(self):
        transitions = self.ownership_bundle["claim"]["sequence_transitions"]
        by_id = {row["witness_id"]: row for row in transitions}
        self.assertEqual(8, by_id["witness-a"]["next_sequence"])
        self.assertEqual(8, by_id["witness-b"]["next_sequence"])
        self.assertEqual(7, by_id["witness-c"]["next_sequence"])
        self.assertFalse(by_id["witness-c"]["participates"])
        next_state = self.ownership_bundle["claim"][
            "next_ownership_state_candidate"
        ]
        self.assertEqual(4, next_state["state"]["state_revision"])

    def test_ownership_evidence_pass_is_not_persistence_or_identity(self):
        evidence = self.ownership_bundle["evidence"]
        self.assertEqual("PASS", evidence["status"])
        self.assertTrue(
            evidence["facts"]["two_of_three_ownership_key_signatures_verified"]
        )
        self.assertFalse(
            evidence["facts"]["ownership_state_persistence_verified"]
        )
        self.assertFalse(evidence["facts"]["witness_identities_verified"])
        self.assert_authority_locked(evidence["authority"])

    def test_v11_binds_ownership_transition_to_v10(self):
        result = self.evaluate_v11()
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertTrue(result["facts"]["ownership_quorum_bound_to_v10"])
        self.assertFalse(
            result["facts"]["caller_quorum_without_ownership_transition_accepted"]
        )
        self.assertFalse(
            result["facts"]["witness_ownership_state_persistence_verified"]
        )
        self.assert_authority_locked(result["authority"])

    def test_advanced_ownership_state_rejects_old_attestation_replay(self):
        next_state = self.ownership_bundle["claim"][
            "next_ownership_state_candidate"
        ]
        result = self.evaluate_v11(previous_state=next_state)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("SIGNED_WITNESS_OWNERSHIP_EVIDENCE_EXACT", result["blockers"])

    def test_fewer_than_two_participants_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build_ownership_bundle(participating_ids=["witness-a"])

    def test_signature_rows_must_match_participants(self):
        claim = self.ownership_bundle["claim"]
        rows = copy.deepcopy(
            self.ownership_bundle["evaluation_kwargs"]["signature_rows"]
        )
        rows[1]["witness_id"] = "witness-c"
        with self.assertRaises(ValueError):
            budget_v11.build_signed_witness_anti_replay_ownership_quorum_v1(
                claim,
                self.ownership_state,
                self.v10.witness_set,
                signature_rows=rows,
                expected_ownership_claim_hash=claim["ownership_claim_hash"],
                claim_build_kwargs=self.ownership_bundle["evaluation_kwargs"][
                    "claim_build_kwargs"
                ],
            )

    def test_wrong_ownership_signing_key_blocks_v11(self):
        bundle = self.build_ownership_bundle(
            signing_key_overrides={"witness-b": Ed25519PrivateKey.generate()},
            label="wrong-ownership-key",
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v11(bundle)
        self.assertEqual("BLOCKED", result["status"])

    def test_ownership_subject_drift_blocks_v11(self):
        cases = {
            "quorum": {"witness_quorum_evidence_hash": _hash("wrong-quorum")},
            "checkpoint": {"next_checkpoint_hash": _hash("wrong-checkpoint")},
            "commit": {"commit_index": 999},
        }
        for label, override in cases.items():
            with self.subTest(label=label):
                bundle = self.build_ownership_bundle(
                    subject_overrides=override,
                    label=f"ownership-drift-{label}",
                )
                self.assertEqual("PASS", bundle["evidence"]["status"])
                result = self.evaluate_v11(bundle)
                self.assertEqual("BLOCKED", result["status"])
                self.assertIn(
                    "OWNERSHIP_TRANSITION_V10_SUBJECT_BINDING_EXACT",
                    result["blockers"],
                )

    def test_v10_below_quorum_block_is_preserved(self):
        one_signer = self.v10.build_quorum_bundle(
            signer_ids=("witness-a",),
            label="v11-one-signer-v10",
        )
        ownership = self.build_ownership_bundle(
            quorum_bundle=one_signer,
            participating_ids=["witness-a", "witness-b"],
            label="ownership-over-blocked-v10",
        )
        result = self.evaluate_v11(ownership, one_signer)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("V10_EFFECTIVE_BUDGET_PASS", result["blockers"])

    def test_duplicate_or_boolean_sequence_rows_are_rejected(self):
        duplicate = copy.deepcopy(self.sequence_rows)
        duplicate[1]["witness_id"] = duplicate[0]["witness_id"]
        with self.assertRaises(ValueError):
            budget_v11.build_witness_anti_replay_ownership_state_v1(
                self.v10.witness_set,
                **{**self.ownership_state_kwargs, "witness_sequences": duplicate},
            )
        boolean = copy.deepcopy(self.sequence_rows)
        boolean[0]["sequence"] = True
        with self.assertRaises(ValueError):
            budget_v11.build_witness_anti_replay_ownership_state_v1(
                self.v10.witness_set,
                **{**self.ownership_state_kwargs, "witness_sequences": boolean},
            )

    def test_exact_verifiers_reject_resealed_promotions(self):
        state = copy.deepcopy(self.ownership_state)
        original_state_hash = state.pop("ownership_state_hash")
        state["status"] = "PASS"
        state = seal_strict_canonical_document(state, "ownership_state_hash")
        self.assertFalse(
            budget_v11.verify_witness_anti_replay_ownership_state_v1(
                state,
                self.v10.witness_set,
                expected_ownership_state_hash=original_state_hash,
                **self.ownership_state_kwargs,
            )
        )
        evidence = copy.deepcopy(self.ownership_bundle["evidence"])
        original_evidence_hash = evidence.pop("ownership_evidence_hash")
        evidence["status"] = "BLOCKED"
        evidence = seal_strict_canonical_document(
            evidence,
            "ownership_evidence_hash",
        )
        self.assertFalse(
            budget_v11.verify_signed_witness_anti_replay_ownership_evidence_v1(
                evidence,
                self.ownership_bundle["signed"],
                self.ownership_bundle["claim"],
                self.ownership_state,
                self.v10.witness_set,
                expected_ownership_evidence_hash=original_evidence_hash,
                **self.ownership_bundle["evaluation_kwargs"],
            )
        )

    def test_v11_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v11()
        args, kwargs = self.call_parts()
        self.assertTrue(
            budget_v11.verify_strategy_correlation_cluster_effective_bet_budget_v11(
                result,
                *args,
                expected_budget_v11_hash=result["budget_v11_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        original_hash = tampered.pop("budget_v11_hash")
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v11_hash")
        self.assertFalse(
            budget_v11.verify_strategy_correlation_cluster_effective_bet_budget_v11(
                tampered,
                *args,
                expected_budget_v11_hash=original_hash,
                **kwargs,
            )
        )

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        before = copy.deepcopy(
            {
                "ownership": self.ownership_bundle,
                "state": self.ownership_state,
                "quorum": self.v10.quorum_bundle,
            }
        )
        first = self.evaluate_v11()
        second = self.evaluate_v11()
        self.assertEqual(first, second)
        self.assertEqual(before["ownership"], self.ownership_bundle)
        self.assertEqual(before["state"], self.ownership_state)
        self.assertEqual(before["quorum"], self.v10.quorum_bundle)

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
        source = Path(budget_v11.__file__).read_text(encoding="utf-8")
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
