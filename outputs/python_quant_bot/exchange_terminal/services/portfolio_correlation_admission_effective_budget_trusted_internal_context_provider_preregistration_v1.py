"""Preregister a request-local trusted context provider without implementing it."""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.interfaces.http import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as projection_candidate,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as provider_binding,
)
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1 as mount_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-trusted-internal-context-"
    "provider-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-trusted-internal-"
    "context-provider-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-trusted-internal-"
    "context-provider-v1"
)
CONTEXT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-trusted-internal-context-v1"
)
CONTEXT_PROVIDER_ID = PREREGISTRATION_ID

POSITIONAL_ROLES = (
    "adapter_registration_document",
    "consumer_preregistration_document",
    "binding_document",
    "admission_v2_document",
    "effective_budget_v3_document",
    "report_document",
    "correlation_preregistration_document",
    "correlation_matrix_document",
    "selection_cells_document",
    "complete_link_audit_document",
    "complete_link_gate_document",
    "strata_preregistration_document",
    "strata_gate_document",
)
KEYWORD_ROLES = (
    "strategy_id",
    "variant_id",
    "lane",
    "equity",
    "positions",
    "proposed_symbol",
    "proposed_notional",
    "proposed_direction",
    "max_cluster_gross_pct",
    "risk_increasing",
)
POSITIONAL_ROLE_HASH = (
    "1c1652d5ff99d81b063678e20bc8b5e621c718df34c249028884a24349a9f8b2"
)
KEYWORD_ROLE_HASH = (
    "24672b9e3d2501291d683ac83803c112846578e8a230a18409346acb3ab05edb"
)
CONTEXT_SHAPE_HASH = (
    "c7d53837786e478a6b2341463594ac0c6a8d348d1a1eb3458a0e8eed11772d43"
)
EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH = (
    "14e08fb0d46ea1738e77c416ebc49506430778ce025c45d500130c722ea31cff"
)

PREDECESSOR_CONTRACT = {
    "mount_preregistration_hash": (
        "d87dca5d784cd6575af89fd30a4ac6703fddab75d02174a91c15324949233ad2"
    ),
    "mount_implementation_path": (
        "exchange_terminal/services/portfolio_correlation_admission_effective_"
        "budget_readonly_http_projection_mount_preregistration_v1.py"
    ),
    "mount_implementation_sha256": (
        "460cc552d650a8615191da4a40c8afac16b6c5700e552bdcdc000a9b5f2b10ae"
    ),
    "mount_test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_readonly_"
        "http_projection_mount_preregistration_v1.py"
    ),
    "mount_test_sha256": (
        "ba5d0dc605f8b9003eed0e48064bfc18017cc34cfdc0833dfe9e02d4f5382241"
    ),
    "mount_adr_path": (
        "docs/adr/0318-portfolio-correlation-admission-effective-budget-"
        "readonly-http-projection-mount-preregistration-v1.md"
    ),
    "mount_adr_sha256": (
        "671dc630a65ea85ab95a43cd3feee4ea99180b34319289406b5de3f0d8e26032"
    ),
    "projection_request_schema_version": projection_candidate.REQUEST_SCHEMA_VERSION,
    "projection_response_schema_version": projection_candidate.RESPONSE_SCHEMA_VERSION,
    "projection_id": projection_candidate.PROJECTION_ID,
    "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
}

CONTEXT_BLOCKERS = (
    "ADR0319_PREREGISTRATION_ONLY",
    "AUTHENTICATED_REQUEST_SCOPE_PROVIDER_UNREGISTERED",
    "TRUSTED_SOURCE_CHAIN_RESOLVER_UNREGISTERED",
    "CONTEXT_PROVIDER_IMPLEMENTATION_MISSING",
    "CONTEXT_GENERATION_ID_PROVIDER_UNREGISTERED",
    "SINGLE_USE_GUARD_UNREGISTERED",
    "CONTEXT_REDACTION_POLICY_UNREGISTERED",
    "INDEPENDENT_CONTEXT_REVIEW_REQUIRED",
    "HANDLER_BINDING_UNAUTHORIZED",
    "ROUTE_NOT_REGISTERED",
    "ADR0318_SECURITY_CONTROLS_INCOMPLETE",
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
    document = mount_preregistration.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1()
    if not mount_preregistration.verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1(
        document
    ):
        raise ValueError("ADR0318 mount preregistration is not exact")
    _require_equal(
        "ADR0318 mount preregistration hash",
        document.get("mount_preregistration_hash"),
        PREDECESSOR_CONTRACT["mount_preregistration_hash"],
    )
    if document["proposed_transport"]["registered"] is not False:
        raise ValueError("ADR0318 route must remain unregistered")
    if document["proposed_transport"]["handler"] is not None:
        raise ValueError("ADR0318 handler must remain null")
    if document["proposed_transport"]["endpoint"] is not None:
        raise ValueError("ADR0318 endpoint must remain null")


def _context_shape() -> dict[str, Any]:
    positional_roles = list(POSITIONAL_ROLES)
    keyword_roles = list(KEYWORD_ROLES)
    _require_equal(
        "positional role hash",
        strict_canonical_hash(positional_roles),
        POSITIONAL_ROLE_HASH,
    )
    _require_equal(
        "keyword role hash",
        strict_canonical_hash(keyword_roles),
        KEYWORD_ROLE_HASH,
    )
    shape = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "context_provider_id": CONTEXT_PROVIDER_ID,
        "owner": "TRUSTED_INTERNAL_REQUEST_SCOPE_ONLY",
        "input_source": "INTERNAL_ADR0311_EXACT_SOURCE_CHAIN_ONLY",
        "positional_roles": positional_roles,
        "positional_role_hash": POSITIONAL_ROLE_HASH,
        "keyword_roles": keyword_roles,
        "keyword_role_hash": KEYWORD_ROLE_HASH,
        "source_documents_present_in_internal_context": True,
        "source_documents_client_supplied_allowed": False,
        "provider_context_client_supplied_allowed": False,
        "response_embedding_allowed": False,
        "request_logging_allowed": False,
    }
    _require_equal(
        "context shape hash",
        strict_canonical_hash(shape),
        CONTEXT_SHAPE_HASH,
    )
    return shape


def _unregistered_controls() -> dict[str, dict[str, Any]]:
    return {
        "context_provider_implementation": {
            "required": True,
            "registered": False,
            "implementation_id": None,
        },
        "authenticated_request_scope_provider": {
            "required": True,
            "registered": False,
            "provider_id": None,
        },
        "trusted_source_chain_resolver": {
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
        "context_redaction_policy": {
            "required": True,
            "registered": False,
            "policy_id": None,
        },
        "independent_context_review": {
            "required": True,
            "completed": False,
            "review_id": None,
        },
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "context_provider_implementation_allowed": False,
        "request_scope_binding_allowed": False,
        "source_chain_resolution_allowed": False,
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


def build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1() -> dict[str, Any]:
    """Build the exact blocked context-provider preregistration."""

    _verify_predecessor()
    context_shape = _context_shape()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "BLOCKED",
        "registration_state": (
            "TRUSTED_INTERNAL_CONTEXT_PROVIDER_PREREGISTERED_IMPLEMENTATION_"
            "REQUEST_SCOPE_BINDING_AND_SINGLE_USE_GUARD_UNBOUND"
        ),
        "predecessor_contract": dict(PREDECESSOR_CONTRACT),
        "context_shape": context_shape,
        "context_shape_hash": CONTEXT_SHAPE_HASH,
        "lifecycle_contract": {
            "construction_mode": (
                "REQUEST_LOCAL_AFTER_AUTHENTICATION_CSRF_AND_TRUSTED_SOURCE_"
                "RESOLUTION"
            ),
            "freshness_mode": "SAME_SYNCHRONOUS_REQUEST_SCOPE_ONLY",
            "clock_or_timestamp_required": False,
            "maximum_resolution_count": 1,
            "single_use_required": True,
            "reuse_across_requests_allowed": False,
            "persistence_allowed": False,
            "database_allowed": False,
            "cache_allowed": False,
            "filesystem_allowed": False,
            "network_allowed": False,
            "discard_after_projection": True,
        },
        "ownership_contract": {
            "context_builder_owner": "TRUSTED_INTERNAL_SERVER_COMPONENT",
            "request_scope_id_source": "AUTHENTICATED_SERVER_REQUEST_SCOPE",
            "context_generation_id_source": "TRUSTED_INTERNAL_CONTEXT_PROVIDER",
            "source_chain_owner": "ADR0311_INTERNAL_PROVIDER_CHAIN",
            "client_request_fields_allowed": ["schema_version", "projection_id"],
            "client_context_fields_allowed": [],
            "client_override_allowed": False,
            "client_context_hash_allowed": False,
            "client_freshness_evidence_allowed": False,
        },
        "binding_contract": {
            "projection_id": projection_candidate.PROJECTION_ID,
            "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
            "mount_preregistration_hash": (
                mount_preregistration.EXPECTED_MOUNT_PREREGISTRATION_HASH
            ),
            "context_provider_id": CONTEXT_PROVIDER_ID,
            "context_provider_implementation": None,
            "request_scope_provider": None,
            "single_use_guard": None,
            "handler_binding": None,
            "route_binding": None,
            "registered": False,
        },
        "redaction_contract": {
            "request_body_logging_allowed": False,
            "context_logging_allowed": False,
            "source_document_logging_allowed": False,
            "position_logging_allowed": False,
            "symbol_logging_allowed": False,
            "context_hash_response_embedding_allowed": False,
            "source_hash_response_embedding_allowed": True,
            "projection_response_only": True,
        },
        "unregistered_controls": _unregistered_controls(),
        "activation_order": [
            "VERIFY_EXACT_ADR0318_MOUNT_PREREGISTRATION_AND_SOURCE_PINS",
            "REGISTER_AUTHENTICATED_REQUEST_SCOPE_PROVIDER",
            "REGISTER_TRUSTED_SOURCE_CHAIN_RESOLVER",
            "IMPLEMENT_CONTEXT_PROVIDER_IN_SEPARATE_VERSION",
            "REGISTER_CONTEXT_GENERATION_ID_AND_SINGLE_USE_GUARD",
            "REGISTER_CONTEXT_REDACTION_POLICY",
            "COMPLETE_INDEPENDENT_CONTEXT_REVIEW",
            "BIND_CONTEXT_PROVIDER_TO_HANDLER_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
            "KEEP_ROUTE_UNREGISTERED_UNTIL_ALL_ADR0318_CONTROLS_PASS",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "mount_preregistration_exactly_pinned": True,
            "context_shape_preregistered": True,
            "context_role_order_pinned": True,
            "request_local_lifecycle_preregistered": True,
            "client_override_forbidden": True,
            "context_provider_implemented": False,
            "request_scope_provider_present": False,
            "source_chain_resolver_present": False,
            "single_use_guard_present": False,
            "redaction_policy_present": False,
            "handler_bound": False,
            "route_registered": False,
            "externally_callable": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(CONTEXT_BLOCKERS),
        "authority": _authority(),
        "decision": (
            "ADR0318_MOUNT_POLICY_AND_EXACT_ADR0317_CONTEXT_SHAPE_PINNED_"
            "REQUEST_LOCAL_SINGLE_USE_NO_CLOCK_NO_PERSISTENCE_CLIENT_OVERRIDE_"
            "FORBIDDEN_IMPLEMENTATION_HANDLER_ROUTE_CURRENT_PAPER_AND_LIVE_UNBOUND"
        ),
    }
    sealed = seal_strict_canonical_document(
        document,
        "context_provider_preregistration_hash",
    )
    _require_equal(
        "context provider preregistration hash",
        sealed.get("context_provider_preregistration_hash"),
        EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH,
    )
    return sealed


def verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
    document: Any,
) -> bool:
    """Return true only for the exact safely snapshotted preregistration."""

    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "CONTEXT_BLOCKERS",
    "CONTEXT_PROVIDER_ID",
    "CONTEXT_SCHEMA_VERSION",
    "CONTEXT_SHAPE_HASH",
    "EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH",
    "KEYWORD_ROLES",
    "KEYWORD_ROLE_HASH",
    "POSITIONAL_ROLES",
    "POSITIONAL_ROLE_HASH",
    "PREDECESSOR_CONTRACT",
    "PREREGISTRATION_ID",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1",
    "verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1",
]
