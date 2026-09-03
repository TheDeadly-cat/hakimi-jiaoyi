from __future__ import annotations

import math
from copy import deepcopy
from statistics import NormalDist
from typing import Any

from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
    verify_strategy_trial_return_matrix,
)


SCHEMA_VERSION = "deflated-sharpe-diagnostic-v1"
RECEIPT_SCHEMA_VERSION = "deflated-sharpe-diagnostic-receipt-v1"
POLICY_SCHEMA_VERSION = "deflated-sharpe-policy-v1"
EVIDENCE_STATE = "OBSERVED"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_DEFLATED_SHARPE_DIAGNOSTIC_ONLY"
EULER_MASCHERONI = 0.5772156649015329

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "PROBABILITY_OF_BACKTEST_OVERFITTING_NOT_COMPUTED",
    "REAL_MARKET_DATA_NOT_USED",
    "THREE_TRIAL_SYNTHETIC_DIAGNOSTIC_ONLY",
]


class DeflatedSharpeDiagnosticError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise DeflatedSharpeDiagnosticError(f"{path}: {message}")


def _decimal(value: float, path: str) -> str:
    if type(value) is not float or not math.isfinite(value):
        _fail(path, "must be a finite exact float")
    if value == 0.0:
        return "0"
    return format(value, ".17g")


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def deflated_sharpe_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "method_source": "BAILEY_LOPEZ_DE_PRADO_2014_DEFLATED_SHARPE_RATIO",
        "candidate_sharpe_estimator": "NON_ANNUALISED_SAMPLE_MEAN_OVER_SAMPLE_STDDEV_DDOF_1",
        "candidate_sharpe_dispersion": "SAMPLE_VARIANCE_ACROSS_ALL_PREREGISTERED_TRIALS_DDOF_1",
        "selected_return_skewness": "POPULATION_STANDARDISED_THIRD_CENTRAL_MOMENT",
        "selected_return_kurtosis": "POPULATION_PEARSON_NON_EXCESS_FOURTH_CENTRAL_MOMENT",
        "trial_dependence": "EQUAL_WEIGHTED_AVERAGE_PAIRWISE_PEARSON_CORRELATION",
        "implied_independent_trials_formula": "N=RHO_BAR+(1-RHO_BAR)*M",
        "expected_maximum_formula": "SR0=SD(SR_TRIALS)*((1-GAMMA)*PHI_INV(1-1/N)+GAMMA*PHI_INV(1-1/(N*E)))",
        "deflated_sharpe_formula": "DSR=PHI((SR_SELECTED-SR0)*SQRT(T-1)/SQRT(1-SKEW*SR_SELECTED+((KURTOSIS-1)/4)*SR_SELECTED^2))",
        "euler_mascheroni": format(EULER_MASCHERONI, ".17g"),
        "normal_distribution": "STANDARD_NORMAL_STATISTICS_NORMALDIST",
        "annualisation_usage": "DISPLAY_ONLY_NOT_USED_IN_DSR_PROBABILITY",
        "decision_threshold": None,
        "formal_inference_claimed": False,
        "performance_selection_performed": False,
        "post_observation_policy_tuning": False,
    }
    return _seal(policy, "policy_sha256")


def _parse_returns(row: dict[str, Any], path: str) -> list[float]:
    values = row.get("period_returns")
    if type(values) is not list or len(values) < 3:
        _fail(path, "must contain at least three exact decimal strings")
    output: list[float] = []
    for index, value in enumerate(values):
        if type(value) is not str or not value:
            _fail(f"{path}[{index}]", "must be an exact decimal str")
        try:
            numeric = float(value)
        except ValueError:
            _fail(f"{path}[{index}]", "must parse as a decimal")
        if not math.isfinite(numeric):
            _fail(f"{path}[{index}]", "must be finite")
        output.append(numeric)
    return output


def _mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def _sample_variance(values: list[float], path: str) -> float:
    if len(values) < 2:
        _fail(path, "requires at least two observations")
    center = _mean(values)
    variance = math.fsum((value - center) ** 2 for value in values) / (
        len(values) - 1
    )
    if not math.isfinite(variance) or variance <= 0.0:
        _fail(path, "must have positive finite sample variance")
    return variance


def _moments(values: list[float], path: str) -> tuple[float, float]:
    center = _mean(values)
    deviations = [value - center for value in values]
    second = math.fsum(value**2 for value in deviations) / len(values)
    if not math.isfinite(second) or second <= 0.0:
        _fail(path, "selected returns must have positive variance")
    third = math.fsum(value**3 for value in deviations) / len(values)
    fourth = math.fsum(value**4 for value in deviations) / len(values)
    skewness = third / (second**1.5)
    kurtosis = fourth / (second**2)
    if not math.isfinite(skewness) or not math.isfinite(kurtosis):
        _fail(path, "selected moments must be finite")
    return skewness, kurtosis


def _pearson(left: list[float], right: list[float], path: str) -> float:
    if len(left) != len(right) or len(left) < 2:
        _fail(path, "requires aligned samples")
    left_mean = _mean(left)
    right_mean = _mean(right)
    left_deviations = [value - left_mean for value in left]
    right_deviations = [value - right_mean for value in right]
    denominator = math.sqrt(
        math.fsum(value**2 for value in left_deviations)
        * math.fsum(value**2 for value in right_deviations)
    )
    if not math.isfinite(denominator) or denominator <= 0.0:
        _fail(path, "requires positive candidate variance")
    correlation = math.fsum(
        left_value * right_value
        for left_value, right_value in zip(left_deviations, right_deviations)
    ) / denominator
    if not math.isfinite(correlation):
        _fail(path, "correlation must be finite")
    return max(-1.0, min(1.0, correlation))


def _trial_statistics(
    trial_id: str,
    row: dict[str, Any],
    returns: list[float],
    periods_per_year: int,
) -> dict[str, Any]:
    average = _mean(returns)
    variance = _sample_variance(returns, f"{trial_id}.returns")
    standard_deviation = math.sqrt(variance)
    sharpe = average / standard_deviation
    skewness, kurtosis = _moments(returns, f"{trial_id}.returns")
    statistics = {
        "trial_id": trial_id,
        "source_row_sha256": row["row_sha256"],
        "observation_count": len(returns),
        "mean_return": _decimal(average, f"{trial_id}.mean_return"),
        "sample_standard_deviation": _decimal(
            standard_deviation, f"{trial_id}.sample_standard_deviation"
        ),
        "non_annualised_sharpe_ratio": _decimal(
            sharpe, f"{trial_id}.non_annualised_sharpe_ratio"
        ),
        "annualised_sharpe_ratio_display_only": _decimal(
            sharpe * math.sqrt(periods_per_year),
            f"{trial_id}.annualised_sharpe_ratio_display_only",
        ),
        "skewness": _decimal(skewness, f"{trial_id}.skewness"),
        "pearson_kurtosis": _decimal(kurtosis, f"{trial_id}.pearson_kurtosis"),
    }
    return _seal(statistics, "statistics_sha256")


def build_deflated_sharpe_diagnostic(
    trial_return_matrix: dict[str, Any],
) -> dict[str, Any]:
    try:
        matrix_receipt = verify_strategy_trial_return_matrix(trial_return_matrix)
    except Exception as exc:
        _fail(
            "trial_return_matrix",
            f"verification failed:{type(exc).__name__}:{exc}",
        )
    if matrix_receipt.get("state") != "OBSERVED":
        _fail("trial_return_matrix", "must contain observed aligned candidates")
    policy = deflated_sharpe_policy_v1()
    trial_ids = trial_return_matrix["preregistered_trial_ids"]
    rows = trial_return_matrix["candidate_rows"]
    periods_per_year = trial_return_matrix["periods_per_year"]
    returns_by_trial: dict[str, list[float]] = {}
    trial_statistics: list[dict[str, Any]] = []
    for index, trial_id in enumerate(trial_ids):
        returns = _parse_returns(
            rows[index], f"trial_return_matrix.candidate_rows[{index}].period_returns"
        )
        returns_by_trial[trial_id] = returns
        trial_statistics.append(
            _trial_statistics(trial_id, rows[index], returns, periods_per_year)
        )

    pairwise_correlations: list[dict[str, Any]] = []
    correlation_values: list[float] = []
    for left_index in range(len(trial_ids)):
        for right_index in range(left_index + 1, len(trial_ids)):
            left_id = trial_ids[left_index]
            right_id = trial_ids[right_index]
            correlation = _pearson(
                returns_by_trial[left_id],
                returns_by_trial[right_id],
                f"pairwise_correlation.{left_id}.{right_id}",
            )
            correlation_values.append(correlation)
            pairwise_correlations.append(
                _seal(
                    {
                        "left_trial_id": left_id,
                        "right_trial_id": right_id,
                        "pearson_correlation": _decimal(
                            correlation,
                            f"pairwise_correlation.{left_id}.{right_id}",
                        ),
                    },
                    "correlation_sha256",
                )
            )
    if not correlation_values:
        _fail("pairwise_correlations", "requires at least two trials")
    average_correlation = _mean(correlation_values)
    trial_count = len(trial_ids)
    lower_correlation_bound = -1.0 / (trial_count - 1)
    if average_correlation < lower_correlation_bound - 1e-12:
        _fail("average_pairwise_correlation", "violates correlation-matrix bound")
    effective_trial_count = average_correlation + (
        1.0 - average_correlation
    ) * trial_count
    if not math.isfinite(effective_trial_count) or effective_trial_count <= 1.0:
        _fail("effective_independent_trial_count", "must exceed one")

    candidate_sharpes = [
        float(item["non_annualised_sharpe_ratio"])
        for item in trial_statistics
    ]
    candidate_sharpe_variance = _sample_variance(
        candidate_sharpes, "candidate_sharpe_ratios"
    )
    candidate_sharpe_standard_deviation = math.sqrt(candidate_sharpe_variance)
    normal = NormalDist()
    first_probability = 1.0 - (1.0 / effective_trial_count)
    second_probability = 1.0 - (
        1.0 / (effective_trial_count * math.e)
    )
    if not (0.0 < first_probability < 1.0 and 0.0 < second_probability < 1.0):
        _fail("effective_independent_trial_count", "produced invalid normal quantiles")
    expected_maximum_sharpe = candidate_sharpe_standard_deviation * (
        (1.0 - EULER_MASCHERONI) * normal.inv_cdf(first_probability)
        + EULER_MASCHERONI * normal.inv_cdf(second_probability)
    )

    selected_trial_id = trial_return_matrix["selected_trial_id"]
    selected_index = trial_ids.index(selected_trial_id)
    selected_statistics = trial_statistics[selected_index]
    selected_sharpe = float(selected_statistics["non_annualised_sharpe_ratio"])
    selected_skewness = float(selected_statistics["skewness"])
    selected_kurtosis = float(selected_statistics["pearson_kurtosis"])
    observation_count = selected_statistics["observation_count"]
    non_normality_adjustment = (
        1.0
        - selected_skewness * selected_sharpe
        + ((selected_kurtosis - 1.0) / 4.0) * selected_sharpe**2
    )
    if not math.isfinite(non_normality_adjustment) or non_normality_adjustment <= 0.0:
        _fail("non_normality_adjustment", "must be positive and finite")
    test_statistic = (
        (selected_sharpe - expected_maximum_sharpe)
        * math.sqrt(observation_count - 1)
        / math.sqrt(non_normality_adjustment)
    )
    probability = normal.cdf(test_statistic)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        _fail("deflated_sharpe_probability", "must be a finite probability")

    source_binding = {
        "trial_return_matrix_record_sha256": trial_return_matrix["record_sha256"],
        "matrix_sha256": trial_return_matrix["matrix_sha256"],
        "observation_times_sha256": trial_return_matrix[
            "observation_times_sha256"
        ],
        "candidate_row_sha256s": [row["row_sha256"] for row in rows],
        "source_robustness_bundle_sha256": trial_return_matrix["source_binding"][
            "source_robustness_bundle_sha256"
        ],
    }
    _seal(source_binding, "source_binding_sha256")
    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": trial_return_matrix["strategy_id"],
        "search_family_id": trial_return_matrix["search_family_id"],
        "observation_class": trial_return_matrix["observation_class"],
        "evidence_state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "policy": policy,
        "source_binding": source_binding,
        "selected_trial_id": selected_trial_id,
        "selection_rule": trial_return_matrix["selection_rule"],
        "trial_count": trial_count,
        "observation_count": observation_count,
        "periods_per_year": periods_per_year,
        "trial_statistics": trial_statistics,
        "pairwise_correlations": pairwise_correlations,
        "average_pairwise_correlation": _decimal(
            average_correlation, "average_pairwise_correlation"
        ),
        "effective_independent_trial_count": _decimal(
            effective_trial_count, "effective_independent_trial_count"
        ),
        "candidate_sharpe_variance": _decimal(
            candidate_sharpe_variance, "candidate_sharpe_variance"
        ),
        "candidate_sharpe_standard_deviation": _decimal(
            candidate_sharpe_standard_deviation,
            "candidate_sharpe_standard_deviation",
        ),
        "expected_maximum_non_annualised_sharpe": _decimal(
            expected_maximum_sharpe,
            "expected_maximum_non_annualised_sharpe",
        ),
        "expected_maximum_annualised_sharpe_display_only": _decimal(
            expected_maximum_sharpe * math.sqrt(periods_per_year),
            "expected_maximum_annualised_sharpe_display_only",
        ),
        "selected_non_normality_adjustment": _decimal(
            non_normality_adjustment, "selected_non_normality_adjustment"
        ),
        "deflated_sharpe_test_statistic": _decimal(
            test_statistic, "deflated_sharpe_test_statistic"
        ),
        "deflated_sharpe_probability": _decimal(
            probability, "deflated_sharpe_probability"
        ),
        "interpretation": "DESCRIPTIVE_SYNTHETIC_DIAGNOSTIC_WITHOUT_DECISION_THRESHOLD",
        "computed_diagnostics": [
            "CANDIDATE_SHARPE_DISPERSION",
            "IMPLIED_INDEPENDENT_TRIAL_COUNT",
            "NON_NORMALITY_ADJUSTED_DEFLATED_SHARPE_PROBABILITY",
        ],
        "gaps": list(_GAPS),
        "authority": dict(_AUTHORITY),
    }
    return _seal(diagnostic, "diagnostic_sha256")


def verify_deflated_sharpe_diagnostic(
    diagnostic: dict[str, Any], trial_return_matrix: dict[str, Any]
) -> dict[str, Any]:
    if type(diagnostic) is not dict:
        _fail("diagnostic", "must be an exact dict")
    canonical_trial_return_matrix_sha256(diagnostic)
    expected = build_deflated_sharpe_diagnostic(trial_return_matrix)
    if diagnostic != expected:
        _fail("diagnostic", "must match deterministic source-bound DSR diagnostic")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "diagnostic_sha256": diagnostic["diagnostic_sha256"],
        "selected_trial_id": diagnostic["selected_trial_id"],
        "trial_count": diagnostic["trial_count"],
        "observation_count": diagnostic["observation_count"],
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(_GAPS),
        "authority": dict(_AUTHORITY),
    }
