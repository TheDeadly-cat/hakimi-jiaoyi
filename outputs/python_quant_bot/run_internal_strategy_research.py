from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

from exchange_terminal import server
from exchange_terminal.services.backtest_engine import EXECUTION_MODEL_VERSION, causal_prefix_invariance_check, prepare_backtest_dataset
from exchange_terminal.services.implementation_manifest import build_implementation_manifest
from exchange_terminal.services.strategy_benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    align_completed_daily_payloads,
    build_calendar_split_schedule,
    buy_and_hold_report,
)
from exchange_terminal.services.strategy_quality import strategy_lookahead_check
from exchange_terminal.services.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    aggregate_frozen_test,
    aggregate_holdout_confirmation,
    aggregate_validation_variant,
    build_parameter_variants,
    build_parameter_stability_snapshot,
    canonical_hash,
    freeze_validation_candidates,
)
from exchange_terminal.services.strategy_hypothesis_preregistration import (
    STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2,
    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3,
    load_strategy_hypothesis_preregistration,
    verify_strategy_hypothesis_preregistration,
)
from exchange_terminal.services.strategy_cost_stress import (
    COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
    FROZEN_TEST_COST_STRESS_STAGE,
    SELECTION_COST_STRESS_STAGE,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3,
    STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION,
    build_strategy_cost_stress_contract,
    build_strategy_cost_stress_evidence,
    normalize_strategy_cost_risk,
    project_cost_stress_observation,
)
from exchange_terminal.services.strategy_chronological_slice import (
    COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS,
    FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4,
    build_fixed_chronological_slice_evidence,
    build_fixed_chronological_slice_evidence_v2,
)
from exchange_terminal.services.strategy_research_evidence import (
    IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
    LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
    STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION,
    STRATEGY_RESEARCH_WORKFLOW,
    POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS,
    REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS,
    strategy_research_holdout_cell_hash,
    strategy_research_holdout_cell_hash_for_report,
    strategy_research_result_hash,
    strategy_research_selection_cell_hash_for_report,
    strategy_research_test_cell_hash,
    strategy_research_test_cell_hash_for_report,
    verify_strategy_research_report,
)
from exchange_terminal.services.strategy_frozen_evaluation_replay import (
    FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
    FROZEN_TEST_ROLE,
    HOLDOUT_CONFIRMATION_ROLE,
    STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1,
    STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2,
    build_strategy_frozen_evaluation_replay_evidence,
)
from exchange_terminal.services.strategy_preregistered_failure_admission import (
    MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
    build_strategy_preregistered_failure_admission,
    build_strategy_preregistered_failure_admission_v2,
)
from exchange_terminal.services.strategy_selection_replay import (
    DEVELOPMENT_SELECTION_SPLIT_POLICY,
    build_development_selection_prefix_schedule,
    build_strategy_selection_replay_evidence,
)
from exchange_terminal.services.strategy_selection_alignment import (
    build_strategy_selection_alignment_input_snapshot,
)
from exchange_terminal.services.research_symbol_market import research_market_for_symbol
from exchange_terminal.services.strategy_research_pointer import (
    DEFAULT_STRATEGY_RESEARCH_POINTER_FILE,
    build_strategy_research_pointer_publication_expectation,
    publish_strategy_research_report_pointer,
    strategy_research_pointer_publication_eligibility,
    verify_strategy_research_pointer_publication_receipt,
)
from exchange_terminal.services.strategy_matrix_protocol import (
    StrategyMatrixRegistrationStore,
    audit_strategy_matrix_holdout_exposure,
    build_strategy_matrix_completion,
    canonical_hash as protocol_canonical_hash,
    verify_strategy_matrix_completion,
    verify_strategy_research_canonical_registry_path,
)
from exchange_terminal.services.strategy_research_search_lineage import (
    verify_strategy_research_search_lineage,
)
from exchange_terminal.services.prepared_research_result import (
    build_prepared_research_result,
    load_prepared_research_result,
    prepared_research_result_path,
    publish_json_no_clobber,
    publish_prepared_research_result_no_clobber,
    verify_prepared_research_result,
)
from exchange_terminal.services.strategy_signals import (
    assert_new_research_allowed,
    build_strategy_signal_fn,
    strategy_signal_input,
    validated_strategy_ids,
)
from exchange_terminal.services.strategy_risk_profiles import STRATEGY_RISK_PROFILE_VERSION, strategy_research_risk_profile
from exchange_terminal.services.strategy_validation import chronological_folds, summarize_cost_sensitivity, summarize_walk_forward
from exchange_terminal.services.trusted_clock import attest_utc_clock
from run_internal_strategy_matrix import (
    MATRIX_SPLIT_POLICY,
    build_matrix_dataset_snapshot,
    completed_rows,
    dataset_manifests,
    load_payloads,
    run_cell as run_holdout_cell,
    write_json_atomic,
)


DEFAULT_SELECTION_SYMBOLS = ["AAPL", "NVDA", "MSFT", "MU", "WDC", "BTC-USDT"]
DEFAULT_HOLDOUT_SYMBOLS = ["QQQ", "ETH-USDT"]
RESEARCH_WORKFLOW = STRATEGY_RESEARCH_WORKFLOW


def build_research_batch_spec(
    *,
    selection_symbols: list[str],
    holdout_symbols: list[str],
    strategies: list[str],
    position_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    fee_rate: float,
    slippage_bps: float,
    limit: int,
    max_test_candidates: int,
    research_generation: str,
    selection_test_policy: str,
    hypothesis_preregistration: dict[str, Any] | None = None,
    search_lineage: dict[str, Any] | None = None,
    report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
) -> dict[str, Any]:
    normalized_selection = list(dict.fromkeys(
        str(symbol or "").strip().upper()
        for symbol in selection_symbols
        if str(symbol or "").strip()
    ))
    normalized_holdout = list(dict.fromkeys(
        str(symbol or "").strip().upper()
        for symbol in holdout_symbols
        if str(symbol or "").strip()
    ))
    normalized_strategies = list(dict.fromkeys(
        str(strategy or "").strip().lower()
        for strategy in strategies
        if str(strategy or "").strip()
    ))
    if not normalized_selection or not normalized_holdout or not normalized_strategies:
        raise ValueError("selection symbols, holdout symbols, and strategies are required")
    overlap = sorted(set(normalized_selection) & set(normalized_holdout))
    if overlap:
        raise ValueError(f"selection and holdout symbols overlap: {', '.join(overlap)}")
    unsupported = [
        strategy for strategy in normalized_strategies
        if strategy not in set(validated_strategy_ids())
    ]
    if unsupported:
        raise ValueError(f"unsupported research strategies: {', '.join(unsupported)}")
    assert_new_research_allowed(normalized_strategies)
    if selection_test_policy not in {"BLIND_ONCE", "DEVELOPMENT_ONLY"}:
        raise ValueError("selection_test_policy must be BLIND_ONCE or DEVELOPMENT_ONLY")
    if not str(research_generation or "").strip():
        raise ValueError("research_generation is required")
    if report_schema_version not in {
        IMPLEMENTATION_MANIFEST_REPORT_SCHEMA_VERSION,
        STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
        COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        raise ValueError("unsupported strategy research report schema")
    sealed_hypothesis: dict[str, Any] | None = None
    if report_schema_version in {
        STRATEGY_HYPOTHESIS_PREREGISTRATION_REPORT_SCHEMA_VERSION,
        COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION,
        FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION,
        FROZEN_EVALUATION_REPLAY_REPORT_SCHEMA_VERSION,
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        verification = verify_strategy_hypothesis_preregistration(
            hypothesis_preregistration,
            expected_strategy_ids=normalized_strategies,
            expected_research_generation=str(research_generation).strip(),
            expected_schema_version=(
                STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V3
                if report_schema_version
                == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
                else (
                    STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION_V2
                    if report_schema_version
                    == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                    else STRATEGY_HYPOTHESIS_PREREGISTRATION_SCHEMA_VERSION
                )
            ),
        )
        if verification.get("status") != "PASS":
            raise ValueError(
                "strategy_hypothesis_preregistration_invalid:"
                + ",".join(str(item) for item in verification.get("blockers") or [])
            )
        sealed_hypothesis = deepcopy(dict(hypothesis_preregistration or {}))
    elif hypothesis_preregistration is not None:
        raise ValueError("legacy_strategy_research_schema_cannot_carry_hypothesis_contract")

    numeric = {
        "position_pct": float(position_pct),
        "take_profit_pct": float(take_profit_pct),
        "stop_loss_pct": float(stop_loss_pct),
        "fee_rate": float(fee_rate),
        "slippage_bps": float(slippage_bps),
    }
    if not all(math.isfinite(value) for value in numeric.values()):
        raise ValueError("research risk parameters must be finite")
    if not 0 < numeric["position_pct"] <= 100:
        raise ValueError("position_pct must be in (0, 100]")
    if not 0 <= numeric["take_profit_pct"] <= 1_000:
        raise ValueError("take_profit_pct must be in [0, 1000]")
    if not 0 < numeric["stop_loss_pct"] <= 100:
        raise ValueError("stop_loss_pct must be in (0, 100]")
    if not 0 <= numeric["fee_rate"] <= 0.10:
        raise ValueError("fee_rate must be in [0, 0.10]")
    if not 0 <= numeric["slippage_bps"] <= 10_000:
        raise ValueError("slippage_bps must be in [0, 10000]")
    if isinstance(limit, bool) or int(limit) < 360:
        raise ValueError("limit must be at least 360 daily rows")

    risk = {**numeric, "leverage": 1.0}
    if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        risk = normalize_strategy_cost_risk(risk)
    variants: list[dict[str, Any]] = []
    strategy_specs: dict[str, dict[str, Any]] = {}
    for strategy_id in normalized_strategies:
        base_params = dict(server.choose_strategy(strategy_id).get("params") or {})
        strategy_variants: list[dict[str, Any]] = []
        for raw_variant in build_parameter_variants(strategy_id, base_params):
            variant = dict(raw_variant)
            variant["implementation_fingerprint"] = server.strategy_implementation_fingerprint(
                strategy_id,
                variant["params"],
            )
            risk_profile = strategy_research_risk_profile(
                strategy_id,
                risk,
                preserve_explicit_transaction_costs=(
                    report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS
                ),
            )
            variant["risk_profile"] = risk_profile
            variant["risk"] = dict(risk_profile["risk"])
            variant["risk_hash"] = risk_profile["risk_hash"]
            if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
                variant["cost_stress_contract"] = build_strategy_cost_stress_contract(
                    variant["risk"]
                )
            variants.append(variant)
            strategy_variants.append(variant)
        strategy_specs[strategy_id] = {
            "base_params": base_params,
            "signal_input": strategy_signal_input(strategy_id),
            "variants": strategy_variants,
        }
    if (
        isinstance(max_test_candidates, bool)
        or not 1 <= int(max_test_candidates) <= len(normalized_strategies)
    ):
        raise ValueError("max_test_candidates must be within the strategy count")
    sealed_search_lineage: dict[str, Any] | None = None
    if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
        lineage_verification = verify_strategy_research_search_lineage(
            search_lineage,
            expected_search_family_id=str(
                (sealed_hypothesis or {}).get("search_family_id") or ""
            ),
            expected_current_trial_count=len(variants),
        )
        if lineage_verification.get("status") != "PASS":
            raise ValueError(
                "strategy_research_search_lineage_invalid:"
                + ",".join(
                    str(item)
                    for item in lineage_verification.get("blockers") or []
                )
            )
        sealed_search_lineage = deepcopy(dict(search_lineage or {}))
    elif search_lineage is not None:
        raise ValueError("legacy_strategy_research_schema_cannot_carry_search_lineage")

    spec = {
        # The shared single-use registry validates this stable benchmark envelope.
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "research_schema_version": STRATEGY_RESEARCH_SCHEMA_VERSION,
        "report_schema_version": report_schema_version,
        "workflow": RESEARCH_WORKFLOW,
        "research_generation": str(research_generation).strip(),
        "selection_symbols": normalized_selection,
        "confirmation_symbols": normalized_holdout,
        "holdout_symbols": normalized_holdout,
        "strategies": normalized_strategies,
        "strategy_specs": strategy_specs,
        "variants": variants,
        "risk": risk,
        "risk_profile_version": STRATEGY_RISK_PROFILE_VERSION,
        "limit": int(limit),
        "max_test_candidates": int(max_test_candidates),
        "max_confirmation_candidates": int(max_test_candidates),
        "selection_test_policy": selection_test_policy,
        "selection_rule": "train_validation_variant_selection_then_single_test_then_symbol_holdout",
        "selection_lanes": {
            "RAW_EXCESS": "positive raw excess on at least 60% of symbols and positive multiple-trial adjusted score",
            "RISK_ADJUSTED": "at least 80% drawdown and return/drawdown efficiency wins, 60% Sharpe wins, median raw lag no worse than 3pp, worst drawdown below 15%",
        },
        "lane_lock_policy": "validation-selected lane is frozen before test and cannot change on test or holdout",
        "test_policy": "BLIND_ONCE requires a claimed single-use protocol; DEVELOPMENT_ONLY never evaluates test rows",
        "holdout_policy": "holdout symbols are loaded only after a frozen candidate passes the single test",
        "optimizer_used": False,
        "fixed_parameter_grid_used": True,
        "split_policy": dict(MATRIX_SPLIT_POLICY),
        "data_policy": {
            "timeframe": "1D",
            "completed_candles_only": True,
            "alignment_schema_version": "daily-batch-alignment-v2",
            "max_endpoint_skew_days": 3,
            "max_boundary_skew_days": 7,
            "frozen_stock_revision_evidence_required": True,
            "frozen_crypto_history_evidence_required": True,
            "exact_dataset_snapshot_required": True,
        },
        "execution_model_version": EXECUTION_MODEL_VERSION,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if sealed_hypothesis is not None:
        spec["hypothesis_preregistration"] = sealed_hypothesis
        spec["hypothesis_preregistration_hash"] = str(
            sealed_hypothesis.get("hypothesis_hash") or ""
        )
    if sealed_search_lineage is not None:
        spec["search_lineage"] = sealed_search_lineage
    return spec


def project_development_selection_data(
    payloads: dict[str, dict[str, Any]],
    schedule: dict[str, Any],
    *,
    dataset_lineage_prefix: str,
    report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Remove protected test OHLCV before a development report is built."""
    boundaries = schedule.get("symbol_boundaries")
    if schedule.get("status") != "PASS" or not isinstance(boundaries, dict):
        blockers = [
            "development_projection_requires_passed_schedule",
            *[f"source_schedule:{item}" for item in schedule.get("blockers") or []],
        ]
        blocked = {
            "schema_version": "development-selection-projection-v1",
            "status": "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "symbol_boundaries": {},
            "protected_test_rows_persisted": False,
        }
        return {}, dict(blocked), dict(blocked)

    projected: dict[str, dict[str, Any]] = {}
    projected_boundaries: dict[str, dict[str, Any]] = {}
    starts: dict[str, str] = {}
    endpoints: dict[str, str] = {}
    counts: dict[str, int] = {}
    blockers: list[str] = []
    for symbol, raw_payload in payloads.items():
        boundary = boundaries.get(symbol)
        rows = completed_rows(list(raw_payload.get("rows") or []))
        if not isinstance(boundary, dict):
            blockers.append(f"{symbol}:development_boundary_missing")
            continue
        train_end = int(boundary.get("train_end_index") or 0)
        validation_end = int(boundary.get("validation_end_index") or 0)
        if not 0 < train_end < validation_end <= len(rows):
            blockers.append(
                f"{symbol}:invalid_development_boundary:{train_end}:{validation_end}:{len(rows)}"
            )
            continue
        selected_rows = rows[:validation_end]
        first = str(selected_rows[0].get("date") or "")[:10]
        last = str(selected_rows[-1].get("date") or "")[:10]
        try:
            date.fromisoformat(first)
            date.fromisoformat(last)
        except ValueError:
            blockers.append(f"{symbol}:development_boundary_date_invalid")
            continue

        payload = {**raw_payload, "rows": selected_rows}
        lineage_id = f"{dataset_lineage_prefix}:{symbol}:train-validation"
        is_stock = (
            research_market_for_symbol(symbol) == "stock"
            if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
            else server.is_stock_symbol(symbol)
        )
        if is_stock:
            previous = dict(raw_payload.get("data_revision_evidence") or {})
            accepted_cache = dict(previous.get("accepted_cache") or {})
            adjustment = dict(raw_payload.get("adjustment_evidence") or {})
            dataset_revision = server.attest_stock_backtest_rows(
                symbol=symbol,
                provider=str(raw_payload.get("source") or ""),
                rows=selected_rows,
                adjustment_basis=str(raw_payload.get("adjustment_basis") or ""),
                corporate_actions_hash=str(adjustment.get("corporate_actions_hash") or ""),
                dataset_lineage_id=lineage_id,
            )
            statuses = {
                str(accepted_cache.get("status") or "BLOCK"),
                str(dataset_revision.get("status") or "BLOCK"),
            }
            payload["data_revision_evidence"] = {
                "status": "BLOCK" if "BLOCK" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS",
                "accepted_cache": accepted_cache,
                "backtest_dataset": dataset_revision,
                "cross_source": list(previous.get("cross_source") or []),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        else:
            previous = dict(raw_payload.get("market_history_evidence") or {})
            payload["market_history_evidence"] = server.build_history_dataset_evidence(
                symbol=symbol,
                rows=selected_rows,
                source=str(raw_payload.get("source") or ""),
                dataset_lineage_id=lineage_id,
                cache_manifest=dict(previous.get("cache_manifest") or {}),
                cache_admitted=previous.get("cache_admitted") is True,
            )
        projected[symbol] = payload
        starts[symbol] = first
        endpoints[symbol] = last
        counts[symbol] = len(selected_rows)
        projected_boundaries[symbol] = {
            "train_end_index": train_end,
            "validation_end_index": len(selected_rows),
            "counts": {
                "train": train_end,
                "validation": len(selected_rows) - train_end,
                "test": 0,
            },
            "row_count": len(selected_rows),
        }

    if blockers or len(projected) != len(payloads) or not projected:
        blocker_list = list(dict.fromkeys(blockers or ["development_projection_empty"]))
        blocked = {
            "schema_version": "development-selection-projection-v1",
            "status": "BLOCK",
            "blockers": blocker_list,
            "symbol_boundaries": {},
            "protected_test_rows_persisted": False,
        }
        return {}, dict(blocked), dict(blocked)

    parsed_endpoints = [date.fromisoformat(value) for value in endpoints.values()]
    common_start = max(starts.values())
    common_as_of = min(endpoints.values())
    endpoint_skew_days = (max(parsed_endpoints) - min(parsed_endpoints)).days
    if (
        report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
    ):
        projected_schedule = build_development_selection_prefix_schedule(
            {
                symbol: {"rows": list(payload.get("rows") or [])}
                for symbol, payload in projected.items()
            },
            train_ratio=schedule.get("train_ratio"),
            validation_ratio=schedule.get("validation_ratio"),
            minimum_segment_rows=schedule.get("minimum_segment_rows"),
        )
        if projected_schedule.get("status") != "PASS":
            blocked = {
                "schema_version": "development-selection-projection-v1",
                "status": "BLOCK",
                "blockers": [
                    "development_selection_split_rebuild_blocked",
                    *list(projected_schedule.get("blockers") or []),
                ],
                "symbol_boundaries": {},
                "protected_test_rows_persisted": False,
            }
            return {}, dict(blocked), dict(blocked)
    else:
        projected_schedule = {
            **schedule,
            "common_end": common_as_of,
            "validation_end": common_as_of,
            "symbol_boundaries": projected_boundaries,
            "blockers": [],
            "projection_policy": "TRAIN_VALIDATION_ONLY",
            "protected_test_rows_persisted": False,
        }
    projected_alignment = {
        "schema_version": "daily-batch-alignment-v2",
        "status": "PASS",
        "common_start": common_start,
        "common_as_of": common_as_of,
        "required_start": "",
        "required_as_of": "",
        "max_endpoint_skew_days": int(schedule.get("max_endpoint_skew_days") or 3),
        "max_boundary_skew_days": int(schedule.get("max_boundary_skew_days") or 7),
        "endpoint_skew_days": endpoint_skew_days,
        "original_starts": starts,
        "original_endpoints": endpoints,
        "original_completed_rows": counts,
        "aligned_starts": starts,
        "aligned_endpoints": endpoints,
        "aligned_completed_rows": counts,
        "blockers": [],
        "projection_policy": (
            DEVELOPMENT_SELECTION_SPLIT_POLICY
            if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
            else "TRAIN_VALIDATION_ONLY"
        ),
        "protected_test_rows_persisted": False,
    }
    return projected, projected_schedule, projected_alignment


def run_backtest(
    *,
    symbol: str,
    strategy_id: str,
    strategy_params: dict[str, Any],
    rows: list[dict[str, Any]],
    source: str,
    risk: dict[str, float],
    fee_rate: float | None = None,
    slippage_bps: float | None = None,
    evaluation_start_index: int | None = None,
) -> dict[str, Any]:
    return server.run_strategy_backtest(
        strategy_id,
        risk["position_pct"],
        risk["take_profit_pct"],
        risk["stop_loss_pct"],
        1.0,
        len(rows),
        symbol,
        {"rows": rows, "source": source, "bar": "1D"},
        fee_rate=risk["fee_rate"] if fee_rate is None else fee_rate,
        slippage_bps=risk["slippage_bps"] if slippage_bps is None else slippage_bps,
        evaluation_start_index=evaluation_start_index,
        strategy_params=strategy_params,
    )


def run_selection_cell(
    *,
    symbol: str,
    variant: dict[str, Any],
    payload: dict[str, Any],
    risk: dict[str, float],
    boundaries: dict[str, Any],
    report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
) -> dict[str, Any]:
    started = time.perf_counter()
    strategy_id = str(variant["strategy_id"])
    params = dict(variant["params"])
    source = str(payload.get("source") or "")
    clean_rows = completed_rows(list(payload.get("rows") or []))
    train_end = int(boundaries.get("train_end_index") or 0)
    validation_end = int(boundaries.get("validation_end_index") or 0)
    selection_rows = clean_rows[:validation_end]
    train_rows = selection_rows[:train_end]
    market = (
        research_market_for_symbol(symbol)
        if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        else "stock" if server.is_stock_symbol(symbol) else "crypto"
    )
    startup = server.strategy_startup_candles(strategy_id, params)
    manifest = prepare_backtest_dataset(
        selection_rows,
        symbol=symbol,
        source=source,
        timeframe="1D",
        minimum_rows=startup + 2,
        market=market,
    )["manifest"]
    selection_replay: dict[str, Any] | None = None
    if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS:
        selection_replay = build_strategy_selection_replay_evidence(
            selection_rows=selection_rows,
            train_end_index=train_end,
            symbol=symbol,
            source=source,
            market=market,
            timeframe="1D",
            variant_id=str(variant.get("variant_id") or ""),
            strategy_id=strategy_id,
            params=params,
            param_hash=str(variant.get("param_hash") or ""),
            implementation_fingerprint=str(
                variant.get("implementation_fingerprint") or ""
            ),
            risk=risk,
        )
        train = dict(selection_replay["train_run"]["result_projection"])
        validation = dict(selection_replay["validation_run"]["result_projection"])
        validation_benchmark = dict(
            selection_replay["benchmark_run"]["result_projection"]
        )
    else:
        train = run_backtest(
            symbol=symbol,
            strategy_id=strategy_id,
            strategy_params=params,
            rows=train_rows,
            source=f"{source}:research_train",
            risk=risk,
        )
        validation = run_backtest(
            symbol=symbol,
            strategy_id=strategy_id,
            strategy_params=params,
            rows=selection_rows,
            source=f"{source}:research_validation",
            risk=risk,
            evaluation_start_index=train_end,
        )
        validation_benchmark = buy_and_hold_report(
            rows=selection_rows,
            symbol=symbol,
            source=f"{source}:validation_buy_hold",
            position_pct=risk["position_pct"],
            startup_candles=80,
            fee_rate=risk["fee_rate"],
            slippage_bps=risk["slippage_bps"],
            market=market,
            evaluation_start_index=train_end,
        )

    folds = chronological_folds(selection_rows, fold_count=3, minimum_fold_rows=120)
    fold_reports: list[dict[str, Any]] = []
    if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS:
        fold_stability = build_fixed_chronological_slice_evidence_v2(
            selection_rows=selection_rows,
            symbol=symbol,
            source=source,
            market=market,
            timeframe="1D",
            strategy_id=strategy_id,
            params=params,
            param_hash=str(variant.get("param_hash") or ""),
            risk=risk,
        )
    else:
        for fold in folds.get("folds") or []:
            report = run_backtest(
                symbol=symbol,
                strategy_id=strategy_id,
                strategy_params=params,
                rows=list(fold.get("rows") or []),
                source=f"{source}:pretest_fold_{fold.get('fold')}",
                risk=risk,
            )
            fold_reports.append({
                "fold": fold.get("fold"),
                "start": fold.get("start"),
                "end": fold.get("end"),
                "ok": bool(report.get("ok")),
                "total_return_pct": report.get("total_return_pct"),
                "max_drawdown_pct": report.get("max_drawdown_pct"),
                "trade_count": report.get("trade_count"),
            })
    if report_schema_version == LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION:
        fold_stability = build_fixed_chronological_slice_evidence(
            selection_rows=selection_rows,
            symbol=symbol,
            source=source,
            market=market,
            timeframe="1D",
            fold_plans=list(folds.get("folds") or []),
            fold_reports=fold_reports,
            minimum_fold_rows=int(folds.get("minimum_fold_rows") or 120),
        )
    elif report_schema_version not in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS:
        fold_stability = summarize_walk_forward(fold_reports)
        if folds.get("status") != "PASS":
            fold_stability["status"] = "BLOCK"
            fold_stability["blockers"] = list(dict.fromkeys([
                *(fold_stability.get("blockers") or []),
                *(folds.get("blockers") or []),
            ]))

    if selection_replay is not None:
        configured_cost_scenarios = []
    elif report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        cost_contract = dict(
            variant.get("cost_stress_contract")
            or build_strategy_cost_stress_contract(risk)
        )
        configured_cost_scenarios = [
            dict(item) for item in cost_contract.get("selection_scenarios") or []
            if isinstance(item, dict)
        ]
    else:
        configured_cost_scenarios = [
            {
                "name": "stress",
                "fee_rate": max(risk["fee_rate"] * 1.6, 0.0008),
                "slippage_bps": max(risk["slippage_bps"] * 2.5, 5.0),
            },
            {
                "name": "severe",
                "fee_rate": max(risk["fee_rate"] * 2.4, 0.0012),
                "slippage_bps": max(risk["slippage_bps"] * 5.0, 10.0),
            },
        ]
    cost_scenarios: list[dict[str, Any]] = []
    for configured_scenario in configured_cost_scenarios:
        name = str(configured_scenario.get("name") or "")
        fee_rate = float(configured_scenario["fee_rate"])
        slippage_bps = float(configured_scenario["slippage_bps"])
        report = run_backtest(
            symbol=symbol,
            strategy_id=strategy_id,
            strategy_params=params,
            rows=selection_rows,
            source=f"{source}:validation_cost_{name}",
            risk=risk,
            fee_rate=fee_rate,
            slippage_bps=slippage_bps,
            evaluation_start_index=train_end,
        )
        cost_scenarios.append(project_cost_stress_observation(name, report))
    if selection_replay is not None:
        cost_sensitivity = dict(selection_replay["cost_sensitivity"])
    elif report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        cost_sensitivity = build_strategy_cost_stress_evidence(
            stage=SELECTION_COST_STRESS_STAGE,
            risk=risk,
            baseline=project_cost_stress_observation("configured", validation),
            scenarios=cost_scenarios,
        )
    else:
        cost_sensitivity = summarize_cost_sensitivity(validation, cost_scenarios)

    if selection_replay is not None:
        lookahead = dict(selection_replay["lookahead"])
    else:
        prefix_invariance = causal_prefix_invariance_check(
            rows=selection_rows,
            symbol=symbol,
            source=f"{source}:pretest_causal_audit",
            signal_factory=lambda _rows: build_strategy_signal_fn(strategy_id, params),
            position_pct=risk["position_pct"],
            take_profit_pct=risk["take_profit_pct"],
            stop_loss_pct=risk["stop_loss_pct"],
            startup_candles=startup,
            fee_rate=risk["fee_rate"],
            slippage_bps=risk["slippage_bps"],
            leverage=1.0,
            market=market,
            timeframe="1D",
            signal_input=strategy_signal_input(strategy_id),
        )
        strategy = {**server.choose_strategy(strategy_id), "params": params}
        lookahead = strategy_lookahead_check(
            strategy,
            candle_count=len(selection_rows),
            startup_candles=startup,
            rows=selection_rows,
            prefix_invariance=prefix_invariance,
        )
    validation_return = float(validation.get("total_return_pct") or 0.0)
    benchmark_return = float(validation_benchmark.get("total_return_pct") or 0.0)
    validation_drawdown = float(validation.get("max_drawdown_pct") or 0.0)
    benchmark_drawdown = float(validation_benchmark.get("max_drawdown_pct") or 0.0)
    validation_sharpe = float(validation.get("sharpe") or 0.0)
    benchmark_sharpe = float(validation_benchmark.get("sharpe") or 0.0)
    validation_efficiency = validation_return / max(validation_drawdown, 1.0)
    benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)
    result = {
        "phase": "TRAIN_VALIDATION_SELECTION",
        "symbol": symbol,
        "strategy_id": strategy_id,
        "variant_id": variant["variant_id"],
        "params": params,
        "param_hash": variant["param_hash"],
        "implementation_fingerprint": variant["implementation_fingerprint"],
        "dataset_status": manifest.get("status", "BLOCK"),
        "dataset_hash": manifest.get("data_hash", ""),
        "dataset_blockers": manifest.get("blockers") or [],
        "selection_input_rows": len(selection_rows),
        "selection_input_end": str(selection_rows[-1].get("date") or "") if selection_rows else "",
        "test_rows_evaluated": False,
        "train_ok": bool(train.get("ok")),
        "train_return_pct": train.get("total_return_pct"),
        "train_trade_count": train.get("trade_count"),
        "validation_ok": bool(validation.get("ok")),
        "validation_return_pct": validation.get("total_return_pct"),
        "validation_excess_return_pct": round(validation_return - benchmark_return, 4),
        "validation_trade_count": validation.get("trade_count"),
        "validation_max_drawdown_pct": validation.get("max_drawdown_pct"),
        "validation_sharpe": validation.get("sharpe"),
        "validation_buy_hold_return_pct": validation_benchmark.get("total_return_pct"),
        "validation_buy_hold_max_drawdown_pct": validation_benchmark.get("max_drawdown_pct"),
        "validation_buy_hold_sharpe": validation_benchmark.get("sharpe"),
        "validation_drawdown_improvement_pct": round(benchmark_drawdown - validation_drawdown, 4),
        "validation_sharpe_excess": round(validation_sharpe - benchmark_sharpe, 4),
        "validation_return_drawdown_efficiency": round(validation_efficiency, 6),
        "validation_buy_hold_return_drawdown_efficiency": round(benchmark_efficiency, 6),
        "validation_risk_efficiency_excess": round(validation_efficiency - benchmark_efficiency, 6),
        "fold_stability_status": fold_stability.get("status", "BLOCK"),
        "fold_stability": fold_stability,
        "cost_sensitivity_status": cost_sensitivity.get("status", "BLOCK"),
        "cost_sensitivity": cost_sensitivity,
        "lookahead_status": lookahead.get("status", "BLOCK"),
        "lookahead_issues": lookahead.get("issues") or [],
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "cell_evidence_schema_version": (
            STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
            if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
            else STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V4
            if report_schema_version == LEGACY_FIXED_CHRONOLOGICAL_SLICE_EVIDENCE_REPORT_SCHEMA_VERSION
            else STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION_V3
            if report_schema_version == COST_STRESS_EVIDENCE_REPORT_SCHEMA_VERSION
            else LEGACY_STRATEGY_RESEARCH_SELECTION_CELL_EVIDENCE_SCHEMA_VERSION
        ),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if selection_replay is not None:
        result.update(dict(selection_replay["flat_metric_projection"]))
        result["selection_replay"] = selection_replay
    result["run_hash"] = strategy_research_selection_cell_hash_for_report(
        result,
        risk,
        report_schema_version=report_schema_version,
    )
    return result


def run_test_cell(
    *,
    symbol: str,
    candidate: dict[str, Any],
    payload: dict[str, Any],
    risk: dict[str, float],
    boundaries: dict[str, Any],
    report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
) -> dict[str, Any]:
    started = time.perf_counter()
    strategy_id = str(candidate["strategy_id"])
    params = dict(candidate["params"])
    source = str(payload.get("source") or "")
    clean_rows = completed_rows(list(payload.get("rows") or []))
    if report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
        replay = build_strategy_frozen_evaluation_replay_evidence(
            role=FROZEN_TEST_ROLE,
            rows=clean_rows,
            train_end_index=int(boundaries.get("train_end_index") or 0),
            validation_end_index=int(
                boundaries.get("validation_end_index") or 0
            ),
            symbol=symbol,
            source=source,
            market=research_market_for_symbol(symbol),
            timeframe="1D",
            variant_id=str(candidate.get("variant_id") or ""),
            strategy_id=strategy_id,
            params=params,
            param_hash=str(candidate.get("param_hash") or ""),
            implementation_fingerprint=str(
                candidate.get("implementation_fingerprint") or ""
            ),
            risk=risk,
        )
        result = {
            "phase": FROZEN_TEST_ROLE,
            "symbol": symbol,
            "strategy_id": strategy_id,
            "variant_id": candidate["variant_id"],
            "params": params,
            "param_hash": candidate["param_hash"],
            "implementation_fingerprint": candidate[
                "implementation_fingerprint"
            ],
            "frozen_before_test": bool(candidate.get("frozen_before_test")),
            **dict(replay["flat_metric_projection"]),
            "test_cell_evidence_schema_version": (
                STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION_V2
            ),
            "frozen_evaluation_replay": replay,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        result["run_hash"] = strategy_research_test_cell_hash_for_report(
            result,
            risk,
            report_schema_version=report_schema_version,
        )
        return result
    test_start = int(boundaries.get("validation_end_index") or 0)
    market = (
        research_market_for_symbol(symbol)
        if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        else "stock" if server.is_stock_symbol(symbol) else "crypto"
    )
    startup = server.strategy_startup_candles(strategy_id, params)
    manifest = prepare_backtest_dataset(
        clean_rows,
        symbol=symbol,
        source=source,
        timeframe="1D",
        minimum_rows=startup + 2,
        market=market,
    )["manifest"]
    test = run_backtest(
        symbol=symbol,
        strategy_id=strategy_id,
        strategy_params=params,
        rows=clean_rows,
        source=f"{source}:frozen_test",
        risk=risk,
        evaluation_start_index=test_start,
    )
    benchmark = buy_and_hold_report(
        rows=clean_rows,
        symbol=symbol,
        source=f"{source}:frozen_test_buy_hold",
        position_pct=risk["position_pct"],
        startup_candles=80,
        fee_rate=risk["fee_rate"],
        slippage_bps=risk["slippage_bps"],
        market=market,
        evaluation_start_index=test_start,
    )
    if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        cost_contract = build_strategy_cost_stress_contract(risk)
        severe_contract = dict(cost_contract["frozen_test_scenarios"][0])
        severe_fee_rate = float(severe_contract["fee_rate"])
        severe_slippage_bps = float(severe_contract["slippage_bps"])
    else:
        severe_fee_rate = max(risk["fee_rate"] * 2.4, 0.0012)
        severe_slippage_bps = max(risk["slippage_bps"] * 5.0, 10.0)
    severe = run_backtest(
        symbol=symbol,
        strategy_id=strategy_id,
        strategy_params=params,
        rows=clean_rows,
        source=f"{source}:frozen_test_severe_cost",
        risk=risk,
        fee_rate=severe_fee_rate,
        slippage_bps=severe_slippage_bps,
        evaluation_start_index=test_start,
    )
    test_return = float(test.get("total_return_pct") or 0.0)
    benchmark_return = float(benchmark.get("total_return_pct") or 0.0)
    test_drawdown = float(test.get("max_drawdown_pct") or 0.0)
    benchmark_drawdown = float(benchmark.get("max_drawdown_pct") or 0.0)
    test_sharpe = float(test.get("sharpe") or 0.0)
    benchmark_sharpe = float(benchmark.get("sharpe") or 0.0)
    test_efficiency = test_return / max(test_drawdown, 1.0)
    benchmark_efficiency = benchmark_return / max(benchmark_drawdown, 1.0)
    cost_stress_evidence: dict[str, Any] | None = None
    if report_schema_version in COST_STRESS_BOUND_REPORT_SCHEMA_VERSIONS:
        cost_stress_evidence = build_strategy_cost_stress_evidence(
            stage=FROZEN_TEST_COST_STRESS_STAGE,
            risk=risk,
            baseline=project_cost_stress_observation("configured", test),
            scenarios=[project_cost_stress_observation("severe", severe)],
        )
        test_cost_status = str(cost_stress_evidence.get("status") or "BLOCK")
    else:
        test_cost_status = (
            "PASS"
            if severe.get("ok") and float(severe.get("total_return_pct") or 0.0) > 0
            else "BLOCK"
        )
    result = {
        "phase": "FROZEN_TEST_ONCE",
        "symbol": symbol,
        "strategy_id": strategy_id,
        "variant_id": candidate["variant_id"],
        "params": params,
        "param_hash": candidate["param_hash"],
        "implementation_fingerprint": candidate["implementation_fingerprint"],
        "frozen_before_test": bool(candidate.get("frozen_before_test")),
        "dataset_status": manifest.get("status", "BLOCK"),
        "dataset_hash": manifest.get("data_hash", ""),
        "test_ok": bool(test.get("ok")),
        "test_start_index": test_start,
        "test_start": str(clean_rows[test_start].get("date") or "") if 0 <= test_start < len(clean_rows) else "",
        "test_end": str(clean_rows[-1].get("date") or "") if clean_rows else "",
        "test_return_pct": test.get("total_return_pct"),
        "test_excess_return_pct": round(test_return - benchmark_return, 4),
        "test_trade_count": test.get("trade_count"),
        "test_max_drawdown_pct": test.get("max_drawdown_pct"),
        "test_sharpe": test.get("sharpe"),
        "test_buy_hold_return_pct": benchmark.get("total_return_pct"),
        "test_buy_hold_max_drawdown_pct": benchmark.get("max_drawdown_pct"),
        "test_buy_hold_sharpe": benchmark.get("sharpe"),
        "test_drawdown_improvement_pct": round(benchmark_drawdown - test_drawdown, 4),
        "test_sharpe_excess": round(test_sharpe - benchmark_sharpe, 4),
        "test_return_drawdown_efficiency": round(test_efficiency, 6),
        "test_buy_hold_return_drawdown_efficiency": round(benchmark_efficiency, 6),
        "test_risk_efficiency_excess": round(test_efficiency - benchmark_efficiency, 6),
        "test_severe_cost_return_pct": severe.get("total_return_pct"),
        "test_cost_status": test_cost_status,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if cost_stress_evidence is not None:
        result["test_cell_evidence_schema_version"] = (
            STRATEGY_RESEARCH_TEST_CELL_EVIDENCE_SCHEMA_VERSION
        )
        result["cost_stress_evidence"] = cost_stress_evidence
    result["run_hash"] = strategy_research_test_cell_hash_for_report(
        result,
        risk,
        report_schema_version=report_schema_version,
    )
    return result


def run_holdout_replay_cell(
    *,
    symbol: str,
    candidate: dict[str, Any],
    payload: dict[str, Any],
    risk: dict[str, float],
    boundaries: dict[str, Any],
    report_schema_version: int = STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
) -> dict[str, Any]:
    if report_schema_version not in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
        raise ValueError("holdout replay requires the schema-11 contract")
    started = time.perf_counter()
    replay = build_strategy_frozen_evaluation_replay_evidence(
        role=HOLDOUT_CONFIRMATION_ROLE,
        rows=completed_rows(list(payload.get("rows") or [])),
        train_end_index=int(boundaries.get("train_end_index") or 0),
        validation_end_index=int(
            boundaries.get("validation_end_index") or 0
        ),
        symbol=symbol,
        source=str(payload.get("source") or ""),
        market=research_market_for_symbol(symbol),
        timeframe="1D",
        variant_id=str(candidate.get("variant_id") or ""),
        strategy_id=str(candidate.get("strategy_id") or ""),
        params=dict(candidate.get("params") or {}),
        param_hash=str(candidate.get("param_hash") or ""),
        implementation_fingerprint=str(
            candidate.get("implementation_fingerprint") or ""
        ),
        risk=risk,
    )
    result = {
        "phase": HOLDOUT_CONFIRMATION_ROLE,
        "symbol": symbol,
        "strategy_id": candidate["strategy_id"],
        "variant_id": candidate["variant_id"],
        "params": dict(candidate.get("params") or {}),
        "param_hash": candidate["param_hash"],
        "implementation_fingerprint": candidate[
            "implementation_fingerprint"
        ],
        **dict(replay["flat_metric_projection"]),
        "holdout_cell_evidence_schema_version": (
            STRATEGY_RESEARCH_HOLDOUT_CELL_EVIDENCE_SCHEMA_VERSION_V1
        ),
        "frozen_evaluation_replay": replay,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    result["run_hash"] = strategy_research_holdout_cell_hash_for_report(
        result,
        candidate,
        report_schema_version=report_schema_version,
    )
    return result


def build_formal_strategy_research_report(
    payload: dict[str, Any],
    *,
    protocol: dict[str, Any],
    claim: dict[str, Any],
    completion: dict[str, Any],
) -> dict[str, Any]:
    report = dict(payload)
    holdout_exposure_audit = dict(claim.get("holdout_exposure_audit") or {})
    governance = {
        "schema_version": "strategy-matrix-governance-v2",
        "status": "PREREGISTERED_BLIND_SINGLE_USE_COMPLETE",
        "selection_test_policy": "BLIND_ONCE",
        "development_only": False,
        "single_use_claim": True,
        "registration_id": str(protocol.get("registration_id") or ""),
        "protocol_hash": str(protocol.get("protocol_hash") or ""),
        "claim_hash": str(claim.get("claim_hash") or ""),
        "completion_hash": str(completion.get("completion_hash") or ""),
        "registered_at_ms": int(protocol.get("registered_at_ms") or 0),
        "started_at_ms": int(claim.get("started_at_ms") or 0),
        "completed_at_ms": int(completion.get("completed_at_ms") or 0),
        "holdout_exposure_audit": holdout_exposure_audit,
        "protocol": dict(protocol),
        "single_use_claim_receipt": dict(claim),
        "completion_receipt": dict(completion),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    governance["governance_hash"] = canonical_hash(governance)
    report["research_governance"] = governance
    return report


def _verify_formal_strategy_research_report(report: dict[str, Any]) -> dict[str, Any]:
    return verify_strategy_research_report(report, require_formal=True)


def _formal_report_bytes(report: dict[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


def _publish_verified_strategy_research_pointer(
    *,
    report_dir: Path,
    output: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    try:
        expectation = build_strategy_research_pointer_publication_expectation(
            report,
            report_file=output.name,
            report_file_bytes=_formal_report_bytes(report),
        )
        receipt = publish_strategy_research_report_pointer(
            report_dir,
            output,
            expectation=expectation,
        )
        verification = verify_strategy_research_pointer_publication_receipt(
            receipt,
            expectation=expectation,
        )
    except Exception:
        return {
            "status": "BLOCK",
            "published": False,
            "blockers": [
                "strategy_research_pointer_receipt_verification_unavailable"
            ],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if verification.get("status") != "PASS":
        return {
            "status": "BLOCK",
            "published": False,
            "blockers": list(
                verification.get("blockers")
                or ["strategy_research_pointer_receipt_verification_blocked"]
            ),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    return dict(receipt)


def _formal_output_conflict(output: Path, report: dict[str, Any]) -> dict[str, Any]:
    if not output.exists():
        return {"status": "PASS", "blockers": []}
    try:
        existing = output.read_bytes()
    except OSError:
        existing = b""
    return {
        "status": "PASS" if existing == _formal_report_bytes(report) else "BLOCK",
        "blockers": [] if existing == _formal_report_bytes(report) else [
            "strategy_research_final_output_conflict"
        ],
    }


def _prepared_verification(
    prepared: dict[str, Any],
    *,
    report_dir: Path,
    protocol: dict[str, Any],
    claim: dict[str, Any],
) -> dict[str, Any]:
    try:
        prepared_file = prepared_research_result_path(
            report_dir,
            protocol_hash=str(protocol.get("protocol_hash") or ""),
        ).name
    except ValueError:
        prepared_file = ""
    return verify_prepared_research_result(
        prepared,
        expected_workflow=RESEARCH_WORKFLOW,
        expected_protocol=protocol,
        expected_claim=claim,
        report_verifier=_verify_formal_strategy_research_report,
        reserved_output_files={
            DEFAULT_STRATEGY_RESEARCH_POINTER_FILE,
            prepared_file,
        },
    )


def finalize_formal_strategy_research_result(
    *,
    registration_store: StrategyMatrixRegistrationStore,
    registration_id: str,
    report_dir: Path,
    output: Path,
    protocol: dict[str, Any],
    claim: dict[str, Any],
    payload: dict[str, Any],
    completion_clock: dict[str, Any],
) -> dict[str, Any]:
    anticipated_completion = build_strategy_matrix_completion(
        protocol=protocol,
        claim=claim,
        result_hash=str(payload.get("batch_run_hash") or ""),
        dataset_manifest_hash=str(payload.get("dataset_manifest_hash") or ""),
        clock_attestation=completion_clock,
    )
    completion_verification = verify_strategy_matrix_completion(
        anticipated_completion,
        protocol=protocol,
        claim=claim,
    )
    if completion_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [
                f"strategy_research_completion_preview:{item}"
                for item in completion_verification.get("blockers") or []
            ],
        }

    report = build_formal_strategy_research_report(
        payload,
        protocol=protocol,
        claim=claim,
        completion=anticipated_completion,
    )
    report_verification = _verify_formal_strategy_research_report(report)
    if report_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": [
                f"strategy_research_precommit_report:{item}"
                for item in report_verification.get("blockers") or []
            ],
            "report_verification": report_verification,
        }
    prepared = build_prepared_research_result(
        workflow=RESEARCH_WORKFLOW,
        registration_id=str(protocol.get("registration_id") or ""),
        protocol_hash=str(protocol.get("protocol_hash") or ""),
        claim_hash=str(claim.get("claim_hash") or ""),
        batch_spec_hash=str(report.get("batch_spec_hash") or ""),
        result_hash=str(report.get("batch_run_hash") or ""),
        dataset_manifest_hash=str(report.get("dataset_manifest_hash") or ""),
        output_file=output.name,
        report=report,
    )
    prepared_verification = _prepared_verification(
        prepared,
        report_dir=report_dir,
        protocol=protocol,
        claim=claim,
    )
    if prepared_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_verification.get("blockers") or []),
            "prepared_verification": prepared_verification,
        }
    conflict = _formal_output_conflict(output, report)
    if conflict.get("status") != "PASS":
        return {"ok": False, "status": "BLOCK", "blockers": conflict["blockers"]}
    prepared_publication = publish_prepared_research_result_no_clobber(
        report_dir,
        prepared,
    )
    if prepared_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_publication.get("blockers") or []),
            "prepared_publication": prepared_publication,
        }

    completion_result = registration_store.complete(
        registration_id,
        result_hash=str(report.get("batch_run_hash") or ""),
        dataset_manifest_hash=str(report.get("dataset_manifest_hash") or ""),
        clock_attestation=completion_clock,
    )
    if (
        not completion_result.get("ok")
        or completion_result.get("status") != "COMPLETED"
    ):
        return {
            "ok": False,
            "status": "PREPARED_RECOVERY_REQUIRED",
            "blockers": list(
                completion_result.get("blockers")
                or ["strategy_research_registry_completion_blocked"]
            ),
            "completion": completion_result,
            "prepared_publication": prepared_publication,
        }
    if dict(completion_result.get("completion") or {}) != anticipated_completion:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_completion_receipt_drift"],
            "completion": completion_result,
        }

    final_publication = publish_json_no_clobber(
        output,
        report,
        failure_blocker="strategy_research_final_atomic_publish_failed",
    )
    if final_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "FINAL_RECOVERY_REQUIRED",
            "blockers": list(final_publication.get("blockers") or []),
            "final_publication": final_publication,
        }
    pointer_publication = _publish_verified_strategy_research_pointer(
        report_dir=report_dir,
        output=output,
        report=report,
    )
    if pointer_publication.get("published") is not True:
        return {
            "ok": False,
            "status": "POINTER_RECOVERY_REQUIRED",
            "blockers": list(
                pointer_publication.get("blockers")
                or ["strategy_research_pointer_publication_blocked"]
            ),
            "pointer_publication": pointer_publication,
        }
    return {
        "ok": True,
        "status": "COMPLETED",
        "report": report,
        "completion": anticipated_completion,
        "prepared_publication": prepared_publication,
        "final_publication": final_publication,
        "pointer_publication": pointer_publication,
    }


def recover_formal_strategy_research_result(
    *,
    registration_store: StrategyMatrixRegistrationStore,
    registration: dict[str, Any],
    registration_id: str,
    report_dir: Path,
    requested_output: Path | None,
) -> dict[str, Any] | None:
    registry_status = str(registration.get("status") or "")
    if registry_status not in {"RUNNING", "COMPLETED"}:
        return None
    if server.RUNTIME_READ_ONLY:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_recovery_runtime_read_only"],
        }
    protocol = dict(registration.get("protocol") or {})
    claim = dict(registration.get("claim") or {})
    if str(protocol.get("registration_id") or "") != str(registration_id or ""):
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_recovery_registration_mismatch"],
        }
    loaded = load_prepared_research_result(
        report_dir,
        protocol_hash=str(protocol.get("protocol_hash") or ""),
    )
    if loaded.get("status") != "LOADED":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(loaded.get("blockers") or []),
        }
    prepared = dict(loaded.get("prepared") or {})
    prepared_verification = _prepared_verification(
        prepared,
        report_dir=report_dir,
        protocol=protocol,
        claim=claim,
    )
    if prepared_verification.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(prepared_verification.get("blockers") or []),
            "prepared_verification": prepared_verification,
        }
    report = dict(prepared_verification.get("report") or {})
    completion = dict(prepared_verification.get("completion") or {})
    output_file = str(prepared_verification.get("output_file") or "")
    output = (report_dir / output_file).resolve()
    if output.parent != report_dir or output.name != output_file:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_recovery_output_parent_invalid"],
        }
    if requested_output is not None and requested_output.resolve() != output:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_recovery_output_binding_mismatch"],
        }
    pointer_eligibility = strategy_research_pointer_publication_eligibility(
        report_dir,
        output,
    )
    if pointer_eligibility.get("status") != "PASS":
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": list(pointer_eligibility.get("blockers") or []),
        }
    conflict = _formal_output_conflict(output, report)
    if conflict.get("status") != "PASS":
        return {"ok": False, "status": "BLOCK", "blockers": conflict["blockers"]}

    if registry_status == "RUNNING":
        completion_result = registration_store.complete(
            registration_id,
            result_hash=str(prepared.get("result_hash") or ""),
            dataset_manifest_hash=str(prepared.get("dataset_manifest_hash") or ""),
            clock_attestation=dict(completion.get("clock_attestation") or {}),
        )
        if (
            not completion_result.get("ok")
            or completion_result.get("status") != "COMPLETED"
        ):
            return {
                "ok": False,
                "status": "PREPARED_RECOVERY_REQUIRED",
                "blockers": list(
                    completion_result.get("blockers")
                    or ["strategy_research_registry_completion_blocked"]
                ),
                "completion": completion_result,
            }
        registry_completion = dict(completion_result.get("completion") or {})
    else:
        registry_completion = dict(registration.get("completion") or {})
    if registry_completion != completion:
        return {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["strategy_research_recovery_completion_receipt_mismatch"],
        }

    final_publication = publish_json_no_clobber(
        output,
        report,
        failure_blocker="strategy_research_final_atomic_publish_failed",
    )
    if final_publication.get("status") not in {"PUBLISHED", "EXISTING_IDENTICAL"}:
        return {
            "ok": False,
            "status": "FINAL_RECOVERY_REQUIRED",
            "blockers": list(final_publication.get("blockers") or []),
            "final_publication": final_publication,
        }
    pointer_publication = _publish_verified_strategy_research_pointer(
        report_dir=report_dir,
        output=output,
        report=report,
    )
    if pointer_publication.get("published") is not True:
        return {
            "ok": False,
            "status": "POINTER_RECOVERY_REQUIRED",
            "blockers": list(
                pointer_publication.get("blockers")
                or ["strategy_research_pointer_publication_blocked"]
            ),
            "pointer_publication": pointer_publication,
        }
    return {
        "ok": True,
        "status": "RECOVERED",
        "report": report,
        "output": output,
        "completion": completion,
        "final_publication": final_publication,
        "pointer_publication": pointer_publication,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run nested train/validation strategy research before touching test and holdout data.")
    parser.add_argument("--selection-symbols", nargs="+", default=DEFAULT_SELECTION_SYMBOLS)
    parser.add_argument("--holdout-symbols", nargs="+", default=DEFAULT_HOLDOUT_SYMBOLS)
    parser.add_argument("--strategies", nargs="+", default=None)
    parser.add_argument("--position-pct", type=float, default=35.0)
    parser.add_argument("--take-profit-pct", type=float, default=8.0)
    parser.add_argument("--stop-loss-pct", type=float, default=4.0)
    parser.add_argument("--fee-rate", type=float, default=0.0005)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=780)
    parser.add_argument("--max-test-candidates", type=int, default=2)
    parser.add_argument("--research-generation", default="")
    parser.add_argument("--hypothesis-file", default="")
    parser.add_argument("--selection-test-policy", choices=("BLIND_ONCE", "DEVELOPMENT_ONLY"), default="DEVELOPMENT_ONLY")
    parser.add_argument("--output", default="")
    parser.add_argument("--registration-id", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument(
        "--report-schema-version",
        type=int,
        choices=(
            STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
            STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
        ),
        default=None,
        help=(
            "Formal registry preflight declaration; defaults to schema 14. "
            "Development remains schema 13."
        ),
    )
    args = parser.parse_args()

    formal_mode = bool(args.registration_id or args.registry)
    requested_report_schema_version = (
        int(args.report_schema_version)
        if args.report_schema_version is not None
        else (
            STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
            if formal_mode
            else STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION
        )
    )
    if formal_mode and not (args.registration_id and args.registry):
        raise SystemExit("--registration-id and --registry must be supplied together")
    if not formal_mode and args.selection_test_policy != "DEVELOPMENT_ONLY":
        raise SystemExit("BLIND_ONCE requires a pre-registered single-use protocol")
    if not formal_mode and not args.strategies:
        raise SystemExit("--strategies is required for a new development research run")
    if not formal_mode and not str(args.research_generation or "").strip():
        raise SystemExit("--research-generation is required for a new development research run")
    if not formal_mode and not str(args.hypothesis_file or "").strip():
        raise SystemExit("--hypothesis-file is required before a new development research run")
    if (
        not formal_mode
        and requested_report_schema_version
        != STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION
    ):
        raise SystemExit("development strategy research remains schema 13")

    runtime_dir = Path(server.RUNTIME_DIR).resolve()
    report_dir = (runtime_dir / "reports").resolve()
    output = (
        Path(args.output).resolve()
        if args.output
        else report_dir / f"strategy_research_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    )
    pointer_eligibility = strategy_research_pointer_publication_eligibility(
        report_dir,
        output,
    )
    if pointer_eligibility.get("status") != "PASS":
        raise SystemExit(json.dumps({
            "error": "strategy_research_output_not_pointer_publishable",
            "status": "BLOCK",
            "blockers": list(
                pointer_eligibility.get("blockers")
                or ["strategy_research_output_not_pointer_publishable"]
            ),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False))
    development_hypothesis: dict[str, Any] | None = None
    if not formal_mode:
        try:
            development_hypothesis = load_strategy_hypothesis_preregistration(
                args.hypothesis_file,
                project_root=Path(__file__).resolve().parent,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    raw_registry_path = Path(args.registry) if args.registry else Path()
    registry_path = raw_registry_path.resolve() if args.registry else Path()
    registration_store: StrategyMatrixRegistrationStore | None = None
    protocol: dict[str, Any] = {}
    claim: dict[str, Any] = {}
    if formal_mode:
        if (
            requested_report_schema_version
            == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
        ):
            canonical_preflight = verify_strategy_research_canonical_registry_path(
                raw_registry_path,
                active_runtime_root=runtime_dir,
            )
            if canonical_preflight.get("status") != "PASS":
                raise SystemExit(json.dumps({
                    "error": "research_registry_canonical_preflight_blocked",
                    "status": "BLOCK",
                    "blockers": list(
                        canonical_preflight.get("blockers")
                        or ["strategy_research_registry_path_noncanonical"]
                    ),
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }, ensure_ascii=False))
            registry_path = Path(
                str(canonical_preflight.get("canonical_registry_path") or "")
            )
        try:
            output.relative_to(report_dir)
            registry_path.relative_to(runtime_dir)
        except ValueError as exc:
            raise SystemExit("formal research registry and output must remain inside the active runtime") from exc
        frozen_option_names = {
            "--selection-symbols",
            "--holdout-symbols",
            "--strategies",
            "--position-pct",
            "--take-profit-pct",
            "--stop-loss-pct",
            "--fee-rate",
            "--slippage-bps",
            "--limit",
            "--max-test-candidates",
            "--research-generation",
            "--hypothesis-file",
            "--selection-test-policy",
        }
        supplied_frozen_options = sorted({
            argument.split("=", 1)[0]
            for argument in sys.argv[1:]
            if argument.split("=", 1)[0] in frozen_option_names
        })
        if supplied_frozen_options:
            raise SystemExit(
                "formal research parameters come only from the registered protocol; remove: "
                + ", ".join(supplied_frozen_options)
            )
        store_arguments: dict[str, Any] = {
            "db_path": registry_path,
            "read_only": server.RUNTIME_READ_ONLY,
        }
        if (
            requested_report_schema_version
            == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION
        ):
            store_arguments["canonical_runtime_root"] = runtime_dir
        registration_store = StrategyMatrixRegistrationStore(**store_arguments)
        registration = registration_store.get(args.registration_id)
        if not registration.get("ok"):
            raise SystemExit(json.dumps({
                "error": "research_registration_not_claimable",
                "registration": registration,
            }, ensure_ascii=False))
        registered_protocol = dict(registration.get("protocol") or {})
        registered_batch_spec = (
            dict(registered_protocol.get("batch_spec") or {})
            if isinstance(registered_protocol.get("batch_spec"), dict)
            else {}
        )
        registered_report_schema_version = registered_batch_spec.get(
            "report_schema_version"
        )
        if registered_report_schema_version != requested_report_schema_version:
            raise SystemExit(json.dumps({
                "error": "research_formal_schema_declaration_mismatch",
                "status": "BLOCK",
                "declared_report_schema_version": (
                    requested_report_schema_version
                ),
                "registered_report_schema_version": (
                    registered_report_schema_version
                ),
                "blockers": [
                    "formal_report_schema_version_must_match_registered_protocol"
                ],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, ensure_ascii=False))
        recovery = recover_formal_strategy_research_result(
            registration_store=registration_store,
            registration=registration,
            registration_id=args.registration_id,
            report_dir=report_dir,
            requested_output=(Path(args.output).resolve() if args.output else None),
        )
        if recovery is not None:
            if not recovery.get("ok"):
                raise SystemExit(json.dumps({
                    "error": "research_prepared_result_recovery_blocked",
                    "status": str(recovery.get("status") or "BLOCK"),
                    "blockers": list(
                        recovery.get("blockers")
                        or ["strategy_research_prepared_result_recovery_blocked"]
                    ),
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }, ensure_ascii=False))
            recovered_report = dict(recovery.get("report") or {})
            recovered_pointer = dict(recovery.get("pointer_publication") or {})
            print(json.dumps({
                **dict(recovered_report.get("summary") or {}),
                "batch_run_hash": str(recovered_report.get("batch_run_hash") or ""),
                "report": str(recovery.get("output") or ""),
                "recovered_from_prepared_result": True,
                "current_pointer_status": str(recovered_pointer.get("status") or "UNKNOWN"),
                "current_pointer_published": recovered_pointer.get("published") is True,
                "current_pointer_blockers": list(recovered_pointer.get("blockers") or []),
            }, ensure_ascii=False, indent=2))
            return 0
        if registration.get("status") != "REGISTERED":
            raise SystemExit(json.dumps({
                "error": "research_registration_not_claimable",
                "registration": registration,
            }, ensure_ascii=False))
        if output.exists():
            raise SystemExit(f"formal research output already exists: {output}")
        protocol = dict(registration.get("protocol") or {})
        frozen_spec = dict(protocol.get("batch_spec") or {})
        if frozen_spec.get("workflow") != RESEARCH_WORKFLOW:
            raise SystemExit("registered protocol is not a nested strategy research workflow")
        if frozen_spec.get("selection_test_policy") != "BLIND_ONCE":
            raise SystemExit("formal research protocol must use BLIND_ONCE")
        frozen_risk = dict(frozen_spec.get("risk") or {})
        build_arguments = {
            "selection_symbols": list(frozen_spec.get("selection_symbols") or []),
            "holdout_symbols": list(frozen_spec.get("confirmation_symbols") or []),
            "strategies": list(frozen_spec.get("strategies") or []),
            "position_pct": frozen_risk.get("position_pct"),
            "take_profit_pct": frozen_risk.get("take_profit_pct"),
            "stop_loss_pct": frozen_risk.get("stop_loss_pct"),
            "fee_rate": frozen_risk.get("fee_rate"),
            "slippage_bps": frozen_risk.get("slippage_bps"),
            "limit": frozen_spec.get("limit"),
            "max_test_candidates": frozen_spec.get("max_test_candidates"),
            "research_generation": frozen_spec.get("research_generation"),
            "selection_test_policy": "BLIND_ONCE",
            "hypothesis_preregistration": frozen_spec.get("hypothesis_preregistration"),
            "search_lineage": frozen_spec.get("search_lineage"),
            "report_schema_version": frozen_spec.get("report_schema_version"),
        }
    else:
        build_arguments = {
            "selection_symbols": args.selection_symbols,
            "holdout_symbols": args.holdout_symbols,
            "strategies": args.strategies,
            "position_pct": args.position_pct,
            "take_profit_pct": args.take_profit_pct,
            "stop_loss_pct": args.stop_loss_pct,
            "fee_rate": args.fee_rate,
            "slippage_bps": args.slippage_bps,
            "limit": args.limit,
            "max_test_candidates": args.max_test_candidates,
            "research_generation": args.research_generation,
            "selection_test_policy": "DEVELOPMENT_ONLY",
            "hypothesis_preregistration": development_hypothesis,
            "search_lineage": None,
            "report_schema_version": STRATEGY_RESEARCH_REPORT_SCHEMA_VERSION,
        }
    try:
        batch_spec = build_research_batch_spec(**build_arguments)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if formal_mode and (
        str(protocol.get("batch_spec_hash") or "") != canonical_hash(batch_spec)
        or protocol_canonical_hash(protocol.get("batch_spec") or {}) != protocol_canonical_hash(batch_spec)
    ):
        raise SystemExit("registered research batch does not match the requested run")

    selection_symbols = list(batch_spec["selection_symbols"])
    holdout_symbols = list(batch_spec["confirmation_symbols"])
    strategies = list(batch_spec["strategies"])
    variants = [dict(variant) for variant in batch_spec["variants"]]
    research_limit = int(batch_spec["limit"])
    report_schema_version = int(batch_spec["report_schema_version"])
    ranking_trial_count = len(variants)
    started_at_ms = time.time_ns() // 1_000_000
    if formal_mode:
        assert registration_store is not None
        claim_exposure = audit_strategy_matrix_holdout_exposure(
            report_dir,
            runtime_dir,
            holdout_symbols,
        )
        claim_result = registration_store.claim(
            args.registration_id,
            clock_attestation=attest_utc_clock(),
            exposure_audit=claim_exposure,
        )
        if not claim_result.get("ok") or claim_result.get("status") != "CLAIMED":
            raise SystemExit(json.dumps({
                "error": "research_registration_claim_blocked",
                "claim": claim_result,
            }, ensure_ascii=False))
        protocol = dict(claim_result.get("protocol") or {})
        claim = dict(claim_result.get("claim") or {})
        started_at_ms = int(claim.get("started_at_ms") or 0)
        if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
            live_lineage = registration_store.verify_search_lineage_live(
                args.registration_id
            )
            if live_lineage.get("status") != "PASS":
                raise SystemExit(json.dumps({
                    "error": "research_search_lineage_live_verification_blocked",
                    "status": "BLOCK",
                    "blockers": list(
                        live_lineage.get("blockers")
                        or [
                            "strategy_search_lineage_live_registry_verification_required"
                        ]
                    ),
                    "selection_data_loaded": False,
                    "test_rows_evaluated": False,
                    "holdout_data_loaded": False,
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }, ensure_ascii=False))
            cumulative_trial_count = live_lineage.get(
                "cumulative_trial_count"
            )
            if (
                isinstance(cumulative_trial_count, bool)
                or not isinstance(cumulative_trial_count, int)
                or cumulative_trial_count < len(variants)
            ):
                raise SystemExit(json.dumps({
                    "error": "research_search_lineage_trial_count_blocked",
                    "status": "BLOCK",
                    "blockers": [
                        "strategy_search_lineage_cumulative_trial_count_invalid"
                    ],
                    "selection_data_loaded": False,
                    "test_rows_evaluated": False,
                    "holdout_data_loaded": False,
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }, ensure_ascii=False))
            ranking_trial_count = cumulative_trial_count

    implementation_manifest = (
        dict(protocol.get("implementation_manifest") or {})
        if formal_mode
        else build_implementation_manifest([Path(__file__).resolve()])
    )

    lineage_prefix = (
        f"strategy-research:{args.registration_id}:{batch_spec['research_schema_version']}"
        if formal_mode
        else f"strategy-research-development:{started_at_ms}:{canonical_hash(batch_spec)[:12]}"
    )
    selection_payloads, selection_manifests, selection_alignment = load_payloads(
        selection_symbols,
        research_limit,
        dataset_lineage_prefix=f"{lineage_prefix}:selection",
        require_frozen_revision=True,
        manifest_role=(
            "SELECTION"
            if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
            else ""
        ),
        capture_alignment_input=(
            report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        ),
    )
    selection_schedule = build_calendar_split_schedule(selection_payloads)
    if selection_alignment.get("status") == "PASS" and selection_schedule.get("status") != "PASS":
        selection_alignment["status"] = "BLOCK"
        selection_alignment["blockers"] = list(dict.fromkeys([
            *(selection_alignment.get("blockers") or []),
            *[f"calendar_split:{item}" for item in selection_schedule.get("blockers") or []],
        ]))
    if (
        report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        and selection_alignment.get("status") == "PASS"
    ):
        selection_manifest_blockers = [
            f"{manifest.get('symbol')}:selection_manifest:{blocker}"
            for manifest in selection_manifests
            if manifest.get("status") != "PASS"
            for blocker in (manifest.get("blockers") or ["status_not_pass"])
        ]
        if selection_manifest_blockers:
            selection_alignment["status"] = "BLOCK"
            selection_alignment["blockers"] = list(dict.fromkeys([
                *(selection_alignment.get("blockers") or []),
                *selection_manifest_blockers,
            ]))
    if not formal_mode and selection_alignment.get("status") == "PASS":
        selection_payloads, selection_schedule, selection_alignment = project_development_selection_data(
            selection_payloads,
            selection_schedule,
            dataset_lineage_prefix=f"{lineage_prefix}:selection",
            report_schema_version=report_schema_version,
        )
        selection_manifests = dataset_manifests(
            selection_payloads,
            require_frozen_revision=True,
        ) if selection_alignment.get("status") == "PASS" else []
        if (
            report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        ):
            selection_manifests = [
                {**item, "role": "SELECTION"} for item in selection_manifests
            ]
            selection_alignment["input_snapshot"] = (
                build_strategy_selection_alignment_input_snapshot(
                    selection_payloads,
                    selection_manifests,
                )
            )
        manifest_blockers = [
            f"{manifest.get('symbol')}:projected_manifest:{blocker}"
            for manifest in selection_manifests
            if manifest.get("status") != "PASS"
            for blocker in (manifest.get("blockers") or ["status_not_pass"])
        ]
        if manifest_blockers:
            selection_alignment["status"] = "BLOCK"
            selection_alignment["blockers"] = list(dict.fromkeys([
                *(selection_alignment.get("blockers") or []),
                *manifest_blockers,
            ]))

    if (
        report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
        and selection_alignment.get("status") != "PASS"
    ):
        raise SystemExit(json.dumps({
            "error": "research_selection_alignment_blocked",
            "status": "BLOCK",
            "blockers": list(
                selection_alignment.get("blockers")
                or ["strategy_selection_alignment_not_passed"]
            ),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }, ensure_ascii=False))

    selection_cells: list[dict[str, Any]] = []
    if selection_alignment.get("status") == "PASS":
        for variant in variants:
            for symbol in selection_symbols:
                selection_cells.append(run_selection_cell(
                    symbol=symbol,
                    variant=variant,
                    payload=selection_payloads[symbol],
                    risk=dict(variant["risk"]),
                    boundaries=(selection_schedule.get("symbol_boundaries") or {}).get(symbol, {}),
                    report_schema_version=report_schema_version,
                ))
    validation_rankings = [
        aggregate_validation_variant(
            variant,
            [cell for cell in selection_cells if cell.get("variant_id") == variant["variant_id"]],
            required_symbols=len(selection_symbols),
            total_variant_trials=ranking_trial_count,
        )
        for variant in variants
    ] if selection_alignment.get("status") == "PASS" else []
    validation_rankings.sort(key=lambda row: float(row.get("adjusted_score") or -1e9), reverse=True)
    parameter_stability = build_parameter_stability_snapshot(
        validation_rankings,
        frozen_variants=variants,
    )
    validation_candidates = freeze_validation_candidates(
        validation_rankings,
        max_candidates=int(batch_spec["max_test_candidates"]),
    )
    preregistered_failure_admission: dict[str, Any] = {}
    if report_schema_version in {
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        if report_schema_version == STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION:
            if not formal_mode or registration_store is None:
                raise SystemExit(
                    "schema 14 admission requires the live canonical registry"
                )
            preregistered_failure_admission = (
                registration_store.build_search_lineage_admission(
                    args.registration_id,
                    parameter_stability=parameter_stability,
                    selection_cells=selection_cells,
                    validation_candidates=validation_candidates,
                )
            )
        else:
            admission_builder = (
                build_strategy_preregistered_failure_admission_v2
                if report_schema_version
                == MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION
                else build_strategy_preregistered_failure_admission
            )
            preregistered_failure_admission = admission_builder(
                batch_spec=batch_spec,
                hypothesis_preregistration=dict(
                    batch_spec.get("hypothesis_preregistration") or {}
                ),
                parameter_stability=parameter_stability,
                selection_cells=selection_cells,
                validation_candidates=validation_candidates,
            )
        admitted_variant_ids = set(
            str(item or "")
            for item in preregistered_failure_admission.get(
                "admitted_variant_ids"
            ) or []
        )
        frozen_candidates = [
            candidate for candidate in validation_candidates
            if formal_mode
            and str(candidate.get("variant_id") or "") in admitted_variant_ids
        ]
    else:
        frozen_candidates = validation_candidates if formal_mode else []

    test_cells: list[dict[str, Any]] = []
    test_results: list[dict[str, Any]] = []
    if formal_mode:
        for candidate in frozen_candidates:
            for symbol in selection_symbols:
                test_cells.append(run_test_cell(
                    symbol=symbol,
                    candidate=candidate,
                    payload=selection_payloads[symbol],
                    risk=dict(candidate["risk"]),
                    boundaries=(selection_schedule.get("symbol_boundaries") or {}).get(symbol, {}),
                    report_schema_version=report_schema_version,
                ))
        test_results = [
            aggregate_frozen_test(
                candidate,
                [cell for cell in test_cells if cell.get("variant_id") == candidate["variant_id"]],
                required_symbols=len(selection_symbols),
            )
            for candidate in frozen_candidates
        ]
        holdout_candidates = [row for row in test_results if row.get("eligible_for_holdout")]
    else:
        holdout_candidates = []

    holdout_cells: list[dict[str, Any]] = []
    holdout_payloads: dict[str, dict[str, Any]] = {}
    holdout_manifests: list[dict[str, Any]] = []
    holdout_alignment: dict[str, Any] = {
        "status": "NOT_RUN",
        "blockers": ["no_test_candidate" if formal_mode else "formal_registration_required"],
    }
    holdout_schedule: dict[str, Any] = {
        "status": "NOT_RUN",
        "blockers": ["no_test_candidate" if formal_mode else "formal_registration_required"],
    }
    if holdout_candidates:
        holdout_payloads, holdout_manifests, holdout_alignment = load_payloads(
            holdout_symbols,
            research_limit,
            required_start=str(selection_alignment.get("common_start") or ""),
            required_as_of=str(selection_alignment.get("common_as_of") or ""),
            dataset_lineage_prefix=f"{lineage_prefix}:holdout",
            require_frozen_revision=True,
            manifest_role=(
                "CONFIRMATION"
                if report_schema_version in REPLAYED_SELECTION_REPORT_SCHEMA_VERSIONS
                else ""
            ),
        )
        if (
            report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS
            and holdout_alignment.get("status") == "PASS"
        ):
            rebuilt_holdout_payloads, rebuilt_holdout_alignment = (
                align_completed_daily_payloads(
                    holdout_payloads,
                    max_endpoint_skew_days=int(
                        batch_spec["data_policy"]["max_endpoint_skew_days"]
                    ),
                    max_boundary_skew_days=int(
                        batch_spec["data_policy"]["max_boundary_skew_days"]
                    ),
                    required_start=str(
                        selection_alignment.get("common_start") or ""
                    ),
                    required_as_of=str(
                        selection_alignment.get("common_as_of") or ""
                    ),
                )
            )
            holdout_payloads = rebuilt_holdout_payloads
            holdout_alignment = rebuilt_holdout_alignment
        holdout_schedule = build_calendar_split_schedule(
            holdout_payloads,
            train_ratio=batch_spec["split_policy"]["train_ratio"],
            validation_ratio=batch_spec["split_policy"][
                "validation_ratio"
            ],
            minimum_segment_rows=batch_spec["split_policy"][
                "minimum_segment_rows"
            ],
        )
        if holdout_alignment.get("status") == "PASS" and holdout_schedule.get("status") != "PASS":
            holdout_alignment["status"] = "BLOCK"
            holdout_alignment["blockers"] = list(dict.fromkeys([
                *(holdout_alignment.get("blockers") or []),
                *[f"calendar_split:{item}" for item in holdout_schedule.get("blockers") or []],
            ]))
        if holdout_alignment.get("status") == "PASS":
            for candidate in holdout_candidates:
                for symbol in holdout_symbols:
                    if report_schema_version in POST_SELECTION_REPLAY_REPORT_SCHEMA_VERSIONS:
                        holdout_cell = run_holdout_replay_cell(
                            symbol=symbol,
                            candidate=candidate,
                            payload=holdout_payloads[symbol],
                            risk=dict(candidate["risk"]),
                            boundaries=(
                                holdout_schedule.get("symbol_boundaries") or {}
                            ).get(symbol, {}),
                            report_schema_version=report_schema_version,
                        )
                    else:
                        holdout_cell = run_holdout_cell(
                            symbol=symbol,
                            strategy_id=str(candidate["strategy_id"]),
                            payload=holdout_payloads[symbol],
                            risk=dict(candidate["risk"]),
                            limit=research_limit,
                            temporal_boundaries=(
                                holdout_schedule.get("symbol_boundaries") or {}
                            ).get(symbol, {}),
                            strategy_params=dict(candidate["params"]),
                        )
                        holdout_cell["variant_id"] = candidate["variant_id"]
                        holdout_cell["source_run_hash"] = holdout_cell.get(
                            "run_hash"
                        )
                        holdout_cell["run_hash"] = (
                            strategy_research_holdout_cell_hash(
                                holdout_cell,
                                candidate,
                            )
                        )
                    holdout_cells.append(holdout_cell)

    holdout_results: list[dict[str, Any]] = []
    for candidate in holdout_candidates:
        summary = aggregate_holdout_confirmation(
            candidate,
            [cell for cell in holdout_cells if cell.get("variant_id") == candidate["variant_id"]],
            required_symbols=len(holdout_symbols),
        )
        summary.update({
            "variant_id": candidate["variant_id"],
            "params": candidate["params"],
            "param_hash": candidate["param_hash"],
        })
        if holdout_alignment.get("status") != "PASS":
            summary["status"] = "BLOCK"
            summary["forward_candidate"] = False
            summary["blockers"] = list(dict.fromkeys([
                *(summary.get("blockers") or []),
                *[f"holdout_alignment:{item}" for item in holdout_alignment.get("blockers") or []],
            ]))
        holdout_results.append(summary)
    forward_candidates = [row["variant_id"] for row in holdout_results if row.get("forward_candidate")]

    dataset_manifest = [*selection_manifests, *holdout_manifests]
    dataset_manifest_hash = canonical_hash(dataset_manifest)
    dataset_snapshot = build_matrix_dataset_snapshot(
        registration_id=str(protocol.get("registration_id") or "DEVELOPMENT_ONLY"),
        batch_spec_hash=canonical_hash(batch_spec),
        dataset_manifest=dataset_manifest,
        selection_payloads=selection_payloads,
        confirmation_payloads=(holdout_payloads if holdout_candidates else {}),
    )
    if formal_mode:
        holdout_exposure_audit = dict(claim.get("holdout_exposure_audit") or {})
    else:
        holdout_exposure_audit = {
            "schema_version": "strategy-matrix-exposure-audit-v1",
            "status": "BLOCK",
            "evaluated_before_data_load": False,
            "symbols": holdout_symbols,
            "exposed_symbols": [],
            "evidence": {},
            "blockers": ["development_run_has_no_blind_holdout_authority"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        holdout_exposure_audit["audit_hash"] = canonical_hash(holdout_exposure_audit)
    payload = {
        "schema_version": report_schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "implementation_manifest": implementation_manifest,
        "batch_spec": batch_spec,
        "batch_spec_hash": canonical_hash(batch_spec),
        "dataset_manifest": dataset_manifest,
        "dataset_manifest_hash": dataset_manifest_hash,
        "dataset_snapshot": dataset_snapshot,
        "selection_alignment": selection_alignment,
        "selection_calendar_schedule": selection_schedule,
        "selection_cells": selection_cells,
        "validation_rankings": validation_rankings,
        "parameter_stability": parameter_stability,
        "validation_candidates": validation_candidates,
        "frozen_candidates": frozen_candidates,
        "test_cells": test_cells,
        "test_results": test_results,
        "holdout_alignment": holdout_alignment,
        "holdout_exposure_audit": holdout_exposure_audit,
        "holdout_calendar_schedule": holdout_schedule,
        "holdout_cells": holdout_cells,
        "holdout_results": holdout_results,
        "forward_candidates": forward_candidates,
        "summary": {
            "strategies": len(strategies),
            "parameter_variants": len(variants),
            "selection_symbols": len(selection_symbols),
            "selection_cells": len(selection_cells),
            "validation_passed_variants": sum(bool(row.get("eligible_for_test")) for row in validation_rankings),
            "validation_raw_excess_candidates": sum(row.get("selection_lane") == "RAW_EXCESS" for row in validation_rankings),
            "validation_risk_adjusted_candidates": sum(row.get("selection_lane") == "RISK_ADJUSTED" for row in validation_rankings),
            "parameter_stability_status": parameter_stability.get("status", "NOT_CHECKED"),
            "parameter_stability_review_count": len([
                row for row in parameter_stability.get("strategies") or []
                if row.get("status") in {"REVIEW", "NOT_ENOUGH_VARIANTS", "BLOCK"}
            ]),
            "frozen_test_candidates": len(frozen_candidates),
            "test_cells": len(test_cells),
            "test_passed_candidates": sum(
                bool(row.get("eligible_for_holdout"))
                for row in test_results
            ),
            "holdout_eligible_candidates": len(holdout_candidates),
            "holdout_cells": len(holdout_cells),
            "forward_candidates": len(forward_candidates),
            "selection_data_status": selection_alignment.get("status", "BLOCK"),
            "common_as_of": selection_alignment.get("common_as_of", ""),
            "test_evaluated_before_candidate_freeze": False,
            "protected_test_rows_persisted": formal_mode,
            "selection_test_policy": str(batch_spec["selection_test_policy"]),
            "formal_single_use_run": formal_mode,
            "holdout_prior_exposure_status": holdout_exposure_audit.get("status", "BLOCK"),
            "holdout_loaded_before_candidate_freeze": False,
            "holdout_requires_test_pass": True,
            "holdout_loaded_before_test_pass": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    if report_schema_version in {
        PREREGISTERED_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        MECHANISM_FAILURE_ADMISSION_REPORT_SCHEMA_VERSION,
        STRATEGY_RESEARCH_FORMAL_REPORT_SCHEMA_VERSION,
    }:
        payload["preregistered_failure_admission"] = preregistered_failure_admission
        payload["summary"]["preregistered_failure_admission_status"] = str(
            preregistered_failure_admission.get("status") or "BLOCK"
        )
        payload["summary"]["preregistered_failure_admitted_candidates"] = len(
            preregistered_failure_admission.get("admitted_variant_ids") or []
        )
    payload["batch_run_hash"] = strategy_research_result_hash(payload)
    if formal_mode:
        assert registration_store is not None
        finalization = finalize_formal_strategy_research_result(
            registration_store=registration_store,
            registration_id=args.registration_id,
            report_dir=report_dir,
            output=output,
            protocol=protocol,
            claim=claim,
            payload=payload,
            completion_clock=attest_utc_clock(),
        )
        if not finalization.get("ok"):
            raise SystemExit(json.dumps({
                "error": "research_formal_finalization_blocked",
                "status": str(finalization.get("status") or "BLOCK"),
                "blockers": list(
                    finalization.get("blockers")
                    or ["strategy_research_formal_finalization_blocked"]
                ),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }, ensure_ascii=False))
        payload = dict(finalization.get("report") or {})
        pointer_publication = dict(finalization.get("pointer_publication") or {})
    else:
        payload["research_governance"] = {
            "schema_version": "strategy-matrix-governance-v2",
            "status": "DEVELOPMENT_SELECTION_ONLY",
            "selection_test_policy": "DEVELOPMENT_ONLY",
            "development_only": True,
            "single_use_claim": False,
            "registration_id": "",
            "protocol_hash": "",
            "claim_hash": "",
            "completion_hash": "",
            "test_rows_evaluated": False,
            "protected_test_rows_persisted": False,
            "holdout_data_loaded": False,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        payload["research_governance"]["governance_hash"] = canonical_hash(payload["research_governance"])
        write_json_atomic(output, payload)
        pointer_publication = _publish_verified_strategy_research_pointer(
            report_dir=report_dir,
            output=output,
            report=payload,
        )
        if pointer_publication.get("published") is not True:
            raise SystemExit(json.dumps({
                "error": "research_pointer_publication_blocked",
                "pointer_publication": pointer_publication,
            }, ensure_ascii=False))
    print(json.dumps({
        **payload["summary"],
        "batch_run_hash": payload["batch_run_hash"],
        "report": str(output),
        "current_pointer_status": str(pointer_publication.get("status") or "UNKNOWN"),
        "current_pointer_published": pointer_publication.get("published") is True,
        "current_pointer_blockers": list(pointer_publication.get("blockers") or []),
        "top_validation_variants": [{
            "strategy_id": row["strategy_id"],
            "variant_id": row["variant_id"],
            "status": row["status"],
            "selection_lane": row.get("selection_lane", "NONE"),
            "adjusted_score": row["adjusted_score"],
            "blockers": row["blockers"],
        } for row in validation_rankings[:6]],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
