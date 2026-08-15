from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import math
from datetime import date
from statistics import fmean, median, pstdev
from typing import Any

try:
    from market_data.candle_contract import candle_is_complete, explicit_boolean
except ModuleNotFoundError:
    from exchange_terminal.market_data.candle_contract import candle_is_complete, explicit_boolean
from .backtest_engine import numeric_parameter_contract_issues, prepare_backtest_dataset
from .corporate_action_ledger import (
    CORPORATE_ACTION_SCHEMA_VERSION,
    build_adjustment_evidence,
    normalize_corporate_actions,
)
from .market_calendar import (
    MARKET_CALENDAR_SCHEMA_VERSION,
    build_market_calendar_contract,
    infer_market_calendar,
)
from .market_data_revision_ledger import MARKET_DATA_REVISION_SCHEMA_VERSION
from .market_regime import MARKET_REGIME_SCHEMA_VERSION, classify_market_regime
from .security_lifecycle import (
    SECURITY_LIFECYCLE_SCHEMA_VERSION,
    align_security_to_market_calendar,
)
from .portfolio_universe import (
    build_static_research_universe_contract,
    eligible_symbols_on,
    verify_universe_contract,
)


PORTFOLIO_BACKTEST_SCHEMA_VERSION = "causal-relative-strength-portfolio-v14"
PORTFOLIO_EXECUTION_MODEL_VERSION = "signal-close-next-open-risk-buffer-point-in-time-universe-portfolio-v8"
PORTFOLIO_DATASET_SCHEMA_VERSION = "portfolio-aligned-market-dataset-v4"


def relative_strength_settings_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Build engine settings without replacing explicit zero values with defaults."""
    source = dict(spec or {})

    def value(name: str, default: Any) -> Any:
        candidate = source.get(name) if name in source else default
        return default if candidate is None else candidate

    return {
        "benchmark_symbol": str(value("benchmark_symbol", "SPY")).upper(),
        "tradable_symbols": [str(symbol).upper() for symbol in value("tradable_symbols", [])],
        "clusters": {
            str(symbol).upper(): str(cluster).upper()
            for symbol, cluster in dict(value("clusters", {})).items()
        },
        "lookback": int(value("lookback", 126)),
        "skip_recent": int(value("skip_recent", 5)),
        "rebalance_interval": int(value("rebalance_interval", 5)),
        "top_n": int(value("top_n", 3)),
        "rank_buffer": int(value("rank_buffer", 2)),
        "gross_target_pct": float(value("gross_target_pct", 60.0)),
        "execution_risk_buffer_pct": float(value("execution_risk_buffer_pct", 0.25)),
        "max_per_cluster": int(value("max_per_cluster", 1)),
        "minimum_trade_pct": float(value("minimum_trade_pct", 1.0)),
        "drawdown_guard_pct": float(value("drawdown_guard_pct", 12.0)),
        "drawdown_cooldown_bars": int(value("drawdown_cooldown_bars", 20)),
        "volatility_window": int(value("volatility_window", 63)),
        "target_portfolio_volatility_pct": float(value("target_portfolio_volatility_pct", 15.0)),
        "max_position_weight_pct": float(value("max_position_weight_pct", 50.0)),
        "liquidity_window": int(value("liquidity_window", 20)),
        "minimum_median_dollar_volume": float(value("minimum_median_dollar_volume", 5_000_000.0)),
        "max_entry_participation_pct": float(value("max_entry_participation_pct", 1.0)),
        "max_exit_participation_pct": float(value("max_exit_participation_pct", 2.0)),
        "max_entry_open_gap_pct": float(value("max_entry_open_gap_pct", 12.0)),
        "impact_bps_at_full_participation": float(value("impact_bps_at_full_participation", 15.0)),
        "fee_rate": float(value("fee_rate", 0.0005)),
        "slippage_bps": float(value("slippage_bps", 2.0)),
    }


def relative_strength_numeric_contract_issues(parameters: dict[str, Any]) -> list[str]:
    numeric_names = (
        "lookback",
        "skip_recent",
        "rebalance_interval",
        "top_n",
        "rank_buffer",
        "gross_target_pct",
        "execution_risk_buffer_pct",
        "max_per_cluster",
        "minimum_trade_pct",
        "drawdown_guard_pct",
        "drawdown_cooldown_bars",
        "volatility_window",
        "target_portfolio_volatility_pct",
        "max_position_weight_pct",
        "liquidity_window",
        "minimum_median_dollar_volume",
        "max_entry_participation_pct",
        "max_exit_participation_pct",
        "max_entry_open_gap_pct",
        "impact_bps_at_full_participation",
        "fee_rate",
        "slippage_bps",
        "initial_cash",
        "evaluation_start_index",
    )
    numeric_parameters = {
        name: parameters.get(name)
        for name in numeric_names
        if name in parameters
    }
    issues = numeric_parameter_contract_issues(
        numeric_parameters,
        positive=("initial_cash", "max_position_weight_pct"),
        integer=(
            "lookback",
            "skip_recent",
            "rebalance_interval",
            "top_n",
            "rank_buffer",
            "max_per_cluster",
            "drawdown_cooldown_bars",
            "volatility_window",
            "liquidity_window",
            "evaluation_start_index",
        ),
        minimum={
            "lookback": 60.0,
            "skip_recent": 0.0,
            "rebalance_interval": 1.0,
            "top_n": 1.0,
            "rank_buffer": 0.0,
            "gross_target_pct": 0.0,
            "execution_risk_buffer_pct": 0.0,
            "max_per_cluster": 1.0,
            "minimum_trade_pct": 0.0,
            "drawdown_guard_pct": 0.0,
            "drawdown_cooldown_bars": 1.0,
            "volatility_window": 20.0,
            "target_portfolio_volatility_pct": 0.0,
            "liquidity_window": 5.0,
            "minimum_median_dollar_volume": 0.0,
            "max_entry_participation_pct": 0.0,
            "max_exit_participation_pct": 0.0,
            "max_entry_open_gap_pct": 0.0,
            "impact_bps_at_full_participation": 0.0,
            "fee_rate": 0.0,
            "slippage_bps": 0.0,
            "evaluation_start_index": 0.0,
        },
        maximum={
            "gross_target_pct": 100.0,
            "execution_risk_buffer_pct": 10.0,
            "minimum_trade_pct": 10.0,
            "drawdown_guard_pct": 50.0,
            "target_portfolio_volatility_pct": 100.0,
            "max_position_weight_pct": 100.0,
            "max_entry_participation_pct": 25.0,
            "max_exit_participation_pct": 50.0,
            "max_entry_open_gap_pct": 100.0,
            "impact_bps_at_full_participation": 500.0,
            "fee_rate": 0.02,
            "slippage_bps": 500.0,
        },
    )
    try:
        if float(numeric_parameters.get("skip_recent")) > float(numeric_parameters.get("lookback")) - 20.0:
            issues.append("skip_recent:must_leave_20_observations")
    except (TypeError, ValueError, OverflowError):
        pass
    return issues


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def slice_portfolio_payload_through_date(
    payload: dict[str, Any],
    cutoff: str,
    *,
    attest_backtest_rows: Callable[..., dict[str, Any]] | None = None,
    dataset_lineage_id: str = "",
) -> dict[str, Any]:
    """Return a cutoff-safe payload and bind its revision proof to the sliced rows."""
    if not cutoff:
        return dict(payload)
    cutoff_date = str(cutoff).strip()[:10]

    def event_date(item: dict[str, Any], *keys: str) -> str:
        return str(next((item.get(key) for key in keys if item.get(key)), "") or "").strip()[:10]

    result = dict(payload)
    result["rows"] = [
        dict(row) for row in payload.get("rows") or []
        if event_date(row, "date") <= cutoff_date
    ]
    result["corporate_actions"] = [
        dict(action) for action in payload.get("corporate_actions") or []
        if event_date(action, "event_date", "date") <= cutoff_date
    ]
    result["trading_status_events"] = [
        dict(event) for event in payload.get("trading_status_events") or []
        if event_date(event, "start_date", "event_date", "date") <= cutoff_date
    ]
    result["adjustment_evidence"] = {}
    existing_revision = dict(payload.get("data_revision_evidence") or {})
    result["data_revision_evidence"] = {
        key: value
        for key, value in existing_revision.items()
        if key not in {"status", "evidence_hash", "backtest_dataset"}
    }
    if attest_backtest_rows is None:
        result["data_revision_evidence"] = {}
        return result

    normalized_actions = normalize_corporate_actions(
        str(payload.get("symbol") or ""),
        str(payload.get("source") or "unknown"),
        list(result.get("corporate_actions") or []),
    )

    return bind_portfolio_payload_revision(
        result,
        attest_backtest_rows=attest_backtest_rows,
        corporate_actions_hash=_canonical_hash(normalized_actions),
        dataset_lineage_id=dataset_lineage_id,
    )


def bind_portfolio_payload_revision(
    payload: dict[str, Any],
    *,
    attest_backtest_rows: Callable[..., dict[str, Any]],
    corporate_actions_hash: str = "",
    dataset_lineage_id: str = "",
) -> dict[str, Any]:
    result = dict(payload)
    existing_revision = dict(payload.get("data_revision_evidence") or {})
    dataset_revision = attest_backtest_rows(
        symbol=str(payload.get("symbol") or ""),
        provider=str(payload.get("source") or ""),
        rows=list(payload.get("rows") or []),
        adjustment_basis=str(payload.get("adjustment_basis") or ""),
        corporate_actions_hash=str(
            corporate_actions_hash
            or dict(payload.get("adjustment_evidence") or {}).get("corporate_actions_hash")
            or ""
        ),
        dataset_lineage_id=str(dataset_lineage_id or ""),
    )
    statuses = {
        str(dict(existing_revision.get("accepted_cache") or {}).get("status") or "PASS").upper(),
        str(dataset_revision.get("status") or "PASS").upper(),
    }
    result["data_revision_evidence"] = {
        **existing_revision,
        "status": "BLOCK" if "BLOCK" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS",
        "backtest_dataset": dataset_revision,
    }
    return result


def prepare_attested_portfolio_dataset(
    payloads: dict[str, dict[str, Any]],
    *,
    benchmark_symbol: str,
    minimum_rows: int,
    attest_backtest_rows: Callable[..., dict[str, Any]],
    dataset_lineage_id: str = "",
    universe_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Align once, attest that exact row set, then build the frozen manifest."""
    initial = prepare_portfolio_dataset(
        payloads,
        benchmark_symbol=benchmark_symbol,
        minimum_rows=minimum_rows,
        universe_contract=universe_contract,
    )
    if initial["status"] != "PASS":
        return {**initial, "payloads": {}}

    rebound: dict[str, dict[str, Any]] = {}
    for symbol in initial["manifest"]["symbols"]:
        source_payload = dict(payloads.get(symbol) or payloads.get(str(symbol).upper()) or {})
        adjustment = dict(initial["manifest"].get("adjustment_evidence", {}).get(symbol) or {})
        rebound[symbol] = bind_portfolio_payload_revision(
            {
                **source_payload,
                "symbol": symbol,
                "rows": list(initial["rows"][symbol]),
                "adjustment_evidence": adjustment,
            },
            attest_backtest_rows=attest_backtest_rows,
            corporate_actions_hash=str(adjustment.get("corporate_actions_hash") or ""),
            dataset_lineage_id=dataset_lineage_id,
        )

    final = prepare_portfolio_dataset(
        rebound,
        benchmark_symbol=benchmark_symbol,
        minimum_rows=minimum_rows,
        universe_contract=universe_contract,
    )
    final["payloads"] = {
        symbol: {
            **rebound[symbol],
            "rows": list(final["rows"].get(symbol) or []),
            "adjustment_evidence": dict(
                final["manifest"].get("adjustment_evidence", {}).get(symbol) or {}
            ),
            "data_revision_evidence": dict(
                final["manifest"].get("data_revision_evidence", {}).get(symbol) or {}
            ),
        }
        for symbol in final["manifest"].get("symbols") or []
    } if final["status"] == "PASS" else {}
    return final


def _revision_dataset_identity(revision: dict[str, Any]) -> dict[str, Any]:
    accepted = dict(revision.get("accepted_cache") or {})
    backtest = dict(revision.get("backtest_dataset") or {})
    revision_status = str(revision.get("status") or "REVIEW").upper()
    accepted_status = str(accepted.get("status") or "PASS").upper()
    backtest_status = str(backtest.get("status") or "REVIEW").upper()
    blocked = "BLOCK" in {revision_status, accepted_status, backtest_status}
    return {
        "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "gate": "BLOCK" if blocked else "NON_BLOCKING",
        "backtest_dataset_snapshot_hash": str(
            dict(backtest.get("current") or {}).get("snapshot_hash") or ""
        ),
        "accepted_cache_blockers": sorted({
            str(reason) for reason in accepted.get("blockers") or [] if str(reason)
        }) if blocked else [],
        "backtest_dataset_blockers": sorted({
            str(reason) for reason in backtest.get("blockers") or [] if str(reason)
        }) if blocked else [],
    }


def portfolio_revision_evidence_hash(revision: dict[str, Any]) -> str:
    return _canonical_hash(_revision_dataset_identity(dict(revision or {})))


def _completed(row: dict[str, Any]) -> bool:
    return candle_is_complete(row, default_if_missing=False)


def _normalize_symbol_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict) or not _completed(raw):
            continue
        try:
            item = {
                "date": str(raw.get("date") or "").strip()[:10],
                "ts_ms": int(raw.get("ts_ms") or raw.get("ts") or 0),
                "open": float(raw.get("open")),
                "high": float(raw.get("high")),
                "low": float(raw.get("low")),
                "close": float(raw.get("close")),
                "volume": float(raw.get("volume") or 0.0),
                "complete": True,
            }
        except (TypeError, ValueError, OverflowError):
            continue
        prices = [item["open"], item["high"], item["low"], item["close"]]
        if (
            not item["date"]
            or not all(math.isfinite(value) and value > 0 for value in prices)
            or not math.isfinite(item["volume"])
            or item["volume"] < 0
            or item["high"] < max(item["open"], item["close"], item["low"])
            or item["low"] > min(item["open"], item["close"], item["high"])
        ):
            continue
        if "tradable" in raw:
            item.update({
                "tradable": explicit_boolean(raw.get("tradable")) is True,
                "trading_status": str(raw.get("trading_status") or "TRADABLE").upper(),
                "calendar_session": explicit_boolean(raw.get("calendar_session", True)) is True,
                "valuation_only": (
                    explicit_boolean(raw.get("valuation_only")) is not False
                    if "valuation_only" in raw else False
                ),
                "valuation_basis": str(raw.get("valuation_basis") or ""),
                "mandatory_cash_settlement": (
                    explicit_boolean(raw.get("mandatory_cash_settlement")) is not False
                    if "mandatory_cash_settlement" in raw else False
                ),
                "lifecycle_event_hash": str(raw.get("lifecycle_event_hash") or ""),
            })
        normalized[item["date"]] = item
    return normalized


def prepare_portfolio_dataset(
    payloads: dict[str, dict[str, Any]],
    *,
    benchmark_symbol: str,
    minimum_rows: int,
    universe_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_payloads = {str(symbol).upper(): dict(payload or {}) for symbol, payload in payloads.items()}
    benchmark = str(benchmark_symbol or "").upper()
    blockers: list[str] = []
    warnings: list[str] = []
    if benchmark not in clean_payloads:
        blockers.append(f"benchmark_missing:{benchmark or '--'}")
    active_universe_contract = dict(universe_contract or {})
    universe_verification = verify_universe_contract(active_universe_contract) if active_universe_contract else {}
    point_in_time_verified = bool(
        active_universe_contract
        and universe_verification.get("status") == "PASS"
        and universe_verification.get("historical_membership_verified") is True
        and universe_verification.get("point_in_time_constituents") is True
    )
    if active_universe_contract:
        blockers.extend(
            f"universe:{item}"
            for item in universe_verification.get("blockers") or []
        )
        declared_benchmark = str(active_universe_contract.get("benchmark_symbol") or "").upper()
        declared_tradables = {
            str(symbol or "").upper()
            for symbol in active_universe_contract.get("tradable_symbols") or []
            if str(symbol or "")
        }
        payload_tradables = set(clean_payloads) - {benchmark}
        if declared_benchmark != benchmark:
            blockers.append("universe:benchmark_mismatch")
        if declared_tradables != payload_tradables:
            blockers.append("universe:tradable_symbols_mismatch")
    membership_starts = {
        symbol: min(
            (
                str(item.get("effective_from") or "")
                for item in active_universe_contract.get("membership_records") or []
                if str(item.get("symbol") or "").upper() == symbol
                and str(item.get("effective_from") or "")
            ),
            default="",
        )
        for symbol in clean_payloads
        if symbol != benchmark
    } if point_in_time_verified else {}
    benchmark_input_dates: list[str] = []
    for row in list((clean_payloads.get(benchmark) or {}).get("rows") or []):
        if not isinstance(row, dict) or not _completed(row):
            continue
        raw_date = str(row.get("date") or "").strip()[:10]
        try:
            benchmark_input_dates.append(date.fromisoformat(raw_date).isoformat())
        except ValueError:
            continue
    benchmark_input_end = max(benchmark_input_dates, default="")
    required = max(int(minimum_rows), 2)
    symbol_manifests: dict[str, dict[str, Any]] = {}
    adjustment_evidence: dict[str, dict[str, Any]] = {}
    data_revision_evidence: dict[str, dict[str, Any]] = {}
    lifecycle_contracts: dict[str, dict[str, Any]] = {}
    corporate_actions: dict[str, list[dict[str, Any]]] = {}
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    pre_membership_only_symbols: set[str] = set()
    for symbol, payload in clean_payloads.items():
        source = str(payload.get("origin_source") or payload.get("source") or "")
        raw_rows = [dict(row) for row in payload.get("rows") or [] if isinstance(row, dict)]
        observed_raw_rows = [
            row
            for row in raw_rows
            if not (
                row.get("valuation_only") is True
                and row.get("tradable") is False
                and str(row.get("trading_status") or "").upper() == "OUTSIDE_UNIVERSE"
                and str(row.get("valuation_basis") or "") == "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL"
            )
        ]
        pre_membership_only = bool(
            point_in_time_verified
            and symbol != benchmark
            and membership_starts.get(symbol)
            and benchmark_input_end
            and benchmark_input_end < membership_starts[symbol]
            and not observed_raw_rows
        )
        if pre_membership_only:
            pre_membership_only_symbols.add(symbol)
        lifecycle_metadata_by_date = {
            str(row.get("date") or "")[:10]: {
                key: row.get(key)
                for key in (
                    "tradable",
                    "trading_status",
                    "calendar_session",
                    "valuation_only",
                    "valuation_basis",
                    "mandatory_cash_settlement",
                    "lifecycle_event_hash",
                )
                if key in row
            }
            for row in raw_rows
            if str(row.get("date") or "")
        }
        quality = prepare_backtest_dataset(
            raw_rows,
            symbol=symbol,
            source=source,
            timeframe="1D",
            minimum_rows=(2 if point_in_time_verified and symbol != benchmark else required),
            market="stock",
            daily_continuity_policy="DEFER_TO_PORTFOLIO_LIFECYCLE",
        )
        symbol_manifests[symbol] = dict(quality.get("manifest") or {})
        if pre_membership_only:
            symbol_manifests[symbol] = {
                **symbol_manifests[symbol],
                "status": "PASS",
                "blockers": [],
                "warnings": [
                    *list(symbol_manifests[symbol].get("warnings") or []),
                    "outside_universe_before_first_membership_no_market_rows",
                ],
                "pre_membership_only": True,
            }
        elif symbol_manifests[symbol].get("status") != "PASS":
            reasons = symbol_manifests[symbol].get("blockers") or ["dataset_quality_blocked"]
            blockers.extend(f"{symbol}:{reason}" for reason in reasons)
        validated_rows = [
            {
                **dict(row),
                **lifecycle_metadata_by_date.get(str(row.get("date") or "")[:10], {}),
            }
            for row in quality.get("rows") or []
        ]
        normalized[symbol] = _normalize_symbol_rows(validated_rows)
        observed_adjustment_rows = [
            row
            for row in validated_rows
            if not (
                row.get("valuation_only") is True
                and row.get("tradable") is False
                and str(row.get("trading_status") or "").upper() == "OUTSIDE_UNIVERSE"
                and str(row.get("valuation_basis") or "") == "NO_POSITION_OUTSIDE_UNIVERSE_SENTINEL"
            )
        ]
        evidence = build_adjustment_evidence(
            symbol=symbol,
            rows=observed_adjustment_rows,
            source=source,
            adjustment_basis=str(payload.get("adjustment_basis") or ""),
            corporate_actions=list(payload.get("corporate_actions") or []),
            corporate_action_coverage=str(payload.get("corporate_action_coverage") or ""),
            interval="1d",
            session="regular",
        )
        adjustment_evidence[symbol] = evidence
        corporate_actions[symbol] = normalize_corporate_actions(
            symbol,
            source,
            list(payload.get("corporate_actions") or []),
        )
        if evidence.get("backtest_eligible") is not True:
            blockers.extend(
                f"{symbol}:adjustment:{reason}"
                for reason in (evidence.get("blockers") or ["unverified_adjustment_contract"])
            )
        revision = dict(payload.get("data_revision_evidence") or {})
        if revision:
            revision["evidence_hash"] = portfolio_revision_evidence_hash(revision)
            data_revision_evidence[symbol] = revision
            revision_status = str(revision.get("status") or "REVIEW").upper()
            if revision_status == "BLOCK":
                revision_blockers = [
                    *list(dict(revision.get("accepted_cache") or {}).get("blockers") or []),
                    *list(dict(revision.get("backtest_dataset") or {}).get("blockers") or []),
                ]
                blockers.extend(
                    f"{symbol}:data_revision:{reason}"
                    for reason in (revision_blockers or ["unresolved_revision_evidence"])
                )
            elif revision_status == "REVIEW":
                warnings.append(f"{symbol}:data_revision_review_required")
            cross_source_rows = [
                dict(item) for item in revision.get("cross_source") or [] if isinstance(item, dict)
            ]
            cross_source_statuses = {str(item.get("status") or "REVIEW").upper() for item in cross_source_rows}
            if "BLOCK" in cross_source_statuses:
                cross_blockers = [
                    reason
                    for item in cross_source_rows
                    for reason in list(item.get("blockers") or [])
                ]
                blockers.extend(
                    f"{symbol}:cross_source:{reason}"
                    for reason in (cross_blockers or ["independent_source_divergence"])
                )
            elif "REVIEW" in cross_source_statuses:
                warnings.append(f"{symbol}:cross_source_review_required")
    for symbol, rows in normalized.items():
        if not rows and symbol not in pre_membership_only_symbols:
            blockers.append(f"{symbol}:no_completed_rows")

    first_dates = {symbol: min(rows) for symbol, rows in normalized.items() if rows}
    last_dates = {symbol: max(rows) for symbol, rows in normalized.items() if rows}
    coverage_start = (
        first_dates.get(benchmark, "")
        if point_in_time_verified
        else max(first_dates.values()) if len(first_dates) == len(normalized) and first_dates else ""
    )
    coverage_end = last_dates.get(benchmark, "")
    benchmark_payload = clean_payloads.get(benchmark) or {}
    calendar_name = infer_market_calendar(
        benchmark,
        source=str(benchmark_payload.get("origin_source") or benchmark_payload.get("source") or ""),
        explicit=str(benchmark_payload.get("market_calendar") or ""),
    )
    benchmark_observed = sorted(
        session_date
        for session_date in (normalized.get(benchmark) or {})
        if coverage_start and coverage_end and coverage_start <= session_date <= coverage_end
    )
    calendar_contract = build_market_calendar_contract(
        calendar_name=calendar_name,
        start_date=coverage_start,
        end_date=coverage_end,
        observed_dates=benchmark_observed,
    )
    if calendar_contract.get("status") != "PASS":
        blockers.extend(f"calendar:{reason}" for reason in calendar_contract.get("blockers") or ["calendar_contract_blocked"])
    expected_dates = list(calendar_contract.get("expected_dates") or [])
    if len(expected_dates) < required:
        blockers.append(f"calendar_rows:{len(expected_dates)}<{required}")

    aligned: dict[str, list[dict[str, Any]]] = {}
    coverage: dict[str, dict[str, Any]] = {}
    for symbol, rows in normalized.items():
        window_rows = {
            session_date: dict(row)
            for session_date, row in rows.items()
            if coverage_start and coverage_end and coverage_start <= session_date <= coverage_end
        }
        lifecycle = align_security_to_market_calendar(
            symbol=symbol,
            rows_by_date=window_rows,
            expected_dates=expected_dates,
            lifecycle_events=list(clean_payloads[symbol].get("trading_status_events") or []),
            universe_membership_start=(membership_starts.get(symbol, "") if point_in_time_verified else ""),
            universe_contract_hash=(
                str(active_universe_contract.get("contract_hash") or "")
                if point_in_time_verified and symbol != benchmark else ""
            ),
        )
        lifecycle_contracts[symbol] = {key: value for key, value in lifecycle.items() if key != "rows"}
        aligned[symbol] = list(lifecycle.get("rows") or [])
        if lifecycle.get("status") != "PASS":
            blockers.extend(
                f"{symbol}:lifecycle:{reason}"
                for reason in lifecycle.get("blockers") or ["security_lifecycle_blocked"]
            )
        excluded_prefix = sum(1 for session_date in rows if coverage_start and session_date < coverage_start)
        after_benchmark = sorted(session_date for session_date in rows if coverage_end and session_date > coverage_end)
        if after_benchmark:
            blockers.append(f"{symbol}:rows_after_benchmark_end:{len(after_benchmark)}")
        coverage[symbol] = {
            "raw_first": first_dates.get(symbol, ""),
            "raw_last": last_dates.get(symbol, ""),
            "universe_membership_start": membership_starts.get(symbol, ""),
            "excluded_prefix_sessions": excluded_prefix,
            "rows_after_benchmark_end": after_benchmark,
            "aligned_session_count": len(aligned[symbol]),
            "outside_universe_session_count": int(lifecycle.get("outside_universe_session_count") or 0),
        }
    excluded_market_prefix = 0
    if benchmark in normalized and coverage_start:
        excluded_market_prefix = sum(1 for session_date in normalized[benchmark] if session_date < coverage_start)
        if excluded_market_prefix:
            warnings.append(f"universe_common_coverage_excludes_benchmark_prefix:{excluded_market_prefix}")

    data_content = {
        "schema_version": PORTFOLIO_DATASET_SCHEMA_VERSION,
        "benchmark_symbol": benchmark,
        "symbols": sorted(aligned),
        "universe_contract_hash": str(active_universe_contract.get("contract_hash") or ""),
        "point_in_time_universe_verified": point_in_time_verified,
        "market_calendar_schema_version": MARKET_CALENDAR_SCHEMA_VERSION,
        "market_data_revision_schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "market_calendar_hash": calendar_contract.get("contract_hash", ""),
        "market_calendar_schedule_hash": calendar_contract.get("schedule_hash", ""),
        "security_lifecycle_schema_version": SECURITY_LIFECYCLE_SCHEMA_VERSION,
        "security_lifecycle_hashes": {
            symbol: lifecycle_contracts[symbol].get("contract_hash", "")
            for symbol in sorted(lifecycle_contracts)
        },
        "common_dates": expected_dates,
        "rows": aligned,
        "adjustment_evidence_hashes": {
            symbol: adjustment_evidence[symbol].get("evidence_hash", "")
            for symbol in sorted(adjustment_evidence)
        },
        "data_revision_evidence_hashes": {
            symbol: data_revision_evidence[symbol].get("evidence_hash", "")
            for symbol in sorted(data_revision_evidence)
        },
        "corporate_action_hashes": {
            symbol: _canonical_hash(corporate_actions[symbol])
            for symbol in sorted(corporate_actions)
        },
    }
    data_hash = _canonical_hash(data_content)
    manifest_contract = {
        "schema_version": PORTFOLIO_DATASET_SCHEMA_VERSION,
        "data_hash": data_hash,
        "universe_contract_hash": data_content["universe_contract_hash"],
        "market_calendar_hash": calendar_contract.get("contract_hash", ""),
        "security_lifecycle_hashes": data_content["security_lifecycle_hashes"],
        "adjustment_evidence_hashes": data_content["adjustment_evidence_hashes"],
        "data_revision_evidence_hashes": data_content["data_revision_evidence_hashes"],
        "corporate_action_hashes": data_content["corporate_action_hashes"],
    }
    manifest = {
        "schema_version": PORTFOLIO_DATASET_SCHEMA_VERSION,
        "strategy_schema_version": PORTFOLIO_BACKTEST_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": warnings,
        "benchmark_symbol": benchmark,
        "symbols": sorted(aligned),
        "symbol_count": len(aligned),
        "row_count": len(expected_dates),
        "first": expected_dates[0] if expected_dates else "",
        "last": expected_dates[-1] if expected_dates else "",
        "data_hash": data_hash,
        "manifest_hash": _canonical_hash(manifest_contract),
        "universe_contract_hash": data_content["universe_contract_hash"],
        "point_in_time_universe_verified": point_in_time_verified,
        "market_data_revision_schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "market_calendar": calendar_contract,
        "security_lifecycle": lifecycle_contracts,
        "coverage": {
            "policy": (
                "OFFICIAL_BENCHMARK_CALENDAR_WITH_POINT_IN_TIME_PREMEMBERSHIP_GAPS"
                if point_in_time_verified
                else "OFFICIAL_BENCHMARK_CALENDAR_WITH_DECLARED_SECURITY_GAPS"
            ),
            "start": coverage_start,
            "end": coverage_end,
            "excluded_benchmark_prefix_sessions": excluded_market_prefix,
            "symbols": coverage,
        },
        "sources": {
            symbol: str(clean_payloads[symbol].get("source") or "")
            for symbol in sorted(clean_payloads)
        },
        "symbol_manifests": symbol_manifests,
        "adjustment_evidence": adjustment_evidence,
        "data_revision_evidence": data_revision_evidence,
        "corporate_actions": corporate_actions,
    }
    return {
        "status": manifest["status"],
        "rows": aligned,
        "dates": expected_dates,
        "corporate_actions": corporate_actions,
        "manifest": manifest,
    }


def _max_drawdown(values: list[float]) -> float:
    peak = 0.0
    maximum = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            maximum = max(maximum, 1.0 - value / peak)
    return maximum


def _sharpe(values: list[float], periods_per_year: int = 252) -> float:
    returns = [current / previous - 1.0 for previous, current in zip(values[:-1], values[1:]) if previous > 0]
    if len(returns) < 2:
        return 0.0
    deviation = pstdev(returns)
    return fmean(returns) / deviation * math.sqrt(periods_per_year) if deviation > 0 else 0.0


def _capped_weights(raw_weights: dict[str, float], maximum_weight: float) -> dict[str, float]:
    symbols = sorted(raw_weights)
    if not symbols:
        return {}
    cap = max(0.0, min(float(maximum_weight), 1.0))
    remaining = set(symbols)
    result = {symbol: 0.0 for symbol in symbols}
    remaining_budget = 1.0
    while remaining:
        denominator = sum(max(raw_weights[symbol], 0.0) for symbol in remaining)
        if denominator <= 1e-15:
            equal = remaining_budget / len(remaining)
            for symbol in remaining:
                result[symbol] = equal
            break
        capped = []
        for symbol in remaining:
            proposed = remaining_budget * max(raw_weights[symbol], 0.0) / denominator
            if proposed > cap + 1e-12:
                result[symbol] = cap
                remaining_budget -= cap
                capped.append(symbol)
        if not capped:
            for symbol in remaining:
                result[symbol] = remaining_budget * max(raw_weights[symbol], 0.0) / denominator
            break
        remaining.difference_update(capped)
    return {symbol: max(min(value, cap), 0.0) for symbol, value in result.items()}


def run_causal_relative_strength_backtest(
    *,
    payloads: dict[str, dict[str, Any]],
    benchmark_symbol: str,
    tradable_symbols: list[str] | None = None,
    clusters: dict[str, str] | None = None,
    lookback: int = 126,
    skip_recent: int = 5,
    rebalance_interval: int = 5,
    top_n: int = 3,
    rank_buffer: int = 2,
    gross_target_pct: float = 60.0,
    execution_risk_buffer_pct: float = 0.25,
    max_per_cluster: int = 1,
    minimum_trade_pct: float = 1.0,
    drawdown_guard_pct: float = 12.0,
    drawdown_cooldown_bars: int = 20,
    volatility_window: int = 63,
    target_portfolio_volatility_pct: float = 15.0,
    max_position_weight_pct: float = 50.0,
    liquidity_window: int = 20,
    minimum_median_dollar_volume: float = 5_000_000.0,
    max_entry_participation_pct: float = 1.0,
    max_exit_participation_pct: float = 2.0,
    max_entry_open_gap_pct: float = 12.0,
    impact_bps_at_full_participation: float = 15.0,
    fee_rate: float = 0.0005,
    slippage_bps: float = 2.0,
    initial_cash: float = 100_000.0,
    evaluation_start_index: int | None = None,
    universe_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    numeric_issues = relative_strength_numeric_contract_issues(
        {
            "lookback": lookback,
            "skip_recent": skip_recent,
            "rebalance_interval": rebalance_interval,
            "top_n": top_n,
            "rank_buffer": rank_buffer,
            "gross_target_pct": gross_target_pct,
            "execution_risk_buffer_pct": execution_risk_buffer_pct,
            "max_per_cluster": max_per_cluster,
            "minimum_trade_pct": minimum_trade_pct,
            "drawdown_guard_pct": drawdown_guard_pct,
            "drawdown_cooldown_bars": drawdown_cooldown_bars,
            "volatility_window": volatility_window,
            "target_portfolio_volatility_pct": target_portfolio_volatility_pct,
            "max_position_weight_pct": max_position_weight_pct,
            "liquidity_window": liquidity_window,
            "minimum_median_dollar_volume": minimum_median_dollar_volume,
            "max_entry_participation_pct": max_entry_participation_pct,
            "max_exit_participation_pct": max_exit_participation_pct,
            "max_entry_open_gap_pct": max_entry_open_gap_pct,
            "impact_bps_at_full_participation": impact_bps_at_full_participation,
            "fee_rate": fee_rate,
            "slippage_bps": slippage_bps,
            "initial_cash": initial_cash,
            "evaluation_start_index": evaluation_start_index,
        }
    )
    if numeric_issues:
        return {
            "ok": False,
            "error": "Portfolio numeric parameter contract failed: " + ", ".join(numeric_issues),
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    clean_benchmark = str(benchmark_symbol or "").upper()
    clean_lookback = max(int(float(lookback)), 60)
    clean_skip = max(0, min(int(float(skip_recent)), clean_lookback - 20))
    clean_rebalance = max(int(float(rebalance_interval)), 1)
    clean_top_n = max(int(float(top_n)), 1)
    clean_rank_buffer = max(int(float(rank_buffer)), 0)
    clean_max_per_cluster = max(int(float(max_per_cluster)), 1)
    startup = max(clean_lookback + 1, 121)
    clean_payloads = {
        str(symbol).upper(): dict(payload or {})
        for symbol, payload in payloads.items()
    }
    available_symbols = sorted(clean_payloads)
    requested = [
        str(symbol).upper()
        for symbol in (tradable_symbols or available_symbols)
        if str(symbol).upper() != clean_benchmark
    ]
    tradable = [
        symbol
        for symbol in dict.fromkeys(requested)
        if symbol in clean_payloads
    ]
    if not tradable:
        return {
            "ok": False,
            "error": "No available tradable symbols.",
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    active_universe_contract = dict(universe_contract or build_static_research_universe_contract(
        benchmark_symbol=clean_benchmark,
        tradable_symbols=tradable,
        declared_at="1970-01-01T00:00:00Z",
        selection_basis="EXPLICIT_TRADABLE_SYMBOL_ARGUMENT",
    ))
    universe_verification = verify_universe_contract(active_universe_contract)
    universe_blockers = list(universe_verification.get("blockers") or [])
    if str(active_universe_contract.get("benchmark_symbol") or "") != clean_benchmark:
        universe_blockers.append("universe_benchmark_mismatch")
    if set(active_universe_contract.get("tradable_symbols") or []) != set(tradable):
        universe_blockers.append("universe_tradable_symbols_mismatch")
    if universe_blockers:
        return {
            "ok": False,
            "error": "Portfolio universe contract gate failed.",
            "universe_contract": active_universe_contract,
            "universe_verification": {
                **universe_verification,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(universe_blockers)),
            },
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    selected_payloads = {
        symbol: clean_payloads[symbol]
        for symbol in [clean_benchmark, *tradable]
        if symbol in clean_payloads
    }
    prepared = prepare_portfolio_dataset(
        selected_payloads,
        benchmark_symbol=clean_benchmark,
        minimum_rows=startup + 2,
        universe_contract=active_universe_contract,
    )
    manifest = prepared["manifest"]
    if manifest["status"] != "PASS":
        return {
            "ok": False,
            "error": "Portfolio dataset gate failed.",
            "dataset_manifest": manifest,
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    rows_by_symbol = prepared["rows"]
    dates = prepared["dates"]
    corporate_actions_by_symbol = dict(prepared.get("corporate_actions") or {})
    return_accounting_by_symbol = {
        symbol: dict((manifest.get("adjustment_evidence", {}).get(symbol) or {}).get("return_accounting") or {})
        for symbol in rows_by_symbol
    }
    if clean_rebalance != 5:
        return {
            "ok": False,
            "error": "The portfolio engine currently supports only the calendar-anchored weekly rebalance contract.",
            "dataset_manifest": manifest,
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    evaluation_start = startup if evaluation_start_index is None else max(startup, int(float(evaluation_start_index)))
    if evaluation_start >= len(dates):
        return {
            "ok": False,
            "error": "Evaluation window starts after the available portfolio dataset.",
            "dataset_manifest": manifest,
            "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    cluster_map = {str(symbol).upper(): str(cluster or symbol).upper() for symbol, cluster in dict(clusters or {}).items()}
    fee = max(0.0, min(float(fee_rate), 0.02))
    slippage_rate = max(0.0, min(float(slippage_bps), 500.0)) / 10_000.0
    target_gross = max(0.0, min(float(gross_target_pct), 100.0)) / 100.0
    execution_risk_buffer = max(0.0, min(float(execution_risk_buffer_pct), 10.0)) / 100.0
    minimum_trade_fraction = max(0.0, min(float(minimum_trade_pct), 10.0)) / 100.0
    drawdown_guard = max(0.0, min(float(drawdown_guard_pct), 50.0)) / 100.0
    cooldown_bars = max(int(float(drawdown_cooldown_bars)), 1)
    clean_volatility_window = max(int(float(volatility_window)), 20)
    clean_liquidity_window = max(int(float(liquidity_window)), 5)
    minimum_dollar_volume = max(float(minimum_median_dollar_volume), 0.0)
    entry_participation = max(0.0, min(float(max_entry_participation_pct), 25.0)) / 100.0
    exit_participation = max(0.0, min(float(max_exit_participation_pct), 50.0)) / 100.0
    maximum_entry_gap = max(0.0, min(float(max_entry_open_gap_pct), 100.0)) / 100.0
    impact_at_full_participation = max(0.0, min(float(impact_bps_at_full_participation), 500.0))
    target_portfolio_volatility = max(0.0, min(float(target_portfolio_volatility_pct), 100.0)) / 100.0
    max_position_weight = max(0.0, min(float(max_position_weight_pct), 100.0)) / 100.0
    cash = float(initial_cash)
    quantities = {symbol: 0.0 for symbol in tradable}
    total_fees = 0.0
    turnover = 0.0
    orders: list[dict[str, Any]] = []
    execution_events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []
    selection_counts = {symbol: 0 for symbol in tradable}
    peak_equity = float(initial_cash)
    drawdown_guard_active = False
    risk_off_until_index = -1
    risk_off_event_count = 0
    liquidity_block_count = 0
    gap_block_count = 0
    partial_fill_count = 0
    tradability_block_count = 0
    total_dividends = 0.0
    dividend_cash_paid = 0.0
    dividend_receivables: list[dict[str, Any]] = []
    corporate_action_events: list[dict[str, Any]] = []
    processed_action_ids: set[str] = set()
    pending_exit_targets: dict[str, float] = {}

    def is_observed_tradable_row(row: dict[str, Any]) -> bool:
        return (
            row.get("tradable") is True
            and row.get("valuation_only") is not True
            and str(row.get("trading_status") or "").upper() == "TRADABLE"
            and float(row.get("close") or 0.0) > 0
        )

    def receivable_balance() -> float:
        return sum(float(item.get("amount") or 0.0) for item in dividend_receivables if not item.get("settled"))

    def apply_pre_open_events(index: int) -> dict[str, float]:
        nonlocal cash, total_dividends, dividend_cash_paid
        session_date = dates[index]
        quantity_adjustments: dict[str, float] = {}
        for symbol in tradable:
            policy = return_accounting_by_symbol.get(symbol) or {}
            actions = list(corporate_actions_by_symbol.get(symbol) or [])
            if str(policy.get("split_mode") or "") == "EXPLICIT_QUANTITY_ADJUSTMENT":
                for action in actions:
                    action_id = str(action.get("action_id") or _canonical_hash(action))
                    if (
                        action_id in processed_action_ids
                        or action.get("action_type") != "SPLIT"
                        or str(action.get("event_date") or "") != session_date
                    ):
                        continue
                    processed_action_ids.add(action_id)
                    ratio = float(action.get("ratio") or 0.0)
                    previous_quantity = quantities[symbol]
                    if ratio > 0:
                        quantity_adjustments[symbol] = quantity_adjustments.get(symbol, 1.0) * ratio
                    if previous_quantity > 1e-12 and ratio > 0:
                        quantities[symbol] = previous_quantity * ratio
                        if symbol in pending_exit_targets:
                            pending_exit_targets[symbol] *= ratio
                        corporate_action_events.append({
                            "date": session_date,
                            "symbol": symbol,
                            "action_type": "SPLIT_QUANTITY_ADJUSTMENT",
                            "action_id": action_id,
                            "ratio": round(ratio, 8),
                            "quantity_before": round(previous_quantity, 10),
                            "quantity_after": round(quantities[symbol], 10),
                        })
            if str(policy.get("dividend_mode") or "") == "EXPLICIT_PAY_DATE_CASH":
                for action in actions:
                    action_id = str(action.get("action_id") or _canonical_hash(action))
                    if (
                        action_id in processed_action_ids
                        or action.get("action_type") != "DIVIDEND"
                        or str(action.get("event_date") or "") != session_date
                    ):
                        continue
                    processed_action_ids.add(action_id)
                    cash_amount = float(action.get("cash_amount") or 0.0)
                    quantity = quantities[symbol]
                    entitlement = quantity * cash_amount
                    if quantity <= 1e-12 or cash_amount <= 0:
                        continue
                    receivable = {
                        "action_id": action_id,
                        "symbol": symbol,
                        "ex_date": session_date,
                        "pay_date": str(action.get("pay_date") or ""),
                        "quantity": quantity,
                        "cash_per_share": cash_amount,
                        "amount": entitlement,
                        "settled": False,
                    }
                    dividend_receivables.append(receivable)
                    total_dividends += entitlement
                    corporate_action_events.append({
                        "date": session_date,
                        "symbol": symbol,
                        "action_type": "DIVIDEND_RECEIVABLE_ACCRUED",
                        "action_id": action_id,
                        "pay_date": receivable["pay_date"],
                        "quantity": round(quantity, 10),
                        "cash_per_share": round(cash_amount, 8),
                        "amount": round(entitlement, 6),
                    })

        for receivable in dividend_receivables:
            if receivable.get("settled") or str(receivable.get("pay_date") or "") > session_date:
                continue
            amount = float(receivable.get("amount") or 0.0)
            cash += amount
            dividend_cash_paid += amount
            receivable["settled"] = True
            receivable["settled_date"] = session_date
            corporate_action_events.append({
                "date": session_date,
                "symbol": receivable.get("symbol", ""),
                "action_type": "DIVIDEND_CASH_SETTLED",
                "action_id": receivable.get("action_id", ""),
                "pay_date": receivable.get("pay_date", ""),
                "amount": round(amount, 6),
            })

        for symbol in tradable:
            row = rows_by_symbol[symbol][index]
            if not row.get("mandatory_cash_settlement"):
                continue
            quantity = quantities[symbol]
            pending_exit_targets.pop(symbol, None)
            if quantity <= 1e-12:
                continue
            settlement_price = float(row["open"])
            amount = quantity * settlement_price
            cash += amount
            quantities[symbol] = 0.0
            corporate_action_events.append({
                "date": session_date,
                "symbol": symbol,
                "action_type": "DELISTING_CASH_SETTLEMENT",
                "lifecycle_event_hash": row.get("lifecycle_event_hash", ""),
                "quantity": round(quantity, 10),
                "settlement_price": round(settlement_price, 8),
                "amount": round(amount, 6),
            })

        return quantity_adjustments

    def liquidity_at(symbol: str, index: int) -> dict[str, Any]:
        start = max(0, index - clean_liquidity_window + 1)
        observations = [
            float(row["close"]) * float(row.get("volume") or 0.0)
            for row in rows_by_symbol[symbol][start:index + 1]
            if (
                is_observed_tradable_row(row)
                and float(row.get("volume") or 0.0) > 0
            )
        ]
        median_dollar_volume = median(observations) if observations else 0.0
        return {
            "window": clean_liquidity_window,
            "observation_count": len(observations),
            "median_dollar_volume": round(median_dollar_volume, 2),
            "minimum_median_dollar_volume": round(minimum_dollar_volume, 2),
            "eligible": len(observations) >= clean_liquidity_window and median_dollar_volume >= minimum_dollar_volume,
            "as_of": dates[index],
        }

    def membership_at(index: int) -> dict[str, Any]:
        return eligible_symbols_on(active_universe_contract, dates[index], tradable)

    def decision_at(index: int) -> dict[str, Any]:
        score_end = index - clean_skip
        score_start = index - clean_lookback
        scores: dict[str, float] = {}
        if score_start < 0 or score_end <= score_start:
            return {"signal_date": dates[index], "target_symbols": [], "target_allocation_pct": 0.0, "scores": {}, "reason": "insufficient_history", "execute": True}
        membership = membership_at(index)
        eligible_tradable = list(membership.get("eligible_symbols") or [])
        history_start = min(
            score_start,
            index - clean_volatility_window,
            index - clean_liquidity_window + 1,
        )
        causal_history: dict[str, dict[str, Any]] = {}
        for symbol in eligible_tradable:
            history_rows = (
                rows_by_symbol[symbol][history_start:index + 1]
                if history_start >= 0 else []
            )
            expected_history_count = index - history_start + 1 if history_start >= 0 else 0
            observed_history_count = sum(
                1 for row in history_rows if is_observed_tradable_row(row)
            )
            history_eligible = bool(
                history_start >= 0
                and len(history_rows) == expected_history_count
                and observed_history_count == expected_history_count
            )
            causal_history[symbol] = {
                "status": "PASS" if history_eligible else "INSUFFICIENT",
                "start_date": dates[history_start] if history_start >= 0 else "",
                "end_date": dates[index],
                "expected_observation_count": expected_history_count,
                "observed_tradable_count": observed_history_count,
            }
            if not history_eligible:
                continue
            start_close = float(rows_by_symbol[symbol][score_start]["close"])
            end_close = float(rows_by_symbol[symbol][score_end]["close"])
            scores[symbol] = end_close / max(start_close, 1e-12) - 1.0
        regime = classify_market_regime(rows_by_symbol[clean_benchmark][:index + 1], market="stock")
        regime_multiplier = float(regime.get("long_only_budget_multiplier") or 0.0) if regime.get("status") == "PASS" else 0.0
        liquidity = {symbol: liquidity_at(symbol, index) for symbol in eligible_tradable}
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        rank_by_symbol = {symbol: rank for rank, (symbol, _score) in enumerate(ranked, start=1)}
        selected: list[str] = []
        retained: list[str] = []
        cluster_counts: dict[str, int] = {}
        held_symbols = [symbol for symbol in eligible_tradable if quantities[symbol] > 1e-12]
        for symbol in sorted(held_symbols, key=lambda item: (rank_by_symbol.get(item, 10**9), item)):
            score = scores.get(symbol, 0.0)
            if (
                score <= 0
                or rank_by_symbol.get(symbol, 10**9) > clean_top_n + clean_rank_buffer
                or not liquidity[symbol]["eligible"]
                or not bool(rows_by_symbol[symbol][index].get("tradable", True))
            ):
                continue
            cluster = cluster_map.get(symbol, symbol)
            if cluster_counts.get(cluster, 0) >= clean_max_per_cluster:
                continue
            selected.append(symbol)
            retained.append(symbol)
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        for symbol, score in ranked:
            if score <= 0 or len(selected) >= clean_top_n:
                continue
            if symbol in selected:
                continue
            if (
                not liquidity[symbol]["eligible"]
                or not bool(rows_by_symbol[symbol][index].get("tradable", True))
            ):
                continue
            cluster = cluster_map.get(symbol, symbol)
            if cluster_counts.get(cluster, 0) >= clean_max_per_cluster:
                continue
            selected.append(symbol)
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        return_series: dict[str, list[float]] = {}
        realized_volatility: dict[str, float] = {}
        for symbol in selected:
            closes = [float(row["close"]) for row in rows_by_symbol[symbol][max(0, index - clean_volatility_window):index + 1]]
            returns = [current / max(previous, 1e-12) - 1.0 for previous, current in zip(closes[:-1], closes[1:])]
            return_series[symbol] = returns
            realized_volatility[symbol] = pstdev(returns) * math.sqrt(252) if len(returns) > 1 else 0.0
        raw_weights = {
            symbol: 1.0 / max(realized_volatility.get(symbol, 0.0), 0.05)
            for symbol in selected
        }
        target_weights = _capped_weights(raw_weights, max_position_weight)
        unallocated_target_weight = max(1.0 - sum(target_weights.values()), 0.0)
        estimated_variance = 0.0
        if selected:
            overlap = min((len(return_series[symbol]) for symbol in selected), default=0)
            if overlap > 1:
                means = {symbol: fmean(return_series[symbol][-overlap:]) for symbol in selected}
                for left in selected:
                    for right in selected:
                        covariance = fmean([
                            (left_value - means[left]) * (right_value - means[right])
                            for left_value, right_value in zip(return_series[left][-overlap:], return_series[right][-overlap:])
                        ])
                        estimated_variance += target_weights[left] * target_weights[right] * covariance * 252
        estimated_portfolio_volatility = math.sqrt(max(estimated_variance, 0.0))
        base_allocation = target_gross * max(0.0, min(regime_multiplier, 1.0)) if selected else 0.0
        volatility_allocation = (
            target_portfolio_volatility / estimated_portfolio_volatility
            if target_portfolio_volatility > 0 and estimated_portfolio_volatility > 1e-12
            else base_allocation
        )
        uncushioned_allocation = min(base_allocation, volatility_allocation)
        allocation = max(uncushioned_allocation - execution_risk_buffer, 0.0) if selected else 0.0
        return {
            "signal_date": dates[index],
            "target_symbols": selected,
            "target_allocation_pct": round(allocation * 100.0, 6),
            "uncushioned_target_allocation_pct": round(uncushioned_allocation * 100.0, 6),
            "execution_risk_buffer_pct": round(execution_risk_buffer * 100.0, 6),
            "scores": {symbol: round(score, 8) for symbol, score in sorted(scores.items())},
            "retained_symbols": retained,
            "target_weights": {symbol: round(weight, 8) for symbol, weight in target_weights.items()},
            "unallocated_target_weight_pct": round(unallocated_target_weight * 100.0, 6),
            "realized_volatility_pct": {
                symbol: round(value * 100.0, 6) for symbol, value in realized_volatility.items()
            },
            "estimated_portfolio_volatility_pct": round(estimated_portfolio_volatility * 100.0, 6),
            "liquidity": liquidity,
            "liquidity_excluded_symbols": sorted(
                symbol for symbol in eligible_tradable if scores.get(symbol, 0.0) > 0 and not liquidity[symbol]["eligible"]
            ),
            "insufficient_causal_history_symbols": sorted(
                symbol
                for symbol in eligible_tradable
                if causal_history.get(symbol, {}).get("status") != "PASS"
            ),
            "causal_history": causal_history,
            "nontradable_excluded_symbols": sorted(
                symbol
                for symbol in eligible_tradable
                if scores.get(symbol, 0.0) > 0 and not bool(rows_by_symbol[symbol][index].get("tradable", True))
            ),
            "universe_membership": membership,
            "universe_ineligible_symbols": list(membership.get("ineligible_symbols") or []),
            "regime": regime,
            "reason": "relative_strength_rebalance",
            "execute": True,
        }

    def is_weekly_rebalance_close(index: int) -> bool:
        if index <= 0:
            return True
        current = date.fromisoformat(str(dates[index])[:10]).isocalendar()[:2]
        previous = date.fromisoformat(str(dates[index - 1])[:10]).isocalendar()[:2]
        return current != previous

    def execute_decision(
        decision: dict[str, Any],
        index: int,
        *,
        quantity_adjustments: dict[str, float] | None = None,
    ) -> None:
        nonlocal cash, total_fees, turnover, liquidity_block_count, gap_block_count
        nonlocal partial_fill_count, tradability_block_count
        if not bool(decision.get("execute", True)):
            return
        target_symbols = list(decision.get("target_symbols") or [])
        allocation = max(0.0, min(float(decision.get("target_allocation_pct") or 0.0) / 100.0, 1.0))
        target_weights = dict(decision.get("target_weights") or {})
        if target_symbols and not target_weights:
            target_weights = {symbol: 1.0 / len(target_symbols) for symbol in target_symbols}
        open_prices = {symbol: float(rows_by_symbol[symbol][index]["open"]) for symbol in tradable}
        equity_open = cash + receivable_balance() + sum(quantities[symbol] * open_prices[symbol] for symbol in tradable)
        minimum_trade_notional = equity_open * minimum_trade_fraction
        decision_liquidity = dict(decision.get("liquidity") or {})

        def execution_terms(symbol: str, side: str, requested_notional: float) -> dict[str, float | bool]:
            evidence = dict(decision_liquidity.get(symbol) or liquidity_at(symbol, max(index - 1, 0)))
            median_dollar_volume = max(float(evidence.get("median_dollar_volume") or 0.0), 0.0)
            maximum_participation = entry_participation if side == "BUY" else exit_participation
            capacity_notional = median_dollar_volume * maximum_participation
            capacity_limited = float(requested_notional) > capacity_notional + 1e-9
            fill_notional = min(max(float(requested_notional), 0.0), max(capacity_notional, 0.0))
            participation = fill_notional / max(median_dollar_volume, 1e-12) if median_dollar_volume > 0 else 0.0
            participation_ratio = participation / max(maximum_participation, 1e-12) if maximum_participation > 0 else 0.0
            impact_bps = impact_at_full_participation * math.sqrt(max(0.0, min(participation_ratio, 1.0)))
            return {
                "median_dollar_volume": median_dollar_volume,
                "capacity_notional": capacity_notional,
                "fill_notional": fill_notional,
                "participation_pct": participation * 100.0,
                "impact_bps": impact_bps,
                "exit_fallback": False,
                "capacity_limited": capacity_limited,
            }

        raw_override = dict(decision.get("target_quantities_override") or {})
        split_adjustments = dict(quantity_adjustments or {})
        override = {
            symbol: float(raw_override.get(symbol, quantities[symbol]))
            * max(float(split_adjustments.get(symbol, 1.0)), 0.0)
            for symbol in tradable
        } if raw_override else {}
        target_quantities = (
            {
                symbol: max(float(override.get(symbol, quantities[symbol])), 0.0)
                for symbol in tradable
            }
            if override
            else {
                symbol: equity_open * allocation * float(target_weights.get(symbol) or 0.0)
                / max(open_prices[symbol] * (1.0 + slippage_rate), 1e-12)
                if symbol in target_symbols else 0.0
                for symbol in tradable
            }
        )
        execution_membership = membership_at(index)
        execution_ineligible = set(execution_membership.get("ineligible_symbols") or [])
        for symbol in sorted(execution_ineligible):
            requested_target = target_quantities.get(symbol, 0.0)
            if requested_target > 1e-12 or quantities[symbol] > 1e-12:
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "SELL" if quantities[symbol] > 1e-12 else "BUY",
                    "status": "FORCED_UNIVERSE_EXIT" if quantities[symbol] > 1e-12 else "SKIPPED_UNIVERSE_INELIGIBLE",
                    "requested_target_quantity": round(requested_target, 10),
                    "current_quantity": round(quantities[symbol], 10),
                    "universe_contract_hash": str(active_universe_contract.get("contract_hash") or ""),
                })
            target_quantities[symbol] = 0.0
        for symbol in tradable:
            sell_quantity = max(quantities[symbol] - target_quantities[symbol], 0.0)
            if sell_quantity <= 1e-12:
                if quantities[symbol] <= target_quantities[symbol] + 1e-12:
                    pending_exit_targets.pop(symbol, None)
                continue
            estimated_notional = sell_quantity * open_prices[symbol]
            full_exit = target_quantities[symbol] <= 1e-12
            if not full_exit and estimated_notional < minimum_trade_notional:
                continue
            row = rows_by_symbol[symbol][index]
            if not bool(row.get("tradable", True)):
                tradability_block_count += 1
                pending_exit_targets[symbol] = target_quantities[symbol]
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "SELL",
                    "status": "BLOCKED_NON_TRADABLE",
                    "trading_status": row.get("trading_status", "UNKNOWN"),
                    "requested_notional": round(estimated_notional, 2),
                })
                continue
            terms = execution_terms(symbol, "SELL", estimated_notional)
            execution_rate = slippage_rate + float(terms["impact_bps"]) / 10_000.0
            execution_price = open_prices[symbol] * (1.0 - execution_rate)
            filled_quantity = min(
                sell_quantity,
                float(terms["fill_notional"]) / max(execution_price, 1e-12),
            )
            if filled_quantity <= 1e-12:
                liquidity_block_count += 1
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "SELL",
                    "status": "BLOCKED_NO_LIQUIDITY",
                    "requested_notional": round(estimated_notional, 2),
                    "median_dollar_volume": round(float(terms["median_dollar_volume"]), 2),
                })
                pending_exit_targets[symbol] = target_quantities[symbol]
                continue
            partial = filled_quantity + 1e-12 < sell_quantity
            partial_fill_count += int(partial)
            notional = filled_quantity * execution_price
            order_fee = notional * fee
            cash += notional - order_fee
            quantities[symbol] -= filled_quantity
            total_fees += order_fee
            turnover += notional
            orders.append({
                "signal_date": decision.get("signal_date", ""),
                "date": dates[index],
                "symbol": symbol,
                "side": "SELL",
                "requested_quantity": round(sell_quantity, 10),
                "quantity": round(filled_quantity, 10),
                "price": round(execution_price, 8),
                "fee": round(order_fee, 6),
                "status": "PARTIAL" if partial else "FILLED",
                "median_dollar_volume": round(float(terms["median_dollar_volume"]), 2),
                "participation_pct": round(float(terms["participation_pct"]), 6),
                "impact_bps": round(float(terms["impact_bps"]), 6),
                "exit_liquidity_fallback": bool(terms["exit_fallback"]),
                "reason": (
                    "universe_membership_exit"
                    if symbol in execution_ineligible else decision.get("reason", "relative_strength_rebalance")
                ),
                "fill_basis": "NEXT_BAR_OPEN",
            })
            if quantities[symbol] <= target_quantities[symbol] + 1e-12:
                pending_exit_targets.pop(symbol, None)
            else:
                pending_exit_targets[symbol] = target_quantities[symbol]
        buy_symbols = [
            symbol for symbol in tradable
            if target_quantities[symbol] > quantities[symbol] + 1e-12
        ]
        for symbol in buy_symbols:
            buy_quantity = max(target_quantities[symbol] - quantities[symbol], 0.0)
            if buy_quantity <= 1e-12:
                continue
            estimated_notional = buy_quantity * open_prices[symbol]
            new_position = quantities[symbol] <= 1e-12
            if not new_position and estimated_notional < minimum_trade_notional:
                continue
            row = rows_by_symbol[symbol][index]
            if not bool(row.get("tradable", True)):
                tradability_block_count += 1
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "BUY",
                    "status": "BLOCKED_NON_TRADABLE",
                    "trading_status": row.get("trading_status", "UNKNOWN"),
                    "requested_notional": round(estimated_notional, 2),
                })
                continue
            previous_close = float(rows_by_symbol[symbol][max(index - 1, 0)]["close"])
            open_gap = abs(open_prices[symbol] / max(previous_close, 1e-12) - 1.0)
            if open_gap > maximum_entry_gap:
                gap_block_count += 1
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "BUY",
                    "status": "BLOCKED_ENTRY_GAP",
                    "open_gap_pct": round(open_gap * 100.0, 6),
                    "maximum_open_gap_pct": round(maximum_entry_gap * 100.0, 6),
                    "requested_notional": round(estimated_notional, 2),
                })
                continue
            terms = execution_terms(symbol, "BUY", estimated_notional)
            if float(terms["fill_notional"]) <= 0:
                liquidity_block_count += 1
                execution_events.append({
                    "signal_date": decision.get("signal_date", ""),
                    "date": dates[index],
                    "symbol": symbol,
                    "side": "BUY",
                    "status": "BLOCKED_NO_LIQUIDITY",
                    "requested_notional": round(estimated_notional, 2),
                    "median_dollar_volume": round(float(terms["median_dollar_volume"]), 2),
                })
                continue
            execution_rate = slippage_rate + float(terms["impact_bps"]) / 10_000.0
            execution_price = open_prices[symbol] * (1.0 + execution_rate)
            affordable = cash / max(execution_price * (1.0 + fee), 1e-12)
            capacity_quantity = (
                float(terms["fill_notional"]) / max(execution_price, 1e-12)
                if bool(terms["capacity_limited"])
                else buy_quantity
            )
            filled_quantity = min(buy_quantity, capacity_quantity, max(affordable, 0.0))
            if filled_quantity <= 1e-12:
                continue
            partial = filled_quantity + 1e-12 < buy_quantity
            partial_fill_count += int(partial)
            notional = filled_quantity * execution_price
            order_fee = notional * fee
            cash -= notional + order_fee
            quantities[symbol] += filled_quantity
            total_fees += order_fee
            turnover += notional
            orders.append({
                "signal_date": decision.get("signal_date", ""),
                "date": dates[index],
                "symbol": symbol,
                "side": "BUY",
                "requested_quantity": round(buy_quantity, 10),
                "quantity": round(filled_quantity, 10),
                "price": round(execution_price, 8),
                "fee": round(order_fee, 6),
                "status": "PARTIAL" if partial else "FILLED",
                "open_gap_pct": round(open_gap * 100.0, 6),
                "median_dollar_volume": round(float(terms["median_dollar_volume"]), 2),
                "participation_pct": round(float(terms["participation_pct"]), 6),
                "impact_bps": round(float(terms["impact_bps"]), 6),
                "reason": decision.get("reason", "relative_strength_rebalance"),
                "fill_basis": "NEXT_BAR_OPEN",
            })

    def retry_pending_exits(
        index: int,
        *,
        reason: str = "retry_blocked_exit",
        membership_exit_symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        override = {
            symbol: max(pending_exit_targets.get(symbol, quantities[symbol]), 0.0)
            for symbol in tradable
        }
        return {
            "signal_date": dates[index],
            "target_symbols": [symbol for symbol in tradable if override[symbol] > 1e-12],
            "target_quantities_override": override,
            "target_allocation_pct": 0.0,
            "scores": {},
            "reason": reason,
            "pending_exit_symbols": sorted(pending_exit_targets),
            "membership_exit_symbols": sorted(membership_exit_symbols or []),
            "liquidity": {symbol: liquidity_at(symbol, index) for symbol in pending_exit_targets},
            "execute": True,
        }

    pending = {
        "signal_date": dates[evaluation_start - 1],
        "target_symbols": [],
        "target_allocation_pct": 0.0,
        "scores": {},
        "reason": "awaiting_scheduled_rebalance",
        "execute": False,
    }
    for index in range(evaluation_start, len(dates)):
        quantity_adjustments = apply_pre_open_events(index)
        execute_decision(pending, index, quantity_adjustments=quantity_adjustments)
        if bool(pending.get("execute", True)) and pending.get("reason") == "relative_strength_rebalance":
            for symbol in pending.get("target_symbols") or []:
                selection_counts[symbol] += 1
        closes = {symbol: float(rows_by_symbol[symbol][index]["close"]) for symbol in tradable}
        position_value = sum(quantities[symbol] * closes[symbol] for symbol in tradable)
        equity = cash + receivable_balance() + position_value
        peak_equity = max(peak_equity, equity)
        current_drawdown = 1.0 - equity / max(peak_equity, 1e-12)
        equity_curve.append({
            "date": dates[index],
            "equity": round(equity, 2),
            "gross_exposure_pct": round(position_value / max(equity, 1e-12) * 100.0, 4),
            "drawdown_pct": round(current_drawdown * 100.0, 4),
        })
        membership = membership_at(index)
        eligible_now = set(membership.get("eligible_symbols") or [])
        membership_exit_symbols = sorted(
            symbol for symbol in tradable
            if quantities[symbol] > 1e-12 and symbol not in eligible_now
        )
        for symbol in membership_exit_symbols:
            pending_exit_targets[symbol] = 0.0
        if not drawdown_guard_active and drawdown_guard > 0 and current_drawdown >= drawdown_guard:
            drawdown_guard_active = True
            risk_off_until_index = index + cooldown_bars
            risk_off_event_count += 1
            pending = {
                "signal_date": dates[index],
                "target_symbols": [],
                "target_allocation_pct": 0.0,
                "scores": {},
                "reason": "portfolio_drawdown_guard",
                "drawdown_pct": round(current_drawdown * 100.0, 6),
                "risk_off_until_index": risk_off_until_index,
                "execute": True,
            }
            decisions.append(pending)
        elif drawdown_guard_active and index >= risk_off_until_index:
            drawdown_guard_active = False
            peak_equity = equity
            pending = retry_pending_exits(index) if pending_exit_targets else decision_at(index)
            decisions.append(pending)
        elif drawdown_guard_active:
            remaining_positions = [symbol for symbol in tradable if quantities[symbol] > 1e-12]
            pending = {
                "signal_date": dates[index],
                "target_symbols": [],
                "target_allocation_pct": 0.0,
                "scores": {},
                "reason": "drawdown_cooldown_liquidation" if remaining_positions else "drawdown_cooldown",
                "risk_off_until_index": risk_off_until_index,
                "remaining_positions": remaining_positions,
                "liquidity": {symbol: liquidity_at(symbol, index) for symbol in remaining_positions},
                "execute": bool(remaining_positions),
            }
        elif pending_exit_targets:
            pending = retry_pending_exits(
                index,
                reason="universe_membership_exit" if membership_exit_symbols else "retry_blocked_exit",
                membership_exit_symbols=membership_exit_symbols,
            )
            decisions.append(pending)
        elif is_weekly_rebalance_close(index):
            pending = decision_at(index)
            decisions.append(pending)
        else:
            pending = {
                "signal_date": dates[index],
                "target_symbols": [symbol for symbol in tradable if quantities[symbol] > 1e-12],
                "target_allocation_pct": round(position_value / max(equity, 1e-12) * 100.0, 6),
                "scores": {},
                "reason": "hold_between_rebalances",
                "execute": False,
            }

    equity_values = [float(initial_cash), *[float(item["equity"]) for item in equity_curve]]
    final_equity = equity_values[-1]
    total_return = final_equity / max(float(initial_cash), 1e-12) - 1.0
    average_exposure = fmean([float(item["gross_exposure_pct"]) for item in equity_curve]) if equity_curve else 0.0
    elapsed_ms = max(
        int(rows_by_symbol[clean_benchmark][-1]["ts_ms"]) - int(rows_by_symbol[clean_benchmark][evaluation_start]["ts_ms"]),
        86_400_000,
    )
    elapsed_years = elapsed_ms / (365.2425 * 86_400_000)
    annualized_turnover_multiple = turnover / max(float(initial_cash), 1e-12) / max(elapsed_years, 1e-12)
    final_positions = {
        symbol: {
            "quantity": round(quantity, 10),
            "market_value": round(quantity * float(rows_by_symbol[symbol][-1]["close"]), 2),
        }
        for symbol, quantity in quantities.items()
        if quantity > 1e-12
    }
    liquidity_exclusion_count = sum(len(item.get("liquidity_excluded_symbols") or []) for item in decisions)
    capacity_estimates: list[float] = []
    for decision in decisions:
        allocation_fraction = max(float(decision.get("target_allocation_pct") or 0.0) / 100.0, 0.0)
        weights = dict(decision.get("target_weights") or {})
        liquidity = dict(decision.get("liquidity") or {})
        if allocation_fraction <= 0:
            continue
        for symbol in decision.get("target_symbols") or []:
            weight = max(float(weights.get(symbol) or 0.0), 0.0)
            median_dollar_volume = max(float((liquidity.get(symbol) or {}).get("median_dollar_volume") or 0.0), 0.0)
            if weight > 0 and median_dollar_volume > 0 and entry_participation > 0:
                capacity_estimates.append(median_dollar_volume * entry_participation / (allocation_fraction * weight))
    estimated_capacity = min(capacity_estimates) if capacity_estimates else 0.0
    run_spec = {
        "dataset_hash": manifest["data_hash"],
        "benchmark_symbol": clean_benchmark,
        "tradable_symbols": tradable,
        "clusters": cluster_map,
        "lookback": clean_lookback,
        "skip_recent": clean_skip,
        "rebalance_interval": clean_rebalance,
        "rebalance_schedule": "FIRST_COMPLETED_TRADING_DAY_OF_ISO_WEEK",
        "top_n": clean_top_n,
        "rank_buffer": clean_rank_buffer,
        "gross_target_pct": target_gross * 100.0,
        "execution_risk_buffer_pct": execution_risk_buffer * 100.0,
        "max_per_cluster": clean_max_per_cluster,
        "minimum_trade_pct": minimum_trade_fraction * 100.0,
        "drawdown_guard_pct": drawdown_guard * 100.0,
        "drawdown_cooldown_bars": cooldown_bars,
        "volatility_window": clean_volatility_window,
        "target_portfolio_volatility_pct": target_portfolio_volatility * 100.0,
        "max_position_weight_pct": max_position_weight * 100.0,
        "liquidity_window": clean_liquidity_window,
        "minimum_median_dollar_volume": minimum_dollar_volume,
        "max_entry_participation_pct": entry_participation * 100.0,
        "max_exit_participation_pct": exit_participation * 100.0,
        "max_entry_open_gap_pct": maximum_entry_gap * 100.0,
        "impact_bps_at_full_participation": impact_at_full_participation,
        "fee_rate": fee,
        "slippage_bps": slippage_rate * 10_000.0,
        "initial_cash": float(initial_cash),
        "evaluation_start_index": evaluation_start,
        "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
        "market_regime_schema_version": MARKET_REGIME_SCHEMA_VERSION,
        "market_calendar_schema_version": MARKET_CALENDAR_SCHEMA_VERSION,
        "market_calendar_contract_hash": str((manifest.get("market_calendar") or {}).get("contract_hash") or ""),
        "security_lifecycle_schema_version": SECURITY_LIFECYCLE_SCHEMA_VERSION,
        "security_lifecycle_contract_hashes": {
            symbol: str(item.get("contract_hash") or "")
            for symbol, item in sorted(dict(manifest.get("security_lifecycle") or {}).items())
        },
        "corporate_action_schema_version": CORPORATE_ACTION_SCHEMA_VERSION,
        "universe_contract_hash": str(active_universe_contract.get("contract_hash") or ""),
        "universe_membership_policy": str(active_universe_contract.get("membership_policy") or ""),
        "point_in_time_universe_verified": active_universe_contract.get("historical_membership_verified") is True,
        "return_accounting_hashes": {
            symbol: str(item.get("return_accounting_hash") or "")
            for symbol, item in sorted(dict(manifest.get("adjustment_evidence") or {}).items())
        },
    }
    planned_rebalance_dates = [
        str(item.get("signal_date") or "")
        for item in decisions
        if item.get("reason") == "relative_strength_rebalance"
    ]
    date_indexes = {session_date: index for index, session_date in enumerate(dates)}
    schedule_violation_dates = [
        session_date
        for session_date in planned_rebalance_dates
        if session_date not in date_indexes or not is_weekly_rebalance_close(date_indexes[session_date])
    ]
    return {
        "ok": True,
        "schema_version": PORTFOLIO_BACKTEST_SCHEMA_VERSION,
        "execution_model": PORTFOLIO_EXECUTION_MODEL_VERSION,
        "dataset_manifest": manifest,
        "universe_contract": active_universe_contract,
        "universe_verification": universe_verification,
        "run_spec": run_spec,
        "run_hash": _canonical_hash(run_spec),
        "evaluation_window": {
            "start_index": evaluation_start,
            "start": dates[evaluation_start],
            "end": dates[-1],
            "evaluated_rows": len(dates) - evaluation_start,
        },
        "initial_cash": round(float(initial_cash), 2),
        "final_equity": round(final_equity, 2),
        "total_return_pct": round(total_return * 100.0, 4),
        "max_drawdown_pct": round(_max_drawdown(equity_values) * 100.0, 4),
        "sharpe": round(_sharpe(equity_values), 4),
        "average_gross_exposure_pct": round(average_exposure, 4),
        "order_event_count": len(orders),
        "decision_event_count": len(decisions),
        "rebalance_decision_count": len(planned_rebalance_dates),
        "planned_rebalance_dates": planned_rebalance_dates,
        "schedule_contract": {
            "name": "FIRST_COMPLETED_TRADING_DAY_OF_ISO_WEEK",
            "status": "PASS" if not schedule_violation_dates else "BLOCK",
            "violation_dates": schedule_violation_dates,
            "initial_state": "CASH_UNTIL_FIRST_SCHEDULED_REBALANCE",
        },
        "risk_off_event_count": risk_off_event_count,
        "liquidity_exclusion_count": liquidity_exclusion_count,
        "liquidity_block_count": liquidity_block_count,
        "gap_block_count": gap_block_count,
        "partial_fill_count": partial_fill_count,
        "tradability_block_count": tradability_block_count,
        "forced_universe_exit_count": sum(
            1 for item in execution_events if item.get("status") == "FORCED_UNIVERSE_EXIT"
        ),
        "universe_ineligible_skip_count": sum(
            1 for item in execution_events if item.get("status") == "SKIPPED_UNIVERSE_INELIGIBLE"
        ),
        "estimated_strategy_capacity": round(estimated_capacity, 2),
        "turnover": round(turnover, 2),
        "annualized_turnover_multiple": round(annualized_turnover_multiple, 4),
        "total_fees": round(total_fees, 4),
        "total_dividends": round(total_dividends, 6),
        "dividend_cash_paid": round(dividend_cash_paid, 6),
        "dividend_receivable": round(receivable_balance(), 6),
        "corporate_action_event_count": len(corporate_action_events),
        "corporate_action_events": corporate_action_events,
        "pending_forced_exit_symbols": sorted(pending_exit_targets),
        "selection_counts": selection_counts,
        "final_positions": final_positions,
        "pending_decision_at_end": pending,
        "orders": orders,
        "execution_events": execution_events,
        "decisions": decisions,
        "equity_curve": equity_curve,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def audit_relative_strength_causality(
    *,
    payloads: dict[str, dict[str, Any]],
    checkpoint_ratios: tuple[float, ...] = (0.60, 0.80),
    **settings: Any,
) -> dict[str, Any]:
    frozen_input = json.loads(json.dumps(payloads, ensure_ascii=True, default=str))
    input_hash = _canonical_hash(frozen_input)
    full = run_causal_relative_strength_backtest(payloads=frozen_input, **settings)
    if not full.get("ok"):
        return {
            "status": "BLOCK",
            "blockers": [str(full.get("error") or "full_backtest_failed")],
            "checkpoints": [],
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    full_curve = list(full.get("equity_curve") or [])
    full_orders = list(full.get("orders") or [])
    row_count = int((full.get("dataset_manifest") or {}).get("row_count") or 0)
    calendar_dates = list(
        ((full.get("dataset_manifest") or {}).get("market_calendar") or {}).get("expected_dates") or []
    )
    checkpoints: list[dict[str, Any]] = []
    for ratio in checkpoint_ratios:
        row_limit = max(130, min(row_count, math.ceil(row_count * float(ratio))))
        cutoff = str(calendar_dates[row_limit - 1]) if len(calendar_dates) >= row_limit else ""
        prefix_payloads = {
            symbol: slice_portfolio_payload_through_date(dict(payload), cutoff)
            for symbol, payload in frozen_input.items()
        }
        prefix = run_causal_relative_strength_backtest(payloads=prefix_payloads, **settings)
        prefix_curve = list(prefix.get("equity_curve") or []) if prefix.get("ok") else []
        prefix_orders = list(prefix.get("orders") or []) if prefix.get("ok") else []
        curve_match = bool(prefix.get("ok")) and full_curve[:len(prefix_curve)] == prefix_curve
        order_match = bool(prefix.get("ok")) and full_orders[:len(prefix_orders)] == prefix_orders
        checkpoints.append({
            "ratio": float(ratio),
            "row_limit": row_limit,
            "cutoff": cutoff,
            "prefix_ok": bool(prefix.get("ok")),
            "equity_prefix_match": curve_match,
            "order_prefix_match": order_match,
            "passed": curve_match and order_match,
        })
    input_unchanged = _canonical_hash(frozen_input) == input_hash
    passed = input_unchanged and all(item["passed"] for item in checkpoints)
    return {
        "status": "PASS" if passed else "BLOCK",
        "blockers": [] if passed else ["relative_strength_prefix_invariance_failed"],
        "input_unchanged": input_unchanged,
        "checkpoints": checkpoints,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
