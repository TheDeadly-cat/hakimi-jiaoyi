from __future__ import annotations

import base64
import copy
import hashlib
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v10 as budget_v10,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import test_strategy_correlation_cluster_effective_bet_budget_v9 as v9_tests


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _spki(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class StrategyCorrelationClusterEffectiveBetBudgetV10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v9 = v9_tests.StrategyCorrelationClusterEffectiveBetBudgetV9Tests(
            methodName="test_v9_binds_signed_read_to_v8_and_keeps_admission_blocked"
        )
        self.v9.setUp()
        self.witness_private = {
            witness_id: Ed25519PrivateKey.generate()
            for witness_id in ("witness-a", "witness-b", "witness-c")
        }
        self.witness_spki = {
            witness_id: _spki(private_key)
            for witness_id, private_key in self.witness_private.items()
        }
        self.witnesses = [
            {
                "witness_id": witness_id,
                "key_id": f"{witness_id}.key.v1",
                "public_key_spki_sha256": hashlib.sha256(
                    self.witness_spki[witness_id]
                ).hexdigest(),
                "trust_domain": f"trust-{suffix}",
                "failure_domain": f"failure-{suffix}",
                "implementation_claim_sha256": _hash(
                    f"implementation-{witness_id}"
                ),
            }
            for witness_id, suffix in (
                ("witness-a", "a"),
                ("witness-b", "b"),
                ("witness-c", "c"),
            )
        ]
        self.witness_set_kwargs = {
            "atomic_store_provider_hash": self.v9.v8.store_provider[
                "atomic_store_provider_hash"
            ],
            "account_scope_hash": self.v9.v8.store_provider["identity"][
                "account_scope_hash"
            ],
            "store_epoch_hash": self.v9.v8.store_provider["identity"][
                "store_epoch_hash"
            ],
            "minimum_witness_quorum": 2,
            "witnesses": self.witnesses,
        }
        self.witness_set = (
            budget_v10.build_checkpoint_witness_set_preregistration_v1(
                **self.witness_set_kwargs
            )
        )
        self.quorum_bundle = self.build_quorum_bundle()

    def assert_authority_locked(self, authority) -> None:
        self.assertTrue(authority["descriptive_only"])
        self.assertFalse(
            any(
                value
                for key, value in authority.items()
                if key != "descriptive_only"
            )
        )

    def build_quorum_bundle(
        self,
        *,
        signer_ids=("witness-a", "witness-b"),
        subject_overrides=None,
        witness_set=None,
        witness_set_kwargs=None,
        signing_key_overrides=None,
        read_bundle=None,
        atomic_bundle=None,
        clock_bundle=None,
        label="checkpoint-witness-quorum",
    ):
        witness_set = self.witness_set if witness_set is None else witness_set
        witness_set_kwargs = (
            self.witness_set_kwargs
            if witness_set_kwargs is None
            else witness_set_kwargs
        )
        read_bundle = self.v9.read_bundle if read_bundle is None else read_bundle
        atomic_bundle = (
            self.v9.v8.atomic_bundle if atomic_bundle is None else atomic_bundle
        )
        clock_bundle = (
            self.v9.v8.v7.clock_bundle if clock_bundle is None else clock_bundle
        )
        observation = read_bundle["evidence"]["observation"]
        subject = {
            "previous_checkpoint_hash": read_bundle["evidence"]["source"][
                "previous_checkpoint_hash"
            ],
            "latest_head_read_evidence_hash": read_bundle["evidence"][
                "latest_head_read_evidence_hash"
            ],
            "next_checkpoint_hash": read_bundle["evidence"]["source"][
                "next_checkpoint_hash"
            ],
            "atomic_store_provider_hash": self.v9.v8.store_provider[
                "atomic_store_provider_hash"
            ],
            "atomic_commit_evidence_hash": observation[
                "atomic_commit_evidence_hash"
            ],
            "atomic_head_state_hash": observation["atomic_head_state_hash"],
            "clock_evidence_hash": read_bundle["evidence"]["query"][
                "clock_evidence_hash"
            ],
            "account_scope_hash": self.v9.v8.store_provider["identity"][
                "account_scope_hash"
            ],
            "commit_index": observation["commit_index"],
            "clock_counter": observation["clock_counter"],
            "state_revision": observation["state_revision"],
        }
        subject.update(subject_overrides or {})
        claim_kwargs = {
            "witness_set_build_kwargs": witness_set_kwargs,
            "attestation_id_hash": _hash(label),
            "witness_round": subject["commit_index"],
            "evaluated_at_unix_ms": clock_bundle["claim"]["clock_reading"][
                "evaluated_at_unix_ms"
            ],
            **subject,
        }
        claim = budget_v10.build_checkpoint_witness_quorum_claim_v1(
            witness_set,
            **claim_kwargs,
        )
        signature_rows = []
        for witness_id in sorted(signer_ids):
            signing_key = (signing_key_overrides or {}).get(
                witness_id,
                self.witness_private[witness_id],
            )
            signature_rows.append(
                {
                    "witness_id": witness_id,
                    "public_key_spki_base64": _b64(self.witness_spki[witness_id]),
                    "signature_base64": _b64(
                        signing_key.sign(
                            bytes.fromhex(claim["witness_quorum_claim_hash"])
                        )
                    ),
                }
            )
        signed = budget_v10.build_signed_checkpoint_witness_quorum_v1(
            claim,
            witness_set,
            signature_rows=signature_rows,
            expected_witness_quorum_claim_hash=claim[
                "witness_quorum_claim_hash"
            ],
            claim_build_kwargs=claim_kwargs,
        )
        evaluation_kwargs = {
            "signature_rows": signature_rows,
            "expected_witness_quorum_claim_hash": claim[
                "witness_quorum_claim_hash"
            ],
            "expected_signed_witness_quorum_hash": signed[
                "signed_witness_quorum_hash"
            ],
            "claim_build_kwargs": claim_kwargs,
        }
        evidence = budget_v10.evaluate_signed_checkpoint_witness_quorum_v1(
            signed,
            claim,
            witness_set,
            **evaluation_kwargs,
        )
        return {
            "witness_set": witness_set,
            "witness_set_kwargs": witness_set_kwargs,
            "claim": claim,
            "signed": signed,
            "evidence": evidence,
            "evaluation_kwargs": evaluation_kwargs,
        }

    def call_parts(
        self,
        quorum_bundle=None,
        read_bundle=None,
        atomic_bundle=None,
        clock_bundle=None,
        checkpoint=None,
    ):
        quorum_bundle = self.quorum_bundle if quorum_bundle is None else quorum_bundle
        v9_args, v9_kwargs = self.v9.call_parts(
            read_bundle,
            atomic_bundle,
            clock_bundle,
            checkpoint,
        )
        args = (
            quorum_bundle["evidence"],
            quorum_bundle["signed"],
            quorum_bundle["claim"],
            quorum_bundle["witness_set"],
            *v9_args,
        )
        kwargs = dict(v9_kwargs)
        kwargs.update(
            {
                "expected_witness_quorum_evidence_hash": quorum_bundle[
                    "evidence"
                ]["witness_quorum_evidence_hash"],
                "witness_quorum_evaluation_kwargs": quorum_bundle[
                    "evaluation_kwargs"
                ],
            }
        )
        return args, kwargs

    def evaluate_v10(self, quorum_bundle=None, **overrides):
        args, kwargs = self.call_parts(quorum_bundle)
        kwargs.update(overrides)
        return budget_v10.evaluate_strategy_correlation_cluster_effective_bet_budget_v10(
            *args,
            **kwargs,
        )

    def test_reproduces_v9_caller_selected_old_checkpoint_gap(self):
        old_before = self.v9.evaluate_v9()
        newer = self.v9.build_newer_chain()
        checkpoint_102 = newer["read"]["claim"]["next_checkpoint_candidate"]
        old_after = self.v9.evaluate_v9()
        self.assertEqual("PASS", old_before["status"])
        self.assertEqual("PASS", newer["result"]["status"])
        self.assertEqual(102, checkpoint_102["checkpoint"]["minimum_commit_index"])
        self.assertEqual("PASS", old_after["status"])
        self.assertEqual(101, old_after["latest_head_summary"]["commit_index"])
        self.assertFalse(old_after["facts"]["latest_head_source_truth_verified"])

    def test_witness_set_is_exact_three_domain_registration(self):
        self.assertTrue(
            budget_v10.verify_checkpoint_witness_set_preregistration_v1(
                self.witness_set,
                **self.witness_set_kwargs,
            )
        )
        self.assertEqual(3, self.witness_set["quorum_policy"]["witness_count"])
        self.assertEqual(
            2,
            self.witness_set["quorum_policy"]["minimum_witness_quorum"],
        )
        self.assertFalse(
            self.witness_set["facts"][
                "witness_failure_domain_independence_verified"
            ]
        )
        self.assert_authority_locked(self.witness_set["authority"])

    def test_duplicate_trust_or_failure_domain_is_rejected(self):
        for field in ("trust_domain", "failure_domain"):
            with self.subTest(field=field):
                witnesses = copy.deepcopy(self.witnesses)
                witnesses[1][field] = witnesses[0][field]
                with self.assertRaises(ValueError):
                    budget_v10.build_checkpoint_witness_set_preregistration_v1(
                        **{**self.witness_set_kwargs, "witnesses": witnesses}
                    )

    def test_quorum_claim_binds_exact_v9_subject(self):
        claim = self.quorum_bundle["claim"]
        subject = claim["subject"]
        self.assertEqual(
            self.v9.read_bundle["evidence"]["latest_head_read_evidence_hash"],
            subject["latest_head_read_evidence_hash"],
        )
        self.assertEqual(101, subject["commit_index"])
        self.assertEqual(101, claim["attestation"]["witness_round"])
        self.assertTrue(
            budget_v10.verify_checkpoint_witness_quorum_claim_v1(
                claim,
                self.witness_set,
                expected_witness_quorum_claim_hash=claim[
                    "witness_quorum_claim_hash"
                ],
                **self.quorum_bundle["evaluation_kwargs"]["claim_build_kwargs"],
            )
        )

    def test_two_of_three_signature_evidence_pass_is_not_identity_or_latestness(self):
        evidence = self.quorum_bundle["evidence"]
        self.assertEqual("PASS", evidence["status"])
        self.assertEqual(2, evidence["quorum_summary"]["valid_witness_count"])
        self.assertTrue(evidence["facts"]["two_of_three_key_signatures_verified"])
        self.assertFalse(evidence["facts"]["witness_identities_verified"])
        self.assertFalse(evidence["facts"]["global_latest_checkpoint_verified"])
        self.assert_authority_locked(evidence["authority"])

    def test_v10_binds_quorum_to_v9_and_keeps_admission_blocked(self):
        result = self.evaluate_v10()
        self.assertEqual("PASS", result["status"])
        self.assertEqual("BLOCKED", result["admission_status"])
        self.assertTrue(
            result["facts"]["two_of_three_preregistered_key_signatures_verified"]
        )
        self.assertTrue(result["facts"]["witness_quorum_bound_to_latest_head_read"])
        self.assertFalse(result["facts"]["global_latest_checkpoint_verified"])
        self.assertFalse(
            result["facts"]["caller_checkpoint_without_witness_quorum_accepted"]
        )
        self.assert_authority_locked(result["authority"])

    def test_three_of_three_quorum_also_passes(self):
        bundle = self.build_quorum_bundle(
            signer_ids=("witness-a", "witness-b", "witness-c"),
            label="three-of-three",
        )
        self.assertEqual("PASS", bundle["evidence"]["status"])
        self.assertEqual(3, bundle["evidence"]["quorum_summary"]["valid_witness_count"])
        result = self.evaluate_v10(bundle)
        self.assertEqual("PASS", result["status"])

    def test_single_witness_is_below_quorum_and_blocks_v10(self):
        bundle = self.build_quorum_bundle(
            signer_ids=("witness-a",),
            label="one-of-three",
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v10(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("TWO_OF_THREE_WITNESS_KEY_SIGNATURES_PASS", result["blockers"])

    def test_wrong_witness_signing_key_blocks_quorum(self):
        bundle = self.build_quorum_bundle(
            signing_key_overrides={"witness-b": Ed25519PrivateKey.generate()},
            label="wrong-witness-key",
        )
        self.assertEqual("BLOCKED", bundle["evidence"]["status"])
        result = self.evaluate_v10(bundle)
        self.assertEqual("BLOCKED", result["status"])

    def test_quorum_subject_drift_blocks_v10(self):
        cases = {
            "checkpoint": {"next_checkpoint_hash": _hash("wrong-checkpoint")},
            "read": {"latest_head_read_evidence_hash": _hash("wrong-read")},
            "state": {"atomic_head_state_hash": _hash("wrong-state")},
            "clock": {"clock_evidence_hash": _hash("wrong-clock")},
        }
        for label, override in cases.items():
            with self.subTest(label=label):
                bundle = self.build_quorum_bundle(
                    subject_overrides=override,
                    label=f"drift-{label}",
                )
                self.assertEqual("PASS", bundle["evidence"]["status"])
                result = self.evaluate_v10(bundle)
                self.assertEqual("BLOCKED", result["status"])
                self.assertIn(
                    "WITNESS_QUORUM_SUBJECT_BINDING_EXACT",
                    result["blockers"],
                )

    def test_witness_set_account_scope_drift_blocks_v10(self):
        kwargs = {
            **self.witness_set_kwargs,
            "account_scope_hash": _hash("wrong-witness-scope"),
        }
        witness_set = budget_v10.build_checkpoint_witness_set_preregistration_v1(
            **kwargs
        )
        bundle = self.build_quorum_bundle(
            witness_set=witness_set,
            witness_set_kwargs=kwargs,
            subject_overrides={"account_scope_hash": kwargs["account_scope_hash"]},
            label="wrong-witness-scope",
        )
        self.assertEqual("PASS", bundle["evidence"]["status"])
        result = self.evaluate_v10(bundle)
        self.assertEqual("BLOCKED", result["status"])
        self.assertIn("WITNESS_QUORUM_STORE_SCOPE_BINDING_EXACT", result["blockers"])

    def test_duplicate_signature_witness_is_rejected(self):
        row = self.quorum_bundle["evaluation_kwargs"]["signature_rows"][0]
        with self.assertRaises(ValueError):
            budget_v10.build_signed_checkpoint_witness_quorum_v1(
                self.quorum_bundle["claim"],
                self.witness_set,
                signature_rows=[row, copy.deepcopy(row)],
                expected_witness_quorum_claim_hash=self.quorum_bundle["claim"][
                    "witness_quorum_claim_hash"
                ],
                claim_build_kwargs=self.quorum_bundle["evaluation_kwargs"][
                    "claim_build_kwargs"
                ],
            )

    def test_boolean_round_and_invalid_quorum_are_rejected(self):
        with self.assertRaises(ValueError):
            budget_v10.build_checkpoint_witness_set_preregistration_v1(
                **{**self.witness_set_kwargs, "minimum_witness_quorum": 1}
            )
        claim_kwargs = self.quorum_bundle["evaluation_kwargs"]["claim_build_kwargs"]
        with self.assertRaises(ValueError):
            budget_v10.build_checkpoint_witness_quorum_claim_v1(
                self.witness_set,
                **{**claim_kwargs, "witness_round": True},
            )

    def test_exact_verifiers_reject_resealed_promotions(self):
        witness_set = copy.deepcopy(self.witness_set)
        original_set_hash = witness_set.pop("witness_set_hash")
        witness_set["status"] = "PASS"
        witness_set = seal_strict_canonical_document(witness_set, "witness_set_hash")
        self.assertNotEqual(original_set_hash, witness_set["witness_set_hash"])
        self.assertFalse(
            budget_v10.verify_checkpoint_witness_set_preregistration_v1(
                witness_set,
                **self.witness_set_kwargs,
            )
        )

        evidence = copy.deepcopy(self.quorum_bundle["evidence"])
        original_evidence_hash = evidence.pop("witness_quorum_evidence_hash")
        evidence["status"] = "BLOCKED"
        evidence = seal_strict_canonical_document(
            evidence,
            "witness_quorum_evidence_hash",
        )
        self.assertFalse(
            budget_v10.verify_signed_checkpoint_witness_quorum_evidence_v1(
                evidence,
                self.quorum_bundle["signed"],
                self.quorum_bundle["claim"],
                self.witness_set,
                expected_witness_quorum_evidence_hash=original_evidence_hash,
                **self.quorum_bundle["evaluation_kwargs"],
            )
        )

    def test_v10_exact_verifier_rejects_resealed_output(self):
        result = self.evaluate_v10()
        args, kwargs = self.call_parts()
        self.assertTrue(
            budget_v10.verify_strategy_correlation_cluster_effective_bet_budget_v10(
                result,
                *args,
                expected_budget_v10_hash=result["budget_v10_hash"],
                **kwargs,
            )
        )
        tampered = copy.deepcopy(result)
        original_hash = tampered.pop("budget_v10_hash")
        tampered["status"] = "BLOCKED"
        tampered = seal_strict_canonical_document(tampered, "budget_v10_hash")
        self.assertFalse(
            budget_v10.verify_strategy_correlation_cluster_effective_bet_budget_v10(
                tampered,
                *args,
                expected_budget_v10_hash=original_hash,
                **kwargs,
            )
        )

    def test_outputs_are_deterministic_immutable_and_redacted(self):
        before = copy.deepcopy(
            {
                "quorum": self.quorum_bundle,
                "witness_set": self.witness_set,
                "read": self.v9.read_bundle,
            }
        )
        first = self.evaluate_v10()
        second = self.evaluate_v10()
        self.assertEqual(first, second)
        self.assertEqual(before["quorum"], self.quorum_bundle)
        self.assertEqual(before["witness_set"], self.witness_set)
        self.assertEqual(before["read"], self.v9.read_bundle)

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

    def test_production_has_no_private_key_witness_io_network_or_runtime_access(self):
        source = Path(budget_v10.__file__).read_text(encoding="utf-8")
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
