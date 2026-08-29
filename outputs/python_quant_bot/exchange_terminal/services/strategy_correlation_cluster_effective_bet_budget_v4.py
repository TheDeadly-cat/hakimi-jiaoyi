"""Verified risk-reduction successor for correlation-cluster budgets."""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v4"
BUDGET_VERIFICATION_SCHEMA_VERSION = f"{BUDGET_SCHEMA_VERSION}-verification-v1"
RISK_REDUCTION_TRANSITION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-risk-reduction-transition-v1"
)
RISK_REDUCTION_VERIFICATION_SCHEMA_VERSION = (
    f"{RISK_REDUCTION_TRANSITION_SCHEMA_VERSION}-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260824-verified-risk-reduction-effective-budget-v4-synthetic-lock-1"
)
V3_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
POSITION_GROSS_RULE = "SUM_ABSOLUTE_NOTIONAL_WITHOUT_DIRECTION_NETTING"
REDUCTION_RULE = (
    "ONE_EXISTING_POSITION_SAME_SIDE_TARGET_REDUCED_BY_OPPOSITE_ORDER_NO_CROSS"
)


class VerifiedRiskReductionBudgetError(ValueError):
    pass


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "automatic_internal_backtest_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _number(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    clean = float(value)
    if not math.isfinite(clean):
        return None
    if positive and clean <= 0.0:
        return None
    if not positive and clean < 0.0:
        return None
    return round(clean, 8)


def _symbol(value: Any) -> str:
    return value.strip().upper() if type(value) is str else ""


def _direction(value: Any) -> str:
    clean = value.strip().upper() if type(value) is str else ""
    return clean if clean in {"LONG", "SHORT"} else ""


def _normalize_positions(value: Any, label: str) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise VerifiedRiskReductionBudgetError(f"{label} must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in value:
        if (
            type(row) is not dict
            or set(row) != {"symbol", "notional", "direction"}
        ):
            raise VerifiedRiskReductionBudgetError(
                f"{label} position schema is not exact"
            )
        symbol = _symbol(row["symbol"])
        direction = _direction(row["direction"])
        notional = _number(row["notional"], positive=True)
        if not symbol or not direction or notional is None:
            raise VerifiedRiskReductionBudgetError(
                f"{label} position is invalid"
            )
        if symbol in seen:
            raise VerifiedRiskReductionBudgetError(
                f"{label} contains duplicate symbols"
            )
        seen.add(symbol)
        normalized.append(
            {
                "symbol": symbol,
                "notional": notional,
                "direction": direction,
            }
        )
    return sorted(normalized, key=lambda row: row["symbol"])


def build_strategy_correlation_cluster_risk_reduction_transition_v1(
    positions_before: Any,
    positions_after: Any,
    *,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
) -> dict[str, Any]:
    before = _normalize_positions(positions_before, "positions_before")
    after = _normalize_positions(positions_after, "positions_after")
    symbol = _symbol(proposed_symbol)
    amount = _number(proposed_notional, positive=True)
    order_direction = _direction(proposed_direction)
    if not symbol or amount is None or not order_direction:
        raise VerifiedRiskReductionBudgetError(
            "risk-reduction proposal is invalid"
        )
    before_by_symbol = {row["symbol"]: row for row in before}
    target = before_by_symbol.get(symbol)
    if target is None:
        raise VerifiedRiskReductionBudgetError(
            "risk reduction must target an existing position"
        )
    expected_order_direction = (
        "SHORT" if target["direction"] == "LONG" else "LONG"
    )
    if order_direction != expected_order_direction:
        raise VerifiedRiskReductionBudgetError(
            "risk reduction order must oppose the existing position"
        )
    if amount > target["notional"] + 1e-8:
        raise VerifiedRiskReductionBudgetError(
            "risk reduction cannot cross or reverse the position"
        )

    remaining = round(target["notional"] - amount, 8)
    expected_after = {
        row["symbol"]: {
            "symbol": row["symbol"],
            "notional": row["notional"],
            "direction": row["direction"],
        }
        for row in before
    }
    if remaining <= 1e-8:
        expected_after.pop(symbol)
        remaining = 0.0
    else:
        expected_after[symbol]["notional"] = remaining
    normalized_expected_after = sorted(
        expected_after.values(), key=lambda row: row["symbol"]
    )
    if after != normalized_expected_after:
        raise VerifiedRiskReductionBudgetError(
            "positions_after is not the exact single-position reduction"
        )

    gross_before = round(sum(row["notional"] for row in before), 8)
    gross_after = round(sum(row["notional"] for row in after), 8)
    gross_reduction = round(gross_before - gross_after, 8)
    if (
        gross_before <= 0.0
        or gross_after < 0.0
        or gross_after >= gross_before
        or abs(gross_reduction - amount) > 1e-8
    ):
        raise VerifiedRiskReductionBudgetError(
            "portfolio gross notional did not decrease exactly"
        )

    document = {
        "schema_version": RISK_REDUCTION_TRANSITION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "decision": "VERIFIED_SINGLE_POSITION_GROSS_RISK_REDUCTION",
        "source": {
            "positions_before_hash": strict_canonical_hash(before),
            "positions_after_hash": strict_canonical_hash(after),
            "proposal_hash": strict_canonical_hash(
                {
                    "proposed_symbol": symbol,
                    "proposed_notional": amount,
                    "proposed_direction": order_direction,
                }
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        "transition": {
            "target_symbol": symbol,
            "position_direction": target["direction"],
            "order_direction": order_direction,
            "position_notional_before": target["notional"],
            "position_notional_after": remaining,
            "reduction_notional": amount,
            "portfolio_gross_before": gross_before,
            "portfolio_gross_after": gross_after,
            "portfolio_gross_reduction": gross_reduction,
        },
        "facts": {
            "existing_position_targeted": True,
            "opposite_order_direction_verified": True,
            "single_position_changed": True,
            "position_direction_preserved": True,
            "position_cross_or_reversal_allowed": False,
            "portfolio_gross_strictly_reduced": True,
            "direction_netting_used": False,
            "correlation_sources_required": False,
            "position_snapshot_provenance_verified": False,
            "execution_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
        },
        "policy": {
            "position_gross_rule": POSITION_GROSS_RULE,
            "reduction_rule": REDUCTION_RULE,
            "caller_risk_reduction_flag_sufficient": False,
        },
        "authority": _authority(),
        "blockers": [
            "POSITION_SNAPSHOT_PROVENANCE_UNVERIFIED",
            "EXECUTION_UNVERIFIED",
            "CURRENT_ACTIVATION_UNAUTHORIZED",
        ],
    }
    return seal_strict_canonical_document(document, "transition_hash")


def verify_strategy_correlation_cluster_risk_reduction_transition_v1(
    document: Any,
    positions_before: Any,
    positions_after: Any,
    *,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
) -> dict[str, Any]:
    try:
        expected = (
            build_strategy_correlation_cluster_risk_reduction_transition_v1(
                positions_before,
                positions_after,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
            )
        )
        exact = strict_json_contract_equal(document, expected)
    except (TypeError, ValueError):
        exact = False
        expected = None
    return {
        "schema_version": RISK_REDUCTION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "transition_status": expected["status"] if exact else "UNKNOWN",
        "transition_hash": expected["transition_hash"] if exact else None,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


def _call_v3(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    strata_registration: Any,
    strata_gate: Any,
    complete_link_gate: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
    max_cluster_gross_pct: Any,
    risk_increasing: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        document = (
            budget_v3.evaluate_strategy_correlation_cluster_effective_bet_budget_v3(
                preregistration,
                correlation_matrix,
                complete_link_audit,
                strata_registration=strata_registration,
                strata_gate=strata_gate,
                complete_link_gate=complete_link_gate,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
        )
        receipt = (
            budget_v3.verify_strategy_correlation_cluster_effective_bet_budget_v3(
                document,
                preregistration,
                correlation_matrix,
                complete_link_audit,
                strata_registration=strata_registration,
                strata_gate=strata_gate,
                complete_link_gate=complete_link_gate,
                equity=equity,
                positions=positions,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
            )
        )
    except (KeyError, TypeError, ValueError):
        return {}, {}
    return (
        document if type(document) is dict else {},
        receipt if type(receipt) is dict else {},
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v3.budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
    positions_after: Any = None,
    risk_reduction_transition: Any = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    risk_flag_exact = type(risk_increasing) is bool
    clean_risk_flag = risk_increasing if risk_flag_exact else True
    if not risk_flag_exact:
        blockers.append("risk_increasing_type_invalid")

    v3_document, v3_receipt = _call_v3(
        preregistration,
        correlation_matrix,
        complete_link_audit,
        strata_registration=strata_registration,
        strata_gate=strata_gate,
        complete_link_gate=complete_link_gate,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        max_cluster_gross_pct=max_cluster_gross_pct,
        risk_increasing=clean_risk_flag,
    )
    v3_exact = bool(
        v3_receipt.get("status") == "PASS"
        and type(v3_document.get("budget_v3_hash")) is str
    )
    v3_status = v3_document.get("status") if v3_exact else "UNKNOWN"
    v3_decision = v3_document.get("decision") if v3_exact else "UNKNOWN"
    v3_hash = v3_document.get("budget_v3_hash") if v3_exact else None
    if not v3_exact:
        blockers.append("effective_budget_v3_exact_verification")
    elif v3_status != "PASS":
        blockers.append("effective_budget_v3_decision")

    transition_exact = False
    transition_hash = None
    transition_summary: dict[str, Any] = {}
    if clean_risk_flag is False:
        if positions_after is None or risk_reduction_transition is None:
            blockers.append("verified_risk_reduction_transition_missing")
        else:
            try:
                expected_transition = (
                    build_strategy_correlation_cluster_risk_reduction_transition_v1(
                        positions,
                        positions_after,
                        proposed_symbol=proposed_symbol,
                        proposed_notional=proposed_notional,
                        proposed_direction=proposed_direction,
                    )
                )
                receipt = (
                    verify_strategy_correlation_cluster_risk_reduction_transition_v1(
                        risk_reduction_transition,
                        positions,
                        positions_after,
                        proposed_symbol=proposed_symbol,
                        proposed_notional=proposed_notional,
                        proposed_direction=proposed_direction,
                    )
                )
                transition_exact = bool(
                    receipt.get("status") == "PASS"
                    and risk_reduction_transition == expected_transition
                )
                if transition_exact:
                    transition_hash = expected_transition["transition_hash"]
                    transition_summary = expected_transition["transition"]
            except (KeyError, TypeError, ValueError):
                transition_exact = False
            if not transition_exact:
                blockers.append("verified_risk_reduction_transition_invalid")
        if v3_decision != "RISK_REDUCTION_PATH":
            blockers.append("effective_budget_v3_risk_reduction_path")
    elif positions_after is not None or risk_reduction_transition is not None:
        blockers.append("unexpected_risk_reduction_transition")

    blockers = sorted(set(blockers))
    status = "PASS" if not blockers else "BLOCK"
    verified_reduction = bool(
        status == "PASS" and clean_risk_flag is False and transition_exact
    )
    verified_increase = bool(
        status == "PASS" and clean_risk_flag is True
    )
    return seal_strict_canonical_document(
        {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": status,
            "decision": (
                "PASS_VERIFIED_RISK_REDUCTION_TRANSITION"
                if verified_reduction
                else "PASS_VERIFIED_RISK_INCREASING_BUDGET"
                if verified_increase
                else "BLOCK"
            ),
            "source": {
                "v3_budget_hash": v3_hash,
                "v3_implementation_sha256": V3_IMPLEMENTATION_SHA256,
                "v3_status": v3_status,
                "v3_decision": v3_decision,
                "risk_reduction_transition_hash": transition_hash,
                "precomputed_predecessor_result_accepted": False,
                "strict_canonical_implementation_sha256": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
            },
            "checks": {
                "risk_flag_type_exact": risk_flag_exact,
                "v3_exactly_rebuilt": v3_exact,
                "v3_decision_pass": v3_status == "PASS",
                "verified_risk_reduction_transition": (
                    transition_exact if clean_risk_flag is False else None
                ),
                "caller_flag_only_bypass_rejected": True,
                "unexpected_transition_absent": (
                    positions_after is None
                    and risk_reduction_transition is None
                    if clean_risk_flag is True
                    else None
                ),
            },
            "transition_summary": {
                "target_symbol": transition_summary.get("target_symbol"),
                "position_direction": transition_summary.get(
                    "position_direction"
                ),
                "order_direction": transition_summary.get(
                    "order_direction"
                ),
                "position_notional_before": transition_summary.get(
                    "position_notional_before"
                ),
                "position_notional_after": transition_summary.get(
                    "position_notional_after"
                ),
                "reduction_notional": transition_summary.get(
                    "reduction_notional"
                ),
                "portfolio_gross_before": transition_summary.get(
                    "portfolio_gross_before"
                ),
                "portfolio_gross_after": transition_summary.get(
                    "portfolio_gross_after"
                ),
                "portfolio_gross_reduction": transition_summary.get(
                    "portfolio_gross_reduction"
                ),
            },
            "facts": {
                "risk_increasing": risk_increasing if risk_flag_exact else None,
                "caller_risk_reduction_flag_sufficient": False,
                "risk_reduction_derived_from_position_transition": (
                    verified_reduction
                ),
                "single_position_reduction_verified": verified_reduction,
                "portfolio_gross_notional_reduced": verified_reduction,
                "risk_increasing_v3_decision_preserved": verified_increase,
                "direction_netting_used": False,
                "source_documents_embedded": False,
                "position_rows_embedded": False,
                "profitability_proven": False,
                "position_snapshot_provenance_verified": False,
                "execution_verified": False,
                "runtime_assets_accessed": False,
                "runtime_gate_integrated": False,
            },
            "policy": {
                "position_gross_rule": POSITION_GROSS_RULE,
                "risk_reduction_rule": REDUCTION_RULE,
                "verified_transition_required_for_risk_reduction": True,
                "caller_risk_reduction_flag_sufficient": False,
                "cross_zero_or_reversal_allowed": False,
                "other_position_changes_allowed": False,
            },
            "blockers": blockers,
            "authority": _authority(),
        },
        "budget_v4_hash",
    )


def verify_strategy_correlation_cluster_effective_bet_budget_v4(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        expected = (
            evaluate_strategy_correlation_cluster_effective_bet_budget_v4(
                *args, **kwargs
            )
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        exact = False
        expected = None
    return {
        "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "budget_decision": expected["decision"] if exact else "UNKNOWN",
        "budget_v4_hash": expected["budget_v4_hash"] if exact else None,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "BUDGET_VERIFICATION_SCHEMA_VERSION",
    "RISK_REDUCTION_TRANSITION_SCHEMA_VERSION",
    "RISK_REDUCTION_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VerifiedRiskReductionBudgetError",
    "build_strategy_correlation_cluster_risk_reduction_transition_v1",
    "evaluate_strategy_correlation_cluster_effective_bet_budget_v4",
    "verify_strategy_correlation_cluster_effective_bet_budget_v4",
    "verify_strategy_correlation_cluster_risk_reduction_transition_v1",
]
