"""Synthetic, unregistered request-scope source resolver candidate.

This module is intentionally detached from HTTP, runtime state, persistence, and
trading authority.  It proves only deterministic hash binding, JSON-safe source
snapshotting, and one-shot in-memory consumption.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-scope-"
    "source-resolver-candidate-contract-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-request-scope-"
    "source-resolver-candidate-v1-synthetic-unregistered-lock-2"
)
REQUEST_SCOPE_EVIDENCE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-scope-"
    "evidence-candidate-v1"
)
CONTEXT_RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-local-source-"
    "context-candidate-receipt-v1"
)
CONSUMPTION_RECEIPT_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-local-source-"
    "context-consumption-receipt-v1"
)

SCOPE_RESOLVER_PREREGISTRATION_HASH = (
    "8f2f3521a280610163f690ee53e414fabd48ae5dfc9f1ce0977457b9a959f72d"
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
POSITIONAL_ROLE_ORDER_HASH = (
    "1c1652d5ff99d81b063678e20bc8b5e621c718df34c249028884a24349a9f8b2"
)
KEYWORD_ROLE_ORDER_HASH = (
    "24672b9e3d2501291d683ac83803c112846578e8a230a18409346acb3ab05edb"
)
CONTEXT_SHAPE_HASH = (
    "c7d53837786e478a6b2341463594ac0c6a8d348d1a1eb3458a0e8eed11772d43"
)
PRIOR_CANDIDATE_CONTRACT_HASH = (
    "5524137b7e093a197cdfaa256263540a3f50f09cb87d222bed084989d7fa3ac5"
)
CANDIDATE_CONTRACT_HASH = (
    "7fd73f90c797621c2df621cf5163bf9c83ba77d49f3262518c6c0a7cb72c72b1"
)

PROPOSED_METHOD = "POST"
PROPOSED_ROUTE = (
    "/api/v1/research/portfolio-correlation/admission-effective-budget"
)
POSITIONAL_SOURCE_COUNT = 13
KEYWORD_SOURCE_COUNT = 10
MAXIMUM_RESOLUTION_COUNT = 1
MAXIMUM_CANONICAL_CONTEXT_BYTES = 1_000_000

_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_FIELDS = (
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
_BLOCKERS = (
    "UNREGISTERED_CANDIDATE",
    "SYNTHETIC_ONLY",
    "SECURITY_RECEIPT_SEMANTICS_UNVERIFIED",
    "REQUEST_CONTRACT_CONTENT_UNVERIFIED",
    "HTTP_MOUNT_NOT_IMPLEMENTED",
    "AUTHENTICATION_NOT_PERFORMED",
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
_CONSTRUCTION_TOKEN = object()


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


def _is_lower_hex_64(value: Any) -> bool:
    return isinstance(value, str) and _LOWER_HEX_64.fullmatch(value) is not None


def _safe_json_snapshot(value: Any) -> Any:
    encoded = _canonical_json(value)
    if len(encoded.encode("utf-8")) > MAXIMUM_CANONICAL_CONTEXT_BYTES:
        raise ValueError("canonical source context exceeds the candidate limit")
    return json.loads(encoded)


def _seal(document: Mapping[str, Any], seal_field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[seal_field] = _canonical_hash(document)
    return sealed


def _hash_matches(left: Any, right: Any) -> bool:
    return (
        _is_lower_hex_64(left)
        and _is_lower_hex_64(right)
        and hmac.compare_digest(left, right)
    )


def build_request_scope_evidence_candidate_v1(
    *,
    scope_resolver_preregistration_hash: str,
    request_scope_id: str,
    authentication_receipt_hash: str,
    csrf_receipt_hash: str,
    origin_receipt_hash: str,
    request_contract_hash: str,
    context_generation_id: str,
) -> dict[str, Any] | None:
    """Build a hash-only synthetic request-scope evidence candidate.

    Receipt hashes are treated as opaque identifiers.  Their security meaning is
    deliberately not verified by this candidate.
    """

    supplied_hashes = (
        request_scope_id,
        authentication_receipt_hash,
        csrf_receipt_hash,
        origin_receipt_hash,
        request_contract_hash,
        context_generation_id,
    )
    if not _hash_matches(
        scope_resolver_preregistration_hash,
        SCOPE_RESOLVER_PREREGISTRATION_HASH,
    ) or not all(_is_lower_hex_64(value) for value in supplied_hashes):
        return None

    evidence = {
        "schema_version": REQUEST_SCOPE_EVIDENCE_SCHEMA_VERSION,
        "request_scope_id": request_scope_id,
        "authentication_receipt_hash": authentication_receipt_hash,
        "csrf_receipt_hash": csrf_receipt_hash,
        "origin_receipt_hash": origin_receipt_hash,
        "request_contract_hash": request_contract_hash,
        "method": PROPOSED_METHOD,
        "route": PROPOSED_ROUTE,
        "context_generation_id": context_generation_id,
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "consumed": False,
    }
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "candidate_state": "HASH_BOUND_SYNTHETIC_REQUEST_SCOPE",
        "synthetic_only": True,
        "registered": False,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "prior_candidate_contract_hash": PRIOR_CANDIDATE_CONTRACT_HASH,
        "scope_resolver_preregistration_hash": (
            SCOPE_RESOLVER_PREREGISTRATION_HASH
        ),
        "request_scope_contract_hash": REQUEST_SCOPE_CONTRACT_HASH,
        "source_resolver_contract_hash": SOURCE_RESOLVER_CONTRACT_HASH,
        "cross_binding_contract_hash": CROSS_BINDING_CONTRACT_HASH,
        "evidence": evidence,
        "evidence_hash": _canonical_hash(evidence),
        "facts": {
            "field_order_exact": tuple(evidence) == _EVIDENCE_FIELDS,
            "hash_shapes_validated": True,
            "security_receipts_hash_bound": True,
            "security_receipts_semantically_verified": False,
            "request_contract_content_verified": False,
            "authentication_performed": False,
            "source_documents_embedded": False,
            "request_local_only": True,
            "clockless": True,
            "creation_receipt_exact_rebuild_verifier": True,
            "builder_only_context_construction": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(candidate, "candidate_hash")


def verify_request_scope_evidence_candidate_v1(document: Any) -> bool:
    if not isinstance(document, Mapping):
        return False
    evidence = document.get("evidence")
    if not isinstance(evidence, Mapping) or tuple(evidence) != _EVIDENCE_FIELDS:
        return False
    rebuilt = build_request_scope_evidence_candidate_v1(
        scope_resolver_preregistration_hash=document.get(
            "scope_resolver_preregistration_hash"
        ),
        request_scope_id=evidence.get("request_scope_id"),
        authentication_receipt_hash=evidence.get(
            "authentication_receipt_hash"
        ),
        csrf_receipt_hash=evidence.get("csrf_receipt_hash"),
        origin_receipt_hash=evidence.get("origin_receipt_hash"),
        request_contract_hash=evidence.get("request_contract_hash"),
        context_generation_id=evidence.get("context_generation_id"),
    )
    return rebuilt is not None and document == rebuilt


def _build_context_receipt_from_hashes(
    scope_candidate: Mapping[str, Any],
    positional_hashes: Sequence[str],
    keyword_hashes: Sequence[str],
) -> dict[str, Any]:
    evidence = scope_candidate["evidence"]
    context_binding = {
        "scope_evidence_hash": scope_candidate["evidence_hash"],
        "request_scope_id": evidence["request_scope_id"],
        "context_generation_id": evidence["context_generation_id"],
        "positional_role_order_hash": POSITIONAL_ROLE_ORDER_HASH,
        "keyword_role_order_hash": KEYWORD_ROLE_ORDER_HASH,
        "context_shape_hash": CONTEXT_SHAPE_HASH,
        "positional_source_hashes_in_contract_order": list(positional_hashes),
        "keyword_source_hashes_in_contract_order": list(keyword_hashes),
    }
    receipt = {
        "schema_version": CONTEXT_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "candidate_state": "REQUEST_LOCAL_SOURCE_CONTEXT_CREATED",
        "synthetic_only": True,
        "registered": False,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "prior_candidate_contract_hash": PRIOR_CANDIDATE_CONTRACT_HASH,
        "scope_evidence_hash": scope_candidate["evidence_hash"],
        "request_scope_id": evidence["request_scope_id"],
        "context_generation_id": evidence["context_generation_id"],
        "context_hash": _canonical_hash(context_binding),
        "positional_role_order_hash": POSITIONAL_ROLE_ORDER_HASH,
        "keyword_role_order_hash": KEYWORD_ROLE_ORDER_HASH,
        "context_shape_hash": CONTEXT_SHAPE_HASH,
        "positional_source_count": POSITIONAL_SOURCE_COUNT,
        "keyword_source_count": KEYWORD_SOURCE_COUNT,
        "positional_source_hashes_in_contract_order": list(positional_hashes),
        "keyword_source_hashes_in_contract_order": list(keyword_hashes),
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "consumed_at_creation": False,
        "source_documents_embedded": False,
        "facts": {
            "sources_snapshotted_as_json": True,
            "contract_order_preserved": True,
            "source_role_meaning_reverified": False,
            "single_resolution_enforced": True,
            "discard_after_resolution": True,
            "request_local_only": True,
            "clockless": True,
            "creation_receipt_exact_rebuild_verifier": True,
            "builder_only_context_construction": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(receipt, "receipt_hash")


def _build_context_receipt(
    scope_candidate: Mapping[str, Any],
    positional_sources: Sequence[Any],
    keyword_sources: Sequence[Any],
) -> dict[str, Any]:
    return _build_context_receipt_from_hashes(
        scope_candidate,
        [_canonical_hash(value) for value in positional_sources],
        [_canonical_hash(value) for value in keyword_sources],
    )


def verify_context_creation_receipt_v1(
    document: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    if not isinstance(document, Mapping) or not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return False
    positional_hashes = document.get(
        "positional_source_hashes_in_contract_order"
    )
    keyword_hashes = document.get("keyword_source_hashes_in_contract_order")
    if (
        not isinstance(positional_hashes, list)
        or not isinstance(keyword_hashes, list)
        or len(positional_hashes) != POSITIONAL_SOURCE_COUNT
        or len(keyword_hashes) != KEYWORD_SOURCE_COUNT
        or not all(_is_lower_hex_64(value) for value in positional_hashes)
        or not all(_is_lower_hex_64(value) for value in keyword_hashes)
    ):
        return False
    try:
        expected = _build_context_receipt_from_hashes(
            request_scope_evidence_candidate,
            positional_hashes,
            keyword_hashes,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected


def _build_consumption_receipt(
    creation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = {
        "schema_version": CONSUMPTION_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "consumption_state": "CONTEXT_RESOLVED_ONCE_AND_DISCARDED",
        "synthetic_only": True,
        "registered": False,
        "candidate_contract_hash": CANDIDATE_CONTRACT_HASH,
        "prior_candidate_contract_hash": PRIOR_CANDIDATE_CONTRACT_HASH,
        "creation_receipt_hash": creation_receipt["receipt_hash"],
        "scope_evidence_hash": creation_receipt["scope_evidence_hash"],
        "request_scope_id": creation_receipt["request_scope_id"],
        "context_generation_id": creation_receipt["context_generation_id"],
        "context_hash": creation_receipt["context_hash"],
        "resolution_count": 1,
        "maximum_resolution_count": MAXIMUM_RESOLUTION_COUNT,
        "source_documents_embedded": False,
        "discarded_after_resolution": True,
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(receipt, "consumption_receipt_hash")


def verify_context_consumption_receipt_v1(
    document: Any,
    creation_receipt: Any,
    request_scope_evidence_candidate: Any,
) -> bool:
    if not isinstance(document, Mapping) or not verify_context_creation_receipt_v1(
        creation_receipt,
        request_scope_evidence_candidate,
    ):
        return False
    try:
        expected = _build_consumption_receipt(creation_receipt)
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected


class RequestLocalSourceContextCandidateV1:
    """Private JSON snapshots that can be resolved exactly once."""

    __slots__ = (
        "_positional_sources",
        "_keyword_sources",
        "_creation_receipt",
        "_consumption_receipt",
        "_consumed",
    )

    def __init__(
        self,
        positional_sources: Sequence[Any],
        keyword_sources: Sequence[Any],
        creation_receipt: Mapping[str, Any],
        *,
        _construction_token: object | None = None,
    ) -> None:
        if _construction_token is not _CONSTRUCTION_TOKEN:
            raise TypeError("use build_request_local_source_context_candidate_v1")
        self._positional_sources = tuple(positional_sources)
        self._keyword_sources = tuple(keyword_sources)
        self._creation_receipt = dict(creation_receipt)
        self._consumption_receipt: dict[str, Any] | None = None
        self._consumed = False

    def __repr__(self) -> str:
        return (
            "<RequestLocalSourceContextCandidateV1 "
            f"consumed={self._consumed} source_documents=REDACTED>"
        )

    @property
    def consumed(self) -> bool:
        return self._consumed

    @property
    def receipt(self) -> dict[str, Any]:
        return deepcopy(self._creation_receipt)

    @property
    def consumption_receipt(self) -> dict[str, Any] | None:
        return deepcopy(self._consumption_receipt)

    def resolve_once(self) -> dict[str, Any] | None:
        if self._consumed:
            return None
        positional_sources = deepcopy(list(self._positional_sources))
        keyword_sources = deepcopy(list(self._keyword_sources))
        self._consumed = True
        self._positional_sources = ()
        self._keyword_sources = ()
        self._consumption_receipt = _build_consumption_receipt(
            self._creation_receipt
        )
        return {
            "positional_sources_in_contract_order": positional_sources,
            "keyword_sources_in_contract_order": keyword_sources,
            "consumption_receipt": deepcopy(self._consumption_receipt),
        }


def build_request_local_source_context_candidate_v1(
    *,
    request_scope_evidence_candidate: Any,
    positional_sources_in_contract_order: Any,
    keyword_sources_in_contract_order: Any,
) -> RequestLocalSourceContextCandidateV1 | None:
    """Snapshot a contract-ordered source context without registering it."""

    if not verify_request_scope_evidence_candidate_v1(
        request_scope_evidence_candidate
    ):
        return None
    evidence = request_scope_evidence_candidate["evidence"]
    if evidence["consumed"] is not False:
        return None
    if (
        not isinstance(positional_sources_in_contract_order, Sequence)
        or isinstance(positional_sources_in_contract_order, (str, bytes))
        or not isinstance(keyword_sources_in_contract_order, Sequence)
        or isinstance(keyword_sources_in_contract_order, (str, bytes))
    ):
        return None
    if (
        len(positional_sources_in_contract_order) != POSITIONAL_SOURCE_COUNT
        or len(keyword_sources_in_contract_order) != KEYWORD_SOURCE_COUNT
    ):
        return None
    try:
        positional_snapshot = _safe_json_snapshot(
            list(positional_sources_in_contract_order)
        )
        keyword_snapshot = _safe_json_snapshot(
            list(keyword_sources_in_contract_order)
        )
        receipt = _build_context_receipt(
            request_scope_evidence_candidate,
            positional_snapshot,
            keyword_snapshot,
        )
    except (TypeError, ValueError, OverflowError):
        return None
    return RequestLocalSourceContextCandidateV1(
        positional_snapshot,
        keyword_snapshot,
        receipt,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


__all__ = [
    "CANDIDATE_CONTRACT_HASH",
    "CONSUMPTION_RECEIPT_SCHEMA_VERSION",
    "CONTEXT_RECEIPT_SCHEMA_VERSION",
    "KEYWORD_ROLE_ORDER_HASH",
    "KEYWORD_SOURCE_COUNT",
    "POSITIONAL_ROLE_ORDER_HASH",
    "POSITIONAL_SOURCE_COUNT",
    "PRIOR_CANDIDATE_CONTRACT_HASH",
    "REQUEST_SCOPE_EVIDENCE_SCHEMA_VERSION",
    "RequestLocalSourceContextCandidateV1",
    "SCOPE_RESOLVER_PREREGISTRATION_HASH",
    "STATIC_FINGERPRINT",
    "build_request_local_source_context_candidate_v1",
    "build_request_scope_evidence_candidate_v1",
    "verify_context_creation_receipt_v1",
    "verify_context_consumption_receipt_v1",
    "verify_request_scope_evidence_candidate_v1",
]
