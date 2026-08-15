from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from urllib.parse import urlparse


PROVIDER_GOVERNANCE_SCHEMA_VERSION = "provider-governance-v2"
PROVIDER_REVIEW_SCHEMA_VERSION = "provider-governance-review-v2"
PROVIDER_APPROVAL_RECEIPT_SCHEMA_VERSION = "provider-governance-approval-receipt-v1"
REDISTRIBUTION_STATUSES = {
    "ALLOWED",
    "ALLOWED_WITH_CONDITIONS",
    "PROHIBITED",
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _clean_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_reference(value: Any) -> bool:
    text = str(value or "").strip()
    if text.startswith("urn:"):
        return len(text) > 4
    parsed = urlparse(text)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _positive_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if parsed > 0 else 0


def _normalize_provider_ids(provider_ids: list[str]) -> list[str]:
    return sorted({str(item or "").strip().lower() for item in provider_ids or [] if str(item or "").strip()})


def build_provider_approval_receipt(
    *,
    provider_id: str,
    terms_ref: str,
    terms_sha256: str,
    terms_version: str,
    reviewed_at: str,
    review_expires_at: str,
    local_storage_status: str,
    redistribution_status: str,
    quota_model: str,
    request_limit: int,
    quota_window_seconds: int,
    retry_policy_id: str,
    reviewer_id: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": PROVIDER_APPROVAL_RECEIPT_SCHEMA_VERSION,
        "decision": "APPROVED",
        "provider_id": str(provider_id or "").strip().lower(),
        "terms_ref": str(terms_ref or "").strip(),
        "terms_sha256": str(terms_sha256 or "").strip().lower(),
        "terms_version": str(terms_version or "").strip(),
        "reviewed_at": _clean_timestamp(reviewed_at),
        "review_expires_at": _clean_timestamp(review_expires_at),
        "local_storage_status": str(local_storage_status or "").strip().upper(),
        "redistribution_status": str(redistribution_status or "").strip().upper(),
        "quota_model": str(quota_model or "").strip().upper(),
        "request_limit": _positive_int(request_limit),
        "quota_window_seconds": _positive_int(quota_window_seconds),
        "retry_policy_id": str(retry_policy_id or "").strip(),
        "reviewer_id": str(reviewer_id or "").strip(),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["receipt_hash"] = _canonical_hash(payload)
    return payload


def required_provider_ids_from_evidence(
    adjustments: dict[str, Any],
    revisions: dict[str, Any],
) -> list[str]:
    providers = {
        str(dict(item or {}).get("source") or "").strip().lower()
        for item in adjustments.values()
        if isinstance(item, dict)
    }
    for revision in revisions.values():
        if not isinstance(revision, dict):
            continue
        for record in revision.get("cross_source") or []:
            if not isinstance(record, dict):
                continue
            providers.add(str(record.get("primary_provider") or "").strip().lower())
            providers.add(str(record.get("secondary_provider") or "").strip().lower())
    return sorted(item for item in providers if item)


def build_provider_review_record(
    *,
    provider_id: str,
    terms_ref: str,
    terms_sha256: str,
    terms_version: str,
    reviewed_at: str,
    review_expires_at: str,
    local_storage_status: str,
    redistribution_status: str,
    quota_model: str,
    request_limit: int,
    quota_window_seconds: int,
    retry_policy_id: str,
    reviewer_id: str,
    approval_receipt: dict[str, Any] | None,
    approval_receipt_sha256: str,
    assessed_at: str,
) -> dict[str, Any]:
    provider = str(provider_id or "").strip().lower()
    terms_reference = str(terms_ref or "").strip()
    terms_hash = str(terms_sha256 or "").strip().lower()
    version = str(terms_version or "").strip()
    reviewed = _clean_timestamp(reviewed_at)
    expires = _clean_timestamp(review_expires_at)
    assessed = _clean_timestamp(assessed_at)
    storage = str(local_storage_status or "").strip().upper()
    redistribution = str(redistribution_status or "").strip().upper()
    quota = str(quota_model or "").strip().upper()
    limit = _positive_int(request_limit)
    window = _positive_int(quota_window_seconds)
    retry_policy = str(retry_policy_id or "").strip()
    reviewer = str(reviewer_id or "").strip()
    receipt = dict(approval_receipt or {})
    receipt_hash = str(approval_receipt_sha256 or "").strip().lower()
    blockers: list[str] = []
    if not provider:
        blockers.append("provider_id_missing")
    if not _valid_reference(terms_reference):
        blockers.append("provider_terms_reference_invalid")
    if not _valid_sha256(terms_hash):
        blockers.append("provider_terms_hash_invalid")
    if not version:
        blockers.append("provider_terms_version_missing")
    if not reviewed or not expires or not assessed:
        blockers.append("provider_review_timestamp_invalid")
    elif reviewed > assessed:
        blockers.append("provider_review_after_assessment")
    elif expires <= assessed:
        blockers.append("provider_review_expired")
    if storage != "ALLOWED":
        blockers.append(f"provider_local_storage_not_approved:{storage or '--'}")
    if redistribution not in REDISTRIBUTION_STATUSES:
        blockers.append(f"provider_redistribution_status_invalid:{redistribution or '--'}")
    if not quota or not limit or not window:
        blockers.append("provider_quota_contract_incomplete")
    if not retry_policy:
        blockers.append("provider_retry_policy_missing")
    if not reviewer or not _valid_sha256(receipt_hash):
        blockers.append("provider_approval_receipt_invalid")
    expected_receipt = build_provider_approval_receipt(
        provider_id=provider,
        terms_ref=terms_reference,
        terms_sha256=terms_hash,
        terms_version=version,
        reviewed_at=reviewed,
        review_expires_at=expires,
        local_storage_status=storage,
        redistribution_status=redistribution,
        quota_model=quota,
        request_limit=limit,
        quota_window_seconds=window,
        retry_policy_id=retry_policy,
        reviewer_id=reviewer,
    )
    if not receipt:
        blockers.append("provider_approval_receipt_payload_missing")
    elif receipt != expected_receipt or receipt_hash != str(receipt.get("receipt_hash") or ""):
        blockers.append("provider_approval_receipt_payload_invalid")
    payload = {
        "schema_version": PROVIDER_REVIEW_SCHEMA_VERSION,
        "provider_id": provider,
        "status": "PASS" if not blockers else "NOT_ASSESSED",
        "blockers": blockers,
        "terms_ref": terms_reference,
        "terms_sha256": terms_hash,
        "terms_version": version,
        "reviewed_at": reviewed,
        "review_expires_at": expires,
        "local_storage_status": storage,
        "redistribution_status": redistribution,
        "quota_model": quota,
        "request_limit": limit,
        "quota_window_seconds": window,
        "retry_policy_id": retry_policy,
        "reviewer_id": reviewer,
        "approval_receipt": receipt,
        "approval_receipt_sha256": receipt_hash,
        "assessed_at": assessed,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["review_hash"] = _canonical_hash(payload)
    return payload


def _rebuild_review(record: dict[str, Any], *, assessed_at: str) -> dict[str, Any]:
    return build_provider_review_record(
        provider_id=str(record.get("provider_id") or ""),
        terms_ref=str(record.get("terms_ref") or ""),
        terms_sha256=str(record.get("terms_sha256") or ""),
        terms_version=str(record.get("terms_version") or ""),
        reviewed_at=str(record.get("reviewed_at") or ""),
        review_expires_at=str(record.get("review_expires_at") or ""),
        local_storage_status=str(record.get("local_storage_status") or ""),
        redistribution_status=str(record.get("redistribution_status") or ""),
        quota_model=str(record.get("quota_model") or ""),
        request_limit=record.get("request_limit"),
        quota_window_seconds=record.get("quota_window_seconds"),
        retry_policy_id=str(record.get("retry_policy_id") or ""),
        reviewer_id=str(record.get("reviewer_id") or ""),
        approval_receipt=(
            dict(record.get("approval_receipt") or {})
            if isinstance(record.get("approval_receipt"), dict)
            else {}
        ),
        approval_receipt_sha256=str(record.get("approval_receipt_sha256") or ""),
        assessed_at=assessed_at,
    )


def build_provider_governance_contract(
    *,
    provider_ids: list[str],
    reviews: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    providers = _normalize_provider_ids(provider_ids)
    timestamp = _clean_timestamp(generated_at)
    normalized_reviews = [
        _rebuild_review(dict(item), assessed_at=timestamp)
        for item in reviews or []
        if isinstance(item, dict)
    ]
    normalized_reviews.sort(key=lambda item: str(item.get("provider_id") or ""))
    blockers: list[str] = []
    if not timestamp:
        blockers.append("provider_governance_generated_at_invalid")
    if not providers:
        blockers.append("provider_governance_provider_ids_missing")
    review_ids = [str(item.get("provider_id") or "") for item in normalized_reviews]
    if len(review_ids) != len(set(review_ids)):
        blockers.append("provider_governance_duplicate_reviews")
    outside = sorted(set(review_ids) - set(providers))
    if outside:
        blockers.append(f"provider_governance_unexpected_reviews:{','.join(outside)}")
    by_provider = {str(item.get("provider_id") or ""): item for item in normalized_reviews}
    for provider in providers:
        review = by_provider.get(provider)
        if not review:
            blockers.append(f"provider_review_missing:{provider}")
        elif review.get("status") != "PASS":
            blockers.append(f"provider_review_not_approved:{provider}")
    approved = bool(providers) and not blockers
    payload = {
        "schema_version": PROVIDER_GOVERNANCE_SCHEMA_VERSION,
        "status": "APPROVED" if approved else "NOT_ASSESSED",
        "blockers": blockers,
        "generated_at": timestamp,
        "required_provider_ids": providers,
        "provider_reviews": normalized_reviews,
        "provider_review_hashes": {
            provider: str(by_provider.get(provider, {}).get("review_hash") or "")
            for provider in providers
        },
        "license_review_status": "PASS" if approved else "NOT_ASSESSED",
        "rate_limit_policy_status": "PASS" if approved else "NOT_ASSESSED",
        "approved_for_research_storage": approved,
        "manual_review_required": not approved,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["contract_hash"] = _canonical_hash(payload)
    return payload


def build_unassessed_provider_governance_contract(
    *,
    provider_ids: list[str],
    generated_at: str,
) -> dict[str, Any]:
    return build_provider_governance_contract(
        provider_ids=provider_ids,
        reviews=[],
        generated_at=generated_at,
    )


def verify_provider_governance_contract(
    contract: dict[str, Any],
    *,
    required_providers: list[str] | None = None,
    verification_at: str = "",
) -> dict[str, Any]:
    contract = dict(contract) if isinstance(contract, dict) else {}
    payload = dict(contract)
    expected_hash = str(payload.pop("contract_hash", "") or "")
    blockers: list[str] = []
    if str(contract.get("schema_version") or "") != PROVIDER_GOVERNANCE_SCHEMA_VERSION:
        blockers.append("provider_governance_schema_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("provider_governance_hash_invalid")
    provider_value = contract.get("required_provider_ids")
    if not isinstance(provider_value, list):
        blockers.append("provider_governance_provider_ids_type_invalid")
        provider_value = []
    providers = _normalize_provider_ids(list(provider_value))
    requested = _normalize_provider_ids(list(required_providers or providers))
    if providers != list(provider_value):
        blockers.append("provider_governance_provider_ids_not_normalized")
    missing = sorted(set(requested) - set(providers))
    if missing:
        blockers.append(f"provider_governance_required_providers_missing:{','.join(missing)}")
    reviews = contract.get("provider_reviews")
    if not isinstance(reviews, list):
        blockers.append("provider_governance_reviews_type_invalid")
        reviews = []
    rebuilt = build_provider_governance_contract(
        provider_ids=providers,
        reviews=[dict(item) for item in reviews if isinstance(item, dict)],
        generated_at=str(contract.get("generated_at") or ""),
    )
    semantic_fields = (
        "status",
        "blockers",
        "generated_at",
        "required_provider_ids",
        "provider_reviews",
        "provider_review_hashes",
        "license_review_status",
        "rate_limit_policy_status",
        "approved_for_research_storage",
        "manual_review_required",
    )
    for field in semantic_fields:
        if contract.get(field) != rebuilt.get(field):
            blockers.append(f"provider_governance_semantic_mismatch:{field}")
    verification_time = _clean_timestamp(verification_at)
    freshness_blockers: list[str] = []
    if rebuilt.get("approved_for_research_storage") is True:
        if not verification_time:
            freshness_blockers.append("provider_governance_verification_time_missing")
        else:
            generated_at = _clean_timestamp(rebuilt.get("generated_at"))
            if generated_at and verification_time < generated_at:
                freshness_blockers.append("provider_governance_verified_before_generation")
            for review in rebuilt.get("provider_reviews") or []:
                provider = str(review.get("provider_id") or "--")
                reviewed_at = _clean_timestamp(review.get("reviewed_at"))
                expires_at = _clean_timestamp(review.get("review_expires_at"))
                if reviewed_at and verification_time < reviewed_at:
                    freshness_blockers.append(f"provider_review_not_yet_effective:{provider}")
                if not expires_at or expires_at <= verification_time:
                    freshness_blockers.append(f"provider_review_expired_at_verification:{provider}")
    blockers.extend(freshness_blockers)
    if (
        contract.get("research_only") is not True
        or contract.get("paper_authorized") is not False
        or contract.get("live_order_allowed") is not False
    ):
        blockers.append("provider_governance_has_execution_authority")
    approved = rebuilt.get("approved_for_research_storage") is True and not blockers
    freshness_status = (
        "PASS"
        if approved
        else "EXPIRED"
        if any("expired_at_verification" in item for item in freshness_blockers)
        else "NOT_ASSESSED"
    )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "contract_hash": expected_hash,
        "governance_status": "APPROVED" if approved else freshness_status,
        "approved_for_research_storage": approved,
        "license_review_status": "PASS" if approved else freshness_status,
        "rate_limit_policy_status": "PASS" if approved else freshness_status,
        "approval_freshness_status": freshness_status,
        "verification_at": verification_time,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
