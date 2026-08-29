from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_portfolio_risk_adapter_v1 import (
    ADAPTER_SCHEMA_VERSION,
    ADAPTER_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-public-projection-v1"
)
PROJECTION_VERIFICATION_SCHEMA_VERSION = f"{PROJECTION_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-portfolio-risk-geometry-projection-lock-1"


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


def build_strategy_correlation_cluster_portfolio_risk_projection_v1(
    adapter_document: Any,
    preregistration: Any,
    cluster_correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    proposed_cluster: Any = "",
    risk_increasing: Any = True,
    legacy_correlations: Any = None,
    regime: Any = None,
    legacy_limits: Any = None,
    max_cluster_gross_pct: Any = 45.0,
) -> dict[str, Any]:
    supplied = adapter_document is not None
    adapter_verification: dict[str, Any] = {}
    if type(adapter_document) is dict:
        try:
            candidate = (
                verify_strategy_correlation_cluster_portfolio_risk_adapter_v1(
                    adapter_document,
                    preregistration,
                    cluster_correlation_matrix,
                    complete_link_audit,
                    equity=equity,
                    positions=positions,
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    proposed_cluster=proposed_cluster,
                    risk_increasing=risk_increasing,
                    legacy_correlations=legacy_correlations,
                    regime=regime,
                    legacy_limits=legacy_limits,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                )
            )
            if type(candidate) is dict:
                adapter_verification = candidate
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            adapter_verification = {}

    exact = bool(
        type(adapter_document) is dict
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

    adapter_facts = _dict(adapter_document.get("facts")) if exact else {}
    adapter_portfolio = _dict(adapter_document.get("portfolio")) if exact else {}
    adapter_status = adapter_document.get("status") if exact else None
    risk_flag = _bool_or_none(adapter_facts.get("risk_increasing"))
    if not exact:
        gap_state = "UNKNOWN" if supplied else "NOT_SUPPLIED"
    elif risk_flag is False:
        gap_state = "RISK_REDUCTION_PATH"
    elif adapter_status == "PASS":
        gap_state = "WITHIN_DECLARED_RESEARCH_LIMITS"
    else:
        gap_state = "RESEARCH_LIMIT_GAP_PRESENT"

    if exact:
        adapter_decision = _text_or_none(adapter_document.get("decision"))
    else:
        adapter_decision = "UNKNOWN" if supplied else "NOT_SUPPLIED"

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
                _text_or_none(adapter_document.get("schema_version"))
                if exact
                else None
            ),
            "adapter_hash": (
                _text_or_none(adapter_document.get("adapter_hash"))
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
            "risk_increasing": risk_flag,
            "legacy_gate_passed": _bool_or_none(
                adapter_facts.get("legacy_gate_passed")
            ),
            "effective_bet_gate_passed": _bool_or_none(
                adapter_facts.get("effective_bet_gate_passed")
            ),
            "cluster_limit_aligned": _bool_or_none(
                adapter_facts.get("cluster_limit_aligned")
            ),
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
            "blocker_count": (
                len(_list(adapter_document.get("blockers"))) if exact else None
            ),
        },
        "facts": {
            "source_documents_embedded": False,
            "component_results_embedded": False,
            "raw_correlations_embedded": False,
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
            "runtime_gate_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "projection_hash")


def verify_strategy_correlation_cluster_portfolio_risk_projection_v1(
    document: Any,
    adapter_document: Any,
    preregistration: Any,
    cluster_correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    proposed_cluster: Any = "",
    risk_increasing: Any = True,
    legacy_correlations: Any = None,
    regime: Any = None,
    legacy_limits: Any = None,
    max_cluster_gross_pct: Any = 45.0,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_projection_v1(
        adapter_document,
        preregistration,
        cluster_correlation_matrix,
        complete_link_audit,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        proposed_cluster=proposed_cluster,
        risk_increasing=risk_increasing,
        legacy_correlations=legacy_correlations,
        regime=regime,
        legacy_limits=legacy_limits,
        max_cluster_gross_pct=max_cluster_gross_pct,
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
    "build_strategy_correlation_cluster_portfolio_risk_projection_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_projection_v1",
]
