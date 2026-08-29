"""Unregistered read-only HTTP projection candidate for correlation evidence.

The external request shell carries no source data.  A trusted caller must supply
the exact ADR0316 binding and internal provider call context separately.  This
module has no route, server import, runtime read, cache, browser, or writer API.
"""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_python_provider_binding_v1 as provider_binding,
)
from exchange_terminal.services.portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 import (
    SCHEMA_VERSION as PROVIDER_RESULT_SCHEMA_VERSION,
    STATIC_FINGERPRINT as PROVIDER_RESULT_STATIC_FINGERPRINT,
    verify_portfolio_correlation_admission_effective_budget_hash_envelope_source_consumer_v1 as _verify_provider_result,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-readonly-http-projection-"
    "candidate-request-v1"
)
RESPONSE_SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-readonly-http-projection-"
    "candidate-response-v1"
)
STATIC_FINGERPRINT = (
    "20260824-portfolio-correlation-admission-effective-budget-readonly-http-"
    "projection-candidate-v1-unregistered-lock-1"
)
PROJECTION_ID = "portfolio-correlation-admission-effective-budget-readonly-v1"
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"

KNOWN_STATE = "KNOWN"
UNKNOWN_STATE = "UNKNOWN"
BLOCKED_STATE = "BLOCKED"

_REQUEST_FIELDS = frozenset({"schema_version", "projection_id"})
_PROVIDER_KWARG_FIELDS = frozenset(
    {
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
    }
)
_PROVIDER_POSITIONAL_COUNT = 13


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


def _transport() -> dict[str, Any]:
    return {
        "registered": False,
        "externally_callable": False,
        "method": None,
        "route": None,
        "endpoint": None,
        "input_source": "INTERNAL_PROVIDER_RESULT_ONLY",
        "runtime_reads": False,
        "runtime_mutations": False,
        "database_reads": False,
        "database_writes": False,
        "cache_reads": False,
        "cache_writes": False,
        "network_used": False,
        "request_body_logging_allowed": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "external_request_invocation_allowed": False,
        "http_projection_binding_allowed": False,
        "route_registration_allowed": False,
        "endpoint_registration_allowed": False,
        "application_import_allowed": False,
        "runtime_asset_loading_allowed": False,
        "browser_execution_allowed": False,
        "dom_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "request_contract_valid": False,
        "internal_provider_context_valid": False,
        "provider_binding_verified": False,
        "provider_resolved": False,
        "provider_invocation_attempted": False,
        "provider_result_verified": False,
        "source_known": False,
        "source_unknown": False,
        "source_blocked": False,
        "result_available": False,
        "request_document_embedded": False,
        "internal_provider_context_embedded": False,
        "source_documents_embedded": False,
        "transport_registered": False,
        "runtime_mutations_performed": False,
        "profitability_proven": False,
    }


def _lineage(
    *,
    provider_bound: bool,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "provider_binding_schema_version": (
            provider_binding.SCHEMA_VERSION if provider_bound else None
        ),
        "provider_binding_hash": (
            provider_binding.EXPECTED_PROVIDER_BINDING_HASH
            if provider_bound
            else None
        ),
        "provider_result_schema_version": (
            PROVIDER_RESULT_SCHEMA_VERSION if result is not None else None
        ),
        "provider_result_static_fingerprint": (
            PROVIDER_RESULT_STATIC_FINGERPRINT if result is not None else None
        ),
        "provider_result_hash": (
            result.get("consumer_result_hash") if result is not None else None
        ),
        "provider_envelope_hash": (
            result.get("envelope_hash") if result is not None else None
        ),
        "request_document_embedded": False,
        "internal_provider_context_embedded": False,
        "source_documents_embedded": False,
    }


def _sealed(
    *,
    state: str,
    reason_code: str,
    payload: dict[str, Any] | None,
    facts: dict[str, bool],
    lineage: dict[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "projection_id": PROJECTION_ID,
            "interface_status": INTERFACE_STATUS,
            "state": state,
            "reason_code": reason_code,
            "payload": payload,
            "facts": facts,
            "lineage": lineage,
            "transport": _transport(),
            "authority": _authority(),
            "blockers": blockers,
        },
        "response_hash",
    )


def _unknown(
    reason_code: str,
    *,
    facts: dict[str, bool] | None = None,
    provider_bound: bool = False,
) -> dict[str, Any]:
    return _sealed(
        state=UNKNOWN_STATE,
        reason_code=reason_code,
        payload=None,
        facts=facts if facts is not None else _facts(),
        lineage=_lineage(provider_bound=provider_bound, result=None),
        blockers=[reason_code, "HTTP_TRANSPORT_UNREGISTERED"],
    )


def _request_valid(request_payload: Any) -> bool:
    return (
        type(request_payload) is dict
        and frozenset(request_payload) == _REQUEST_FIELDS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and request_payload.get("projection_id") == PROJECTION_ID
    )


def _provider_context(
    positional: Any,
    keyword: Any,
) -> tuple[list[Any], dict[str, Any]] | None:
    if type(positional) is not list or len(positional) != _PROVIDER_POSITIONAL_COUNT:
        return None
    if type(keyword) is not dict or frozenset(keyword) != _PROVIDER_KWARG_FIELDS:
        return None
    try:
        positional_snapshot = _snapshot_json_value(positional, set())
        keyword_snapshot = _snapshot_json_value(keyword, set())
    except Exception:
        return None
    if type(positional_snapshot) is not list or type(keyword_snapshot) is not dict:
        return None
    return positional_snapshot, keyword_snapshot


def _provider_result_presentable(result: Any) -> bool:
    if type(result) is not dict:
        return False
    if (
        result.get("schema_version") != PROVIDER_RESULT_SCHEMA_VERSION
        or result.get("static_fingerprint") != PROVIDER_RESULT_STATIC_FINGERPRINT
        or result.get("status") not in {KNOWN_STATE, UNKNOWN_STATE, BLOCKED_STATE}
    ):
        return False
    authority = result.get("authority")
    facts = result.get("facts")
    transport = result.get("transport")
    if not all(type(value) is dict for value in (authority, facts, transport)):
        return False
    if any(authority.values()):
        return False
    if (
        facts.get("input_documents_embedded") is not False
        or facts.get("browser_executed") is not False
        or facts.get("dom_mounted") is not False
        or facts.get("runtime_mutations_performed") is not False
        or facts.get("profitability_proven") is not False
        or transport.get("storage_used") is not False
        or transport.get("network_used") is not False
        or transport.get("route") is not None
        or transport.get("endpoint") is not None
    ):
        return False

    status = result["status"]
    envelope = result.get("envelope")
    if status == BLOCKED_STATE:
        return envelope is None and result.get("envelope_hash") is None
    if type(envelope) is not dict:
        return False
    payload = envelope.get("presentation_payload")
    if status == UNKNOWN_STATE:
        return payload is None
    if type(payload) is not dict:
        return False
    payload_facts = payload.get("facts")
    permissions = payload.get("permissions")
    return bool(
        type(payload_facts) is dict
        and type(permissions) is dict
        and payload.get("status") == KNOWN_STATE
        and payload_facts.get("hash_only_projection") is True
        and payload_facts.get("positions_embedded") is False
        and payload_facts.get("raw_symbol_lists_embedded") is False
        and payload_facts.get("source_documents_embedded") is False
        and payload_facts.get("profitability_proven") is False
        and not any(permissions.values())
    )


def _known_payload(
    result: dict[str, Any],
) -> dict[str, Any]:
    presentation = result["envelope"]["presentation_payload"]
    return {
        "schema_version": presentation["schema_version"],
        "source_status": KNOWN_STATE,
        "provider_binding_hash": provider_binding.EXPECTED_PROVIDER_BINDING_HASH,
        "provider_result_hash": result["consumer_result_hash"],
        "provider_envelope_hash": result["envelope_hash"],
        "presentation_payload_hash": presentation["presentation_payload_hash"],
        "presentation": presentation,
    }


def build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
    request_payload: Any,
    *,
    provider_binding_document: Any,
    internal_provider_positional: Any,
    internal_provider_keyword: Any,
) -> dict[str, Any]:
    """Build an unregistered response from an explicit trusted provider context."""

    request_snapshot = _snapshot_json_mapping(request_payload)
    if request_snapshot is None or not _request_valid(request_snapshot):
        return _unknown("REQUEST_CONTRACT_INVALID")
    facts = _facts()
    facts["request_contract_valid"] = True

    binding_snapshot = _snapshot_json_mapping(provider_binding_document)
    if binding_snapshot is None:
        return _unknown("PROVIDER_BINDING_SNAPSHOT_FAILED", facts=facts)
    provider = provider_binding.resolve_portfolio_correlation_admission_effective_budget_python_provider_v1(
        binding_snapshot
    )
    if provider is None:
        return _unknown("PROVIDER_BINDING_UNVERIFIED", facts=facts)
    facts["provider_binding_verified"] = True
    facts["provider_resolved"] = True

    context = _provider_context(
        internal_provider_positional,
        internal_provider_keyword,
    )
    if context is None:
        return _unknown(
            "INTERNAL_PROVIDER_CONTEXT_INVALID",
            facts=facts,
            provider_bound=True,
        )
    positional, keyword = context
    facts["internal_provider_context_valid"] = True
    facts["provider_invocation_attempted"] = True
    try:
        result = provider(*positional, **keyword)
    except Exception:
        return _unknown(
            "PROVIDER_INVOCATION_ERROR",
            facts=facts,
            provider_bound=True,
        )
    try:
        verified = _verify_provider_result(result, *positional, **keyword)
    except Exception:
        verified = False
    if verified is not True or not _provider_result_presentable(result):
        return _unknown(
            "PROVIDER_RESULT_UNVERIFIED",
            facts=facts,
            provider_bound=True,
        )

    result_snapshot = _snapshot_json_mapping(result)
    if result_snapshot is None:
        return _unknown(
            "PROVIDER_RESULT_SNAPSHOT_FAILED",
            facts=facts,
            provider_bound=True,
        )
    facts["provider_result_verified"] = True
    state = result_snapshot["status"]
    facts["source_known"] = state == KNOWN_STATE
    facts["source_unknown"] = state == UNKNOWN_STATE
    facts["source_blocked"] = state == BLOCKED_STATE
    facts["result_available"] = state == KNOWN_STATE

    reason_codes = {
        KNOWN_STATE: "SOURCE_PROVIDER_KNOWN_PROJECTED",
        UNKNOWN_STATE: "SOURCE_PROVIDER_UNKNOWN",
        BLOCKED_STATE: "SOURCE_PROVIDER_BLOCKED",
    }
    blockers = ["HTTP_TRANSPORT_UNREGISTERED"]
    if state != KNOWN_STATE:
        blockers.insert(0, reason_codes[state])
    return _sealed(
        state=state,
        reason_code=reason_codes[state],
        payload=_known_payload(result_snapshot) if state == KNOWN_STATE else None,
        facts=facts,
        lineage=_lineage(provider_bound=True, result=result_snapshot),
        blockers=blockers,
    )


def verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
    document: Any,
    request_payload: Any,
    *,
    provider_binding_document: Any,
    internal_provider_positional: Any,
    internal_provider_keyword: Any,
) -> bool:
    """Verify an exact candidate response against the same trusted context."""

    snapshot = _snapshot_json_mapping(document)
    if snapshot is None:
        return False
    try:
        expected = build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1(
            request_payload,
            provider_binding_document=provider_binding_document,
            internal_provider_positional=internal_provider_positional,
            internal_provider_keyword=internal_provider_keyword,
        )
    except Exception:
        return False
    return strict_json_contract_equal(snapshot, expected)


__all__ = [
    "BLOCKED_STATE",
    "INTERFACE_STATUS",
    "KNOWN_STATE",
    "PROJECTION_ID",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    "build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1",
    "verify_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1",
]
