"""Summary-only frontend projection for an exact HTTP candidate-v6 response."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.interfaces.http import (
    strategy_correlation_cluster_portfolio_risk_presentation_candidate_v6 as candidate_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-projection-v6"
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-envelope-first-http-candidate-v6-frontend-projection-lock-1"
)
CANDIDATE_V6_IMPLEMENTATION_SHA256 = (
    "04ef8a63761f12dacb48d2b41a57f40f304d04b913e7117572a2a627d8fd5096"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_VERIFY_CANDIDATE = (
    candidate_v6.verify_strategy_correlation_cluster_portfolio_risk_presentation_http_candidate_response_v6
)
_CONTEXT_KEYS = {"request_payload", "envelope_verification_context"}
_CANDIDATE_KEYS = {
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
_PAYLOAD_KEYS = {
    "schema_version",
    "presentation_status",
    "axis_order",
    "source",
    "stages",
    "summary",
    "facts",
    "authority",
}
_SUMMARY_KEYS = {
    "source_state",
    "local_status",
    "local_decision",
    "adapter_v5_status",
    "downside_tail_source_state",
    "downside_tail_gate_decision",
    "downside_tail_gate_reason",
    "risk_increasing",
    "local_blocker_count",
    "local_blockers",
    "http_candidate_blocker_count",
    "http_candidate_blockers",
}
_CANDIDATE_AUTHORITY = {
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
_AUTHORITY = {
    "research_only": True,
    "presentation_only": True,
    "frontend_projection_only": True,
    "presentation_consumer_activation_allowed": False,
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
    return bool(
        type(context) is dict
        and set(context) == _CONTEXT_KEYS
        and type(context.get("request_payload")) is dict
        and type(context.get("envelope_verification_context")) is dict
    )


def _candidate_presentable(document: Any) -> bool:
    if type(document) is not dict or set(document) != _CANDIDATE_KEYS:
        return False
    payload = document.get("payload")
    response_facts = document.get("facts")
    lineage = document.get("lineage")
    blockers = document.get("blockers")
    if not all(
        type(value) is dict for value in (payload, response_facts, lineage)
    ) or type(blockers) is not list:
        return False
    if set(payload) != _PAYLOAD_KEYS:
        return False
    source = payload.get("source")
    summary = payload.get("summary")
    payload_facts = payload.get("facts")
    stages = payload.get("stages")
    if not all(
        type(value) is dict for value in (source, summary, payload_facts)
    ) or type(stages) is not list:
        return False
    if set(summary) != _SUMMARY_KEYS:
        return False
    if set(source) != {"presentation_envelope", "adapter_v6"}:
        return False
    envelope_source = source.get("presentation_envelope")
    adapter_source = source.get("adapter_v6")
    if type(envelope_source) is not dict or type(adapter_source) is not dict:
        return False
    source_state = summary.get("source_state")
    source_known = payload_facts.get("joint_local_research_source_known")
    local_status = summary.get("local_status")
    source_consistent = bool(
        (
            source_known is True
            and source_state == "OBSERVED"
            and local_status in {"PASS", "BLOCK"}
        )
        or (
            source_known is False
            and source_state == "UNKNOWN"
            and local_status == "UNKNOWN"
        )
    )
    return bool(
        document.get("schema_version") == candidate_v6.RESPONSE_SCHEMA_VERSION
        and document.get("static_fingerprint")
        == candidate_v6.STATIC_FINGERPRINT
        and document.get("interface_status")
        == candidate_v6.INTERFACE_STATUS
        and document.get("state") == candidate_v6.KNOWN_BLOCKED_STATE
        and _sealed_hash_exact(document, "response_hash")
        and payload.get("schema_version") == candidate_v6.PAYLOAD_SCHEMA_VERSION
        and payload.get("presentation_status") == "UNMOUNTED_HTTP_CANDIDATE"
        and payload.get("axis_order") == list(AXIS_ORDER)
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
        and source_consistent
        and envelope_source.get("schema_version")
        == candidate_v6.envelope_v1.SCHEMA_VERSION
        and envelope_source.get("static_fingerprint")
        == candidate_v6.envelope_v1.STATIC_FINGERPRINT
        and envelope_source.get("implementation_sha256")
        == candidate_v6.ENVELOPE_V1_IMPLEMENTATION_SHA256
        and _is_hash(envelope_source.get("envelope_hash"))
        and envelope_source.get("source_state") == source_state
        and adapter_source.get("exactly_verified")
        is payload_facts.get("adapter_v6_exactly_verified")
        and (
            _is_hash(adapter_source.get("adapter_v6_hash"))
            if adapter_source.get("exactly_verified") is True
            else adapter_source.get("adapter_v6_hash") is None
        )
        and type(summary.get("local_decision")) is str
        and summary.get("adapter_v5_status")
        in {"PASS", "BLOCK", "UNKNOWN"}
        and summary.get("downside_tail_source_state")
        in {"OBSERVED", "UNKNOWN"}
        and summary.get("downside_tail_gate_decision")
        in {"PASS", "BLOCK", "UNKNOWN"}
        and type(summary.get("downside_tail_gate_reason")) is str
        and (
            type(summary.get("risk_increasing")) is bool
            or summary.get("risk_increasing") is None
        )
        and type(summary.get("local_blockers")) is list
        and summary.get("local_blocker_count")
        == len(summary.get("local_blockers"))
        and summary.get("http_candidate_blockers")
        == list(candidate_v6.HTTP_CANDIDATE_BLOCKERS)
        and summary.get("http_candidate_blocker_count")
        == len(candidate_v6.HTTP_CANDIDATE_BLOCKERS)
        and payload_facts.get("presentation_envelope_v1_bound") is True
        and payload_facts.get("presentation_envelope_v1_document_embedded")
        is False
        and payload_facts.get(
            "presentation_envelope_v1_verification_context_embedded"
        )
        is False
        and payload_facts.get("downside_tail_block_override_visible") is True
        and payload_facts.get("risk_reduction_joint_exemption_implemented")
        is False
        and payload_facts.get("runtime_consumer_bound") is False
        and payload_facts.get("profitability_proven") is False
        and response_facts.get("request_contract_valid") is True
        and response_facts.get(
            "adapter_v6_presentation_envelope_exactly_verified"
        )
        is True
        and response_facts.get("joint_local_research_source_known")
        is source_known
        and response_facts.get("result_available") is True
        and response_facts.get(
            "presentation_http_contract_candidate_v6_versioned"
        )
        is True
        and response_facts.get("transport_registered") is False
        and response_facts.get("route_registered") is False
        and response_facts.get("ui_mounted") is False
        and response_facts.get("runtime_mutations_performed") is False
        and response_facts.get("profitability_proven") is False
        and lineage.get("presentation_envelope_v1_implementation_sha256")
        == candidate_v6.ENVELOPE_V1_IMPLEMENTATION_SHA256
        and lineage.get("presentation_envelope_v1_hash")
        == envelope_source.get("envelope_hash")
        and lineage.get("strict_canonical_implementation_sha256")
        == STRICT_CANONICAL_IMPLEMENTATION_SHA256
        and lineage.get("source_bound") is True
        and lineage.get("request_documents_embedded") is False
        and lineage.get("verification_context_embedded") is False
        and document.get("transport") == _candidate_transport()
        and strict_json_contract_equal(
            document.get("authority"), _CANDIDATE_AUTHORITY
        )
        and strict_json_contract_equal(
            payload.get("authority"), _CANDIDATE_AUTHORITY
        )
        and "HTTP_CANDIDATE_V6_UNREGISTERED" in blockers
    )


def _verify_candidate(document: Any, context: Any) -> bool:
    if not _context_valid(context):
        return False
    try:
        verified = _VERIFY_CANDIDATE(
            document,
            context["request_payload"],
            envelope_verification_context=context[
                "envelope_verification_context"
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
        "axis_order": list(AXIS_ORDER),
        "source": {
            "state": "UNKNOWN",
            "candidate_v6_schema_version": "UNKNOWN",
            "candidate_v6_static_fingerprint": "UNKNOWN",
            "candidate_v6_response_hash": None,
            "candidate_v6_implementation_sha256": (
                CANDIDATE_V6_IMPLEMENTATION_SHA256
            ),
            "candidate_state": "UNKNOWN",
            "presentation_envelope_v1_hash": None,
            "adapter_v6_hash": None,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "local_decision": {
            "status": "UNKNOWN",
            "decision": "UNKNOWN",
            "adapter_v5_status": "UNKNOWN",
            "downside_tail_source_state": "UNKNOWN",
            "downside_tail_gate_decision": "UNKNOWN",
            "downside_tail_gate_reason": "UNKNOWN",
            "risk_increasing": None,
        },
        "gaps": {
            "local_blocker_count": None,
            "local_blockers": [],
            "http_candidate_blocker_count": None,
            "http_candidate_blockers": [],
            "candidate_blockers": [],
        },
        "stages": [
            {"axis": "SOURCE", "state": "UNKNOWN", "detail": "UNKNOWN"},
            {
                "axis": "GAP",
                "state": "UNKNOWN",
                "detail": "SOURCE_CONTRACT_UNKNOWN",
            },
            {
                "axis": "MATURITY",
                "state": "CANDIDATE_ONLY",
                "detail": "UNMOUNTED_FRONTEND_PROJECTION_V6",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_PRESENTATION_MOUNT_OR_EXECUTION_PERMISSION",
            },
        ],
        "facts": {
            "candidate_v6_exactly_verified": False,
            "presentation_envelope_v1_bound": False,
            "adapter_v6_exactly_verified": False,
            "joint_local_research_source_known": False,
            "trade_symbol_set_tail_identity_set_cross_bound": False,
            "downside_tail_block_override_visible": True,
            "risk_reduction_joint_exemption_implemented": False,
            "projection_only": True,
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "positions_embedded": False,
            "aligned_observations_embedded": False,
            "pair_results_embedded": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "projection_hash")


def _project(document: dict[str, Any]) -> dict[str, Any]:
    payload = document["payload"]
    source = payload["source"]
    summary = payload["summary"]
    payload_facts = payload["facts"]
    envelope_source = source["presentation_envelope"]
    adapter_source = source["adapter_v6"]
    projection = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "decision": (
            "EXACT_HTTP_CANDIDATE_V6_PROJECTED_AUTHORITY_UNCHANGED"
        ),
        "axis_order": list(AXIS_ORDER),
        "source": {
            "state": summary["source_state"],
            "candidate_v6_schema_version": document["schema_version"],
            "candidate_v6_static_fingerprint": document[
                "static_fingerprint"
            ],
            "candidate_v6_response_hash": document["response_hash"],
            "candidate_v6_implementation_sha256": (
                CANDIDATE_V6_IMPLEMENTATION_SHA256
            ),
            "candidate_state": document["state"],
            "presentation_envelope_v1_hash": envelope_source[
                "envelope_hash"
            ],
            "adapter_v6_hash": adapter_source["adapter_v6_hash"],
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "local_decision": {
            "status": summary["local_status"],
            "decision": summary["local_decision"],
            "adapter_v5_status": summary["adapter_v5_status"],
            "downside_tail_source_state": summary[
                "downside_tail_source_state"
            ],
            "downside_tail_gate_decision": summary[
                "downside_tail_gate_decision"
            ],
            "downside_tail_gate_reason": summary[
                "downside_tail_gate_reason"
            ],
            "risk_increasing": summary["risk_increasing"],
        },
        "gaps": {
            "local_blocker_count": summary["local_blocker_count"],
            "local_blockers": deepcopy(summary["local_blockers"]),
            "http_candidate_blocker_count": summary[
                "http_candidate_blocker_count"
            ],
            "http_candidate_blockers": deepcopy(
                summary["http_candidate_blockers"]
            ),
            "candidate_blockers": deepcopy(document["blockers"]),
        },
        "stages": deepcopy(payload["stages"]),
        "facts": {
            "candidate_v6_exactly_verified": True,
            "presentation_envelope_v1_bound": True,
            "adapter_v6_exactly_verified": payload_facts[
                "adapter_v6_exactly_verified"
            ],
            "joint_local_research_source_known": payload_facts[
                "joint_local_research_source_known"
            ],
            "trade_symbol_set_tail_identity_set_cross_bound": payload_facts[
                "trade_symbol_set_tail_identity_set_cross_bound"
            ],
            "downside_tail_block_override_visible": True,
            "risk_reduction_joint_exemption_implemented": False,
            "projection_only": True,
            "source_document_embedded": False,
            "verification_context_embedded": False,
            "positions_embedded": False,
            "aligned_observations_embedded": False,
            "pair_results_embedded": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(projection, "projection_hash")


def project_strategy_correlation_cluster_portfolio_risk_projection_v6(
    presentation_candidate_v6_document: Any,
    *,
    presentation_candidate_v6_verification_context: Any,
) -> dict[str, Any]:
    """Project an exact unmounted candidate without adding authority."""

    if not _context_valid(
        presentation_candidate_v6_verification_context
    ):
        return _unknown()
    if not _candidate_presentable(presentation_candidate_v6_document):
        return _unknown()
    if not _verify_candidate(
        presentation_candidate_v6_document,
        presentation_candidate_v6_verification_context,
    ):
        return _unknown()
    return _project(presentation_candidate_v6_document)


def verify_strategy_correlation_cluster_portfolio_risk_projection_v6(
    document: Any,
    presentation_candidate_v6_document: Any,
    *,
    presentation_candidate_v6_verification_context: Any,
) -> dict[str, Any]:
    """Verify an exact deterministic frontend projection rebuild."""

    expected = project_strategy_correlation_cluster_portfolio_risk_projection_v6(
        presentation_candidate_v6_document,
        presentation_candidate_v6_verification_context=(
            presentation_candidate_v6_verification_context
        ),
    )
    exact = bool(
        type(document) is dict
        and _sealed_hash_exact(document, "projection_hash")
        and strict_json_contract_equal(document, expected)
    )
    return seal_strict_canonical_document(
        {
            "schema_version": VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if exact else "BLOCK",
            "projection_exactly_verified": exact,
            "projection_status": expected.get("status") if exact else "UNKNOWN",
            "projection_hash": expected.get("projection_hash") if exact else None,
            "blockers": [] if exact else ["PROJECTION_V6_NOT_EXACT"],
            "presentation_consumer_activation_allowed": False,
            "presentation_mount_allowed": False,
            "formal_registry_activation_allowed": False,
            "current_admission_allowed": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "verification_hash",
    )


__all__ = [
    "AXIS_ORDER",
    "CANDIDATE_V6_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "project_strategy_correlation_cluster_portfolio_risk_projection_v6",
    "verify_strategy_correlation_cluster_portfolio_risk_projection_v6",
]
