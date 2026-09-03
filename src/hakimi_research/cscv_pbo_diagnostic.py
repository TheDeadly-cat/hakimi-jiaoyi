from __future__ import annotations

import itertools
import math
from copy import deepcopy
from typing import Any

from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
    verify_strategy_trial_return_matrix,
)


SCHEMA_VERSION = "cscv-pbo-diagnostic-v1"
RECEIPT_SCHEMA_VERSION = "cscv-pbo-diagnostic-receipt-v1"
POLICY_SCHEMA_VERSION = "cscv-pbo-policy-v1"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_CSCV_PBO_DIAGNOSTIC_ONLY"
PARTITION_COUNT = 8

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_BASE_GAPS = [
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "ODD_THREE_TRIAL_MEDIAN_BOUNDARY_SENSITIVITY",
    "REAL_MARKET_DATA_NOT_USED",
    "THREE_TRIAL_RANK_RESOLUTION_LIMIT",
    "TRAILING_OBSERVATION_EXCLUDED_FOR_EQUAL_CSCV_PARTITIONS",
]
_TIE_GAP = "NON_UNIQUE_CSCV_PERFORMANCE_RANK"


class CscvPboDiagnosticError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise CscvPboDiagnosticError(f"{path}: {message}")


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


def cscv_pbo_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "method_source": "BAILEY_BORWEIN_LOPEZ_DE_PRADO_ZHU_2015_CSCV_PBO",
        "partition_count": PARTITION_COUNT,
        "partition_count_must_be_even": True,
        "partition_shape": "CONTIGUOUS_EQUAL_LENGTH_ORIGINAL_ORDER",
        "usable_observation_policy": "LARGEST_CHRONOLOGICAL_PREFIX_DIVISIBLE_BY_PARTITION_COUNT",
        "excluded_observation_policy": "TRAILING_OBSERVATIONS_EXPLICITLY_RETAINED_AND_HASH_BOUND",
        "is_partition_count": PARTITION_COUNT // 2,
        "oos_partition_count": PARTITION_COUNT // 2,
        "combination_policy": "ALL_BINOMIAL_S_CHOOSE_S_OVER_2_INCLUDING_COMPLEMENTS",
        "expected_combination_count": math.comb(
            PARTITION_COUNT, PARTITION_COUNT // 2
        ),
        "performance_metric": "COMPOUNDED_SIMPLE_TOTAL_RETURN",
        "performance_metric_binding": "MATCHES_EXISTING_VALIDATION_TOTAL_RETURN_SELECTION_FAMILY",
        "performance_tie_policy": "GAP_NO_ARBITRARY_RANK_NO_SPLIT_DROP",
        "is_selection_rule": "UNIQUE_MAXIMUM_PERFORMANCE",
        "oos_rank_rule": "ASCENDING_ONE_IS_WORST_N_IS_BEST",
        "relative_rank_formula": "OMEGA=OOS_RANK/(N+1)",
        "logit_formula": "LAMBDA=LN(OMEGA/(1-OMEGA))",
        "pbo_primary_boundary": "NONPOSITIVE_LOGIT_INCLUSIVE_ZERO",
        "strict_below_median_sensitivity": "OOS_RANK<(N+1)/2",
        "decision_threshold": None,
        "formal_inference_claimed": False,
        "post_observation_policy_tuning": False,
    }
    return _seal(policy, "policy_sha256")


def _parse_returns(row: dict[str, Any], path: str) -> list[float]:
    values = row.get("period_returns")
    if type(values) is not list:
        _fail(path, "must be an exact list")
    output: list[float] = []
    for index, value in enumerate(values):
        if type(value) is not str or not value:
            _fail(f"{path}[{index}]", "must be an exact decimal str")
        try:
            numeric = float(value)
        except ValueError:
            _fail(f"{path}[{index}]", "must parse as a decimal")
        if not math.isfinite(numeric) or numeric <= -1.0:
            _fail(f"{path}[{index}]", "must be finite and greater than -1")
        output.append(numeric)
    return output


def _compounded_total_return(values: list[float], indices: list[int]) -> float:
    total = math.expm1(math.fsum(math.log1p(values[index]) for index in indices))
    if not math.isfinite(total):
        _fail("performance", "compounded total return must be finite")
    return total


def _tie_groups(
    trial_ids: list[str], scores: list[float]
) -> list[list[str]]:
    groups: dict[float, list[str]] = {}
    for trial_id, score in zip(trial_ids, scores):
        groups.setdefault(score, []).append(trial_id)
    return sorted(
        [sorted(group) for group in groups.values() if len(group) > 1],
        key=lambda group: tuple(group),
    )


def _partition_records(
    observation_times: list[str], partition_size: int
) -> list[dict[str, Any]]:
    partitions = []
    for index in range(PARTITION_COUNT):
        start = index * partition_size
        end = start + partition_size
        times = observation_times[start:end]
        partition = {
            "partition_id": f"partition-{index + 1:02d}",
            "partition_index": index,
            "start_observation_index": start,
            "end_observation_index_inclusive": end - 1,
            "observation_count": len(times),
            "start_time": times[0],
            "end_time": times[-1],
            "observation_times_sha256": canonical_trial_return_matrix_sha256(
                times
            ),
        }
        partitions.append(_seal(partition, "partition_sha256"))
    return partitions


def _excluded_observations(
    trial_return_matrix: dict[str, Any], usable_count: int
) -> list[dict[str, Any]]:
    times = trial_return_matrix["observation_times"]
    rows = trial_return_matrix["candidate_rows"]
    output = []
    for index in range(usable_count, len(times)):
        item = {
            "source_observation_index": index,
            "time": times[index],
            "trial_returns": [
                {
                    "trial_id": row["trial_id"],
                    "period_return": row["period_returns"][index],
                }
                for row in rows
            ],
        }
        output.append(_seal(item, "excluded_observation_sha256"))
    return output


def _performance_records(
    trial_ids: list[str], scores: list[float], side: str
) -> list[dict[str, Any]]:
    return [
        {
            "trial_id": trial_id,
            "compounded_total_return": _decimal(
                score, f"{side}_performance.{trial_id}"
            ),
        }
        for trial_id, score in zip(trial_ids, scores)
    ]


def _split_record(
    *,
    split_index: int,
    is_partition_indices: tuple[int, ...],
    partition_size: int,
    trial_ids: list[str],
    returns_by_trial: dict[str, list[float]],
) -> dict[str, Any]:
    is_partition_set = set(is_partition_indices)
    oos_partition_indices = tuple(
        index for index in range(PARTITION_COUNT) if index not in is_partition_set
    )
    is_indices = [
        observation_index
        for partition_index in is_partition_indices
        for observation_index in range(
            partition_index * partition_size,
            (partition_index + 1) * partition_size,
        )
    ]
    oos_indices = [
        observation_index
        for partition_index in oos_partition_indices
        for observation_index in range(
            partition_index * partition_size,
            (partition_index + 1) * partition_size,
        )
    ]
    is_scores = [
        _compounded_total_return(returns_by_trial[trial_id], is_indices)
        for trial_id in trial_ids
    ]
    oos_scores = [
        _compounded_total_return(returns_by_trial[trial_id], oos_indices)
        for trial_id in trial_ids
    ]
    is_ties = _tie_groups(trial_ids, is_scores)
    oos_ties = _tie_groups(trial_ids, oos_scores)
    record: dict[str, Any] = {
        "split_id": f"cscv-{split_index + 1:03d}",
        "is_partition_ids": [
            f"partition-{index + 1:02d}" for index in is_partition_indices
        ],
        "oos_partition_ids": [
            f"partition-{index + 1:02d}" for index in oos_partition_indices
        ],
        "is_observation_count": len(is_indices),
        "oos_observation_count": len(oos_indices),
        "is_performance": _performance_records(trial_ids, is_scores, "is"),
        "oos_performance": _performance_records(trial_ids, oos_scores, "oos"),
        "is_tie_groups": is_ties,
        "oos_tie_groups": oos_ties,
    }
    if is_ties or oos_ties:
        record.update(
            {
                "state": "GAP",
                "gap_code": _TIE_GAP,
                "selected_trial_id": None,
                "selected_is_performance": None,
                "selected_oos_performance": None,
                "selected_oos_rank": None,
                "relative_oos_rank": None,
                "logit": None,
                "nonpositive_logit": None,
                "strictly_below_median": None,
            }
        )
        return _seal(record, "split_sha256")

    selected_index = max(range(len(trial_ids)), key=lambda index: is_scores[index])
    selected_trial_id = trial_ids[selected_index]
    ordered_oos = sorted(range(len(trial_ids)), key=lambda index: oos_scores[index])
    selected_oos_rank = ordered_oos.index(selected_index) + 1
    relative_rank = selected_oos_rank / (len(trial_ids) + 1.0)
    logit = math.log(relative_rank / (1.0 - relative_rank))
    record.update(
        {
            "state": "OBSERVED",
            "gap_code": None,
            "selected_trial_id": selected_trial_id,
            "selected_is_performance": _decimal(
                is_scores[selected_index], "selected_is_performance"
            ),
            "selected_oos_performance": _decimal(
                oos_scores[selected_index], "selected_oos_performance"
            ),
            "selected_oos_rank": selected_oos_rank,
            "relative_oos_rank": _decimal(relative_rank, "relative_oos_rank"),
            "logit": _decimal(logit, "logit"),
            "nonpositive_logit": logit <= 0.0,
            "strictly_below_median": selected_oos_rank
            < (len(trial_ids) + 1.0) / 2.0,
        }
    )
    return _seal(record, "split_sha256")


def build_cscv_pbo_diagnostic(
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
    policy = cscv_pbo_policy_v1()
    trial_ids = trial_return_matrix["preregistered_trial_ids"]
    observation_count = trial_return_matrix["observation_count"]
    usable_count = observation_count - (observation_count % PARTITION_COUNT)
    if usable_count < PARTITION_COUNT * 2:
        _fail("trial_return_matrix", "insufficient observations for eight CSCV partitions")
    partition_size = usable_count // PARTITION_COUNT
    usable_times = trial_return_matrix["observation_times"][:usable_count]
    returns_by_trial = {
        row["trial_id"]: _parse_returns(
            row, f"candidate_rows[{index}].period_returns"
        )[:usable_count]
        for index, row in enumerate(trial_return_matrix["candidate_rows"])
    }
    partitions = _partition_records(usable_times, partition_size)
    excluded = _excluded_observations(trial_return_matrix, usable_count)
    combinations = list(
        itertools.combinations(range(PARTITION_COUNT), PARTITION_COUNT // 2)
    )
    if len(combinations) != policy["expected_combination_count"]:
        _fail("combinations", "count drifted")
    splits = [
        _split_record(
            split_index=index,
            is_partition_indices=combination,
            partition_size=partition_size,
            trial_ids=trial_ids,
            returns_by_trial=returns_by_trial,
        )
        for index, combination in enumerate(combinations)
    ]
    gap_split_count = sum(split["state"] == "GAP" for split in splits)
    observed_split_count = len(splits) - gap_split_count
    evidence_state = "OBSERVED" if gap_split_count == 0 else "GAP"
    if evidence_state == "OBSERVED":
        nonpositive_count = sum(split["nonpositive_logit"] for split in splits)
        strict_count = sum(split["strictly_below_median"] for split in splits)
        median_count = sum(
            split["selected_oos_rank"] == (len(trial_ids) + 1) / 2
            for split in splits
        )
        pbo_rate = _decimal(nonpositive_count / len(splits), "pbo_rate")
        strict_rate = _decimal(strict_count / len(splits), "strict_rate")
        median_rate = _decimal(median_count / len(splits), "median_rate")
        logit_distribution_sha256 = canonical_trial_return_matrix_sha256(
            [split["logit"] for split in splits]
        )
    else:
        nonpositive_count = None
        strict_count = None
        median_count = None
        pbo_rate = None
        strict_rate = None
        median_rate = None
        logit_distribution_sha256 = None

    gaps = list(_BASE_GAPS)
    if gap_split_count:
        gaps.append(_TIE_GAP)
    source_binding = {
        "trial_return_matrix_record_sha256": trial_return_matrix["record_sha256"],
        "matrix_sha256": trial_return_matrix["matrix_sha256"],
        "observation_times_sha256": trial_return_matrix[
            "observation_times_sha256"
        ],
        "candidate_row_sha256s": [
            row["row_sha256"] for row in trial_return_matrix["candidate_rows"]
        ],
        "usable_observation_times_sha256": canonical_trial_return_matrix_sha256(
            usable_times
        ),
        "excluded_observations_sha256": canonical_trial_return_matrix_sha256(
            excluded
        ),
    }
    _seal(source_binding, "source_binding_sha256")
    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": trial_return_matrix["strategy_id"],
        "search_family_id": trial_return_matrix["search_family_id"],
        "observation_class": trial_return_matrix["observation_class"],
        "evidence_state": evidence_state,
        "status": STATUS,
        "maturity": MATURITY,
        "policy": policy,
        "source_binding": source_binding,
        "trial_count": len(trial_ids),
        "source_observation_count": observation_count,
        "usable_observation_count": usable_count,
        "excluded_observation_count": len(excluded),
        "partition_count": PARTITION_COUNT,
        "partition_size": partition_size,
        "combination_count": len(combinations),
        "observed_split_count": observed_split_count,
        "gap_split_count": gap_split_count,
        "partitions": partitions,
        "excluded_observations": excluded,
        "splits": splits,
        "nonpositive_logit_count": nonpositive_count,
        "strict_below_median_count": strict_count,
        "median_rank_count": median_count,
        "pbo_nonpositive_logit_rate": pbo_rate,
        "strict_below_median_rate": strict_rate,
        "median_rank_rate": median_rate,
        "logit_distribution_sha256": logit_distribution_sha256,
        "interpretation": "DESCRIPTIVE_SYNTHETIC_CSCV_DIAGNOSTIC_WITHOUT_DECISION_THRESHOLD",
        "computed_diagnostics": [
            "ALL_SYMMETRIC_CSCV_SPLITS_RETAINED",
            "PBO_NONPOSITIVE_LOGIT_RATE"
            if evidence_state == "OBSERVED"
            else "PBO_UNIDENTIFIABLE_DUE_TO_RANK_TIES",
        ],
        "gaps": gaps,
        "authority": dict(_AUTHORITY),
    }
    return _seal(diagnostic, "diagnostic_sha256")


def verify_cscv_pbo_diagnostic(
    diagnostic: dict[str, Any], trial_return_matrix: dict[str, Any]
) -> dict[str, Any]:
    if type(diagnostic) is not dict:
        _fail("diagnostic", "must be an exact dict")
    canonical_trial_return_matrix_sha256(diagnostic)
    expected = build_cscv_pbo_diagnostic(trial_return_matrix)
    if diagnostic != expected:
        _fail("diagnostic", "must match deterministic source-bound CSCV diagnostic")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": diagnostic["evidence_state"],
        "status": STATUS,
        "maturity": MATURITY,
        "diagnostic_sha256": diagnostic["diagnostic_sha256"],
        "trial_count": diagnostic["trial_count"],
        "usable_observation_count": diagnostic["usable_observation_count"],
        "excluded_observation_count": diagnostic["excluded_observation_count"],
        "combination_count": diagnostic["combination_count"],
        "observed_split_count": diagnostic["observed_split_count"],
        "gap_split_count": diagnostic["gap_split_count"],
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(diagnostic["gaps"]),
        "authority": deepcopy(_AUTHORITY),
    }
