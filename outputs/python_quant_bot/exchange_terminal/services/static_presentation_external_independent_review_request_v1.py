"""Build a deterministic external-review request and unauthenticated claim intake."""

from __future__ import annotations

import math
import re
from typing import Any

from exchange_terminal.services.static_presentation_unmounted_render_review_asset_registration_v1 import (
    SCHEMA_VERSION as ASSET_REGISTRATION_SCHEMA_VERSION,
    STATIC_FINGERPRINT as ASSET_REGISTRATION_STATIC_FINGERPRINT,
    build_static_presentation_unmounted_render_review_asset_registration_v1,
    verify_static_presentation_unmounted_render_review_asset_registration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "static-presentation-external-independent-review-request-v1"
)
CLAIM_SCHEMA_VERSION = "static-presentation-external-independent-review-claim-v1"
INTAKE_SCHEMA_VERSION = (
    "static-presentation-external-independent-review-claim-intake-v1"
)
STATIC_FINGERPRINT = (
    "20260823-static-presentation-external-review-request-v1-unverified-lock-1"
)

ASSET_REGISTRATION_HASH = (
    "0fd4a8390690881b6a78ccd9c631f52231b109b84db356344951c140c7c0561b"
)
ASSET_MANIFEST_HASH = (
    "1edc9135c83886f871ee307fa079a9feb1f8e61eeae6cfe1f776f301a7aa9456"
)
ASSET_REGISTRATION_IMPLEMENTATION_SHA256 = (
    "47e359e0393b208f826f3cb9c276694f68e3343d8761f9386cb0353f295f3fd2"
)
ASSET_REGISTRATION_TEST_SHA256 = (
    "198f9e4cc82d5f471c6c871ef2c145f9a16ef23a3171f5e1f5d5c4680ae4ec64"
)
ADR0297_SHA256 = (
    "bc47b8908a651459300eb102b000f222808529dde2a376227ea4cc51378936bb"
)
REVIEW_IMPLEMENTATION_SHA256 = (
    "7fe82458e3d9b2e2df853a8203b4f3cea82a4edf5f957bbb0a122a09a1eccc44"
)
REVIEW_NODE_TEST_SHA256 = (
    "e97745d653a71e8b2d36b56a6dfe09ffad553da7290e783b3f0b4b357f7abf63"
)
ADR0296_SHA256 = (
    "6b5b9fe946d61d385f7a8ccaae90afd2e103f6321852dc527954dff950ce7a87"
)

CLEAR_REVIEW_RECEIPT_HASH = (
    "2c86b3ca749cacbe6bb8292af854d8826282e0d705310343591a0f7274b901df"
)
CLEAR_MARKUP_SHA256 = (
    "77653e0f647a5ffa2375ba7498a7e5969ddce6fb72d281f506a2fdc507ac64c7"
)
BLOCK_REVIEW_RECEIPT_HASH = (
    "9964ee8d9aace7be17cbba6b5ebe79198904d7d9f0b14e3d4bf731e01471da9a"
)
BLOCK_MARKUP_SHA256 = (
    "cae89e02027c53f773d881a9c01fd6d75ded2cf2e7703c427b27f47d942aed9e"
)
UNKNOWN_REVIEW_RECEIPT_HASH = (
    "d1252f088c633bc8a6b3e5c06b6bd723106865a1df960dd85b73e14805dad272"
)

REVIEW_RUBRIC_KEYS = frozenset({
    "app_fragment_unmounted_and_no_dom",
    "asset_registration_exact",
    "clear_block_unknown_behavior_exact",
    "host_patch_plan_matches_pinned_preimages",
    "neutral_stage_order_and_copy",
    "no_profitability_or_ready_claim",
    "no_raw_source_or_markup_leak",
    "permission_and_trading_authority_locked",
    "production_test_dependency_separation_exact",
})
_CLAIM_KEYS = frozenset({
    "schema_version",
    "review_request_hash",
    "target_manifest_hash",
    "reviewer_claim_id",
    "reviewer_process_id",
    "independence_claimed",
    "rubric_results",
})
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_AUTHORITY_KEYS = (
    "attestation_signature_acceptance_allowed",
    "browser_execution_allowed",
    "current_admission_allowed",
    "dom_mount_allowed",
    "external_review_completion_allowed",
    "host_asset_write_allowed",
    "live_order_allowed",
    "paper_authorized",
    "review_promotion_allowed",
    "route_registration_allowed",
    "runtime_asset_loading_allowed",
    "writer_allowed",
)
_BASE_BLOCKERS = [
    "REVIEWER_IDENTITY_UNAUTHENTICATED",
    "REVIEWER_PROCESS_UNAUTHENTICATED",
    "ATTESTATION_SIGNATURE_ABSENT",
    "REVIEW_REPLAY_DURABILITY_UNPROVEN",
    "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
]


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite values are not permitted")
        return value
    if type(value) not in {dict, list}:
        raise TypeError("review documents require native JSON values")
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise ValueError("cyclic review documents are not permitted")
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError("review document keys must be strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _review_target() -> dict[str, Any]:
    return {
        "asset_registration": {
            "schema_version": ASSET_REGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": ASSET_REGISTRATION_STATIC_FINGERPRINT,
            "asset_registration_hash": ASSET_REGISTRATION_HASH,
            "asset_manifest_hash": ASSET_MANIFEST_HASH,
            "implementation_sha256": ASSET_REGISTRATION_IMPLEMENTATION_SHA256,
            "test_sha256": ASSET_REGISTRATION_TEST_SHA256,
            "adr_sha256": ADR0297_SHA256,
        },
        "review_assets": {
            "implementation_sha256": REVIEW_IMPLEMENTATION_SHA256,
            "node_test_sha256": REVIEW_NODE_TEST_SHA256,
            "adr_sha256": ADR0296_SHA256,
        },
        "local_behavior_evidence": {
            "evidence_kind": "PURE_SYNTHETIC_NO_DOM_FIXTURE",
            "clear": {
                "source_status": "PASS",
                "status_label": "LOCAL CLEAR",
                "review_receipt_hash": CLEAR_REVIEW_RECEIPT_HASH,
                "markup_sha256": CLEAR_MARKUP_SHA256,
                "markup_length": 3419,
            },
            "block": {
                "source_status": "BLOCK",
                "status_label": "LOCAL BLOCK",
                "review_receipt_hash": BLOCK_REVIEW_RECEIPT_HASH,
                "markup_sha256": BLOCK_MARKUP_SHA256,
                "markup_length": 3443,
            },
            "unknown": {
                "source_status": "UNKNOWN",
                "status_label": "SOURCE UNKNOWN",
                "review_receipt_hash": UNKNOWN_REVIEW_RECEIPT_HASH,
                "markup_sha256": None,
                "markup_length": None,
            },
        },
        "permission_baseline": {
            "external_independent_review_complete": False,
            "host_patch_applied": False,
            "browser_visual_review_performed": False,
            "dom_mounted": False,
            "current_activated": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "profitability_proven": False,
        },
    }


def _registration_exact(document: Any) -> bool:
    return (
        type(document) is dict
        and verify_static_presentation_unmounted_render_review_asset_registration_v1(
            document
        )
        and document.get("asset_registration_hash") == ASSET_REGISTRATION_HASH
        and document.get("asset_manifest_hash") == ASSET_MANIFEST_HASH
        and document.get("status") == "BLOCKED"
        and document.get("facts", {}).get(
            "external_independent_review_complete"
        )
        is False
        and all(value is None for value in document.get("host_plan", {}).values())
        and all(value is False for value in document.get("authority", {}).values())
    )


def build_static_presentation_external_independent_review_request_v1(
    asset_registration_document: Any,
) -> dict[str, Any]:
    try:
        registration = _plain_json_snapshot(asset_registration_document)
    except Exception:
        registration = None
    registration_exact = _registration_exact(registration)
    target = _review_target() if registration_exact else None
    target_hash = strict_canonical_hash(target) if target is not None else None
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
            if registration_exact
            else "UNKNOWN"
        ),
        "request_state": (
            "EXACT_REVIEW_TARGET_BOUND_AWAITING_EXTERNAL_REVIEW"
            if registration_exact
            else "UNKNOWN"
        ),
        "review_target": target,
        "target_manifest_hash": target_hash,
        "rubric": {
            key: "REVIEWER_MUST_ATTEST_TRUE"
            for key in sorted(REVIEW_RUBRIC_KEYS)
        },
        "facts": {
            "asset_registration_exactly_verified": registration_exact,
            "review_target_hashes_bound": registration_exact,
            "local_behavior_evidence_hashes_bound": registration_exact,
            "review_target_embedded": registration_exact,
            "raw_host_sources_embedded": False,
            "raw_envelope_embedded": False,
            "raw_source_candidate_embedded": False,
            "raw_markup_embedded": False,
            "reviewer_identity_authenticated": False,
            "reviewer_process_authenticated": False,
            "attestation_signature_verified": False,
            "review_replay_durability_proven": False,
            "descriptor_content_review_observed_by_system": False,
            "external_independent_review_complete": False,
            "host_patch_applied": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(_BASE_BLOCKERS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "review_request_hash")


def verify_static_presentation_external_independent_review_request_v1(
    document: Any,
    asset_registration_document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = build_static_presentation_external_independent_review_request_v1(
            asset_registration_document
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


def _clean_identifier(value: Any) -> str | None:
    if type(value) is not str or value != value.strip():
        return None
    return value if _IDENTIFIER_RE.fullmatch(value) is not None else None


def _claim_exact(claim: Any, request: Any) -> bool:
    if (
        type(claim) is not dict
        or frozenset(claim) != _CLAIM_KEYS
        or claim.get("schema_version") != CLAIM_SCHEMA_VERSION
        or type(request) is not dict
        or request.get("status") != "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
        or claim.get("review_request_hash") != request.get("review_request_hash")
        or claim.get("target_manifest_hash")
        != request.get("target_manifest_hash")
        or _clean_identifier(claim.get("reviewer_claim_id")) is None
        or _clean_identifier(claim.get("reviewer_process_id")) is None
        or claim.get("independence_claimed") is not True
    ):
        return False
    rubric = claim.get("rubric_results")
    return (
        type(rubric) is dict
        and frozenset(rubric) == REVIEW_RUBRIC_KEYS
        and all(type(value) is bool and value is True for value in rubric.values())
    )


def build_static_presentation_external_independent_review_claim_intake_v1(
    review_request_document: Any,
    review_claim: Any,
    asset_registration_document: Any,
) -> dict[str, Any]:
    try:
        request = _plain_json_snapshot(review_request_document)
    except Exception:
        request = None
    try:
        claim = _plain_json_snapshot(review_claim)
    except Exception:
        claim = None
    request_exact = (
        request is not None
        and verify_static_presentation_external_independent_review_request_v1(
            request,
            asset_registration_document,
        )
        and request.get("status") == "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
    )
    claim_exact = _claim_exact(claim, request)
    claim_bound = request_exact and claim_exact
    claim_id = _clean_identifier(claim.get("reviewer_claim_id")) if claim_exact else None
    process_id = (
        _clean_identifier(claim.get("reviewer_process_id")) if claim_exact else None
    )
    document = {
        "schema_version": INTAKE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            "LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN"
            if claim_bound
            else "UNKNOWN"
        ),
        "intake_state": "CLAIM_BOUND_UNVERIFIED" if claim_bound else "UNKNOWN",
        "source": {
            "review_request_hash": (
                request.get("review_request_hash") if claim_bound else None
            ),
            "target_manifest_hash": (
                request.get("target_manifest_hash") if claim_bound else None
            ),
            "reviewer_claim_id_sha256": (
                strict_canonical_hash({"reviewer_claim_id": claim_id})
                if claim_bound
                else None
            ),
            "reviewer_process_id_sha256": (
                strict_canonical_hash({"reviewer_process_id": process_id})
                if claim_bound
                else None
            ),
            "raw_review_request_embedded": False,
            "raw_review_claim_embedded": False,
            "raw_reviewer_identifiers_embedded": False,
        },
        "facts": {
            "review_request_exactly_verified": request_exact,
            "review_claim_contract_exact": claim_exact,
            "review_claim_bound": claim_bound,
            "rubric_claims_all_true": claim_bound,
            "reviewer_independence_claimed": claim_bound,
            "reviewer_identity_authenticated": False,
            "reviewer_process_authenticated": False,
            "attestation_signature_verified": False,
            "review_replay_durability_proven": False,
            "descriptor_content_review_observed_by_system": False,
            "external_independent_review_complete": False,
            "host_patch_applied": False,
            "browser_executed": False,
            "dom_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(_BASE_BLOCKERS)
        + ([] if claim_bound else ["REVIEW_CLAIM_CONTRACT_INVALID"]),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "claim_intake_hash")


def verify_static_presentation_external_independent_review_claim_intake_v1(
    document: Any,
    review_request_document: Any,
    review_claim: Any,
    asset_registration_document: Any,
) -> bool:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = build_static_presentation_external_independent_review_claim_intake_v1(
            review_request_document,
            review_claim,
            asset_registration_document,
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "CLAIM_SCHEMA_VERSION",
    "INTAKE_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "REVIEW_RUBRIC_KEYS",
    "STATIC_FINGERPRINT",
    "build_static_presentation_external_independent_review_claim_intake_v1",
    "build_static_presentation_external_independent_review_request_v1",
    "verify_static_presentation_external_independent_review_claim_intake_v1",
    "verify_static_presentation_external_independent_review_request_v1",
]
