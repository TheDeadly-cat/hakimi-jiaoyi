from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from hakimi_research.trial_return_matrix import (
    canonical_trial_return_matrix_sha256,
    verify_strategy_trial_return_matrix,
)


SCHEMA_VERSION = "return-contribution-concentration-diagnostic-v1"
RECEIPT_SCHEMA_VERSION = "return-contribution-concentration-diagnostic-receipt-v1"
POLICY_SCHEMA_VERSION = "return-contribution-concentration-policy-v1"
EVIDENCE_STATE = "OBSERVED_WITH_GAPS"
STATUS = "BLOCK"
MATURITY = "SYNTHETIC_RETURN_CONTRIBUTION_CONCENTRATION_DIAGNOSTIC_ONLY"
FIXED_WINDOW_LENGTH = 21

_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
}
_BASE_GAPS = [
    "CALENDAR_MONTH_SYNTHETIC_ONLY",
    "CONCENTRATION_DIAGNOSTIC_WITHOUT_DECISION_THRESHOLD",
    "FORMAL_FROZEN_BLIND_TEST_NOT_EXECUTED",
    "FROZEN_STABILITY_REUSE_NOT_FORMAL_BLIND_EVIDENCE",
    "NO_FORMAL_INFERENCE_AUTHORITY",
    "OPEN_POSITION_UNREALISED_PNL_NOT_ATTRIBUTED_TO_CLOSED_TRADES",
    "REAL_MARKET_DATA_NOT_USED",
    "TRADE_LEDGER_SYNTHETIC_EXECUTION_MODEL_ONLY",
]
_LEGACY_FILL_KEYS = {
    "action",
    "fee",
    "fill_basis",
    "fill_time",
    "pnl",
    "price",
    "quantity",
    "reason",
    "signal_time",
    "symbol",
}
_CAPACITY_FILL_KEYS = _LEGACY_FILL_KEYS | {
    "available_volume",
    "fill_ratio",
    "filled_quantity",
    "max_volume_participation_rate",
    "partial_fill",
    "requested_quantity",
    "volume_capacity_quantity",
}


class ReturnContributionConcentrationError(ValueError):
    pass


def _fail(path: str, message: str) -> None:
    raise ReturnContributionConcentrationError(f"{path}: {message}")


def _seal(record: dict[str, Any], field: str) -> dict[str, Any]:
    if field in record:
        _fail(field, "duplicate seal field")
    record[field] = canonical_trial_return_matrix_sha256(record)
    return record


def _decimal(value: float, path: str) -> str:
    if type(value) is not float or not math.isfinite(value):
        _fail(path, "must be a finite exact float")
    if value == 0.0:
        return "0"
    return format(value, ".17g")


def _number(value: Any, path: str) -> float:
    if type(value) not in (int, float):
        _fail(path, "must be an exact non-bool number")
    numeric = float(value)
    if not math.isfinite(numeric):
        _fail(path, "must be finite")
    return numeric


def _compound(values: list[float], path: str) -> float:
    if type(values) is not list or not values:
        _fail(path, "must contain at least one return")
    growth = 1.0
    for index, value in enumerate(values):
        if type(value) is not float or not math.isfinite(value) or value <= -1.0:
            _fail(f"{path}[{index}]", "must be a finite exact float greater than -1")
        growth *= 1.0 + value
        if not math.isfinite(growth) or growth <= 0.0:
            _fail(path, "produced invalid compounded growth")
    return growth - 1.0


def _parse_returns(row: dict[str, Any]) -> list[float]:
    values = row.get("period_returns")
    if type(values) is not list or len(values) < FIXED_WINDOW_LENGTH + 1:
        _fail(
            "selected_row.period_returns",
            f"must contain more than {FIXED_WINDOW_LENGTH} decimal strings",
        )
    output: list[float] = []
    for index, value in enumerate(values):
        if type(value) is not str or not value:
            _fail(
                f"selected_row.period_returns[{index}]",
                "must be an exact decimal str",
            )
        try:
            numeric = float(value)
        except ValueError:
            _fail(f"selected_row.period_returns[{index}]", "must parse as decimal")
        if not math.isfinite(numeric) or numeric <= -1.0:
            _fail(
                f"selected_row.period_returns[{index}]",
                "must be finite and greater than -1",
            )
        output.append(numeric)
    return output


def _month_id(timestamp: Any, path: str) -> str:
    if type(timestamp) is not str or not timestamp:
        _fail(path, "must be a non-empty exact timestamp str")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        _fail(path, "must be an ISO-8601 timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "must contain an explicit UTC offset")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m")


def _positive_contribution(values: list[float], *, label: str) -> dict[str, Any]:
    positives = [value for value in values if value > 0.0]
    if not positives:
        return _seal(
            {
                "label": label,
                "state": "GAP",
                "positive_count": 0,
                "positive_total": None,
                "largest_positive_share": None,
                "herfindahl_hirschman_index": None,
                "gap_code": f"NO_POSITIVE_{label}_CONTRIBUTION",
            },
            "concentration_sha256",
        )
    total = math.fsum(positives)
    shares = [value / total for value in positives]
    return _seal(
        {
            "label": label,
            "state": "OBSERVED",
            "positive_count": len(positives),
            "positive_total": _decimal(total, f"{label}.positive_total"),
            "largest_positive_share": _decimal(
                max(shares), f"{label}.largest_positive_share"
            ),
            "herfindahl_hirschman_index": _decimal(
                math.fsum(share**2 for share in shares),
                f"{label}.herfindahl_hirschman_index",
            ),
            "gap_code": None,
        },
        "concentration_sha256",
    )


def return_contribution_concentration_policy_v1() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "source_trial_policy": "PREREGISTERED_SELECTED_CENTER_ONLY",
        "source_phase": "FROZEN_STABILITY",
        "period_return_convention": "SOURCE_MATRIX_SIMPLE_NET_RETURNS",
        "compounded_return_formula": "PRODUCT(1+R_T)-1",
        "best_observation_selection": "MAX_SIMPLE_RETURN_EARLIEST_INDEX_TIE_BREAK",
        "calendar_month_timezone": "UTC",
        "calendar_month_return": "COMPOUNDED_SOURCE_PERIOD_RETURNS",
        "best_calendar_month_selection": "MAX_COMPOUNDED_RETURN_EARLIEST_MONTH_TIE_BREAK",
        "best_calendar_month_removal": "REMOVE_ALL_SOURCE_OBSERVATIONS_IN_SELECTED_UTC_MONTH",
        "fixed_window_length": FIXED_WINDOW_LENGTH,
        "fixed_window_candidates": "ALL_CONTIGUOUS_EQUAL_LENGTH_WINDOWS",
        "best_fixed_window_selection": "MAX_COMPOUNDED_RETURN_EARLIEST_START_INDEX_TIE_BREAK",
        "closed_trade_universe": "SOURCE_RESULT_SELL_FILLS",
        "closed_trade_contribution": "SOURCE_FILL_REALISED_PNL_AFTER_ENTRY_AND_EXIT_FEES",
        "best_closed_trade_selection": "MAX_REALISED_PNL_EARLIEST_SOURCE_FILL_INDEX_TIE_BREAK",
        "positive_contribution_formula": "SHARE_I=POSITIVE_I/SUM_POSITIVE;HHI=SUM(SHARE_I^2)",
        "open_position_policy": "NOT_ATTRIBUTED_TO_CLOSED_TRADE_PNL",
        "performance_selection_performed": False,
        "post_observation_policy_tuning": False,
        "decision_threshold": None,
        "formal_inference_claimed": False,
    }
    return _seal(policy, "policy_sha256")


def _calendar_month_records(
    times: list[str], returns: list[float]
) -> list[dict[str, Any]]:
    groups: list[tuple[str, list[int]]] = []
    for index, timestamp in enumerate(times):
        month = _month_id(timestamp, f"observation_times[{index}]")
        if not groups or groups[-1][0] != month:
            groups.append((month, []))
        groups[-1][1].append(index)
    records: list[dict[str, Any]] = []
    for month, indices in groups:
        month_return = _compound(
            [returns[index] for index in indices], f"calendar_month.{month}"
        )
        records.append(
            _seal(
                {
                    "month_id": month,
                    "start_index": indices[0],
                    "end_index_inclusive": indices[-1],
                    "start_time": times[indices[0]],
                    "end_time": times[indices[-1]],
                    "observation_count": len(indices),
                    "compounded_return": _decimal(
                        month_return, f"calendar_month.{month}.compounded_return"
                    ),
                },
                "month_record_sha256",
            )
        )
    if len(records) < 2:
        _fail("calendar_month_records", "requires at least two UTC months")
    return records


def _best_fixed_window(
    times: list[str], returns: list[float]
) -> dict[str, Any]:
    candidate_count = len(returns) - FIXED_WINDOW_LENGTH + 1
    if candidate_count <= 0:
        _fail("fixed_window", "source is shorter than the fixed window")
    best_start = 0
    best_return = _compound(
        returns[:FIXED_WINDOW_LENGTH], "fixed_window.candidates[0]"
    )
    for start in range(1, candidate_count):
        candidate_return = _compound(
            returns[start : start + FIXED_WINDOW_LENGTH],
            f"fixed_window.candidates[{start}]",
        )
        if candidate_return > best_return:
            best_start = start
            best_return = candidate_return
    end_exclusive = best_start + FIXED_WINDOW_LENGTH
    without = returns[:best_start] + returns[end_exclusive:]
    return _seal(
        {
            "window_length": FIXED_WINDOW_LENGTH,
            "candidate_count": candidate_count,
            "start_index": best_start,
            "end_index_inclusive": end_exclusive - 1,
            "start_time": times[best_start],
            "end_time": times[end_exclusive - 1],
            "compounded_return": _decimal(
                best_return, "best_fixed_window.compounded_return"
            ),
            "full_return_without_best_window": _decimal(
                _compound(without, "best_fixed_window.without"),
                "best_fixed_window.full_return_without_best_window",
            ),
        },
        "window_record_sha256",
    )


def _numbers_match(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _validate_capacity_fill(
    fill: dict[str, Any], *, path: str, quantity: float
) -> None:
    requested = _number(fill["requested_quantity"], f"{path}.requested_quantity")
    filled = _number(fill["filled_quantity"], f"{path}.filled_quantity")
    ratio = _number(fill["fill_ratio"], f"{path}.fill_ratio")
    if requested <= 0.0 or filled <= 0.0:
        _fail(path, "requested/filled quantity boundary invalid")
    if filled > requested and not _numbers_match(filled, requested):
        _fail(f"{path}.filled_quantity", "must not exceed requested quantity")
    if not _numbers_match(filled, quantity):
        _fail(f"{path}.filled_quantity", "must equal fill quantity")
    expected_ratio = filled / requested
    if ratio <= 0.0 or ratio > 1.0 or not _numbers_match(ratio, expected_ratio):
        _fail(f"{path}.fill_ratio", "must equal filled/requested quantity")

    partial = fill["partial_fill"]
    if type(partial) is not bool:
        _fail(f"{path}.partial_fill", "must be an exact bool")
    expected_partial = filled < requested - 1e-12
    if partial is not expected_partial:
        _fail(f"{path}.partial_fill", "must match the quantity boundary")

    available_raw = fill["available_volume"]
    available = (
        None
        if available_raw is None
        else _number(available_raw, f"{path}.available_volume")
    )
    if available is not None and available < 0.0:
        _fail(f"{path}.available_volume", "must be non-negative")

    participation_raw = fill["max_volume_participation_rate"]
    participation = (
        None
        if participation_raw is None
        else _number(
            participation_raw,
            f"{path}.max_volume_participation_rate",
        )
    )
    if participation is not None and not 0.0 < participation <= 1.0:
        _fail(
            f"{path}.max_volume_participation_rate",
            "must be in (0, 1]",
        )

    capacity_raw = fill["volume_capacity_quantity"]
    if available is None or participation is None:
        if capacity_raw is not None:
            _fail(
                f"{path}.volume_capacity_quantity",
                "must be null without both capacity inputs",
            )
        return

    capacity = _number(capacity_raw, f"{path}.volume_capacity_quantity")
    expected_capacity = available * participation
    if capacity < 0.0 or not _numbers_match(capacity, expected_capacity):
        _fail(
            f"{path}.volume_capacity_quantity",
            "must equal available volume times participation rate",
        )
    if filled > capacity and not _numbers_match(filled, capacity):
        _fail(f"{path}.filled_quantity", "must not exceed volume capacity")


def _closed_trade_records(result: dict[str, Any]) -> list[dict[str, Any]]:
    fills = result.get("fills")
    if type(fills) is not list:
        _fail("selected_result.fills", "must be an exact list")
    trade_count = result.get("trades")
    if type(trade_count) is not int or trade_count != len(fills):
        _fail("selected_result.trades", "must equal the exact fill count")
    records: list[dict[str, Any]] = []
    for index, fill in enumerate(fills):
        path = f"selected_result.fills[{index}]"
        if type(fill) is not dict:
            _fail(path, "fill shape mismatch")
        fill_keys = set(fill)
        if fill_keys not in (_LEGACY_FILL_KEYS, _CAPACITY_FILL_KEYS):
            _fail(path, "fill shape mismatch")
        action = fill["action"]
        if type(action) is not str or action not in {"BUY", "SELL"}:
            _fail(f"{path}.action", "must be exact BUY or SELL")
        for field in ("symbol", "reason", "signal_time", "fill_time", "fill_basis"):
            if type(fill[field]) is not str:
                _fail(f"{path}.{field}", "must be an exact str")
        quantity = _number(fill["quantity"], f"{path}.quantity")
        price = _number(fill["price"], f"{path}.price")
        fee = _number(fill["fee"], f"{path}.fee")
        pnl = _number(fill["pnl"], f"{path}.pnl")
        if quantity <= 0.0 or price <= 0.0 or fee < 0.0:
            _fail(path, "quantity/price/fee boundary invalid")
        if fill_keys == _CAPACITY_FILL_KEYS:
            _validate_capacity_fill(fill, path=path, quantity=quantity)
        if action == "BUY" and pnl != 0.0:
            _fail(f"{path}.pnl", "BUY fill realised PnL must be zero")
        if action == "SELL":
            records.append(
                _seal(
                    {
                        "source_fill_index": index,
                        "fill_time": fill["fill_time"],
                        "quantity": _decimal(quantity, f"{path}.quantity"),
                        "price": _decimal(price, f"{path}.price"),
                        "fee": _decimal(fee, f"{path}.fee"),
                        "realised_pnl": _decimal(pnl, f"{path}.pnl"),
                        "source_fill_sha256": canonical_trial_return_matrix_sha256(
                            fill
                        ),
                    },
                    "trade_record_sha256",
                )
            )
    return records


def build_return_contribution_concentration_diagnostic(
    trial_return_matrix: dict[str, Any],
) -> dict[str, Any]:
    try:
        receipt = verify_strategy_trial_return_matrix(trial_return_matrix)
    except Exception as exc:
        _fail(
            "trial_return_matrix",
            f"verification failed:{type(exc).__name__}:{exc}",
        )
    if receipt.get("state") != "OBSERVED":
        _fail("trial_return_matrix", "must contain observed aligned candidates")

    selected_trial_id = trial_return_matrix["selected_trial_id"]
    selected_index = trial_return_matrix["preregistered_trial_ids"].index(
        selected_trial_id
    )
    selected_row = trial_return_matrix["candidate_rows"][selected_index]
    if selected_row["trial_id"] != selected_trial_id:
        _fail("selected_row.trial_id", "selected source order drifted")
    returns = _parse_returns(selected_row)
    times = trial_return_matrix["observation_times"]
    if type(times) is not list or len(times) != len(returns):
        _fail("observation_times", "must align exactly with selected returns")

    total_return = _compound(returns, "selected_returns")
    best_observation_index = max(range(len(returns)), key=lambda index: returns[index])
    without_best_observation = (
        returns[:best_observation_index] + returns[best_observation_index + 1 :]
    )
    best_observation = _seal(
        {
            "index": best_observation_index,
            "time": times[best_observation_index],
            "simple_return": _decimal(
                returns[best_observation_index], "best_observation.simple_return"
            ),
            "full_return_without_best_observation": _decimal(
                _compound(without_best_observation, "best_observation.without"),
                "best_observation.full_return_without_best_observation",
            ),
        },
        "observation_record_sha256",
    )

    month_records = _calendar_month_records(times, returns)
    best_month = max(
        month_records, key=lambda record: float(record["compounded_return"])
    )
    best_month_id = best_month["month_id"]
    returns_without_best_month = [
        value
        for index, value in enumerate(returns)
        if _month_id(times[index], f"observation_times[{index}]") != best_month_id
    ]
    best_calendar_month = _seal(
        {
            "month_id": best_month_id,
            "source_month_record_sha256": best_month["month_record_sha256"],
            "observation_count": best_month["observation_count"],
            "compounded_return": best_month["compounded_return"],
            "full_return_without_best_calendar_month": _decimal(
                _compound(returns_without_best_month, "best_calendar_month.without"),
                "best_calendar_month.full_return_without_best_calendar_month",
            ),
        },
        "calendar_month_record_sha256",
    )

    best_window = _best_fixed_window(times, returns)
    period_concentration = _positive_contribution(
        returns, label="PERIOD_RETURN"
    )
    result = selected_row["source_run"]["result"]
    closed_trade_records = _closed_trade_records(result)
    closed_trade_pnls = [
        float(record["realised_pnl"]) for record in closed_trade_records
    ]
    trade_concentration = _positive_contribution(
        closed_trade_pnls, label="CLOSED_TRADE_PNL"
    )
    gaps = list(_BASE_GAPS)
    if period_concentration["gap_code"] is not None:
        gaps.append(period_concentration["gap_code"])
    if not closed_trade_records:
        best_closed_trade = None
        closed_trade_pnl_total = None
        closed_trade_pnl_without_best = None
        closed_trade_state = "GAP"
        gaps.append("NO_CLOSED_SELL_FILL_FOR_TRADE_SENSITIVITY")
    else:
        best_closed_trade = max(
            closed_trade_records,
            key=lambda record: float(record["realised_pnl"]),
        )
        total_closed_pnl = math.fsum(closed_trade_pnls)
        best_closed_pnl = float(best_closed_trade["realised_pnl"])
        closed_trade_pnl_total = _decimal(
            total_closed_pnl, "closed_trade_pnl_total"
        )
        closed_trade_pnl_without_best = _decimal(
            total_closed_pnl - best_closed_pnl,
            "closed_trade_pnl_without_best",
        )
        closed_trade_state = "OBSERVED"
    if trade_concentration["gap_code"] is not None:
        gaps.append(trade_concentration["gap_code"])

    source_binding = {
        "trial_return_matrix_record_sha256": trial_return_matrix["record_sha256"],
        "matrix_sha256": trial_return_matrix["matrix_sha256"],
        "observation_times_sha256": trial_return_matrix[
            "observation_times_sha256"
        ],
        "selected_row_sha256": selected_row["row_sha256"],
        "selected_period_returns_sha256": selected_row["period_returns_sha256"],
        "selected_source_run_sha256": selected_row["source_run"]["run_sha256"],
        "selected_source_result_sha256": selected_row["source_run"][
            "result_sha256"
        ],
        "selected_fills_sha256": canonical_trial_return_matrix_sha256(
            result["fills"]
        ),
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
        "policy": return_contribution_concentration_policy_v1(),
        "source_binding": source_binding,
        "selected_trial_id": selected_trial_id,
        "selection_rule": trial_return_matrix["selection_rule"],
        "observation_count": len(returns),
        "selected_compounded_return": _decimal(
            total_return, "selected_compounded_return"
        ),
        "best_observation": best_observation,
        "positive_period_return_concentration": period_concentration,
        "calendar_month_count": len(month_records),
        "calendar_month_records": month_records,
        "best_calendar_month": best_calendar_month,
        "best_fixed_window": best_window,
        "closed_trade_evidence_state": closed_trade_state,
        "closed_trade_count": len(closed_trade_records),
        "closed_trade_records": closed_trade_records,
        "closed_trade_pnl_total": closed_trade_pnl_total,
        "best_closed_trade": deepcopy(best_closed_trade),
        "closed_trade_pnl_without_best": closed_trade_pnl_without_best,
        "positive_closed_trade_pnl_concentration": trade_concentration,
        "interpretation": "DESCRIPTIVE_SYNTHETIC_SENSITIVITY_WITHOUT_DECISION_THRESHOLD",
        "computed_diagnostics": [
            "BEST_SINGLE_PERIOD_REMOVAL",
            "BEST_UTC_CALENDAR_MONTH_REMOVAL",
            "BEST_CONTIGUOUS_21_PERIOD_WINDOW_REMOVAL",
            "POSITIVE_PERIOD_RETURN_HHI",
            "BEST_CLOSED_SELL_FILL_PNL_REMOVAL",
            "POSITIVE_CLOSED_TRADE_PNL_HHI_WHEN_AVAILABLE",
        ],
        "gaps": gaps,
        "authority": dict(_AUTHORITY),
    }
    return _seal(diagnostic, "diagnostic_sha256")


def verify_return_contribution_concentration_diagnostic(
    diagnostic: dict[str, Any],
    trial_return_matrix: dict[str, Any],
) -> dict[str, Any]:
    if type(diagnostic) is not dict:
        _fail("diagnostic", "must be an exact dict")
    canonical_trial_return_matrix_sha256(diagnostic)
    expected = build_return_contribution_concentration_diagnostic(
        trial_return_matrix
    )
    if diagnostic != expected:
        _fail(
            "diagnostic",
            "must match deterministic source-bound concentration diagnostic",
        )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "state": EVIDENCE_STATE,
        "status": STATUS,
        "maturity": MATURITY,
        "diagnostic_sha256": diagnostic["diagnostic_sha256"],
        "selected_trial_id": diagnostic["selected_trial_id"],
        "observation_count": diagnostic["observation_count"],
        "calendar_month_count": diagnostic["calendar_month_count"],
        "fixed_window_candidate_count": diagnostic["best_fixed_window"][
            "candidate_count"
        ],
        "closed_trade_count": diagnostic["closed_trade_count"],
        "closed_trade_evidence_state": diagnostic[
            "closed_trade_evidence_state"
        ],
        "positive_closed_trade_concentration_state": diagnostic[
            "positive_closed_trade_pnl_concentration"
        ]["state"],
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "gaps": list(diagnostic["gaps"]),
        "authority": dict(_AUTHORITY),
    }
