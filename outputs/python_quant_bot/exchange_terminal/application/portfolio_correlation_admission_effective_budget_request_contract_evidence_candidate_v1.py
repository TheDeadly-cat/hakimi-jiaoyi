"""Synthetic request-contract evidence derived from one JSON snapshot."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-contract-"
    "evidence-candidate-contract-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-request-contract-"
    "evidence-candidate-v1-synthetic-unregistered-lock-1"
)
REQUEST_CONTRACT_PAYLOAD_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-request-contract-payload-v1"
)
PROJECTION_REQUEST_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-readonly-http-"
    "projection-candidate-request-v1"
)
PROJECTION_ID = (
    "portfolio-correlation-admission-effective-budget-readonly-v1"
)
METHOD = "POST"
ROUTE = "/api/v1/research/portfolio-correlation/admission-effective-budget"
REQUEST_EVIDENCE_CONTRACT_HASH = (
    "cae0e79f6ad2ceec2444574858ab9d542ebb4912c1e7d463b8a426ba15dc165a"
)
KNOWN_REQUEST_PAYLOAD_HASH = (
    "03d52bc29aa187160a9a1ff0a67a5f58835a0b48d787da399dbe950f4bbe24f9"
)
KNOWN_REQUEST_CONTRACT_HASH = (
    "7423b83ea15bc410a10ec6964dc906c60368a2147a19e16ebeffdf6a8175b5b4"
)

_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_FIELDS = ("schema_version", "projection_id")
_BLOCKERS = (
    "UNREGISTERED_CANDIDATE",
    "SYNTHETIC_ONLY",
    "AUTHENTICATION_NOT_PERFORMED",
    "SECURITY_RECEIPT_SEMANTICS_UNVERIFIED",
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


def _safe_snapshot(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _seal(document: Mapping[str, Any], field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[field] = _canonical_hash(document)
    return sealed


def build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
    request_payload: Any,
) -> dict[str, Any] | None:
    """Derive the request contract from one exact synthetic request snapshot."""

    try:
        raw_snapshot = _safe_snapshot(request_payload)
    except (TypeError, ValueError, OverflowError):
        return None
    if (
        not isinstance(raw_snapshot, Mapping)
        or set(raw_snapshot) != set(_REQUEST_FIELDS)
        or raw_snapshot.get("schema_version") != PROJECTION_REQUEST_SCHEMA_VERSION
        or raw_snapshot.get("projection_id") != PROJECTION_ID
    ):
        return None
    request_snapshot = {
        "schema_version": PROJECTION_REQUEST_SCHEMA_VERSION,
        "projection_id": PROJECTION_ID,
    }
    request_payload_hash = _canonical_hash(request_snapshot)
    request_contract_payload = {
        "schema_version": REQUEST_CONTRACT_PAYLOAD_SCHEMA_VERSION,
        "method": METHOD,
        "route": ROUTE,
        "request_schema_version": PROJECTION_REQUEST_SCHEMA_VERSION,
        "request_payload_hash": request_payload_hash,
    }
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": "UNREGISTERED_CANDIDATE",
        "status": "BLOCKED",
        "candidate_state": "REQUEST_CONTRACT_DERIVED_FROM_EXACT_SNAPSHOT",
        "synthetic_only": True,
        "registered": False,
        "request_evidence_contract_hash": REQUEST_EVIDENCE_CONTRACT_HASH,
        "method": METHOD,
        "route": ROUTE,
        "request_snapshot": request_snapshot,
        "request_payload_hash": request_payload_hash,
        "request_contract_payload": request_contract_payload,
        "request_contract_hash": _canonical_hash(request_contract_payload),
        "facts": {
            "request_snapshotted_once": True,
            "request_fields_exact": tuple(request_snapshot) == _REQUEST_FIELDS,
            "request_contract_hash_derived_not_supplied": True,
            "request_contains_source_documents": False,
            "authentication_performed": False,
            "clockless": True,
        },
        "blockers": list(_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(candidate, "candidate_hash")


def verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
    document: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    rebuilt = build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1(
        document.get("request_snapshot")
    )
    return rebuilt is not None and document == rebuilt


__all__ = [
    "KNOWN_REQUEST_CONTRACT_HASH",
    "KNOWN_REQUEST_PAYLOAD_HASH",
    "METHOD",
    "PROJECTION_ID",
    "PROJECTION_REQUEST_SCHEMA_VERSION",
    "REQUEST_EVIDENCE_CONTRACT_HASH",
    "ROUTE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1",
    "verify_portfolio_correlation_admission_effective_budget_request_contract_evidence_candidate_v1",
]
