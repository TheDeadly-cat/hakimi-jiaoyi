from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from hakimi_research.cscv_pbo_diagnostic import (
    SCHEMA_VERSION as SOURCE_CSCV_SCHEMA_VERSION,
)
from hakimi_research.trial_return_matrix import (
    TrialReturnMatrixError,
    canonical_trial_return_matrix_sha256,
)


SCHEMA_VERSION = "cscv-pbo-tie-bounds-v1"
RECEIPT_SCHEMA_VERSION = "cscv-pbo-tie-bounds-receipt-v1"
POLICY_SCHEMA_VERSION = "cscv-pbo-tie-bounds-policy-v1"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_CSCV_PBO_TIE_BOUNDS_ONLY"

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_SOURCE_TIE_GAP = "NON_UNIQUE_CSCV_PERFORMANCE_RANK"


class CscvPboTieBoundsError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise CscvPboTieBoundsError(f"{path}: {message}")


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


def _require_canonical(value: Any, path: str) -> None:
    try:
        canonical_trial_return_matrix_sha256(value)
    except TrialReturnMatrixError as exc:
        _fail(path, str(exc))


def cscv_pbo_tie_bounds_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_method": "CSCV_PBO_V1_ALL_70_SYMMETRIC_SPLITS",
        "is_selection_set": "ALL_TRIALS_AT_EXACT_MAXIMUM_IS_PERFORMANCE",
        "oos_rank_lower_formula": "1+COUNT(OOS_SCORE<SELECTED_SCORE)",
        "oos_rank_upper_formula": "COUNT(OOS_SCORE<=SELECTED_SCORE)",
        "selection_tie_aggregation": "MIN_LOWER_RANK_AND_MAX_UPPER_RANK_ACROSS_ALL_IS_MAXIMIZERS",
        "relative_rank_interval": "RANK_BOUND/(TRIAL_COUNT+1)",
        "logit_interval": "MONOTONE_LOGIT_OF_RELATIVE_RANK_INTERVAL",
        "nonpositive_lower_indicator": "TRUE_ONLY_IF_LOGIT_UPPER<=0",
        "nonpositive_upper_indicator": "TRUE_UNLESS_LOGIT_LOWER>0",
        "pbo_lower_bound": "MEAN(NONPOSITIVE_LOWER_INDICATOR)",
        "pbo_upper_bound": "MEAN(NONPOSITIVE_UPPER_INDICATOR)",
        "arbitrary_tie_breaking": False,
        "interval_midpoint_reported_as_pbo": False,
        "split_drop_allowed": False,
        "decision_threshold": None,
        "formal_inference_claimed": False,
        "post_observation_policy_tuning": False,
    }
    return _seal(policy, "policy_sha256")


def _performance(
    value: Any, path: str, expected_trial_count: int
) -> tuple[list[str], list[float]]:
    if type(value) is not list or len(value) != expected_trial_count:
        _fail(path, "must retain one record per preregistered trial")
    trial_ids: list[str] = []
    scores: list[float] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if type(item) is not dict or set(item) != {
            "trial_id",
            "compounded_total_return",
        }:
            _fail(item_path, "shape mismatch")
        trial_id = item["trial_id"]
        decimal = item["compounded_total_return"]
        if type(trial_id) is not str or not trial_id:
            _fail(f"{item_path}.trial_id", "must be an exact non-empty str")
        if type(decimal) is not str or not decimal:
            _fail(
                f"{item_path}.compounded_total_return",
                "must be an exact decimal str",
            )
        try:
            score = float(decimal)
        except ValueError:
            _fail(f"{item_path}.compounded_total_return", "must parse")
        if not math.isfinite(score) or score <= -1.0:
            _fail(
                f"{item_path}.compounded_total_return",
                "must be finite and greater than -1",
            )
        trial_ids.append(trial_id)
        scores.append(score)
    if len(set(trial_ids)) != len(trial_ids):
        _fail(path, "trial ids must be unique")
    return trial_ids, scores


def _split_bounds(
    split: dict[str, Any], *, split_index: int, trial_count: int
) -> dict[str, Any]:
    path = f"splits[{split_index}]"
    if type(split) is not dict:
        _fail(path, "must be an exact dict")
    source_split_sha256 = split.get("split_sha256")
    split_id = split.get("split_id")
    if type(source_split_sha256) is not str or len(source_split_sha256) != 64:
        _fail(f"{path}.split_sha256", "must be a SHA-256")
    if type(split_id) is not str or not split_id:
        _fail(f"{path}.split_id", "must be an exact non-empty str")
    is_ids, is_scores = _performance(
        split.get("is_performance"), f"{path}.is_performance", trial_count
    )
    oos_ids, oos_scores = _performance(
        split.get("oos_performance"), f"{path}.oos_performance", trial_count
    )
    if oos_ids != is_ids:
        _fail(path, "IS and OOS trial order must match")

    maximum_is = max(is_scores)
    selected_indices = [
        index for index, score in enumerate(is_scores) if score == maximum_is
    ]
    candidate_intervals = []
    for selected_index in selected_indices:
        selected_score = oos_scores[selected_index]
        rank_lower = 1 + sum(score < selected_score for score in oos_scores)
        rank_upper = sum(score <= selected_score for score in oos_scores)
        candidate = {
            "trial_id": is_ids[selected_index],
            "selected_is_performance": _decimal(
                is_scores[selected_index],
                f"{path}.selected_is_performance",
            ),
            "selected_oos_performance": _decimal(
                selected_score, f"{path}.selected_oos_performance"
            ),
            "oos_rank_lower": rank_lower,
            "oos_rank_upper": rank_upper,
        }
        candidate_intervals.append(_seal(candidate, "candidate_sha256"))

    rank_lower = min(item["oos_rank_lower"] for item in candidate_intervals)
    rank_upper = max(item["oos_rank_upper"] for item in candidate_intervals)
    relative_lower = rank_lower / (trial_count + 1.0)
    relative_upper = rank_upper / (trial_count + 1.0)
    logit_lower = math.log(relative_lower / (1.0 - relative_lower))
    logit_upper = math.log(relative_upper / (1.0 - relative_upper))
    definitely_nonpositive = logit_upper <= 0.0
    definitely_positive = logit_lower > 0.0
    if definitely_nonpositive:
        classification = "DEFINITELY_NONPOSITIVE"
    elif definitely_positive:
        classification = "DEFINITELY_POSITIVE"
    else:
        classification = "AMBIGUOUS_CROSSES_ZERO"
    point_identified = rank_lower == rank_upper
    if point_identified:
        gaps: list[str] = []
    elif rank_lower == 1 and rank_upper == trial_count:
        gaps = ["TIE_RANK_IDENTIFIED_SET_SPANS_ALL_TRIALS"]
    else:
        gaps = ["TIE_RANK_IDENTIFIED_SET_PARTIAL"]
    record = {
        "schema_version": "cscv-pbo-tie-bounds-split-v1",
        "split_id": split_id,
        "source_split_sha256": source_split_sha256,
        "selected_trial_ids": [
            is_ids[index] for index in selected_indices
        ],
        "selected_trial_count": len(selected_indices),
        "candidate_rank_intervals": candidate_intervals,
        "oos_rank_lower": rank_lower,
        "oos_rank_upper": rank_upper,
        "relative_oos_rank_lower": _decimal(
            relative_lower, f"{path}.relative_oos_rank_lower"
        ),
        "relative_oos_rank_upper": _decimal(
            relative_upper, f"{path}.relative_oos_rank_upper"
        ),
        "logit_lower": _decimal(logit_lower, f"{path}.logit_lower"),
        "logit_upper": _decimal(logit_upper, f"{path}.logit_upper"),
        "nonpositive_lower_indicator": definitely_nonpositive,
        "nonpositive_upper_indicator": not definitely_positive,
        "classification": classification,
        "point_identified": point_identified,
        "evidence_state": (
            "OBSERVED" if point_identified else "OBSERVED_WITH_GAPS"
        ),
        "gaps": gaps,
    }
    return _seal(record, "split_bounds_sha256")


def build_cscv_pbo_tie_bounds(
    source_diagnostic: dict[str, Any],
) -> dict[str, Any]:
    if type(source_diagnostic) is not dict:
        _fail("source_diagnostic", "must be an exact dict")
    _require_canonical(source_diagnostic, "source_diagnostic")
    if source_diagnostic.get("schema_version") != SOURCE_CSCV_SCHEMA_VERSION:
        _fail("source_diagnostic.schema_version", "unexpected source schema")
    source_sha256 = source_diagnostic.get("diagnostic_sha256")
    trial_count = source_diagnostic.get("trial_count")
    combination_count = source_diagnostic.get("combination_count")
    splits = source_diagnostic.get("splits")
    if type(source_sha256) is not str or len(source_sha256) != 64:
        _fail("source_diagnostic.diagnostic_sha256", "must be a SHA-256")
    if type(trial_count) is not int or trial_count < 2:
        _fail("source_diagnostic.trial_count", "must be an exact int >= 2")
    if (
        type(combination_count) is not int
        or type(splits) is not list
        or len(splits) != combination_count
        or combination_count < 1
    ):
        _fail("source_diagnostic.splits", "combination coverage mismatch")

    split_bounds = [
        _split_bounds(split, split_index=index, trial_count=trial_count)
        for index, split in enumerate(splits)
    ]
    definite_nonpositive_count = sum(
        item["nonpositive_lower_indicator"] for item in split_bounds
    )
    possible_nonpositive_count = sum(
        item["nonpositive_upper_indicator"] for item in split_bounds
    )
    ambiguous_count = sum(
        item["classification"] == "AMBIGUOUS_CROSSES_ZERO"
        for item in split_bounds
    )
    definite_positive_count = sum(
        item["classification"] == "DEFINITELY_POSITIVE"
        for item in split_bounds
    )
    point_count = sum(item["point_identified"] for item in split_bounds)
    lower = definite_nonpositive_count / combination_count
    upper = possible_nonpositive_count / combination_count
    width = upper - lower
    if width == 0.0:
        bound_quality = "POINT_IDENTIFIED"
    elif lower == 0.0 and upper == 1.0:
        bound_quality = "FULL_UNIT_INTERVAL"
    else:
        bound_quality = "PARTIAL_IDENTIFIED_SET"

    source_gaps = source_diagnostic.get("gaps")
    if type(source_gaps) is not list or any(
        type(gap) is not str for gap in source_gaps
    ):
        _fail("source_diagnostic.gaps", "must be an exact string list")
    gaps = [gap for gap in source_gaps if gap != _SOURCE_TIE_GAP]
    if width > 0.0:
        gaps.append("TIE_AWARE_PBO_IDENTIFIED_SET_SYNTHETIC_ONLY")
        gaps.append(
            "PBO_IDENTIFIED_SET_FULL_UNIT_INTERVAL"
            if bound_quality == "FULL_UNIT_INTERVAL"
            else "PBO_IDENTIFIED_SET_PARTIAL_INTERVAL"
        )
    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": source_diagnostic["strategy_id"],
        "search_family_id": source_diagnostic["search_family_id"],
        "observation_class": source_diagnostic["observation_class"],
        "source_diagnostic_sha256": source_sha256,
        "source_matrix_record_sha256": source_diagnostic["source_binding"][
            "trial_return_matrix_record_sha256"
        ],
        "policy": cscv_pbo_tie_bounds_policy_v1(),
        "trial_count": trial_count,
        "combination_count": combination_count,
        "retained_split_count": len(split_bounds),
        "point_identified_split_count": point_count,
        "interval_identified_split_count": combination_count - point_count,
        "definite_nonpositive_count": definite_nonpositive_count,
        "possible_nonpositive_count": possible_nonpositive_count,
        "ambiguous_cross_zero_count": ambiguous_count,
        "definite_positive_count": definite_positive_count,
        "pbo_nonpositive_logit_lower_bound": _decimal(
            lower, "pbo_nonpositive_logit_lower_bound"
        ),
        "pbo_nonpositive_logit_upper_bound": _decimal(
            upper, "pbo_nonpositive_logit_upper_bound"
        ),
        "pbo_bound_width": _decimal(width, "pbo_bound_width"),
        "bound_quality": bound_quality,
        "split_bounds": split_bounds,
        "evidence_state": (
            "OBSERVED" if width == 0.0 else "OBSERVED_WITH_GAPS"
        ),
        "status": STATUS,
        "maturity": MATURITY,
        "computed_diagnostics": [
            "ALL_SOURCE_CSCV_SPLITS_RETAINED",
            "IS_MAXIMIZER_SELECTION_SET",
            "OOS_TIE_RANK_IDENTIFIED_SET",
            "PBO_NONPOSITIVE_LOGIT_LOWER_AND_UPPER_BOUNDS",
        ],
        "interpretation": "DESCRIPTIVE_SYNTHETIC_TIE_AWARE_PBO_IDENTIFIED_SET_WITHOUT_POINT_SUBSTITUTION",
        "gaps": gaps,
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(diagnostic, "diagnostic_sha256")


def verify_cscv_pbo_tie_bounds(
    diagnostic: dict[str, Any], source_diagnostic: dict[str, Any]
) -> dict[str, Any]:
    if type(diagnostic) is not dict:
        _fail("diagnostic", "must be an exact dict")
    _require_canonical(diagnostic, "diagnostic")
    expected = build_cscv_pbo_tie_bounds(source_diagnostic)
    if diagnostic != expected:
        _fail("diagnostic", "must match deterministic source-bound bounds")
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": diagnostic["evidence_state"],
        "status": STATUS,
        "maturity": MATURITY,
        "diagnostic_sha256": diagnostic["diagnostic_sha256"],
        "source_diagnostic_sha256": diagnostic["source_diagnostic_sha256"],
        "combination_count": diagnostic["combination_count"],
        "retained_split_count": diagnostic["retained_split_count"],
        "pbo_nonpositive_logit_lower_bound": diagnostic[
            "pbo_nonpositive_logit_lower_bound"
        ],
        "pbo_nonpositive_logit_upper_bound": diagnostic[
            "pbo_nonpositive_logit_upper_bound"
        ],
        "bound_quality": diagnostic["bound_quality"],
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(diagnostic["gaps"]),
        "authority": deepcopy(_AUTHORITY),
    }
