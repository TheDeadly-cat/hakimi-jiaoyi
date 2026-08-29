"""Exact internal adapter candidate for the read-only correlation projection.

The adapter is synthetic, in-memory, and unregistered.  It binds the ADR0322
single-use context to the real ADR0317 projection callable without creating an
HTTP route or any runtime, persistence, paper, live, or trading authority.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from exchange_terminal.application.ports.portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 import (
    REQUEST_SCHEMA_VERSION as PROJECTION_REQUEST_SCHEMA_VERSION,
    RESPONSE_SCHEMA_VERSION as PROJECTION_RESPONSE_SCHEMA_VERSION,
    build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1 import (
    CALLABLE_IDENTITY_SCHEMA_VERSION as PROJECTION_CALLABLE_IDENTITY_SCHEMA_VERSION,
    EXPECTED_CALLABLE_IDENTITY_HASH as EXPECTED_PROJECTION_CALLABLE_IDENTITY_HASH,
    build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1,
    verify_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1,
)
from exchange_terminal.application.portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1 import (
    REQUEST_EVIDENCE_CONTRACT_HASH,
    verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_python_provider_binding_v1 import (
    EXPECTED_PROVIDER_BINDING_HASH,
    verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_request_scope_source_resolver_candidate_v1 import (
    CANDIDATE_CONTRACT_HASH as REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH,
    CONTEXT_SHAPE_HASH,
    KEYWORD_ROLE_ORDER_HASH,
    POSITIONAL_ROLE_ORDER_HASH,
    RequestLocalSourceContextCandidateV1,
    verify_context_consumption_receipt_v1,
    verify_context_creation_receipt_v1,
    verify_request_scope_evidence_candidate_v1,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_trusted_internal_context_provider_preregistration_v1 import (
    KEYWORD_ROLES,
    POSITIONAL_ROLES,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-readonly-projection-"
    "adapter-candidate-contract-v1"
)
ADAPTER_CONTRACT_MANIFEST_SCHEMA_VERSION="portfolio-correlation-admission-effective-budget-readonly-projection-adapter-contract-manifest-v1"
STATIC_FINGERPRINT="20260824-portfolio-correlation-admission-effective-budget-readonly-projection-adapter-candidate-v1-synthetic-unregistered-lock-4"
PROJECTION_SOURCE_SHA256 = (
    "14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc"
)
PROJECTION_CALLABLE_IDENTITY_HASH=EXPECTED_PROJECTION_CALLABLE_IDENTITY_HASH
PRIOR_ADAPTER_CONTRACT_HASH="ff4de40e1323657a1df6213616c9fd2c92e194f7545bee54bfe4108132e1333f"
ADAPTER_CONTRACT_HASH="c6e04132f9e773dfdf77fdbd4ef3255d102b6c0000918b6b3631f204f485215b"
PRIOR_PROVENANCE_ADAPTER_CONTRACT_HASH = (
    "b5a0894605088509d85e70163c77b6c9bcf8957469577f95f00a4e996bc8ad51"
)

_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_PROJECTION_RESPONSE_FIELDS = (
    "schema_version",
    "static_fingerprint",
    "projection_id",
    "interface_status",
    "state",
    "reason_code",
    "payload",
    "facts",
    "lineage",
    "transport",
    "authority",
    "blockers",
    "response_hash",
)
_BLOCKERS = (
    "UNREGISTERED_CANDIDATE",
    "SYNTHETIC_ONLY",
    "SECURITY_RECEIPT_SEMANTICS_UNVERIFIED",
    "REQUEST_SNAPSHOT_SYNTHETIC_ONLY",
    "SEMANTIC_VERIFICATION_REQUIRES_EPHEMERAL_SOURCE_DOCUMENTS",
    "HTTP_MOUNT_NOT_IMPLEMENTED",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "descriptive_research_only": True,
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

def build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1()->dict[str,Any]:
    body={"schema_version":ADAPTER_CONTRACT_MANIFEST_SCHEMA_VERSION,"adapter_schema_version":SCHEMA_VERSION,"static_fingerprint":STATIC_FINGERPRINT,"prior_adapter_contract_hash":PRIOR_ADAPTER_CONTRACT_HASH,"projection_source_sha256":PROJECTION_SOURCE_SHA256,"projection_callable_identity_schema_version":PROJECTION_CALLABLE_IDENTITY_SCHEMA_VERSION,"projection_callable_identity_hash":PROJECTION_CALLABLE_IDENTITY_HASH,"projection_request_schema_version":PROJECTION_REQUEST_SCHEMA_VERSION,"projection_response_schema_version":PROJECTION_RESPONSE_SCHEMA_VERSION,"request_evidence_contract_hash":REQUEST_EVIDENCE_CONTRACT_HASH,"request_scope_source_resolver_contract_hash":REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH,"provider_binding_contract_hash":EXPECTED_PROVIDER_BINDING_HASH,"context_shape_hash":CONTEXT_SHAPE_HASH,"positional_role_order_hash":POSITIONAL_ROLE_ORDER_HASH,"keyword_role_order_hash":KEYWORD_ROLE_ORDER_HASH}
    return {**body,"adapter_contract_hash":_canonical_hash(body)}
def verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1(document:Any)->bool:
    if not isinstance(document,Mapping):return False
    expected=build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1()
    return tuple(document)==tuple(expected) and document==expected and document.get("adapter_contract_hash")==ADAPTER_CONTRACT_HASH
def _adapter_contract_hash_is_exact()->bool:return verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1(build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1())


def _safe_snapshot(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _is_lower_hex_64(value: Any) -> bool:
    return isinstance(value, str) and _LOWER_HEX_64.fullmatch(value) is not None


def _seal(document: Mapping[str, Any], field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[field] = _canonical_hash(document)
    return sealed


def _projection_callable_identity_is_exact()->bool:
    return verify_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1(build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1(),build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1)


def _role_contract_is_exact() -> bool:
    return (
        len(POSITIONAL_ROLES) == 13
        and len(KEYWORD_ROLES) == 10
        and _canonical_hash(list(POSITIONAL_ROLES))
        == POSITIONAL_ROLE_ORDER_HASH
        and _canonical_hash(list(KEYWORD_ROLES)) == KEYWORD_ROLE_ORDER_HASH
    )


def _projection_response_seal_is_exact(document: Any) -> bool:
    if (
        not isinstance(document, Mapping)
        or tuple(document) != _PROJECTION_RESPONSE_FIELDS
        or document.get("schema_version") != PROJECTION_RESPONSE_SCHEMA_VERSION
        or not _is_lower_hex_64(document.get("response_hash"))
    ):
        return False
    unsigned = dict(document)
    supplied_hash = unsigned.pop("response_hash")
    expected_hash = _canonical_hash(unsigned)
    return hmac.compare_digest(supplied_hash, expected_hash)


def _build_adapter_envelope(
    *,
    request_contract_evidence_candidate: Mapping[str, Any],
    binding_snapshot: Mapping[str, Any],
    request_scope_evidence_candidate: Mapping[str, Any],
    creation_receipt: Mapping[str, Any],
    consumption_receipt: Mapping[str, Any],
    projection_response: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "adapter_state": "REAL_PROJECTION_EXECUTED_SYNTHETIC_INTERNAL_ONLY",
        "synthetic_only": True,
        "registered": False,
        "adapter_contract_hash": ADAPTER_CONTRACT_HASH,
        "adapter_contract_manifest_schema_version": ADAPTER_CONTRACT_MANIFEST_SCHEMA_VERSION,
        "prior_adapter_contract_hash": PRIOR_ADAPTER_CONTRACT_HASH,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "projection_callable_identity_schema_version": PROJECTION_CALLABLE_IDENTITY_SCHEMA_VERSION,
        "projection_callable_identity_hash": PROJECTION_CALLABLE_IDENTITY_HASH,
        "projection_source_sha256": PROJECTION_SOURCE_SHA256,
        "request_scope_source_resolver_contract_hash": (
            REQUEST_SCOPE_SOURCE_RESOLVER_CONTRACT_HASH
        ),
        "provider_binding_hash": binding_snapshot["provider_binding_hash"],
        "request_payload_hash": request_contract_evidence_candidate[
            "request_payload_hash"
        ],
        "request_contract_hash": request_contract_evidence_candidate[
            "request_contract_hash"
        ],
        "request_scope_evidence_hash": request_scope_evidence_candidate[
            "evidence_hash"
        ],
        "context_creation_receipt": deepcopy(creation_receipt),
        "context_consumption_receipt": deepcopy(consumption_receipt),
        "projection_response": deepcopy(projection_response),
        "projection_response_hash": projection_response["response_hash"],
        "evidence_verification_level": (
            "CONSISTENCY_ONLY_WITHOUT_EPHEMERAL_SOURCES"
        ),
        "role_binding": {
            "positional_roles": list(POSITIONAL_ROLES),
            "positional_role_order_hash": POSITIONAL_ROLE_ORDER_HASH,
            "keyword_roles": list(KEYWORD_ROLES),
            "keyword_role_order_hash": KEYWORD_ROLE_ORDER_HASH,
            "context_shape_hash": CONTEXT_SHAPE_HASH,
        },
        "facts": {
            "request_and_binding_snapshotted_once": True,
            "request_contract_derived_from_exact_snapshot": True,
            "request_contract_hash_matched_scope": True,
            "request_scope_exactly_verified": True,
            "creation_receipt_exactly_verified": True,
            "consumption_receipt_exactly_verified": True,
            "resolved_source_hashes_matched_receipt": True,
            "real_projection_callable_invoked_once": True,
            "projection_response_seal_verified": True,
            "consistency_verifier_proves_projection_provenance": False,
            "source_bearing_semantic_verifier_available": True,
            "source_documents_embedded": False,
            "request_local_context_discarded": True,
            "clockless": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(adapter, "adapter_hash")


def build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
    request_contract_evidence_candidate: Any,
    *,
    provider_binding_document: Any,
    request_scope_evidence_candidate: Any,
    request_local_source_context_candidate: Any,
) -> dict[str, Any] | None:
    """Consume one validated context and invoke the fixed projection once."""

    if (
        not _projection_callable_identity_is_exact()
        or not _adapter_contract_hash_is_exact()
        or not _role_contract_is_exact()
        or not verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request_contract_evidence_candidate
        )
        or not verify_request_scope_evidence_candidate_v1(
            request_scope_evidence_candidate
        )
        or request_scope_evidence_candidate["evidence"]["request_contract_hash"]
        != request_contract_evidence_candidate["request_contract_hash"]
        or type(request_local_source_context_candidate)
        is not RequestLocalSourceContextCandidateV1
        or request_local_source_context_candidate.consumed
    ):
        return None
    try:
        request_snapshot = _safe_snapshot(
            request_contract_evidence_candidate["request_snapshot"]
        )
        binding_snapshot = _safe_snapshot(provider_binding_document)
    except (TypeError, ValueError, OverflowError):
        return None
    if (
        not isinstance(request_snapshot, Mapping)
        or not isinstance(binding_snapshot, Mapping)
        or request_snapshot.get("schema_version")
        != PROJECTION_REQUEST_SCHEMA_VERSION
        or not verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
            binding_snapshot
        )
        or binding_snapshot.get("provider_binding_hash")
        != EXPECTED_PROVIDER_BINDING_HASH
    ):
        return None

    creation_receipt = request_local_source_context_candidate.receipt
    if not verify_context_creation_receipt_v1(
        creation_receipt,
        request_scope_evidence_candidate,
    ):
        return None
    resolved = request_local_source_context_candidate.resolve_once()
    if not isinstance(resolved, Mapping):
        return None
    positional_sources = resolved.get("positional_sources_in_contract_order")
    keyword_sources = resolved.get("keyword_sources_in_contract_order")
    consumption_receipt = resolved.get("consumption_receipt")
    if (
        not isinstance(positional_sources, list)
        or not isinstance(keyword_sources, list)
        or len(positional_sources) != len(POSITIONAL_ROLES)
        or len(keyword_sources) != len(KEYWORD_ROLES)
        or [_canonical_hash(value) for value in positional_sources]
        != creation_receipt["positional_source_hashes_in_contract_order"]
        or [_canonical_hash(value) for value in keyword_sources]
        != creation_receipt["keyword_source_hashes_in_contract_order"]
        or not verify_context_consumption_receipt_v1(
            consumption_receipt,
            creation_receipt,
            request_scope_evidence_candidate,
        )
    ):
        return None
    keyword_mapping = dict(zip(KEYWORD_ROLES, keyword_sources, strict=True))
    try:
        projection_response = build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
            request_snapshot,
            provider_binding_document=binding_snapshot,
            internal_provider_positional=positional_sources,
            internal_provider_keyword=keyword_mapping,
        )
    except Exception:
        return None
    if not _projection_response_seal_is_exact(projection_response):
        return None
    adapter = _build_adapter_envelope(
        request_contract_evidence_candidate=request_contract_evidence_candidate,
        binding_snapshot=binding_snapshot,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
        creation_receipt=creation_receipt,
        consumption_receipt=consumption_receipt,
        projection_response=projection_response,
    )
    positional_sources = None
    keyword_sources = None
    keyword_mapping = None
    return adapter


def verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
    document: Any,
    request_contract_evidence_candidate: Any,
    *,
    provider_binding_document: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    """Verify envelope consistency only, never projection provenance."""

    if (
        not isinstance(document, Mapping)
        or not _projection_callable_identity_is_exact()
        or not _adapter_contract_hash_is_exact()
        or not _role_contract_is_exact()
        or not verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
            request_contract_evidence_candidate
        )
        or not verify_request_scope_evidence_candidate_v1(
            request_scope_evidence_candidate
        )
        or request_scope_evidence_candidate["evidence"]["request_contract_hash"]
        != request_contract_evidence_candidate["request_contract_hash"]
    ):
        return False
    try:
        request_snapshot = _safe_snapshot(
            request_contract_evidence_candidate["request_snapshot"]
        )
        binding_snapshot = _safe_snapshot(provider_binding_document)
    except (TypeError, ValueError, OverflowError):
        return False
    if (
        not isinstance(request_snapshot, Mapping)
        or not isinstance(binding_snapshot, Mapping)
        or not verify_portfolio_correlation_admission_effective_budget_python_provider_binding_v1(
            binding_snapshot
        )
        or binding_snapshot.get("provider_binding_hash")
        != EXPECTED_PROVIDER_BINDING_HASH
    ):
        return False
    creation_receipt = document.get("context_creation_receipt")
    consumption_receipt = document.get("context_consumption_receipt")
    projection_response = document.get("projection_response")
    if (
        not verify_context_creation_receipt_v1(
            creation_receipt,
            request_scope_evidence_candidate,
        )
        or not verify_context_consumption_receipt_v1(
            consumption_receipt,
            creation_receipt,
            request_scope_evidence_candidate,
        )
        or not _projection_response_seal_is_exact(projection_response)
    ):
        return False
    try:
        expected = _build_adapter_envelope(
            request_contract_evidence_candidate=request_contract_evidence_candidate,
            binding_snapshot=binding_snapshot,
            request_scope_evidence_candidate=request_scope_evidence_candidate,
            creation_receipt=creation_receipt,
            consumption_receipt=consumption_receipt,
            projection_response=projection_response,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected


def verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1(
    document: Any,
    request_contract_evidence_candidate: Any,
    *,
    provider_binding_document: Any,
    request_scope_evidence_candidate: Any,
    internal_provider_positional: Any,
    internal_provider_keyword: Any,
) -> bool:
    """Source-bearing semantic gate for the synthetic adapter candidate."""

    if (
        not isinstance(internal_provider_positional, Sequence)
        or isinstance(internal_provider_positional, (str, bytes))
        or not isinstance(internal_provider_keyword, Mapping)
    ):
        return False
    try:
        request_snapshot = _safe_snapshot(
            request_contract_evidence_candidate["request_snapshot"]
        )
        binding_snapshot = _safe_snapshot(provider_binding_document)
        positional_snapshot = _safe_snapshot(list(internal_provider_positional))
        keyword_snapshot = _safe_snapshot(internal_provider_keyword)
    except (TypeError, ValueError, OverflowError):
        return False
    if (
        not isinstance(request_snapshot, Mapping)
        or not isinstance(binding_snapshot, Mapping)
        or not isinstance(positional_snapshot, list)
        or not isinstance(keyword_snapshot, Mapping)
        or len(positional_snapshot) != len(POSITIONAL_ROLES)
        or set(keyword_snapshot) != set(KEYWORD_ROLES)
    ):
        return False
    keyword_mapping = {
        role: keyword_snapshot[role]
        for role in KEYWORD_ROLES
    }
    if not verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1(
        document,
        request_contract_evidence_candidate,
        provider_binding_document=binding_snapshot,
        request_scope_evidence_candidate=request_scope_evidence_candidate,
    ):
        return False
    creation_receipt = document["context_creation_receipt"]
    if (
        [_canonical_hash(value) for value in positional_snapshot]
        != creation_receipt["positional_source_hashes_in_contract_order"]
        or [_canonical_hash(keyword_mapping[role]) for role in KEYWORD_ROLES]
        != creation_receipt["keyword_source_hashes_in_contract_order"]
    ):
        return False
    return verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
        document["projection_response"],
        request_snapshot,
        provider_binding_document=binding_snapshot,
        internal_provider_positional=positional_snapshot,
        internal_provider_keyword=keyword_mapping,
    )


__all__=[
    "ADAPTER_CONTRACT_HASH",
    "ADAPTER_CONTRACT_MANIFEST_SCHEMA_VERSION",
    "PROJECTION_CALLABLE_IDENTITY_HASH",
    "PROJECTION_CALLABLE_IDENTITY_SCHEMA_VERSION",
    "PROJECTION_SOURCE_SHA256",
    "PRIOR_ADAPTER_CONTRACT_HASH",
    "PRIOR_PROVENANCE_ADAPTER_CONTRACT_HASH",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1",
    "build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1",
    "verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1",
    "verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_consistency_candidate_v1",
    "verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1",
]
