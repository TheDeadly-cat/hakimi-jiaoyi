"""Deterministic preregistration for a still-unmounted membership HTTP route."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-http-mount-preregistration-v1-lock-1"
)

ROUTE_CONTRACT_V1_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-route-contract-response-v1"
)
ROUTE_CONTRACT_V1_STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-http-route-contract-v1-unregistered-lock-1"
)
ROUTE_CONTRACT_V1_SHA256 = (
    "51d11d9fc7cc1b9913069b6d102ba802aebd57f80dd273b588cebb454133de49"
)
CANDIDATE_V11_SHA256 = (
    "edb4deca22e9dfee22627626ac6982af09199ec6052fb9e6658df371566415d1"
)
SERVER_BASELINE_SHA256 = (
    "3d93569e4a6874342cd60bcade636fa99eab30ca2e95a0863e1abb5540eb7864"
)
HTTP_CONTRACT_BASELINE_SHA256 = (
    "526dfb623c067c46fa640e3ac6637d3dbd0b0b6f5bfd7bc359f4b001a0670c6b"
)

PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = (
    "/api/research/strategy-correlation-clusters/"
    "common-observation-membership-presentation-v11"
)

MOUNT_BLOCKERS = (
    "AUTHENTICATION_MECHANISM_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_CANDIDATE_CONTEXT_PROVIDER_UNREGISTERED",
    "REQUEST_LOG_REDACTION_POLICY_UNREGISTERED",
    "CONSUMER_BINDING_REVIEW_REQUIRED",
    "INDEPENDENT_MOUNT_REVIEW_REQUIRED",
    "ROUTE_NOT_REGISTERED",
)


def _required_transport_controls() -> dict[str, Any]:
    return {
        "loopback_only": True,
        "same_origin_required": True,
        "request_content_type": "application/json",
        "response_content_type": "application/json; charset=utf-8",
        "cache_control": "no-store",
        "x_content_type_options": "nosniff",
        "x_frame_options": "DENY",
        "referrer_policy": "no-referrer",
        "cross_origin_opener_policy": "same-origin",
        "read_only": True,
        "schema_only_request": True,
        "bounded_projection_only_response": True,
        "runtime_reads_allowed": False,
        "runtime_mutations_allowed": False,
        "cache_reads_allowed": False,
        "cache_writes_allowed": False,
        "request_body_logging_allowed": False,
        "candidate_document_client_supplied_allowed": False,
        "verification_context_client_supplied_allowed": False,
    }


def _unregistered_controls() -> dict[str, dict[str, Any]]:
    return {
        "authentication": {
            "required": True,
            "registered": False,
            "mechanism": None,
        },
        "rate_limit": {
            "required": True,
            "registered": False,
            "requests_per_window": None,
            "window_seconds": None,
            "burst": None,
        },
        "request_body_limit": {
            "required": True,
            "registered": False,
            "maximum_bytes": None,
        },
        "trusted_candidate_context_provider": {
            "required": True,
            "registered": False,
            "candidate_document_provider_id": None,
            "verification_context_provider_id": None,
            "client_supplied_allowed": False,
            "runtime_asset_reads_allowed": False,
        },
        "request_log_redaction": {
            "required": True,
            "registered": False,
            "policy_id": None,
            "request_body_logging_allowed": False,
        },
        "consumer_binding_review": {
            "required": True,
            "completed": False,
            "review_id": None,
            "frontend_mounted": False,
        },
        "independent_mount_review": {
            "required": True,
            "completed": False,
            "review_id": None,
        },
        "route_registration": {
            "registered": False,
            "registration_id": None,
        },
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "mount_allowed": False,
        "registration_allowed": False,
        "externally_callable": False,
        "candidate_consumer_activation_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1() -> dict[str, Any]:
    """Build a blocked policy document; this performs no mount or source I/O."""
    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "route_contract": {
                "schema_version": ROUTE_CONTRACT_V1_SCHEMA_VERSION,
                "static_fingerprint": ROUTE_CONTRACT_V1_STATIC_FINGERPRINT,
                "implementation_sha256": ROUTE_CONTRACT_V1_SHA256,
            },
            "candidate": {
                "version": "membership-presentation-http-candidate-v11-lock-4",
                "implementation_sha256": CANDIDATE_V11_SHA256,
            },
            "source_baseline_pins": {
                "server_sha256": SERVER_BASELINE_SHA256,
                "http_contract_sha256": HTTP_CONTRACT_BASELINE_SHA256,
            },
            "proposed_transport": {
                "method": PROPOSED_METHOD,
                "route": PROPOSED_ROUTE,
                "registered": False,
                "externally_callable": False,
            },
            "required_transport_controls": _required_transport_controls(),
            "unregistered_controls": _unregistered_controls(),
            "facts": {
                "policy_preregistered": True,
                "route_contract_available": True,
                "candidate_contract_available": True,
                "source_hashes_pinned": True,
                "trusted_candidate_context_provider_available": False,
                "consumer_binding_review_complete": False,
                "independent_mount_review_complete": False,
                "mount_controls_complete": False,
                "route_registered": False,
                "frontend_mounted": False,
                "mount_allowed": False,
                "runtime_assets_accessed": False,
                "profitability_proven": False,
            },
            "authority": _authority(),
            "blockers": list(MOUNT_BLOCKERS),
            "stages": [
                {
                    "axis": "SOURCE",
                    "state": "PREREGISTERED",
                    "detail": "ROUTE_CONTRACT_AND_SOURCE_BASELINES_PINNED",
                },
                {
                    "axis": "GAP",
                    "state": "BLOCKED",
                    "detail": "TRANSPORT_CONTROLS_AND_REVIEWS_UNREGISTERED",
                },
                {
                    "axis": "MATURITY",
                    "state": "POLICY_ONLY",
                    "detail": "HTTP_MOUNT_PREREGISTRATION_V1",
                },
                {
                    "axis": "PERMISSION",
                    "state": "NONE",
                    "detail": "NO_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
                },
            ],
        },
        "preregistration_hash",
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(
    document: Any,
) -> bool:
    """Verify only the exact deterministic preregistration document."""
    if type(document) is not dict:
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(),
    )


__all__ = [
    "CANDIDATE_V11_SHA256",
    "HTTP_CONTRACT_BASELINE_SHA256",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROPOSED_METHOD",
    "PROPOSED_ROUTE",
    "ROUTE_CONTRACT_V1_SCHEMA_VERSION",
    "ROUTE_CONTRACT_V1_SHA256",
    "ROUTE_CONTRACT_V1_STATIC_FINGERPRINT",
    "SERVER_BASELINE_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1",
]
