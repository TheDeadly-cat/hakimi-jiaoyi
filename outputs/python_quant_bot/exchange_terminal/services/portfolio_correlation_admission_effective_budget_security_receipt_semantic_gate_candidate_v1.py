"""Fail-closed security-receipt semantic gate with no success path."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    REQUEST_EVIDENCE_CONTRACT_HASH,
    verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH,
    verify_request_scope_evidence_candidate_v1,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-security-receipt-"
    "semantic-gate-candidate-contract-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-security-receipt-"
    "semantic-gate-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-security-receipt-"
    "semantic-gate-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-security-receipt-"
    "semantic-gate-candidate-v1-unregistered-lock-1"
)
PROVIDER_ROLES = ("authentication", "csrf", "origin")
AUTHENTICATION_RECEIPT_FIELDS = (
    "schema_version",
    "provider_registration_hash",
    "request_scope_id",
    "request_contract_hash",
    "principal_binding_hash",
    "authentication_method_binding_hash",
    "authenticated",
    "receipt_nonce_hash",
    "receipt_hash",
)
CSRF_RECEIPT_FIELDS = (
    "schema_version",
    "provider_registration_hash",
    "request_scope_id",
    "request_contract_hash",
    "csrf_token_binding_hash",
    "session_binding_hash",
    "verified",
    "receipt_nonce_hash",
    "receipt_hash",
)
ORIGIN_RECEIPT_FIELDS = (
    "schema_version",
    "provider_registration_hash",
    "request_scope_id",
    "request_contract_hash",
    "normalized_origin_hash",
    "origin_policy_hash",
    "allowed",
    "receipt_nonce_hash",
    "receipt_hash",
)
AUTHENTICATION_RECEIPT_FIELD_ORDER_HASH = (
    "99f62ad29526d6976aed07597e778b5163f60f66549148263cafa3d7b635901b"
)
CSRF_RECEIPT_FIELD_ORDER_HASH = (
    "5913900c17d29f5577c260944e9180a7e89429ef2cd569ae2b0da0e8dda78f69"
)
ORIGIN_RECEIPT_FIELD_ORDER_HASH = (
    "f60dd627e4568d19703aa8d108460ad1d092791a351a71a9cbcce2c0a5ad3197"
)
GATE_CONTRACT_HASH = (
    "141b844a7e43fc069921aefc99214d4d8cb1ee63f80408f249899d29839bad71"
)
EXPECTED_PREREGISTRATION_HASH = (
    "9a0455aba48d9b3361aed84428b101c82352833cb3a32e09960b34afe46ab72f"
)

_ACTIVATION_ORDER = (
    "REGISTER_PROVIDER_IDENTITIES",
    "BIND_VERIFIER_CALLABLES",
    "VERIFY_RECEIPT_ISSUER_AND_REQUEST_BINDING",
    "ACTIVATE_INTERNAL_LIFECYCLE_CONSUMER",
    "CONSIDER_HTTP_MOUNT",
)
_BLOCKERS = (
    "SECURITY_PROVIDERS_UNREGISTERED",
    "SEMANTIC_VERIFIER_CALLABLES_UNBOUND",
    "RECEIPT_ISSUER_TRUST_UNAVAILABLE",
    "AUTHENTICATED_REQUEST_OWNER_NOT_REGISTERED",
    "HTTP_MOUNT_NOT_IMPLEMENTED",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "descriptive_research_only": True,
    "security_semantics_verified": False,
    "authenticated_request_authorized": False,
    "lifecycle_activation_authorized": False,
    "http_registration_authorized": False,
    "runtime_activation_authorized": False,
    "paper_authorized": False,
    "live_authorized": False,
    "profitability_claimed": False,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _seal(document: Mapping[str, Any], field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[field] = _canonical_hash(document)
    return sealed


def _provider_bindings() -> dict[str, dict[str, Any]]:
    return {
        role: {
            "provider_id": None,
            "callable_identity_hash": None,
            "registration_hash": None,
            "registered": False,
            "semantic_verifier_bound": False,
        }
        for role in PROVIDER_ROLES
    }


def build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1() -> dict[str, Any]:
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNREGISTERED",
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "provider_roles": list(PROVIDER_ROLES),
        "receipt_field_contracts": {
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
        },
        "providers": _provider_bindings(),
        "activation_order": list(_ACTIVATION_ORDER),
        "facts": {
            "all_providers_registered": False,
            "all_semantic_verifiers_bound": False,
            "self_reported_receipt_flags_authoritative": False,
            "opaque_hashes_prove_semantics": False,
            "semantic_success_state_enabled": False,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(document, "preregistration_hash")


def verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1(
    document: Any,
) -> bool:
    return (
        isinstance(document, Mapping)
        and document
        == build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1()
        and document.get("preregistration_hash")
        == EXPECTED_PREREGISTRATION_HASH
    )


def _document_hash_or_none(value: Any) -> str | None:
    try:
        return _canonical_hash(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _request_and_scope_are_bound(
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    return (
        verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request_contract_evidence_candidate
        )
        and verify_request_scope_evidence_candidate_v1(
            request_scope_evidence_candidate
        )
        and request_scope_evidence_candidate["evidence"]["request_contract_hash"]
        == request_contract_evidence_candidate["request_contract_hash"]
    )


def build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
    preregistration_document: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    *,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> dict[str, Any] | None:
    """Return UNKNOWN while every semantic provider remains unregistered."""

    if not verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1(
        preregistration_document
    ) or not _request_and_scope_are_bound(
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
    ):
        return None
    evidence = request_scope_evidence_candidate["evidence"]
    receipt_hashes = {
        "authentication": _document_hash_or_none(
            authentication_receipt_document
        ),
        "csrf": _document_hash_or_none(csrf_receipt_document),
        "origin": _document_hash_or_none(origin_receipt_document),
    }
    evaluation = {
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
        "request_scope_source_resolver_contract_hash": (
            REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH
        ),
        "request_candidate_hash": request_contract_evidence_candidate[
            "candidate_hash"
        ],
        "request_contract_hash": request_contract_evidence_candidate[
            "request_contract_hash"
        ],
        "request_scope_candidate_hash": request_scope_evidence_candidate[
            "candidate_hash"
        ],
        "request_scope_id": evidence["request_scope_id"],
        "receipt_document_hashes": receipt_hashes,
        "provider_states": _provider_bindings(),
        "facts": {
            "receipt_documents_hash_bound_when_json": True,
            "receipt_documents_semantically_inspected": False,
            "self_reported_authenticated_ignored": True,
            "self_reported_csrf_verified_ignored": True,
            "self_reported_origin_allowed_ignored": True,
            "security_semantics_verified": False,
            "lifecycle_activation_authorized": False,
            "semantic_success_state_enabled": False,
            "receipt_documents_embedded": False,
            "clockless": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(evaluation, "evaluation_hash")


def verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
    document: Any,
    preregistration_document: Any,
    request_contract_evidence_candidate: Any,
    request_scope_evidence_candidate: Any,
    *,
    authentication_receipt_document: Any = None,
    csrf_receipt_document: Any = None,
    origin_receipt_document: Any = None,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    expected = build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1(
        preregistration_document,
        request_contract_evidence_candidate,
        request_scope_evidence_candidate,
        authentication_receipt_document=authentication_receipt_document,
        csrf_receipt_document=csrf_receipt_document,
        origin_receipt_document=origin_receipt_document,
    )
    return expected is not None and document == expected


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
    "build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1",
    "build_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1",
    "verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_evaluation_v1",
    "verify_portfolio_correlation_admission_effective_budget_security_receipt_semantic_gate_preregistration_v1",
]
