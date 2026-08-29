"""Preregister an ADR0335 trusted internal provider without implementing it."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_candidate_v9
    as _candidate_v9,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1
    as _mount_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-internal-provider-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-trusted-internal-provider-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-internal-provider-v1"
)
PROVIDER_ID = PREREGISTRATION_ID
PROVIDER_OUTPUT_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-internal-provider-output-v1"
)

REQUEST_ROLES = (
    "schema_version",
    "geometry_budget_multi_window_presentation_binding_evaluation",
    "expected_geometry_budget_multi_window_presentation_binding_evaluation_hash",
)
VERIFICATION_CONTEXT_ROLES = (
    "presentation_binding_evaluation",
    "adapter_v7_document",
    "expected_evaluation_hash",
    "expected_presentation_binding_evaluation_hash",
    "expected_adapter_v7_hash",
    "presentation_binding_verification_context",
    "adapter_v7_verification_context",
)
REQUEST_ROLE_HASH = (
    "2d6ad49ff964471733c26c428a8450757d4e00c3f1f268510fd950d31a8d1928"
)
VERIFICATION_CONTEXT_ROLE_HASH = (
    "e437b2ec29452cfa8a899a95042f834617ec61648f3cebfaa4453578a9162299"
)
PROVIDER_OUTPUT_SHAPE_HASH = (
    "e8ab642585b4c1ef1f7f6358e1127c30313a15bf5338ce4c38317f2257b5ba72"
)

MOUNT_IMPLEMENTATION_PATH = (
    "exchange_terminal/services/strategy_correlation_matrix_geometry_budget_"
    "multi_window_presentation_http_mount_preregistration_v1.py"
)
MOUNT_IMPLEMENTATION_SHA256 = (
    "eeba8e61430dc9a6ceb5997738e0eb6d2e2a5fa5bbf7a4f2c48d5520fe54f3d4"
)
MOUNT_TEST_PATH = (
    "tests/test_strategy_correlation_matrix_geometry_budget_multi_window_"
    "presentation_http_mount_preregistration_v1.py"
)
MOUNT_TEST_SHA256 = (
    "479d3ffdd2e53fe162eae1b5e840bc9aad36185978ba9497a2db888be3a91ceb"
)
MOUNT_ADR_PATH = (
    "docs/adr/0336-geometry-bound-multi-window-http-mount-preregistration-v1.md"
)
MOUNT_ADR_SHA256 = (
    "15391d7d36d5846814fd3c91546e5d66405d928a0a18377eddabc2e4d3a537b7"
)
MOUNT_PREREGISTRATION_HASH = (
    "7723e8556e62c5e3cdb13b57bcc4e54689ccda6fb0a35256c5bf9eb15822e606"
)

PREDECESSOR_CONTRACT = {
    "mount_preregistration_hash": MOUNT_PREREGISTRATION_HASH,
    "mount_implementation_path": MOUNT_IMPLEMENTATION_PATH,
    "mount_implementation_sha256": MOUNT_IMPLEMENTATION_SHA256,
    "mount_test_path": MOUNT_TEST_PATH,
    "mount_test_sha256": MOUNT_TEST_SHA256,
    "mount_adr_path": MOUNT_ADR_PATH,
    "mount_adr_sha256": MOUNT_ADR_SHA256,
    "candidate_implementation_sha256": (
        _mount_preregistration.CANDIDATE_V9_IMPLEMENTATION_SHA256
    ),
    "candidate_contract_hash": _candidate_v9.CONTRACT_HASH,
    "candidate_request_schema_version": _candidate_v9.REQUEST_SCHEMA_VERSION,
    "candidate_response_schema_version": _candidate_v9.RESPONSE_SCHEMA_VERSION,
    "candidate_static_fingerprint": _candidate_v9.STATIC_FINGERPRINT,
    "proposed_method": _mount_preregistration.PROPOSED_METHOD,
    "proposed_route": _mount_preregistration.PROPOSED_ROUTE,
}

PROVIDER_BLOCKERS = (
    "ADR0337_PREREGISTRATION_ONLY",
    "AUTHENTICATED_REQUEST_SCOPE_PROVIDER_UNREGISTERED",
    "TRUSTED_ADR0334_SOURCE_RESOLVER_UNREGISTERED",
    "PROVIDER_IMPLEMENTATION_MISSING",
    "CONTEXT_GENERATION_ID_PROVIDER_UNREGISTERED",
    "SINGLE_USE_GUARD_UNREGISTERED",
    "PROVIDER_REDACTION_POLICY_UNREGISTERED",
    "INDEPENDENT_PROVIDER_REVIEW_REQUIRED",
    "HANDLER_BINDING_UNAUTHORIZED",
    "ROUTE_NOT_REGISTERED",
    "ADR0336_TRANSPORT_CONTROLS_INCOMPLETE",
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


def _verify_predecessor() -> None:
    document = _mount_preregistration.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1()
    if not _mount_preregistration.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_http_mount_preregistration_v1(
        document
    ):
        raise ValueError("ADR0336 mount preregistration is not exact")
    _require_equal(
        "ADR0336 mount preregistration hash",
        document.get("preregistration_hash"),
        MOUNT_PREREGISTRATION_HASH,
    )
    _require_equal(
        "ADR0335 candidate contract hash",
        document.get("candidate_contract", {}).get("contract_hash"),
        _candidate_v9.CONTRACT_HASH,
    )
    transport = document.get("proposed_transport")
    provider = document.get("unregistered_controls", {}).get(
        "trusted_candidate_context_provider"
    )
    if (
        type(transport) is not dict
        or transport.get("registered") is not False
        or transport.get("handler") is not None
        or transport.get("endpoint") is not None
        or type(provider) is not dict
        or provider.get("registered") is not False
        or provider.get("client_supplied_allowed") is not False
    ):
        raise ValueError("ADR0336 must remain unmounted and provider-unbound")


def _provider_output_shape() -> dict[str, Any]:
    request_roles = list(REQUEST_ROLES)
    context_roles = list(VERIFICATION_CONTEXT_ROLES)
    _require_equal(
        "request role hash",
        strict_canonical_hash(request_roles),
        REQUEST_ROLE_HASH,
    )
    _require_equal(
        "verification context role hash",
        strict_canonical_hash(context_roles),
        VERIFICATION_CONTEXT_ROLE_HASH,
    )
    shape = {
        "schema_version": PROVIDER_OUTPUT_SCHEMA_VERSION,
        "provider_id": PROVIDER_ID,
        "owner": "TRUSTED_INTERNAL_REQUEST_SCOPE_ONLY",
        "input_source": "INTERNAL_ADR0334_EXACT_SOURCE_CHAIN_ONLY",
        "request_roles": request_roles,
        "request_role_hash": REQUEST_ROLE_HASH,
        "verification_context_roles": context_roles,
        "verification_context_role_hash": VERIFICATION_CONTEXT_ROLE_HASH,
        "candidate_document_client_supplied_allowed": False,
        "verification_context_client_supplied_allowed": False,
        "response_embedding_allowed": False,
        "request_logging_allowed": False,
    }
    _require_equal(
        "provider output shape hash",
        strict_canonical_hash(shape),
        PROVIDER_OUTPUT_SHAPE_HASH,
    )
    return shape


def _unregistered_controls() -> dict[str, dict[str, Any]]:
    return {
        "provider_implementation": {
            "required": True,
            "registered": False,
            "implementation_id": None,
        },
        "authenticated_request_scope_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "trusted_adr0334_source_resolver": {
            "required": True,
            "registered": False,
            "resolver_id": None,
        },
        "context_generation_id_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "single_use_guard": {
            "required": True,
            "registered": False,
            "guard_id": None,
        },
        "provider_redaction_policy": {
            "required": True,
            "registered": False,
            "policy_id": None,
        },
        "independent_provider_review": {
            "required": True,
            "completed": False,
            "review_id": None,
        },
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "provider_implementation_allowed": False,
        "request_scope_binding_allowed": False,
        "source_resolution_allowed": False,
        "single_use_guard_binding_allowed": False,
        "handler_binding_allowed": False,
        "route_registration_allowed": False,
        "external_call_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1() -> dict[str, Any]:
    """Build the exact blocked provider preregistration."""
    _verify_predecessor()
    output_shape = _provider_output_shape()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "BLOCKED",
        "registration_state": (
            "TRUSTED_INTERNAL_PROVIDER_PREREGISTERED_IMPLEMENTATION_REQUEST_"
            "SCOPE_SOURCE_RESOLUTION_SINGLE_USE_HANDLER_AND_ROUTE_UNBOUND"
        ),
        "predecessor_contract": dict(PREDECESSOR_CONTRACT),
        "provider_output_shape": output_shape,
        "provider_output_shape_hash": PROVIDER_OUTPUT_SHAPE_HASH,
        "lifecycle_contract": {
            "construction_mode": (
                "REQUEST_LOCAL_AFTER_AUTHENTICATION_CSRF_RATE_LIMIT_BODY_LIMIT_"
                "AND_TRUSTED_ADR0334_SOURCE_RESOLUTION"
            ),
            "freshness_mode": "SAME_SYNCHRONOUS_REQUEST_SCOPE_ONLY",
            "clock_or_timestamp_required": False,
            "maximum_resolution_count": 1,
            "single_use_required": True,
            "reuse_across_requests_allowed": False,
            "persistence_allowed": False,
            "runtime_allowed": False,
            "database_allowed": False,
            "cache_allowed": False,
            "filesystem_allowed": False,
            "network_allowed": False,
            "discard_after_candidate_response": True,
        },
        "ownership_contract": {
            "provider_owner": "TRUSTED_INTERNAL_SERVER_COMPONENT",
            "request_scope_id_source": "AUTHENTICATED_SERVER_REQUEST_SCOPE",
            "context_generation_id_source": "TRUSTED_INTERNAL_PROVIDER",
            "source_chain_owner": "ADR0334_INTERNAL_GEOMETRY_BOUND_CHAIN",
            "client_request_fields_allowed": [],
            "client_context_fields_allowed": [],
            "client_override_allowed": False,
            "client_context_hash_allowed": False,
            "client_freshness_evidence_allowed": False,
        },
        "binding_contract": {
            "candidate_contract_hash": _candidate_v9.CONTRACT_HASH,
            "candidate_implementation_sha256": (
                _mount_preregistration.CANDIDATE_V9_IMPLEMENTATION_SHA256
            ),
            "mount_preregistration_hash": MOUNT_PREREGISTRATION_HASH,
            "provider_id": PROVIDER_ID,
            "provider_implementation": None,
            "authenticated_request_scope_provider": None,
            "trusted_source_resolver": None,
            "context_generation_id_provider": None,
            "single_use_guard": None,
            "handler_binding": None,
            "route_binding": None,
            "registered": False,
        },
        "redaction_contract": {
            "request_body_logging_allowed": False,
            "provider_output_logging_allowed": False,
            "candidate_document_logging_allowed": False,
            "verification_context_logging_allowed": False,
            "position_logging_allowed": False,
            "symbol_logging_allowed": False,
            "provider_hash_response_embedding_allowed": False,
            "source_hash_response_embedding_allowed": False,
            "candidate_response_only": True,
        },
        "unregistered_controls": _unregistered_controls(),
        "activation_order": [
            "VERIFY_EXACT_ADR0336_MOUNT_PREREGISTRATION_AND_SOURCE_PINS",
            "REGISTER_AUTHENTICATED_REQUEST_SCOPE_PROVIDER",
            "REGISTER_TRUSTED_ADR0334_SOURCE_RESOLVER",
            "IMPLEMENT_PROVIDER_IN_SEPARATE_VERSION",
            "REGISTER_CONTEXT_GENERATION_ID_AND_SINGLE_USE_GUARD",
            "REGISTER_PROVIDER_REDACTION_POLICY",
            "COMPLETE_INDEPENDENT_PROVIDER_REVIEW",
            "BIND_PROVIDER_TO_HANDLER_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
            "KEEP_ROUTE_UNREGISTERED_UNTIL_ALL_ADR0336_CONTROLS_PASS",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "mount_preregistration_exactly_pinned": True,
            "provider_output_shape_preregistered": True,
            "provider_role_order_pinned": True,
            "request_local_lifecycle_preregistered": True,
            "client_override_forbidden": True,
            "provider_implemented": False,
            "request_scope_provider_present": False,
            "source_resolver_present": False,
            "single_use_guard_present": False,
            "redaction_policy_present": False,
            "handler_bound": False,
            "route_registered": False,
            "externally_callable": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(PROVIDER_BLOCKERS),
        "authority": _authority(),
        "decision": (
            "ADR0336_MOUNT_POLICY_AND_ADR0335_PROVIDER_OUTPUT_SHAPE_PINNED_"
            "REQUEST_LOCAL_SINGLE_USE_NO_CLOCK_NO_PERSISTENCE_CLIENT_OVERRIDE_"
            "FORBIDDEN_IMPLEMENTATION_HANDLER_ROUTE_CURRENT_PAPER_LIVE_UNBOUND"
        ),
    }
    return seal_strict_canonical_document(
        document,
        "provider_preregistration_hash",
    )


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
    document: Any,
) -> bool:
    """Verify one safely snapshotted exact preregistration."""
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "PREDECESSOR_CONTRACT",
    "PREREGISTRATION_ID",
    "PROVIDER_BLOCKERS",
    "PROVIDER_ID",
    "PROVIDER_OUTPUT_SCHEMA_VERSION",
    "PROVIDER_OUTPUT_SHAPE_HASH",
    "REQUEST_ROLES",
    "REQUEST_ROLE_HASH",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_CONTEXT_ROLES",
    "VERIFICATION_CONTEXT_ROLE_HASH",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1",
]
