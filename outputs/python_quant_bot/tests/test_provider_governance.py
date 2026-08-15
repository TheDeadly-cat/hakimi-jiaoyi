from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.provider_governance import (
    build_provider_approval_receipt,
    build_provider_governance_contract,
    build_provider_review_record,
    build_unassessed_provider_governance_contract,
    verify_provider_governance_contract,
)


GENERATED_AT = "2026-08-03T00:00:00Z"


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def review(provider: str) -> dict[str, object]:
    terms_ref = f"https://example.test/{provider}/terms"
    terms_sha256 = hashlib.sha256(f"{provider}-terms".encode("utf-8")).hexdigest()
    receipt = build_provider_approval_receipt(
        provider_id=provider,
        terms_ref=terms_ref,
        terms_sha256=terms_sha256,
        terms_version="2026-01",
        reviewed_at="2026-07-01T00:00:00Z",
        review_expires_at="2027-07-01T00:00:00Z",
        local_storage_status="ALLOWED",
        redistribution_status="PROHIBITED",
        quota_model="FIXED_WINDOW",
        request_limit=100,
        quota_window_seconds=60,
        retry_policy_id="bounded-exponential-v1",
        reviewer_id="test-compliance-reviewer",
    )
    return build_provider_review_record(
        provider_id=provider,
        terms_ref=terms_ref,
        terms_sha256=terms_sha256,
        terms_version="2026-01",
        reviewed_at="2026-07-01T00:00:00Z",
        review_expires_at="2027-07-01T00:00:00Z",
        local_storage_status="ALLOWED",
        redistribution_status="PROHIBITED",
        quota_model="FIXED_WINDOW",
        request_limit=100,
        quota_window_seconds=60,
        retry_policy_id="bounded-exponential-v1",
        reviewer_id="test-compliance-reviewer",
        approval_receipt=receipt,
        approval_receipt_sha256=str(receipt["receipt_hash"]),
        assessed_at=GENERATED_AT,
    )


class ProviderGovernanceTests(unittest.TestCase):
    def test_malformed_governance_contract_fails_closed_without_raising(self) -> None:
        audit = verify_provider_governance_contract([], required_providers=["futu"])

        self.assertEqual(audit["status"], "BLOCK")

    def test_unassessed_contract_has_integrity_without_approval(self) -> None:
        contract = build_unassessed_provider_governance_contract(
            provider_ids=["yahoo", "futu"],
            generated_at=GENERATED_AT,
        )

        audit = verify_provider_governance_contract(
            contract,
            required_providers=["futu", "yahoo"],
            verification_at=GENERATED_AT,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["governance_status"], "NOT_ASSESSED")
        self.assertFalse(audit["approved_for_research_storage"])

    def test_complete_current_reviews_are_approved(self) -> None:
        contract = build_provider_governance_contract(
            provider_ids=["futu", "yahoo"],
            reviews=[review("futu"), review("yahoo")],
            generated_at=GENERATED_AT,
        )

        audit = verify_provider_governance_contract(
            contract,
            required_providers=["futu", "yahoo"],
            verification_at=GENERATED_AT,
        )

        self.assertEqual(contract["status"], "APPROVED")
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(audit["approved_for_research_storage"])

    def test_bare_pass_strings_are_not_a_governance_contract(self) -> None:
        audit = verify_provider_governance_contract({
            "license_review_status": "PASS",
            "rate_limit_policy_status": "PASS",
        }, required_providers=["futu"])

        self.assertEqual(audit["status"], "BLOCK")
        self.assertFalse(audit["approved_for_research_storage"])

    def test_synthetic_receipt_hash_without_receipt_payload_is_rejected(self) -> None:
        record = build_provider_review_record(
            provider_id="futu",
            terms_ref="https://example.test/futu/terms",
            terms_sha256="a" * 64,
            terms_version="2026-01",
            reviewed_at="2026-07-01T00:00:00Z",
            review_expires_at="2027-07-01T00:00:00Z",
            local_storage_status="ALLOWED",
            redistribution_status="PROHIBITED",
            quota_model="FIXED_WINDOW",
            request_limit=100,
            quota_window_seconds=60,
            retry_policy_id="bounded-exponential-v1",
            reviewer_id="test-compliance-reviewer",
            approval_receipt=None,
            approval_receipt_sha256="b" * 64,
            assessed_at=GENERATED_AT,
        )

        self.assertEqual(record["status"], "NOT_ASSESSED")
        self.assertIn("provider_approval_receipt_payload_missing", record["blockers"])

    def test_resealed_invalid_terms_reference_cannot_keep_approval(self) -> None:
        contract = build_provider_governance_contract(
            provider_ids=["futu"],
            reviews=[review("futu")],
            generated_at=GENERATED_AT,
        )
        provider_review = contract["provider_reviews"][0]
        provider_review["terms_ref"] = "local-file-without-authority"
        provider_review.pop("review_hash")
        provider_review["review_hash"] = canonical_hash(provider_review)
        contract["provider_review_hashes"]["futu"] = provider_review["review_hash"]
        contract.pop("contract_hash")
        contract["contract_hash"] = canonical_hash(contract)

        audit = verify_provider_governance_contract(
            contract,
            required_providers=["futu"],
            verification_at=GENERATED_AT,
        )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertFalse(audit["approved_for_research_storage"])
        self.assertTrue(any(
            item.startswith("provider_governance_semantic_mismatch")
            for item in audit["blockers"]
        ))

    def test_required_provider_not_covered_by_contract_is_blocked(self) -> None:
        contract = build_provider_governance_contract(
            provider_ids=["futu"],
            reviews=[review("futu")],
            generated_at=GENERATED_AT,
        )

        audit = verify_provider_governance_contract(
            contract,
            required_providers=["futu", "yahoo"],
            verification_at=GENERATED_AT,
        )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("provider_governance_required_providers_missing:yahoo", audit["blockers"])

    def test_approval_is_rejected_after_review_expiry(self) -> None:
        contract = build_provider_governance_contract(
            provider_ids=["futu"],
            reviews=[review("futu")],
            generated_at=GENERATED_AT,
        )

        audit = verify_provider_governance_contract(
            contract,
            required_providers=["futu"],
            verification_at="2027-07-01T00:00:00Z",
        )

        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["approval_freshness_status"], "EXPIRED")
        self.assertIn("provider_review_expired_at_verification:futu", audit["blockers"])


if __name__ == "__main__":
    unittest.main()
