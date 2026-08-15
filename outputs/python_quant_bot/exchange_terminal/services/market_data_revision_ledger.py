from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import closing
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any, Callable

from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable

try:
    from market_data.candle_contract import candle_is_complete
except ModuleNotFoundError:
    from exchange_terminal.market_data.candle_contract import candle_is_complete


MARKET_DATA_REVISION_SCHEMA_VERSION = "market-data-revision-ledger-v9"
MARKET_DATA_REVISION_COMPATIBLE_EVIDENCE_SCHEMAS = {
    "market-data-revision-ledger-v5",
    "market-data-revision-ledger-v6",
    "market-data-revision-ledger-v7",
    "market-data-revision-ledger-v8",
    MARKET_DATA_REVISION_SCHEMA_VERSION,
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _finite(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return parsed if math.isfinite(parsed) else 0.0


def _provider_family(provider: str) -> str:
    text = str(provider or "unknown").strip().lower()
    if "futu" in text:
        return "futu"
    if "yahoo" in text:
        return "yahoo"
    if "stooq" in text:
        return "stooq"
    if "accepted" in text or "sqlite" in text or "cache" in text:
        return "accepted_cache"
    return text or "unknown"


def _authority_tier(provider: str) -> str:
    family = _provider_family(provider)
    return {
        "futu": "PRIMARY_MARKET_PROVIDER",
        "yahoo": "INDEPENDENT_PUBLIC_REFERENCE",
        "stooq": "SECONDARY_UNVERIFIED_REFERENCE",
        "accepted_cache": "LOCAL_ACCEPTED_DATASET",
    }.get(family, "UNKNOWN")


def _row_date(row: dict[str, Any]) -> str:
    text = str(row.get("date") or row.get("trading_date") or "").strip()[:10]
    if len(text) == 10 and text[4:5] == "-" and text[7:8] == "-":
        return text
    return ""


def _normalized_rows(
    rows: list[dict[str, Any]] | None,
    *,
    completed_only: bool,
    through_date: str,
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        trading_date = _row_date(raw)
        if not trading_date or (through_date and trading_date > through_date):
            continue
        complete = candle_is_complete(raw, default_if_missing=False)
        if completed_only and not complete:
            continue
        close = _finite(raw.get("close"))
        if close <= 0:
            continue
        item = {
            "date": trading_date,
            "open": round(_finite(raw.get("open")) or close, 8),
            "high": round(_finite(raw.get("high")) or close, 8),
            "low": round(_finite(raw.get("low")) or close, 8),
            "close": round(close, 8),
            "volume": round(max(_finite(raw.get("volume") or raw.get("vol")), 0.0), 4),
            "complete": complete,
        }
        item["row_hash"] = _canonical_hash(item)
        by_date[trading_date] = item
    return [by_date[key] for key in sorted(by_date)]


def build_market_data_snapshot(
    *,
    symbol: str,
    provider: str,
    rows: list[dict[str, Any]] | None,
    interval: str = "1d",
    session: str = "regular",
    role: str = "PROVIDER_OBSERVATION",
    adjustment_basis: str = "",
    corporate_actions_hash: str = "",
    completed_only: bool = True,
    through_date: str = "",
    lineage_id: str = "",
) -> dict[str, Any]:
    normalized = _normalized_rows(
        rows,
        completed_only=completed_only,
        through_date=str(through_date or "")[:10],
    )
    clean_role = str(role or "PROVIDER_OBSERVATION").strip().upper()
    clean_lineage_id = str(lineage_id or "").strip()
    if len(clean_lineage_id) > 160:
        raise ValueError("market_data_lineage_id_too_long")
    if clean_role != "BACKTEST_DATASET":
        clean_lineage_id = ""
    family = _provider_family(provider)
    payload = {
        "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "symbol": str(symbol or "").strip().upper(),
        "provider": str(provider or "unknown").strip().lower(),
        "provider_family": family,
        "authority_tier": _authority_tier(provider),
        "role": clean_role,
        "interval": str(interval or "1d").strip().lower(),
        "session": str(session or "regular").strip().lower(),
        "adjustment_basis": str(adjustment_basis or "").strip().upper(),
        "corporate_actions_hash": str(corporate_actions_hash or ""),
        "completed_only": bool(completed_only),
        "through_date": str(through_date or "")[:10],
        "lineage_id": clean_lineage_id,
        "row_count": len(normalized),
        "first_date": normalized[0]["date"] if normalized else "",
        "last_date": normalized[-1]["date"] if normalized else "",
        "rows": normalized,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["rows_hash"] = _canonical_hash(normalized)
    payload["snapshot_hash"] = _canonical_hash({key: value for key, value in payload.items() if key != "rows"})
    return payload


def _rebuild_market_data_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = snapshot.get("rows")
    return build_market_data_snapshot(
        symbol=str(snapshot.get("symbol") or ""),
        provider=str(snapshot.get("provider") or ""),
        rows=[dict(item) for item in rows if isinstance(item, dict)] if isinstance(rows, list) else [],
        interval=str(snapshot.get("interval") or ""),
        session=str(snapshot.get("session") or ""),
        role=str(snapshot.get("role") or ""),
        adjustment_basis=str(snapshot.get("adjustment_basis") or ""),
        corporate_actions_hash=str(snapshot.get("corporate_actions_hash") or ""),
        completed_only=snapshot.get("completed_only") is True,
        through_date=str(snapshot.get("through_date") or ""),
        lineage_id=str(snapshot.get("lineage_id") or ""),
    )


def verify_market_data_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(snapshot) if isinstance(snapshot, dict) else {}
    blockers: list[str] = []
    if str(snapshot.get("schema_version") or "") != MARKET_DATA_REVISION_SCHEMA_VERSION:
        blockers.append("market_data_snapshot_schema_invalid")
    rows = snapshot.get("rows")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        blockers.append("market_data_snapshot_rows_invalid")
    rebuilt = _rebuild_market_data_snapshot(snapshot)
    if set(snapshot) != set(rebuilt):
        blockers.append("market_data_snapshot_fields_invalid")
    for field, expected in rebuilt.items():
        if snapshot.get(field) != expected:
            blockers.append(f"market_data_snapshot_semantic_mismatch:{field}")
    if (
        snapshot.get("research_only") is not True
        or snapshot.get("paper_authorized") is not False
        or snapshot.get("live_order_allowed") is not False
    ):
        blockers.append("market_data_snapshot_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "snapshot_hash": str(rebuilt.get("snapshot_hash") or ""),
        "rows_hash": str(rebuilt.get("rows_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _public_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if not snapshot:
        return {}
    return {key: value for key, value in snapshot.items() if key != "rows"}


def _uniform_price_rebase(
    previous_rows: dict[str, dict[str, Any]],
    current_rows: dict[str, dict[str, Any]],
    changed_dates: list[str],
) -> tuple[bool, float, float]:
    ratios: list[float] = []
    for trading_date in changed_dates:
        previous = previous_rows[trading_date]
        current = current_rows[trading_date]
        for field in ("open", "high", "low", "close"):
            old = _finite(previous.get(field))
            new = _finite(current.get(field))
            if old <= 0 or new <= 0:
                return False, 1.0, 1.0
            ratios.append(new / old)
    if len(ratios) < 8:
        return False, 1.0, 1.0
    scale = median(ratios)
    dispersion = max(abs(value / max(scale, 1e-12) - 1.0) for value in ratios)
    return bool(abs(scale - 1.0) > 1e-8 and dispersion <= 0.0025), scale, dispersion


def _price_change_is_material(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    for field in ("open", "high", "low", "close"):
        old = _finite(previous.get(field))
        new = _finite(current.get(field))
        tolerance = max(0.00011, abs(old) * 0.000002)
        if abs(new - old) > tolerance:
            return True
    return False


def _volume_change_is_material(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    old = _finite(previous.get("volume"))
    new = _finite(current.get("volume"))
    tolerance = max(1.0, max(abs(old), abs(new)) * 0.00001)
    return abs(new - old) > tolerance


def compare_market_data_snapshots(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    previous = dict(previous or {})
    current = dict(current or {})
    role = str(current.get("role") or "PROVIDER_OBSERVATION").upper()
    previous_rows = {str(row.get("date") or ""): row for row in previous.get("rows") or []}
    current_rows = {str(row.get("date") or ""): row for row in current.get("rows") or []}
    added_dates = sorted(set(current_rows) - set(previous_rows))
    removed_dates = sorted(set(previous_rows) - set(current_rows))
    changed_dates = sorted(
        trading_date
        for trading_date in set(previous_rows) & set(current_rows)
        if str(previous_rows[trading_date].get("row_hash") or "")
        != str(current_rows[trading_date].get("row_hash") or "")
    )
    price_changed_dates = [
        trading_date
        for trading_date in changed_dates
        if any(
            _finite(previous_rows[trading_date].get(field))
            != _finite(current_rows[trading_date].get(field))
            for field in ("open", "high", "low", "close")
        )
    ]
    material_price_changed_dates = [
        trading_date
        for trading_date in price_changed_dates
        if _price_change_is_material(previous_rows[trading_date], current_rows[trading_date])
    ]
    raw_volume_changed_dates = [
        trading_date
        for trading_date in changed_dates
        if _finite(previous_rows[trading_date].get("volume"))
        != _finite(current_rows[trading_date].get("volume"))
    ]
    volume_changed_dates = [
        trading_date
        for trading_date in raw_volume_changed_dates
        if _volume_change_is_material(previous_rows[trading_date], current_rows[trading_date])
    ]
    immaterial_volume_changed_dates = sorted(set(raw_volume_changed_dates) - set(volume_changed_dates))
    uniform_rebase, scale, scale_dispersion = _uniform_price_rebase(
        previous_rows,
        current_rows,
        material_price_changed_dates,
    ) if material_price_changed_dates else (False, 1.0, 0.0)

    blockers: list[str] = []
    warnings: list[str] = []
    if not previous:
        classification = "INITIAL_BASELINE"
        status = "PASS"
    elif str(previous.get("snapshot_hash") or "") == str(current.get("snapshot_hash") or ""):
        classification = "UNCHANGED"
        status = "PASS"
    elif removed_dates:
        classification = "HISTORICAL_ROWS_REMOVED"
        blockers.append(f"completed_rows_removed:{len(removed_dates)}")
        status = "BLOCK"
    elif changed_dates and not material_price_changed_dates and not volume_changed_dates:
        classification = "IMMATERIAL_NUMERIC_DRIFT"
        if price_changed_dates:
            warnings.append(f"sub_tolerance_price_quantization_drift:{len(price_changed_dates)}")
        if immaterial_volume_changed_dates:
            warnings.append(f"sub_tolerance_volume_quantization_drift:{len(immaterial_volume_changed_dates)}")
        status = "PASS"
    elif material_price_changed_dates and uniform_rebase:
        classification = "UNIFORM_PRICE_REBASE"
        if role in {"ACCEPTED_CACHE", "BACKTEST_DATASET"}:
            blockers.append(f"frozen_price_vintage_rebased:{len(material_price_changed_dates)}")
            status = "BLOCK"
        else:
            warnings.append(f"provider_adjusted_vintage_rebased:{len(material_price_changed_dates)}")
            status = "REVIEW"
    elif material_price_changed_dates:
        classification = "HISTORICAL_PRICE_REVISION"
        blockers.append(f"completed_prices_revised:{len(material_price_changed_dates)}")
        status = "BLOCK"
    elif volume_changed_dates:
        classification = "HISTORICAL_VOLUME_REVISION"
        if role in {"ACCEPTED_CACHE", "BACKTEST_DATASET"}:
            blockers.append(f"completed_volumes_revised:{len(volume_changed_dates)}")
            status = "BLOCK"
        else:
            warnings.append(f"provider_volumes_revised:{len(volume_changed_dates)}")
            status = "REVIEW"
    elif added_dates:
        classification = "APPEND_ONLY"
        status = "PASS"
    elif (
        str(previous.get("rows_hash") or "") == str(current.get("rows_hash") or "")
        and not str(previous.get("corporate_actions_hash") or "")
        and bool(str(current.get("corporate_actions_hash") or ""))
        and "ADJUSTED" in str(current.get("adjustment_basis") or "").upper()
        and all(
            previous.get(key) == current.get(key)
            for key in (
                "symbol", "provider", "provider_family", "role", "interval", "session",
                "adjustment_basis", "completed_only", "through_date",
            )
        )
    ):
        classification = "CONTRACT_METADATA_ENRICHMENT"
        warnings.append("corporate_actions_hash_backfilled_without_row_change")
        status = "PASS"
    elif (
        str(previous.get("rows_hash") or "") == str(current.get("rows_hash") or "")
        and str(previous.get("corporate_actions_hash") or "")
        != str(current.get("corporate_actions_hash") or "")
        and "ADJUSTED" in str(current.get("adjustment_basis") or "").upper()
        and all(
            previous.get(key) == current.get(key)
            for key in (
                "symbol", "provider", "provider_family", "role", "interval", "session",
                "adjustment_basis", "completed_only", "through_date",
            )
        )
    ):
        classification = "ADJUSTED_METADATA_REVISION"
        warnings.append("adjusted_rows_unchanged_but_corporate_actions_evidence_revised")
        status = "REVIEW"
    elif (
        str(previous.get("rows_hash") or "") == str(current.get("rows_hash") or "")
        and all(
            previous.get(key) == current.get(key)
            for key in (
                "symbol", "provider", "provider_family", "role", "interval", "session",
                "adjustment_basis", "corporate_actions_hash", "completed_only", "through_date",
            )
        )
        and str(previous.get("schema_version") or "") != str(current.get("schema_version") or "")
    ):
        classification = "SCHEMA_MIGRATION"
        warnings.append(
            f"snapshot_schema_migrated:{previous.get('schema_version') or 'unknown'}->{current.get('schema_version') or 'unknown'}"
        )
        status = "PASS"
    else:
        classification = "CONTRACT_REVISION"
        blockers.append("snapshot_contract_changed_without_row_change")
        status = "BLOCK" if role in {"ACCEPTED_CACHE", "BACKTEST_DATASET"} else "REVIEW"

    evidence = {
        "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "symbol": str(current.get("symbol") or "").upper(),
        "provider_family": str(current.get("provider_family") or ""),
        "role": role,
        "classification": classification,
        "status": status,
        "previous_snapshot_hash": str(previous.get("snapshot_hash") or ""),
        "current_snapshot_hash": str(current.get("snapshot_hash") or ""),
        "added_date_count": len(added_dates),
        "removed_date_count": len(removed_dates),
        "changed_date_count": len(changed_dates),
        "price_changed_date_count": len(price_changed_dates),
        "material_price_changed_date_count": len(material_price_changed_dates),
        "volume_changed_date_count": len(volume_changed_dates),
        "raw_volume_changed_date_count": len(raw_volume_changed_dates),
        "immaterial_volume_changed_date_count": len(immaterial_volume_changed_dates),
        "added_dates": added_dates[:50],
        "removed_dates": removed_dates[:50],
        "changed_dates": changed_dates[:50],
        "uniform_price_scale": round(scale, 10),
        "uniform_price_scale_dispersion": round(scale_dispersion, 10),
        "blockers": blockers,
        "warnings": warnings,
        "previous": _public_snapshot(previous),
        "current": _public_snapshot(current),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    evidence["event_hash"] = _canonical_hash(evidence)
    return evidence


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def _date_gap_days(left: str, right: str) -> int:
    try:
        return abs((date.fromisoformat(left) - date.fromisoformat(right)).days)
    except (TypeError, ValueError):
        return 999999


def build_cross_source_evidence(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    required_overlap: int = 120,
) -> dict[str, Any]:
    primary_snapshot = _rebuild_market_data_snapshot(dict(primary or {}))
    secondary_snapshot = _rebuild_market_data_snapshot(dict(secondary or {}))
    primary_rows = {str(row.get("date") or ""): row for row in primary_snapshot.get("rows") or []}
    secondary_rows = {str(row.get("date") or ""): row for row in secondary_snapshot.get("rows") or []}
    overlap_dates = sorted(set(primary_rows) & set(secondary_rows))
    return_differences: list[float] = []
    direction_matches: list[bool] = []
    price_ratios: list[float] = []
    for previous_date, current_date in zip(overlap_dates, overlap_dates[1:]):
        primary_previous = _finite(primary_rows[previous_date].get("close"))
        primary_current = _finite(primary_rows[current_date].get("close"))
        secondary_previous = _finite(secondary_rows[previous_date].get("close"))
        secondary_current = _finite(secondary_rows[current_date].get("close"))
        if min(primary_previous, primary_current, secondary_previous, secondary_current) <= 0:
            continue
        primary_return = primary_current / primary_previous - 1.0
        secondary_return = secondary_current / secondary_previous - 1.0
        return_differences.append(abs(primary_return - secondary_return))
        direction_matches.append(
            abs(primary_return) < 1e-12
            or abs(secondary_return) < 1e-12
            or (primary_return > 0) == (secondary_return > 0)
        )
        price_ratios.append(primary_current / secondary_current)

    median_difference = median(return_differences) if return_differences else 0.0
    p95_difference = _quantile(return_differences, 0.95)
    p99_difference = _quantile(return_differences, 0.99)
    direction_agreement = (
        sum(1 for item in direction_matches if item) / len(direction_matches)
        if direction_matches else 0.0
    )
    median_ratio = median(price_ratios) if price_ratios else 1.0
    ratio_dispersion = (
        max(abs(value / max(median_ratio, 1e-12) - 1.0) for value in price_ratios)
        if price_ratios else 0.0
    )
    primary_family = str(primary_snapshot.get("provider_family") or "")
    secondary_family = str(secondary_snapshot.get("provider_family") or "")
    latest_overlap = overlap_dates[-1] if overlap_dates else ""
    latest_reference = max(
        str(primary_snapshot.get("last_date") or ""),
        str(secondary_snapshot.get("last_date") or ""),
    )
    latest_gap_days = _date_gap_days(latest_overlap, latest_reference) if latest_overlap else 999999
    minimum_overlap = max(int(required_overlap), 2)
    blockers: list[str] = []
    warnings: list[str] = []
    if not primary_rows or not secondary_rows:
        blockers.append("cross_source_rows_missing")
    if primary_family == secondary_family:
        blockers.append(f"cross_source_not_independent:{primary_family or 'unknown'}")
    if len(overlap_dates) < 30:
        blockers.append(f"cross_source_overlap_too_small:{len(overlap_dates)}<30")
    elif len(overlap_dates) < minimum_overlap:
        warnings.append(f"cross_source_overlap_below_target:{len(overlap_dates)}<{minimum_overlap}")
    if return_differences:
        if median_difference > 0.002:
            blockers.append(f"cross_source_median_return_divergence:{median_difference:.8f}")
        if p95_difference > 0.01:
            blockers.append(f"cross_source_p95_return_divergence:{p95_difference:.8f}")
        if direction_agreement < 0.95:
            blockers.append(f"cross_source_direction_agreement_low:{direction_agreement:.6f}")
        if ratio_dispersion > 0.15:
            blockers.append(f"cross_source_price_ratio_unstable:{ratio_dispersion:.8f}")
    if latest_gap_days > 10:
        warnings.append(f"cross_source_recent_overlap_stale:{latest_gap_days}d")
    status = "BLOCK" if blockers else "PASS" if len(overlap_dates) >= minimum_overlap and latest_gap_days <= 10 else "REVIEW"
    evidence = {
        "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
        "symbol": str(primary_snapshot.get("symbol") or secondary_snapshot.get("symbol") or "").upper(),
        "status": status,
        "primary_provider": primary_family,
        "secondary_provider": secondary_family,
        "primary_snapshot_hash": str(primary_snapshot.get("snapshot_hash") or ""),
        "secondary_snapshot_hash": str(secondary_snapshot.get("snapshot_hash") or ""),
        "primary_snapshot": primary_snapshot,
        "secondary_snapshot": secondary_snapshot,
        "independent_provider_families": bool(primary_family and secondary_family and primary_family != secondary_family),
        "required_overlap": minimum_overlap,
        "overlap_count": len(overlap_dates),
        "overlap_first": overlap_dates[0] if overlap_dates else "",
        "overlap_last": latest_overlap,
        "latest_overlap_gap_days": latest_gap_days,
        "median_abs_return_difference": round(median_difference, 10),
        "p95_abs_return_difference": round(p95_difference, 10),
        "p99_abs_return_difference": round(p99_difference, 10),
        "direction_agreement": round(direction_agreement, 8),
        "price_ratio_dispersion": round(ratio_dispersion, 8),
        "blockers": blockers,
        "warnings": warnings,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    evidence["evidence_hash"] = _canonical_hash(evidence)
    return evidence


def verify_cross_source_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence = dict(evidence) if isinstance(evidence, dict) else {}
    payload = dict(evidence)
    expected_hash = str(payload.pop("evidence_hash", "") or "")
    blockers: list[str] = []
    schema = str(evidence.get("schema_version") or "")
    if schema not in MARKET_DATA_REVISION_COMPATIBLE_EVIDENCE_SCHEMAS:
        blockers.append("cross_source_evidence_schema_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("cross_source_evidence_hash_invalid")
    primary = str(evidence.get("primary_provider") or "").strip().lower()
    secondary = str(evidence.get("secondary_provider") or "").strip().lower()
    independent = evidence.get("independent_provider_families")
    if not primary or not secondary or primary == secondary or independent is not True:
        blockers.append("cross_source_provider_independence_invalid")
    for field in ("primary_snapshot_hash", "secondary_snapshot_hash"):
        value = str(evidence.get(field) or "").strip().lower()
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            blockers.append(f"cross_source_{field}_invalid")
    integer_fields = (
        "required_overlap",
        "overlap_count",
        "latest_overlap_gap_days",
    )
    numeric_fields = (
        "median_abs_return_difference",
        "p95_abs_return_difference",
        "p99_abs_return_difference",
        "direction_agreement",
        "price_ratio_dispersion",
    )
    numeric: dict[str, float] = {}
    for field in integer_fields:
        value = evidence.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            blockers.append(f"cross_source_{field}_invalid")
            numeric[field] = 0.0
        else:
            numeric[field] = float(value)
    for field in numeric_fields:
        value = evidence.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            blockers.append(f"cross_source_{field}_invalid")
            numeric[field] = 0.0
        else:
            numeric[field] = float(value)
    required_overlap = int(numeric.get("required_overlap", 0))
    overlap_count = int(numeric.get("overlap_count", 0))
    latest_gap = int(numeric.get("latest_overlap_gap_days", 0))
    if required_overlap < 2 or overlap_count < 0 or latest_gap < 0:
        blockers.append("cross_source_count_contract_invalid")
    for field in (
        "median_abs_return_difference",
        "p95_abs_return_difference",
        "p99_abs_return_difference",
        "price_ratio_dispersion",
    ):
        if numeric.get(field, 0.0) < 0.0:
            blockers.append(f"cross_source_{field}_negative")
    if not (
        numeric.get("median_abs_return_difference", 0.0)
        <= numeric.get("p95_abs_return_difference", 0.0)
        <= numeric.get("p99_abs_return_difference", 0.0)
    ):
        blockers.append("cross_source_return_quantiles_invalid")
    if overlap_count and (not _row_date({"date": evidence.get("overlap_first")}) or not _row_date({"date": evidence.get("overlap_last")})):
        blockers.append("cross_source_overlap_dates_invalid")
    elif overlap_count and str(evidence.get("overlap_first") or "") > str(evidence.get("overlap_last") or ""):
        blockers.append("cross_source_overlap_date_order_invalid")
    semantic_blockers: list[str] = []
    if overlap_count < 30:
        semantic_blockers.append("cross_source_overlap_too_small")
    if numeric.get("median_abs_return_difference", 0.0) > 0.002:
        semantic_blockers.append("cross_source_median_return_divergence")
    if numeric.get("p95_abs_return_difference", 0.0) > 0.01:
        semantic_blockers.append("cross_source_p95_return_divergence")
    direction_agreement = numeric.get("direction_agreement", 0.0)
    if not 0.0 <= direction_agreement <= 1.0 or direction_agreement < 0.95:
        semantic_blockers.append("cross_source_direction_agreement_low")
    ratio_dispersion = numeric.get("price_ratio_dispersion", 0.0)
    if ratio_dispersion < 0.0 or ratio_dispersion > 0.15:
        semantic_blockers.append("cross_source_price_ratio_unstable")
    declared_blockers = [str(item) for item in evidence.get("blockers") or [] if str(item)]
    expected_status = (
        "BLOCK"
        if semantic_blockers or declared_blockers
        else "PASS"
        if overlap_count >= required_overlap and latest_gap <= 10
        else "REVIEW"
    )
    if str(evidence.get("status") or "") != expected_status:
        blockers.append("cross_source_status_semantic_mismatch")
    if semantic_blockers and not declared_blockers:
        blockers.extend(f"cross_source_undeclared_semantic_blocker:{item}" for item in semantic_blockers)
    if schema == MARKET_DATA_REVISION_SCHEMA_VERSION:
        primary_snapshot = (
            dict(evidence.get("primary_snapshot") or {})
            if isinstance(evidence.get("primary_snapshot"), dict)
            else {}
        )
        secondary_snapshot = (
            dict(evidence.get("secondary_snapshot") or {})
            if isinstance(evidence.get("secondary_snapshot"), dict)
            else {}
        )
        primary_audit = verify_market_data_snapshot(primary_snapshot)
        secondary_audit = verify_market_data_snapshot(secondary_snapshot)
        blockers.extend(
            f"cross_source_primary_snapshot:{item}"
            for item in primary_audit.get("blockers") or []
        )
        blockers.extend(
            f"cross_source_secondary_snapshot:{item}"
            for item in secondary_audit.get("blockers") or []
        )
        rebuilt = build_cross_source_evidence(
            primary_snapshot,
            secondary_snapshot,
            required_overlap=required_overlap if required_overlap >= 2 else 2,
        )
        if set(evidence) != set(rebuilt):
            blockers.append("cross_source_evidence_fields_invalid")
        for field, expected in rebuilt.items():
            if field != "evidence_hash" and evidence.get(field) != expected:
                blockers.append(f"cross_source_semantic_mismatch:{field}")
    else:
        blockers.append("cross_source_snapshot_content_missing")
    if (
        evidence.get("research_only") is not True
        or evidence.get("paper_authorized") is not False
        or evidence.get("live_order_allowed") is not False
    ):
        blockers.append("cross_source_evidence_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "evidence_hash": expected_hash,
        "evidence_status": str(evidence.get("status") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class MarketDataRevisionLedger:
    """Content-addressed snapshots plus immutable revision and cross-source evidence."""

    def __init__(
        self,
        db_path: Path | str,
        now_ms: Callable[[], int],
        *,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if not self.read_only:
            self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = connect_runtime_sqlite(self.db_path, read_only=self.read_only)
        connection.row_factory = sqlite3.Row
        if not self.read_only:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _ensure_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS market_data_revision_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_data_snapshots (
                    snapshot_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    provider_family TEXT NOT NULL,
                    role TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    session TEXT NOT NULL,
                    first_observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_data_latest_snapshots (
                    scope_key TEXT PRIMARY KEY,
                    snapshot_hash TEXT NOT NULL,
                    state_status TEXT NOT NULL,
                    blocking_event_hash TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_data_revision_events (
                    event_hash TEXT PRIMARY KEY,
                    scope_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    provider_family TEXT NOT NULL,
                    role TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    status TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_market_revision_events_latest
                    ON market_data_revision_events(symbol, observed_at DESC);
                CREATE TABLE IF NOT EXISTS market_data_cross_source_evidence (
                    evidence_hash TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    primary_provider TEXT NOT NULL,
                    secondary_provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    observed_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_market_cross_source_latest
                    ON market_data_cross_source_evidence(symbol, observed_at DESC);
                CREATE TABLE IF NOT EXISTS market_data_latest_cross_source (
                    symbol TEXT PRIMARY KEY,
                    evidence_hash TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_data_revision_resolutions (
                    resolution_hash TEXT PRIMARY KEY,
                    event_hash TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    resolved_at INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO market_data_revision_schema(key, value) VALUES('schema_version', ?)",
                (MARKET_DATA_REVISION_SCHEMA_VERSION,),
            )
            self._reconcile_latest_blocking_states(connection)
            connection.commit()

    @staticmethod
    def _scope_key(snapshot: dict[str, Any]) -> str:
        role = str(snapshot.get("role") or "PROVIDER_OBSERVATION").upper()
        first_date = str(snapshot.get("first_date") or "") if role == "BACKTEST_DATASET" else ""
        through_date = str(snapshot.get("through_date") or "") if role == "BACKTEST_DATASET" else ""
        parts = [
            role,
            str(snapshot.get("symbol") or "").upper(),
            str(snapshot.get("provider_family") or "unknown").lower(),
            str(snapshot.get("interval") or "1d").lower(),
            str(snapshot.get("session") or "regular").lower(),
            first_date,
            through_date,
        ]
        if role == "BACKTEST_DATASET":
            parts.append(str(snapshot.get("lineage_id") or ""))
        return "|".join(parts)

    @staticmethod
    def _snapshot_from_connection(connection: sqlite3.Connection, snapshot_hash: str) -> dict[str, Any]:
        if not snapshot_hash:
            return {}
        row = connection.execute(
            "SELECT payload_json FROM market_data_snapshots WHERE snapshot_hash = ?",
            (snapshot_hash,),
        ).fetchone()
        return json.loads(row["payload_json"]) if row else {}

    def _intrinsic_event_status(self, connection: sqlite3.Connection, payload: dict[str, Any]) -> str:
        stored_status = str(payload.get("intrinsic_status") or payload.get("status") or "REVIEW")
        rebuild_required = (
            str(payload.get("schema_version") or "") != MARKET_DATA_REVISION_SCHEMA_VERSION
            or "prior_unresolved_historical_revision" in list(payload.get("blockers") or [])
        )
        if not rebuild_required:
            return stored_status
        previous = self._snapshot_from_connection(
            connection,
            str(payload.get("previous_snapshot_hash") or ""),
        )
        current = self._snapshot_from_connection(
            connection,
            str(payload.get("current_snapshot_hash") or ""),
        )
        if not current:
            return "BLOCK"
        return str(compare_market_data_snapshots(previous, current).get("status") or "BLOCK")

    def _first_unresolved_intrinsic_block(
        self,
        connection: sqlite3.Connection,
        scope_key: str,
    ) -> str:
        rows = connection.execute(
            """
            SELECT event.event_hash, event.payload_json
            FROM market_data_revision_events event
            LEFT JOIN market_data_revision_resolutions resolution
              ON resolution.event_hash = event.event_hash
            WHERE event.scope_key = ? AND event.status = 'BLOCK'
              AND resolution.resolution_hash IS NULL
            ORDER BY event.observed_at, event.rowid
            """,
            (scope_key,),
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            if self._intrinsic_event_status(connection, payload) == "BLOCK":
                return str(row["event_hash"] or "")
        return ""

    def _latest_intrinsic_state(
        self,
        connection: sqlite3.Connection,
        scope_key: str,
        snapshot_hash: str,
    ) -> str:
        rows = connection.execute(
            """
            SELECT event.event_hash, event.payload_json,
                   resolution.resolution_hash
            FROM market_data_revision_events event
            LEFT JOIN market_data_revision_resolutions resolution
              ON resolution.event_hash = event.event_hash
            WHERE event.scope_key = ?
            ORDER BY event.observed_at DESC, event.rowid DESC
            """,
            (scope_key,),
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            if str(payload.get("current_snapshot_hash") or "") != snapshot_hash:
                continue
            intrinsic_status = self._intrinsic_event_status(connection, payload)
            if intrinsic_status == "BLOCK" and row["resolution_hash"]:
                return "PASS"
            return intrinsic_status if intrinsic_status in {"PASS", "REVIEW", "BLOCK"} else "REVIEW"
        return "PASS"

    def _reconcile_latest_blocking_states(self, connection: sqlite3.Connection) -> None:
        latest_rows = connection.execute(
            "SELECT scope_key, snapshot_hash, state_status, blocking_event_hash FROM market_data_latest_snapshots"
        ).fetchall()
        for row in latest_rows:
            scope_key = str(row["scope_key"] or "")
            root_event_hash = self._first_unresolved_intrinsic_block(connection, scope_key)
            if root_event_hash:
                state_status = "BLOCK"
                blocking_event_hash = root_event_hash
            else:
                state_status = self._latest_intrinsic_state(
                    connection,
                    scope_key,
                    str(row["snapshot_hash"] or ""),
                )
                blocking_event_hash = ""
            if (
                state_status != str(row["state_status"] or "")
                or blocking_event_hash != str(row["blocking_event_hash"] or "")
            ):
                connection.execute(
                    """
                    UPDATE market_data_latest_snapshots
                    SET state_status = ?, blocking_event_hash = ?
                    WHERE scope_key = ?
                    """,
                    (state_status, blocking_event_hash, scope_key),
                )

    def record_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="market_data_revision_ledger")
        current = dict(snapshot or {})
        if not current.get("snapshot_hash"):
            raise ValueError("market_data_snapshot_hash_required")
        scope_key = self._scope_key(current)
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            latest = connection.execute(
                "SELECT snapshot_hash, state_status, blocking_event_hash FROM market_data_latest_snapshots WHERE scope_key = ?",
                (scope_key,),
            ).fetchone()
            previous: dict[str, Any] = {}
            if latest:
                row = connection.execute(
                    "SELECT payload_json FROM market_data_snapshots WHERE snapshot_hash = ?",
                    (str(latest["snapshot_hash"] or ""),),
                ).fetchone()
                previous = json.loads(row["payload_json"]) if row else {}
            intrinsic_evidence = compare_market_data_snapshots(previous, current)
            intrinsic_evidence["intrinsic_status"] = str(intrinsic_evidence.get("status") or "REVIEW")
            intrinsic_evidence["event_hash"] = _canonical_hash({
                key: value for key, value in intrinsic_evidence.items() if key != "event_hash"
            })
            carried_blocking_event = self._first_unresolved_intrinsic_block(connection, scope_key)
            blocking_event_hash = carried_blocking_event or (
                str(intrinsic_evidence["event_hash"])
                if intrinsic_evidence["intrinsic_status"] == "BLOCK" else ""
            )
            evidence = dict(intrinsic_evidence)
            if blocking_event_hash:
                evidence["status"] = "BLOCK"
                evidence["blockers"] = list(intrinsic_evidence.get("blockers") or [])
                if carried_blocking_event:
                    evidence["blockers"] = list(dict.fromkeys([
                        *evidence["blockers"],
                        "prior_unresolved_historical_revision",
                    ]))
                evidence["effective_state_hash"] = _canonical_hash({
                    "event_hash": intrinsic_evidence["event_hash"],
                    "status": evidence["status"],
                    "blockers": evidence["blockers"],
                    "blocking_event_hash": blocking_event_hash,
                })
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO market_data_snapshots(
                    snapshot_hash, symbol, provider_family, role, interval, session,
                    first_observed_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(current["snapshot_hash"]),
                    str(current.get("symbol") or "").upper(),
                    str(current.get("provider_family") or "unknown"),
                    str(current.get("role") or "PROVIDER_OBSERVATION"),
                    str(current.get("interval") or "1d"),
                    str(current.get("session") or "regular"),
                    stamp,
                    json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            if (
                intrinsic_evidence["classification"] != "UNCHANGED"
                or intrinsic_evidence["intrinsic_status"] == "BLOCK"
            ):
                connection.execute(
                    """
                    INSERT OR IGNORE INTO market_data_revision_events(
                        event_hash, scope_key, symbol, provider_family, role,
                        classification, status, observed_at, payload_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(intrinsic_evidence["event_hash"]),
                        scope_key,
                        str(intrinsic_evidence.get("symbol") or "").upper(),
                        str(intrinsic_evidence.get("provider_family") or "unknown"),
                        str(intrinsic_evidence.get("role") or "PROVIDER_OBSERVATION"),
                        str(intrinsic_evidence.get("classification") or "UNKNOWN"),
                        str(intrinsic_evidence.get("intrinsic_status") or "REVIEW"),
                        stamp,
                        json.dumps(intrinsic_evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    ),
                )
            connection.execute(
                """
                INSERT INTO market_data_latest_snapshots(
                    scope_key, snapshot_hash, state_status, blocking_event_hash, updated_at
                ) VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(scope_key) DO UPDATE SET
                    snapshot_hash=excluded.snapshot_hash,
                    state_status=excluded.state_status,
                    blocking_event_hash=excluded.blocking_event_hash,
                    updated_at=excluded.updated_at
                """,
                (scope_key, str(current["snapshot_hash"]), str(evidence["status"]), blocking_event_hash, stamp),
            )
            connection.commit()
        return {
            **evidence,
            "scope_key": scope_key,
            "blocking_event_hash": blocking_event_hash,
            "current": _public_snapshot(current),
            "previous": _public_snapshot(previous),
        }

    def latest_snapshot(
        self,
        *,
        symbol: str,
        provider: str,
        role: str = "PROVIDER_OBSERVATION",
        interval: str = "1d",
        session: str = "regular",
        first_date: str = "",
        through_date: str = "",
        lineage_id: str = "",
    ) -> dict[str, Any]:
        descriptor = {
            "symbol": str(symbol or "").upper(),
            "provider_family": _provider_family(provider),
            "role": str(role or "PROVIDER_OBSERVATION").upper(),
            "interval": str(interval or "1d").lower(),
            "session": str(session or "regular").lower(),
            "first_date": str(first_date or "")[:10],
            "through_date": str(through_date or "")[:10],
            "lineage_id": str(lineage_id or "").strip(),
        }
        scope_key = self._scope_key(descriptor)
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT latest.state_status, latest.blocking_event_hash,
                       latest.updated_at, snapshot.payload_json
                FROM market_data_latest_snapshots latest
                JOIN market_data_snapshots snapshot
                  ON snapshot.snapshot_hash = latest.snapshot_hash
                WHERE latest.scope_key = ?
                """,
                (scope_key,),
            ).fetchone()
        if not row:
            return {}
        return {
            "scope_key": scope_key,
            "state_status": str(row["state_status"] or "REVIEW"),
            "blocking_event_hash": str(row["blocking_event_hash"] or ""),
            "updated_at": int(row["updated_at"] or 0),
            "snapshot": json.loads(row["payload_json"]),
        }

    def snapshot_by_hash(self, snapshot_hash: str) -> dict[str, Any]:
        clean_hash = str(snapshot_hash or "").strip()
        if not clean_hash:
            return {}
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM market_data_snapshots WHERE snapshot_hash = ?",
                (clean_hash,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else {}

    def record_cross_source(self, evidence: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="market_data_revision_ledger")
        payload = dict(evidence or {})
        if not payload.get("evidence_hash"):
            raise ValueError("cross_source_evidence_hash_required")
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO market_data_cross_source_evidence(
                    evidence_hash, symbol, primary_provider, secondary_provider,
                    status, observed_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payload["evidence_hash"]),
                    str(payload.get("symbol") or "").upper(),
                    str(payload.get("primary_provider") or "unknown"),
                    str(payload.get("secondary_provider") or "unknown"),
                    str(payload.get("status") or "REVIEW"),
                    stamp,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            connection.execute(
                """
                INSERT INTO market_data_latest_cross_source(symbol, evidence_hash, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    evidence_hash=excluded.evidence_hash,
                    updated_at=excluded.updated_at
                """,
                (str(payload.get("symbol") or "").upper(), str(payload["evidence_hash"]), stamp),
            )
            connection.commit()
        return payload

    def resolve_blocking_revision(self, *, scope_key: str, event_hash: str, reason: str) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="market_data_revision_ledger")
        clean_scope = str(scope_key or "").strip()
        clean_event = str(event_hash or "").strip()
        clean_reason = str(reason or "").strip()
        if not clean_scope or not clean_event or not clean_reason:
            raise ValueError("revision_resolution_scope_event_and_reason_required")
        stamp = int(self.now_ms())
        with self._lock, closing(self._connect()) as connection:
            latest = connection.execute(
                "SELECT state_status, blocking_event_hash FROM market_data_latest_snapshots WHERE scope_key = ?",
                (clean_scope,),
            ).fetchone()
            if not latest or str(latest["state_status"] or "") != "BLOCK":
                raise ValueError("revision_scope_is_not_blocked")
            if str(latest["blocking_event_hash"] or "") != clean_event:
                raise ValueError("revision_blocking_event_mismatch")
            connection.execute("BEGIN IMMEDIATE")
            provisional = {
                "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
                "scope_key": clean_scope,
                "event_hash": clean_event,
                "reason": clean_reason,
                "resolved_at": stamp,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            provisional_hash = _canonical_hash(provisional)
            connection.execute(
                """
                INSERT OR IGNORE INTO market_data_revision_resolutions(
                    resolution_hash, event_hash, scope_key, resolved_at, reason, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    provisional_hash, clean_event, clean_scope, stamp, clean_reason,
                    json.dumps({**provisional, "resolution_hash": provisional_hash}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
            next_blocking_event_hash = self._first_unresolved_intrinsic_block(connection, clean_scope)
            post_resolution_status = (
                "BLOCK"
                if next_blocking_event_hash
                else self._latest_intrinsic_state(
                    connection,
                    clean_scope,
                    str(connection.execute(
                        "SELECT snapshot_hash FROM market_data_latest_snapshots WHERE scope_key = ?",
                        (clean_scope,),
                    ).fetchone()["snapshot_hash"] or ""),
                )
            )
            payload = {
                **provisional,
                "next_blocking_event_hash": next_blocking_event_hash,
                "post_resolution_status": post_resolution_status,
            }
            payload["resolution_hash"] = _canonical_hash(payload)
            connection.execute(
                """
                UPDATE market_data_revision_resolutions
                SET resolution_hash = ?, payload_json = ?
                WHERE event_hash = ? AND scope_key = ?
                """,
                (
                    payload["resolution_hash"],
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    clean_event,
                    clean_scope,
                ),
            )
            connection.execute(
                """
                UPDATE market_data_latest_snapshots
                SET state_status = ?, blocking_event_hash = ?, updated_at = ?
                WHERE scope_key = ?
                """,
                (post_resolution_status, next_blocking_event_hash, stamp, clean_scope),
            )
            connection.commit()
        return payload

    def latest_cross_source(self, symbol: str) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT evidence.payload_json
                FROM market_data_latest_cross_source latest
                JOIN market_data_cross_source_evidence evidence
                  ON evidence.evidence_hash = latest.evidence_hash
                WHERE latest.symbol = ?
                """,
                (str(symbol or "").upper(),),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else {}

    def summary(self, symbol: str = "") -> dict[str, Any]:
        clean_symbol = str(symbol or "").upper()
        where = " WHERE symbol = ?" if clean_symbol else ""
        params: tuple[Any, ...] = (clean_symbol,) if clean_symbol else ()
        with self._lock, closing(self._connect()) as connection:
            snapshot_count = int(connection.execute(
                f"SELECT COUNT(*) FROM market_data_snapshots{where}", params
            ).fetchone()[0])
            revision_count = int(connection.execute(
                f"SELECT COUNT(*) FROM market_data_revision_events{where}", params
            ).fetchone()[0])
            blocking_count = int(connection.execute(
                """
                SELECT COUNT(*)
                FROM market_data_latest_snapshots latest
                JOIN market_data_snapshots snapshot
                  ON snapshot.snapshot_hash = latest.snapshot_hash
                WHERE latest.state_status = 'BLOCK'
                """ + (" AND snapshot.symbol = ?" if clean_symbol else ""),
                params,
            ).fetchone()[0])
            blocking_rows = connection.execute(
                """
                SELECT latest.scope_key, latest.blocking_event_hash,
                       latest.updated_at, snapshot.payload_json
                FROM market_data_latest_snapshots latest
                JOIN market_data_snapshots snapshot
                  ON snapshot.snapshot_hash = latest.snapshot_hash
                WHERE latest.state_status = 'BLOCK'
                """ + (" AND snapshot.symbol = ?" if clean_symbol else "") +
                " ORDER BY snapshot.symbol, latest.scope_key",
                params,
            ).fetchall()
            review_count = int(connection.execute(
                """
                SELECT COUNT(*)
                FROM market_data_latest_snapshots latest
                JOIN market_data_snapshots snapshot
                  ON snapshot.snapshot_hash = latest.snapshot_hash
                WHERE latest.state_status = 'REVIEW'
                """ + (" AND snapshot.symbol = ?" if clean_symbol else ""),
                params,
            ).fetchone()[0])
            cross_count = int(connection.execute(
                f"SELECT COUNT(*) FROM market_data_cross_source_evidence{where}", params
            ).fetchone()[0])
            resolution_count = int(connection.execute(
                "SELECT COUNT(*) FROM market_data_revision_resolutions"
            ).fetchone()[0])
            latest_rows = connection.execute(
                """
                SELECT evidence.symbol, evidence.primary_provider, evidence.secondary_provider,
                       evidence.status, latest.updated_at AS observed_at, evidence.payload_json
                FROM market_data_latest_cross_source latest
                JOIN market_data_cross_source_evidence evidence
                  ON evidence.evidence_hash = latest.evidence_hash
                ORDER BY evidence.symbol
                """
            ).fetchall()
        latest_cross_source = [json.loads(row["payload_json"]) for row in latest_rows]
        if clean_symbol:
            latest_cross_source = [item for item in latest_cross_source if item.get("symbol") == clean_symbol]
        cross_block_count = sum(1 for item in latest_cross_source if item.get("status") == "BLOCK")
        cross_review_count = sum(1 for item in latest_cross_source if item.get("status") == "REVIEW")
        unresolved_revisions = []
        for row in blocking_rows:
            snapshot = json.loads(row["payload_json"])
            unresolved_revisions.append({
                "scope_key": str(row["scope_key"] or ""),
                "blocking_event_hash": str(row["blocking_event_hash"] or ""),
                "updated_at": int(row["updated_at"] or 0),
                "schema_version": str(snapshot.get("schema_version") or ""),
                "symbol": str(snapshot.get("symbol") or ""),
                "provider_family": str(snapshot.get("provider_family") or ""),
                "role": str(snapshot.get("role") or ""),
                "first_date": str(snapshot.get("first_date") or ""),
                "last_date": str(snapshot.get("last_date") or ""),
            })
        return {
            "schema_version": MARKET_DATA_REVISION_SCHEMA_VERSION,
            "status": "BLOCK" if blocking_count or cross_block_count else "REVIEW" if review_count or cross_review_count else "PASS",
            "symbol": clean_symbol,
            "snapshot_count": snapshot_count,
            "revision_event_count": revision_count,
            "unresolved_blocking_revision_count": blocking_count,
            "unresolved_blocking_revisions": unresolved_revisions,
            "latest_revision_review_count": review_count,
            "cross_source_evidence_count": cross_count,
            "cross_source_block_count": cross_block_count,
            "cross_source_review_count": cross_review_count,
            "resolution_count": resolution_count,
            "latest_cross_source": latest_cross_source,
            "path": str(self.db_path),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
