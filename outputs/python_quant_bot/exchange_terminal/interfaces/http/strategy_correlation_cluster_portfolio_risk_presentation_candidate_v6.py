"""Unmounted HTTP candidate consuming an exact adapter-v6 presentation envelope."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1 as envelope_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REQUEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-"
    "candidate-request-v6"
)
RESPONSE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-"
    "candidate-response-v6"
)
PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v6"
)
STATIC_FINGERPRINT = (
    "20260823-adapter-v6-envelope-first-http-unregistered-candidate-1"
)
INTERFACE_STATUS = "UNREGISTERED_CANDIDATE"
KNOWN_BLOCKED_STATE = "KNOWN_BLOCKED"
UNKNOWN_STATE = "UNKNOWN"
ENVELOPE_V1_IMPLEMENTATION_SHA256 = (
    "ec8977a0b3750b17a5ac35c20c6fe1791573a0529e0d8e61a81a07010ebf02dd"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
HTTP_CANDIDATE_BLOCKERS = (
    "HTTP_CANDIDATE_V6_UNREGISTERED",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
)

_VERIFY_ENVELOPE = (
    envelope_v1.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1
)
_REQUEST_KEYS = {
    "schema_version",
    "adapter_v6_presentation_envelope_v1_document",
    "expected_presentation_envelope_hash",
}
_CONTEXT_KEYS = {
    "adapter_v6_document",
    "adapter_v5_document",
    "downside_tail_registration",
    "downside_tail_evaluation",
    "expected_adapter_v6_hash",
    "adapter_v5_verification_context",
    "downside_tail_verification_context",
}
_ENVELOPE_KEYS = {
    "schema_version",
    "static_fingerprint",
    "status",
    "decision",
    "axis_order",
    "source",
    "local_decision",
    "policy",
    "gaps",
    "stages",
    "facts",
    "authority",
    "envelope_hash",
}
_ENVELOPE_RECEIPT_KEYS = {
    "schema_version",
    "status",
    "envelope_exactly_verified",
    "envelope_status",
    "envelope_hash",
    "blockers",
    "presentation_consumer_activation_allowed",
    "formal_registry_activation_allowed",
    "current_admission_allowed",
    "runtime_gate_activation_allowed",
    "writer_allowed",
    "paper_authorized",
    "live_order_allowed",
    "verification_hash",
}
_ENVELOPE_AUTHORITY = {
    "research_only": True,
    "presentation_only": True,
    "descriptive_only": True,
    "http_candidate_creation_allowed": False,
    "presentation_consumer_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "migration_allowed": False,
    "runtime_gate_activation_allowed": False,
    "shadow_consumer_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_AUTHORITY = {
    "descriptive_only": True,
    "route_registration_allowed": False,
    "consumer_activation_allowed": False,
    "presentation_mount_allowed": False,
    "formal_registry_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "runtime_gate_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _is_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed_hash_exact(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(hash_field)):
        return False
    unsigned = deepcopy(document)
    claimed = unsigned.pop(hash_field, None)
    return claimed == strict_canonical_hash(unsigned)


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
    return bool(
        type(request_payload) is dict
        and set(request_payload) == _REQUEST_KEYS
        and request_payload.get("schema_version") == REQUEST_SCHEMA_VERSION
        and type(
            request_payload.get(
                "adapter_v6_presentation_envelope_v1_document"
            )
        )
        is dict
        and _is_hash(
            request_payload.get("expected_presentation_envelope_hash")
        )
    )


def _context_valid(context: Any) -> bool:
    if type(context) is not dict or set(context) != _CONTEXT_KEYS:
        return False
    document_keys = {
        "adapter_v6_document",
        "adapter_v5_document",
        "downside_tail_registration",
        "downside_tail_evaluation",
        "adapter_v5_verification_context",
        "downside_tail_verification_context",
    }
    return bool(
        all(type(context.get(key)) is dict for key in document_keys)
        and _is_hash(context.get("expected_adapter_v6_hash"))
    )


def _envelope_presentable(document: Any, expected_hash: Any) -> bool:
    if (
        type(document) is not dict
        or set(document) != _ENVELOPE_KEYS
        or not _is_hash(expected_hash)
        or document.get("envelope_hash") != expected_hash
    ):
        return False
    source = document.get("source")
    local_decision = document.get("local_decision")
    policy = document.get("policy")
    gaps = document.get("gaps")
    stages = document.get("stages")
    facts = document.get("facts")
    if not all(
        type(value) is dict
        for value in (source, local_decision, policy, gaps, facts)
    ) or type(stages) is not list:
        return False
    return bool(
        document.get("schema_version") == envelope_v1.SCHEMA_VERSION
        and document.get("static_fingerprint")
        == envelope_v1.STATIC_FINGERPRINT
        and document.get("status") == "BLOCK"
        and document.get("axis_order") == list(AXIS_ORDER)
        and _sealed_hash_exact(document, "envelope_hash")
        and len(stages) == len(AXIS_ORDER)
        and all(
            type(stage) is dict
            and set(stage) == {"axis", "state", "detail"}
            and stage.get("axis") == axis
            and type(stage.get("state")) is str
            and type(stage.get("detail")) is str
            for stage, axis in zip(stages, AXIS_ORDER)
        )
        and stages[2].get("state") == "CANDIDATE_ONLY"
        and stages[3].get("state") == "UNAUTHORIZED"
        and policy.get("tail_block_overrides_linear_multi_window_clear")
        is True
        and policy.get("risk_reduction_joint_exemption_implemented") is False
        and facts.get("risk_reduction_joint_exemption_implemented") is False
        and facts.get("projection_only") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and facts.get("aligned_observations_embedded") is False
        and facts.get("pair_results_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("ui_mounted") is False
        and facts.get("profitability_proven") is False
        and strict_json_contract_equal(
            document.get("authority"), _ENVELOPE_AUTHORITY
        )
    )


def _call_envelope_verifier(
    document: dict[str, Any],
    context: dict[str, Any],
) -> Any:
    try:
        return _VERIFY_ENVELOPE(
            document,
            context["adapter_v6_document"],
            context["adapter_v5_document"],
            context["downside_tail_registration"],
            context["downside_tail_evaluation"],
            expected_adapter_v6_hash=context["expected_adapter_v6_hash"],
            adapter_v5_verification_context=context[
                "adapter_v5_verification_context"
            ],
            downside_tail_verification_context=context[
                "downside_tail_verification_context"
            ],
        )
    except Exception:
        return None


def _envelope_receipt_passed(
    receipt: Any,
    document: dict[str, Any],
) -> bool:
    return bool(
        type(receipt) is dict
        and set(receipt) == _ENVELOPE_RECEIPT_KEYS
        and _sealed_hash_exact(receipt, "verification_hash")
        and receipt.get("schema_version")
        == envelope_v1.VERIFICATION_SCHEMA_VERSION
        and receipt.get("status") == "PASS"
        and receipt.get("envelope_exactly_verified") is True
        and receipt.get("envelope_status") == document.get("status")
        and receipt.get("envelope_hash") == document.get("envelope_hash")
        and receipt.get("blockers") == []
        and receipt.get("presentation_consumer_activation_allowed") is False
        and receipt.get("formal_registry_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("writer_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _unknown(reason: str, *, request_valid: bool = False) -> dict[str, Any]:
    document = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": INTERFACE_STATUS,
        "state": UNKNOWN_STATE,
        "payload": None,
        "facts": {
            "request_contract_valid": request_valid,
            "adapter_v6_presentation_envelope_exactly_verified": False,
            "adapter_v6_source_exactly_verified": False,
            "joint_local_research_source_known": False,
            "result_available": False,
            "presentation_http_contract_candidate_v6_versioned": True,
            "transport_registered": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "lineage": {
            "presentation_envelope_v1_implementation_sha256": (
                ENVELOPE_V1_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "source_bound": False,
            "request_documents_embedded": False,
            "verification_context_embedded": False,
        },
        "transport": _transport(),
        "authority": dict(_AUTHORITY),
        "blockers": [reason],
    }
    return seal_strict_canonical_document(document, "response_hash")


def _payload(envelope: dict[str, Any]) -> dict[str, Any]:
    local = envelope["local_decision"]
    source = envelope["source"]
    source_known = envelope["facts"]["joint_local_research_source_known"]
    if not source_known:
        gap_state = "UNKNOWN"
        gap_detail = "JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN"
    elif local["status"] == "BLOCK":
        gap_state = "BLOCKED"
        gap_detail = "LOCAL_RESEARCH_GATE_BLOCKED"
    else:
        gap_state = "PRESENT"
        gap_detail = "HTTP_REGISTRATION_CONSUMER_AND_CURRENT_GAPS"
    return {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "presentation_status": "UNMOUNTED_HTTP_CANDIDATE",
        "axis_order": list(AXIS_ORDER),
        "source": {
            "presentation_envelope": {
                "schema_version": envelope["schema_version"],
                "static_fingerprint": envelope["static_fingerprint"],
                "implementation_sha256": ENVELOPE_V1_IMPLEMENTATION_SHA256,
                "envelope_hash": envelope["envelope_hash"],
                "source_state": source["state"],
            },
            "adapter_v6": {
                "schema_version": source["adapter_v6_schema_version"],
                "adapter_v6_hash": source["adapter_v6_hash"],
                "exactly_verified": envelope["facts"][
                    "adapter_v6_exactly_verified"
                ],
            },
        },
        "stages": [
            deepcopy(envelope["stages"][0]),
            {"axis": "GAP", "state": gap_state, "detail": gap_detail},
            {
                "axis": "MATURITY",
                "state": "CANDIDATE_ONLY",
                "detail": "UNMOUNTED_HTTP_CANDIDATE_V6",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_ROUTE_MOUNT_CURRENT_PAPER_OR_LIVE_AUTHORITY",
            },
        ],
        "summary": {
            "source_state": source["state"],
            "local_status": local["status"],
            "local_decision": local["decision"],
            "adapter_v5_status": local["adapter_v5_status"],
            "downside_tail_source_state": local[
                "downside_tail_source_state"
            ],
            "downside_tail_gate_decision": local[
                "downside_tail_gate_decision"
            ],
            "downside_tail_gate_reason": local[
                "downside_tail_gate_reason"
            ],
            "risk_increasing": local["risk_increasing"],
            "local_blocker_count": len(local["blockers"]),
            "local_blockers": deepcopy(local["blockers"]),
            "http_candidate_blocker_count": len(HTTP_CANDIDATE_BLOCKERS),
            "http_candidate_blockers": list(HTTP_CANDIDATE_BLOCKERS),
        },
        "facts": {
            "presentation_envelope_v1_bound": True,
            "presentation_envelope_v1_document_embedded": False,
            "presentation_envelope_v1_verification_context_embedded": False,
            "adapter_v6_exactly_verified": envelope["facts"][
                "adapter_v6_exactly_verified"
            ],
            "joint_local_research_source_known": source_known,
            "trade_symbol_set_tail_identity_set_cross_bound": envelope[
                "facts"
            ]["trade_symbol_set_tail_identity_set_cross_bound"],
            "downside_tail_block_override_visible": True,
            "risk_reduction_joint_exemption_implemented": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }


def _known_blocked(envelope: dict[str, Any]) -> dict[str, Any]:
    local = envelope["local_decision"]
    source_known = envelope["facts"]["joint_local_research_source_known"]
    blockers = list(HTTP_CANDIDATE_BLOCKERS)
    if not source_known:
        blockers.append("JOINT_LOCAL_RESEARCH_SOURCE_UNKNOWN")
    elif local["status"] == "BLOCK":
        blockers.append("LOCAL_RESEARCH_GATE_BLOCKED")
    document = {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "interface_status": INTERFACE_STATUS,
        "state": KNOWN_BLOCKED_STATE,
        "payload": _payload(envelope),
        "facts": {
            "request_contract_valid": True,
            "adapter_v6_presentation_envelope_exactly_verified": True,
            "adapter_v6_source_exactly_verified": envelope["facts"][
                "adapter_v6_exactly_verified"
            ],
            "joint_local_research_source_known": source_known,
            "result_available": True,
            "presentation_http_contract_candidate_v6_versioned": True,
            "transport_registered": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "lineage": {
            "presentation_envelope_v1_schema_version": envelope[
                "schema_version"
            ],
            "presentation_envelope_v1_static_fingerprint": envelope[
                "static_fingerprint"
            ],
            "presentation_envelope_v1_implementation_sha256": (
                ENVELOPE_V1_IMPLEMENTATION_SHA256
            ),
            "presentation_envelope_v1_hash": envelope["envelope_hash"],
            "adapter_v6_hash": envelope["source"]["adapter_v6_hash"],
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "source_bound": True,
            "request_documents_embedded": False,
            "verification_context_embedded": False,
        },
        "transport": _transport(),
        "authority": dict(_AUTHORITY),
        "blockers": blockers,
    }
    return seal_strict_canonical_document(document, "response_hash")


def build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
    request_payload: Any,
    *,
    envelope_verification_context: Any,
) -> dict[str, Any]:
    """Build an unregistered response from an exact source envelope."""

    if not _request_valid(request_payload):
        return _unknown("REQUEST_CONTRACT_INVALID")
    if not _context_valid(envelope_verification_context):
        return _unknown("VERIFICATION_CONTEXT_INVALID", request_valid=True)
    envelope = request_payload[
        "adapter_v6_presentation_envelope_v1_document"
    ]
    expected_hash = request_payload["expected_presentation_envelope_hash"]
    if not _envelope_presentable(envelope, expected_hash):
        return _unknown("PRESENTATION_ENVELOPE_V1_UNPRESENTABLE", request_valid=True)
    receipt = _call_envelope_verifier(
        envelope,
        envelope_verification_context,
    )
    if not _envelope_receipt_passed(receipt, envelope):
        return _unknown("PRESENTATION_ENVELOPE_V1_UNVERIFIED", request_valid=True)
    return _known_blocked(envelope)


def verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
    document: Any,
    request_payload: Any,
    *,
    envelope_verification_context: Any,
) -> bool:
    """Verify an exact rebuild without granting transport or mount authority."""

    if type(document) is not dict or not _sealed_hash_exact(
        document, "response_hash"
    ):
        return False
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6(
        request_payload,
        envelope_verification_context=envelope_verification_context,
    )
    return strict_json_contract_equal(document, expected)


__all__ = [
    "AXIS_ORDER",
    "ENVELOPE_V1_IMPLEMENTATION_SHA256",
    "HTTP_CANDIDATE_BLOCKERS",
    "INTERFACE_STATUS",
    "KNOWN_BLOCKED_STATE",
    "PAYLOAD_SCHEMA_VERSION",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "UNKNOWN_STATE",
    "build_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6",
    "verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6",
]
