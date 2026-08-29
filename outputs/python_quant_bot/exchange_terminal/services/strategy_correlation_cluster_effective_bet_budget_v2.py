"""Weight-aware shadow successor for the correlation-cluster budget v1.

V1 counts each active cluster as one independent bet regardless of its weight.
V2 preserves every v1 blocker and adds an inverse-HHI diversification gate when
total active gross exceeds the per-cluster gross limit.  It remains unmounted,
research-only, and cannot grant paper or live authority.
"""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget as budget_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v2"
BUDGET_VERIFICATION_SCHEMA_VERSION = f"{BUDGET_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-weighted-effective-cluster-budget-v2-lock-1"
V1_IMPLEMENTATION_SHA256 = (
    "b3a1fc720f9a54776279431abaef23155b6ab313868603e3a061919f698669b8"
)
MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT = 1.5
DIVERSIFICATION_TRIGGER_RULE = "TOTAL_GROSS_EXCEEDS_CLUSTER_GROSS_LIMIT"
WEIGHTING_RULE = "INVERSE_HERFINDAHL_ON_CLUSTER_GROSS_NOTIONAL"

_EVALUATE_V1 = budget_v1.evaluate_strategy_correlation_cluster_effective_bet_budget
_VERIFY_V1 = budget_v1.verify_strategy_correlation_cluster_effective_bet_budget


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _is_number(value: Any, *, positive: bool = False) -> bool:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        return False
    return not positive or float(value) > 0.0


def _hash_or_none(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    ):
        return value
    return None


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return bool(
        type(authority) is dict
        and authority
        and all(type(key) is str and type(value) is bool for key, value in authority.items())
        and authority.get("descriptive_only") is True
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _v1_receipt_passed(receipt: Any) -> bool:
    return bool(
        type(receipt) is dict
        and receipt.get("schema_version")
        == budget_v1.BUDGET_VERIFICATION_SCHEMA_VERSION
        and receipt.get("status") == "PASS"
        and receipt.get("blockers") == []
        and receipt.get("budget_decision")
        in {"PASS_RESEARCH_BUDGET", "RISK_REDUCTION_PATH", "BLOCK"}
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _call_v1(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any,
    max_cluster_gross_pct: Any,
    risk_increasing: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        candidate = _EVALUATE_V1(
            preregistration,
            correlation_matrix,
            complete_link_audit,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
        if type(candidate) is not dict:
            return {}, {}
        receipt = _VERIFY_V1(
            candidate,
            preregistration,
            correlation_matrix,
            complete_link_audit,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return {}, {}
    return candidate, receipt if type(receipt) is dict else {}


def _v1_presentable(document: Any, receipt: Any) -> bool:
    facts = document.get("facts") if type(document) is dict else None
    return bool(
        _v1_receipt_passed(receipt)
        and document.get("schema_version") == budget_v1.BUDGET_SCHEMA_VERSION
        and document.get("static_fingerprint") == budget_v1.STATIC_FINGERPRINT
        and document.get("status") in {"PASS", "BLOCK"}
        and document.get("decision")
        in {"PASS_RESEARCH_BUDGET", "RISK_REDUCTION_PATH", "BLOCK"}
        and _hash_or_none(document.get("budget_hash")) is not None
        and type(document.get("portfolio")) is dict
        and type(document.get("cluster_exposures")) is list
        and type(facts) is dict
        and type(facts.get("risk_increasing")) is bool
        and _authority_locked(document)
    )


def _derive_weighted_metrics(
    document: dict[str, Any], *, equity: Any
) -> dict[str, Any] | None:
    if not _is_number(equity, positive=True):
        return None
    exposures = document.get("cluster_exposures")
    if type(exposures) is not list or not exposures:
        return None
    expected_keys = {
        "cluster_id",
        "symbols",
        "symbol_ticket_count",
        "gross_notional",
        "gross_exposure_pct",
        "limit_pct",
        "status",
    }
    parsed: list[tuple[str, float, float]] = []
    seen: set[str] = set()
    common_limit: float | None = None
    denominator = float(equity)
    for raw in exposures:
        if type(raw) is not dict or set(raw) != expected_keys:
            return None
        cluster_id = raw.get("cluster_id")
        symbols = raw.get("symbols")
        ticket_count = raw.get("symbol_ticket_count")
        gross_notional = raw.get("gross_notional")
        gross_pct = raw.get("gross_exposure_pct")
        limit_pct = raw.get("limit_pct")
        status = raw.get("status")
        if (
            type(cluster_id) is not str
            or not cluster_id
            or cluster_id in seen
            or type(symbols) is not list
            or not symbols
            or not all(type(symbol) is str and symbol for symbol in symbols)
            or len(set(symbols)) != len(symbols)
            or type(ticket_count) is not int
            or ticket_count != len(symbols)
            or not _is_number(gross_notional, positive=True)
            or not _is_number(gross_pct, positive=True)
            or not _is_number(limit_pct)
            or not 0.0 <= float(limit_pct) <= 100.0
            or status not in {"PASS", "BLOCK"}
        ):
            return None
        gross = float(gross_notional)
        exposure_pct = float(gross_pct)
        limit = float(limit_pct)
        if round(gross / denominator * 100.0, 4) != exposure_pct:
            return None
        expected_status = "PASS" if exposure_pct <= limit + 1e-9 else "BLOCK"
        if status != expected_status:
            return None
        if common_limit is None:
            common_limit = limit
        elif common_limit != limit:
            return None
        seen.add(cluster_id)
        parsed.append((cluster_id, gross, exposure_pct))

    parsed.sort(key=lambda item: item[0])
    total_gross = sum(item[1] for item in parsed)
    squared_gross = sum(item[1] ** 2 for item in parsed)
    if total_gross <= 0.0 or squared_gross <= 0.0 or common_limit is None:
        return None
    weighted_effective_count = total_gross**2 / squared_gross
    maximum_gross = max(item[1] for item in parsed)
    dominant_cluster_id = min(
        item[0] for item in parsed if item[1] == maximum_gross
    )
    total_gross_pct = total_gross / denominator * 100.0
    gate_applied = total_gross_pct > common_limit + 1e-9
    gate_passed = bool(
        not gate_applied
        or weighted_effective_count + 1e-12
        >= MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT
    )
    return {
        "active_cluster_count": len(parsed),
        "total_active_gross_pct": round(total_gross_pct, 4),
        "weighted_effective_cluster_count": round(weighted_effective_count, 6),
        "dominant_cluster_id": dominant_cluster_id,
        "dominant_cluster_share_of_active_gross_pct": round(
            maximum_gross / total_gross * 100.0, 4
        ),
        "diversification_trigger_gross_pct": round(common_limit, 4),
        "weighted_diversification_gate_applied": gate_applied,
        "weighted_diversification_gate_passed": gate_passed,
    }


def _check(name: str, ok: bool, pass_message: str, block_message: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "blocking": True,
        "message": pass_message if ok else block_message,
    }


def evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    v1_document, v1_receipt = _call_v1(
        preregistration,
        correlation_matrix,
        complete_link_audit,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        max_cluster_gross_pct=max_cluster_gross_pct,
        risk_increasing=risk_increasing,
    )
    v1_exact = _v1_presentable(v1_document, v1_receipt)
    v1_status = v1_document.get("status") if v1_exact else "UNKNOWN"
    v1_decision = v1_document.get("decision") if v1_exact else "UNKNOWN"
    facts = v1_document.get("facts") if v1_exact else {}
    risk_reduction = bool(
        v1_exact
        and v1_status == "PASS"
        and v1_decision == "RISK_REDUCTION_PATH"
        and type(facts) is dict
        and facts.get("risk_increasing") is False
    )
    metrics = (
        None
        if risk_reduction or not v1_exact
        else _derive_weighted_metrics(v1_document, equity=equity)
    )
    metrics_ok = risk_reduction or metrics is not None
    weighted_gate_applied = bool(
        metrics is not None and metrics["weighted_diversification_gate_applied"]
    )
    weighted_gate_ok = bool(
        risk_reduction
        or (
            metrics is not None
            and metrics["weighted_diversification_gate_passed"] is True
        )
    )
    v1_gate_ok = bool(v1_exact and v1_status == "PASS")
    authority_ok = bool(v1_exact and _authority_locked(v1_document))
    checks = [
        _check(
            "v1_exact_public_verification",
            v1_exact,
            "The v1 budget matches its public exact verifier.",
            "The v1 budget is unavailable or cannot be exactly verified.",
        ),
        _check(
            "v1_budget_gate",
            v1_gate_ok,
            "Every v1 cluster-gross and source gate passes.",
            "The v1 budget blocks or is unknown.",
        ),
        _check(
            "weighted_cluster_metrics",
            metrics_ok,
            "Weight-aware cluster metrics are exactly derived or not applicable.",
            "Weight-aware cluster metrics cannot be exactly derived.",
        ),
        _check(
            "weighted_effective_cluster_gate",
            weighted_gate_ok,
            "Gross-weighted cluster diversification is sufficient or not applicable.",
            "Active gross is concentrated despite multiple cluster labels.",
        ),
        _check(
            "component_authority_lock",
            authority_ok,
            "The source budget remains research-only.",
            "The source authority lock is missing or invalid.",
        ),
    ]
    blockers = [check["name"] for check in checks if check["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"
    portfolio_v1 = v1_document.get("portfolio") if v1_exact else {}
    if type(portfolio_v1) is not dict:
        portfolio_v1 = {}
    document: dict[str, Any] = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "RISK_REDUCTION_PATH"
            if status == "PASS" and risk_reduction
            else "PASS_WEIGHTED_RESEARCH_BUDGET"
            if status == "PASS"
            else "BLOCK"
        ),
        "source": {
            "v1_schema_version": (
                v1_document.get("schema_version") if v1_exact else None
            ),
            "v1_static_fingerprint": (
                v1_document.get("static_fingerprint") if v1_exact else None
            ),
            "v1_budget_hash": (
                _hash_or_none(v1_document.get("budget_hash")) if v1_exact else None
            ),
            "v1_implementation_sha256": V1_IMPLEMENTATION_SHA256,
            "v1_exactly_verified": v1_exact,
            "v1_status": v1_status,
            "v1_decision": v1_decision,
            "precomputed_v1_result_accepted": False,
        },
        "policy": {
            "weighting_rule": WEIGHTING_RULE,
            "diversification_trigger_rule": DIVERSIFICATION_TRIGGER_RULE,
            "minimum_weighted_effective_cluster_count": (
                MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT
            ),
        },
        "portfolio": {
            "symbol_ticket_count": (
                portfolio_v1.get("symbol_ticket_count")
                if type(portfolio_v1.get("symbol_ticket_count")) is int
                else None
            ),
            "unweighted_effective_cluster_count": (
                portfolio_v1.get("effective_independent_bet_count")
                if type(portfolio_v1.get("effective_independent_bet_count")) is int
                else None
            ),
            "active_cluster_count": (
                metrics["active_cluster_count"] if metrics is not None else None
            ),
            "total_active_gross_pct": (
                metrics["total_active_gross_pct"] if metrics is not None else None
            ),
            "weighted_effective_cluster_count": (
                metrics["weighted_effective_cluster_count"]
                if metrics is not None
                else None
            ),
            "dominant_cluster_id": (
                metrics["dominant_cluster_id"] if metrics is not None else None
            ),
            "dominant_cluster_share_of_active_gross_pct": (
                metrics["dominant_cluster_share_of_active_gross_pct"]
                if metrics is not None
                else None
            ),
            "diversification_trigger_gross_pct": (
                metrics["diversification_trigger_gross_pct"]
                if metrics is not None
                else None
            ),
            "weighted_diversification_gate_applied": (
                weighted_gate_applied if metrics is not None else False
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "risk_increasing": (
                facts.get("risk_increasing")
                if type(facts) is dict
                and type(facts.get("risk_increasing")) is bool
                else None
            ),
            "v1_decision_preserved": v1_gate_ok,
            "weighted_metrics_exactly_derived": metrics is not None,
            "weighted_diversification_not_applicable": risk_reduction,
            "gross_weighting_used": metrics is not None,
            "direction_netting_used": False,
            "cluster_labels_treated_as_equal_weight_bets": False,
            "source_documents_embedded": False,
            "cluster_exposure_rows_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "budget_v2_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v2(
    document: Any,
    preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = budget_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_cluster_effective_bet_budget_v2(
            preregistration,
            correlation_matrix,
            complete_link_audit,
            equity=equity,
            positions=positions,
            proposed_symbol=proposed_symbol,
            proposed_notional=proposed_notional,
            proposed_direction=proposed_direction,
            max_cluster_gross_pct=max_cluster_gross_pct,
            risk_increasing=risk_increasing,
        )
    except Exception:
        return {
            "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": ["budget_v2_rebuild_error"],
            "budget_decision": "UNKNOWN",
            "runtime_gate_activation_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": BUDGET_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["budget_v2_exact_reconstruction"],
        "budget_decision": expected["decision"] if exact else "UNKNOWN",
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "BUDGET_SCHEMA_VERSION",
    "BUDGET_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "V1_IMPLEMENTATION_SHA256",
    "MINIMUM_WEIGHTED_EFFECTIVE_CLUSTER_COUNT",
    "DIVERSIFICATION_TRIGGER_RULE",
    "WEIGHTING_RULE",
    "evaluate_strategy_correlation_cluster_effective_bet_budget_v2",
    "verify_strategy_correlation_cluster_effective_bet_budget_v2",
]
