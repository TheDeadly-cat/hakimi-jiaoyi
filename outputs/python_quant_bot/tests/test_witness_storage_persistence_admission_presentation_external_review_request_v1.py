from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import unittest

from exchange_terminal.application import (
    witness_ownership_snapshot_storage_persistence_admission_presentation_v1 as projection,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services import (
    witness_storage_persistence_admission_presentation_external_review_request_v1 as subject,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NonNativeDocument(dict):
    pass


class WitnessStoragePersistenceAdmissionExternalReviewRequestV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.request = (
            subject.build_witness_storage_persistence_admission_presentation_external_review_request_v1()
        )

    def test_request_binds_target_and_awaits_authenticated_external_review(self) -> None:
        self.assertEqual(
            self.request["schema_version"], subject.REQUEST_SCHEMA_VERSION
        )
        self.assertEqual(
            self.request["status"], "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
        )
        self.assertEqual(
            self.request["request_state"],
            "EXACT_REVIEW_TARGET_BOUND_AWAITING_AUTHENTICATED_EXTERNAL_REVIEW",
        )

    def test_target_manifest_hash_is_exact(self) -> None:
        self.assertEqual(
            self.request["target_manifest_hash"],
            strict_canonical_hash(self.request["review_target"]),
        )

    def test_source_contract_pins_projection_view_model_and_hash_policy(self) -> None:
        contract = self.request["review_target"]["source_contract"]
        self.assertEqual(
            contract["presentation_schema_version"], projection.SCHEMA_VERSION
        )
        self.assertEqual(
            contract["presentation_static_fingerprint"],
            projection.STATIC_FINGERPRINT,
        )
        self.assertEqual(
            contract["expected_source_hash_policy"],
            subject.EXPECTED_SOURCE_HASH_POLICY,
        )
        self.assertEqual(contract["ordered_stages"], list(subject.ORDERED_STAGES))

    def test_review_artifact_hashes_match_current_explicit_sources(self) -> None:
        expected = subject.expected_review_artifact_hashes_v1()
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)
        self.assertEqual(
            self.request["review_target"]["review_artifact_sha256"], expected
        )

    def test_protected_host_preimages_match_and_are_not_registration(self) -> None:
        expected = subject.expected_protected_host_preimages_v1()
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)
        baseline = self.request["review_target"]["permission_baseline"]
        self.assertFalse(baseline["host_assets_modified"])
        self.assertFalse(baseline["route_registered"])
        self.assertFalse(baseline["dom_mounted"])

    def test_local_contract_counts_are_scoped_as_synthetic_only(self) -> None:
        baseline = self.request["review_target"][
            "declared_local_contract_baseline"
        ]
        self.assertEqual(baseline["evidence_kind"], "PURE_SYNTHETIC_IN_MEMORY_NO_DOM")
        self.assertEqual(baseline["python_projection_targeted_case_count"], 9)
        self.assertEqual(baseline["node_view_model_targeted_case_count"], 13)
        self.assertEqual(baseline["explicit_adr0413_adr0426_matrix_case_count"], 239)
        self.assertFalse(baseline["browser_visual_review_performed"])
        self.assertFalse(baseline["real_source_truth_verified"])
        self.assertFalse(baseline["external_persistence_verified"])

    def test_rubric_is_exact_and_requires_external_attestation(self) -> None:
        self.assertEqual(set(self.request["rubric"]), set(subject.REVIEW_RUBRIC_KEYS))
        self.assertEqual(len(self.request["rubric"]), 10)
        self.assertTrue(
            all(
                value == "REVIEWER_MUST_ATTEST_TRUE"
                for value in self.request["rubric"].values()
            )
        )

    def test_request_never_claims_delivery_review_or_consumer_registration(self) -> None:
        facts = self.request["facts"]
        self.assertFalse(facts["review_request_delivered"])
        self.assertFalse(facts["reviewer_identity_authenticated"])
        self.assertFalse(facts["attestation_signature_verified"])
        self.assertFalse(facts["external_independent_review_complete"])
        self.assertFalse(facts["consumer_preregistered"])
        self.assertTrue(all(value is False for value in self.request["authority"].values()))

    def test_all_review_and_activation_blockers_remain_explicit(self) -> None:
        blockers = self.request["blockers"]
        self.assertIn("REVIEW_REQUEST_DELIVERY_NOT_AUTHORIZED", blockers)
        self.assertIn("REVIEWER_IDENTITY_UNAUTHENTICATED", blockers)
        self.assertIn("ATTESTATION_SIGNATURE_ABSENT", blockers)
        self.assertIn("EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED", blockers)
        self.assertIn("CONSUMER_PREREGISTRATION_BLOCKED_PENDING_REVIEW", blockers)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_promotion(self) -> None:
        self.assertTrue(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                self.request
            )
        )
        promoted = deepcopy(self.request)
        promoted["facts"]["external_independent_review_complete"] = True
        promoted["authority"]["consumer_preregistration_allowed"] = True
        promoted.pop("review_request_hash")
        promoted = seal_strict_canonical_document(promoted, "review_request_hash")
        self.assertFalse(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                promoted
            )
        )

    def test_target_hash_substitution_is_rejected_even_when_resealed(self) -> None:
        tampered = deepcopy(self.request)
        tampered["review_target"]["review_artifact_sha256"][
            next(iter(subject.expected_review_artifact_hashes_v1()))
        ] = "f" * 64
        tampered["target_manifest_hash"] = strict_canonical_hash(
            tampered["review_target"]
        )
        tampered.pop("review_request_hash")
        tampered = seal_strict_canonical_document(tampered, "review_request_hash")
        self.assertFalse(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                tampered
            )
        )

    def test_non_native_cyclic_and_extra_documents_fail_exact_verification(self) -> None:
        self.assertFalse(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                NonNativeDocument(self.request)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                cyclic
            )
        )
        extra = deepcopy(self.request)
        extra["compatibility_alias"] = True
        self.assertFalse(
            subject.verify_witness_storage_persistence_admission_presentation_external_review_request_v1(
                extra
            )
        )

    def test_hash_maps_are_fresh_copies(self) -> None:
        artifacts = subject.expected_review_artifact_hashes_v1()
        protected = subject.expected_protected_host_preimages_v1()
        artifacts.clear()
        protected.clear()
        self.assertEqual(len(subject.expected_review_artifact_hashes_v1()), 7)
        self.assertEqual(len(subject.expected_protected_host_preimages_v1()), 3)

    def test_request_contains_no_promotional_or_sensitive_runtime_claim(self) -> None:
        serialized = json.dumps(self.request, sort_keys=True)
        forbidden = re.compile(
            r"\b(?:READY|PROFIT|RETURN|BUY|SELL)\b", re.IGNORECASE
        )
        self.assertIsNone(forbidden.search(serialized))
        self.assertNotIn("connection_string", serialized)
        self.assertNotIn("storage_path", serialized)
        self.assertNotIn("private_key", serialized)
        self.assertFalse(self.request["facts"]["raw_projection_document_embedded"])
        self.assertFalse(self.request["facts"]["raw_view_model_document_embedded"])

    def test_request_is_deterministic_native_json(self) -> None:
        rebuilt = (
            subject.build_witness_storage_persistence_admission_presentation_external_review_request_v1()
        )
        self.assertEqual(self.request, rebuilt)
        self.assertEqual(json.loads(json.dumps(self.request)), self.request)


if __name__ == "__main__":
    unittest.main()
