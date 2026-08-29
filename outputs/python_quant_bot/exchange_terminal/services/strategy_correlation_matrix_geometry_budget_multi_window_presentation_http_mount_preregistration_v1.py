"""Blocked mount preregistration for the ADR0335 HTTP candidate."""

from __future__ import annotations

from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9
    as _candidate_v9,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "http-mount-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-http-mount-preregistration-v1-blocked-lock-1"
)

CANDIDATE_V9_MODULE = (
    "exchange_terminal.interfaces.http.strategy_correlation_matrix_geometry_"
    "budget_multi_window_presentation_http_candidate_v9"
)
CANDIDATE_V9_IMPLEMENTATION_SHA256 = (
    "c99ab75e16bf006a1834676aa5980c128018ddfb669cf7e32baea8cbae7b403a"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
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
    "geometry-budget-multi-window-presentation-v9"
)

MOUNT_BLOCKERS = (
    "AUTHENTICATION_MECHANISM_UNREGISTERED",
    "CSRF_POLICY_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_CANDIDATE_CONTEXT_PROVIDER_UNREGISTERED",
    "REQUEST_LOG_REDACTION_POLICY_UNREGISTERED",
    "HANDLER_IMPLEMENTATION_UNREGISTERED",
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
        "database_reads_allowed": False,
        "database_writes_allowed": False,
        "cache_reads_allowed": False,
        "cache_writes_allowed": False,
        "external_network_access_allowed": False,
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
        "csrf": {
            "required": True,
            "registered": False,
            "policy_id": None,
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
            "database_reads_allowed": False,
            "cache_reads_allowed": False,
            "external_network_access_allowed": False,
        },
        "request_log_redaction": {
            "required": True,
            "registered": False,
            "policy_id": None,
            "request_body_logging_allowed": False,
        },
        "handler_implementation": {
            "required": True,
            "registered": False,
            "handler_id": None,
            "implementation_sha256": None,
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


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1() -> dict[str, Any]:
    """Build a deterministic policy document without source or runtime I/O."""
    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "candidate_contract": {
                "module": CANDIDATE_V9_MODULE,
                "implementation_sha256": CANDIDATE_V9_IMPLEMENTATION_SHA256,
                "contract_hash": _candidate_v9.CONTRACT_HASH,
                "request_schema_version": _candidate_v9.REQUEST_SCHEMA_VERSION,
                "response_schema_version": _candidate_v9.RESPONSE_SCHEMA_VERSION,
                "static_fingerprint": _candidate_v9.STATIC_FINGERPRINT,
                "interface_status": _candidate_v9.INTERFACE_STATUS,
            },
            "source_baseline_pins": {
                "strict_canonical_sha256": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
                "server_sha256": SERVER_BASELINE_SHA256,
                "http_contract_sha256": HTTP_CONTRACT_BASELINE_SHA256,
            },
            "proposed_transport": {
                "method": PROPOSED_METHOD,
                "route": PROPOSED_ROUTE,
                "handler": None,
                "endpoint": None,
                "registered": False,
                "externally_callable": False,
            },
            "required_transport_controls": _required_transport_controls(),
            "unregistered_controls": _unregistered_controls(),
            "facts": {
                "policy_preregistered": True,
                "candidate_contract_available": True,
                "source_hashes_pinned": True,
                "trusted_candidate_context_provider_available": False,
                "handler_available": False,
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
                    "detail": "ADR0335_CONTRACT_AND_SOURCE_BASELINES_PINNED",
                },
                {
                    "axis": "GAP",
                    "state": "BLOCKED",
                    "detail": "TRANSPORT_PROVIDER_HANDLER_AND_REVIEWS_UNREGISTERED",
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


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
    document: Any,
) -> bool:
    """Verify only the exact deterministic blocked preregistration."""
    return bool(
        type(document) is dict
        and strict_json_contract_equal(
            document,
            build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(),
        )
    )


__all__ = [
    "CANDIDATE_V9_IMPLEMENTATION_SHA256",
    "CANDIDATE_V9_MODULE",
    "HTTP_CONTRACT_BASELINE_SHA256",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROPOSED_METHOD",
    "PROPOSED_ROUTE",
    "SERVER_BASELINE_SHA256",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1",
]
