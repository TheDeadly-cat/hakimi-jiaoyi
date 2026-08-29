from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import inspect
import unittest

from exchange_terminal.application import witness_ownership_state_service as service
from exchange_terminal.interfaces import witness_ownership_state_store as store
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_strategy_correlation_cluster_effective_bet_budget_v11 as v11_tests,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipStateStoreContractV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = v11_tests.StrategyCorrelationClusterEffectiveBetBudgetV11Tests(
            methodName="test_v11_binds_ownership_transition_to_v10"
        )
        fixture.setUp()
        self.ownership_bundle = fixture.build_ownership_bundle()
        self.v11_args, self.v11_kwargs = fixture.call_parts(
            ownership_bundle=self.ownership_bundle
        )
        self.v11_document = fixture.evaluate_v11(
            ownership_bundle=self.ownership_bundle
        )
        self.registry_id = "synthetic-witness-ownership-registry"
        self.command = (
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=_hash(
                    "synthetic-witness-ownership-namespace-preregistration"
                ),
                ownership_claim_hash=self.v11_document["source"][
                    "ownership_claim_hash"
                ],
                ownership_evidence_hash=self.v11_document["source"][
                    "ownership_evidence_hash"
                ],
                expected_state_hash=self.v11_document["source"][
                    "previous_ownership_state_hash"
                ],
                proposed_state_hash=self.v11_document["source"][
                    "next_ownership_state_hash"
                ],
                expected_registry_revision=41,
                request_nonce_hash=_hash("synthetic-persistence-request-42"),
            )
        )
        self.result = (
            store.build_witness_ownership_compare_consume_and_advance_result_v1(
                self.command,
                outcome=store.WitnessOwnershipProviderOutcomeV1.ADVANCED,
                registry_id=self.registry_id,
                observed_registry_revision=41,
                observed_state_hash=self.command.expected_state_hash,
            )
        )

    def evaluate(self, *, document=None, command=None, result=None, **overrides):
        budget_document = self.v11_document if document is None else document
        candidate_command = self.command if command is None else command
        candidate_result = self.result if result is None else result
        kwargs = {
            "expected_budget_v11_hash": self.v11_document["budget_v11_hash"],
            "budget_v11_verify_args": self.v11_args,
            "budget_v11_verify_kwargs": self.v11_kwargs,
            "expected_command_hash": candidate_command.command_hash,
            "expected_registry_id": self.registry_id,
        }
        kwargs.update(overrides)
        return service.evaluate_witness_ownership_state_persistence_consumer_v1(
            budget_document,
            candidate_command,
            candidate_result,
            **kwargs,
        )

    def test_reproduces_v11_persistence_gap(self):
        self.assertFalse(
            self.v11_document["facts"][
                "witness_ownership_state_persistence_verified"
            ]
        )
        self.assertIsNone(
            service.evaluate_witness_ownership_state_persistence_consumer_v1(
                self.v11_document,
                self.command,
                None,
                expected_budget_v11_hash=self.v11_document["budget_v11_hash"],
                budget_v11_verify_args=self.v11_args,
                budget_v11_verify_kwargs=self.v11_kwargs,
                expected_command_hash=self.command.command_hash,
                expected_registry_id=self.registry_id,
            )
        )

    def test_command_is_exact_and_deterministic(self):
        rebuilt = (
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=(
                    self.command.namespace_preregistration_hash
                ),
                ownership_claim_hash=self.command.ownership_claim_hash,
                ownership_evidence_hash=self.command.ownership_evidence_hash,
                expected_state_hash=self.command.expected_state_hash,
                proposed_state_hash=self.command.proposed_state_hash,
                expected_registry_revision=self.command.expected_registry_revision,
                request_nonce_hash=self.command.request_nonce_hash,
            )
        )
        self.assertEqual(rebuilt, self.command)

    def test_consumption_key_binds_claim_and_preregistration(self):
        changed_claim_key = store.build_witness_ownership_consumption_key_v1(
            namespace_preregistration_hash=(
                self.command.namespace_preregistration_hash
            ),
            ownership_claim_hash=_hash("different-claim"),
        )
        changed_namespace_key = store.build_witness_ownership_consumption_key_v1(
            namespace_preregistration_hash=_hash("different-preregistration"),
            ownership_claim_hash=self.command.ownership_claim_hash,
        )
        self.assertNotEqual(changed_claim_key, self.command.consumption_key)
        self.assertNotEqual(changed_namespace_key, self.command.consumption_key)

    def test_boolean_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=(
                    self.command.namespace_preregistration_hash
                ),
                ownership_claim_hash=self.command.ownership_claim_hash,
                ownership_evidence_hash=self.command.ownership_evidence_hash,
                expected_state_hash=self.command.expected_state_hash,
                proposed_state_hash=self.command.proposed_state_hash,
                expected_registry_revision=True,
                request_nonce_hash=self.command.request_nonce_hash,
            )

    def test_noop_state_transition_is_rejected(self):
        with self.assertRaises(ValueError):
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=(
                    self.command.namespace_preregistration_hash
                ),
                ownership_claim_hash=self.command.ownership_claim_hash,
                ownership_evidence_hash=self.command.ownership_evidence_hash,
                expected_state_hash=self.command.expected_state_hash,
                proposed_state_hash=self.command.expected_state_hash,
                expected_registry_revision=41,
                request_nonce_hash=self.command.request_nonce_hash,
            )

    def test_advanced_result_and_receipt_are_exact(self):
        self.assertTrue(
            store.verify_witness_ownership_compare_consume_and_advance_result_v1(
                self.result,
                self.command,
                expected_registry_id=self.registry_id,
            )
        )
        receipt = self.result.receipt_document
        self.assertEqual(
            receipt["returned_state_hash"], self.command.proposed_state_hash
        )
        self.assertFalse(
            receipt["verification_limits"]["claims_independently_verified"]
        )

    def test_advanced_result_requires_exact_cas_baseline(self):
        with self.assertRaises(ValueError):
            store.build_witness_ownership_compare_consume_and_advance_result_v1(
                self.command,
                outcome=store.WitnessOwnershipProviderOutcomeV1.ADVANCED,
                registry_id=self.registry_id,
                observed_registry_revision=42,
                observed_state_hash=self.command.expected_state_hash,
            )

    def test_rejected_result_leaves_state_unchanged(self):
        duplicate = (
            store.build_witness_ownership_compare_consume_and_advance_result_v1(
                self.command,
                outcome=(
                    store.WitnessOwnershipProviderOutcomeV1.DUPLICATE_REJECTED
                ),
                registry_id=self.registry_id,
                observed_registry_revision=42,
                observed_state_hash=self.command.proposed_state_hash,
            )
        )
        self.assertEqual(
            duplicate.observed_registry_revision,
            duplicate.returned_registry_revision,
        )
        self.assertEqual(
            duplicate.observed_state_hash, duplicate.returned_state_hash
        )
        self.assertIsNone(duplicate.receipt_document)

    def test_tampered_receipt_claim_is_rejected(self):
        receipt = dict(self.result.receipt_document)
        claims = dict(receipt["provider_claims"])
        claims["durable_commit_claimed"] = False
        receipt["provider_claims"] = claims
        tampered = replace(self.result, receipt_document=receipt)
        self.assertFalse(
            store.verify_witness_ownership_compare_consume_and_advance_result_v1(
                tampered,
                self.command,
                expected_registry_id=self.registry_id,
            )
        )

    def test_consumer_accepts_structure_but_keeps_source_truth_unknown(self):
        document = self.evaluate()
        self.assertEqual(document["status"], "UNKNOWN")
        self.assertEqual(document["admission_status"], "BLOCKED")
        self.assertTrue(document["facts"]["provider_result_structurally_bound"])
        for name in (
            "provider_identity_verified",
            "provider_receipt_signature_verified",
            "durable_commit_verified",
            "linearizable_read_after_write_verified",
            "rollback_resistance_verified",
            "witness_ownership_state_persistence_verified",
        ):
            self.assertFalse(document["facts"][name])
        self.assertTrue(all(value is False for value in document["authority"].values()))

    def test_consumer_binds_all_v11_ownership_hashes(self):
        changed = (
            store.build_witness_ownership_compare_consume_and_advance_command_v1(
                namespace_preregistration_hash=(
                    self.command.namespace_preregistration_hash
                ),
                ownership_claim_hash=self.command.ownership_claim_hash,
                ownership_evidence_hash=_hash("different-ownership-evidence"),
                expected_state_hash=self.command.expected_state_hash,
                proposed_state_hash=self.command.proposed_state_hash,
                expected_registry_revision=self.command.expected_registry_revision,
                request_nonce_hash=self.command.request_nonce_hash,
            )
        )
        self.assertIsNone(self.evaluate(command=changed))

    def test_resealed_v11_drift_is_rejected(self):
        changed = dict(self.v11_document)
        changed_source = dict(changed["source"])
        changed_source["ownership_claim_hash"] = _hash("drifted-claim")
        changed["source"] = changed_source
        changed.pop("budget_v11_hash")
        changed = seal_strict_canonical_document(changed, "budget_v11_hash")
        self.assertIsNone(self.evaluate(document=changed))

    def test_expected_command_hash_drift_is_rejected(self):
        self.assertIsNone(
            self.evaluate(expected_command_hash=_hash("wrong-command"))
        )

    def test_registry_identity_drift_is_rejected(self):
        self.assertIsNone(
            self.evaluate(expected_registry_id="different-synthetic-registry")
        )

    def test_duplicate_result_is_blocked_without_promotion(self):
        duplicate = (
            store.build_witness_ownership_compare_consume_and_advance_result_v1(
                self.command,
                outcome=(
                    store.WitnessOwnershipProviderOutcomeV1.DUPLICATE_REJECTED
                ),
                registry_id=self.registry_id,
                observed_registry_revision=42,
                observed_state_hash=self.command.proposed_state_hash,
            )
        )
        document = self.evaluate(result=duplicate)
        self.assertEqual(document["status"], "BLOCKED")
        self.assertIn("PROVIDER_RESULT_NOT_ADVANCED", document["blockers"])
        self.assertEqual(document["admission_status"], "BLOCKED")

    def test_exact_evaluation_verifier_rejects_resealed_promotion(self):
        document = self.evaluate()
        self.assertTrue(
            service.verify_witness_ownership_state_persistence_consumer_v1(
                document,
                self.v11_document,
                self.command,
                self.result,
                expected_evaluation_hash=document["evaluation_hash"],
                expected_budget_v11_hash=self.v11_document["budget_v11_hash"],
                budget_v11_verify_args=self.v11_args,
                budget_v11_verify_kwargs=self.v11_kwargs,
                expected_command_hash=self.command.command_hash,
                expected_registry_id=self.registry_id,
            )
        )
        promoted = dict(document)
        promoted["admission_status"] = "READY"
        promoted.pop("evaluation_hash")
        promoted = seal_strict_canonical_document(promoted, "evaluation_hash")
        self.assertFalse(
            service.verify_witness_ownership_state_persistence_consumer_v1(
                promoted,
                self.v11_document,
                self.command,
                self.result,
                expected_evaluation_hash=promoted["evaluation_hash"],
                expected_budget_v11_hash=self.v11_document["budget_v11_hash"],
                budget_v11_verify_args=self.v11_args,
                budget_v11_verify_kwargs=self.v11_kwargs,
                expected_command_hash=self.command.command_hash,
                expected_registry_id=self.registry_id,
            )
        )

    def test_outputs_are_deterministic_and_redacted(self):
        first = self.evaluate()
        second = self.evaluate()
        self.assertEqual(first, second)
        serialized = repr(first)
        self.assertNotIn("signature_rows", serialized)
        self.assertNotIn("public_key", serialized)
        self.assertNotIn("private_key", serialized)

    def test_provider_protocol_is_structural_only(self):
        class SyntheticProvider:
            registry_id = self.registry_id

            def compare_consume_and_advance(self, command):
                return self_result

        self_result = self.result
        provider = SyntheticProvider()
        self.assertIsInstance(provider, store.WitnessOwnershipStateProviderPortV1)
        self.assertEqual(
            provider.compare_consume_and_advance(self.command), self.result
        )

    def test_production_modules_have_no_io_or_private_key_material(self):
        source = inspect.getsource(store) + inspect.getsource(service)
        for forbidden in (
            "Ed25519PrivateKey",
            "private_key =",
            "requests.",
            "socket.",
            "subprocess.",
            "sqlite3",
            "os.environ",
            "Path(",
            "open(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
