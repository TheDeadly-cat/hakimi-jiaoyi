from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist
from typing import Any

try:
    from .strategy_correlation_cluster_stability import (
        GATE_SCHEMA_VERSION as FULL_WINDOW_STABILITY_GATE_SCHEMA_VERSION,
        verify_strategy_correlation_cluster_stability_gate,
    )
    from .strategy_correlation_uncertainty_audit import (
        STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
        verify_strategy_correlation_uncertainty_audit,
    )
    from .strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_json_contract_equal,
    )
    from .strict_governance_primitives import (
        strict_iso_date,
        strict_locked_fields,
        strict_native_true,
        strict_nonempty_string,
    )
    from .strict_research_authority import strict_research_authority_invalid
except ImportError:  # pragma: no cover - project-root service import compatibility
    from services.strategy_correlation_cluster_stability import (
        GATE_SCHEMA_VERSION as FULL_WINDOW_STABILITY_GATE_SCHEMA_VERSION,
        verify_strategy_correlation_cluster_stability_gate,
    )
    from services.strategy_correlation_uncertainty_audit import (
        STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
        verify_strategy_correlation_uncertainty_audit,
    )
    from services.strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_json_contract_equal,
    )
    from services.strict_governance_primitives import (
        strict_iso_date,
        strict_locked_fields,
        strict_native_true,
        strict_nonempty_string,
    )
    from services.strict_research_authority import strict_research_authority_invalid


POLICY_SCHEMA_VERSION = "strategy-correlation-cluster-temporal-stability-policy-v1"
POLICY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-stability-policy-verification-v1"
)
AUDIT_SCHEMA_VERSION = "strategy-correlation-cluster-temporal-stability-audit-v1"
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-temporal-stability-gate-v1"
GATE_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-stability-gate-verification-v1"
)

LOOKBACK_OBSERVATIONS = 60
WINDOW_COUNT = 3
WINDOW_OBSERVATIONS = 20
MINIMUM_EFFECTIVE_OBSERVATIONS = 12.0
ABSOLUTE_PEARSON_THRESHOLD = 0.75
FAMILYWISE_CONFIDENCE_LEVEL = 0.95
CORRECTION_METHOD = "BONFERRONI_TWO_SIDED_FWER_V1"
EFFECTIVE_SAMPLE_METHOD = "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1"
WINDOW_RULE = "ALL_PREREGISTERED_WINDOWS_ADJUSTED_ABSOLUTE_LOWER_GTE_THRESHOLD"
WINDOW_SPLIT_RULE = "THREE_CONTIGUOUS_NON_OVERLAPPING_OLDEST_TO_NEWEST_V1"
FAMILY_SCOPE = "WITHIN_CLUSTER_PAIR_X_PREREGISTERED_WINDOW"
SIGN_POLICY = "ABSOLUTE_DEPENDENCE_SIGN_AGNOSTIC"

_LOCK_FIELDS = ("current_writer_activation_allowed", "current_admission_allowed")


def _permissions() -> dict[str, bool]:
    return {"paper_authorized": False, "live_order_allowed": False}


def build_strategy_correlation_cluster_temporal_stability_policy() -> dict[str, Any]:
    document = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_uncertainty_audit_schema_version": (
            STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION
        ),
        "source_full_window_stability_gate_schema_version": (
            FULL_WINDOW_STABILITY_GATE_SCHEMA_VERSION
        ),
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "window_count": WINDOW_COUNT,
        "window_observations": WINDOW_OBSERVATIONS,
        "window_split_rule": WINDOW_SPLIT_RULE,
        "window_rule": WINDOW_RULE,
        "family_scope": FAMILY_SCOPE,
        "familywise_confidence_level": FAMILYWISE_CONFIDENCE_LEVEL,
        "correction_method": CORRECTION_METHOD,
        "critical_value_formula": (
            "NORMAL_INV_CDF(1 - 0.05 / (2 * within_cluster_pair_window_count))"
        ),
        "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
        "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "sign_policy": SIGN_POLICY,
        "singleton_cluster_rule": "NO_INTERNAL_PAIR_REQUIRED",
        "source_block_action": "PRESERVE_BLOCK",
        "full_window_stability_block_action": "PRESERVE_BLOCK",
        "descriptive_only": True,
        "parameter_selection_allowed": False,
        "consumer_only": True,
        "writer_available": False,
        "report_integration_status": "NOT_IMPLEMENTED",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    return seal_strict_canonical_document(document, "policy_hash")


def verify_strategy_correlation_cluster_temporal_stability_policy(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    policy = document if isinstance(document, dict) else {}
    if not isinstance(document, dict):
        blockers.append("POLICY_NOT_OBJECT")
    expected = build_strategy_correlation_cluster_temporal_stability_policy()
    if not strict_json_contract_equal(policy, expected):
        blockers.append("POLICY_REBUILD_MISMATCH")
    if strict_research_authority_invalid(policy):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not strict_locked_fields(policy, _LOCK_FIELDS):
        blockers.append("POLICY_AUTHORITY_NOT_LOCKED")
    if policy.get("writer_available") is not False:
        blockers.append("WRITER_AVAILABLE_ALIAS")
    unique = list(dict.fromkeys(blockers))
    passed = not unique
    return {
        "schema_version": POLICY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique,
        "policy_verified": passed,
        "writer_available": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 3:
        raise ValueError("temporal_pair_length_invalid")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    left_variance = sum((value - left_mean) ** 2 for value in left)
    right_variance = sum((value - right_mean) ** 2 for value in right)
    denominator = math.sqrt(left_variance * right_variance)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("temporal_pair_zero_variance")
    value = numerator / denominator
    if not math.isfinite(value):
        raise ValueError("temporal_pair_correlation_nonfinite")
    return max(-1.0, min(1.0, value))


def _lag1_autocorrelation(values: list[float]) -> float:
    return _pearson(values[:-1], values[1:])


def _effective_observations(
    observations: int,
    left_lag1: float,
    right_lag1: float,
) -> float:
    product = max(-0.95, min(0.95, left_lag1 * right_lag1))
    raw = observations * (1.0 - product) / (1.0 + product)
    return min(float(observations), max(4.0, raw))


def _absolute_interval(
    correlation: float,
    effective_observations: float,
    critical_value: float,
) -> tuple[float, float]:
    clipped = max(-1.0 + 1e-12, min(1.0 - 1e-12, correlation))
    standard_error = 1.0 / math.sqrt(effective_observations - 3.0)
    center = math.atanh(clipped)
    lower = math.tanh(center - critical_value * standard_error)
    upper = math.tanh(center + critical_value * standard_error)
    absolute_lower = 0.0 if lower <= 0.0 <= upper else min(abs(lower), abs(upper))
    absolute_upper = max(abs(lower), abs(upper))
    return absolute_lower, absolute_upper


def _extract_returns(source_uncertainty_audit: dict[str, Any]) -> dict[str, list[float]]:
    replay = source_uncertainty_audit.get("matrix_replay")
    completed = replay.get("completed_price_input") if isinstance(replay, dict) else None
    datasets = completed.get("datasets") if isinstance(completed, dict) else None
    if not isinstance(datasets, list):
        raise ValueError("temporal_completed_datasets_missing")
    returns_by_symbol: dict[str, list[float]] = {}
    for dataset in datasets:
        if not isinstance(dataset, dict):
            raise ValueError("temporal_dataset_invalid")
        symbol = dataset.get("symbol")
        rows = dataset.get("price_rows")
        if not strict_nonempty_string(symbol) or symbol in returns_by_symbol:
            raise ValueError("temporal_dataset_symbol_invalid")
        if not isinstance(rows, list) or len(rows) != LOOKBACK_OBSERVATIONS + 1:
            raise ValueError("temporal_price_row_count_invalid")
        closes: list[float] = []
        dates: list[str] = []
        for row in rows:
            if not isinstance(row, dict) or not strict_native_true(row.get("complete")):
                raise ValueError("temporal_price_row_incomplete")
            trading_date = row.get("date")
            close = row.get("close")
            if not strict_iso_date(trading_date):
                raise ValueError("temporal_price_date_invalid")
            if type(close) not in (int, float) or not math.isfinite(close) or close <= 0.0:
                raise ValueError("temporal_price_close_invalid")
            dates.append(trading_date)
            closes.append(float(close))
        if any(right <= left for left, right in zip(dates, dates[1:])):
            raise ValueError("temporal_price_dates_not_increasing")
        returns_by_symbol[symbol] = [
            closes[index] / closes[index - 1] - 1.0
            for index in range(1, len(closes))
        ]
    return returns_by_symbol


def _within_cluster_pairs(preregistration: dict[str, Any]) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    clusters = preregistration.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("temporal_clusters_invalid")
    for cluster in clusters:
        if not isinstance(cluster, dict):
            raise ValueError("temporal_cluster_invalid")
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if not strict_nonempty_string(cluster_id) or not isinstance(members, list):
            raise ValueError("temporal_cluster_shape_invalid")
        for left, right in combinations(members, 2):
            if not strict_nonempty_string(left) or not strict_nonempty_string(right):
                raise ValueError("temporal_cluster_member_invalid")
            pairs.append((cluster_id, left, right))
    return pairs


def _build_temporal_audit(
    source_uncertainty_audit: Any,
    full_window_stability_gate: Any,
    *,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    policy = build_strategy_correlation_cluster_temporal_stability_policy()
    blockers: list[str] = []
    source = source_uncertainty_audit if isinstance(source_uncertainty_audit, dict) else {}
    full_gate = full_window_stability_gate if isinstance(full_window_stability_gate, dict) else {}
    prereg = preregistration if isinstance(preregistration, dict) else {}
    matrix = correlation_matrix if isinstance(correlation_matrix, dict) else {}

    try:
        source_verification = verify_strategy_correlation_uncertainty_audit(source)
    except Exception:
        source_verification = {"status": "BLOCK"}
    try:
        full_gate_verification = verify_strategy_correlation_cluster_stability_gate(
            full_gate,
            source_uncertainty_audit=source,
            complete_link_gate=complete_link_gate,
            preregistration=prereg,
            correlation_matrix=matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except Exception:
        full_gate_verification = {"status": "BLOCK"}

    source_audit_verified = source_verification.get("status") == "PASS"
    full_window_gate_verified = full_gate_verification.get("status") == "PASS"
    source_contract_verified = source_audit_verified and full_window_gate_verified
    if not source_audit_verified:
        blockers.append("SOURCE_UNCERTAINTY_AUDIT_NOT_VERIFIED")
    if not full_window_gate_verified:
        blockers.append("FULL_WINDOW_STABILITY_GATE_NOT_VERIFIED")
    if strict_research_authority_invalid(source) or strict_research_authority_invalid(full_gate):
        blockers.append("RESEARCH_AUTHORITY_INVALID")

    pair_results: list[dict[str, Any]] = []
    cluster_results: list[dict[str, Any]] = []
    within_pairs: list[tuple[str, str, str]] = []
    returns_by_symbol: dict[str, list[float]] = {}
    try:
        within_pairs = _within_cluster_pairs(prereg)
        returns_by_symbol = _extract_returns(source)
    except Exception as exc:
        blockers.append(type(exc).__name__ + ":TEMPORAL_INPUT_REPLAY_FAILED")

    family_size = len(within_pairs) * WINDOW_COUNT
    per_test_alpha = (
        (1.0 - FAMILYWISE_CONFIDENCE_LEVEL) / family_size if family_size else None
    )
    critical_value = (
        NormalDist().inv_cdf(1.0 - per_test_alpha / 2.0)
        if per_test_alpha is not None
        else 0.0
    )

    can_evaluate = (
        source_contract_verified
        and source.get("status") == "PASS"
        and isinstance(full_gate, dict)
        and full_gate.get("status") == "PASS"
        and not blockers
    )
    if source_contract_verified and source.get("status") != "PASS":
        blockers.append("SOURCE_UNCERTAINTY_DECISION_BLOCK")
    if isinstance(full_gate, dict) and full_gate.get("status") != "PASS":
        blockers.append("FULL_WINDOW_STABILITY_DECISION_BLOCK")

    if can_evaluate:
        pair_status_by_cluster: dict[str, list[str]] = {}
        for cluster_id, left, right in within_pairs:
            left_returns = returns_by_symbol.get(left)
            right_returns = returns_by_symbol.get(right)
            window_results: list[dict[str, Any]] = []
            pair_blockers: list[str] = []
            if left_returns is None or right_returns is None:
                pair_blockers.append("PAIR_RETURN_SERIES_MISSING")
            else:
                for window_index in range(WINDOW_COUNT):
                    start = window_index * WINDOW_OBSERVATIONS
                    end = start + WINDOW_OBSERVATIONS
                    left_window = left_returns[start:end]
                    right_window = right_returns[start:end]
                    try:
                        correlation = _pearson(left_window, right_window)
                        left_lag1 = _lag1_autocorrelation(left_window)
                        right_lag1 = _lag1_autocorrelation(right_window)
                        effective = _effective_observations(
                            WINDOW_OBSERVATIONS,
                            left_lag1,
                            right_lag1,
                        )
                        if effective < MINIMUM_EFFECTIVE_OBSERVATIONS:
                            classification = "INSUFFICIENT_EFFECTIVE_SAMPLE"
                            absolute_lower = 0.0
                            absolute_upper = 1.0
                            window_status = "BLOCK"
                        else:
                            absolute_lower, absolute_upper = _absolute_interval(
                                correlation,
                                effective,
                                critical_value,
                            )
                            if absolute_lower >= ABSOLUTE_PEARSON_THRESHOLD:
                                classification = "STABLE_ABSOLUTE_DEPENDENCE"
                                window_status = "PASS"
                            else:
                                classification = "UNSTABLE_ABSOLUTE_DEPENDENCE"
                                window_status = "BLOCK"
                    except Exception:
                        correlation = 0.0
                        left_lag1 = 0.0
                        right_lag1 = 0.0
                        effective = 0.0
                        absolute_lower = 0.0
                        absolute_upper = 1.0
                        classification = "INVALID_PAIR_INPUT"
                        window_status = "BLOCK"
                    window_results.append(
                        {
                            "window_index": window_index + 1,
                            "return_start_offset": start,
                            "return_end_offset_exclusive": end,
                            "overlap_observations": WINDOW_OBSERVATIONS,
                            "correlation": round(correlation, 12),
                            "absolute_correlation": round(abs(correlation), 12),
                            "left_lag1_autocorrelation": round(left_lag1, 12),
                            "right_lag1_autocorrelation": round(right_lag1, 12),
                            "effective_observations": round(effective, 6),
                            "adjusted_absolute_interval_lower": round(
                                absolute_lower, 12
                            ),
                            "adjusted_absolute_interval_upper": round(
                                absolute_upper, 12
                            ),
                            "classification": classification,
                            "status": window_status,
                        }
                    )
                    if window_status != "PASS":
                        pair_blockers.append(
                            f"WINDOW_{window_index + 1}_{classification}"
                        )
            pair_status = "PASS" if not pair_blockers else "BLOCK"
            pair_status_by_cluster.setdefault(cluster_id, []).append(pair_status)
            pair_results.append(
                {
                    "cluster_id": cluster_id,
                    "left_symbol": left,
                    "right_symbol": right,
                    "status": pair_status,
                    "blockers": pair_blockers,
                    "window_results": window_results,
                }
            )
            if pair_blockers:
                blockers.extend(
                    f"{cluster_id}:{left}:{right}:{item}" for item in pair_blockers
                )

        for cluster in prereg.get("clusters", []):
            cluster_id = cluster.get("cluster_id")
            pair_statuses = pair_status_by_cluster.get(cluster_id, [])
            singleton = len(cluster.get("members", [])) == 1
            cluster_status = (
                "PASS"
                if singleton or (pair_statuses and all(item == "PASS" for item in pair_statuses))
                else "BLOCK"
            )
            cluster_results.append(
                {
                    "cluster_id": cluster_id,
                    "singleton": singleton,
                    "internal_pair_count": len(pair_statuses),
                    "status": cluster_status,
                }
            )

    unique_blockers = list(dict.fromkeys(blockers))
    if not source_contract_verified:
        first_blocking_tier = "SOURCE_CONTRACTS"
    elif source.get("status") != "PASS" or full_gate.get("status") != "PASS":
        first_blocking_tier = "FULL_WINDOW_STABILITY"
    elif unique_blockers:
        first_blocking_tier = "TEMPORAL_WINDOWS"
    else:
        first_blocking_tier = "NONE"
    passed = not unique_blockers and can_evaluate
    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "first_blocking_tier": first_blocking_tier,
        "blockers": unique_blockers,
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "source_uncertainty_audit_hash": source.get("audit_hash"),
        "full_window_stability_gate_hash": full_gate.get("gate_hash"),
        "preregistration_hash": prereg.get("preregistration_hash"),
        "matrix_hash": matrix.get("matrix_hash"),
        "input_binding": {
            "source_uncertainty_audit_verified": source_audit_verified,
            "full_window_stability_gate_verified": full_window_gate_verified,
            "full_window_stability_gate_status_pass": full_gate.get("status") == "PASS",
            "strategy_identity_bound": (
                full_gate.get("strategy_id") == strategy_id
                and full_gate.get("variant_id") == variant_id
                and full_gate.get("lane") == lane
            ),
        },
        "within_cluster_pair_count": len(within_pairs),
        "pair_window_hypothesis_count": family_size,
        "per_test_alpha": round(per_test_alpha, 12) if per_test_alpha else None,
        "bonferroni_critical_value": round(critical_value, 12),
        "pair_results": pair_results,
        "cluster_results": cluster_results,
        "consumer_only": True,
        "writer_available": False,
        "report_integration_status": "NOT_IMPLEMENTED",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    return seal_strict_canonical_document(audit, "audit_hash")


def evaluate_strategy_correlation_cluster_temporal_stability_gate(
    source_uncertainty_audit: Any,
    full_window_stability_gate: Any,
    *,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    audit = _build_temporal_audit(
        source_uncertainty_audit,
        full_window_stability_gate,
        complete_link_gate=complete_link_gate,
        preregistration=preregistration,
        correlation_matrix=correlation_matrix,
        selection_cells=selection_cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    status = audit["status"]
    document = {
        "schema_version": GATE_SCHEMA_VERSION,
        "status": status,
        "first_blocking_tier": audit["first_blocking_tier"],
        "blockers": audit["blockers"],
        "strategy_id": strategy_id,
        "variant_id": variant_id,
        "lane": lane,
        "policy_hash": audit["policy_hash"],
        "temporal_stability_audit_hash": audit["audit_hash"],
        "temporal_stability_audit": audit,
        "tiers": [
            {
                "tier_id": "SOURCE_CONTRACTS",
                "status": (
                    "PASS"
                    if audit["first_blocking_tier"] != "SOURCE_CONTRACTS"
                    else "BLOCK"
                ),
            },
            {
                "tier_id": "FULL_WINDOW_STABILITY",
                "status": (
                    "BLOCK"
                    if audit["first_blocking_tier"] == "FULL_WINDOW_STABILITY"
                    else "PASS"
                ),
            },
            {"tier_id": "TEMPORAL_WINDOWS", "status": status},
        ],
        "consumer_only": True,
        "writer_available": False,
        "requires_new_report_schema": True,
        "report_integration_status": "NOT_IMPLEMENTED",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_cluster_temporal_stability_gate(
    document: Any,
    *,
    source_uncertainty_audit: Any,
    full_window_stability_gate: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate = document if isinstance(document, dict) else {}
    if not isinstance(document, dict):
        blockers.append("GATE_NOT_OBJECT")
    try:
        expected = evaluate_strategy_correlation_cluster_temporal_stability_gate(
            source_uncertainty_audit,
            full_window_stability_gate,
            complete_link_gate=complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
        if not strict_json_contract_equal(gate, expected):
            blockers.append("GATE_REBUILD_MISMATCH")
    except Exception:
        expected = {}
        blockers.append("GATE_REBUILD_FAILED")
    if strict_research_authority_invalid(gate):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not strict_locked_fields(gate, _LOCK_FIELDS):
        blockers.append("GATE_AUTHORITY_NOT_LOCKED")
    if gate.get("writer_available") is not False:
        blockers.append("WRITER_AVAILABLE_ALIAS")
    unique = list(dict.fromkeys(blockers))
    passed = not unique
    return {
        "schema_version": GATE_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique,
        "gate_verified": passed,
        "decision_status": expected.get("status", "UNKNOWN"),
        "consumer_only": True,
        "writer_available": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


__all__ = [
    "POLICY_SCHEMA_VERSION",
    "POLICY_VERIFICATION_SCHEMA_VERSION",
    "AUDIT_SCHEMA_VERSION",
    "GATE_SCHEMA_VERSION",
    "GATE_VERIFICATION_SCHEMA_VERSION",
    "LOOKBACK_OBSERVATIONS",
    "WINDOW_COUNT",
    "WINDOW_OBSERVATIONS",
    "MINIMUM_EFFECTIVE_OBSERVATIONS",
    "ABSOLUTE_PEARSON_THRESHOLD",
    "FAMILYWISE_CONFIDENCE_LEVEL",
    "CORRECTION_METHOD",
    "EFFECTIVE_SAMPLE_METHOD",
    "WINDOW_RULE",
    "WINDOW_SPLIT_RULE",
    "FAMILY_SCOPE",
    "SIGN_POLICY",
    "build_strategy_correlation_cluster_temporal_stability_policy",
    "verify_strategy_correlation_cluster_temporal_stability_policy",
    "evaluate_strategy_correlation_cluster_temporal_stability_gate",
    "verify_strategy_correlation_cluster_temporal_stability_gate",
]
