from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

from exchange_terminal.application.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1 import (
    METHOD,
    REQUEST_EVIDENCE_CONTRACT_HASH,
    ROUTE,
    verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as SOURCE_RESOLVER_CONTRACT_HASH,
    verify_context_creation_receipt_v1,
    verify_request_scope_evidence_candidate_v1,
)
from exchange_terminal.services.strategy_correlation_matrix_geometry_budget_multi_window_presentation_trusted_adr0334_source_producer_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as SOURCE_PRODUCER_CONTRACT_HASH,
    verify_trusted_adr0334_source_production_receipt_v1,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "security-receipt-semantic-gate-candidate-contract-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "security-receipt-semantic-gate-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-"
    "security-receipt-semantic-gate-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-"
    "presentation-security-receipt-semantic-gate-candidate-v1-"
    "unregistered-lock-1"
)

PROVIDER_ROLES = ("authentication", "csrf", "origin")
_COMMON_RECEIPT_FIELDS = (
    "schema_version",
    "provider_registration_hash",
    "provider_callable_identity_hash",
    "request_scope_id",
    "context_generation_id",
    "request_contract_hash",
    "request_evidence_candidate_hash",
    "adr0334_evaluation_hash",
    "source_production_receipt_hash",
)
AUTHENTICATION_RECEIPT_FIELDS = _COMMON_RECEIPT_FIELDS + (
    "principal_binding_hash",
    "authentication_method_binding_hash",
    "authenticated",
    "receipt_nonce_hash",
    "receipt_hash",
)
CSRF_RECEIPT_FIELDS = _COMMON_RECEIPT_FIELDS + (
    "csrf_token_binding_hash",
    "session_binding_hash",
    "verified",
    "receipt_nonce_hash",
    "receipt_hash",
)
ORIGIN_RECEIPT_FIELDS = _COMMON_RECEIPT_FIELDS + (
    "normalized_origin_hash",
    "origin_policy_hash",
    "allowed",
    "receipt_nonce_hash",
    "receipt_hash",
)
AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH = (
    "00049f40df5bde5a1afba4805565c538c63f3446c2a7d63a76ad3ba53548280d"
)
CSRF_RECEIPT_FIELD_ORDER_HASH = (
    "898a56fa990a2844792422652fe9e02bcff96ce5bc8d69474d1c5b750281895e"
)
ORIGIN_RECEIPT_FIELD_ORDER_HASH = (
    "26e641bad6a0adb8bb8ba2f1d075bfdb955b4b2eb61a57cb24932ca9f2477191"
)
GATE_CONTRACT_HASH = (
    "f1da8347793aee5d57462ab2c46a38cce3dcd6889c78bb975a65a0b0c0a3e645"
)
EXPECTED_PREREGISTRATION_HASH = (
    "580e8b14d316c47b80c660bc7ad2236351e5daaa80f1246ee45fd4501c6be372"
)

_CROSS_BINDING_REQUIREMENTS = (
    "REQUEST_EVIDENCE_EXACT_VERIFY",
    "REQUEST_SCOPE_EXACT_VERIFY",
    "SCOPE_REQUEST_CONTRACT_HASH_EQUALS_DERIVED_EVIDENCE",
    "SOURCE_PRODUCTION_RECEIPT_EXACT_VERIFY",
    "CONTEXT_CREATION_RECEIPT_EXACT_VERIFY",
    "REQUEST_AND_PRODUCTION_EVALUATION_HASH_EQUAL",
    "METHOD_AND_ROUTE_EQUAL",
)
_ACTIVATION_ORDER = (
    "REGISTER_AUTHENTICATION_CSRF_ORIGIN_PROVIDER_IDENTITIES",
    "BIND_FIXED_SEMANTIC_VERIFIER_CALLABLES",
    "BIND_RECEIPT_ISSUER_TRUST",
    "VERIFY_RECEIPT_SCHEMA_SEAL_REQUEST_SCOPE_EVALUATION_AND_SOURCE_BINDINGS",
    "REGISTER_AUTHENTICATED_REQUEST_LIFECYCLE_OWNER",
    "IMPLEMENT_TRUSTED_INTERNAL_PROVIDER",
    "BIND_HANDLER_BY_SEPARATE_DECISION",
    "REGISTER_ROUTE_BY_SEPARATE_DECISION",
    "CONSIDER_CURRENT_BY_SEPARATE_DECISION",
)
_BLOCKERS = (
    "ADR0342_SYNTHETIC_GATE_ONLY",
    "SECURITY_PROVIDERS_UNREGISTERED",
    "SEMANTIC_VERIFIERS_UNBOUND",
    "RECEIPT_ISSUER_TRUST_UNAVAILABLE",
    "AUTHENTICATED_REQUEST_LIFECYCLE_OWNER_UNREGISTERED",
    "TRUSTED_INTERNAL_PROVIDER_IMPLEMENTATION_MISSING",
    "HANDLER_BINDING_UNAUTHORIZED",
    "ROUTE_NOT_REGISTERED",
    "CURRENT_ACTIVATION_NOT_AUTHORIZED",
    "PAPER_AND_LIVE_PERMISSION_NOT_AUTHORIZED",
)
_PROVIDER_BINDING_FIELDS = (
    "provider_id",
    "callable_identity_hash",
    "registration_hash",
    "registered",
    "semantic_verifier_bound",
    "receipt_issuer_trust_bound",
)
_PREREGISTRATION_FACT_FIELDS = (
    "cross_binding_contract_frozen",
    "provider_roles_frozen",
    "all_providers_registered",
    "all_semantic_verifiers_bound",
    "all_receipt_issuer_trust_bound",
    "self_reported_receipt_flags_authoritative",
    "self_reported_receipt_hash_match_authoritative",
    "semantic_success_state_enabled",
)
_EVALUATION_FACT_FIELDS = (
    "all_nonsecurity_cross_bindings_verified",
    "receipt_documents_hash_bound_when_json",
    "receipt_documents_semantically_inspected",
    "receipt_documents_embedded",
    "self_reported_authenticated_ignored",
    "self_reported_csrf_verified_ignored",
    "self_reported_origin_allowed_ignored",
    "self_reported_receipt_hash_match_authoritative",
    "security_semantics_verified",
    "authenticated_request_authorized",
    "lifecycle_activation_authorized",
    "semantic_success_state_enabled",
    "clockless",
    "runtime_assets_accessed",
    "runtime_mutations_performed",
    "profitability_proven",
)
_AUTHORITY_FIELDS = (
    "descriptive_research_only",
    "security_semantics_verified",
    "authenticated_request_authorized",
    "lifecycle_activation_authorized",
    "provider_binding_authorized",
    "http_registration_authorized",
    "runtime_activation_authorized",
    "current_admission_allowed",
    "paper_authorized",
    "live_authorized",
    "writer_allowed",
    "profitability_claimed",
)
_PREREGISTRATION_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "status",
    "gate_contract_hash",
    "request_evidence_contract_hash",
    "source_producer_contract_hash",
    "source_resolver_contract_hash",
    "provider_roles",
    "receipt_field_contracts",
    "cross_binding_requirements",
    "providers",
    "activation_order",
    "facts",
    "blockers",
    "authority",
    "preregistration_hash",
)
_EVALUATION_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "status",
    "gate_state",
    "permission_state",
    "synthetic_only",
    "registered",
    "gate_contract_hash",
    "preregistration_hash",
    "request_evidence_contract_hash",
    "source_producer_contract_hash",
    "source_resolver_contract_hash",
    "request_evidence_candidate_hash",
    "request_payload_hash",
    "request_contract_hash",
    "request_scope_candidate_hash",
    "request_scope_id",
    "context_generation_id",
    "adr0334_evaluation_hash",
    "source_production_receipt_hash",
    "context_creation_receipt_hash",
    "receipt_document_hashes",
    "scope_receipt_hashes",
    "self_reported_receipt_hashes",
    "self_reported_hash_matches_scope",
    "provider_states",
    "facts",
    "blockers",
    "authority",
    "evaluation_hash",
)


def _canonical_json_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (OverflowError, RecursionError, TypeError, ValueError):
        return None


def _canonical_hash(value: Any) -> str | None:
    payload = _canonical_json_bytes(value)
    if payload is None:
        return None
    return sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _has_exact_fields(value: Any, fields: tuple[str, ...]) -> bool:
    return type(value) is dict and tuple(value) == fields


def _authority() -> dict[str, bool]:
    return {
        "descriptive_research_only": True,
        "security_semantics_verified": False,
        "authenticated_request_authorized": False,
        "lifecycle_activation_authorized": False,
        "provider_binding_authorized": False,
        "http_registration_authorized": False,
        "runtime_activation_authorized": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_authorized": False,
        "writer_allowed": False,
        "profitability_claimed": False,
    }


def _provider_bindings() -> dict[str, dict[str, Any]]:
    return {
        role: {
            "provider_id": None,
            "callable_identity_hash": None,
            "registration_hash": None,
            "registered": False,
            "semantic_verifier_bound": False,
            "receipt_issuer_trust_bound": False,
        }
        for role in PROVIDER_ROLES
    }


def _receipt_field_contracts() -> dict[str, dict[str, Any]]:
    return {
        "authentication": {
            "fields": list(AUTHENTICATION_RECEIPT_FIELDS),
            "field_order_hash": AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH,
        },
        "csrf": {
            "fields": list(CSRF_RECEIPT_FIELDS),
            "field_order_hash": CSRF_RECEIPT_FIELD_ORDER_HASH,
        },
        "origin": {
            "fields": list(ORIGIN_RECEIPT_FIELDS),
            "field_order_hash": ORIGIN_RECEIPT_FIELD_ORDER_HASH,
        },
    }


def _candidate_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "preregistration_schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "evaluation_schema_version": EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "source_producer_contract_hash": SOURCE_PRODUCER_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "provider_roles": list(PROVIDER_ROLES),
        "receipt_field_contracts": _receipt_field_contracts(),
        "cross_binding_requirements": list(_CROSS_BINDING_REQUIREMENTS),
        "semantic_success_state_enabled": False,
        "status": "UNKNOWN",
        "registered": False,
    }


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1() -> dict[str, Any]:
    document_without_hash = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNREGISTERED",
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "source_producer_contract_hash": SOURCE_PRODUCER_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "provider_roles": list(PROVIDER_ROLES),
        "receipt_field_contracts": _receipt_field_contracts(),
        "cross_binding_requirements": list(_CROSS_BINDING_REQUIREMENTS),
        "providers": _provider_bindings(),
        "activation_order": list(_ACTIVATION_ORDER),
        "facts": {
            "cross_binding_contract_frozen": True,
            "provider_roles_frozen": True,
            "all_providers_registered": False,
            "all_semantic_verifiers_bound": False,
            "all_receipt_issuer_trust_bound": False,
            "self_reported_receipt_flags_authoritative": False,
            "self_reported_receipt_hash_match_authoritative": False,
            "semantic_success_state_enabled": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    preregistration_hash = _canonical_hash(document_without_hash)
    if preregistration_hash is None:
        raise RuntimeError("preregistration must be hashable")
    return {**document_without_hash, "preregistration_hash": preregistration_hash}


def _role_mapping_has_exact_fields(value: Any) -> bool:
    return type(value) is dict and tuple(value) == PROVIDER_ROLES


def _provider_states_are_exact(value: Any) -> bool:
    return _role_mapping_has_exact_fields(value) and all(
        _has_exact_fields(value[role], _PROVIDER_BINDING_FIELDS)
        for role in PROVIDER_ROLES
    )


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1(
    document: Any,
) -> bool:
    if not _has_exact_fields(document, _PREREGISTRATION_FIELDS):
        return False
    if not _provider_states_are_exact(document.get("providers")):
        return False
    if not _has_exact_fields(document.get("facts"), _PREREGISTRATION_FACT_FIELDS):
        return False
    if not _has_exact_fields(document.get("authority"), _AUTHORITY_FIELDS):
        return False
    return (
        document
        == build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1()
        and document["preregistration_hash"] == EXPECTED_PREREGISTRATION_HASH
    )


def _cross_bindings_verify(
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
) -> bool:
    if not verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_request_contract_evidence_candidate_v1(
        request_contract_evidence_candidate
    ):
        return False
    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return False
    if not verify_context_creation_receipt_v1(
        request_local_context_creation_receipt,
        request_scope_evidence_candidate,
    ):
        return False
    if not verify_trusted_adr0334_source_production_receipt_v1(
        source_production_receipt,
        request_scope_evidence_candidate,
        request_local_context_creation_receipt,
    ):
        return False
    evidence = request_scope_evidence_candidate["evidence"]
    return (
        evidence["request_contract_hash"]
        == request_contract_evidence_candidate["request_contract_hash"]
        and evidence["method"] == request_contract_evidence_candidate["method"] == METHOD
        and evidence["route"] == request_contract_evidence_candidate["route"] == ROUTE
        and request_contract_evidence_candidate["adr0334_evaluation_hash"]
        == source_production_receipt["adr0334_evaluation_hash"]
    )


def _document_hash_or_none(value: Any) -> str | None:
    return _canonical_hash(value)


def _self_reported_receipt_hash_or_none(value: Any) -> str | None:
    if type(value) is not dict:
        return None
    receipt_hash = value.get("receipt_hash")
    return receipt_hash if _is_sha256(receipt_hash) else None


def build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
    preregistration_document: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    *,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> dict[str, Any] | None:
    if not verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1(
        preregistration_document
    ):
        return None
    if not _cross_bindings_verify(
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
        source_production_receipt,
        request_local_context_creation_receipt,
    ):
        return None
    receipt_documents = {
        "authentication": authentication_receipt_document,
        "csrf": csrf_receipt_document,
        "origin": origin_receipt_document,
    }
    receipt_document_hashes = {
        role: _document_hash_or_none(receipt_documents[role])
        for role in PROVIDER_ROLES
    }
    evidence = request_scope_evidence_candidate["evidence"]
    scope_receipt_hashes = {
        "authentication": evidence["authentication_receipt_hash"],
        "csrf": evidence["csrf_receipt_hash"],
        "origin": evidence["origin_receipt_hash"],
    }
    self_reported_receipt_hashes = {
        role: _self_reported_receipt_hash_or_none(receipt_documents[role])
        for role in PROVIDER_ROLES
    }
    self_reported_hash_matches_scope = {
        role: (
            self_reported_receipt_hashes[role] is not None
            and self_reported_receipt_hashes[role] == scope_receipt_hashes[role]
        )
        for role in PROVIDER_ROLES
    }
    request_scope_candidate_hash = _canonical_hash(
        request_scope_evidence_candidate
    )
    context_creation_receipt_hash = _canonical_hash(
        request_local_context_creation_receipt
    )
    if request_scope_candidate_hash is None or context_creation_receipt_hash is None:
        raise RuntimeError("verified scope and context receipts must be hashable")
    evaluation_without_hash = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "gate_state": "SECURITY_SEMANTICS_UNAVAILABLE",
        "permission_state": "UNAUTHORIZED",
        "synthetic_only": True,
        "registered": False,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "preregistration_hash": EXPECTED_PREREGISTRATION_HASH,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "source_producer_contract_hash": SOURCE_PRODUCER_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "request_evidence_candidate_hash": request_contract_evidence_candidate[
            "candidate_hash"
        ],
        "request_payload_hash": request_contract_evidence_candidate[
            "request_payload_hash"
        ],
        "request_contract_hash": request_contract_evidence_candidate[
            "request_contract_hash"
        ],
        "request_scope_candidate_hash": request_scope_candidate_hash,
        "request_scope_id": evidence["request_scope_id"],
        "context_generation_id": evidence["context_generation_id"],
        "adr0334_evaluation_hash": request_contract_evidence_candidate[
            "adr0334_evaluation_hash"
        ],
        "source_production_receipt_hash": source_production_receipt[
            "production_receipt_hash"
        ],
        "context_creation_receipt_hash": context_creation_receipt_hash,
        "receipt_document_hashes": receipt_document_hashes,
        "scope_receipt_hashes": scope_receipt_hashes,
        "self_reported_receipt_hashes": self_reported_receipt_hashes,
        "self_reported_hash_matches_scope": self_reported_hash_matches_scope,
        "provider_states": _provider_bindings(),
        "facts": {
            "all_nonsecurity_cross_bindings_verified": True,
            "receipt_documents_hash_bound_when_json": True,
            "receipt_documents_semantically_inspected": False,
            "receipt_documents_embedded": False,
            "self_reported_authenticated_ignored": True,
            "self_reported_csrf_verified_ignored": True,
            "self_reported_origin_allowed_ignored": True,
            "self_reported_receipt_hash_match_authoritative": False,
            "security_semantics_verified": False,
            "authenticated_request_authorized": False,
            "lifecycle_activation_authorized": False,
            "semantic_success_state_enabled": False,
            "clockless": True,
            "runtime_assets_accessed": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": _authority(),
    }
    evaluation_hash = _canonical_hash(evaluation_without_hash)
    if evaluation_hash is None:
        raise RuntimeError("gate evaluation must be hashable")
    return {**evaluation_without_hash, "evaluation_hash": evaluation_hash}


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
    document: Any,
    preregistration_document: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    source_production_receipt: Any,
    request_local_context_creation_receipt: Any,
    *,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> bool:
    if not _has_exact_fields(document, _EVALUATION_FIELDS):
        return False
    for field in (
        "receipt_document_hashes",
        "scope_receipt_hashes",
        "self_reported_receipt_hashes",
        "self_reported_hash_matches_scope",
    ):
        if not _role_mapping_has_exact_fields(document.get(field)):
            return False
    if not _provider_states_are_exact(document.get("provider_states")):
        return False
    if not _has_exact_fields(document.get("facts"), _EVALUATION_FACT_FIELDS):
        return False
    if not _has_exact_fields(document.get("authority"), _AUTHORITY_FIELDS):
        return False
    expected = build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1(
        preregistration_document,
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
        source_production_receipt,
        request_local_context_creation_receipt,
        authentication_receipt_document=authentication_receipt_document,
        csrf_receipt_document=csrf_receipt_document,
        origin_receipt_document=origin_receipt_document,
    )
    return expected is not None and document == expected


if _canonical_hash(list(AUTHENTICATION_RECEIPT_FIELDS)) != (
    AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH
):
    raise RuntimeError("authentication receipt field-order hash drifted")
if _canonical_hash(list(CSRF_RECEIPT_FIELDS)) != CSRF_RECEIPT_FIELD_ORDER_HASH:
    raise RuntimeError("CSRF receipt field-order hash drifted")
if _canonical_hash(list(ORIGIN_RECEIPT_FIELDS)) != ORIGIN_RECEIPT_FIELD_ORDER_HASH:
    raise RuntimeError("origin receipt field-order hash drifted")
if _canonical_hash(_candidate_contract()) != GATE_CONTRACT_HASH:
    raise RuntimeError("ADR0342 gate contract hash drifted")
if build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1()[
    "preregistration_hash"
] != EXPECTED_PREREGISTRATION_HASH:
    raise RuntimeError("ADR0342 preregistration hash drifted")


__all__ = [
    "AUTHENTICATION_RECEIPT_FIELDS",
    "AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH",
    "CSRF_RECEIPT_FIELDS",
    "CSRF_RECEIPT_FIELD_ORDER_HASH",
    "EVALUATION_SCHEMA_VERSION",
    "EXPECTED_PREREGISTRATION_HASH",
    "GATE_CONTRACT_HASH",
    "ORIGIN_RECEIPT_FIELDS",
    "ORIGIN_RECEIPT_FIELD_ORDER_HASH",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_ROLES",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1",
    "build_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_evaluation_v1",
    "verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_security_receipt_semantic_gate_preregistration_v1",
]
