"""Unmounted presentation candidate binding v4 projection to adapter-v5 evidence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v4 import (
    build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4 as _BUILD_V4,
)
from exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v4 import (
    verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v4 as _VERIFY_V4,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_adapter_v5 import (
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v5 as _VERIFY_ADAPTER_V5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-request-v5"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v5"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v5"
)
STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-presentation-http-adapter-v5-unregistered-candidate-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"

V4_IMPLEMENTATION_SHA256 = (
    "5e043ff6d7cb4d78a7161449a27e627ad075cdd72bcc4fd2e1b059e51b2be40b"
)
ADAPTER_V5_IMPLEMENTATION_SHA256 = (
    "d44d5a1ca180d6b7b432266be6f4ca00cc639ef949a4bc56226ad77d2bccd509"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_V4_RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v4"
)
_V4_PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v4"
)
_V4_STATIC_FINGERPRINT = "20260823-portfolio-risk-presentation-http-unregistered-candidate-4"
_ADAPTER_V5_SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v5"
_ADAPTER_V5_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-adapter-v5-verification-v1"
)
_ADAPTER_V5_STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-adapter-v5-multi-window-joint-lock-1"
)
_ADAPTER_V5_PASS_DECISION = "PASS_WEIGHTED_AND_MULTI_WINDOW_STABLE_RESEARCH_GATE"
_AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "presentation_candidate_v4_request",
        "portfolio_risk_adapter_v5_document",
    }
)
_ADAPTER_CONTEXT_KEYS = frozenset(
    {
        "adapter_v4_document",
        "stability_gate_document",
        "adapter_v4_verification_context",
        "stability_gate_verification_context",
    }
)
_V4_RESPONSE_KEYS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "interface_status",
        "state",
        "payload",
        "facts",
        "lineage",
        "transport",
        "authority",
        "blockers",
        "response_hash",
    }
)
_ADAPTER_DOCUMENT_KEYS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "status",
        "decision",
        "source",
        "component_states",
        "checks",
        "facts",
        "blockers",
        "authority",
        "adapter_v5_hash",
    }
)
_ADAPTER_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "adapter_v5_exactly_verified",
        "adapter_v5_status",
        "adapter_v5_hash",
        "blockers",
        "writer_allowed",
        "risk_service_invocation_allowed",
        "runtime_gate_activation_allowed",
        "current_admission_allowed",
        "paper_authorized",
        "live_order_allowed",
    }
)


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed_hash_exact(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    unsigned = deepcopy(document)
    claimed = unsigned.pop(hash_field, None)
    return claimed == strict_canonical_hash(unsigned)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "route_registration_allowed": False,
        "consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _adapter_authority() -> dict[str, bool]:
    return {
        "local_decision_only": True,
        "research_only": True,
        "writer_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _transport() -> dict[str, Any]:
    return {
        "registered": False,
        "externally_callable": False,
        "method": None,
        "route": None,
        "runtime_reads": False,
        "runtime_mutations": False,
        "cache_reads": False,
        "cache_writes": False,
    }


def _request_valid(request_payload: Any) -> bool:
    return (
        isinstance(request_payload, dict)
        and set(request_payload) == _REQUEST_KEYS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and isinstance(request_payload.get("presentation_candidate_v4_request"), dict)
        and isinstance(request_payload.get("portfolio_risk_adapter_v5_document"), dict)
    )


def _adapter_context_valid(context: Any) -> bool:
    return (
        isinstance(context, dict)
        and set(context) == _ADAPTER_CONTEXT_KEYS
        and all(isinstance(context.get(key), dict) for key in _ADAPTER_CONTEXT_KEYS)
    )


def _v4_presentable(document: Any) -> bool:
    if not isinstance(document, dict) or set(document) != _V4_RESPONSE_KEYS:
        return False
    payload = document.get("payload")
    facts = document.get("facts")
    lineage = document.get("lineage")
    if not all(isinstance(value, dict) for value in (payload, facts, lineage)):
        return False
    return (
        document.get("schema_version") == _V4_RESPONSE_SCHEMA_VERSION
        and document.get("static_fingerprint") == _V4_STATIC_FINGERPRINT
        and document.get("interface_status") == INTERFACE_STATUS
        and document.get("state") == KNOWN_BLOCKED_STATE
        and _sealed_hash_exact(document, "response_hash")
        and payload.get("schema_version") == _V4_PAYLOAD_SCHEMA_VERSION
        and payload.get("presentation_status") == "UNMOUNTED_HTTP_CANDIDATE"
        and payload.get("axis_order") == list(_AXIS_ORDER)
        and payload.get("authority") == _authority()
        and facts.get("request_contract_valid") is True
        and facts.get("source_preregistration_verified") is True
        and facts.get("result_available") is True
        and facts.get("transport_registered") is False
        and facts.get("route_registered") is False
        and facts.get("ui_mounted") is False
        and facts.get("runtime_mutations_performed") is False
        and facts.get("profitability_proven") is False
        and lineage.get("request_documents_embedded") is False
        and lineage.get("verification_context_embedded") is False
        and document.get("transport") == _transport()
        and document.get("authority") == _authority()
        and isinstance(document.get("blockers"), list)
    )


def _adapter_presentable(document: Any) -> bool:
    if not isinstance(document, dict) or set(document) != _ADAPTER_DOCUMENT_KEYS:
        return False
    source = document.get("source")
    checks = document.get("checks")
    facts = document.get("facts")
    blockers = document.get("blockers")
    if not all(isinstance(value, dict) for value in (source, checks, facts)):
        return False
    status = document.get("status")
    decision = document.get("decision")
    status_consistent = (
        status == "PASS" and decision == _ADAPTER_V5_PASS_DECISION and blockers == []
    ) or (
        status in {"BLOCK", "UNKNOWN"}
        and isinstance(decision, str)
        and decision.startswith("BLOCK_")
        and isinstance(blockers, list)
        and len(blockers) > 0
    )
    return (
        document.get("schema_version") == _ADAPTER_V5_SCHEMA_VERSION
        and document.get("static_fingerprint") == _ADAPTER_V5_STATIC_FINGERPRINT
        and status_consistent
        and _sealed_hash_exact(document, "adapter_v5_hash")
        and source.get("source_documents_embedded") is False
        and source.get("verification_contexts_embedded") is False
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and facts.get("correlation_matrices_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("risk_service_invoked") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("profitability_proven") is False
        and document.get("authority") == _adapter_authority()
        and all(isinstance(value, bool) for value in checks.values())
    )


def _adapter_receipt_passed(receipt: Any, document: dict[str, Any]) -> bool:
    if not isinstance(receipt, dict) or set(receipt) != _ADAPTER_RECEIPT_KEYS:
        return False
    return (
        receipt.get("schema_version") == _ADAPTER_V5_VERIFICATION_SCHEMA_VERSION
        and receipt.get("status") == "PASS"
        and receipt.get("adapter_v5_exactly_verified") is True
        and receipt.get("adapter_v5_status") == document.get("status")
        and receipt.get("adapter_v5_hash") == document.get("adapter_v5_hash")
        and isinstance(receipt.get("blockers"), list)
        and receipt.get("writer_allowed") is False
        and receipt.get("risk_service_invocation_allowed") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _call_v4(request_payload: dict[str, Any], context: dict[str, Any]) -> tuple[Any, bool]:
    try:
        response = _BUILD_V4(request_payload, v10_verification_context=context)
        verified = _VERIFY_V4(
            response,
            request_payload,
            v10_verification_context=context,
        )
    except Exception:
        return None, False
    return response, verified is True


def _call_adapter_verifier(document: dict[str, Any], context: dict[str, Any]) -> Any:
    try:
        return _VERIFY_ADAPTER_V5(
            document,
            context["adapter_v4_document"],
            context["stability_gate_document"],
            adapter_v4_verification_context=context["adapter_v4_verification_context"],
            stability_gate_verification_context=context[
                "stability_gate_verification_context"
            ],
        )
    except Exception:
        return None


def _payload(
    v4_response: dict[str, Any], adapter_document: dict[str, Any]
) -> dict[str, Any]:
    v4_payload = v4_response["payload"]
    adapter_passed = adapter_document["status"] == "PASS"
    summary = deepcopy(v4_payload["summary"])
    summary.update(
        {
            "portfolio_risk_adapter_v5_status": adapter_document["status"],
            "portfolio_risk_adapter_v5_decision": adapter_document["decision"],
            "multi_window_stability_gate_verified": adapter_document["facts"][
                "multi_window_stability_gate_exactly_verified"
            ],
            "anchor_window_budget_and_context_bound": adapter_document["facts"][
                "anchor_window_budget_and_context_bound"
            ],
            "trade_identity_cross_bound": adapter_document["facts"][
                "trade_identity_cross_bound"
            ],
            "joint_local_research_decision_made": adapter_document["facts"][
                "joint_local_research_decision_made"
            ],
            "joint_risk_gate_passed": adapter_passed,
        }
    )
    facts = deepcopy(v4_payload["facts"])
    facts.update(
        {
            "portfolio_risk_adapter_v5_bound": True,
            "portfolio_risk_adapter_v5_document_embedded": False,
            "portfolio_risk_adapter_v5_verification_context_embedded": False,
            "multi_window_stability_gate_bound": adapter_document["facts"][
                "multi_window_stability_gate_exactly_verified"
            ],
            "anchor_window_budget_and_context_bound": adapter_document["facts"][
                "anchor_window_budget_and_context_bound"
            ],
            "trade_identity_cross_bound": adapter_document["facts"][
                "trade_identity_cross_bound"
            ],
            "joint_risk_gate_passed": adapter_passed,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        }
    )
    gap_detail = (
        "EXTERNAL_TRUST_REVIEW_EXECUTION_TRANSPORT_AND_MOUNT_GAPS"
        if adapter_passed
        else "MULTI_WINDOW_JOINT_RISK_GATE_NOT_PASSED_AND_EXTERNAL_GAPS"
    )
    return {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "presentation_status": "UNMOUNTED_HTTP_CANDIDATE",
        "axis_order": list(_AXIS_ORDER),
        "source": {
            "preregistration": deepcopy(v4_payload["source"]),
            "joint_portfolio_risk": {
                "schema_version": adapter_document["schema_version"],
                "static_fingerprint": adapter_document["static_fingerprint"],
                "implementation_sha256": ADAPTER_V5_IMPLEMENTATION_SHA256,
                "adapter_v5_hash": adapter_document["adapter_v5_hash"],
                "status": adapter_document["status"],
                "decision": adapter_document["decision"],
                "anchor_window_id": adapter_document["source"]["anchor_window_id"],
                "trade_identity_hash": adapter_document["source"]["trade_identity_hash"],
            },
        },
        "stages": [
            {
                "axis": "SOURCE",
                "state": "VERIFIED",
                "detail": "V10_AND_ADAPTER_V5_EXACT_REBUILD",
            },
            {"axis": "GAP", "state": "PRESENT", "detail": gap_detail},
            {
                "axis": "MATURITY",
                "state": "LOCAL_EVIDENCE_BOUND",
                "detail": "SIGNED_REVIEW_EXECUTION_AND_MULTI_WINDOW_JOINT_RISK_BOUND_ONLY",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
            },
        ],
        "summary": summary,
        "facts": facts,
        "authority": _authority(),
    }


def _unknown(reason: str, *, request_valid: bool = False) -> dict[str, Any]:
    document = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": INTERFACE_STATUS,
        "state": UNKNOWN_STATE,
        "payload": None,
        "facts": {
            "request_contract_valid": request_valid,
            "source_presentation_v4_exactly_verified": False,
            "portfolio_risk_adapter_v5_exactly_verified": False,
            "result_available": False,
            "presentation_http_contract_candidate_v5_versioned": True,
            "transport_registered": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "lineage": {
            "source_presentation_v4_implementation_sha256": V4_IMPLEMENTATION_SHA256,
            "portfolio_risk_adapter_v5_implementation_sha256": (
                ADAPTER_V5_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "source_bound": False,
            "request_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "transport": _transport(),
        "authority": _authority(),
        "blockers": [reason],
    }
    return seal_strict_canonical_document(document, "response_hash")


def _known_blocked(
    v4_response: dict[str, Any], adapter_document: dict[str, Any]
) -> dict[str, Any]:
    adapter_passed = adapter_document["status"] == "PASS"
    blockers = list(v4_response["blockers"])
    if not adapter_passed:
        blockers.append("PORTFOLIO_RISK_ADAPTER_V5_NOT_PASS")
    blockers.append("PRESENTATION_HTTP_CANDIDATE_V5_UNREGISTERED")
    blockers = list(dict.fromkeys(blockers))

    facts = deepcopy(v4_response["facts"])
    facts.update(
        {
            "request_contract_valid": True,
            "source_presentation_v4_exactly_verified": True,
            "portfolio_risk_adapter_v5_exactly_verified": True,
            "multi_window_joint_risk_evidence_bound": True,
            "joint_risk_gate_passed": adapter_passed,
            "presentation_http_contract_candidate_v5_versioned": True,
            "transport_registered": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        }
    )
    document = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": INTERFACE_STATUS,
        "state": KNOWN_BLOCKED_STATE,
        "payload": _payload(v4_response, adapter_document),
        "facts": facts,
        "lineage": {
            "source_presentation_v4_schema_version": v4_response["schema_version"],
            "source_presentation_v4_static_fingerprint": v4_response[
                "static_fingerprint"
            ],
            "source_presentation_v4_implementation_sha256": V4_IMPLEMENTATION_SHA256,
            "source_presentation_v4_response_hash": v4_response["response_hash"],
            "source_preregistration_hash": v4_response["lineage"][
                "source_preregistration_hash"
            ],
            "portfolio_risk_adapter_v5_schema_version": adapter_document[
                "schema_version"
            ],
            "portfolio_risk_adapter_v5_static_fingerprint": adapter_document[
                "static_fingerprint"
            ],
            "portfolio_risk_adapter_v5_implementation_sha256": (
                ADAPTER_V5_IMPLEMENTATION_SHA256
            ),
            "portfolio_risk_adapter_v5_hash": adapter_document["adapter_v5_hash"],
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "request_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "transport": _transport(),
        "authority": _authority(),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(document, "response_hash")


def build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5(
    request_payload: Any,
    *,
    v4_verification_context: Any,
    adapter_v5_verification_context: Any,
) -> dict[str, Any]:
    """Build a summary-only, unregistered candidate response."""

    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")
    if not isinstance(v4_verification_context, dict) or not _adapter_context_valid(
        adapter_v5_verification_context
    ):
        return _unknown("VERIFICATION_CONTEXT_INVALID", request_valid=True)

    v4_request = request_payload["presentation_candidate_v4_request"]
    adapter_document = request_payload["portfolio_risk_adapter_v5_document"]
    v4_response, v4_verified = _call_v4(v4_request, v4_verification_context)
    if not v4_verified or not _v4_presentable(v4_response):
        return _unknown("SOURCE_PRESENTATION_V4_UNVERIFIED", request_valid=True)

    if not _adapter_presentable(adapter_document):
        return _unknown("PORTFOLIO_RISK_ADAPTER_V5_UNPRESENTABLE", request_valid=True)
    adapter_receipt = _call_adapter_verifier(
        adapter_document, adapter_v5_verification_context
    )
    if not _adapter_receipt_passed(adapter_receipt, adapter_document):
        return _unknown("PORTFOLIO_RISK_ADAPTER_V5_UNVERIFIED", request_valid=True)

    return _known_blocked(v4_response, adapter_document)


def verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5(
    document: Any,
    request_payload: Any,
    *,
    v4_verification_context: Any,
    adapter_v5_verification_context: Any,
) -> bool:
    """Verify an exact deterministic rebuild; never grant transport or authority."""

    if not isinstance(document, dict) or not _sealed_hash_exact(document, "response_hash"):
        return False
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5(
        request_payload,
        v4_verification_context=v4_verification_context,
        adapter_v5_verification_context=adapter_v5_verification_context,
    )
    return strict_json_contract_equal(document, expected)
