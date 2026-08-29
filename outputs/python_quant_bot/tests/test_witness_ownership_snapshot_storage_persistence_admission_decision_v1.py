from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1 as evidence,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_persistence_admission_decision_v1 as admission,
)
from tests import (
    test_witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1 as lineage_fixture,
)


def _hash(label: str) -> str:
    return sha256(label.encode("ascii")).hexdigest()


class WitnessOwnershipPersistenceAdmissionDecisionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_class = (
            lineage_fixture.WitnessOwnershipHarnessEvidenceLineageBindingV1Tests
        )
        self.fixture = fixture_class(
            "test_complete_chain_binds_thirteen_driver_and_one_observer_requirement"
        )
        self.fixture.setUp()
        self.lineage_document = self.fixture._evaluate()

    def _lineage_args(self, reports=None, evidence_evaluation=None):
        reports = self.fixture.signed_reports if reports is None else reports
        evidence_evaluation = (
            self.fixture.evidence_evaluation
            if evidence_evaluation is None
            else evidence_evaluation
        )
        return (
            evidence_evaluation,
            reports,
            self.fixture.harness_bundle,
            self.fixture.plan,
            self.fixture.admission_evaluation,
            self.fixture.identity_assertions,
            self.fixture.identity_document,
            self.fixture.storage_document,
            self.fixture.observer_registrations,
        )

    def _lineage_kwargs(self):
        return {
            "storage_preregistration_kwargs": self.fixture.storage_kwargs,
            "harness_plan_build_kwargs": self.fixture.plan_kwargs,
            "identity_source_preregistration_kwargs": self.fixture.identity_kwargs,
        }

    def _evaluate(self, lineage_document=None, lineage_args=None):
        lineage_document = (
            self.lineage_document if lineage_document is None else lineage_document
        )
        lineage_args = self._lineage_args() if lineage_args is None else lineage_args
        return admission.evaluate_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
            lineage_document,
            *lineage_args,
            expected_lineage_binding_hash=lineage_document["lineage_binding_hash"],
            **self._lineage_kwargs(),
        )

    def test_complete_lineage_is_only_a_structural_test_candidate(self) -> None:
        decision = self._evaluate()
        self.assertEqual(
            decision["status"],
            admission.STATUS_STRUCTURAL_TEST_CANDIDATE,
        )
        self.assertTrue(decision["structural_lineage_verified"])
        self.assertTrue(decision["isolated_backend_test_candidate"])

    def test_candidate_gate_remains_block_and_decision_is_do_not_mount(self) -> None:
        decision = self._evaluate()
        self.assertEqual(decision["gate_status"], admission.GATE_STATUS_BLOCK)
        self.assertEqual(decision["decision"], admission.DECISION_DO_NOT_MOUNT)
        self.assertFalse(decision["isolated_backend_test_authorized"])
        self.assertFalse(decision["backend_mount_authorized"])

    def test_candidate_lists_all_six_pending_conditions(self) -> None:
        decision = self._evaluate()
        self.assertEqual(
            decision["blocker_codes"],
            list(admission.PENDING_CONDITIONS),
        )

    def test_all_execution_and_trading_authorities_remain_false(self) -> None:
        decision = self._evaluate()
        false_fields = (
            "explicit_isolated_test_authorization_supplied",
            "isolated_backend_test_authorized",
            "backend_mount_authorized",
            "real_identity_source_truth_verified",
            "external_observer_identity_verified",
            "real_adapter_execution_verified",
            "isolated_domain_confinement_verified",
            "external_persistence_independently_verified",
            "permission",
            "paper_authorized",
            "live_authorized",
            "snapshot_publication_authorized",
            "current_chain_activated",
        )
        self.assertTrue(all(decision[field] is False for field in false_fields))

    def test_exact_verifier_accepts_exact_decision(self) -> None:
        decision = self._evaluate()
        self.assertTrue(
            admission.verify_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
                decision,
                self.lineage_document,
                *self._lineage_args(),
                expected_persistence_admission_decision_hash=decision[
                    "persistence_admission_decision_hash"
                ],
                expected_lineage_binding_hash=self.lineage_document[
                    "lineage_binding_hash"
                ],
                **self._lineage_kwargs(),
            )
        )

    def test_valid_blocked_lineage_is_not_a_candidate(self) -> None:
        requirement_id = self.fixture.plan["scenarios"][0]["requirement_id"]
        reports = self.fixture._build_reports(
            {requirement_id: {"artifact_hash": _hash("wrong-artifact")}}
        )
        evidence_evaluation = evidence.evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
            reports,
            self.fixture.storage_document,
            self.fixture.observer_registrations,
            storage_preregistration_kwargs=self.fixture.storage_kwargs,
        )
        blocked_lineage = self.fixture._evaluate(reports, evidence_evaluation)
        decision = self._evaluate(
            blocked_lineage,
            self._lineage_args(reports, evidence_evaluation),
        )
        self.assertEqual(decision["status"], admission.STATUS_BLOCK)
        self.assertFalse(decision["isolated_backend_test_candidate"])
        self.assertEqual(decision["blocker_codes"], ["LINEAGE_BINDING_NOT_COMPLETE"])

    def test_tampered_lineage_is_rejected_not_downgraded(self) -> None:
        tampered = deepcopy(self.lineage_document)
        tampered["permission"] = True
        result = admission.evaluate_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
            tampered,
            *self._lineage_args(),
            expected_lineage_binding_hash=self.lineage_document["lineage_binding_hash"],
            **self._lineage_kwargs(),
        )
        self.assertEqual(result, {})

    def test_verifier_rejects_candidate_authorization_escalation(self) -> None:
        decision = self._evaluate()
        tampered = deepcopy(decision)
        tampered["isolated_backend_test_authorized"] = True
        self.assertFalse(
            admission.verify_witness_ownership_snapshot_storage_persistence_admission_decision_v1(
                tampered,
                self.lineage_document,
                *self._lineage_args(),
                expected_persistence_admission_decision_hash=decision[
                    "persistence_admission_decision_hash"
                ],
                expected_lineage_binding_hash=self.lineage_document[
                    "lineage_binding_hash"
                ],
                **self._lineage_kwargs(),
            )
        )

    def test_decision_binds_lineage_and_component_hashes(self) -> None:
        decision = self._evaluate()
        self.assertEqual(
            decision["lineage_binding_hash"],
            self.lineage_document["lineage_binding_hash"],
        )
        self.assertEqual(
            decision["component_hashes"],
            self.lineage_document["component_hashes"],
        )

    def test_decision_contains_no_ready_profit_or_runtime_locator_claims(self) -> None:
        serialized = json.dumps(self._evaluate(), sort_keys=True)
        self.assertNotIn('"READY"', serialized)
        self.assertNotIn("profitability", serialized)
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn('"backend_mount_authorized": true', serialized)


if __name__ == "__main__":
    unittest.main()
