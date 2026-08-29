"""Summary-only frontend projection for an exact presentation candidate-v5 response."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.interfaces.http.strategy_correlation_cluster_portfolio_risk_presentation_candidate_v5 import (
    verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v5 as _VERIFY_CANDIDATE_V5,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-projection-v5"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-projection-v5-verification-v1"
)
STATIC_FINGERPRINT = "20260823-http-candidate-v5-frontend-projection-lock-1"
CANDIDATE_V5_IMPLEMENTATION_SHA256 = (
    "ec407914dc260a1110e17ee932c80a5d5786183e4c34601f9604d0e88482358b"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)

_CANDIDATE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-candidate-response-v5"
)
_CANDIDATE_PAYLOAD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-presentation-http-payload-v5"
)
_CANDIDATE_STATIC_FINGERPRINT = (
    "20260823-portfolio-risk-presentation-http-adapter-v5-unregistered-candidate-1"
)
_ADAPTER_V5_SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v5"
_AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
_CONTEXT_KEYS = frozenset(
    {
        "request_payload",
        "v4_verification_context",
        "adapter_v5_verification_context",
    }
)
_CANDIDATE_KEYS = frozenset(
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
_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "presentation_status",
        "axis_order",
        "source",
        "stages",
        "summary",
        "facts",
        "authority",
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


def _projection_authority() -> dict[str, bool]:
    return {
        "research_only": True,
        "presentation_only": True,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _candidate_authority() -> dict[str, bool]:
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


def _candidate_transport() -> dict[str, Any]:
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


def _context_valid(context: Any) -> bool:
    return (
        isinstance(context, dict)
        and set(context) == _CONTEXT_KEYS
        and all(isinstance(context.get(key), dict) for key in _CONTEXT_KEYS)
    )


def _candidate_presentable(document: Any) -> bool:
    if not isinstance(document, dict) or set(document) != _CANDIDATE_KEYS:
        return False
    payload = document.get("payload")
    facts = document.get("facts")
    lineage = document.get("lineage")
    if not all(isinstance(value, dict) for value in (payload, facts, lineage)):
        return False
    if set(payload) != _PAYLOAD_KEYS:
        return False
    source = payload.get("source")
    summary = payload.get("summary")
    payload_facts = payload.get("facts")
    stages = payload.get("stages")
    if not all(
        isinstance(value, dict) for value in (source, summary, payload_facts)
    ) or not isinstance(stages, list):
        return False
    if set(source) != {"preregistration", "joint_portfolio_risk"}:
        return False
    preregistration = source.get("preregistration")
    joint = source.get("joint_portfolio_risk")
    if not isinstance(preregistration, dict) or not isinstance(joint, dict):
        return False
    if len(stages) != 4 or payload.get("axis_order") != list(_AXIS_ORDER):
        return False
    if any(
        not isinstance(stage, dict)
        or set(stage) != {"axis", "state", "detail"}
        or stage.get("axis") != axis
        or not isinstance(stage.get("state"), str)
        or not isinstance(stage.get("detail"), str)
        for stage, axis in zip(stages, _AXIS_ORDER)
    ):
        return False
    joint_passed = joint.get("status") == "PASS"
    return (
        document.get("schema_version") == _CANDIDATE_SCHEMA_VERSION
        and document.get("static_fingerprint") == _CANDIDATE_STATIC_FINGERPRINT
        and document.get("interface_status") == "UNREGISTERED_CANDIDATE"
        and document.get("state") == "KNOWN_BLOCKED"
        and _sealed_hash_exact(document, "response_hash")
        and payload.get("schema_version") == _CANDIDATE_PAYLOAD_SCHEMA_VERSION
        and payload.get("presentation_status") == "UNMOUNTED_HTTP_CANDIDATE"
        and payload.get("authority") == _candidate_authority()
        and joint.get("schema_version") == _ADAPTER_V5_SCHEMA_VERSION
        and joint.get("implementation_sha256")
        == "d44d5a1ca180d6b7b432266be6f4ca00cc639ef949a4bc56226ad77d2bccd509"
        and joint.get("status") in {"PASS", "BLOCK", "UNKNOWN"}
        and isinstance(joint.get("decision"), str)
        and _is_hash(joint.get("adapter_v5_hash"))
        and _is_hash(joint.get("trade_identity_hash"))
        and isinstance(joint.get("anchor_window_id"), str)
        and _is_hash(preregistration.get("preregistration_hash"))
        and summary.get("portfolio_risk_adapter_v5_status") == joint.get("status")
        and summary.get("portfolio_risk_adapter_v5_decision")
        == joint.get("decision")
        and summary.get("joint_risk_gate_passed") is joint_passed
        and facts.get("joint_risk_gate_passed") is joint_passed
        and facts.get("transport_registered") is False
        and facts.get("route_registered") is False
        and facts.get("ui_mounted") is False
        and facts.get("runtime_mutations_performed") is False
        and facts.get("profitability_proven") is False
        and payload_facts.get("portfolio_risk_adapter_v5_document_embedded") is False
        and payload_facts.get(
            "portfolio_risk_adapter_v5_verification_context_embedded"
        )
        is False
        and payload_facts.get("runtime_consumer_bound") is False
        and payload_facts.get("profitability_proven") is False
        and lineage.get("request_documents_embedded") is False
        and lineage.get("verification_contexts_embedded") is False
        and document.get("transport") == _candidate_transport()
        and document.get("authority") == _candidate_authority()
        and isinstance(document.get("blockers"), list)
    )


def _verify_candidate(document: dict[str, Any], context: dict[str, Any]) -> bool:
    try:
        verified = _VERIFY_CANDIDATE_V5(
            document,
            context["request_payload"],
            v4_verification_context=context["v4_verification_context"],
            adapter_v5_verification_context=context[
                "adapter_v5_verification_context"
            ],
        )
    except Exception:
        return False
    return verified is True


def _unknown() -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "decision": "UNKNOWN_SOURCE",
        "source": {
            "candidate_v5_schema_version": "UNKNOWN",
            "candidate_v5_static_fingerprint": "UNKNOWN",
            "candidate_v5_response_hash": None,
            "candidate_v5_exactly_verified": False,
            "candidate_v5_implementation_sha256": CANDIDATE_V5_IMPLEMENTATION_SHA256,
            "candidate_state": "UNKNOWN",
            "source_preregistration_hash": None,
            "portfolio_risk_adapter_v5_hash": None,
        },
        "local_decision": {
            "status": "UNKNOWN",
            "decision": "UNKNOWN",
            "joint_risk_gate_passed": False,
            "blockers": [],
        },
        "joint_risk": {
            "assessment": "UNKNOWN",
            "multi_window_stability_gate_verified": False,
            "anchor_window_budget_and_context_bound": False,
            "trade_identity_cross_bound": False,
            "anchor_window_id": None,
            "trade_identity_hash": None,
        },
        "gaps": {
            "remaining_blocker_count": None,
            "remaining_blockers": [],
            "candidate_blockers": [],
        },
        "stages": [
            {"key": "SOURCE", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {"key": "GAP", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {"key": "MATURITY", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {
                "key": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_PERMISSION_CAN_BE_INFERRED",
            },
        ],
        "facts": {
            "projection_only": True,
            "candidate_v5_exactly_verified": False,
            "http_candidate_to_projection_bound": False,
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "positions_embedded": False,
            "correlation_matrices_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
        },
        "authority": _projection_authority(),
    }
    return seal_strict_canonical_document(document, "projection_hash")


def _project(document: dict[str, Any]) -> dict[str, Any]:
    payload = document["payload"]
    summary = payload["summary"]
    joint = payload["source"]["joint_portfolio_risk"]
    preregistration = payload["source"]["preregistration"]
    stages = [
        {"key": stage["axis"], "state": stage["state"], "detail": stage["detail"]}
        for stage in payload["stages"]
    ]
    projection = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "decision": "EXACT_HTTP_CANDIDATE_V5_PROJECTED_KNOWN_BLOCKED_AUTHORITY_UNCHANGED",
        "source": {
            "candidate_v5_schema_version": document["schema_version"],
            "candidate_v5_static_fingerprint": document["static_fingerprint"],
            "candidate_v5_response_hash": document["response_hash"],
            "candidate_v5_exactly_verified": True,
            "candidate_v5_implementation_sha256": CANDIDATE_V5_IMPLEMENTATION_SHA256,
            "candidate_state": document["state"],
            "source_preregistration_hash": preregistration["preregistration_hash"],
            "portfolio_risk_adapter_v5_hash": joint["adapter_v5_hash"],
        },
        "local_decision": {
            "status": joint["status"],
            "decision": joint["decision"],
            "joint_risk_gate_passed": summary["joint_risk_gate_passed"],
            "blockers": deepcopy(document["blockers"]),
        },
        "joint_risk": {
            "assessment": (
                "LOCAL_JOINT_RESEARCH_GATE_PASSED"
                if summary["joint_risk_gate_passed"]
                else "LOCAL_JOINT_RESEARCH_GATE_BLOCKED"
            ),
            "multi_window_stability_gate_verified": summary[
                "multi_window_stability_gate_verified"
            ],
            "anchor_window_budget_and_context_bound": summary[
                "anchor_window_budget_and_context_bound"
            ],
            "trade_identity_cross_bound": summary["trade_identity_cross_bound"],
            "anchor_window_id": joint["anchor_window_id"],
            "trade_identity_hash": joint["trade_identity_hash"],
        },
        "gaps": {
            "remaining_blocker_count": summary["remaining_blocker_count"],
            "remaining_blockers": deepcopy(summary["remaining_blockers"]),
            "candidate_blockers": deepcopy(document["blockers"]),
        },
        "stages": stages,
        "facts": {
            "projection_only": True,
            "candidate_v5_exactly_verified": True,
            "http_candidate_to_projection_bound": True,
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "positions_embedded": False,
            "correlation_matrices_embedded": False,
            "profitability_proven": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
        },
        "authority": _projection_authority(),
    }
    return seal_strict_canonical_document(projection, "projection_hash")


def project_strategy_correlation_cluster_portfolio_risk_projection_v5(
    presentation_candidate_v5_document: Any,
    *,
    presentation_candidate_v5_verification_context: Any,
) -> dict[str, Any]:
    """Project an exact candidate response without runtime or mount authority."""

    if not _context_valid(presentation_candidate_v5_verification_context):
        return _unknown()
    if not _candidate_presentable(presentation_candidate_v5_document):
        return _unknown()
    if not _verify_candidate(
        presentation_candidate_v5_document,
        presentation_candidate_v5_verification_context,
    ):
        return _unknown()
    return _project(presentation_candidate_v5_document)


def verify_strategy_correlation_cluster_portfolio_risk_projection_v5(
    document: Any,
    presentation_candidate_v5_document: Any,
    *,
    presentation_candidate_v5_verification_context: Any,
) -> dict[str, Any]:
    """Verify an exact deterministic projection rebuild."""

    expected = project_strategy_correlation_cluster_portfolio_risk_projection_v5(
        presentation_candidate_v5_document,
        presentation_candidate_v5_verification_context=(
            presentation_candidate_v5_verification_context
        ),
    )
    exact = (
        isinstance(document, dict)
        and _sealed_hash_exact(document, "projection_hash")
        and strict_json_contract_equal(document, expected)
    )
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "projection_exactly_verified": exact,
        "projection_status": document.get("status") if exact else None,
        "projection_hash": document.get("projection_hash") if exact else None,
        "blockers": [] if exact else ["PROJECTION_V5_NOT_EXACT"],
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "presentation_consumer_activation_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
