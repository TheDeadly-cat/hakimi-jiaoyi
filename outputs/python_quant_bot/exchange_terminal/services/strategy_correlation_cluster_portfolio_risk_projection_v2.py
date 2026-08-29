from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    SCHEMA_VERSION as ADAPTER_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as ADAPTER_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v2,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-public-projection-v2"
)
PROJECTION_VERIFICATION_SCHEMA_VERSION = f"{PROJECTION_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-portfolio-risk-temporal-lattice-projection-lock-1"


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _number_or_none(value: Any) -> int | float | None:
    return value if type(value) in (int, float) else None


def _int_or_none(value: Any) -> int | None:
    return value if type(value) is int else None


def _bool_or_none(value: Any) -> bool | None:
    return value if type(value) is bool else None


def build_strategy_correlation_cluster_portfolio_risk_projection_v2(
    adapter_v2_document: Any,
    adapter_v1_document: Any,
    temporal_stability_gate: Any,
    *,
    adapter_v1_verification_context: Any,
    temporal_stability_verification_context: Any,
) -> dict[str, Any]:
    supplied = adapter_v2_document is not None
    adapter_verification: dict[str, Any] = {}
    if type(adapter_v2_document) is dict:
        try:
            candidate = verify_strategy_correlation_cluster_portfolio_risk_adapter_v2(
                adapter_v2_document,
                adapter_v1_document,
                temporal_stability_gate,
                adapter_v1_verification_context=adapter_v1_verification_context,
                temporal_stability_verification_context=(
                    temporal_stability_verification_context
                ),
            )
            if type(candidate) is dict:
                adapter_verification = candidate
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            adapter_verification = {}

    exact = bool(
        type(adapter_v2_document) is dict
        and adapter_verification.get("schema_version")
        == ADAPTER_VERIFICATION_SCHEMA_VERSION
        and adapter_verification.get("status") == "PASS"
        and adapter_verification.get("adapter_exactly_verified") is True
        and not _list(adapter_verification.get("blockers"))
    )
    projection_status = (
        "OBSERVED" if exact else ("UNKNOWN" if supplied else "NOT_SUPPLIED")
    )
    source_state = (
        "VERIFIED" if exact else ("UNKNOWN" if supplied else "NOT_SUPPLIED")
    )

    adapter_facts = _dict(adapter_v2_document.get("facts")) if exact else {}
    adapter_portfolio = (
        _dict(adapter_v2_document.get("portfolio")) if exact else {}
    )
    adapter_stability = (
        _dict(adapter_v2_document.get("stability")) if exact else {}
    )
    adapter_status = adapter_v2_document.get("status") if exact else None
    adapter_decision = (
        _text_or_none(adapter_v2_document.get("decision"))
        if exact
        else ("UNKNOWN" if supplied else "NOT_SUPPLIED")
    )
    risk_increasing = _bool_or_none(adapter_facts.get("risk_increasing"))
    base_adapter_passed = _bool_or_none(adapter_facts.get("base_adapter_passed"))
    temporal_required = _bool_or_none(
        adapter_facts.get("temporal_stability_required")
    )
    temporal_passed = _bool_or_none(
        adapter_facts.get("temporal_stability_passed")
    )

    if not exact:
        gap_state = "UNKNOWN" if supplied else "NOT_SUPPLIED"
    elif risk_increasing is False:
        gap_state = "RISK_REDUCTION_PATH"
    elif base_adapter_passed is False:
        gap_state = "PORTFOLIO_RISK_LIMIT_GAP_PRESENT"
    elif temporal_required is True and temporal_passed is False:
        gap_state = "TEMPORAL_STABILITY_GAP_PRESENT"
    elif (
        adapter_status == "PASS"
        and base_adapter_passed is True
        and temporal_required is True
        and temporal_passed is True
    ):
        gap_state = "WITHIN_DECLARED_RESEARCH_LIMITS_AND_TEMPORAL_STABILITY"
    else:
        gap_state = "JOINT_RESEARCH_GAP_PRESENT"

    document: dict[str, Any] = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": projection_status,
        "pipeline": [
            {"stage": "SOURCE", "state": source_state},
            {"stage": "GAP", "state": gap_state},
            {"stage": "MATURITY", "state": "UNMOUNTED_CANDIDATE"},
            {"stage": "PERMISSION", "state": "UNAUTHORIZED"},
        ],
        "source": {
            "adapter_supplied": supplied,
            "adapter_exactly_verified": exact,
            "adapter_schema_version": (
                _text_or_none(adapter_v2_document.get("schema_version"))
                if exact
                else None
            ),
            "adapter_hash": (
                _text_or_none(adapter_v2_document.get("adapter_hash"))
                if exact
                else None
            ),
            "verification_schema_version": (
                ADAPTER_VERIFICATION_SCHEMA_VERSION if exact else None
            ),
        },
        "summary": {
            "adapter_decision": adapter_decision,
            "adapter_status": _text_or_none(adapter_status),
            "risk_increasing": risk_increasing,
            "base_adapter_passed": base_adapter_passed,
            "temporal_stability_required": temporal_required,
            "temporal_stability_passed": temporal_passed,
            "legacy_gross_exposure_pct": _number_or_none(
                adapter_portfolio.get("legacy_gross_exposure_pct")
            ),
            "legacy_net_exposure_pct": _number_or_none(
                adapter_portfolio.get("legacy_net_exposure_pct")
            ),
            "legacy_proposal_centered_cluster_pct": _number_or_none(
                adapter_portfolio.get("legacy_proposal_centered_cluster_pct")
            ),
            "all_cluster_max_gross_exposure_pct": _number_or_none(
                adapter_portfolio.get("all_cluster_max_gross_exposure_pct")
            ),
            "symbol_ticket_count": _int_or_none(
                adapter_portfolio.get("symbol_ticket_count")
            ),
            "effective_independent_bet_count": _int_or_none(
                adapter_portfolio.get("effective_independent_bet_count")
            ),
            "correlated_duplicate_ticket_count": _int_or_none(
                adapter_portfolio.get("correlated_duplicate_ticket_count")
            ),
            "effective_bet_blocker_count": _int_or_none(
                adapter_portfolio.get("effective_bet_blocker_count")
            ),
            "legacy_reject_reason_count": _int_or_none(
                adapter_portfolio.get("legacy_reject_reason_count")
            ),
            "temporal_stability_status": _text_or_none(
                adapter_stability.get("status")
            ),
            "window_result_count": _int_or_none(
                adapter_stability.get("window_result_count")
            ),
            "unstable_window_count": _int_or_none(
                adapter_stability.get("unstable_window_count")
            ),
            "insufficient_sample_window_count": _int_or_none(
                adapter_stability.get("insufficient_sample_window_count")
            ),
            "blocked_window_count": _int_or_none(
                adapter_stability.get("blocked_window_count")
            ),
            "within_cluster_pair_count": _int_or_none(
                adapter_stability.get("within_cluster_pair_count")
            ),
            "pair_window_hypothesis_count": _int_or_none(
                adapter_stability.get("pair_window_hypothesis_count")
            ),
            "first_blocking_tier": _text_or_none(
                adapter_stability.get("first_blocking_tier")
            ),
            "stability_blocker_count": _int_or_none(
                adapter_stability.get("blocker_count")
            ),
            "adapter_blocker_count": (
                len(_list(adapter_v2_document.get("blockers"))) if exact else None
            ),
            "adapter_warning_count": (
                len(_list(adapter_v2_document.get("warnings"))) if exact else None
            ),
        },
        "facts": {
            "source_documents_embedded": False,
            "component_results_embedded": False,
            "raw_correlations_embedded": False,
            "return_series_embedded": False,
            "window_rows_embedded": False,
            "profitability_proof": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_mounted": False,
            "natural_forward_chain_changed": False,
        },
        "authority": {
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "descriptive_only": True,
            "formal_registry_activation_allowed": False,
            "live_order_allowed": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "risk_service_invocation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "projection_hash")


def verify_strategy_correlation_cluster_portfolio_risk_projection_v2(
    document: Any,
    adapter_v2_document: Any,
    adapter_v1_document: Any,
    temporal_stability_gate: Any,
    *,
    adapter_v1_verification_context: Any,
    temporal_stability_verification_context: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_projection_v2(
        adapter_v2_document,
        adapter_v1_document,
        temporal_stability_gate,
        adapter_v1_verification_context=adapter_v1_verification_context,
        temporal_stability_verification_context=(
            temporal_stability_verification_context
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": PROJECTION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["projection_exact_rebuild_mismatch"],
        "projection_status": expected["status"] if exact else "UNKNOWN",
        "projection_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
    }


__all__ = [
    "PROJECTION_SCHEMA_VERSION",
    "PROJECTION_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_projection_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_projection_v2",
]
