from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-mount-"
    "preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-http-mount-preregistration-1"
)

CANDIDATE_ADAPTER_SHA256 = (
    "2acd18017a1d3e7cd6afce5102f6391b6b63ac3824ba0214e807679f543681e4"
)
PUBLIC_PROJECTION_SHA256 = (
    "4f6df866f6923fe175e41e6f260539c8921d76b13db2232ebcd28b70d32c7f02"
)
SERVER_BASELINE_SHA256 = (
    "3d93569e4a6874342cd60bcade636fa99eab30ca2e95a0863e1abb5540eb7864"
)
HTTP_CONTRACT_BASELINE_SHA256 = (
    "526dfb623c067c46fa640e3ac6637d3dbd0b0b6f5bfd7bc359f4b001a0670c6b"
)

CANDIDATE_RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-http-candidate-"
    "response-v1"
)
CANDIDATE_STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-http-candidate-1"
)
PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-migration-public-summary-v1"
)
PUBLIC_SUMMARY_STATIC_FINGERPRINT = (
    "20260822-report22-date-grid-migration-projection-lock-1"
)

PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = (
    "/api/v1/research/strategy-correlation/"
    "report22-date-grid-migration-evidence"
)

MOUNT_BLOCKERS = (
    "AUTHENTICATION_MECHANISM_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_MIGRATION_EVIDENCE_PROVIDER_UNREGISTERED",
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
        "public_summary_only_response": True,
        "runtime_reads_allowed": False,
        "runtime_mutations_allowed": False,
        "cache_reads_allowed": False,
        "cache_writes_allowed": False,
        "request_body_logging_allowed": False,
        "migration_assessment_client_supplied_allowed": False,
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
        "trusted_migration_evidence_provider": {
            "required": True,
            "registered": False,
            "assessment_provider_id": None,
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
        "migration_execution_allowed": False,
        "fresh_migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "candidate": {
                "adapter_schema_version": CANDIDATE_RESPONSE_SCHEMA_VERSION,
                "adapter_static_fingerprint": CANDIDATE_STATIC_FINGERPRINT,
                "adapter_sha256": CANDIDATE_ADAPTER_SHA256,
            },
            "public_projection": {
                "summary_schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
                "summary_static_fingerprint": PUBLIC_SUMMARY_STATIC_FINGERPRINT,
                "projection_sha256": PUBLIC_PROJECTION_SHA256,
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
                "candidate_contract_available": True,
                "public_projection_contract_available": True,
                "source_hashes_pinned": True,
                "trusted_migration_evidence_provider_available": False,
                "consumer_binding_review_complete": False,
                "mount_controls_complete": False,
                "route_registered": False,
                "mount_allowed": False,
            },
            "authority": _authority(),
            "blockers": list(MOUNT_BLOCKERS),
        },
        "preregistration_hash",
    )


def verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(
    document: Any,
) -> bool:
    if type(document) is not dict:
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1(),
    )


__all__ = [
    "CANDIDATE_ADAPTER_SHA256",
    "CANDIDATE_RESPONSE_SCHEMA_VERSION",
    "CANDIDATE_STATIC_FINGERPRINT",
    "HTTP_CONTRACT_BASELINE_SHA256",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROPOSED_METHOD",
    "PROPOSED_ROUTE",
    "PUBLIC_PROJECTION_SHA256",
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "PUBLIC_SUMMARY_STATIC_FINGERPRINT",
    "SERVER_BASELINE_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1",
    "verify_strategy_correlation_cluster_temporal_date_grid_migration_http_mount_preregistration_v1",
]
