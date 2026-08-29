from __future__ import annotations

import hmac
import math
from itertools import combinations
from statistics import NormalDist
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_nonempty_string,
    strict_sha256,
)


EVALUATION_SCHEMA = "strategy-correlation-cross-lag-gate-candidate-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-dependence-gate-1"

LAGS = (-2, -1, 1, 2)
MIN_IDENTITY_COUNT = 2
MAX_IDENTITY_COUNT = 64
MIN_OBSERVATION_COUNT = 64
MAX_OBSERVATION_COUNT = 2_000
MIN_EFFECTIVE_SAMPLE = 20.0
MIN_ADJUSTED_ABSOLUTE_LOWER = 0.75
FAMILY_ALPHA = 0.05
AUTOCORRELATION_PRODUCT_CLIP = 0.95

_AUTHORITY = {
    "descriptive_only": True,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "strata_timing_attested": False,
    "sequence_order_attested": False,
    "formal_preregistration_bound": False,
    "candidate_binding_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "profitability_claim_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _strict_identifier(value: Any) -> bool:
    return (
        strict_nonempty_string(value)
        and value == value.strip()
        and len(value) <= 128
        and all(ord(character) >= 32 for character in value)
    )


def _normalize_strata(value: Any) -> dict[str, str] | None:
    if type(value) is not dict or not MIN_IDENTITY_COUNT <= len(value) <= MAX_IDENTITY_COUNT:
        return None
    normalized: dict[str, str] = {}
    for identity, stratum in value.items():
        if not _strict_identifier(identity) or not _strict_identifier(stratum):
            return None
        normalized[identity] = stratum
    if len(set(normalized.values())) < 2:
        return None
    return dict(sorted(normalized.items()))


def _decimal_text(value: float) -> str:
    return format(value, ".12g")


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_ss = sum((value - left_mean) ** 2 for value in left)
    right_ss = sum((value - right_mean) ** 2 for value in right)
    if left_ss <= 0.0 or right_ss <= 0.0:
        return None
    covariance = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left, right)
    )
    return max(-1.0, min(1.0, covariance / math.sqrt(left_ss * right_ss)))


def _lag1_autocorrelation(values: list[float]) -> float | None:
    if len(values) < 4:
        return None
    return _pearson(values[:-1], values[1:])


def _effective_sample_size(left: list[float], right: list[float]) -> float | None:
    left_autocorrelation = _lag1_autocorrelation(left)
    right_autocorrelation = _lag1_autocorrelation(right)
    if left_autocorrelation is None or right_autocorrelation is None:
        return None
    product = max(
        -AUTOCORRELATION_PRODUCT_CLIP,
        min(AUTOCORRELATION_PRODUCT_CLIP, left_autocorrelation * right_autocorrelation),
    )
    estimate = len(left) * (1.0 - product) / (1.0 + product)
    return max(4.0, min(float(len(left)), estimate))


def _shifted_pair(
    left: list[float],
    right: list[float],
    lag: int,
) -> tuple[list[float], list[float]]:
    if lag > 0:
        return left[:-lag], right[lag:]
    shift = -lag
    return left[shift:], right[:-shift]


def _adjusted_absolute_lower(
    correlation: float,
    effective_sample_size: float,
    family_test_count: int,
) -> float:
    per_test_two_sided_alpha = FAMILY_ALPHA / family_test_count
    critical = NormalDist().inv_cdf(1.0 - per_test_two_sided_alpha / 2.0)
    absolute = min(abs(correlation), 1.0 - 1e-15)
    fisher = math.atanh(absolute)
    lower_fisher = max(
        0.0,
        fisher - critical / math.sqrt(effective_sample_size - 3.0),
    )
    return math.tanh(lower_fisher)


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "evaluation_hash")


def _unknown(
    reason: str,
    *,
    stratum_assignment_hash: str | None = None,
) -> dict[str, Any]:
    return _seal(
        {
            "schema_version": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "UNKNOWN",
            "gate_decision": "BLOCK",
            "gate_reason": reason,
            "maturity_state": "NOT_EVALUABLE",
            "stratum_assignment_hash": stratum_assignment_hash,
            "observation_count": None,
            "cross_stratum_pair_count": None,
            "lag_family": list(LAGS),
            "lag_test_count": 0,
            "dependent_test_count": 0,
            "max_adjusted_absolute_lower": None,
            "lag_results": [],
            "blockers": [reason],
            "authority": dict(_AUTHORITY),
        }
    )


def evaluate_strategy_correlation_cross_lag_gate(
    preregistered_strata: Any,
    aligned_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    strata = _normalize_strata(preregistered_strata)
    if strata is None:
        return _unknown("STRATA_CONTRACT_INVALID")
    stratum_assignment_hash = strict_canonical_hash(strata)
    if not strict_sha256(expected_stratum_assignment_hash) or not hmac.compare_digest(
        stratum_assignment_hash,
        expected_stratum_assignment_hash,
    ):
        return _unknown(
            "EXPECTED_STRATUM_ASSIGNMENT_HASH_MISMATCH",
            stratum_assignment_hash=stratum_assignment_hash,
        )
    if type(aligned_observations) is not list:
        return _unknown(
            "ALIGNED_OBSERVATIONS_INVALID",
            stratum_assignment_hash=stratum_assignment_hash,
        )

    identities = list(strata)
    identity_set = set(identities)
    seen_ids: set[str] = set()
    series = {identity: [] for identity in identities}
    for expected_sequence, row in enumerate(aligned_observations):
        if type(row) is not dict or set(row) != {
            "sequence_number",
            "observation_id",
            "returns",
        }:
            return _unknown(
                "OBSERVATION_ROW_CONTRACT_INVALID",
                stratum_assignment_hash=stratum_assignment_hash,
            )
        if type(row.get("sequence_number")) is not int or row[
            "sequence_number"
        ] != expected_sequence:
            return _unknown(
                "OBSERVATION_SEQUENCE_INVALID",
                stratum_assignment_hash=stratum_assignment_hash,
            )
        observation_id = row.get("observation_id")
        if not _strict_identifier(observation_id) or observation_id in seen_ids:
            return _unknown(
                "OBSERVATION_ID_INVALID_OR_DUPLICATE",
                stratum_assignment_hash=stratum_assignment_hash,
            )
        returns = row.get("returns")
        if type(returns) is not dict or set(returns) != identity_set:
            return _unknown(
                "OBSERVATION_IDENTITY_SET_MISMATCH",
                stratum_assignment_hash=stratum_assignment_hash,
            )
        for identity in identities:
            value = returns[identity]
            if type(value) not in (int, float):
                return _unknown(
                    "RETURN_VALUE_INVALID",
                    stratum_assignment_hash=stratum_assignment_hash,
                )
            numeric = float(value)
            if not math.isfinite(numeric):
                return _unknown(
                    "RETURN_VALUE_INVALID",
                    stratum_assignment_hash=stratum_assignment_hash,
                )
            series[identity].append(numeric)
        seen_ids.add(observation_id)

    observation_count = len(aligned_observations)
    if not MIN_OBSERVATION_COUNT <= observation_count <= MAX_OBSERVATION_COUNT:
        return _unknown(
            "OBSERVATION_COUNT_OUTSIDE_PROTOCOL",
            stratum_assignment_hash=stratum_assignment_hash,
        )

    pairs = [
        (left, right)
        for left, right in combinations(identities, 2)
        if strata[left] != strata[right]
    ]
    if not pairs:
        return _unknown(
            "NO_CROSS_STRATUM_PAIR",
            stratum_assignment_hash=stratum_assignment_hash,
        )
    family_test_count = len(pairs) * len(LAGS)

    lag_results: list[dict[str, Any]] = []
    dependent_test_count = 0
    max_lower = 0.0
    for left_identity, right_identity in pairs:
        for lag in LAGS:
            left_values, right_values = _shifted_pair(
                series[left_identity],
                series[right_identity],
                lag,
            )
            correlation = _pearson(left_values, right_values)
            effective_sample_size = _effective_sample_size(left_values, right_values)
            if correlation is None or effective_sample_size is None:
                return _unknown(
                    "SHIFTED_SERIES_NOT_EVALUABLE",
                    stratum_assignment_hash=stratum_assignment_hash,
                )
            if effective_sample_size < MIN_EFFECTIVE_SAMPLE:
                return _unknown(
                    "EFFECTIVE_SAMPLE_BELOW_PROTOCOL",
                    stratum_assignment_hash=stratum_assignment_hash,
                )
            adjusted_lower = _adjusted_absolute_lower(
                correlation,
                effective_sample_size,
                family_test_count,
            )
            dependent = adjusted_lower >= MIN_ADJUSTED_ABSOLUTE_LOWER
            if dependent:
                dependent_test_count += 1
            max_lower = max(max_lower, adjusted_lower)
            lag_results.append(
                {
                    "left_identity": left_identity,
                    "right_identity": right_identity,
                    "left_stratum": strata[left_identity],
                    "right_stratum": strata[right_identity],
                    "lag": lag,
                    "paired_observation_count": len(left_values),
                    "effective_sample_size": _decimal_text(effective_sample_size),
                    "correlation": _decimal_text(correlation),
                    "adjusted_absolute_lower": _decimal_text(adjusted_lower),
                    "dependent": dependent,
                }
            )

    blocked = dependent_test_count > 0
    gate_reason = (
        "CROSS_LAG_DEPENDENCE_DETECTED"
        if blocked
        else "NO_PREREGISTERED_CROSS_LAG_DEPENDENCE_DETECTED"
    )
    return _seal(
        {
            "schema_version": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": "BLOCK" if blocked else "PASS",
            "gate_reason": gate_reason,
            "maturity_state": "CANDIDATE_EVALUATED_NOT_FORMAL",
            "stratum_assignment_hash": stratum_assignment_hash,
            "observation_count": observation_count,
            "cross_stratum_pair_count": len(pairs),
            "lag_family": list(LAGS),
            "lag_test_count": family_test_count,
            "dependent_test_count": dependent_test_count,
            "max_adjusted_absolute_lower": _decimal_text(max_lower),
            "lag_results": lag_results,
            "blockers": [gate_reason] if blocked else [],
            "authority": dict(_AUTHORITY),
        }
    )


def verify_strategy_correlation_cross_lag_evaluation(
    document: Any,
    preregistered_strata: Any,
    aligned_observations: Any,
    *,
    expected_stratum_assignment_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    expected = evaluate_strategy_correlation_cross_lag_gate(
        preregistered_strata,
        aligned_observations,
        expected_stratum_assignment_hash=expected_stratum_assignment_hash,
    )
    return strict_json_contract_equal(document, expected)
