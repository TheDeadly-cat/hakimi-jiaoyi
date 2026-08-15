from __future__ import annotations

import math
from typing import Any, Callable

from .execution_authority import authority_violations
from .strategy_frozen_evaluation_replay import (
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION,
)
from .strategy_research import (
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
)


STRATEGY_POST_SELECTION_REPLAY_SUMMARY_SCHEMA_VERSION = (
    "strategy-post-selection-replay-summary-v1"
)
POST_SELECTION_REPLAY_SUMMARY_REPORT_SCHEMA_VERSIONS = frozenset({11, 12, 13, 14})

_STAGE_FIELDS = {
    "stage",
    "status",
    "candidate_count",
    "result_count",
    "cell_count",
    "replay_verified_cell_count",
    "replay_pass_cell_count",
    "aggregate_pass_candidate_count",
    "minimum_configured_return_pct",
    "minimum_excess_return_pct",
    "minimum_severe_cost_return_pct",
    "worst_drawdown_pct",
    "total_trades",
    "fixed_slice_pass_cell_count",
    "prefix_invariance_pass_cell_count",
    "lookahead_pass_cell_count",
    "blockers",
}


def _sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _native_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _clean_strategy_id(value: Any) -> str:
    return str(value or "").strip().lower()


def _clean_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _empty_stage(stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": "NOT_RUN",
        "candidate_count": 0,
        "result_count": 0,
        "cell_count": 0,
        "replay_verified_cell_count": 0,
        "replay_pass_cell_count": 0,
        "aggregate_pass_candidate_count": 0,
        "minimum_configured_return_pct": None,
        "minimum_excess_return_pct": None,
        "minimum_severe_cost_return_pct": None,
        "worst_drawdown_pct": None,
        "total_trades": None,
        "fixed_slice_pass_cell_count": 0,
        "prefix_invariance_pass_cell_count": 0,
        "lookahead_pass_cell_count": 0,
        "blockers": [],
    }


def _stage_summary(
    *,
    stage: str,
    strategy_id: str,
    candidates: list[dict[str, Any]],
    results: list[dict[str, Any]],
    cells: list[dict[str, Any]],
    required_symbols: list[str],
    aggregate: Callable[..., dict[str, Any]],
    input_types_valid: bool,
) -> dict[str, Any]:
    """Build a deliberately stricter replay-preservation view than the formal gate.

    A formal aggregate may tolerate a bounded number of outcome-blocked cells.  This
    public summary calls the stage PASS only when every independently verified replay
    and every corresponding aggregate is PASS.  It never changes the formal report.
    """

    if input_types_valid and not candidates and not results and not cells:
        return _empty_stage(stage)

    blockers: list[str] = []
    candidate_ids = [str(item.get("variant_id") or "") for item in candidates]
    result_ids = [str(item.get("variant_id") or "") for item in results]
    symbol_scope = [_clean_symbol(item) for item in required_symbols]
    candidate_contract_valid = (
        input_types_valid
        and
        bool(candidates)
        and all(isinstance(item, dict) for item in candidates)
        and all(
            isinstance(item.get("variant_id"), str)
            and bool(str(item.get("variant_id") or "").strip())
            for item in candidates
        )
        and len(set(candidate_ids)) == len(candidate_ids)
        and all(_clean_strategy_id(item.get("strategy_id")) == strategy_id for item in candidates)
    )
    result_contract_valid = (
        input_types_valid
        and
        len(results) == len(candidates)
        and all(isinstance(item, dict) for item in results)
        and all(
            isinstance(item.get("variant_id"), str)
            and bool(str(item.get("variant_id") or "").strip())
            for item in results
        )
        and len(set(result_ids)) == len(result_ids)
        and set(result_ids) == set(candidate_ids)
        and all(_clean_strategy_id(item.get("strategy_id")) == strategy_id for item in results)
    )
    symbol_scope_valid = (
        bool(symbol_scope)
        and all(
            isinstance(item, str) and bool(item.strip())
            for item in required_symbols
        )
        and len(set(symbol_scope)) == len(symbol_scope)
    )
    if not candidate_contract_valid:
        blockers.append("post_selection_candidate_contract_invalid")
    if not result_contract_valid:
        blockers.append("post_selection_result_contract_invalid")
    if not symbol_scope_valid:
        blockers.append("post_selection_symbol_scope_invalid")

    cell_keys: list[tuple[str, str]] = []
    cell_identity_valid = all(isinstance(item, dict) for item in cells)
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        variant_id = str(cell.get("variant_id") or "")
        symbol = _clean_symbol(cell.get("symbol"))
        cell_keys.append((variant_id, symbol))
        if (
            cell.get("phase") != stage
            or not isinstance(cell.get("variant_id"), str)
            or not isinstance(cell.get("symbol"), str)
            or _clean_strategy_id(cell.get("strategy_id")) != strategy_id
            or variant_id not in set(candidate_ids)
        ):
            cell_identity_valid = False
    expected_keys = {
        (variant_id, symbol)
        for variant_id in candidate_ids
        for symbol in symbol_scope
    }
    coverage_valid = (
        candidate_contract_valid
        and symbol_scope_valid
        and cell_identity_valid
        and len(set(cell_keys)) == len(cell_keys)
        and set(cell_keys) == expected_keys
    )
    if not coverage_valid:
        blockers.append("post_selection_cell_coverage_not_preserved")

    replay_verified = 0
    replay_pass = 0
    replay_structure_valid = True
    configured_returns: list[float] = []
    excess_returns: list[float] = []
    severe_returns: list[float] = []
    drawdowns: list[float] = []
    trades: list[int] = []
    fixed_slice_pass = 0
    prefix_pass = 0
    lookahead_pass = 0
    for cell in cells:
        replay = cell.get("frozen_evaluation_replay") if isinstance(cell, dict) else None
        if not isinstance(replay, dict):
            replay_structure_valid = False
            continue
        if (
            replay.get("schema_version")
            != STRATEGY_FROZEN_EVALUATION_REPLAY_SCHEMA_VERSION
            or replay.get("role") != stage
        ):
            replay_structure_valid = False
        if replay.get("verification_status") == "PASS":
            replay_verified += 1
        else:
            replay_structure_valid = False
        if replay.get("status") == "PASS":
            replay_pass += 1

        configured = replay.get("configured_run")
        configured = configured if isinstance(configured, dict) else {}
        configured_result = configured.get("result_projection")
        configured_result = configured_result if isinstance(configured_result, dict) else {}
        severe = replay.get("severe_cost_run")
        severe = severe if isinstance(severe, dict) else {}
        severe_result = severe.get("result_projection")
        severe_result = severe_result if isinstance(severe_result, dict) else {}
        flat = replay.get("flat_metric_projection")
        flat = flat if isinstance(flat, dict) else {}
        configured_return = _finite(configured_result.get("total_return_pct"))
        excess_return = _finite(flat.get("test_excess_return_pct"))
        severe_return = _finite(severe_result.get("total_return_pct"))
        drawdown = _finite(configured_result.get("max_drawdown_pct"))
        trade_count = _native_nonnegative_int(configured_result.get("trade_count"))
        if None in (configured_return, excess_return, severe_return, drawdown) or trade_count is None:
            replay_structure_valid = False
        else:
            configured_returns.append(configured_return)
            excess_returns.append(excess_return)
            severe_returns.append(severe_return)
            drawdowns.append(drawdown)
            trades.append(trade_count)

        if stage == HOLDOUT_CONFIRMATION_ROLE:
            fixed = replay.get("fixed_slice_evidence")
            prefix = replay.get("prefix_invariance")
            lookahead = replay.get("lookahead")
            fixed_slice_pass += int(isinstance(fixed, dict) and fixed.get("status") == "PASS")
            prefix_pass += int(isinstance(prefix, dict) and prefix.get("status") == "PASS")
            lookahead_pass += int(isinstance(lookahead, dict) and lookahead.get("status") == "PASS")
            if not all(isinstance(item, dict) for item in (fixed, prefix, lookahead)):
                replay_structure_valid = False

    if not replay_structure_valid or replay_verified != len(cells):
        blockers.append("post_selection_replay_integrity_not_preserved")

    aggregate_valid = candidate_contract_valid and result_contract_valid and coverage_valid
    aggregate_pass_count = 0
    result_by_id = {
        str(item.get("variant_id") or ""): item
        for item in results
        if isinstance(item, dict)
    }
    if aggregate_valid:
        for candidate in candidates:
            variant_id = str(candidate.get("variant_id") or "")
            candidate_cells = [
                cell for cell in cells
                if isinstance(cell, dict) and str(cell.get("variant_id") or "") == variant_id
            ]
            try:
                rebuilt = aggregate(
                    candidate,
                    candidate_cells,
                    required_symbols=len(symbol_scope),
                )
                if stage == HOLDOUT_CONFIRMATION_ROLE:
                    rebuilt.update({
                        "variant_id": candidate.get("variant_id"),
                        "params": candidate.get("params"),
                        "param_hash": candidate.get("param_hash"),
                    })
            except (TypeError, ValueError, KeyError, OverflowError):
                rebuilt = {}
            reported = result_by_id.get(variant_id)
            if not isinstance(reported, dict) or rebuilt != reported:
                aggregate_valid = False
                break
            aggregate_pass_count += int(rebuilt.get("status") == "PASS")
    if not aggregate_valid:
        blockers.append("post_selection_aggregate_semantics_not_preserved")

    integrity_valid = (
        candidate_contract_valid
        and result_contract_valid
        and symbol_scope_valid
        and coverage_valid
        and replay_structure_valid
        and replay_verified == len(cells)
        and aggregate_valid
    )
    holdout_audits_pass = (
        stage != HOLDOUT_CONFIRMATION_ROLE
        or (
            fixed_slice_pass == len(cells)
            and prefix_pass == len(cells)
            and lookahead_pass == len(cells)
        )
    )
    outcome_pass = (
        integrity_valid
        and replay_pass == len(cells)
        and aggregate_pass_count == len(candidates)
        and holdout_audits_pass
    )
    if integrity_valid and not outcome_pass:
        blockers.append("post_selection_replay_outcome_not_preserved")

    metrics_available = integrity_valid and len(configured_returns) == len(cells)
    result = {
        "stage": stage,
        "status": "PASS" if outcome_pass else "BLOCK",
        "candidate_count": len(candidates),
        "result_count": len(results),
        "cell_count": len(cells),
        "replay_verified_cell_count": replay_verified,
        "replay_pass_cell_count": replay_pass,
        "aggregate_pass_candidate_count": aggregate_pass_count,
        "minimum_configured_return_pct": min(configured_returns) if metrics_available else None,
        "minimum_excess_return_pct": min(excess_returns) if metrics_available else None,
        "minimum_severe_cost_return_pct": min(severe_returns) if metrics_available else None,
        "worst_drawdown_pct": max(drawdowns) if metrics_available else None,
        "total_trades": sum(trades) if metrics_available else None,
        "fixed_slice_pass_cell_count": fixed_slice_pass if integrity_valid else 0,
        "prefix_invariance_pass_cell_count": prefix_pass if integrity_valid else 0,
        "lookahead_pass_cell_count": lookahead_pass if integrity_valid else 0,
        "blockers": list(dict.fromkeys(blockers))[:12],
    }
    if set(result) != _STAGE_FIELDS:
        raise AssertionError("post_selection_stage_field_contract_invalid")
    return result


def build_strategy_post_selection_replay_summary(
    report: dict[str, Any] | Any,
    *,
    strategy_id: str,
) -> dict[str, Any]:
    """Project schema-11/12/13/14 frozen TEST and holdout replay without identities."""

    source = report if isinstance(report, dict) else {}
    report_schema_version = source.get("schema_version")
    if (
        isinstance(report_schema_version, bool)
        or not isinstance(report_schema_version, int)
        or report_schema_version
        not in POST_SELECTION_REPLAY_SUMMARY_REPORT_SCHEMA_VERSIONS
    ):
        raise ValueError("post_selection_replay_summary_report_schema_unsupported")
    selected_strategy = _clean_strategy_id(strategy_id)
    batch_spec = source.get("batch_spec")
    batch_spec = batch_spec if isinstance(batch_spec, dict) else {}
    selection_symbols = _sequence(batch_spec.get("selection_symbols"))
    confirmation_symbols = _sequence(batch_spec.get("confirmation_symbols"))

    frozen_value = source.get("frozen_candidates")
    test_result_value = source.get("test_results")
    test_cell_value = source.get("test_cells")
    holdout_result_value = source.get("holdout_results")
    holdout_cell_value = source.get("holdout_cells")
    raw_frozen_candidates = _sequence(frozen_value)
    raw_test_results = _sequence(test_result_value)
    raw_test_cells = _sequence(test_cell_value)
    raw_holdout_results = _sequence(holdout_result_value)
    raw_holdout_cells = _sequence(holdout_cell_value)
    test_container_types_valid = all(
        isinstance(item, list)
        for item in (frozen_value, test_result_value, test_cell_value)
    )
    holdout_container_types_valid = all(
        isinstance(item, list)
        for item in (test_result_value, holdout_result_value, holdout_cell_value)
    )

    frozen_candidates = [
        dict(item) for item in raw_frozen_candidates
        if isinstance(item, dict)
        and _clean_strategy_id(item.get("strategy_id")) == selected_strategy
    ]
    test_results = [
        dict(item) for item in raw_test_results
        if isinstance(item, dict)
        and _clean_strategy_id(item.get("strategy_id")) == selected_strategy
    ]
    test_cells = [
        dict(item) for item in raw_test_cells
        if isinstance(item, dict)
        and _clean_strategy_id(item.get("strategy_id")) == selected_strategy
    ]

    holdout_candidates = [
        dict(item) for item in test_results if item.get("eligible_for_holdout") is True
    ]
    holdout_results = [
        dict(item) for item in raw_holdout_results
        if isinstance(item, dict)
        and _clean_strategy_id(item.get("strategy_id")) == selected_strategy
    ]
    holdout_cells = [
        dict(item) for item in raw_holdout_cells
        if isinstance(item, dict)
        and _clean_strategy_id(item.get("strategy_id")) == selected_strategy
    ]

    frozen_test = _stage_summary(
        stage=FROZEN_TEST_ROLE,
        strategy_id=selected_strategy,
        candidates=frozen_candidates,
        results=test_results,
        cells=test_cells,
        required_symbols=selection_symbols,
        aggregate=aggregate_frozen_test,
        input_types_valid=test_container_types_valid and all(
            isinstance(item, dict)
            for rows in (raw_frozen_candidates, raw_test_results, raw_test_cells)
            for item in rows
        ),
    )
    holdout = _stage_summary(
        stage=HOLDOUT_CONFIRMATION_ROLE,
        strategy_id=selected_strategy,
        candidates=holdout_candidates,
        results=holdout_results,
        cells=holdout_cells,
        required_symbols=confirmation_symbols,
        aggregate=aggregate_holdout_confirmation,
        input_types_valid=holdout_container_types_valid and all(
            isinstance(item, dict)
            for rows in (raw_test_results, raw_holdout_results, raw_holdout_cells)
            for item in rows
        ),
    )
    statuses = {frozen_test["status"], holdout["status"]}
    if "BLOCK" in statuses:
        status = "BLOCK"
    elif statuses == {"NOT_RUN"}:
        status = "NOT_RUN"
    elif statuses == {"PASS"}:
        status = "PASS"
    else:
        status = "BLOCK"
    content = {
        "schema_version": STRATEGY_POST_SELECTION_REPLAY_SUMMARY_SCHEMA_VERSION,
        "status": status,
        "report_schema_version": report_schema_version,
        "frozen_test": frozen_test,
        "holdout_confirmation": holdout,
        "historical_backtest_only": True,
        "natural_forward_performance_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if authority_violations(content, path="post_selection_replay_summary"):
        raise AssertionError("post_selection_replay_summary_authority_invalid")
    return content


__all__ = [
    "POST_SELECTION_REPLAY_SUMMARY_REPORT_SCHEMA_VERSIONS",
    "STRATEGY_POST_SELECTION_REPLAY_SUMMARY_SCHEMA_VERSION",
    "build_strategy_post_selection_replay_summary",
]
