from __future__ import annotations

from copy import deepcopy
import json
import re
import unittest

from exchange_terminal.application import (
    witness_ownership_snapshot_storage_persistence_admission_decision_v1 as admission,
)
from exchange_terminal.application import (
    witness_ownership_snapshot_storage_persistence_admission_presentation_v1 as subject,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from tests import (
    test_witness_ownership_snapshot_storage_persistence_admission_decision_v1 as decision_fixture,
)


class WitnessOwnershipPersistenceAdmissionPresentationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_class = (
            decision_fixture.WitnessOwnershipPersistenceAdmissionDecisionV1Tests
        )
        self.fixture = fixture_class(
            "test_complete_lineage_is_only_a_structural_test_candidate"
        )
        self.fixture.setUp()
        self.decision = self.fixture._evaluate()

    def _build(self, decision=None, expected_decision_hash=None):
        decision = self.decision if decision is None else decision
        expected_decision_hash = (
            self.decision["persistence_admission_decision_hash"]
            if expected_decision_hash is None
            else expected_decision_hash
        )
        return subject.build_witness_ownership_snapshot_storage_persistence_admission_presentation_v1(
            decision,
            self.fixture.lineage_document,
            *self.fixture._lineage_args(),
            expected_persistence_admission_decision_hash=expected_decision_hash,
            expected_lineage_binding_hash=self.fixture.lineage_document[
                "lineage_binding_hash"
            ],
            **self.fixture._lineage_kwargs(),
        )

    def _verify(self, presentation, expected_presentation_hash=None):
        expected_presentation_hash = (
            presentation["presentation_hash"]
            if expected_presentation_hash is None
            else expected_presentation_hash
        )
        return subject.verify_witness_ownership_snapshot_storage_persistence_admission_presentation_v1(
            presentation,
            self.decision,
            self.fixture.lineage_document,
            *self.fixture._lineage_args(),
            expected_presentation_hash=expected_presentation_hash,
            expected_persistence_admission_decision_hash=self.decision[
                "persistence_admission_decision_hash"
            ],
            expected_lineage_binding_hash=self.fixture.lineage_document[
                "lineage_binding_hash"
            ],
            **self.fixture._lineage_kwargs(),
        )

    def test_stage_order_is_neutral_and_permission_is_blocked(self) -> None:
        presentation = self._build()
        self.assertEqual(presentation["presentation_status"], subject.PRESENTATION_STATUS)
        self.assertEqual(presentation["display_tone"], subject.DISPLAY_TONE)
        self.assertEqual(presentation["stage_order"], list(subject.ORDERED_STAGES))
        self.assertEqual(
            [stage["axis"] for stage in presentation["stages"]],
            list(subject.ORDERED_STAGES),
        )
        self.assertEqual(presentation["stages"][-1]["state"], "BLOCKED")

    def test_candidate_maturity_does_not_promote_permission(self) -> None:
        presentation = self._build()
        self.assertEqual(
            presentation["stages"][2]["state"], "STRUCTURAL_TEST_CANDIDATE"
        )
        self.assertTrue(presentation["facts"]["isolated_backend_test_candidate"])
        self.assertFalse(presentation["facts"]["isolated_backend_test_authorized"])
        self.assertFalse(presentation["facts"]["backend_mount_authorized"])
        self.assertFalse(presentation["facts"]["current_chain_activated"])

    def test_all_six_gaps_are_preserved_without_source_documents(self) -> None:
        presentation = self._build()
        self.assertEqual(presentation["blockers"], list(admission.PENDING_CONDITIONS))
        self.assertEqual(presentation["summary"]["blocker_count"], 6)
        self.assertNotIn("component_hashes", presentation)
        self.assertEqual(
            set(presentation["source"]),
            {
                "persistence_admission_decision_hash",
                "lineage_binding_hash",
                "lineage_bundle_hash",
                "lineage_implementation_sha256",
            },
        )

    def test_redaction_and_all_operational_authority_are_locked(self) -> None:
        presentation = self._build()
        redaction_fields = (
            "raw_decision_document_embedded",
            "raw_lineage_document_embedded",
            "raw_component_hash_map_embedded",
            "raw_key_material_embedded",
            "raw_signature_material_embedded",
        )
        self.assertTrue(
            all(presentation["facts"][field] is False for field in redaction_fields)
        )
        self.assertTrue(
            all(
                value is False
                for key, value in presentation["authority"].items()
                if key != "descriptive_only"
            )
        )

    def test_exact_verifier_accepts_only_the_exact_projection(self) -> None:
        presentation = self._build()
        self.assertTrue(self._verify(presentation))
        tampered = deepcopy(presentation)
        tampered["authority"]["backend_mount_allowed"] = True
        tampered.pop("presentation_hash")
        resealed = seal_strict_canonical_document(tampered, "presentation_hash")
        self.assertFalse(self._verify(resealed, resealed["presentation_hash"]))

    def test_tampered_source_decision_degrades_to_unknown_without_echo(self) -> None:
        tampered = deepcopy(self.decision)
        tampered["backend_mount_authorized"] = True
        tampered["private_locator"] = "must-not-echo"
        presentation = self._build(tampered)
        self.assertEqual(
            presentation["presentation_status"], subject.UNKNOWN_PRESENTATION_STATUS
        )
        self.assertEqual(presentation["display_state"], "UNKNOWN")
        self.assertTrue(all(value is None for value in presentation["source"].values()))
        self.assertNotIn("must-not-echo", json.dumps(presentation, sort_keys=True))

    def test_invalid_expected_hash_degrades_to_unknown(self) -> None:
        presentation = self._build(expected_decision_hash="not-a-hash")
        self.assertEqual(
            presentation["presentation_status"], subject.UNKNOWN_PRESENTATION_STATUS
        )
        self.assertEqual(presentation["stages"][-1]["state"], "BLOCKED")

    def test_projection_is_deterministic_and_contains_no_promotional_words(self) -> None:
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        forbidden = re.compile(r"\b(?:READY|PROFIT|RETURN|BUY|SELL)\b", re.IGNORECASE)
        self.assertIsNone(forbidden.search(json.dumps(first, sort_keys=True)))

    def test_serialized_projection_contains_no_runtime_locator_claims(self) -> None:
        serialized = json.dumps(self._build(), sort_keys=True)
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn('"backend_mount_authorized": true', serialized)
        self.assertNotIn('"paper_authorized": true', serialized)
        self.assertNotIn('"live_order_allowed": true', serialized)


if __name__ == "__main__":
    unittest.main()
