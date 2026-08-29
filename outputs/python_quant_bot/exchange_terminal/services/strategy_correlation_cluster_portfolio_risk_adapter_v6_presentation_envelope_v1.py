"""Neutral, summary-only presentation envelope for an exact adapter-v6 result."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v6 as adapter_v6,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-adapter-v6-"
    "presentation-envelope-v1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-adapter-v6-neutral-presentation-envelope-lock-1"
)
ADAPTER_V6_IMPLEMENTATION_SHA256 = (
    "cedfcc01bb11a5179db093acf806fcb2a49c92fb291182f0a8e34b1a66e464a2"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
PRESENTATION_GAPS = (
    "HTTP_CANDIDATE_V6_NOT_IMPLEMENTED",
    "PRESENTATION_CONSUMER_NOT_REGISTERED",
    "CURRENT_ADMISSION_LOCKED",
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_DOCUMENT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "status",
    "decision",
    "source",
    "component_states",
    "policy",
    "checks",
    "blockers",
    "facts",
    "authority",
    "adapter_v6_hash",
}
_SOURCE_AUTHORITY = {
    "research_only": True,
    "local_decision_only": True,
    "risk_service_invocation_allowed": False,
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


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _sealed_hash_exact(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(hash_field)):
        return False
    unsigned = deepcopy(document)
    claimed = unsigned.pop(hash_field, None)
    return claimed == strict_canonical_hash(unsigned)


def _source_shape_exact(document: Any) -> bool:
    if type(document) is not dict or set(document) != _SOURCE_DOCUMENT_KEYS:
        return False
    source = document.get("source")
    component_states = document.get("component_states")
    policy = document.get("policy")
    facts = document.get("facts")
    blockers = document.get("blockers")
    checks = document.get("checks")
    if not all(
        type(value) is dict
        for value in (source, component_states, policy, facts)
    ):
        return False
    if type(blockers) is not list or type(checks) is not list:
        return False
    return bool(
        document.get("schema_version") == adapter_v6.SCHEMA_VERSION
        and document.get("static_fingerprint")
        == adapter_v6.STATIC_FINGERPRINT
        and document.get("status") in {"PASS", "BLOCK"}
        and type(document.get("decision")) is str
        and document["decision"]
        in {
            "BLOCK_JOINT_SOURCE_UNVERIFIED",
            "BLOCK_ADAPTER_V5_COMPONENT",
            "BLOCK_ADAPTER_V5_STATUS_UNKNOWN",
            "BLOCK_DOWNSIDE_TAIL_COUPLING",
            "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE",
            "BLOCK_DOWNSIDE_TAIL_STATUS_UNKNOWN",
        }
        and _sealed_hash_exact(document, "adapter_v6_hash")
        and strict_json_contract_equal(document.get("authority"), _SOURCE_AUTHORITY)
        and policy.get("tail_block_overrides_adapter_v5_pass") is True
        and policy.get("risk_reduction_joint_exemption_implemented") is False
        and facts.get("risk_reduction_joint_exemption_implemented") is False
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and facts.get("aligned_observations_embedded") is False
        and facts.get("pair_results_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("risk_service_invoked") is False
        and facts.get("runtime_consumer_bound") is False
        and facts.get("profitability_proven") is False
    )


def _source_exactly_verified(
    document: Any,
    adapter_v5_document: Any,
    downside_tail_registration: Any,
    downside_tail_evaluation: Any,
    *,
    expected_adapter_v6_hash: Any,
    adapter_v5_verification_context: Any,
    downside_tail_verification_context: Any,
) -> bool:
    if (
        not _is_hash(expected_adapter_v6_hash)
        or not _source_shape_exact(document)
        or document.get("adapter_v6_hash") != expected_adapter_v6_hash
    ):
        return False
    try:
        receipt = adapter_v6.verify_strategy_correlation_cluster_portfolio_risk_adapter_v6(
            document,
            adapter_v5_document,
            downside_tail_registration,
            downside_tail_evaluation,
            adapter_v5_verification_context=adapter_v5_verification_context,
            downside_tail_verification_context=(
                downside_tail_verification_context
            ),
        )
    except (AttributeError, KeyError, MemoryError, TypeError, ValueError):
        return False
    return bool(
        type(receipt) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("adapter_v6_exactly_rebuilt") is True
        and receipt.get("adapter_v6_hash") == expected_adapter_v6_hash
        and receipt.get("risk_reduction_joint_exemption_verified") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("live_order_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("writer_allowed") is False
    )


def _unknown() -> dict[str, Any]:
    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "decision": "UNKNOWN_SOURCE",
        "axis_order": list(AXIS_ORDER),
        "source": {
            "state": "UNKNOWN",
            "adapter_v6_schema_version": "UNKNOWN",
            "adapter_v6_static_fingerprint": "UNKNOWN",
            "adapter_v6_hash": None,
            "adapter_v6_implementation_sha256": (
                ADAPTER_V6_IMPLEMENTATION_SHA256
            ),
            "adapter_v5_hash": None,
            "downside_tail_registration_hash": None,
            "downside_tail_evaluation_hash": None,
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
            "blockers": [],
        },
        "policy": {
            "tail_block_overrides_linear_multi_window_clear": True,
            "risk_reduction_joint_exemption_implemented": False,
        },
        "gaps": {
            "local_blocker_count": None,
            "presentation_blocker_count": len(PRESENTATION_GAPS),
            "presentation_blockers": list(PRESENTATION_GAPS),
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
                "detail": "UNMOUNTED_VERSIONED_PRESENTATION_ENVELOPE",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
            },
        ],
        "facts": {
            "adapter_v6_exactly_verified": False,
            "joint_local_research_source_known": False,
            "trade_symbol_set_tail_identity_set_cross_bound": False,
            "downside_tail_block_override_visible": True,
            "risk_reduction_joint_exemption_implemented": False,
            "projection_only": True,
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
            "aligned_observations_embedded": False,
            "pair_results_embedded": False,
            "positions_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "envelope_hash")


def _project(document: dict[str, Any]) -> dict[str, Any]:
    source = document["source"]
    components = document["component_states"]
    facts = document["facts"]
    source_known = bool(
        facts.get("joint_local_research_decision_made") is True
        and components.get("downside_tail_source_state") == "OBSERVED"
        and components.get("downside_tail_gate_decision")
        in {"PASS", "BLOCK"}
    )
    local_status = document["status"] if source_known else "UNKNOWN"
    local_decision = document["decision"] if source_known else "UNKNOWN"
    if not source_known:
        gap_state = "UNKNOWN"
        gap_detail = "SOURCE_CONTRACT_UNKNOWN"
    elif local_status == "BLOCK":
        gap_state = "BLOCKED"
        gap_detail = "LOCAL_RESEARCH_GATE_BLOCKED"
    else:
        gap_state = "CLEAR_WITH_GOVERNANCE_GAPS"
        gap_detail = "LOCAL_RESEARCH_GATE_CLEAR_GOVERNANCE_GAPS_REMAIN"
    local_blockers = deepcopy(document["blockers"])
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCK",
        "decision": (
            "EXACT_ADAPTER_V6_LOCAL_RESEARCH_STATE_PROJECTED_"
            "AUTHORITY_UNCHANGED"
            if source_known
            else "EXACT_ADAPTER_V6_UNKNOWN_SOURCE_PROJECTED_"
            "AUTHORITY_UNCHANGED"
        ),
        "axis_order": list(AXIS_ORDER),
        "source": {
            "state": "OBSERVED" if source_known else "UNKNOWN",
            "adapter_v6_schema_version": document["schema_version"],
            "adapter_v6_static_fingerprint": document["static_fingerprint"],
            "adapter_v6_hash": document["adapter_v6_hash"],
            "adapter_v6_implementation_sha256": (
                ADAPTER_V6_IMPLEMENTATION_SHA256
            ),
            "adapter_v5_hash": (
                source.get("adapter_v5_hash")
                if _is_hash(source.get("adapter_v5_hash"))
                else None
            ),
            "downside_tail_registration_hash": (
                source.get("downside_tail_registration_hash")
                if _is_hash(source.get("downside_tail_registration_hash"))
                else None
            ),
            "downside_tail_evaluation_hash": (
                source.get("downside_tail_evaluation_hash")
                if _is_hash(source.get("downside_tail_evaluation_hash"))
                else None
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "local_decision": {
            "status": local_status,
            "decision": local_decision,
            "adapter_v5_status": (
                components.get("adapter_v5_status")
                if source_known
                else "UNKNOWN"
            ),
            "downside_tail_source_state": (
                components.get("downside_tail_source_state")
                if source_known
                else "UNKNOWN"
            ),
            "downside_tail_gate_decision": (
                components.get("downside_tail_gate_decision")
                if source_known
                else "UNKNOWN"
            ),
            "downside_tail_gate_reason": (
                components.get("downside_tail_gate_reason")
                if source_known
                else "UNKNOWN"
            ),
            "risk_increasing": (
                components.get("risk_increasing") if source_known else None
            ),
            "blockers": local_blockers,
        },
        "policy": {
            "tail_block_overrides_linear_multi_window_clear": True,
            "risk_reduction_joint_exemption_implemented": False,
        },
        "gaps": {
            "local_blocker_count": len(local_blockers),
            "presentation_blocker_count": len(PRESENTATION_GAPS),
            "presentation_blockers": list(PRESENTATION_GAPS),
        },
        "stages": [
            {
                "axis": "SOURCE",
                "state": "OBSERVED" if source_known else "UNKNOWN",
                "detail": (
                    "EXACT_ADAPTER_V6_AND_DOWNSIDE_TAIL_SOURCE_BOUND"
                    if source_known
                    else "EXACT_ADAPTER_V6_WITH_UNKNOWN_JOINT_SOURCE"
                ),
            },
            {"axis": "GAP", "state": gap_state, "detail": gap_detail},
            {
                "axis": "MATURITY",
                "state": "CANDIDATE_ONLY",
                "detail": "UNMOUNTED_VERSIONED_PRESENTATION_ENVELOPE",
            },
            {
                "axis": "PERMISSION",
                "state": "UNAUTHORIZED",
                "detail": "NO_EXECUTION_OR_ACTIVATION_PERMISSION",
            },
        ],
        "facts": {
            "adapter_v6_exactly_verified": True,
            "joint_local_research_source_known": source_known,
            "trade_symbol_set_tail_identity_set_cross_bound": bool(
                source_known
                and facts.get(
                    "trade_symbol_set_tail_identity_set_cross_bound"
                )
                is True
            ),
            "downside_tail_block_override_visible": True,
            "risk_reduction_joint_exemption_implemented": False,
            "projection_only": True,
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
            "aligned_observations_embedded": False,
            "pair_results_embedded": False,
            "positions_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(envelope, "envelope_hash")


def build_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
    adapter_v6_document: Any,
    adapter_v5_document: Any,
    downside_tail_registration: Any,
    downside_tail_evaluation: Any,
    *,
    expected_adapter_v6_hash: Any,
    adapter_v5_verification_context: Any,
    downside_tail_verification_context: Any,
) -> dict[str, Any]:
    """Build a neutral envelope without granting presentation or runtime mount."""

    if not _source_exactly_verified(
        adapter_v6_document,
        adapter_v5_document,
        downside_tail_registration,
        downside_tail_evaluation,
        expected_adapter_v6_hash=expected_adapter_v6_hash,
        adapter_v5_verification_context=adapter_v5_verification_context,
        downside_tail_verification_context=downside_tail_verification_context,
    ):
        return _unknown()
    return _project(adapter_v6_document)


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
    document: Any,
    adapter_v6_document: Any,
    adapter_v5_document: Any,
    downside_tail_registration: Any,
    downside_tail_evaluation: Any,
    *,
    expected_adapter_v6_hash: Any,
    adapter_v5_verification_context: Any,
    downside_tail_verification_context: Any,
) -> dict[str, Any]:
    """Verify an exact deterministic envelope rebuild."""

    expected = build_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1(
        adapter_v6_document,
        adapter_v5_document,
        downside_tail_registration,
        downside_tail_evaluation,
        expected_adapter_v6_hash=expected_adapter_v6_hash,
        adapter_v5_verification_context=adapter_v5_verification_context,
        downside_tail_verification_context=downside_tail_verification_context,
    )
    exact = bool(
        type(document) is dict
        and _sealed_hash_exact(document, "envelope_hash")
        and strict_json_contract_equal(document, expected)
    )
    return seal_strict_canonical_document(
        {
            "schema_version": VERIFICATION_SCHEMA_VERSION,
            "status": "PASS" if exact else "BLOCK",
            "envelope_exactly_verified": exact,
            "envelope_status": expected.get("status") if exact else "UNKNOWN",
            "envelope_hash": expected.get("envelope_hash") if exact else None,
            "blockers": [] if exact else ["PRESENTATION_ENVELOPE_NOT_EXACT"],
            "presentation_consumer_activation_allowed": False,
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
    "ADAPTER_V6_IMPLEMENTATION_SHA256",
    "AXIS_ORDER",
    "PRESENTATION_GAPS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6_presentation_envelope_v1",
]
