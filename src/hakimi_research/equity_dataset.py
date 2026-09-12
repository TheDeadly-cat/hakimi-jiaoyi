"""Immutable imported US common-stock daily bars with explicit session evidence.

This module performs no I/O except explicit local load/save operations. A valid
hash establishes input identity, never the truth or completeness of a provider.
The first economic-research admission is limited to declared action-free windows.
"""
from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import io
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pandas as pd

from hakimi_research.data import validate_market_data_frame
from hakimi_research.documents import canonical_bytes, digest, parse_document, read_document
from hakimi_research.reporting import save_json_report

SCHEMA = "us-equity-daily-snapshot-v1"
MANIFEST_SCHEMA = "us-equity-daily-import-v1"
_NY = ZoneInfo("America/New_York")
_MAX_BYTES = 16 * 1024 * 1024
_SECURITY_FIELDS = {"security_id", "symbol", "exchange", "currency", "instrument_type"}
_MANIFEST_FIELDS = {
    "schema_version", "security", "identity", "calendar", "corporate_actions",
    "price_source", "price_basis", "volume_unit", "bar_timestamp_semantics",
    "completed_bars_only", "as_of", "retrieved_at", "bar_availability_lag_seconds",
    "evidence_kind",
}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != expected:
        raise ValueError("equity_" + label + "_fields_invalid")


def _text(value, label, maximum=2048):
    if type(value) is not str or not value or value != value.strip() or len(value) > maximum:
        raise ValueError("equity_" + label + "_text_invalid")
    return value


def _native(value, depth=0):
    if depth > 24:
        raise ValueError("equity_json_depth_exceeded")
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _native(child, depth + 1)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for child in value.values():
            _native(child, depth + 1)
        return
    raise ValueError("equity_exact_finite_json_required")


def _date(value):
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("equity_date_invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("equity_date_invalid") from exc


def _utc(value):
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value) is None:
        raise ValueError("equity_utc_timestamp_invalid")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("equity_utc_timestamp_invalid") from exc


def _utc_text(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _raw(value, label):
    if type(value) is not str or len(value) > _MAX_BYTES * 2:
        raise ValueError("equity_" + label + "_base64_invalid")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("equity_" + label + "_base64_invalid") from exc
    if not raw or len(raw) > _MAX_BYTES:
        raise ValueError("equity_" + label + "_size_invalid")
    return raw


def _source(value, *, imported_at, label):
    _fields(value, {"name", "reference", "retrieved_at", "raw_base64"}, label + "_source")
    _text(value["name"], label + "_source_name")
    reference = _text(value["reference"], label + "_source_reference")
    if not (reference.startswith("https://") or reference.startswith("urn:")):
        raise ValueError("equity_source_reference_https_or_urn_required")
    if _utc(value["retrieved_at"]) > imported_at:
        raise ValueError("equity_source_retrieved_after_import")
    raw = _raw(value["raw_base64"], label + "_source")
    return {**value, "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "truth_status": "DECLARED_SOURCE_NOT_AUTHENTICATED"}


def _calendar(value, *, imported_at):
    _fields(value, {"timezone", "coverage_start", "coverage_end", "source", "days"}, "calendar")
    if value["timezone"] != "America/New_York":
        raise ValueError("equity_new_york_calendar_required")
    first, last = _date(value["coverage_start"]), _date(value["coverage_end"])
    if last < first or (last - first).days > 3660:
        raise ValueError("equity_calendar_range_invalid")
    source = _source(value["source"], imported_at=imported_at, label="calendar")
    days = value["days"]
    if type(days) is not list or len(days) != (last - first).days + 1:
        raise ValueError("equity_every_calendar_date_must_be_declared")
    sessions = []
    for offset, row in enumerate(days):
        day = first + timedelta(days=offset)
        if type(row) is not dict or row.get("date") != day.isoformat():
            raise ValueError("equity_calendar_date_order_or_coverage_invalid")
        if row.get("kind") == "CLOSED":
            _fields(row, {"date", "kind", "reason"}, "closed_day")
            if row["reason"] not in {"WEEKEND", "HOLIDAY", "EXCHANGE_CLOSURE"}:
                raise ValueError("equity_closed_day_reason_invalid")
            if (day.weekday() >= 5) != (row["reason"] == "WEEKEND"):
                raise ValueError("equity_weekend_declaration_invalid")
        elif row.get("kind") == "OPEN":
            _fields(row, {"date", "kind", "open_utc", "close_utc", "early_close"}, "open_day")
            if day.weekday() >= 5 or type(row["early_close"]) is not bool:
                raise ValueError("equity_regular_session_day_invalid")
            opened, closed = _utc(row["open_utc"]), _utc(row["close_utc"])
            expected_open = datetime.combine(day, time(9, 30), _NY)
            expected_close = datetime.combine(day, time(13 if row["early_close"] else 16), _NY)
            if opened != expected_open or closed != expected_close:
                raise ValueError("equity_regular_session_time_or_dst_invalid")
            sessions.append({"date": day.isoformat(), "open_utc": _utc_text(opened),
                             "close_utc": _utc_text(closed), "early_close": row["early_close"]})
        else:
            raise ValueError("equity_calendar_day_kind_invalid")
    if not sessions:
        raise ValueError("equity_calendar_requires_open_sessions")
    return first, last, sessions, {**value, "source": source}


def _identity(value, security, *, first, last, imported_at):
    _fields(value, {"stable_within_coverage", "valid_from", "valid_through", "selection_basis", "source"}, "identity")
    if type(value["stable_within_coverage"]) is not bool:
        raise ValueError("equity_identity_stable_exact_bool_required")
    valid_from, valid_through = _date(value["valid_from"]), _date(value["valid_through"])
    if valid_through < valid_from:
        raise ValueError("equity_identity_validity_range_invalid")
    _text(value["selection_basis"], "selection_basis")
    source = _source(value["source"], imported_at=imported_at, label="identity")
    blockers = []
    if not value["stable_within_coverage"]:
        blockers.append("SECURITY_IDENTITY_NOT_STABLE")
    if valid_from > first or valid_through < last:
        blockers.append("SECURITY_IDENTITY_COVERAGE_INCOMPLETE")
    return {**value, "security_id": security["security_id"], "source": source}, blockers


def _actions(value, security, *, first, last, imported_at):
    _fields(value, {"coverage_start", "coverage_end", "coverage_status", "source", "actions"}, "corporate_actions")
    start, end = _date(value["coverage_start"]), _date(value["coverage_end"])
    if end < start or value["coverage_status"] not in {"DECLARED_COMPLETE", "UNKNOWN"}:
        raise ValueError("equity_corporate_action_coverage_invalid")
    source = _source(value["source"], imported_at=imported_at, label="corporate_actions")
    blockers = []
    if value["coverage_status"] != "DECLARED_COMPLETE" or start > first or end < last:
        blockers.append("CORPORATE_ACTION_COVERAGE_UNVERIFIED_OR_INCOMPLETE")
    actions = value["actions"]
    if type(actions) is not list or len(actions) > 10000:
        raise ValueError("equity_corporate_actions_list_invalid")
    identities = set()
    for action in actions:
        _fields(action, {"action_id", "security_id", "action_type", "effective_date", "source_reference", "details"}, "corporate_action")
        action_id = _text(action["action_id"], "action_id", 180)
        if action_id in identities or action["security_id"] != security["security_id"]:
            raise ValueError("equity_action_identity_mismatch_or_duplicate")
        identities.add(action_id)
        _text(action["action_type"], "action_type", 80)
        _text(action["source_reference"], "action_source_reference")
        if type(action["details"]) is not dict:
            raise ValueError("equity_action_details_object_required")
        effective = _date(action["effective_date"])
        if not start <= effective <= end:
            raise ValueError("equity_action_outside_declared_coverage")
        if first <= effective <= last:
            blockers.append("CORPORATE_ACTION_ACCOUNTING_NOT_IMPLEMENTED:" + action_id)
    return {**value, "source": source}, blockers


def _build(raw_csv, raw_manifest, manifest_encoding):
    if type(raw_csv) is not bytes or not raw_csv or len(raw_csv) > _MAX_BYTES:
        raise ValueError("equity_csv_bytes_or_size_invalid")
    manifest = parse_document(raw_manifest, maximum_bytes=_MAX_BYTES)
    _native(manifest)
    _fields(manifest, _MANIFEST_FIELDS, "manifest")
    if manifest["schema_version"] != MANIFEST_SCHEMA:
        raise ValueError("equity_manifest_schema_invalid")
    if manifest["evidence_kind"] not in {"IMPORTED_UNVERIFIED", "SYNTHETIC_TEST"}:
        raise ValueError("equity_evidence_kind_invalid")
    if manifest["price_basis"] != "RAW_UNADJUSTED":
        raise ValueError("equity_only_raw_unadjusted_prices_supported")
    if manifest["volume_unit"] != "shares" or manifest["bar_timestamp_semantics"] != "SESSION_DATE":
        raise ValueError("equity_daily_shares_session_date_required")
    if manifest["completed_bars_only"] is not True:
        raise ValueError("equity_completed_bars_only_required")
    retrieved, as_of = _utc(manifest["retrieved_at"]), _utc(manifest["as_of"])
    if as_of > retrieved:
        raise ValueError("equity_as_of_after_retrieval")
    lag = manifest["bar_availability_lag_seconds"]
    if type(lag) is not int or not 1 <= lag <= 7 * 86400:
        raise ValueError("equity_positive_explicit_bar_availability_lag_required")
    security = manifest["security"]
    _fields(security, _SECURITY_FIELDS, "security")
    for key, value in security.items():
        _text(value, key, 180)
    if security["exchange"] not in {"XNYS", "XNAS"} or security["currency"] != "USD" or security["instrument_type"] != "COMMON_STOCK":
        raise ValueError("equity_us_usd_common_stock_only")
    if re.fullmatch(r"[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?", security["symbol"]) is None:
        raise ValueError("equity_symbol_invalid")
    first, last, sessions, calendar = _calendar(manifest["calendar"], imported_at=retrieved)
    identity, blockers = _identity(manifest["identity"], security, first=first, last=last, imported_at=retrieved)
    actions, action_blockers = _actions(manifest["corporate_actions"], security, first=first, last=last, imported_at=retrieved)
    blockers.extend(action_blockers)
    price_source = _source(manifest["price_source"], imported_at=retrieved, label="price")
    if _utc(price_source["retrieved_at"]) != retrieved:
        raise ValueError("equity_price_retrieval_must_match_import")
    # A price receipt must bind the actual CSV, not a disconnected declaration.
    if _raw(price_source["raw_base64"], "price_source") != raw_csv:
        raise ValueError("equity_price_source_bytes_mismatch")
    for session in sessions:
        if _utc(session["close_utc"]) + timedelta(seconds=lag) > as_of:
            raise ValueError("equity_session_bar_not_complete_and_available")
    try:
        rows = list(csv.reader(io.StringIO(raw_csv.decode("utf-8-sig"), newline=""), strict=True))
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("equity_csv_encoding_or_structure_invalid") from exc
    if not rows or rows[0] != ["session_date", "open", "high", "low", "close", "volume"]:
        raise ValueError("equity_csv_exact_daily_header_required")
    if len(rows) - 1 != len(sessions):
        raise ValueError("equity_csv_session_count_mismatch")
    candles = []
    for row, session in zip(rows[1:], sessions):
        if len(row) != 6 or row[0] != session["date"]:
            raise ValueError("equity_csv_session_missing_extra_duplicate_or_out_of_order")
        try:
            values = [float(value) for value in row[1:]]
        except (ValueError, OverflowError) as exc:
            raise ValueError("equity_csv_numeric_invalid") from exc
        if any(not math.isfinite(value) for value in values) or any(value <= 0 for value in values[:4]) or values[4] < 0:
            raise ValueError("equity_csv_numeric_invalid")
        opening, high, low, close, volume = values
        if high < max(opening, close) or low > min(opening, close) or low > high:
            raise ValueError("equity_csv_ohlcv_geometry_invalid")
        candles.append([session["open_utc"], opening, high, low, close, volume])
    core = {
        "schema_version": SCHEMA, "security": security, "security_identity": identity,
        "market": "us_equity", "timeframe": "1d", "timezone": "America/New_York",
        "price_basis": "RAW_UNADJUSTED", "volume_unit": "shares", "quote_unit": "USD",
        "sessions": sessions, "calendar": calendar, "corporate_actions": actions,
        "candles": candles, "data_hash": digest(candles),
        "start": sessions[0]["open_utc"], "end_exclusive": _utc_text(datetime.combine(last + timedelta(days=1), time(), timezone.utc)),
        "as_of": manifest["as_of"], "retrieved_at": manifest["retrieved_at"],
        "bar_availability_lag_seconds": lag,
        "availability_policy": "SESSION_CLOSE_PLUS_DECLARED_LAG_NOT_HISTORICAL_RECEIPT",
        "price_source": price_source, "evidence_kind": manifest["evidence_kind"],
        "source_authentication": "NOT_CRYPTOGRAPHICALLY_AUTHENTICATED",
        "raw_input": {"csv_base64": base64.b64encode(raw_csv).decode("ascii"),
                      "csv_sha256": hashlib.sha256(raw_csv).hexdigest(),
                      "manifest_base64": base64.b64encode(raw_manifest).decode("ascii"),
                      "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
                      "manifest_encoding": manifest_encoding},
        "quality": {"status": "PASS", "expected_rows": len(sessions), "accepted_rows": len(candles),
                    "missing_rows": 0, "duplicate_rows": 0, "complete_only": True,
                    "calendar_coverage": "SOURCE_BACKED_IMPORTER_DECLARATION_NOT_EXTERNAL_TRUTH"},
        "research_admission": {"allowed": not blockers, "block_reasons": blockers,
                               "scope": "ACTION_FREE_FIXED_WINDOW_ONLY",
                               "source_truth_verified": False,
                               "synthetic_only": manifest["evidence_kind"] == "SYNTHETIC_TEST"},
        "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False,
    }
    return EquitySnapshot({**core, "snapshot_id": digest(core)})


@dataclass(frozen=True)
class EquitySnapshot:
    document: dict

    @property
    def snapshot_id(self):
        return self.document["snapshot_id"]

    def frame(self):
        checked = verify_equity_snapshot(self.document)
        frame = pd.DataFrame(checked["candles"], columns=["time", "open", "high", "low", "close", "volume"])
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        return validate_market_data_frame(frame.set_index("time"))


def build_equity_snapshot(csv_bytes: bytes, manifest: dict | bytes) -> EquitySnapshot:
    """Bytes preserve original manifest encoding; a dict stores canonical JSON."""
    if type(manifest) is bytes:
        raw, encoding = manifest, "ORIGINAL_JSON_BYTES"
    elif type(manifest) is dict:
        _native(manifest)
        raw, encoding = canonical_bytes(manifest), "CANONICAL_JSON_FROM_OBJECT"
    else:
        raise ValueError("equity_manifest_bytes_or_exact_dict_required")
    return _build(csv_bytes, raw, encoding)


def verify_equity_snapshot(document: dict) -> dict:
    _native(document)
    if type(document) is not dict or document.get("schema_version") != SCHEMA:
        raise ValueError("equity_snapshot_schema_invalid")
    raw = document.get("raw_input")
    _fields(raw, {"csv_base64", "csv_sha256", "manifest_base64", "manifest_sha256", "manifest_encoding"}, "snapshot_raw_input")
    if raw["manifest_encoding"] not in {"ORIGINAL_JSON_BYTES", "CANONICAL_JSON_FROM_OBJECT"}:
        raise ValueError("equity_snapshot_manifest_encoding_invalid")
    csv_bytes = _raw(raw["csv_base64"], "csv")
    manifest_bytes = _raw(raw["manifest_base64"], "manifest")
    if raw["manifest_encoding"] == "CANONICAL_JSON_FROM_OBJECT" and canonical_bytes(parse_document(manifest_bytes)) != manifest_bytes:
        raise ValueError("equity_canonical_manifest_bytes_mismatch")
    expected = _build(csv_bytes, manifest_bytes, raw["manifest_encoding"]).document
    if canonical_bytes(expected) != canonical_bytes(document):
        raise ValueError("equity_snapshot_content_or_receipt_mismatch")
    return expected


def load_equity_snapshot(path: str | Path) -> EquitySnapshot:
    return EquitySnapshot(verify_equity_snapshot(read_document(path)))


def save_equity_snapshot(snapshot: EquitySnapshot, directory: str | Path) -> Path:
    checked = verify_equity_snapshot(snapshot.document)
    return Path(save_json_report(checked, directory, "equity_dataset", artifact_id=checked["snapshot_id"]))
