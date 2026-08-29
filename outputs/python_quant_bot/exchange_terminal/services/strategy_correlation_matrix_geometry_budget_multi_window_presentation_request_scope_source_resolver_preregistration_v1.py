"""Preregister ADR0337 request-scope and source-resolver contracts only."""

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
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1
    as _provider_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-scope-source-resolver-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-request-scope-source-resolver-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-scope-source-resolver-v1"
)
REQUEST_SCOPE_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "authenticated-request-scope-evidence-v1"
)
SOURCE_RESOLVER_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "trusted-adr0334-source-resolver-v1"
)
CROSS_BINDING_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "request-scope-source-resolver-binding-v1"
)

REQUEST_SCOPE_FIELDS = (
    "schema_version",
    "request_scope_id",
    "authentication_receipt_hash",
    "csrf_receipt_hash",
    "origin_receipt_hash",
    "request_contract_hash",
    "method",
    "route",
    "context_generation_id",
    "maximum_resolution_count",
    "consumed",
)
REQUEST_SCOPE_FIELD_ORDER_HASH = (
    "d1ba8add3e26442d8f691f1b13e5a4c03c7107d52c277b63d90fb7f136524000"
)
REQUEST_SCOPE_CONTRACT_HASH = (
    "e7843b2719cd5bac016bab8e2b4cf65a154a5dc77fb2e497a593ae821f343737"
)
SOURCE_RESOLVER_CONTRACT_HASH = (
    "408877a2eb1c5df48f427bf960761e553bd106cea42a3644bce02b687aa843d4"
)
CROSS_BINDING_CONTRACT_HASH = (
    "cf04835edd16a09a6ba06024c62d7c3726a31bfa2546950dbfabc5a614732d97"
)

PROVIDER_IMPLEMENTATION_PATH = (
    "exchange_terminal/services/strategy_correlation_matrix_geometry_budget_"
    "multi_window_presentation_trusted_internal_provider_preregistration_v1.py"
)
PROVIDER_IMPLEMENTATION_SHA256 = (
    "1ebb2683c85863abd2d9ddbded060e8c468d0edab2ad36216f646d875605700e"
)
PROVIDER_TEST_PATH = (
    "tests/test_strategy_correlation_matrix_geometry_budget_multi_window_"
    "presentation_trusted_internal_provider_preregistration_v1.py"
)
PROVIDER_TEST_SHA256 = (
    "b2b27d6fc73bc803e6bc81d749f643a7b6fc7991ecc3aafa9331a212597d49c3"
)
PROVIDER_ADR_PATH = (
    "docs/adr/0337-geometry-bound-multi-window-trusted-internal-provider-"
    "preregistration-v1.md"
)
PROVIDER_ADR_SHA256 = (
    "0a998223891e5f61fb6e3a0e6005e485261fcacd687234c71fe5cc7baf835adb"
)
PROVIDER_PREREGISTRATION_HASH = (
    "a0f387aaf2cd2730e5fc6ab795ce90bbcb82f25d4b21f5e79868d1181eb15ec8"
)

PREDECESSOR_CONTRACT = {
    "provider_preregistration_hash": PROVIDER_PREREGISTRATION_HASH,
    "provider_implementation_path": PROVIDER_IMPLEMENTATION_PATH,
    "provider_implementation_sha256": PROVIDER_IMPLEMENTATION_SHA256,
    "provider_test_path": PROVIDER_TEST_PATH,
    "provider_test_sha256": PROVIDER_TEST_SHA256,
    "provider_adr_path": PROVIDER_ADR_PATH,
    "provider_adr_sha256": PROVIDER_ADR_SHA256,
    "provider_output_shape_hash": (
        _provider_preregistration.PROVIDER_OUTPUT_SHAPE_HASH
    ),
    "request_role_hash": _provider_preregistration.REQUEST_ROLE_HASH,
    "verification_context_role_hash": (
        _provider_preregistration.VERIFICATION_CONTEXT_ROLE_HASH
    ),
    "mount_preregistration_hash": (
        _provider_preregistration.PREDECESSOR_CONTRACT[
            "mount_preregistration_hash"
        ]
    ),
    "candidate_contract_hash": _candidate_v9.CONTRACT_HASH,
    "proposed_method": _mount_preregistration.PROPOSED_METHOD,
    "proposed_route": _mount_preregistration.PROPOSED_ROUTE,
}

SCOPE_RESOLVER_BLOCKERS = (
    "ADR0338_PREREGISTRATION_ONLY",
    "AUTHENTICATION_RECEIPT_PROVIDER_UNREGISTERED",
    "CSRF_RECEIPT_PROVIDER_UNREGISTERED",
    "ORIGIN_RECEIPT_PROVIDER_UNREGISTERED",
    "REQUEST_SCOPE_ID_PROVIDER_UNREGISTERED",
    "CONTEXT_GENERATION_ID_PROVIDER_UNREGISTERED",
    "TRUSTED_ADR0334_SOURCE_RESOLVER_IMPLEMENTATION_MISSING",
    "SINGLE_USE_GUARD_UNREGISTERED",
    "INDEPENDENT_SCOPE_RESOLVER_BINDING_REVIEW_REQUIRED",
    "PROVIDER_IMPLEMENTATION_MISSING",
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
    document = _provider_preregistration.build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1()
    if not _provider_preregistration.verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_internal_provider_preregistration_v1(
        document
    ):
        raise ValueError("ADR0337 provider preregistration is not exact")
    _require_equal(
        "ADR0337 provider preregistration hash",
        document.get("provider_preregistration_hash"),
        PROVIDER_PREREGISTRATION_HASH,
    )
    binding = document.get("binding_contract")
    if type(binding) is not dict or binding.get("registered") is not False:
        raise ValueError("ADR0337 provider binding must remain unregistered")
    for key in (
        "provider_implementation",
        "authenticated_request_scope_provider",
        "trusted_source_resolver",
        "context_generation_id_provider",
        "single_use_guard",
        "handler_binding",
        "route_binding",
    ):
        if binding.get(key) is not None:
            raise ValueError(f"ADR0337 binding slot {key} must remain null")


def _request_scope_contract() -> dict[str, Any]:
    fields = list(REQUEST_SCOPE_FIELDS)
    _require_equal(
        "request scope field-order hash",
        strict_canonical_hash(fields),
        REQUEST_SCOPE_FIELD_ORDER_HASH,
    )
    contract = {
        "schema_version": REQUEST_SCOPE_SCHEMA_VERSION,
        "evidence_owner": "SERVER_TRANSPORT_SECURITY_LAYER_ONLY",
        "field_order": fields,
        "field_order_hash": REQUEST_SCOPE_FIELD_ORDER_HASH,
        "hash_only_security_receipts": True,
        "raw_authentication_material_allowed": False,
        "raw_csrf_material_allowed": False,
        "raw_origin_material_allowed": False,
        "client_authored_allowed": False,
        "client_override_allowed": False,
        "same_synchronous_request_scope_only": True,
        "maximum_resolution_count": 1,
        "request_scope_evidence_producer": None,
        "registered": False,
    }
    _require_equal(
        "request scope contract hash",
        strict_canonical_hash(contract),
        REQUEST_SCOPE_CONTRACT_HASH,
    )
    return contract


def _source_resolver_contract() -> dict[str, Any]:
    contract = {
        "schema_version": SOURCE_RESOLVER_SCHEMA_VERSION,
        "resolver_owner": "TRUSTED_INTERNAL_SERVER_COMPONENT",
        "input_request_scope_schema_version": REQUEST_SCOPE_SCHEMA_VERSION,
        "input_provider_output_shape_hash": (
            _provider_preregistration.PROVIDER_OUTPUT_SHAPE_HASH
        ),
        "input_request_role_hash": _provider_preregistration.REQUEST_ROLE_HASH,
        "input_verification_context_role_hash": (
            _provider_preregistration.VERIFICATION_CONTEXT_ROLE_HASH
        ),
        "output_provider_schema_version": (
            _provider_preregistration.PROVIDER_OUTPUT_SCHEMA_VERSION
        ),
        "source_mode": "EXPLICIT_ADR0334_INTERNAL_GEOMETRY_BOUND_CHAIN_ONLY",
        "runtime_reads_allowed": False,
        "database_reads_allowed": False,
        "cache_reads_allowed": False,
        "filesystem_reads_allowed": False,
        "network_reads_allowed": False,
        "client_source_documents_allowed": False,
        "client_provider_context_allowed": False,
        "request_scope_hash_required": True,
        "context_generation_id_required": True,
        "single_use_guard_required": True,
        "resolver_implementation": None,
        "registered": False,
    }
    _require_equal(
        "source resolver contract hash",
        strict_canonical_hash(contract),
        SOURCE_RESOLVER_CONTRACT_HASH,
    )
    return contract


def _cross_binding_contract() -> dict[str, Any]:
    contract = {
        "schema_version": CROSS_BINDING_SCHEMA_VERSION,
        "request_scope_contract_hash": REQUEST_SCOPE_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "provider_preregistration_hash": PROVIDER_PREREGISTRATION_HASH,
        "provider_output_shape_hash": (
            _provider_preregistration.PROVIDER_OUTPUT_SHAPE_HASH
        ),
        "mount_preregistration_hash": PREDECESSOR_CONTRACT[
            "mount_preregistration_hash"
        ],
        "candidate_contract_hash": _candidate_v9.CONTRACT_HASH,
        "method": _mount_preregistration.PROPOSED_METHOD,
        "route": _mount_preregistration.PROPOSED_ROUTE,
        "same_request_scope_required": True,
        "same_context_generation_required": True,
        "authentication_receipt_required": True,
        "csrf_receipt_required": True,
        "origin_receipt_required": True,
        "unconsumed_scope_required": True,
        "client_binding_override_allowed": False,
        "binding_implementation": None,
        "registered": False,
    }
    _require_equal(
        "cross binding contract hash",
        strict_canonical_hash(contract),
        CROSS_BINDING_CONTRACT_HASH,
    )
    return contract


def _unregistered_controls() -> dict[str, dict[str, Any]]:
    return {
        "authentication_receipt_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "csrf_receipt_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "origin_receipt_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "request_scope_id_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "context_generation_id_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "source_resolver_implementation": {
            "required": True,
            "registered": False,
            "implementation_id": None,
        },
        "single_use_guard": {
            "required": True,
            "registered": False,
            "guard_id": None,
        },
        "independent_binding_review": {
            "required": True,
            "completed": False,
            "review_id": None,
        },
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "security_receipt_provider_registration_allowed": False,
        "request_scope_provider_implementation_allowed": False,
        "source_resolver_implementation_allowed": False,
        "single_use_guard_binding_allowed": False,
        "provider_implementation_allowed": False,
        "handler_binding_allowed": False,
        "route_registration_allowed": False,
        "external_call_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1() -> dict[str, Any]:
    """Build the exact blocked request-scope/resolver preregistration."""
    _verify_predecessor()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "BLOCKED",
        "registration_state": (
            "REQUEST_SCOPE_EVIDENCE_ADR0334_SOURCE_RESOLVER_AND_CROSS_BINDING_"
            "PREREGISTERED_ALL_PRODUCERS_IMPLEMENTATIONS_AND_HOST_BINDINGS_"
            "UNREGISTERED"
        ),
        "predecessor_contract": dict(PREDECESSOR_CONTRACT),
        "request_scope_contract": _request_scope_contract(),
        "request_scope_contract_hash": REQUEST_SCOPE_CONTRACT_HASH,
        "source_resolver_contract": _source_resolver_contract(),
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "cross_binding_contract": _cross_binding_contract(),
        "cross_binding_contract_hash": CROSS_BINDING_CONTRACT_HASH,
        "unregistered_controls": _unregistered_controls(),
        "activation_order": [
            "VERIFY_EXACT_ADR0337_PROVIDER_PREREGISTRATION_AND_SOURCE_PINS",
            "REGISTER_AUTHENTICATION_CSRF_AND_ORIGIN_RECEIPT_PROVIDERS",
            "REGISTER_REQUEST_SCOPE_AND_CONTEXT_GENERATION_ID_PROVIDERS",
            "IMPLEMENT_TRUSTED_ADR0334_SOURCE_RESOLVER_IN_SEPARATE_VERSION",
            "REGISTER_SINGLE_USE_GUARD",
            "COMPLETE_INDEPENDENT_SCOPE_RESOLVER_BINDING_REVIEW",
            "IMPLEMENT_PROVIDER_ONLY_AFTER_ALL_SUBCONTRACTS_VERIFY",
            "BIND_HANDLER_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
            "KEEP_ROUTE_UNREGISTERED_UNTIL_ALL_ADR0336_CONTROLS_PASS",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "provider_preregistration_exactly_pinned": True,
            "request_scope_contract_preregistered": True,
            "source_resolver_contract_preregistered": True,
            "cross_binding_contract_preregistered": True,
            "request_scope_evidence_producer_present": False,
            "security_receipt_providers_present": False,
            "source_resolver_implemented": False,
            "single_use_guard_present": False,
            "cross_binding_registered": False,
            "provider_implemented": False,
            "handler_bound": False,
            "route_registered": False,
            "externally_callable": False,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(SCOPE_RESOLVER_BLOCKERS),
        "authority": _authority(),
        "decision": (
            "ADR0337_PROVIDER_SHAPE_BOUND_TO_SEPARATE_HASH_ONLY_REQUEST_SCOPE_"
            "EVIDENCE_AND_EXPLICIT_ADR0334_SOURCE_RESOLVER_CONTRACTS_ALL_"
            "SECURITY_PRODUCERS_RESOLVER_GUARD_PROVIDER_HANDLER_ROUTE_CURRENT_"
            "PAPER_AND_LIVE_UNREGISTERED"
        ),
    }
    return seal_strict_canonical_document(
        document,
        "scope_resolver_preregistration_hash",
    )


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1(
    document: Any,
) -> bool:
    """Verify one safely snapshotted exact preregistration."""
    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "CROSS_BINDING_CONTRACT_HASH",
    "CROSS_BINDING_SCHEMA_VERSION",
    "PREDECESSOR_CONTRACT",
    "PREREGISTRATION_ID",
    "REQUEST_SCOPE_CONTRACT_HASH",
    "REQUEST_SCOPE_FIELDS",
    "REQUEST_SCOPE_FIELD_ORDER_HASH",
    "REQUEST_SCOPE_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SCOPE_RESOLVER_BLOCKERS",
    "SOURCE_RESOLVER_CONTRACT_HASH",
    "SOURCE_RESOLVER_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_preregistration_v1",
]
