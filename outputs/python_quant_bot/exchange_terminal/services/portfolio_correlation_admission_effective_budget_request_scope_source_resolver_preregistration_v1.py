"""Preregister request-scope evidence and source-resolver contracts only."""

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
from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1 as context_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-scope-source-"
    "resolver-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-request-scope-"
    "source-resolver-preregistration-v1-unbound-lock-1"
)
PREREGISTRATION_ID = (
    "portfolio-correlation-admission-effective-budget-request-scope-source-"
    "resolver-v1"
)
REQUEST_SCOPE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-authenticated-request-"
    "scope-evidence-v1"
)
SOURCE_RESOLVER_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-trusted-source-chain-"
    "resolver-v1"
)
CROSS_BINDING_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-scope-source-"
    "resolver-binding-v1"
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
    "e59927ea8ef3ef38a83647792a0a009a8ad022c959b14828119f5fa464769728"
)
SOURCE_RESOLVER_CONTRACT_HASH = (
    "7337b858ae1f1de7de0778347724f2c5d67690edce227fb5410759f8c55dee1a"
)
CROSS_BINDING_CONTRACT_HASH = (
    "205454c6cd6e3829d7d19bdc52f0ebe3212bceddff50fa81067dd18c41eba91f"
)
EXPECTED_SCOPE_RESOLVER_PREREGISTRATION_HASH = (
    "8f2f3521a280610163f690ee53e414fabd48ae5dfc9f1ce0977457b9a959f72d"
)

PREDECESSOR_CONTRACT = {
    "context_provider_preregistration_hash": (
        "14e08fb0d46ea1738e77c416ebc49506430778ce025c45d500130c722ea31cff"
    ),
    "context_preregistration_implementation_path": (
        "exchange_terminal/services/portfolio_correlation_admission_effective_"
        "budget_trusted_internal_context_provider_preregistration_v1.py"
    ),
    "context_preregistration_implementation_sha256": (
        "9bf879b85723d15575a08da26e3a0d4ca932c10db56ceadcc93eab10828b5e65"
    ),
    "context_preregistration_test_path": (
        "tests/test_portfolio_correlation_admission_effective_budget_trusted_"
        "internal_context_provider_preregistration_v1.py"
    ),
    "context_preregistration_test_sha256": (
        "333a1e24f13aaf47a378f98a390361f07cce753906fd8c91c9a8d1271a72edc1"
    ),
    "context_preregistration_adr_path": (
        "docs/adr/0319-portfolio-correlation-admission-effective-budget-"
        "trusted-internal-context-provider-preregistration-v1.md"
    ),
    "context_preregistration_adr_sha256": (
        "1c36e7eae3cacd2a99d3954a2fc79f3f16a949fafc8705afe426535b682f51d9"
    ),
    "context_shape_hash": context_preregistration.CONTEXT_SHAPE_HASH,
    "positional_role_hash": context_preregistration.POSITIONAL_ROLE_HASH,
    "keyword_role_hash": context_preregistration.KEYWORD_ROLE_HASH,
    "mount_preregistration_hash": (
        mount_preregistration.EXPECTED_MOUNT_PREREGISTRATION_HASH
    ),
    "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
}

SCOPE_RESOLVER_BLOCKERS = (
    "ADR0320_PREREGISTRATION_ONLY",
    "AUTHENTICATION_RECEIPT_PROVIDER_UNREGISTERED",
    "CSRF_RECEIPT_PROVIDER_UNREGISTERED",
    "ORIGIN_RECEIPT_PROVIDER_UNREGISTERED",
    "REQUEST_SCOPE_ID_PROVIDER_UNREGISTERED",
    "CONTEXT_GENERATION_ID_PROVIDER_UNREGISTERED",
    "TRUSTED_SOURCE_CHAIN_RESOLVER_IMPLEMENTATION_MISSING",
    "SINGLE_USE_GUARD_UNREGISTERED",
    "INDEPENDENT_SCOPE_RESOLVER_BINDING_REVIEW_REQUIRED",
    "CONTEXT_PROVIDER_IMPLEMENTATION_MISSING",
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
    document = context_preregistration.build_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1()
    if not context_preregistration.verify_portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1(
        document
    ):
        raise ValueError("ADR0319 context preregistration is not exact")
    _require_equal(
        "ADR0319 preregistration hash",
        document.get("context_provider_preregistration_hash"),
        PREDECESSOR_CONTRACT["context_provider_preregistration_hash"],
    )
    if document["binding_contract"]["registered"] is not False:
        raise ValueError("ADR0319 context binding must remain unregistered")
    for key in (
        "context_provider_implementation",
        "request_scope_provider",
        "single_use_guard",
        "handler_binding",
        "route_binding",
    ):
        if document["binding_contract"][key] is not None:
            raise ValueError(f"ADR0319 binding slot {key} must remain null")


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
        "input_context_shape_hash": context_preregistration.CONTEXT_SHAPE_HASH,
        "input_positional_role_hash": context_preregistration.POSITIONAL_ROLE_HASH,
        "input_keyword_role_hash": context_preregistration.KEYWORD_ROLE_HASH,
        "output_context_schema_version": context_preregistration.CONTEXT_SCHEMA_VERSION,
        "source_mode": "EXPLICIT_ADR0311_INTERNAL_DOCUMENT_CHAIN_ONLY",
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
        "context_provider_preregistration_hash": (
            context_preregistration.EXPECTED_CONTEXT_PROVIDER_PREREGISTRATION_HASH
        ),
        "mount_preregistration_hash": (
            mount_preregistration.EXPECTED_MOUNT_PREREGISTRATION_HASH
        ),
        "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
        "projection_id": projection_candidate.PROJECTION_ID,
        "method": mount_preregistration.PROPOSED_METHOD,
        "route": mount_preregistration.PROPOSED_ROUTE,
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
        "cross-binding contract hash",
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
        "context_provider_implementation_allowed": False,
        "handler_binding_allowed": False,
        "route_registration_allowed": False,
        "external_call_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1() -> dict[str, Any]:
    """Build the exact blocked dual-contract preregistration."""

    _verify_predecessor()
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "preregistration_id": PREREGISTRATION_ID,
        "status": "BLOCKED",
        "registration_state": (
            "REQUEST_SCOPE_EVIDENCE_SOURCE_RESOLVER_AND_CROSS_BINDING_"
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
            "VERIFY_EXACT_ADR0319_CONTEXT_PREREGISTRATION_AND_SOURCE_PINS",
            "REGISTER_AUTHENTICATION_CSRF_AND_ORIGIN_RECEIPT_PROVIDERS",
            "REGISTER_REQUEST_SCOPE_AND_CONTEXT_GENERATION_ID_PROVIDERS",
            "IMPLEMENT_TRUSTED_SOURCE_CHAIN_RESOLVER_IN_SEPARATE_VERSION",
            "REGISTER_SINGLE_USE_GUARD",
            "COMPLETE_INDEPENDENT_SCOPE_RESOLVER_BINDING_REVIEW",
            "IMPLEMENT_CONTEXT_PROVIDER_ONLY_AFTER_ALL_SUBCONTRACTS_VERIFY",
            "BIND_HANDLER_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
            "KEEP_ROUTE_UNREGISTERED_UNTIL_ALL_ADR0318_CONTROLS_PASS",
            "CONSIDER_CURRENT_ONLY_BY_SEPARATE_EXPLICIT_DECISION",
        ],
        "facts": {
            "context_preregistration_exactly_pinned": True,
            "request_scope_contract_preregistered": True,
            "source_resolver_contract_preregistered": True,
            "cross_binding_contract_preregistered": True,
            "request_scope_evidence_producer_present": False,
            "security_receipt_providers_present": False,
            "source_resolver_implemented": False,
            "single_use_guard_present": False,
            "cross_binding_registered": False,
            "context_provider_implemented": False,
            "handler_bound": False,
            "route_registered": False,
            "externally_callable": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(SCOPE_RESOLVER_BLOCKERS),
        "authority": _authority(),
        "decision": (
            "ADR0319_CONTEXT_SHAPE_BOUND_TO_SEPARATE_HASH_ONLY_REQUEST_SCOPE_"
            "EVIDENCE_AND_EXPLICIT_SOURCE_RESOLVER_CONTRACTS_ALL_SECURITY_"
            "PRODUCERS_RESOLVER_GUARD_CONTEXT_HANDLER_ROUTE_CURRENT_PAPER_AND_"
            "LIVE_UNREGISTERED"
        ),
    }
    sealed = seal_strict_canonical_document(
        document,
        "scope_resolver_preregistration_hash",
    )
    _require_equal(
        "scope resolver preregistration hash",
        sealed.get("scope_resolver_preregistration_hash"),
        EXPECTED_SCOPE_RESOLVER_PREREGISTRATION_HASH,
    )
    return sealed


def verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1(
    document: Any,
) -> bool:
    """Return true only for the exact safely snapshotted preregistration."""

    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1()
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "CROSS_BINDING_CONTRACT_HASH",
    "CROSS_BINDING_SCHEMA_VERSION",
    "EXPECTED_SCOPE_RESOLVER_PREREGISTRATION_HASH",
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
    "build_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1",
    "verify_portfolio_correlation_admission_effective_budget_request_scope_source_resolver_preregistration_v1",
]
