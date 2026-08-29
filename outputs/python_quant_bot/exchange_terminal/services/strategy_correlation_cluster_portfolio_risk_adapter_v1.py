from __future__ import annotations

import math
from typing import Any

from .portfolio_risk import (
    DEFAULT_LIMITS,
    PORTFOLIO_RISK_SCHEMA_VERSION,
    evaluate_portfolio_risk,
)
from .strategy_correlation_cluster_effective_bet_budget import (
    BUDGET_SCHEMA_VERSION,
    BUDGET_VERIFICATION_SCHEMA_VERSION,
    evaluate_strategy_correlation_cluster_effective_bet_budget,
    verify_strategy_correlation_cluster_effective_bet_budget,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


ADAPTER_SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v1"
ADAPTER_VERIFICATION_SCHEMA_VERSION = f"{ADAPTER_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-portfolio-risk-dual-gate-adapter-lock-1"

_FLOAT_LIMIT_KEYS = frozenset(
    {
        "max_single_position_pct",
        "max_gross_exposure_pct",
        "max_net_exposure_pct",
        "max_correlated_cluster_pct",
        "max_named_cluster_pct",
        "correlation_threshold",
    }
)
_AUTHORITY_FALSE_KEYS = (
    "current_admission_allowed",
    "current_pointer_written",
    "formal_registry_activation_allowed",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "writer_allowed",
)


def _is_finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _strict_legacy_limits(value: Any) -> bool:
    if value is None:
        return True
    if type(value) is not dict or not set(value).issubset(DEFAULT_LIMITS):
        return False
    for key, raw in value.items():
        if key == "max_positions":
            if type(raw) is not int or raw <= 0:
                return False
            continue
        if key == "require_correlation_for_new_symbol":
            if type(raw) is not bool:
                return False
            continue
        if key not in _FLOAT_LIMIT_KEYS or not _is_finite_number(raw):
            return False
        numeric = float(raw)
        if key == "correlation_threshold":
            if numeric < 0.0 or numeric > 1.0:
                return False
        elif numeric <= 0.0 or numeric > 100.0:
            return False
    return True


def _strict_adapter_input_contract(
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
    proposed_cluster: Any,
    risk_increasing: Any,
    legacy_correlations: Any,
    regime: Any,
    legacy_limits: Any,
    max_cluster_gross_pct: Any,
) -> bool:
    if type(risk_increasing) is not bool:
        return False
    if risk_increasing is False:
        return True
    return bool(
        _is_finite_number(equity)
        and float(equity) > 0.0
        and type(positions) is list
        and all(type(item) is dict for item in positions)
        and type(proposed_symbol) is str
        and proposed_symbol.strip()
        and _is_finite_number(proposed_notional)
        and float(proposed_notional) > 0.0
        and type(proposed_direction) is str
        and proposed_direction.strip().upper() in {"LONG", "SHORT"}
        and type(proposed_cluster) is str
        and (legacy_correlations is None or type(legacy_correlations) is dict)
        and (regime is None or type(regime) is dict)
        and _strict_legacy_limits(legacy_limits)
        and _is_finite_number(max_cluster_gross_pct)
        and 0.0 < float(max_cluster_gross_pct) <= 100.0
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _number_or_none(value: Any) -> int | float | None:
    return value if _is_finite_number(value) else None


def _int_or_none(value: Any) -> int | None:
    return value if type(value) is int else None


def _component_authority_locked(
    legacy_result: dict[str, Any],
    budget_result: dict[str, Any],
) -> bool:
    budget_authority = _dict(budget_result.get("authority"))
    return bool(
        legacy_result.get("paper_authorized") is False
        and legacy_result.get("live_order_allowed") is False
        and budget_authority.get("descriptive_only") is True
        and all(budget_authority.get(key) is False for key in _AUTHORITY_FALSE_KEYS if key in budget_authority)
        and budget_authority.get("current_admission_allowed") is False
        and budget_authority.get("live_order_allowed") is False
        and budget_authority.get("paper_authorized") is False
        and budget_authority.get("runtime_gate_activation_allowed") is False
        and budget_authority.get("writer_allowed") is False
    )


def _limits_aligned(
    legacy_result: dict[str, Any],
    max_cluster_gross_pct: Any,
    *,
    risk_increasing: bool,
) -> bool:
    if risk_increasing is False:
        return True
    legacy_limit = _dict(legacy_result.get("limits")).get("max_correlated_cluster_pct")
    return bool(
        _is_finite_number(legacy_limit)
        and _is_finite_number(max_cluster_gross_pct)
        and float(legacy_limit) == float(max_cluster_gross_pct)
    )


def _check(name: str, ok: bool, pass_message: str, block_message: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "blocking": True,
        "message": pass_message if ok else block_message,
    }


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
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
    input_contract_ok = _strict_adapter_input_contract(
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

    legacy_result: dict[str, Any] = {}
    budget_result: dict[str, Any] = {}
    budget_verification: dict[str, Any] = {}
    if input_contract_ok:
        try:
            candidate_legacy = evaluate_portfolio_risk(
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                proposed_cluster=proposed_cluster,
                risk_increasing=risk_increasing,
                correlations=legacy_correlations,
                regime=regime,
                limits=legacy_limits,
            )
            if type(candidate_legacy) is dict:
                legacy_result = candidate_legacy
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            legacy_result = {}

        try:
            candidate_budget = evaluate_strategy_correlation_cluster_effective_bet_budget(
                preregistration,
                cluster_correlation_matrix,
                complete_link_audit,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
            if type(candidate_budget) is dict:
                budget_result = candidate_budget
                candidate_verification = verify_strategy_correlation_cluster_effective_bet_budget(
                    candidate_budget,
                    preregistration,
                    cluster_correlation_matrix,
                    complete_link_audit,
                    equity=equity,
                    positions=positions,
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                    risk_increasing=risk_increasing,
                )
                if type(candidate_verification) is dict:
                    budget_verification = candidate_verification
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
            budget_result = {}
            budget_verification = {}

    legacy_gate_ok = bool(
        legacy_result.get("schema_version") == PORTFOLIO_RISK_SCHEMA_VERSION
        and legacy_result.get("status") == "PASS"
        and legacy_result.get("portfolio_gate_passed") is True
    )
    budget_exact_ok = bool(
        budget_verification.get("schema_version") == BUDGET_VERIFICATION_SCHEMA_VERSION
        and budget_verification.get("status") == "PASS"
        and not _list(budget_verification.get("blockers"))
    )
    expected_budget_decision = (
        "RISK_REDUCTION_PATH"
        if risk_increasing is False
        else "PASS_RESEARCH_BUDGET"
    )
    budget_gate_ok = bool(
        budget_result.get("schema_version") == BUDGET_SCHEMA_VERSION
        and budget_result.get("status") == "PASS"
        and budget_result.get("decision") == expected_budget_decision
        and not _list(budget_result.get("blockers"))
    )
    limit_alignment_ok = _limits_aligned(
        legacy_result,
        max_cluster_gross_pct,
        risk_increasing=risk_increasing if type(risk_increasing) is bool else True,
    )
    authority_lock_ok = _component_authority_locked(legacy_result, budget_result)

    checks = [
        _check(
            "adapter_input_contract",
            input_contract_ok,
            "Shared portfolio inputs use strict native types.",
            "Shared portfolio inputs are invalid or ambiguous.",
        ),
        _check(
            "legacy_portfolio_risk_gate",
            legacy_gate_ok,
            "Legacy portfolio limits pass on rebuilt inputs.",
            "Legacy portfolio limits block or cannot be rebuilt.",
        ),
        _check(
            "effective_bet_budget_exact_verification",
            budget_exact_ok,
            "Effective-bet budget matches an exact rebuild.",
            "Effective-bet budget cannot be verified by exact rebuild.",
        ),
        _check(
            "all_cluster_effective_bet_gate",
            budget_gate_ok,
            "All verified active clusters are within research budget.",
            "At least one active cluster blocks or source evidence is unavailable.",
        ),
        _check(
            "correlated_cluster_limit_alignment",
            limit_alignment_ok,
            "Legacy and all-cluster gross limits are aligned.",
            "Legacy and all-cluster gross limits differ.",
        ),
        _check(
            "component_authority_lock",
            authority_lock_ok,
            "Both component results remain research-only.",
            "A component authority lock is missing or invalid.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"

    legacy_exposure = _dict(legacy_result.get("exposure_after"))
    budget_portfolio = _dict(budget_result.get("portfolio"))
    cluster_exposures = _list(budget_result.get("cluster_exposures"))
    cluster_gross_values = [
        float(value)
        for item in cluster_exposures
        if type(item) is dict
        for value in [item.get("gross_exposure_pct")]
        if _is_finite_number(value)
    ]

    document: dict[str, Any] = {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "WITHIN_RESEARCH_RISK_BUDGET"
            if status == "PASS"
            else "BLOCKED_RESEARCH_RISK_BUDGET"
        ),
        "source": {
            "legacy_portfolio_schema_version": _text_or_none(
                legacy_result.get("schema_version")
            ),
            "legacy_check_hash": _text_or_none(legacy_result.get("check_hash")),
            "legacy_result_rebuilt": bool(legacy_result),
            "effective_bet_schema_version": _text_or_none(
                budget_result.get("schema_version")
            ),
            "effective_bet_budget_hash": _text_or_none(
                budget_result.get("budget_hash")
            ),
            "effective_bet_exactly_verified": budget_exact_ok,
            "dual_correlation_source_formats_required": True,
        },
        "checks": checks,
        "blockers": blockers,
        "portfolio": {
            "legacy_gross_exposure_pct": _number_or_none(
                legacy_exposure.get("gross_exposure_pct")
            ),
            "legacy_net_exposure_pct": _number_or_none(
                legacy_exposure.get("net_exposure_pct")
            ),
            "legacy_proposal_centered_cluster_pct": _number_or_none(
                legacy_exposure.get("correlated_cluster_pct")
            ),
            "all_cluster_max_gross_exposure_pct": (
                max(cluster_gross_values) if cluster_gross_values else None
            ),
            "symbol_ticket_count": _int_or_none(
                budget_portfolio.get("symbol_ticket_count")
            ),
            "effective_independent_bet_count": _int_or_none(
                budget_portfolio.get("effective_independent_bet_count")
            ),
            "correlated_duplicate_ticket_count": _int_or_none(
                budget_portfolio.get("correlated_duplicate_ticket_count")
            ),
            "legacy_reject_reason_count": len(
                _list(legacy_result.get("reject_reasons"))
            ),
            "effective_bet_blocker_count": len(
                _list(budget_result.get("blockers"))
            ),
        },
        "facts": {
            "risk_increasing": risk_increasing if type(risk_increasing) is bool else None,
            "legacy_gate_passed": legacy_gate_ok,
            "effective_bet_gate_passed": budget_gate_ok,
            "cluster_limit_aligned": limit_alignment_ok,
            "component_decisions_jointly_required": True,
            "precomputed_component_results_accepted": False,
            "component_results_embedded": False,
            "source_documents_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
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
    return seal_strict_canonical_document(document, "adapter_hash")


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v1(
    document: Any,
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
    expected = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1(
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
        "schema_version": ADAPTER_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["adapter_exact_rebuild_mismatch"],
        "adapter_decision": expected["decision"] if exact else "UNKNOWN",
        "adapter_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
    }


__all__ = [
    "ADAPTER_SCHEMA_VERSION",
    "ADAPTER_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v1",
]
