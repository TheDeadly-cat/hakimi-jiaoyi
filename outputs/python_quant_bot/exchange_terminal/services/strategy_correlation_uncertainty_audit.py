from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math
from typing import Any

from .strategy_correlation_cluster_gate import authority_violations
from .strategy_correlation_return_replay import verify_correlation_matrix_replay
from .canonical_json_hash import canonical_hash
from .strict_canonical_json_hash import strict_json_contract_equal


STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-audit-v2"
)
STRATEGY_CORRELATION_UNCERTAINTY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-verification-v2"
)
STRATEGY_CORRELATION_UNCERTAINTY_POLICY_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-policy-v1"
)
STRATEGY_CORRELATION_UNCERTAINTY_POLICY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-policy-verification-v1"
)
UNCERTAINTY_POLICY = "FISHER_Z_95_WITH_LAG1_EFFECTIVE_N_DESCRIPTIVE_V1"
EFFECTIVE_SAMPLE_METHOD = "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1"
LOOKBACK_OBSERVATIONS = 60
REQUIRED_PRICE_ROWS = 61
MINIMUM_PAIR_OVERLAP = 40
MINIMUM_EFFECTIVE_OBSERVATIONS = 12.0
ABSOLUTE_PEARSON_THRESHOLD = 0.75
FISHER_Z_CRITICAL_95 = 1.959963984540054
_POLICY_FIELDS = frozenset({
    "schema_version",
    "uncertainty_audit_schema_version",
    "return_method",
    "uncertainty_policy",
    "effective_sample_method",
    "confidence_level",
    "fisher_z_critical",
    "lookback_observations",
    "required_price_rows",
    "minimum_pair_overlap",
    "minimum_effective_observations",
    "absolute_pearson_threshold",
    "confirmed_high_rule",
    "confirmed_low_rule",
    "ambiguous_cross_cluster_action",
    "insufficient_effective_sample_action",
    "within_cluster_high_additional_votes",
    "descriptive_only",
    "requires_new_report_schema",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "permissions",
    "policy_hash",
})


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("non-native numeric value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric value")
    return result


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("pearson overlap invalid")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_sum = sum(value * value for value in left_centered)
    right_sum = sum(value * value for value in right_centered)
    if left_sum <= 0.0 or right_sum <= 0.0:
        raise ValueError("pearson variance invalid")
    numerator = sum(
        left_value * right_value
        for left_value, right_value in zip(left_centered, right_centered, strict=True)
    )
    return max(-1.0, min(1.0, numerator / math.sqrt(left_sum * right_sum)))


def _lag1_autocorrelation(values: list[float]) -> float:
    if len(values) < 4:
        return 0.0
    try:
        return _pearson(values[:-1], values[1:])
    except ValueError:
        return 0.0


def _effective_observations(
    overlap: int,
    left_lag1: float,
    right_lag1: float,
) -> float:
    product = left_lag1 * right_lag1
    denominator = 1.0 + product
    if denominator <= 1e-12:
        raw = float(overlap)
    else:
        raw = overlap * (1.0 - product) / denominator
    return max(4.0, min(float(overlap), raw))


def _fisher_absolute_interval(correlation: float, effective_n: float) -> tuple[float, float]:
    if effective_n <= 3.0:
        return 0.0, 1.0
    magnitude = min(abs(correlation), 1.0 - 1e-12)
    center = math.atanh(magnitude)
    margin = FISHER_Z_CRITICAL_95 / math.sqrt(effective_n - 3.0)
    lower = max(0.0, math.tanh(center - margin))
    upper = min(1.0, math.tanh(center + margin))
    return lower, upper


def _completed_returns(document: dict[str, Any]) -> dict[str, dict[str, float]]:
    matrix_replay = _mapping(document)
    completed_input = _mapping(matrix_replay.get("completed_price_input"))
    datasets = _sequence(completed_input.get("datasets"))
    result: dict[str, dict[str, float]] = {}
    for dataset in datasets:
        dataset_map = _mapping(dataset)
        symbol = str(dataset_map.get("symbol") or "")
        rows = _sequence(dataset_map.get("price_rows"))
        if not symbol or len(rows) != REQUIRED_PRICE_ROWS or symbol in result:
            raise ValueError("completed price dataset invalid")
        returns: dict[str, float] = {}
        previous_close: float | None = None
        for row in rows:
            row_map = _mapping(row)
            row_date = row_map.get("date")
            close = _finite_number(row_map.get("close"))
            if not isinstance(row_date, str) or not row_date or close <= 0.0:
                raise ValueError("completed price row invalid")
            if previous_close is not None:
                if row_date in returns:
                    raise ValueError("completed return date duplicate")
                returns[row_date] = close / previous_close - 1.0
            previous_close = close
        if len(returns) != LOOKBACK_OBSERVATIONS:
            raise ValueError("completed return lookback invalid")
        result[symbol] = returns
    return result


def _cluster_membership(preregistration: dict[str, Any]) -> dict[str, str]:
    membership: dict[str, str] = {}
    for cluster in _sequence(preregistration.get("clusters")):
        cluster_map = _mapping(cluster)
        cluster_id = str(cluster_map.get("cluster_id") or "")
        for symbol in _sequence(cluster_map.get("members")):
            symbol_text = str(symbol or "")
            if not cluster_id or not symbol_text or symbol_text in membership:
                raise ValueError("cluster membership invalid")
            membership[symbol_text] = cluster_id
    expected_symbols = sorted(str(item or "") for item in _sequence(preregistration.get("symbols")))
    if sorted(membership) != expected_symbols:
        raise ValueError("cluster partition mismatch")
    return membership


def _pair_uncertainty(
    left_symbol: str,
    right_symbol: str,
    returns: dict[str, dict[str, float]],
    membership: dict[str, str],
) -> dict[str, Any]:
    overlap_dates = sorted(set(returns[left_symbol]) & set(returns[right_symbol]))
    if len(overlap_dates) < MINIMUM_PAIR_OVERLAP:
        raise ValueError("pair overlap below minimum")
    left_values = [returns[left_symbol][item] for item in overlap_dates]
    right_values = [returns[right_symbol][item] for item in overlap_dates]
    correlation = _pearson(left_values, right_values)
    left_lag1 = _lag1_autocorrelation(left_values)
    right_lag1 = _lag1_autocorrelation(right_values)
    effective_n = _effective_observations(len(overlap_dates), left_lag1, right_lag1)
    lower, upper = _fisher_absolute_interval(correlation, effective_n)
    if effective_n < MINIMUM_EFFECTIVE_OBSERVATIONS:
        classification = "INSUFFICIENT_EFFECTIVE_SAMPLE"
    elif lower >= ABSOLUTE_PEARSON_THRESHOLD:
        classification = "CONFIRMED_HIGH"
    elif upper < ABSOLUTE_PEARSON_THRESHOLD:
        classification = "CONFIRMED_LOW"
    else:
        classification = "AMBIGUOUS_THRESHOLD"
    left_cluster = membership[left_symbol]
    right_cluster = membership[right_symbol]
    return {
        "left_symbol": left_symbol,
        "right_symbol": right_symbol,
        "left_cluster_id": left_cluster,
        "right_cluster_id": right_cluster,
        "cross_cluster": left_cluster != right_cluster,
        "overlap_observations": len(overlap_dates),
        "correlation": round(correlation, 12),
        "absolute_correlation": round(abs(correlation), 12),
        "left_lag1_autocorrelation": round(left_lag1, 12),
        "right_lag1_autocorrelation": round(right_lag1, 12),
        "effective_observations": round(effective_n, 6),
        "absolute_correlation_interval_lower": round(lower, 12),
        "absolute_correlation_interval_upper": round(upper, 12),
        "classification": classification,
    }


def build_strategy_correlation_uncertainty_policy() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_UNCERTAINTY_POLICY_SCHEMA_VERSION,
        "uncertainty_audit_schema_version": STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
        "return_method": "SIMPLE_CLOSE_TO_CLOSE_RETURN",
        "uncertainty_policy": UNCERTAINTY_POLICY,
        "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
        "confidence_level": 0.95,
        "fisher_z_critical": FISHER_Z_CRITICAL_95,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "confirmed_high_rule": "ABSOLUTE_INTERVAL_LOWER_GTE_THRESHOLD",
        "confirmed_low_rule": "ABSOLUTE_INTERVAL_UPPER_LT_THRESHOLD",
        "ambiguous_cross_cluster_action": "BLOCK",
        "insufficient_effective_sample_action": "BLOCK",
        "within_cluster_high_additional_votes": 0,
        "descriptive_only": True,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["policy_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_uncertainty_policy(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_uncertainty_policy_type_invalid")
        document = {}
    expected = build_strategy_correlation_uncertainty_policy()
    if set(document) != _POLICY_FIELDS or not strict_json_contract_equal(
        document,
        expected,
    ):
        blockers.append("strategy_correlation_uncertainty_policy_contract_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_uncertainty_policy_authority_violation")
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": STRATEGY_CORRELATION_UNCERTAINTY_POLICY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "policy_hash": expected["policy_hash"] if not blockers else "",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def build_strategy_correlation_uncertainty_audit(
    matrix_replay: dict[str, Any],
) -> dict[str, Any]:
    replay_verification = verify_correlation_matrix_replay(matrix_replay)
    if replay_verification.get("status") != "PASS":
        raise ValueError("correlation matrix replay verification blocked")
    replay_map = _mapping(matrix_replay)
    preregistration = _mapping(replay_map.get("preregistration"))
    returns = _completed_returns(replay_map)
    membership = _cluster_membership(preregistration)
    symbols = sorted(membership)
    if sorted(returns) != symbols:
        raise ValueError("uncertainty audit symbol coverage mismatch")
    pairs = [
        _pair_uncertainty(left, right, returns, membership)
        for left, right in combinations(symbols, 2)
    ]
    cross_cluster_pairs = [item for item in pairs if item["cross_cluster"]]
    high_cross_cluster = [
        item for item in cross_cluster_pairs if item["classification"] == "CONFIRMED_HIGH"
    ]
    ambiguous_cross_cluster = [
        item
        for item in cross_cluster_pairs
        if item["classification"] == "AMBIGUOUS_THRESHOLD"
    ]
    insufficient_pairs = [
        item
        for item in pairs
        if item["classification"] == "INSUFFICIENT_EFFECTIVE_SAMPLE"
    ]
    blockers: list[str] = []
    blockers.extend(
        f"insufficient_effective_sample:{item['left_symbol']}:{item['right_symbol']}"
        for item in insufficient_pairs
    )
    blockers.extend(
        f"confirmed_high_cross_cluster:{item['left_symbol']}:{item['right_symbol']}"
        for item in high_cross_cluster
    )
    blockers.extend(
        f"ambiguous_cross_cluster:{item['left_symbol']}:{item['right_symbol']}"
        for item in ambiguous_cross_cluster
    )
    if insufficient_pairs:
        first_blocking_tier = "EFFECTIVE_SAMPLE"
    elif high_cross_cluster:
        first_blocking_tier = "CROSS_CLUSTER_HIGH"
    elif ambiguous_cross_cluster:
        first_blocking_tier = "CROSS_CLUSTER_UNCERTAINTY"
    else:
        first_blocking_tier = "NONE"
    policy = build_strategy_correlation_uncertainty_policy()
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
        "status": "BLOCK" if blockers else "PASS",
        "interpretation": "DESCRIPTIVE_DEPENDENCE_UNCERTAINTY_ONLY",
        "uncertainty_policy": UNCERTAINTY_POLICY,
        "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "confidence_level": 0.95,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "matrix_replay": deepcopy(matrix_replay),
        "pairs": pairs,
        "pair_count": len(pairs),
        "cross_cluster_pair_count": len(cross_cluster_pairs),
        "confirmed_high_cross_cluster_count": len(high_cross_cluster),
        "ambiguous_cross_cluster_count": len(ambiguous_cross_cluster),
        "insufficient_effective_sample_pair_count": len(insufficient_pairs),
        "first_blocking_tier": first_blocking_tier,
        "blockers": blockers,
        "requires_new_report_schema": True,
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["audit_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_uncertainty_audit(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_uncertainty_audit_type_invalid")
        document = {}
    try:
        expected = build_strategy_correlation_uncertainty_audit(
            _mapping(document.get("matrix_replay"))
        )
    except Exception:
        expected = None
        blockers.append("strategy_correlation_uncertainty_audit_source_invalid")
    if expected is not None and not strict_json_contract_equal(document, expected):
        blockers.append("strategy_correlation_uncertainty_audit_replay_mismatch")
    policy_verification = verify_strategy_correlation_uncertainty_policy(
        document.get("policy")
    )
    if policy_verification.get("status") != "PASS":
        blockers.extend(
            f"strategy_correlation_uncertainty_audit_policy:{item}"
            for item in policy_verification.get("blockers") or []
        )
    if document.get("policy_hash") != policy_verification.get("policy_hash"):
        blockers.append("strategy_correlation_uncertainty_audit_policy_hash_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_uncertainty_audit_authority_violation")
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": STRATEGY_CORRELATION_UNCERTAINTY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "audit_hash": expected["audit_hash"] if expected is not None and not blockers else "",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION",
    "STRATEGY_CORRELATION_UNCERTAINTY_POLICY_SCHEMA_VERSION",
    "build_strategy_correlation_uncertainty_audit",
    "build_strategy_correlation_uncertainty_policy",
    "verify_strategy_correlation_uncertainty_audit",
    "verify_strategy_correlation_uncertainty_policy",
]
