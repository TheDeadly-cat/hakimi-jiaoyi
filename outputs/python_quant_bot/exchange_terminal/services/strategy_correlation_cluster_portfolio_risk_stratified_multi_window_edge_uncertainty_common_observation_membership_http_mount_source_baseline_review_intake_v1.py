"""Bind an unauthenticated source-baseline review claim, fail closed.

This module does not read source files, authenticate a reviewer, verify a
signature, prove process independence, establish replay durability, complete a
mount review, or authorize route registration.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1
    as _mount_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "review-request-v1"
)
CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "review-claim-v1"
)
INTAKE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "review-claim-intake-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-http-mount-source-baseline-review-intake-v1-lock-1"
)
MOUNT_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "2670cbcc0a0a7a1d123f1276b82d8948de8733985cdb52e0b3f496de80dffb96"
)

REVIEW_RUBRIC_KEYS = frozenset(
    {
        "server_hash_matches_preregistration",
        "http_contract_hash_matches_preregistration",
        "proposed_route_absent_from_server",
        "route_contract_symbol_absent_from_server",
        "route_contract_symbol_absent_from_http_contract",
        "no_handler_or_ui_binding_observed",
    }
)
_CLAIM_KEYS = {
    "schema_version",
    "review_request_hash",
    "reviewer_claim_id",
    "reviewer_process_id",
    "independence_claimed",
    "observed_source_hashes",
    "rubric_results",
}
_SOURCE_HASH_KEYS = {"server_sha256", "http_contract_sha256"}
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

_VERIFY_PREREGISTRATION = getattr(
    _mount_preregistration,
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_"
    "edge_uncertainty_common_observation_membership_http_mount_"
    "preregistration_v1",
)


def _plain_mapping(value: Any) -> bool:
    return type(value) is dict


def _hash(value: Any) -> bool:
    return isinstance(value, str) and _HASH_RE.fullmatch(value) is not None


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "source_baseline_authentication_allowed": False,
        "review_completion_allowed": False,
        "review_promotion_allowed": False,
        "mount_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if _plain_mapping(document) else None
    return (
        _plain_mapping(authority)
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _preregistration_presentable(document: Any) -> bool:
    if not _plain_mapping(document):
        return False
    if document.get("schema_version") != _mount_preregistration.PREREGISTRATION_SCHEMA_VERSION:
        return False
    if document.get("static_fingerprint") != _mount_preregistration.STATIC_FINGERPRINT:
        return False
    if document.get("status") != "BLOCKED" or not _hash(
        document.get("preregistration_hash")
    ):
        return False
    source_pins = document.get("source_baseline_pins")
    route_contract = document.get("route_contract")
    facts = document.get("facts")
    if not all(_plain_mapping(value) for value in (source_pins, route_contract, facts)):
        return False
    if source_pins != {
        "server_sha256": _mount_preregistration.SERVER_BASELINE_SHA256,
        "http_contract_sha256": _mount_preregistration.HTTP_CONTRACT_BASELINE_SHA256,
    }:
        return False
    if route_contract.get("implementation_sha256") != _mount_preregistration.ROUTE_CONTRACT_V1_SHA256:
        return False
    return (
        facts.get("source_hashes_pinned") is True
        and facts.get("route_registered") is False
        and facts.get("mount_allowed") is False
        and facts.get("frontend_mounted") is False
        and _authority_locked(document)
    )


def _preregistration_exact(document: Any) -> bool:
    if not _preregistration_presentable(document):
        return False
    try:
        return _VERIFY_PREREGISTRATION(copy.deepcopy(document)) is True
    except Exception:
        return False


def _request_blockers() -> list[str]:
    return [
        "EXTERNAL_REVIEW_CLAIM_ABSENT",
        "REVIEWER_IDENTITY_UNAUTHENTICATED",
        "REVIEWER_PROCESS_INDEPENDENCE_UNPROVEN",
        "SIGNED_ATTESTATION_ABSENT",
        "REPLAY_DURABILITY_UNPROVEN",
        "SOURCE_BASELINE_REVIEW_INCOMPLETE",
        "ROUTE_NOT_REGISTERED",
    ]


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
    mount_preregistration_document: Any,
) -> dict[str, Any]:
    """Build an external review request without asserting that review occurred."""
    source = copy.deepcopy(mount_preregistration_document)
    known = _preregistration_exact(source)
    source_pins = source.get("source_baseline_pins") if known else None
    document = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "AWAITING_EXTERNAL_INDEPENDENT_REVIEW" if known else "UNKNOWN",
        "review_state": "REQUESTED_UNAUTHENTICATED" if known else "UNKNOWN",
        "source": {
            "mount_preregistration_hash": source.get("preregistration_hash")
            if known
            else None,
            "mount_preregistration_implementation_sha256": (
                MOUNT_PREREGISTRATION_IMPLEMENTATION_SHA256 if known else None
            ),
            "raw_source_content_embedded": False,
            "mount_preregistration_embedded": False,
        },
        "review_target": {
            "source_baseline_pins": copy.deepcopy(source_pins),
            "source_paths": [
                "exchange_terminal/server.py",
                "exchange_terminal/services/http_contract.py",
            ]
            if known
            else [],
            "proposed_method": _mount_preregistration.PROPOSED_METHOD if known else None,
            "proposed_route": _mount_preregistration.PROPOSED_ROUTE if known else None,
            "route_contract_implementation_sha256": (
                _mount_preregistration.ROUTE_CONTRACT_V1_SHA256 if known else None
            ),
        },
        "rubric_contract": {
            "required_result_keys": sorted(REVIEW_RUBRIC_KEYS),
            "all_results_must_be_true": True,
        },
        "facts": {
            "mount_preregistration_exactly_verified": known,
            "source_hashes_pinned": known,
            "source_content_review_observed_by_system": False,
            "external_review_claim_received": False,
            "reviewer_identity_authenticated": False,
            "reviewer_process_independence_verified": False,
            "signed_attestation_verified": False,
            "replay_durability_verified": False,
            "source_baseline_authenticated": False,
            "independent_review_complete": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _request_blockers()
        + ([] if known else ["MOUNT_PREREGISTRATION_UNVERIFIED"]),
    }
    return seal_strict_canonical_document(document, "review_request_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
    document: Any,
    mount_preregistration_document: Any,
) -> bool:
    if not _plain_mapping(document):
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
            mount_preregistration_document
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


def _claim_bound(review_request: Any, claim: Any) -> bool:
    if not _plain_mapping(review_request) or not _plain_mapping(claim):
        return False
    if set(claim) != _CLAIM_KEYS or claim.get("schema_version") != CLAIM_SCHEMA_VERSION:
        return False
    if review_request.get("status") != "AWAITING_EXTERNAL_INDEPENDENT_REVIEW":
        return False
    if claim.get("review_request_hash") != review_request.get("review_request_hash"):
        return False
    if not _identifier(claim.get("reviewer_claim_id")) or not _identifier(
        claim.get("reviewer_process_id")
    ):
        return False
    if claim.get("independence_claimed") is not True:
        return False
    observed = claim.get("observed_source_hashes")
    target = review_request.get("review_target")
    if not _plain_mapping(observed) or set(observed) != _SOURCE_HASH_KEYS:
        return False
    if not _plain_mapping(target) or observed != target.get("source_baseline_pins"):
        return False
    rubric = claim.get("rubric_results")
    return (
        _plain_mapping(rubric)
        and set(rubric) == REVIEW_RUBRIC_KEYS
        and all(type(value) is bool and value is True for value in rubric.values())
    )


def _intake_blockers() -> list[str]:
    return [
        "REVIEWER_IDENTITY_UNAUTHENTICATED",
        "REVIEWER_PROCESS_INDEPENDENCE_UNPROVEN",
        "SIGNED_ATTESTATION_ABSENT",
        "REVIEW_NONCE_UNIQUENESS_UNPROVEN",
        "REPLAY_DURABILITY_UNPROVEN",
        "SOURCE_CONTENT_REVIEW_CLAIM_UNAUTHENTICATED",
        "SOURCE_BASELINE_REVIEW_INCOMPLETE",
        "ROUTE_NOT_REGISTERED",
    ]


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
    review_request_document: Any,
    review_claim: Any,
    mount_preregistration_document: Any,
) -> dict[str, Any]:
    """Bind a claim while preserving that identity and review remain unproven."""
    request = copy.deepcopy(review_request_document)
    claim = copy.deepcopy(review_claim)
    preregistration = copy.deepcopy(mount_preregistration_document)
    preregistration_exact = _preregistration_exact(preregistration)
    request_exact = (
        preregistration_exact
        and verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
            request, preregistration
        )
    )
    bound = request_exact and _claim_bound(request, claim)
    claim_id = claim.get("reviewer_claim_id") if bound else None
    process_id = claim.get("reviewer_process_id") if bound else None
    document = {
        "schema_version": INTAKE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": (
            "LOCAL_SOURCE_BASELINE_REVIEW_CLAIM_BOUND_AUTHENTICATION_ABSENT"
            if bound
            else "UNKNOWN"
        ),
        "review_state": "CLAIM_BOUND_UNAUTHENTICATED" if bound else "UNKNOWN",
        "source": {
            "review_request_hash": request.get("review_request_hash") if bound else None,
            "mount_preregistration_hash": preregistration.get("preregistration_hash")
            if bound
            else None,
            "review_claim_sha256": strict_canonical_hash({"review_claim": claim})
            if bound
            else None,
            "reviewer_claim_id_sha256": strict_canonical_hash(
                {"reviewer_claim_id": claim_id}
            )
            if bound
            else None,
            "reviewer_process_id_sha256": strict_canonical_hash(
                {"reviewer_process_id": process_id}
            )
            if bound
            else None,
            "observed_source_hashes": copy.deepcopy(
                claim.get("observed_source_hashes")
            )
            if bound
            else None,
            "raw_claim_embedded": False,
            "raw_reviewer_identifiers_embedded": False,
            "raw_source_content_embedded": False,
            "review_request_embedded": False,
        },
        "facts": {
            "mount_preregistration_exactly_verified": preregistration_exact,
            "review_request_exactly_verified": request_exact,
            "review_claim_contract_exact": bound,
            "review_claim_bound": bound,
            "observed_source_hash_claims_match_pins": bound,
            "rubric_claims_all_true": bound,
            "reviewer_independence_claimed": bound,
            "reviewer_identity_authenticated": False,
            "reviewer_process_independence_verified": False,
            "attestation_signature_verified": False,
            "review_nonce_uniqueness_verified": False,
            "replay_durability_verified": False,
            "source_content_review_observed_by_system": False,
            "source_baseline_authenticated": False,
            "independent_review_complete": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _intake_blockers()
        + ([] if bound else ["SOURCE_BASELINE_REVIEW_CLAIM_INVALID"]),
    }
    return seal_strict_canonical_document(document, "intake_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
    document: Any,
    review_request_document: Any,
    review_claim: Any,
    mount_preregistration_document: Any,
) -> bool:
    if not _plain_mapping(document):
        return False
    try:
        expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
            review_request_document,
            review_claim,
            mount_preregistration_document,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "CLAIM_SCHEMA_VERSION",
    "INTAKE_SCHEMA_VERSION",
    "MOUNT_PREREGISTRATION_IMPLEMENTATION_SHA256",
    "REQUEST_SCHEMA_VERSION",
    "REVIEW_RUBRIC_KEYS",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1",
]
