"""Preregister the ADR0317 projection mount policy without mounting it."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.interfaces.http import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as projection_candidate,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as provider_binding,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-readonly-http-projection-"
    "mount-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-readonly-http-"
    "projection-mount-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-readonly-http-"
    "projection-mount-v1"
)
PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = (
    "/api/v1/research/portfolio-correlation/admission-effective-budget"
)
EXPECTED_MOUNT_PREREGISTRATION_HASH = (
    "d87dca5d784cd6575af89fd30a4ac6703fddab75d02174a91c15324949233ad2"
)

SYNTHETIC_STATE_RECEIPTS = {
    "known_response_hash": (
        "4dee39b6203ce91a90f955af6e132a2dfc9968f003806a7d7f4a76c7bed7c8a1"
    ),
    "unknown_response_hash": (
        "4ec56e2b8a2bd571f5afd49e5599255af17afeb2fca6c5c3928c7fc11a751afe"
    ),
    "blocked_response_hash": (
        "5a2c30496e09a5ed3e3f289860d0bcff2d5769334e2fdf1528293191103a9bd8"
    ),
}

SOURCE_BASELINE_PINS = {
    "candidate_implementation_path": (
        "exchange_terminal/interfaces/http/portfolio_correlation_admission_"
        "effective_budget_readonly_projection_candidate_v1.py"
    ),
    "candidate_implementation_sha256": (
        "14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc"
    ),
    "candidate_test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_readonly_"
        "http_projection_candidate_v1.py"
    ),
    "candidate_test_sha256": (
        "c68c3a6e323a6eec5807ad6f68fc51299fcdcaa299114c6834469abfdbf9e83a"
    ),
    "candidate_adr_path": (
        "docs/adr/0317-portfolio-correlation-admission-effective-budget-"
        "readonly-http-projection-candidate-v1.md"
    ),
    "candidate_adr_sha256": (
        "fd232a2d2d99bb60933502d0d844b05e74ce850a875fb18c54a5c3cb8291bc7b"
    ),
    "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
    "server_path": "exchange_terminal/server.py",
    "server_sha256": (
        "3d93569e4a6874342cd60bcade636fa99eab30ca2e95a0863e1abb5540eb7864"
    ),
    "http_contract_path": "exchange_terminal/services/http_contract.py",
    "http_contract_sha256": (
        "526dfb623c067c46fa640e3ac6637d3dbd0b0b6f5bfd7bc359f4b001a0670c6b"
    ),
}

MOUNT_BLOCKERS = (
    "ADR0318_PREREGISTRATION_ONLY",
    "AUTHENTICATION_UNREGISTERED",
    "CSRF_PROTECTION_UNREGISTERED",
    "RATE_LIMIT_POLICY_UNREGISTERED",
    "REQUEST_BODY_LIMIT_UNREGISTERED",
    "TRUSTED_INTERNAL_CONTEXT_PROVIDER_UNREGISTERED",
    "REQUEST_LOG_REDACTION_POLICY_UNREGISTERED",
    "INDEPENDENT_MOUNT_REVIEW_REQUIRED",
    "HANDLER_NOT_IMPLEMENTED",
    "ROUTE_NOT_REGISTERED",
    "AUTHORIZED_BROWSER_REVIEW_NOT_RUN",
    "CURRENT_ACTIVATION_NOT_AUTHORIZED",
    "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
)


def _snapshot_json_value(value: Any, active_ids: set[int]) -> Any:
    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic mapping is not a JSON document")
        active_ids.add(value_id)
        try:
            snapshot: dict[str, Any] = {}
            for key in value:
                if type(key) is not str or key in snapshot:
                    raise TypeError("JSON object keys must be unique strings")
                snapshot[key] = _snapshot_json_value(value[key], active_ids)
            return snapshot
        finally:
            active_ids.remove(value_id)
    if type(value) is list:
        value_id = id(value)
        if value_id in active_ids:
            raise ValueError("cyclic list is not a JSON document")
        active_ids.add(value_id)
        try:
            return [_snapshot_json_value(item, active_ids) for item in value]
        finally:
            active_ids.remove(value_id)
    if value is None or type(value) in (bool, int, float, str):
        return value
    raise TypeError("input must contain only JSON-compatible values")


def _snapshot_json_mapping(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, Mapping):
        return None
    try:
        snapshot = _snapshot_json_value(document, set())
    except Exception:
        return None
    return snapshot if type(snapshot) is dict else None


def _require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label} does not match the pinned contract")


def _candidate_contract() -> dict[str, Any]:
    _require_equal(
        "ADR0317 request schema",
        projection_candidate.REQUEST_SCHEMA_VERSION,
        (
            "portfolio-correlation-admission-effective-budget-readonly-http-"
            "projection-candidate-request-v1"
        ),
    )
    _require_equal(
        "ADR0317 response schema",
        projection_candidate.RESPONSE_SCHEMA_VERSION,
        (
            "portfolio-correlation-admission-effective-budget-readonly-http-"
            "projection-candidate-response-v1"
        ),
    )
    _require_equal(
        "ADR0317 static fingerprint",
        projection_candidate.STATIC_FINGERPRINT,
        (
            "20260824-portfolio-correlation-admission-effective-budget-readonly-"
            "http-projection-candidate-v1-unregistered-lock-1"
        ),
    )
    _require_equal(
        "ADR0317 projection id",
        projection_candidate.PROJECTION_ID,
        "portfolio-correlation-admission-effective-budget-readonly-v1",
    )
    _require_equal(
        "ADR0317 interface status",
        projection_candidate.INTERFACE_STATUS,
        "UNREGISTERED_CANDIDATE",
    )
    return {
        "request_schema_version": projection_candidate.REQUEST_SCHEMA_VERSION,
        "response_schema_version": projection_candidate.RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": projection_candidate.STATIC_FINGERPRINT,
        "projection_id": projection_candidate.PROJECTION_ID,
        "interface_status": projection_candidate.INTERFACE_STATUS,
        "input_source": "INTERNAL_PROVIDER_RESULT_ONLY",
        "state_order": ["KNOWN", "UNKNOWN", "BLOCKED"],
        "synthetic_state_receipts": dict(SYNTHETIC_STATE_RECEIPTS),
    }


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
        "exact_request_contract_required": True,
        "internal_provider_context_only": True,
        "client_source_documents_allowed": False,
        "client_provider_context_allowed": False,
        "request_body_logging_allowed": False,
        "runtime_reads_allowed": False,
        "runtime_mutations_allowed": False,
        "database_reads_allowed": False,
        "database_writes_allowed": False,
        "cache_reads_allowed": False,
        "cache_writes_allowed": False,
    }


def _unregistered_controls() -> dict[str, dict[str, Any]]:
    return {
        "authentication": {
            "required": True,
            "registered": False,
            "mechanism": None,
        },
        "csrf_protection": {
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
        "trusted_internal_context_provider": {
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
        "handler_registration": {
            "registered": False,
            "handler_id": None,
        },
        "route_registration": {
            "registered": False,
            "registration_id": None,
        },
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "handler_implementation_allowed": False,
        "mount_allowed": False,
        "route_registration_allowed": False,
        "endpoint_registration_allowed": False,
        "external_call_allowed": False,
        "application_import_allowed": False,
        "browser_execution_allowed": False,
        "ui_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1() -> dict[str, Any]:
    """Build the exact blocked mount policy without touching the host."""

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "BLOCKED",
        "registration_state": (
            "HTTP_MOUNT_POLICY_PREREGISTERED_ALL_TRANSPORT_SECURITY_AND_HOST_"
            "BINDINGS_UNREGISTERED"
        ),
        "candidate_contract": _candidate_contract(),
        "source_baseline_pins": dict(SOURCE_BASELINE_PINS),
        "proposed_transport": {
            "method": PROPOSED_METHOD,
            "route": PROPOSED_ROUTE,
            "handler": None,
            "endpoint": None,
            "registered": False,
            "externally_callable": False,
        },
        "proposed_http_status_mapping": {
            "known": 200,
            "verified_unknown": 200,
            "verified_blocked": 200,
            "request_contract_invalid": 400,
            "authentication_failed": 401,
            "csrf_failed": 403,
            "rate_limited": 429,
            "trusted_context_unavailable": 503,
            "provider_failure": 503,
        },
        "required_transport_controls": _required_transport_controls(),
        "unregistered_controls": _unregistered_controls(),
        "activation_order": [
            "VERIFY_EXACT_ADR0317_PROJECTION_CANDIDATE_AND_SOURCE_PINS",
            "REGISTER_LOOPBACK_SAME_ORIGIN_AUTHENTICATION_AND_CSRF_CONTROLS",
            "REGISTER_RATE_LIMIT_AND_REQUEST_BODY_LIMIT",
            "REGISTER_TRUSTED_INTERNAL_CONTEXT_PROVIDER",
            "REGISTER_REQUEST_LOG_REDACTION_POLICY",
            "COMPLETE_INDEPENDENT_MOUNT_REVIEW",
            "IMPLEMENT_HANDLER_IN_SEPARATE_VERSION",
            "REGISTER_ROUTE_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
            "RUN_AUTHORIZED_BROWSER_REVIEW_BEFORE_ANY_UI_MOUNT",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "candidate_contract_pinned": True,
            "candidate_source_hashes_pinned": True,
            "server_baseline_pinned": True,
            "http_contract_baseline_pinned": True,
            "transport_policy_preregistered": True,
            "control_requirements_complete": True,
            "control_registrations_complete": False,
            "trusted_internal_context_provider_present": False,
            "handler_implemented": False,
            "route_registered": False,
            "externally_callable": False,
            "browser_executed": False,
            "ui_mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(MOUNT_BLOCKERS),
        "authority": _authority(),
        "decision": (
            "ADR0317_THREE_STATE_PROJECTION_AND_CURRENT_HOST_BASELINES_PINNED_"
            "MOUNT_POLICY_PREREGISTERED_ALL_SECURITY_HANDLER_ROUTE_BROWSER_"
            "MOUNT_CURRENT_PAPER_AND_LIVE_BINDINGS_UNREGISTERED"
        ),
    }
    sealed = seal_strict_canonical_document(document, "mount_preregistration_hash")
    _require_equal(
        "mount_preregistration_hash",
        sealed.get("mount_preregistration_hash"),
        EXPECTED_MOUNT_PREREGISTRATION_HASH,
    )
    return sealed


def verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
    document: Any,
) -> bool:
    """Return true only for the exact safely snapshotted preregistration."""

    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "EXPECTED_MOUNT_PREREGISTRATION_HASH",
    "MOUNT_BLOCKERS",
    "PREREGISTRATION_ID",
    "PROPOSED_METHOD",
    "PROPOSED_ROUTE",
    "SCHEMA_VERSION",
    "SOURCE_BASELINE_PINS",
    "STATIC_FINGERPRINT",
    "SYNTHETIC_STATE_RECEIPTS",
    "build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1",
    "verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1",
]
