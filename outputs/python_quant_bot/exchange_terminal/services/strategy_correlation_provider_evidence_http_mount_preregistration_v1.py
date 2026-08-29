from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-provider-evidence-http-mount-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260822-strategy-correlation-provider-evidence-http-mount-preregistration-1"
)

CANDIDATE_ADAPTER_SHA256 = (
    "79038f90ad26de5620ca78fefc06b546e6dca05bbc8af26cd6c57fd2a553e40b"
)
SERVER_BASELINE_SHA256 = (
    "3d93569e4a6874342cd60bcade636fa99eab30ca2e95a0863e1abb5540eb7864"
)
HTTP_CONTRACT_BASELINE_SHA256 = (
    "526dfb623c067c46fa640e3ac6637d3dbd0b0b6f5bfd7bc359f4b001a0670c6b"
)

PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = "/api/v1/research/strategy-correlation/provider-evidence"

MOUNT_BLOCKERS = (
    "AUTHENTICATION_MECHANISM_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_CONTEXT_PROVIDER_UNREGISTERED",
    "REQUEST_LOG_REDACTION_POLICY_UNREGISTERED",
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
        "runtime_reads_allowed": False,
        "runtime_mutations_allowed": False,
        "cache_reads_allowed": False,
        "cache_writes_allowed": False,
        "request_body_logging_allowed": False,
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
        "trusted_context_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
            "client_supplied_allowed": False,
        },
        "request_log_redaction": {
            "required": True,
            "registered": False,
            "policy_id": None,
            "request_body_logging_allowed": False,
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
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_provider_evidence_http_mount_preregistration_v1() -> (
    dict[str, Any]
):
    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "BLOCKED",
            "candidate": {
                "adapter_schema_version": (
                    "strategy-correlation-provider-evidence-http-candidate-response-v1"
                ),
                "adapter_static_fingerprint": (
                    "20260822-strategy-correlation-provider-evidence-http-candidate-1"
                ),
                "adapter_sha256": CANDIDATE_ADAPTER_SHA256,
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
                "source_hashes_pinned": True,
                "mount_controls_complete": False,
                "route_registered": False,
                "mount_allowed": False,
            },
            "authority": _authority(),
            "blockers": list(MOUNT_BLOCKERS),
        },
        "preregistration_hash",
    )


def verify_strategy_correlation_provider_evidence_http_mount_preregistration_v1(
    document: Any,
) -> bool:
    if type(document) is not dict:
        return False
    return strict_json_contract_equal(
        document,
        build_strategy_correlation_provider_evidence_http_mount_preregistration_v1(),
    )


__all__ = [
    "CANDIDATE_ADAPTER_SHA256",
    "HTTP_CONTRACT_BASELINE_SHA256",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROPOSED_METHOD",
    "PROPOSED_ROUTE",
    "SERVER_BASELINE_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_provider_evidence_http_mount_preregistration_v1",
    "verify_strategy_correlation_provider_evidence_http_mount_preregistration_v1",
]
