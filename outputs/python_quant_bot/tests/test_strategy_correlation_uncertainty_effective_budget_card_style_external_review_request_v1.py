from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import unittest

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1 as subject,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NonNativeDocument(dict):
    pass


class CorrelationEffectiveBudgetCardStyleExternalReviewRequestV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.request = (
            subject.build_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1()
        )

    def test_request_binds_target_and_awaits_authenticated_style_review(self) -> None:
        self.assertEqual(
            self.request["schema_version"], subject.REQUEST_SCHEMA_VERSION
        )
        self.assertEqual(
            self.request["status"],
            "AWAITING_EXTERNAL_INDEPENDENT_STYLE_REVIEW",
        )
        self.assertEqual(
            self.request["request_state"],
            "EXACT_CARD_STYLE_TARGET_BOUND_AWAITING_AUTHENTICATED_EXTERNAL_REVIEW",
        )

    def test_target_manifest_hash_is_exact(self) -> None:
        self.assertEqual(
            self.request["target_manifest_hash"],
            strict_canonical_hash(self.request["review_target"]),
        )

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

    def test_protected_host_preimages_match_and_remain_unmodified(self) -> None:
        expected = subject.expected_protected_host_preimages_v1()
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)
        permission = self.request["review_target"]["permission_baseline"]
        self.assertFalse(permission["host_assets_modified"])
        self.assertFalse(permission["route_registered"])
        self.assertFalse(permission["dom_mounted"])

    def test_asset_pair_contract_pins_card_style_namespace_and_stage_order(self) -> None:
        pair = self.request["review_target"]["asset_pair_contract"]
        self.assertEqual(pair["card_schema_version"], subject.CARD_SCHEMA_VERSION)
        self.assertEqual(
            pair["card_static_fingerprint"], subject.CARD_STATIC_FINGERPRINT
        )
        self.assertEqual(pair["style_filename"], subject.STYLE_FILENAME)
        self.assertEqual(pair["style_namespace"], subject.STYLE_NAMESPACE)
        self.assertEqual(pair["ordered_stages"], list(subject.ORDERED_STAGES))
        self.assertEqual(pair["pair_state"], "UNMOUNTED_REVIEW_TARGET_ONLY")

    def test_local_counts_are_static_no_browser_declarations_only(self) -> None:
        baseline = self.request["review_target"][
            "declared_local_contract_baseline"
        ]
        self.assertEqual(
            baseline["evidence_kind"], "PURE_STATIC_AND_SYNTHETIC_NO_BROWSER"
        )
        self.assertEqual(baseline["card_contract_case_count"], 14)
        self.assertEqual(baseline["style_contract_case_count"], 13)
        self.assertEqual(baseline["combined_case_count"], 27)
        self.assertFalse(baseline["browser_visual_review_performed"])
        self.assertFalse(baseline["screen_reader_review_performed"])
        self.assertFalse(baseline["native_zoom_review_performed"])

    def test_style_characteristics_are_declarations_not_review_completion(self) -> None:
        characteristics = self.request["review_target"]["style_characteristics"]
        self.assertTrue(all(characteristics.values()))
        facts = self.request["facts"]
        self.assertFalse(facts["external_style_review_complete"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["dom_mounted"])

    def test_rubric_is_exact_and_requires_external_attestation(self) -> None:
        self.assertEqual(set(self.request["rubric"]), set(subject.REVIEW_RUBRIC_KEYS))
        self.assertEqual(len(self.request["rubric"]), 11)
        self.assertTrue(
            all(
                value == "REVIEWER_MUST_ATTEST_TRUE"
                for value in self.request["rubric"].values()
            )
        )

    def test_request_never_claims_delivery_review_or_asset_registration(self) -> None:
        facts = self.request["facts"]
        self.assertFalse(facts["review_request_delivered"])
        self.assertFalse(facts["reviewer_identity_authenticated"])
        self.assertFalse(facts["attestation_signature_verified"])
        self.assertFalse(facts["external_style_review_complete"])
        self.assertFalse(facts["asset_pair_preregistered"])
        self.assertTrue(
            all(value is False for value in self.request["authority"].values())
        )

    def test_review_activation_and_mount_blockers_remain_explicit(self) -> None:
        blockers = self.request["blockers"]
        self.assertIn("REVIEW_REQUEST_DELIVERY_NOT_AUTHORIZED", blockers)
        self.assertIn("REVIEWER_IDENTITY_UNAUTHENTICATED", blockers)
        self.assertIn("ATTESTATION_SIGNATURE_ABSENT", blockers)
        self.assertIn("EXTERNAL_STYLE_REVIEW_NOT_COMPLETED", blockers)
        self.assertIn(
            "ASSET_PAIR_PREREGISTRATION_BLOCKED_PENDING_REVIEW", blockers
        )
        self.assertIn("BROWSER_REVIEW_NOT_AUTHORIZED", blockers)
        self.assertIn("HOST_MOUNT_NOT_AUTHORIZED", blockers)

    def test_exact_verifier_accepts_rebuild_and_rejects_resealed_promotion(self) -> None:
        self.assertTrue(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                self.request
            )
        )
        promoted = deepcopy(self.request)
        promoted["facts"]["external_style_review_complete"] = True
        promoted["authority"]["asset_pair_preregistration_allowed"] = True
        promoted.pop("review_request_hash")
        promoted = seal_strict_canonical_document(
            promoted, "review_request_hash"
        )
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                promoted
            )
        )

    def test_target_hash_substitution_is_rejected_even_when_resealed(self) -> None:
        tampered = deepcopy(self.request)
        first_path = next(iter(subject.expected_review_artifact_hashes_v1()))
        tampered["review_target"]["review_artifact_sha256"][first_path] = "f" * 64
        tampered["target_manifest_hash"] = strict_canonical_hash(
            tampered["review_target"]
        )
        tampered.pop("review_request_hash")
        tampered = seal_strict_canonical_document(
            tampered, "review_request_hash"
        )
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                tampered
            )
        )

    def test_non_native_cyclic_and_extra_documents_fail_exact_verification(self) -> None:
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                NonNativeDocument(self.request)
            )
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                cyclic
            )
        )
        extra = deepcopy(self.request)
        extra["compatibility_alias"] = True
        self.assertFalse(
            subject.verify_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1(
                extra
            )
        )

    def test_hash_maps_are_fresh_copies(self) -> None:
        artifacts = subject.expected_review_artifact_hashes_v1()
        protected = subject.expected_protected_host_preimages_v1()
        artifacts.clear()
        protected.clear()
        self.assertEqual(len(subject.expected_review_artifact_hashes_v1()), 8)
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
        self.assertFalse(self.request["facts"]["raw_markup_embedded"])
        self.assertFalse(self.request["facts"]["raw_stylesheet_embedded"])

    def test_request_is_deterministic_native_json(self) -> None:
        rebuilt = (
            subject.build_strategy_correlation_uncertainty_effective_budget_card_style_external_review_request_v1()
        )
        self.assertEqual(self.request, rebuilt)
        self.assertEqual(json.loads(json.dumps(self.request)), self.request)


if __name__ == "__main__":
    unittest.main()
