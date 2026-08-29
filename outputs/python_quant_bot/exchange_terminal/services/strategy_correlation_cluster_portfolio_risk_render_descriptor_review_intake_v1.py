"""Fail-closed request and intake contracts for external descriptor review.

This module can bind an unauthenticated review claim.  It cannot authenticate
the reviewer, verify a signature, establish replay durability, or complete an
independent review.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
    as preregistration_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "independent-review-request-v1"
)
CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "review-claim-v1"
)
INTAKE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "review-claim-intake-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-render-descriptor-review-intake-lock-1"
)
V9_IMPLEMENTATION_SHA256 = (
    "46fdc8db9f191adc188ea3619ac44d142013991830c77148fd9aec647a459c3e"
)

V9_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration_v8_document",
        "http_candidate_response",
        "http_candidate_request",
        "v8_verification_context",
        "successor_implementation_sha256",
    }
)
REVIEW_RUBRIC_KEYS = frozenset(
    {
        "stage_order_preserved",
        "neutral_source_gap_maturity_permission_copy",
        "permission_remains_unauthorized",
        "no_profitability_claim",
        "summary_only_no_raw_positions_or_returns",
    }
)
_CLAIM_FIELDS = frozenset(
    {
        "schema_version",
        "review_request_hash",
        "descriptor_sha256",
        "reviewer_claim_id",
        "reviewer_process_id",
        "independence_claimed",
        "rubric_results",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFY_V9 = (
    preregistration_v9.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v9
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _context_valid(context: Any) -> bool:
    return (
        type(context) is dict
        and frozenset(context) == V9_VERIFICATION_CONTEXT_KEYS
        and all(type(context[key]) is dict for key in V9_VERIFICATION_CONTEXT_KEYS)
    )


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "review_completion_allowed": False,
        "review_promotion_allowed": False,
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and bool(authority)
        and all(type(key) is str and type(value) is bool for key, value in authority.items())
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _v9_receipt_passed(receipt: Any) -> bool:
    return (
        type(receipt) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("preregistration_exactly_verified") is True
        and receipt.get("preregistration_status") == "BLOCKED"
        and receipt.get("blockers") == []
        and all(
            receipt.get(field) is False
            for field in (
                "http_route_registration_allowed",
                "presentation_mount_allowed",
                "current_admission_allowed",
                "paper_authorized",
                "live_order_allowed",
            )
        )
    )


def _call_v9_verifier(document: Any, context: Any) -> bool:
    if not _context_valid(context):
        return False
    try:
        receipt = _VERIFY_V9(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration_v8_document"]),
            copy.deepcopy(context["http_candidate_response"]),
            copy.deepcopy(context["http_candidate_request"]),
            v8_verification_context=copy.deepcopy(
                context["v8_verification_context"]
            ),
            successor_implementation_sha256=copy.deepcopy(
                context["successor_implementation_sha256"]
            ),
        )
    except Exception:
        return False
    return _v9_receipt_passed(receipt)


def _v9_presentable(document: Any, context: Any) -> tuple[bool, str | None]:
    if (
        type(document) is not dict
        or document.get("schema_version") != preregistration_v9.SCHEMA_VERSION
        or document.get("static_fingerprint") != preregistration_v9.STATIC_FINGERPRINT
        or document.get("status") != "BLOCKED"
        or document.get("contract_state") != "KNOWN"
        or not _is_hash(document.get("preregistration_hash"))
        or not _authority_locked(document)
    ):
        return False, None
    facts = document.get("facts")
    source = document.get("source")
    v8 = context.get("preregistration_v8_document") if type(context) is dict else None
    if not all(type(value) is dict for value in (facts, source, v8)):
        return False, None
    v8_source = v8.get("source")
    if type(v8_source) is not dict:
        return False, None
    evidence_summary_hashes = v8_source.get("evidence_summary_hashes")
    if type(evidence_summary_hashes) is not dict:
        return False, None
    descriptor_hash = evidence_summary_hashes.get(
        "registration_evidence_fixture_descriptor_sha256"
    )
    return (
        facts.get("presentation_http_contract_v3_versioned") is True
        and facts.get("presentation_http_transport_registered") is False
        and facts.get("render_descriptor_independently_reviewed") is False
        and facts.get("presentation_registration_v1_activated") is False
        and facts.get("ui_mounted") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("profitability_proven") is False
        and _is_hash(descriptor_hash)
        and source.get("immutable_v8_preregistration_hash")
        == v8.get("preregistration_hash"),
        descriptor_hash if _is_hash(descriptor_hash) else None,
    )


def build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
    preregistration_v9_document: Any,
    *,
    v9_verification_context: Any,
) -> dict[str, Any]:
    context_exact = _context_valid(v9_verification_context)
    v9_exact = _call_v9_verifier(
        preregistration_v9_document, v9_verification_context
    )
    presentable, descriptor_hash = _v9_presentable(
        preregistration_v9_document, v9_verification_context
    )
    request_known = context_exact and v9_exact and presentable
    v8 = (
        v9_verification_context.get("preregistration_v8_document")
        if context_exact
        else None
    )
    http_response = (
        v9_verification_context.get("http_candidate_response")
        if context_exact
        else None
    )
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
            if request_known
            else "UNKNOWN"
        ),
        "review_target": {
            "descriptor_sha256": descriptor_hash if request_known else None,
            "preregistration_v9_sha256": (
                preregistration_v9_document.get("preregistration_hash")
                if request_known
                else None
            ),
            "preregistration_v8_sha256": (
                v8.get("preregistration_hash")
                if request_known and type(v8) is dict
                else None
            ),
            "http_candidate_response_sha256": (
                http_response.get("response_hash")
                if request_known and type(http_response) is dict
                else None
            ),
            "preregistration_v9_implementation_sha256": (
                V9_IMPLEMENTATION_SHA256
            ),
        },
        "rubric": {
            key: "REVIEWER_MUST_ATTEST_TRUE" for key in sorted(REVIEW_RUBRIC_KEYS)
        },
        "facts": {
            "v9_verification_context_exact": context_exact,
            "preregistration_v9_exactly_verified": v9_exact,
            "review_target_hashes_bound": request_known,
            "descriptor_embedded": False,
            "source_documents_embedded": False,
            "verification_context_embedded": False,
            "reviewer_identity_authenticated": False,
            "reviewer_process_authenticated": False,
            "attestation_signature_verified": False,
            "review_replay_durability_proven": False,
            "independent_review_complete": False,
            "runtime_assets_accessed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": [
            "reviewer_identity_unauthenticated",
            "reviewer_process_unauthenticated",
            "review_attestation_signature_absent",
            "review_replay_durability_unproven",
            "external_independent_review_not_completed",
        ],
    }
    return seal_strict_canonical_document(document, "review_request_hash")


def verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
    document: Any,
    preregistration_v9_document: Any,
    *,
    v9_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
            preregistration_v9_document,
            v9_verification_context=v9_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


def _clean_identifier(value: Any) -> str | None:
    if type(value) is not str or value != value.strip() or not 1 <= len(value) <= 128:
        return None
    return value


def _claim_valid(claim: Any, request: Any) -> bool:
    review_target = request.get("review_target") if type(request) is dict else None
    if (
        type(claim) is not dict
        or frozenset(claim) != _CLAIM_FIELDS
        or claim.get("schema_version") != CLAIM_SCHEMA_VERSION
        or type(request) is not dict
        or type(review_target) is not dict
        or claim.get("review_request_hash") != request.get("review_request_hash")
        or claim.get("descriptor_sha256")
        != review_target.get("descriptor_sha256")
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


def build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
    review_request_document: Any,
    review_claim: Any,
    preregistration_v9_document: Any,
    *,
    v9_verification_context: Any,
) -> dict[str, Any]:
    request_exact = verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
        review_request_document,
        preregistration_v9_document,
        v9_verification_context=v9_verification_context,
    )
    request_awaiting = (
        type(review_request_document) is dict
        and review_request_document.get("status")
        == "AWAITING_EXTERNAL_INDEPENDENT_REVIEW"
    )
    claim_exact = _claim_valid(review_claim, review_request_document)
    claim_bound = request_exact and request_awaiting and claim_exact
    claim_id = (
        _clean_identifier(review_claim.get("reviewer_claim_id"))
        if type(review_claim) is dict
        else None
    )
    process_id = (
        _clean_identifier(review_claim.get("reviewer_process_id"))
        if type(review_claim) is dict
        else None
    )
    document = {
        "schema_version": INTAKE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            "LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN"
            if claim_bound
            else "UNKNOWN"
        ),
        "review_state": "CLAIM_BOUND_UNVERIFIED" if claim_bound else "UNKNOWN",
        "source": {
            "review_request_hash": (
                review_request_document.get("review_request_hash")
                if claim_bound
                else None
            ),
            "descriptor_sha256": (
                review_request_document.get("review_target", {}).get(
                    "descriptor_sha256"
                )
                if claim_bound
                else None
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
            "raw_claim_embedded": False,
            "raw_reviewer_identifiers_embedded": False,
            "review_request_embedded": False,
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
            "independent_review_complete": False,
            "http_route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": [
            "reviewer_identity_unauthenticated",
            "reviewer_process_unauthenticated",
            "review_attestation_signature_absent",
            "review_replay_durability_unproven",
            "external_independent_review_not_completed",
        ]
        + ([] if claim_bound else ["review_claim_contract_invalid"]),
    }
    return seal_strict_canonical_document(document, "intake_hash")


def verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
    document: Any,
    review_request_document: Any,
    review_claim: Any,
    preregistration_v9_document: Any,
    *,
    v9_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
            review_request_document,
            review_claim,
            preregistration_v9_document,
            v9_verification_context=v9_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "REQUEST_SCHEMA_VERSION",
    "CLAIM_SCHEMA_VERSION",
    "INTAKE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V9_IMPLEMENTATION_SHA256",
    "V9_VERIFICATION_CONTEXT_KEYS",
    "REVIEW_RUBRIC_KEYS",
    "build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1",
    "build_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1",
]
