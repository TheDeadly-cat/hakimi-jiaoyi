from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from typing import Any

from .distribution_evidence import verify_distribution_evidence
from .frozen_evaluation import render_frozen_evaluation_markdown


VALIDATION_EVIDENCE_VERSION = "validation-evidence-v1"
VERIFIED_RESEARCH_REPORT_VERSION = "frozen-evaluation-markdown-v2"
REQUIRED_MARKET_REGIMES = ("BULL", "BEAR", "RANGE", "HIGH_VOLATILITY")
FORMAL_SEARCH_LINEAGE_PRODUCER_ID = "strategy_research_search_lineage_v2"

_AUTHORITY_FIELDS = (
    "profitability_proven",
    "blind_test_complete",
    "paper_authorized",
    "live_authorized",
    "order_entry_authorized",
)
_SUPERSEDED_BASE_GAPS = {
    "WALK_FORWARD_NOT_BOUND_TO_ADR0509": "WALK_FORWARD_BOUND_BY_VALIDATION_EVIDENCE_V1",
    "PARAMETER_STABILITY_NOT_BOUND_TO_ADR0509": "PARAMETER_STABILITY_BOUND_BY_VALIDATION_EVIDENCE_V1",
    "MULTIPLE_TESTING_LINEAGE_NOT_BOUND_TO_ADR0509": "MULTIPLE_TESTING_LINEAGE_BOUND_BY_VALIDATION_EVIDENCE_V1",
    "MARKET_REGIME_SLICES_NOT_BOUND_TO_ADR0509": "MARKET_REGIME_SLICES_BOUND_BY_VALIDATION_EVIDENCE_V1",
    "TAIL_AND_DISTRIBUTION_METRICS_NOT_AVAILABLE": "TAIL_AND_DISTRIBUTION_METRICS_BOUND_BY_DISTRIBUTION_EVIDENCE_V1",
}
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")


class ValidationEvidenceError(ValueError):
    """Raised when validation evidence is not exact, canonical, or self-consistent."""


def _fail(path: str, message: str) -> None:
    raise ValidationEvidenceError(f"{path}: {message}")


def _require_exact_native(value: Any, path: str) -> None:
    value_type = type(value)
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail(path, "object keys must be exact str values")
            _require_exact_native(item, f"{path}.{key}")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_native(item, f"{path}[{index}]")
        return
    if value_type in (str, int, bool) or value is None:
        return
    if value_type is float:
        if not math.isfinite(value):
            _fail(path, "float values must be finite")
        return
    _fail(path, f"unsupported non-native type {value_type.__name__}")


def _canonical_json(value: Any, path: str) -> str:
    _require_exact_native(value, path)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _canonical_copy(value: Any, path: str) -> Any:
    return json.loads(_canonical_json(value, path))


def _canonical_sha256(value: Any, path: str) -> str:
    payload = _canonical_json(value, path)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _require_dict(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(path, "must be an exact dict")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        _fail(path, f"key mismatch missing={missing} extra={extra}")
    return value


def _require_list(value: Any, path: str) -> list[Any]:
    if type(value) is not list:
        _fail(path, "must be an exact list")
    return value


def _require_id(value: Any, path: str) -> str:
    if type(value) is not str or _ID_PATTERN.fullmatch(value) is None:
        _fail(path, "must be an exact canonical identifier")
    return value


def _require_text(value: Any, path: str) -> str:
    if type(value) is not str or not value or len(value) > 512:
        _fail(path, "must be a non-empty exact str of at most 512 characters")
    if any(ord(character) < 32 for character in value):
        _fail(path, "must not contain control characters")
    return value


def _require_hash(value: Any, path: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        _fail(path, "must be a lowercase SHA-256 hex digest")
    return value


def _require_decimal(value: Any, path: str, *, nonnegative: bool = False) -> Decimal:
    if type(value) is not str or _DECIMAL_PATTERN.fullmatch(value) is None:
        _fail(path, "must be an exact finite base-10 decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        _fail(path, "must be a finite base-10 decimal string")
    if not parsed.is_finite():
        _fail(path, "must be finite")
    if nonnegative and parsed < 0:
        _fail(path, "must be nonnegative")
    return parsed


def _require_nonnegative_int(value: Any, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(path, "must be an exact nonnegative int")
    return value


def _require_positive_int(value: Any, path: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(path, "must be an exact positive int")
    return value


def _verify_period(value: Any, path: str) -> tuple[int, int]:
    period = _require_dict(value, path, {"start_index", "end_index"})
    start = _require_nonnegative_int(period["start_index"], f"{path}.start_index")
    end = _require_nonnegative_int(period["end_index"], f"{path}.end_index")
    if start > end:
        _fail(path, "start_index must not exceed end_index")
    return start, end


def _verify_trial_outcome(value: Any, path: str) -> tuple[str, str]:
    outcome = _require_dict(
        value,
        path,
        {
            "trial_id",
            "status",
            "result_sha256",
            "failure_code",
            "decision_status",
            "decision_blockers",
        },
    )
    trial_id = _require_id(outcome["trial_id"], f"{path}.trial_id")
    status = _require_id(outcome["status"], f"{path}.status")
    decision_blockers = _require_list(outcome["decision_blockers"], f"{path}.decision_blockers")
    canonical_blockers = [
        _require_text(item, f"{path}.decision_blockers[{index}]")
        for index, item in enumerate(decision_blockers)
    ]
    if canonical_blockers != sorted(canonical_blockers) or len(canonical_blockers) != len(set(canonical_blockers)):
        _fail(f"{path}.decision_blockers", "must be a sorted unique exact-str list")
    if status == "OBSERVED":
        _require_hash(outcome["result_sha256"], f"{path}.result_sha256")
        if outcome["failure_code"] is not None:
            _fail(f"{path}.failure_code", "must be null for OBSERVED")
        _require_id(outcome["decision_status"], f"{path}.decision_status")
    elif status == "FAILED":
        if outcome["result_sha256"] is not None:
            _fail(f"{path}.result_sha256", "must be null for FAILED")
        _require_id(outcome["failure_code"], f"{path}.failure_code")
        if outcome["decision_status"] is not None:
            _fail(f"{path}.decision_status", "must be null for FAILED")
        if canonical_blockers:
            _fail(f"{path}.decision_blockers", "must be empty for FAILED")
    else:
        _fail(f"{path}.status", "must be OBSERVED or FAILED")
    return trial_id, status


def _verify_multiple_testing(value: Any, path: str) -> dict[str, Any]:
    section = _require_dict(
        value,
        path,
        {
            "preregistered_trial_ids",
            "trial_outcomes",
            "selected_parameter_id",
            "selection_rule",
            "producer_report_sha256",
            "ledger_sha256",
        },
    )
    trial_ids = _require_list(section["preregistered_trial_ids"], f"{path}.preregistered_trial_ids")
    canonical_ids = [_require_id(item, f"{path}.preregistered_trial_ids[{index}]") for index, item in enumerate(trial_ids)]
    if not canonical_ids or canonical_ids != sorted(canonical_ids) or len(canonical_ids) != len(set(canonical_ids)):
        _fail(f"{path}.preregistered_trial_ids", "must be a non-empty sorted unique list")

    outcomes = _require_list(section["trial_outcomes"], f"{path}.trial_outcomes")
    outcome_pairs = [
        _verify_trial_outcome(item, f"{path}.trial_outcomes[{index}]")
        for index, item in enumerate(outcomes)
    ]
    outcome_ids = [item[0] for item in outcome_pairs]
    if outcome_ids != canonical_ids:
        _fail(f"{path}.trial_outcomes", "must account for every preregistered trial in canonical order")

    selected_id = _require_id(section["selected_parameter_id"], f"{path}.selected_parameter_id")
    observed_ids = {trial_id for trial_id, status in outcome_pairs if status == "OBSERVED"}
    if selected_id not in observed_ids:
        _fail(f"{path}.selected_parameter_id", "must identify an OBSERVED preregistered trial")
    _require_text(section["selection_rule"], f"{path}.selection_rule")
    producer_report_hash = _require_hash(
        section["producer_report_sha256"],
        f"{path}.producer_report_sha256",
    )
    supplied_ledger_hash = _require_hash(section["ledger_sha256"], f"{path}.ledger_sha256")
    ledger_payload = {
        "preregistered_trial_ids": canonical_ids,
        "trial_outcomes": outcomes,
        "selected_parameter_id": selected_id,
        "selection_rule": section["selection_rule"],
        "producer_report_sha256": producer_report_hash,
    }
    expected_ledger_hash = _canonical_sha256(ledger_payload, f"{path}.ledger_payload")
    if supplied_ledger_hash != expected_ledger_hash:
        _fail(f"{path}.ledger_sha256", "does not match the canonical trial ledger")
    return {
        "trial_ids": set(canonical_ids),
        "observed_ids": observed_ids,
        "observed_count": len(observed_ids),
        "failed_count": len(canonical_ids) - len(observed_ids),
        "selected_parameter_id": selected_id,
    }


def _verify_window(value: Any, path: str, observed_trial_ids: set[str]) -> str:
    window = _require_dict(
        value,
        path,
        {
            "window_id",
            "train",
            "validation",
            "frozen_test",
            "purge_bars",
            "embargo_bars",
            "selected_parameter_id",
            "status",
            "strategy_total_return",
            "benchmark_total_return",
            "strategy_result_sha256",
            "benchmark_result_sha256",
            "failure_code",
        },
    )
    _require_id(window["window_id"], f"{path}.window_id")
    train_start, train_end = _verify_period(window["train"], f"{path}.train")
    validation_start, validation_end = _verify_period(window["validation"], f"{path}.validation")
    frozen_start, _ = _verify_period(window["frozen_test"], f"{path}.frozen_test")
    purge_bars = _require_nonnegative_int(window["purge_bars"], f"{path}.purge_bars")
    embargo_bars = _require_nonnegative_int(window["embargo_bars"], f"{path}.embargo_bars")
    if validation_start - train_end - 1 < purge_bars:
        _fail(path, "train-to-validation gap is smaller than purge_bars")
    if frozen_start - validation_end - 1 < embargo_bars:
        _fail(path, "validation-to-frozen gap is smaller than embargo_bars")
    if train_start >= validation_start or validation_start >= frozen_start:
        _fail(path, "partition starts must be strictly ordered")

    selected_id = _require_id(window["selected_parameter_id"], f"{path}.selected_parameter_id")
    if selected_id not in observed_trial_ids:
        _fail(f"{path}.selected_parameter_id", "must reference an OBSERVED trial")
    status = _require_id(window["status"], f"{path}.status")
    observation_fields = (
        "strategy_total_return",
        "benchmark_total_return",
        "strategy_result_sha256",
        "benchmark_result_sha256",
    )
    if status == "OBSERVED":
        _require_decimal(window["strategy_total_return"], f"{path}.strategy_total_return")
        _require_decimal(window["benchmark_total_return"], f"{path}.benchmark_total_return")
        _require_hash(window["strategy_result_sha256"], f"{path}.strategy_result_sha256")
        _require_hash(window["benchmark_result_sha256"], f"{path}.benchmark_result_sha256")
        if window["failure_code"] is not None:
            _fail(f"{path}.failure_code", "must be null for OBSERVED")
    elif status == "FAILED":
        for field in observation_fields:
            if window[field] is not None:
                _fail(f"{path}.{field}", "must be null for FAILED")
        _require_id(window["failure_code"], f"{path}.failure_code")
    else:
        _fail(f"{path}.status", "must be OBSERVED or FAILED")
    return status


def _verify_walk_forward(value: Any, path: str, observed_trial_ids: set[str]) -> dict[str, int | str]:
    section = _require_dict(value, path, {"windows"})
    windows = _require_list(section["windows"], f"{path}.windows")
    if len(windows) < 2:
        _fail(f"{path}.windows", "walk-forward evidence requires at least two windows")
    statuses = [
        _verify_window(item, f"{path}.windows[{index}]", observed_trial_ids)
        for index, item in enumerate(windows)
    ]
    window_ids = [item["window_id"] for item in windows]
    if len(window_ids) != len(set(window_ids)):
        _fail(f"{path}.windows", "window_id values must be unique")
    canonical_order = sorted(
        windows,
        key=lambda item: (item["frozen_test"]["start_index"], item["window_id"]),
    )
    if windows != canonical_order:
        _fail(f"{path}.windows", "must be ordered by frozen-test start and window_id")
    observed_count = statuses.count("OBSERVED")
    return {
        "state": "OBSERVED" if observed_count == len(windows) else "GAP",
        "observed_count": observed_count,
        "failed_count": len(windows) - observed_count,
    }


def _verify_neighbor(value: Any, path: str, trial_ids: set[str], selected_id: str) -> tuple[str, Decimal | None]:
    neighbor = _require_dict(
        value,
        path,
        {"parameter_id", "distance_fraction", "status", "frozen_excess_return", "result_sha256", "failure_code"},
    )
    parameter_id = _require_id(neighbor["parameter_id"], f"{path}.parameter_id")
    if parameter_id == selected_id or parameter_id not in trial_ids:
        _fail(f"{path}.parameter_id", "must reference a different preregistered trial")
    _require_decimal(neighbor["distance_fraction"], f"{path}.distance_fraction", nonnegative=True)
    status = _require_id(neighbor["status"], f"{path}.status")
    if status == "OBSERVED":
        metric = _require_decimal(neighbor["frozen_excess_return"], f"{path}.frozen_excess_return")
        _require_hash(neighbor["result_sha256"], f"{path}.result_sha256")
        if neighbor["failure_code"] is not None:
            _fail(f"{path}.failure_code", "must be null for OBSERVED")
        return parameter_id, metric
    if status == "FAILED":
        if neighbor["frozen_excess_return"] is not None or neighbor["result_sha256"] is not None:
            _fail(path, "FAILED neighbor observations must be null")
        _require_id(neighbor["failure_code"], f"{path}.failure_code")
        return parameter_id, None
    _fail(f"{path}.status", "must be OBSERVED or FAILED")


def _verify_parameter_stability(
    value: Any,
    path: str,
    trial_ids: set[str],
    observed_trial_ids: set[str],
    selected_parameter_id: str,
) -> dict[str, int | str]:
    section = _require_dict(
        value,
        path,
        {
            "selected_parameter_id",
            "selected_frozen_excess_return",
            "selected_result_sha256",
            "max_abs_degradation",
            "minimum_neighbor_count",
            "minimum_stable_neighbor_count",
            "neighbors",
        },
    )
    selected_id = _require_id(section["selected_parameter_id"], f"{path}.selected_parameter_id")
    if selected_id != selected_parameter_id or selected_id not in observed_trial_ids:
        _fail(f"{path}.selected_parameter_id", "must match the OBSERVED ledger selection")
    selected_metric = _require_decimal(section["selected_frozen_excess_return"], f"{path}.selected_frozen_excess_return")
    _require_hash(section["selected_result_sha256"], f"{path}.selected_result_sha256")
    max_degradation = _require_decimal(section["max_abs_degradation"], f"{path}.max_abs_degradation", nonnegative=True)
    minimum_neighbors = _require_positive_int(section["minimum_neighbor_count"], f"{path}.minimum_neighbor_count")
    minimum_stable = _require_positive_int(section["minimum_stable_neighbor_count"], f"{path}.minimum_stable_neighbor_count")
    neighbors = _require_list(section["neighbors"], f"{path}.neighbors")
    pairs = [
        _verify_neighbor(item, f"{path}.neighbors[{index}]", trial_ids, selected_id)
        for index, item in enumerate(neighbors)
    ]
    neighbor_ids = [item[0] for item in pairs]
    if neighbor_ids != sorted(neighbor_ids) or len(neighbor_ids) != len(set(neighbor_ids)):
        _fail(f"{path}.neighbors", "must be sorted by unique parameter_id")
    if minimum_neighbors > len(neighbors) or minimum_stable > len(neighbors):
        _fail(path, "minimum neighbor thresholds cannot exceed declared neighbors")
    observed_metrics = [metric for _, metric in pairs if metric is not None]
    stable_count = sum(1 for metric in observed_metrics if abs(selected_metric - metric) <= max_degradation)
    state = "OBSERVED" if len(observed_metrics) >= minimum_neighbors and stable_count >= minimum_stable else "GAP"
    return {
        "state": state,
        "observed_count": len(observed_metrics),
        "failed_count": len(neighbors) - len(observed_metrics),
        "stable_count": stable_count,
    }


def _verify_regime_slice(value: Any, path: str, expected_regime: str) -> str:
    item = _require_dict(
        value,
        path,
        {"regime_id", "status", "strategy_total_return", "benchmark_total_return", "observation_sha256", "gap_code"},
    )
    regime_id = _require_id(item["regime_id"], f"{path}.regime_id")
    if regime_id != expected_regime:
        _fail(f"{path}.regime_id", f"expected {expected_regime}")
    status = _require_id(item["status"], f"{path}.status")
    if status == "OBSERVED":
        _require_decimal(item["strategy_total_return"], f"{path}.strategy_total_return")
        _require_decimal(item["benchmark_total_return"], f"{path}.benchmark_total_return")
        _require_hash(item["observation_sha256"], f"{path}.observation_sha256")
        if item["gap_code"] is not None:
            _fail(f"{path}.gap_code", "must be null for OBSERVED")
    elif status == "GAP":
        for field in ("strategy_total_return", "benchmark_total_return", "observation_sha256"):
            if item[field] is not None:
                _fail(f"{path}.{field}", "must be null for GAP")
        _require_id(item["gap_code"], f"{path}.gap_code")
    else:
        _fail(f"{path}.status", "must be OBSERVED or GAP")
    return status


def _verify_market_regimes(value: Any, path: str) -> dict[str, int | str]:
    section = _require_dict(value, path, {"slices"})
    slices = _require_list(section["slices"], f"{path}.slices")
    if len(slices) != len(REQUIRED_MARKET_REGIMES):
        _fail(f"{path}.slices", "must declare every required market regime exactly once")
    statuses = [
        _verify_regime_slice(item, f"{path}.slices[{index}]", regime)
        for index, (item, regime) in enumerate(zip(slices, REQUIRED_MARKET_REGIMES))
    ]
    observed_count = statuses.count("OBSERVED")
    return {
        "state": "OBSERVED" if observed_count == len(REQUIRED_MARKET_REGIMES) else "GAP",
        "observed_count": observed_count,
        "gap_count": len(REQUIRED_MARKET_REGIMES) - observed_count,
    }


def _verify_formal_search_lineage(
    value: Any,
    path: str,
    *,
    expected_current_trial_count: int,
) -> dict[str, int | str]:
    binding = _require_dict(
        value,
        path,
        {
            "producer_id",
            "producer_schema_version",
            "artifact_sha256",
            "lineage_sha256",
            "search_family_id",
            "current_trial_count",
            "cumulative_trial_count",
            "prior_registration_count",
        },
    )
    producer_id = _require_id(binding["producer_id"], f"{path}.producer_id")
    if producer_id != FORMAL_SEARCH_LINEAGE_PRODUCER_ID:
        _fail(f"{path}.producer_id", f"must equal {FORMAL_SEARCH_LINEAGE_PRODUCER_ID}")
    _require_id(binding["producer_schema_version"], f"{path}.producer_schema_version")
    _require_hash(binding["artifact_sha256"], f"{path}.artifact_sha256")
    _require_hash(binding["lineage_sha256"], f"{path}.lineage_sha256")
    _require_id(binding["search_family_id"], f"{path}.search_family_id")
    current_count = _require_positive_int(binding["current_trial_count"], f"{path}.current_trial_count")
    cumulative_count = _require_positive_int(binding["cumulative_trial_count"], f"{path}.cumulative_trial_count")
    prior_count = _require_nonnegative_int(binding["prior_registration_count"], f"{path}.prior_registration_count")
    if current_count != expected_current_trial_count:
        _fail(f"{path}.current_trial_count", "must equal the concrete preregistered trial ledger count")
    if cumulative_count < current_count:
        _fail(f"{path}.cumulative_trial_count", "must include the current trial count")
    return {
        "state": "OBSERVED",
        "current_trial_count": current_count,
        "cumulative_trial_count": cumulative_count,
        "prior_registration_count": prior_count,
    }


def _verify_authority(value: Any, path: str) -> None:
    authority = _require_dict(value, path, set(_AUTHORITY_FIELDS))
    for field in _AUTHORITY_FIELDS:
        if type(authority[field]) is not bool or authority[field] is not False:
            _fail(f"{path}.{field}", "must be exact false")


def _prepare_multiple_testing(value: Any) -> dict[str, Any]:
    section = _canonical_copy(value, "multiple_testing_input")
    _require_dict(
        section,
        "multiple_testing_input",
        {
            "preregistered_trial_ids",
            "trial_outcomes",
            "selected_parameter_id",
            "selection_rule",
            "producer_report_sha256",
        },
    )
    trial_ids = _require_list(section["preregistered_trial_ids"], "multiple_testing_input.preregistered_trial_ids")
    for index, trial_id in enumerate(trial_ids):
        _require_id(trial_id, f"multiple_testing_input.preregistered_trial_ids[{index}]")
    section["preregistered_trial_ids"] = sorted(trial_ids)
    outcomes = _require_list(section["trial_outcomes"], "multiple_testing_input.trial_outcomes")
    for index, outcome in enumerate(outcomes):
        _verify_trial_outcome(outcome, f"multiple_testing_input.trial_outcomes[{index}]")
    section["trial_outcomes"] = sorted(outcomes, key=lambda item: item["trial_id"])
    ledger_payload = {
        "preregistered_trial_ids": section["preregistered_trial_ids"],
        "trial_outcomes": section["trial_outcomes"],
        "selected_parameter_id": section["selected_parameter_id"],
        "selection_rule": section["selection_rule"],
        "producer_report_sha256": section["producer_report_sha256"],
    }
    section["ledger_sha256"] = _canonical_sha256(ledger_payload, "multiple_testing_input.ledger_payload")
    return section


def _prepare_walk_forward(value: Any) -> dict[str, Any]:
    section = _canonical_copy(value, "walk_forward_input")
    _require_dict(section, "walk_forward_input", {"windows"})
    windows = _require_list(section["windows"], "walk_forward_input.windows")
    for index, window in enumerate(windows):
        if type(window) is not dict:
            _fail(f"walk_forward_input.windows[{index}]", "must be an exact dict")
        _verify_period(window.get("frozen_test"), f"walk_forward_input.windows[{index}].frozen_test")
        _require_id(window.get("window_id"), f"walk_forward_input.windows[{index}].window_id")
    section["windows"] = sorted(
        windows,
        key=lambda item: (item["frozen_test"]["start_index"], item["window_id"]),
    )
    return section


def _prepare_parameter_stability(value: Any) -> dict[str, Any]:
    section = _canonical_copy(value, "parameter_stability_input")
    if type(section) is not dict or "neighbors" not in section:
        _fail("parameter_stability_input", "must contain neighbors")
    neighbors = _require_list(section["neighbors"], "parameter_stability_input.neighbors")
    for index, neighbor in enumerate(neighbors):
        if type(neighbor) is not dict:
            _fail(f"parameter_stability_input.neighbors[{index}]", "must be an exact dict")
        _require_id(neighbor.get("parameter_id"), f"parameter_stability_input.neighbors[{index}].parameter_id")
    section["neighbors"] = sorted(neighbors, key=lambda item: item["parameter_id"])
    return section


def _prepare_market_regimes(value: Any) -> dict[str, Any]:
    section = _canonical_copy(value, "market_regimes_input")
    _require_dict(section, "market_regimes_input", {"slices"})
    slices = _require_list(section["slices"], "market_regimes_input.slices")
    order = {regime: index for index, regime in enumerate(REQUIRED_MARKET_REGIMES)}
    for index, item in enumerate(slices):
        if type(item) is not dict:
            _fail(f"market_regimes_input.slices[{index}]", "must be an exact dict")
        regime_id = _require_id(item.get("regime_id"), f"market_regimes_input.slices[{index}].regime_id")
        if regime_id not in order:
            _fail(f"market_regimes_input.slices[{index}].regime_id", "is not a required regime")
    section["slices"] = sorted(slices, key=lambda item: order[item["regime_id"]])
    return section


def build_validation_evidence(
    report: dict[str, Any],
    *,
    experiment_id: str,
    formal_search_lineage: dict[str, Any],
    distribution_evidence: dict[str, Any],
    walk_forward: dict[str, Any],
    parameter_stability: dict[str, Any],
    multiple_testing: dict[str, Any],
    market_regimes: dict[str, Any],
) -> dict[str, Any]:
    """Build a canonical, identity-bound supplemental validation evidence object."""

    _require_exact_native(report, "report")
    _require_id(experiment_id, "experiment_id")
    evidence = {
        "schema_version": VALIDATION_EVIDENCE_VERSION,
        "experiment_id": experiment_id,
        "source_report_sha256": _canonical_sha256(report, "report"),
        "formal_search_lineage": _canonical_copy(formal_search_lineage, "formal_search_lineage_input"),
        "distribution_evidence": _canonical_copy(distribution_evidence, "distribution_evidence_input"),
        "walk_forward": _prepare_walk_forward(walk_forward),
        "parameter_stability": _prepare_parameter_stability(parameter_stability),
        "multiple_testing": _prepare_multiple_testing(multiple_testing),
        "market_regimes": _prepare_market_regimes(market_regimes),
        "authority": {field: False for field in _AUTHORITY_FIELDS},
    }
    evidence["evidence_sha256"] = _canonical_sha256(evidence, "evidence_without_digest")
    verify_validation_evidence(evidence, report)
    return evidence


def verify_validation_evidence(evidence: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Verify exact-native identity, complete lineage, and structural evidence bindings."""

    _require_exact_native(evidence, "evidence")
    _require_exact_native(report, "report")
    value = _require_dict(
        evidence,
        "evidence",
        {
            "schema_version",
            "experiment_id",
            "source_report_sha256",
            "formal_search_lineage",
            "distribution_evidence",
            "walk_forward",
            "parameter_stability",
            "multiple_testing",
            "market_regimes",
            "authority",
            "evidence_sha256",
        },
    )
    if type(value["schema_version"]) is not str or value["schema_version"] != VALIDATION_EVIDENCE_VERSION:
        _fail("evidence.schema_version", f"must equal {VALIDATION_EVIDENCE_VERSION}")
    _require_id(value["experiment_id"], "evidence.experiment_id")
    source_hash = _require_hash(value["source_report_sha256"], "evidence.source_report_sha256")
    if source_hash != _canonical_sha256(report, "report"):
        _fail("evidence.source_report_sha256", "does not identify the supplied ADR0509 report")

    multiple_summary = _verify_multiple_testing(value["multiple_testing"], "evidence.multiple_testing")
    lineage_summary = _verify_formal_search_lineage(
        value["formal_search_lineage"],
        "evidence.formal_search_lineage",
        expected_current_trial_count=len(multiple_summary["trial_ids"]),
    )
    walk_summary = _verify_walk_forward(
        value["walk_forward"],
        "evidence.walk_forward",
        multiple_summary["observed_ids"],
    )
    stability_summary = _verify_parameter_stability(
        value["parameter_stability"],
        "evidence.parameter_stability",
        multiple_summary["trial_ids"],
        multiple_summary["observed_ids"],
        multiple_summary["selected_parameter_id"],
    )
    regime_summary = _verify_market_regimes(value["market_regimes"], "evidence.market_regimes")
    distribution_summary = verify_distribution_evidence(value["distribution_evidence"], report)
    _verify_authority(value["authority"], "evidence.authority")

    supplied_digest = _require_hash(value["evidence_sha256"], "evidence.evidence_sha256")
    digest_payload = {key: item for key, item in value.items() if key != "evidence_sha256"}
    if supplied_digest != _canonical_sha256(digest_payload, "evidence_without_digest"):
        _fail("evidence.evidence_sha256", "does not match canonical evidence")

    gaps = list(distribution_summary["gaps"])
    if walk_summary["state"] == "GAP":
        gaps.append("WALK_FORWARD_WINDOW_OUTCOME_GAP")
    if stability_summary["state"] == "GAP":
        gaps.append("PARAMETER_STABILITY_OUTCOME_GAP")
    if regime_summary["state"] == "GAP":
        gaps.append("MARKET_REGIME_OBSERVATION_GAP")
    return {
        "formal_search_lineage": lineage_summary,
        "walk_forward": walk_summary,
        "parameter_stability": stability_summary,
        "multiple_testing": {
            "state": "OBSERVED",
            "observed_count": multiple_summary["observed_count"],
            "failed_count": multiple_summary["failed_count"],
        },
        "market_regimes": regime_summary,
        "distribution": distribution_summary,
        "gaps": gaps,
        "maturity": "EVIDENCE_GAPS_REMAIN" if gaps else "STRUCTURAL_EVIDENCE_BOUND",
        "permission": "RESEARCH_ONLY",
    }


def _markdown(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _period_text(period: dict[str, int]) -> str:
    return f"{period['start_index']}..{period['end_index']}"


def render_verified_research_markdown(
    report: dict[str, Any],
    protocol: dict[str, Any],
    data: dict[str, Any],
    config: dict[str, Any],
    validation_evidence: dict[str, Any],
    *,
    experiment_context: dict[str, Any],
) -> str:
    """Render ADR0509 plus verified supplemental evidence without activating a runner."""

    summary = verify_validation_evidence(validation_evidence, report)
    base_markdown = render_frozen_evaluation_markdown(
        report,
        protocol,
        data,
        config,
        experiment_context=experiment_context,
    )
    if type(base_markdown) is not str:
        _fail("base_markdown", "ADR0509 renderer must return exact str")
    for old_gap, bound_code in _SUPERSEDED_BASE_GAPS.items():
        if old_gap not in base_markdown:
            _fail("base_markdown", f"missing expected ADR0509 coverage marker {old_gap}")
        base_markdown = base_markdown.replace(old_gap, bound_code)

    evidence = validation_evidence
    formal_lineage = evidence["formal_search_lineage"]
    lines = [
        "# Verified Research Validation Report",
        "",
        f"- report_version: {_markdown(VERIFIED_RESEARCH_REPORT_VERSION)}",
        f"- evidence_version: {_markdown(evidence['schema_version'])}",
        f"- experiment_id: {_markdown(evidence['experiment_id'])}",
        f"- source_report_sha256: {_markdown(evidence['source_report_sha256'])}",
        f"- formal_producer_id: {_markdown(formal_lineage['producer_id'])}",
        f"- formal_producer_schema: {_markdown(formal_lineage['producer_schema_version'])}",
        f"- formal_artifact_sha256: {_markdown(formal_lineage['artifact_sha256'])}",
        f"- formal_lineage_sha256: {_markdown(formal_lineage['lineage_sha256'])}",
        f"- formal_search_family_id: {_markdown(formal_lineage['search_family_id'])}",
        f"- formal_current_trial_count: {formal_lineage['current_trial_count']}",
        f"- formal_cumulative_trial_count: {formal_lineage['cumulative_trial_count']}",
        "",
        "## SOURCE",
        "",
        "ADR0509 base evidence is verified first; supplemental observations are bound by exact-native identities and canonical SHA-256 digests.",
        "",
        "## GAP",
        "",
    ]
    lines.extend(f"- {_markdown(gap)}" for gap in summary["gaps"])
    lines.extend(
        [
            "",
            "## MATURITY",
            "",
            f"- state: {_markdown(summary['maturity'])}",
            "- interpretation: structural research evidence only; observations are not profitability proof.",
            "",
            "## PERMISSION",
            "",
            f"- state: {_markdown(summary['permission'])}",
        ]
    )
    for field in _AUTHORITY_FIELDS:
        lines.append(f"- {field}: false")

    lines.extend(
        [
            "",
            "## Evidence Binding",
            "",
            "| Evidence | Binding | Observation state |",
            "| --- | --- | --- |",
            f"| Formal search-lineage count/history | BOUND | {_markdown(summary['formal_search_lineage']['state'])} |",
            f"| Walk-forward with purge/embargo | BOUND | {_markdown(summary['walk_forward']['state'])} |",
            f"| Parameter stability | BOUND | {_markdown(summary['parameter_stability']['state'])} |",
            f"| Multiple-testing ledger | BOUND | {_markdown(summary['multiple_testing']['state'])} |",
            f"| Market-regime slices | BOUND | {_markdown(summary['market_regimes']['state'])} |",
            f"| Tail and distribution metrics | BOUND | {_markdown(summary['distribution']['state'])} |",
            "",
            "## Walk-Forward Windows",
            "",
            "| Window | Train | Validation | Frozen test | Purge | Embargo | Parameter | State | Strategy return observation | Benchmark return observation | Failure |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for window in evidence["walk_forward"]["windows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown(window["window_id"]),
                    _period_text(window["train"]),
                    _period_text(window["validation"]),
                    _period_text(window["frozen_test"]),
                    str(window["purge_bars"]),
                    str(window["embargo_bars"]),
                    _markdown(window["selected_parameter_id"]),
                    _markdown(window["status"]),
                    _markdown(window["strategy_total_return"]),
                    _markdown(window["benchmark_total_return"]),
                    _markdown(window["failure_code"]),
                ]
            )
            + " |"
        )

    stability = evidence["parameter_stability"]
    lines.extend(
        [
            "",
            "## Parameter Stability",
            "",
            f"- selected_parameter_id: {_markdown(stability['selected_parameter_id'])}",
            f"- selected_frozen_excess_return_observation: {_markdown(stability['selected_frozen_excess_return'])}",
            f"- max_abs_degradation: {_markdown(stability['max_abs_degradation'])}",
            f"- stable_neighbors: {summary['parameter_stability']['stable_count']} / {len(stability['neighbors'])}",
            "",
            "| Parameter | Distance fraction | State | Frozen excess return observation | Failure |",
            "| --- | ---: | --- | ---: | --- |",
        ]
    )
    for neighbor in stability["neighbors"]:
        lines.append(
            f"| {_markdown(neighbor['parameter_id'])} | {_markdown(neighbor['distance_fraction'])} | "
            f"{_markdown(neighbor['status'])} | {_markdown(neighbor['frozen_excess_return'])} | "
            f"{_markdown(neighbor['failure_code'])} |"
        )

    multiplicity = evidence["multiple_testing"]
    lines.extend(
        [
            "",
            "## Multiple-Testing Ledger",
            "",
            f"- selection_rule: {_markdown(multiplicity['selection_rule'])}",
            f"- selected_parameter_id: {_markdown(multiplicity['selected_parameter_id'])}",
            f"- producer_report_sha256: {_markdown(multiplicity['producer_report_sha256'])}",
            f"- ledger_sha256: {_markdown(multiplicity['ledger_sha256'])}",
            "",
            "| Trial | Execution state | Decision | Decision blockers | Result SHA-256 | Failure |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for outcome in multiplicity["trial_outcomes"]:
        lines.append(
            f"| {_markdown(outcome['trial_id'])} | {_markdown(outcome['status'])} | "
            f"{_markdown(outcome['decision_status'])} | "
            f"{_markdown(','.join(outcome['decision_blockers']))} | "
            f"{_markdown(outcome['result_sha256'])} | {_markdown(outcome['failure_code'])} |"
        )

    lines.extend(
        [
            "",
            "## Market-Regime Slices",
            "",
            "| Regime | State | Strategy return observation | Benchmark return observation | Observation SHA-256 | Gap |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for item in evidence["market_regimes"]["slices"]:
        lines.append(
            f"| {_markdown(item['regime_id'])} | {_markdown(item['status'])} | "
            f"{_markdown(item['strategy_total_return'])} | {_markdown(item['benchmark_total_return'])} | "
            f"{_markdown(item['observation_sha256'])} | {_markdown(item['gap_code'])} |"
        )

    distribution = evidence["distribution_evidence"]
    lines.extend(
        [
            "",
            "## Tail and Distribution",
            "",
            f"- status: {_markdown(distribution['status'])}",
            f"- source_result_path: {_markdown(json.dumps(distribution['source_result_path'], ensure_ascii=True, separators=(',', ':')))}",
            f"- source_result_sha256: {_markdown(distribution['source_result_sha256'])}",
            f"- quantile_method: {_markdown(distribution['quantile_method'])}",
            "",
            "| Metric | Observation |",
            "| --- | ---: |",
        ]
    )
    for name, observation in distribution["metrics"].items():
        lines.append(f"| {_markdown(name)} | {_markdown(observation)} |")
    lines.extend(
        [
            "",
            "### Monthly Return Distribution",
            "",
            "| Period | Return observation | Partial start |",
            "| --- | ---: | --- |",
        ]
    )
    for item in distribution["monthly_returns"]:
        lines.append(
            f"| {_markdown(item['period'])} | {_markdown(item['return'])} | "
            f"{str(item['partial_start']).lower()} |"
        )
    lines.extend(
        [
            "",
            "### Yearly Return Distribution",
            "",
            "| Period | Return observation | Partial start |",
            "| --- | ---: | --- |",
        ]
    )
    for item in distribution["yearly_returns"]:
        lines.append(
            f"| {_markdown(item['period'])} | {_markdown(item['return'])} | "
            f"{str(item['partial_start']).lower()} |"
        )
    lines.extend(
        [
            "",
            "### Contribution Concentration",
            "",
            "| Observation | Value |",
            "| --- | ---: |",
        ]
    )
    for name, observation in distribution["concentration"].items():
        lines.append(f"| {_markdown(name)} | {_markdown(observation)} |")

    lines.extend(
        [
            "",
            f"- evidence_sha256: {_markdown(evidence['evidence_sha256'])}",
            "",
            "## ADR0509 Base Report",
            "",
            base_markdown.rstrip(),
            "",
        ]
    )
    rendered = "\n".join(lines)
    if "READY" in rendered:
        _fail("rendered_report", "must not contain READY semantics")
    return rendered


__all__ = [
    "FORMAL_SEARCH_LINEAGE_PRODUCER_ID",
    "REQUIRED_MARKET_REGIMES",
    "VALIDATION_EVIDENCE_VERSION",
    "VERIFIED_RESEARCH_REPORT_VERSION",
    "ValidationEvidenceError",
    "build_validation_evidence",
    "render_verified_research_markdown",
    "verify_validation_evidence",
]
