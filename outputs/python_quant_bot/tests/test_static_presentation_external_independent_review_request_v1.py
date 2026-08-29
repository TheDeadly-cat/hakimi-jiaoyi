from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.static_presentation_external_independent_review_request_v1 import (
    CLAIM_SCHEMA_VERSION,
    INTAKE_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    REVIEW_RUBRIC_KEYS,
    build_static_presentation_external_independent_review_claim_intake_v1,
    build_static_presentation_external_independent_review_request_v1,
    verify_static_presentation_external_independent_review_claim_intake_v1,
    verify_static_presentation_external_independent_review_request_v1,
)
from exchange_terminal.services.static_presentation_unmounted_render_review_asset_registration_v1 import (
    build_static_presentation_unmounted_render_review_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationExternalIndependentReviewRequestV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registration = (
            build_static_presentation_unmounted_render_review_asset_registration_v1()
        )
        self.request = build_static_presentation_external_independent_review_request_v1(
            self.registration
        )
        self.claim = {
            "schema_version": CLAIM_SCHEMA_VERSION,
            "review_request_hash": self.request["review_request_hash"],
            "target_manifest_hash": self.request["target_manifest_hash"],
            "reviewer_claim_id": "external-review-claim-0298",
            "reviewer_process_id": "external-review-process-0298",
            "independence_claimed": True,
            "rubric_results": {key: True for key in REVIEW_RUBRIC_KEYS},
        }
        self.intake = (
            build_static_presentation_external_independent_review_claim_intake_v1(
                self.request,
                self.claim,
                self.registration,
            )
        )

    def test_request_binds_exact_registration_and_awaits_external_review(self) -> None:
        self.assertEqual(self.request["schema_version"], REQUEST_SCHEMA_VERSION)
        self.assertEqual(
            self.request["status"],
            "AWAITING_EXTERNAL_INDEPENDENT_REVIEW",
        )
        self.assertEqual(
            self.request["request_state"],
            "EXACT_REVIEW_TARGET_BOUND_AWAITING_EXTERNAL_REVIEW",
        )
        self.assertTrue(self.request["facts"]["asset_registration_exactly_verified"])

    def test_target_manifest_hash_is_exact(self) -> None:
        self.assertEqual(
            self.request["target_manifest_hash"],
            strict_canonical_hash(self.request["review_target"]),
        )

    def test_target_pins_registration_and_source_file_hashes(self) -> None:
        target = self.request["review_target"]
        registration = target["asset_registration"]
        self.assertEqual(
            registration["asset_registration_hash"],
            self.registration["asset_registration_hash"],
        )
        expected = {
            "exchange_terminal/services/static_presentation_unmounted_render_review_asset_registration_v1.py": registration[
                "implementation_sha256"
            ],
            "tests/test_static_presentation_unmounted_render_review_asset_registration_v1.py": registration[
                "test_sha256"
            ],
            "docs/adr/0297-static-presentation-unmounted-render-review-asset-registration-v1.md": registration[
                "adr_sha256"
            ],
            "exchange_terminal/static/evidence_static_presentation_unmounted_render_review_v1.js": target[
                "review_assets"
            ]["implementation_sha256"],
            "exchange_terminal/static/evidence_static_presentation_unmounted_render_review_v1.test.js": target[
                "review_assets"
            ]["node_test_sha256"],
            "docs/adr/0296-static-presentation-unmounted-render-review-v1.md": target[
                "review_assets"
            ]["adr_sha256"],
        }
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_local_behavior_hashes_are_bound_as_synthetic_only(self) -> None:
        evidence = self.request["review_target"]["local_behavior_evidence"]
        self.assertEqual(evidence["evidence_kind"], "PURE_SYNTHETIC_NO_DOM_FIXTURE")
        self.assertEqual(evidence["clear"]["status_label"], "LOCAL CLEAR")
        self.assertEqual(evidence["block"]["status_label"], "LOCAL BLOCK")
        self.assertEqual(evidence["unknown"]["status_label"], "SOURCE UNKNOWN")
        self.assertIsNone(evidence["unknown"]["markup_sha256"])

    def test_rubric_is_exact_and_requires_all_true_attestation(self) -> None:
        self.assertEqual(set(self.request["rubric"]), set(REVIEW_RUBRIC_KEYS))
        self.assertTrue(
            all(
                value == "REVIEWER_MUST_ATTEST_TRUE"
                for value in self.request["rubric"].values()
            )
        )

    def test_request_never_claims_authentication_or_review_completion(self) -> None:
        facts = self.request["facts"]
        self.assertFalse(facts["reviewer_identity_authenticated"])
        self.assertFalse(facts["reviewer_process_authenticated"])
        self.assertFalse(facts["attestation_signature_verified"])
        self.assertFalse(facts["review_replay_durability_proven"])
        self.assertFalse(facts["external_independent_review_complete"])
        self.assertTrue(all(value is False for value in self.request["authority"].values()))

    def test_tampered_registration_builds_unknown_request(self) -> None:
        tampered = copy.deepcopy(self.registration)
        tampered["facts"]["external_independent_review_complete"] = True
        request = build_static_presentation_external_independent_review_request_v1(
            tampered
        )
        self.assertEqual(request["status"], "UNKNOWN")
        self.assertIsNone(request["review_target"])
        self.assertIsNone(request["target_manifest_hash"])

    def test_non_native_registration_builds_unknown_request(self) -> None:
        request = build_static_presentation_external_independent_review_request_v1(
            NonNativeMapping(self.registration)
        )
        self.assertEqual(request["status"], "UNKNOWN")

    def test_request_exact_verifier_accepts_rebuild_and_rejects_promotion(self) -> None:
        self.assertTrue(
            verify_static_presentation_external_independent_review_request_v1(
                self.request,
                self.registration,
            )
        )
        promoted = copy.deepcopy(self.request)
        promoted["facts"]["external_independent_review_complete"] = True
        promoted.pop("review_request_hash")
        promoted = seal_strict_canonical_document(promoted, "review_request_hash")
        self.assertFalse(
            verify_static_presentation_external_independent_review_request_v1(
                promoted,
                self.registration,
            )
        )

    def test_valid_claim_is_bound_but_remains_unverified(self) -> None:
        self.assertEqual(self.intake["schema_version"], INTAKE_SCHEMA_VERSION)
        self.assertEqual(
            self.intake["status"],
            "LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN",
        )
        self.assertEqual(self.intake["intake_state"], "CLAIM_BOUND_UNVERIFIED")
        self.assertTrue(self.intake["facts"]["review_claim_bound"])
        self.assertFalse(self.intake["facts"]["external_independent_review_complete"])

    def test_intake_hashes_reviewer_labels_without_embedding_them(self) -> None:
        serialized = json.dumps(self.intake, sort_keys=True)
        self.assertNotIn(self.claim["reviewer_claim_id"], serialized)
        self.assertNotIn(self.claim["reviewer_process_id"], serialized)
        self.assertRegex(
            self.intake["source"]["reviewer_claim_id_sha256"],
            r"^[0-9a-f]{64}$",
        )
        self.assertFalse(self.intake["source"]["raw_review_claim_embedded"])

    def test_claim_missing_extra_blank_and_numeric_identifiers_are_unknown(self) -> None:
        variants = []
        missing = copy.deepcopy(self.claim)
        missing.pop("reviewer_claim_id")
        variants.append(missing)
        extra = copy.deepcopy(self.claim)
        extra["signature"] = "forged"
        variants.append(extra)
        blank = copy.deepcopy(self.claim)
        blank["reviewer_process_id"] = " "
        variants.append(blank)
        numeric = copy.deepcopy(self.claim)
        numeric["reviewer_claim_id"] = 1
        variants.append(numeric)
        for claim in variants:
            with self.subTest(claim=claim):
                intake = build_static_presentation_external_independent_review_claim_intake_v1(
                    self.request,
                    claim,
                    self.registration,
                )
                self.assertEqual(intake["status"], "UNKNOWN")

    def test_claim_cross_splice_and_independence_false_are_unknown(self) -> None:
        variants = []
        request_splice = copy.deepcopy(self.claim)
        request_splice["review_request_hash"] = "f" * 64
        variants.append(request_splice)
        target_splice = copy.deepcopy(self.claim)
        target_splice["target_manifest_hash"] = "e" * 64
        variants.append(target_splice)
        not_independent = copy.deepcopy(self.claim)
        not_independent["independence_claimed"] = False
        variants.append(not_independent)
        for claim in variants:
            with self.subTest(claim=claim):
                intake = build_static_presentation_external_independent_review_claim_intake_v1(
                    self.request,
                    claim,
                    self.registration,
                )
                self.assertEqual(intake["status"], "UNKNOWN")

    def test_rubric_false_missing_extra_and_bool_alias_are_unknown(self) -> None:
        key = next(iter(REVIEW_RUBRIC_KEYS))
        false_claim = copy.deepcopy(self.claim)
        false_claim["rubric_results"][key] = False
        missing = copy.deepcopy(self.claim)
        missing["rubric_results"].pop(key)
        extra = copy.deepcopy(self.claim)
        extra["rubric_results"]["compatibility_alias"] = True
        alias = copy.deepcopy(self.claim)
        alias["rubric_results"][key] = 1
        for claim in (false_claim, missing, extra, alias):
            with self.subTest(claim=claim):
                intake = build_static_presentation_external_independent_review_claim_intake_v1(
                    self.request,
                    claim,
                    self.registration,
                )
                self.assertEqual(intake["status"], "UNKNOWN")

    def test_tampered_request_prevents_claim_binding(self) -> None:
        request = copy.deepcopy(self.request)
        request["target_manifest_hash"] = "f" * 64
        intake = build_static_presentation_external_independent_review_claim_intake_v1(
            request,
            self.claim,
            self.registration,
        )
        self.assertEqual(intake["status"], "UNKNOWN")
        self.assertFalse(intake["facts"]["review_request_exactly_verified"])

    def test_cyclic_claim_fails_closed_to_unknown(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        intake = build_static_presentation_external_independent_review_claim_intake_v1(
            self.request,
            cyclic,
            self.registration,
        )
        self.assertEqual(intake["status"], "UNKNOWN")

    def test_intake_verifier_accepts_rebuild_and_rejects_promotion(self) -> None:
        self.assertTrue(
            verify_static_presentation_external_independent_review_claim_intake_v1(
                self.intake,
                self.request,
                self.claim,
                self.registration,
            )
        )
        promoted = copy.deepcopy(self.intake)
        promoted["facts"]["attestation_signature_verified"] = True
        promoted.pop("claim_intake_hash")
        promoted = seal_strict_canonical_document(promoted, "claim_intake_hash")
        self.assertFalse(
            verify_static_presentation_external_independent_review_claim_intake_v1(
                promoted,
                self.request,
                self.claim,
                self.registration,
            )
        )

    def test_request_and_intake_keep_all_blockers_and_authority_locked(self) -> None:
        for document in (self.request, self.intake):
            self.assertIn("REVIEWER_IDENTITY_UNAUTHENTICATED", document["blockers"])
            self.assertIn("ATTESTATION_SIGNATURE_ABSENT", document["blockers"])
            self.assertIn("REVIEW_REPLAY_DURABILITY_UNPROVEN", document["blockers"])
            self.assertIn(
                "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
                document["blockers"],
            )
            self.assertTrue(all(value is False for value in document["authority"].values()))

    def test_documents_have_no_promotional_copy(self) -> None:
        serialized = json.dumps(
            {"request": self.request, "intake": self.intake},
            sort_keys=True,
        )
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                serialized,
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.intake["facts"]["profitability_proven"])

    def test_request_and_intake_are_deterministic_native_json(self) -> None:
        self.assertEqual(
            self.request,
            build_static_presentation_external_independent_review_request_v1(
                self.registration
            ),
        )
        self.assertEqual(
            self.intake,
            build_static_presentation_external_independent_review_claim_intake_v1(
                self.request,
                self.claim,
                self.registration,
            ),
        )
        self.assertEqual(json.loads(json.dumps(self.request)), self.request)


if __name__ == "__main__":
    unittest.main()
