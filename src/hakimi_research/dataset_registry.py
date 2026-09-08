"""Self-contained, immutable BTC-USDT spot / 1h snapshots; never consult a cache."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import math
from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd

from hakimi_research.data import parse_okx_candle_response, validate_market_data_frame
from hakimi_research.documents import digest, parse_document, read_document
from hakimi_research.reporting import save_json_report

LEGACY_SCHEMA = "research-dataset-snapshot-v1"
SCHEMA = "research-dataset-snapshot-v2"
HOUR = pd.Timedelta(hours=1)
ORIGIN = "https://www.okx.com"
ENDPOINT = "/api/v5/market/history-candles"


def utc_time(value: object, *, aligned: bool = True) -> pd.Timestamp:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("canonical_utc_Z_required")
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_utc_time") from exc
    if pd.isna(stamp) or stamp.tz is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("utc_required")
    if aligned and stamp != stamp.floor("h"):
        raise ValueError("hour_alignment_required")
    return stamp


def utc_text(stamp: pd.Timestamp) -> str:
    return stamp.isoformat().replace("+00:00", "Z")


def _bounds(start: str, end: str, as_of: str):
    first, last, cutoff = utc_time(start), utc_time(end), utc_time(as_of, aligned=False)
    count = int((last - first) / HOUR)
    if last <= first or last > cutoff or count > 50000:
        raise ValueError("snapshot_range_or_cutoff_invalid")
    return first, last, cutoff


@dataclass(frozen=True)
class DatasetSnapshot:
    document: dict

    @property
    def snapshot_id(self) -> str:
        return self.document["snapshot_id"]

    def frame(self) -> pd.DataFrame:
        checked = verify_snapshot(self.document)
        frame = pd.DataFrame(checked["candles"], columns=["time", "open", "high", "low", "close", "volume"])
        frame["time"] = pd.to_datetime(frame["time"], utc=True)
        return validate_market_data_frame(frame.set_index("time"))


def _build_v1_snapshot(pages: list[dict], *, start: str, end: str, as_of: str,
                       evidence_kind: str = "IMPORTED_UNVERIFIED") -> DatasetSnapshot:
    first, last, cutoff = _bounds(start, end, as_of)
    if evidence_kind not in {"IMPORTED_UNVERIFIED", "PUBLIC_HTTP_CAPTURE", "SYNTHETIC_TEST"}:
        raise ValueError("snapshot_evidence_kind_invalid")
    if type(pages) is not list or not 1 <= len(pages) <= 500:
        raise ValueError("snapshot_pages_invalid")
    frames, receipts, stored_pages = [], [], []
    uncompleted = 0
    raw_timestamps = {}
    for page_index, page in enumerate(pages):
        if type(page) is not dict or set(page) != {"raw_base64", "endpoint", "params", "retrieved_at", "origin"}:
            raise ValueError("snapshot_page_fields_invalid")
        if page["origin"] != ORIGIN or page["endpoint"] != ENDPOINT:
            raise ValueError("snapshot_source_not_supported")
        params = page["params"]
        if type(params) is not dict or params.get("instId") != "BTC-USDT" or params.get("bar") != "1H":
            raise ValueError("snapshot_requires_BTC_USDT_spot_1h")
        retrieved = utc_time(page["retrieved_at"], aligned=False)
        if retrieved < cutoff:
            raise ValueError("snapshot_cutoff_after_retrieval")
        try:
            raw = base64.b64decode(page["raw_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("snapshot_raw_base64_invalid") from exc
        envelope = parse_document(raw, maximum_bytes=8 * 1024 * 1024)
        # Locate duplicates before the lower-level frame validator can reduce
        # the error to an unhelpful generic duplicate-index message.
        if type(envelope.get("data")) is list:
            for row_index, row in enumerate(envelope["data"]):
                if type(row) is list and len(row) == 9 and type(row[0]) is str and row[0].isascii() and row[0].isdigit():
                    timestamp_ms = int(row[0])
                    if timestamp_ms in raw_timestamps:
                        first_page, first_row = raw_timestamps[timestamp_ms]
                        stamp = utc_text(pd.Timestamp(timestamp_ms, unit="ms", tz="UTC"))
                        raise ValueError(f"snapshot_duplicate_raw_timestamp:timestamp={stamp}:page={page_index}:row={row_index}:first_page={first_page}:first_row={first_row}")
                    raw_timestamps[timestamp_ms] = (page_index, row_index)
        frame, receipt = parse_okx_candle_response(raw, endpoint=ENDPOINT, params=params,
                                                retrieved_at=page["retrieved_at"])
        if len(envelope["data"]) > params["limit"]:
            raise ValueError("response_exceeds_requested_limit")
        for row_index, row in enumerate(envelope["data"]):
            timestamp_ms = int(row[0])
            if "after" in params and timestamp_ms >= params["after"]:
                raise ValueError("source_row_outside_after_cursor")
            if "before" in params and timestamp_ms <= params["before"]:
                raise ValueError("source_row_outside_before_cursor")
            stamp = pd.Timestamp(timestamp_ms, unit="ms", tz="UTC")
            if stamp != stamp.floor("h"):
                raise ValueError(f"source_timestamp_wrong_period:timestamp={utc_text(stamp)}:page={page_index}:row={row_index}:expected=1h")
            if row[8] == "1" and stamp + HOUR > retrieved:
                raise ValueError("source_completed_before_close")
            for value in row[1:8]:
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ValueError("source_numeric_invalid") from exc
                if not math.isfinite(number) or number < 0:
                    raise ValueError("source_numeric_invalid")
        frames.append(frame)
        receipts.append(receipt)
        stored_pages.append(dict(page))
        uncompleted += receipt["row_receipt"]["rejected_uncompleted_row_count"]
    combined = pd.concat(frames).sort_index()
    if not combined.index.is_unique:
        repeated = [utc_text(stamp) for stamp in combined.index[combined.index.duplicated()].unique()]
        raise ValueError("snapshot_duplicate_timestamp:timestamps=" + ",".join(repeated))
    selected = combined[(combined.index >= first) & (combined.index < last)]
    expected = pd.date_range(first, last, freq="h", inclusive="left")
    if not selected.index.equals(expected):
        missing = expected.difference(selected.index)
        raise ValueError(f"snapshot_incomplete_range:missing={len(missing)}:timestamps=" + ",".join(utc_text(stamp) for stamp in missing))
    selected = validate_market_data_frame(selected)
    candles = [[utc_text(index), *[float(row[c]) for c in ("open", "high", "low", "close", "volume")]]
               for index, row in selected.iterrows()]
    core = {
        "schema_version": LEGACY_SCHEMA, "dataset_id": "okx-btc-usdt-spot-1h",
        "market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT",
        "timeframe": "1h", "timezone": "UTC", "volume_unit": "base_currency",
        "quote_unit": "USDT", "start": utc_text(first), "end_exclusive": utc_text(last),
        "as_of": utc_text(cutoff), "complete_cutoff": utc_text(last),
        "evidence_kind": evidence_kind,
        "source_authentication": "NOT_CRYPTOGRAPHICALLY_AUTHENTICATED",
        "pages": stored_pages, "source_receipts": receipts, "candles": candles,
        "data_hash": digest(candles),
        "quality": {"status": "PASS", "expected_rows": len(expected), "accepted_rows": len(candles),
                    "rejected_uncompleted_rows": uncompleted,
                    "excluded_outside_range_rows": len(combined) - len(selected),
                    "duplicate_rows": 0, "missing_rows": 0, "complete_only": True},
        "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False,
    }
    return DatasetSnapshot({**core, "snapshot_id": digest(core)})


def _series(document: dict) -> str:
    return document.get("dataset_series_id", document["dataset_id"])


def _checked_lineage(lineage: object) -> dict:
    if type(lineage) is not dict or set(lineage) != {"previous_snapshot_id", "previous_dataset_id"}:
        raise ValueError("snapshot_lineage_fields_invalid")
    snapshot_id, dataset_id = lineage["previous_snapshot_id"], lineage["previous_dataset_id"]
    if snapshot_id is None and dataset_id is None:
        return dict(lineage)
    if (type(snapshot_id) is not str or re.fullmatch("[0-9a-f]{64}", snapshot_id) is None
            or type(dataset_id) is not str or not dataset_id or len(dataset_id) > 180
            or re.fullmatch("[a-z0-9][a-z0-9-]*", dataset_id) is None):
        raise ValueError("snapshot_lineage_identity_invalid")
    return dict(lineage)


def _versioned(base: dict, *, source_format: str, series: str, lineage: dict) -> DatasetSnapshot:
    core = {key: value for key, value in base.items() if key not in {"schema_version", "dataset_id", "snapshot_id"}}
    core.update({
        "schema_version": SCHEMA, "source_format": source_format, "dataset_series_id": series,
        "timestamp_semantics": {"index": "bar_open_time", "bar_close_time": "bar_open_time_plus_1h"},
        "lineage": _checked_lineage(lineage),
        "lineage_status": "RECORDED_REFERENCE" if lineage["previous_snapshot_id"] is not None else "NO_PREDECESSOR",
    })
    # Raw bytes, normalized values, metadata and lineage all identify a version.
    # The stable series name is deliberately distinct from this version identity.
    core["dataset_id"] = series + "-" + digest(core)
    return DatasetSnapshot({**core, "snapshot_id": digest(core)})


def _lineage_for(predecessor: DatasetSnapshot | dict | None, *, series: str, base: dict) -> dict:
    if predecessor is None:
        return {"previous_snapshot_id": None, "previous_dataset_id": None}
    previous = verify_snapshot(predecessor.document if type(predecessor) is DatasetSnapshot else predecessor)
    if _series(previous) != series or any(previous[field] != base[field] for field in
            ("market", "instrument_type", "symbol", "timeframe", "timezone", "volume_unit", "quote_unit")):
        raise ValueError("snapshot_predecessor_series_mismatch")
    return {"previous_snapshot_id": previous["snapshot_id"], "previous_dataset_id": previous["dataset_id"]}


def build_snapshot(pages: list[dict], *, start: str, end: str, as_of: str,
                   evidence_kind: str = "IMPORTED_UNVERIFIED",
                   predecessor: DatasetSnapshot | dict | None = None) -> DatasetSnapshot:
    base = _build_v1_snapshot(pages, start=start, end=end, as_of=as_of, evidence_kind=evidence_kind).document
    # OKX documents newest-first source rows. Validate rather than relying on
    # sorting to hide an unexpected source order. Legacy v1 readers stay intact.
    for page_index, page in enumerate(base["pages"]):
        rows = parse_document(base64.b64decode(page["raw_base64"], validate=True))["data"]
        for row_index in range(1, len(rows)):
            if int(rows[row_index][0]) >= int(rows[row_index - 1][0]):
                stamp = utc_text(pd.Timestamp(int(rows[row_index][0]), unit="ms", tz="UTC"))
                raise ValueError(f"source_timestamp_order_invalid:timestamp={stamp}:page={page_index}:row={row_index}:expected=descending")
    series = "okx-btc-usdt-spot-1h"
    return _versioned(base, source_format="OKX_JSON", series=series,
                      lineage=_lineage_for(predecessor, series=series, base=base))


_CSV_METADATA_FIELDS = {"market", "instrument_type", "symbol", "timeframe", "source", "retrieved_at",
                        "as_of", "volume_unit", "quote_unit", "timezone", "start", "end_exclusive",
                        "completed_bars_only"}
_CSV_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


def _csv_base(raw: bytes, metadata: dict) -> tuple[dict, str]:
    if type(raw) is not bytes or not raw or len(raw) > 32 * 1024 * 1024:
        raise ValueError("csv_raw_bytes_invalid_or_too_large")
    if type(metadata) is not dict or set(metadata) != _CSV_METADATA_FIELDS:
        raise ValueError("csv_metadata_required_fields_invalid")
    expected = {"market": "crypto_spot", "instrument_type": "SPOT", "symbol": "BTC-USDT",
                "timeframe": "1h", "volume_unit": "base_currency", "quote_unit": "USDT", "timezone": "UTC"}
    for field, value in expected.items():
        if type(metadata[field]) is not str or metadata[field] != value:
            raise ValueError("csv_metadata_unsupported:" + field)
    if metadata["completed_bars_only"] is not True:
        raise ValueError("csv_completed_bars_importer_declaration_required")
    source = metadata["source"]
    if type(source) is not str or not source or source != source.strip() or len(source) > 2048:
        raise ValueError("csv_source_declaration_required")
    first, last, cutoff = _bounds(metadata["start"], metadata["end_exclusive"], metadata["as_of"])
    retrieved = utc_time(metadata["retrieved_at"], aligned=False)
    if retrieved < cutoff:
        raise ValueError("csv_cutoff_after_retrieval")
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        if next(reader, None) != _CSV_COLUMNS:
            raise ValueError("csv_exact_header_required:time,open,high,low,close,volume")
        rows, seen = [], {}
        previous = None
        for row_number, row in enumerate(reader, start=2):
            if len(rows) >= 50000 or len(row) != len(_CSV_COLUMNS):
                raise ValueError(f"csv_row_size_or_limit_invalid:row={row_number}")
            try:
                stamp = utc_time(row[0])
            except ValueError as exc:
                raise ValueError(f"csv_timestamp_invalid:row={row_number}:value={row[0]}") from exc
            if stamp in seen:
                raise ValueError(f"csv_duplicate_timestamp:timestamp={utc_text(stamp)}:row={row_number}:first_row={seen[stamp]}")
            if previous is not None and stamp < previous:
                raise ValueError(f"csv_timestamp_order_invalid:timestamp={utc_text(stamp)}:row={row_number}:expected=ascending")
            if stamp + HOUR > retrieved:
                raise ValueError(f"csv_declared_complete_before_close:timestamp={utc_text(stamp)}:row={row_number}")
            try:
                values = [float(value) for value in row[1:]]
            except (ValueError, OverflowError) as exc:
                raise ValueError(f"csv_numeric_invalid:row={row_number}") from exc
            if any(not math.isfinite(value) for value in values) or any(value <= 0 for value in values[:4]) or values[4] < 0:
                raise ValueError(f"csv_numeric_invalid:row={row_number}")
            opening, high, low, close, volume = values
            if high < max(opening, close) or low > min(opening, close) or high < low:
                raise ValueError(f"csv_ohlcv_geometry_invalid:timestamp={utc_text(stamp)}:row={row_number}")
            rows.append([utc_text(stamp), *values])
            seen[stamp], previous = row_number, stamp
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("csv_encoding_or_structure_invalid") from exc
    selected = [row for row in rows if first <= utc_time(row[0]) < last]
    wanted = pd.date_range(first, last, freq="h", inclusive="left")
    available = pd.DatetimeIndex([utc_time(row[0]) for row in selected])
    missing = wanted.difference(available)
    if len(missing):
        raise ValueError(f"csv_incomplete_range:missing={len(missing)}:timestamps=" + ",".join(utc_text(stamp) for stamp in missing))
    receipt = {"schema_version": "csv-source-receipt-v1", "source": source,
               "raw_csv_sha256": hashlib.sha256(raw).hexdigest(), "raw_csv_size": len(raw),
               "retrieved_at": utc_text(retrieved), "normalized_sha256": digest(selected),
               "completion_basis": "IMPORTER_DECLARATION_ONLY", "provider_authentication": "NOT_VERIFIED"}
    base = {**expected, "start": utc_text(first), "end_exclusive": utc_text(last), "as_of": utc_text(cutoff),
            "complete_cutoff": utc_text(last), "evidence_kind": "IMPORTED_UNVERIFIED",
            "source_authentication": "IMPORTER_DECLARATION_NOT_VERIFIED", "pages": [],
            "csv_input": {"raw_base64": base64.b64encode(raw).decode("ascii"), "metadata": dict(metadata)},
            "source_receipts": [receipt], "candles": selected, "data_hash": digest(selected),
            "quality": {"status": "PASS", "expected_rows": len(wanted), "accepted_rows": len(selected),
                        "rejected_uncompleted_rows": 0, "excluded_outside_range_rows": len(rows) - len(selected),
                        "duplicate_rows": 0, "missing_rows": 0, "complete_only": True,
                        "completion_basis": "IMPORTER_DECLARATION_ONLY",
                        "limitations": ["CSV labels, origin and closed-bar status are importer declarations; no OKX confirm or HTTP capture is attested."]},
            "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    series = "csv-btc-usdt-spot-1h-" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    return base, series


def build_csv_snapshot(raw: bytes, metadata: dict, *, predecessor: DatasetSnapshot | dict | None = None) -> DatasetSnapshot:
    base, series = _csv_base(raw, metadata)
    return _versioned(base, source_format="CSV", series=series,
                      lineage=_lineage_for(predecessor, series=series, base=base))


def import_csv(csv_path: str | Path, metadata_path: str | Path,
               *, predecessor: DatasetSnapshot | dict | None = None) -> DatasetSnapshot:
    with Path(csv_path).open("rb") as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    return build_csv_snapshot(raw, read_document(metadata_path), predecessor=predecessor)


def verify_snapshot(document: dict) -> dict:
    if type(document) is not dict or document.get("schema_version") not in {LEGACY_SCHEMA, SCHEMA}:
        raise ValueError("snapshot_schema_invalid")
    if document["schema_version"] == LEGACY_SCHEMA:
        expected = _build_v1_snapshot(document["pages"], start=document["start"], end=document["end_exclusive"],
                                      as_of=document["as_of"], evidence_kind=document["evidence_kind"]).document
    elif document.get("source_format") == "OKX_JSON":
        base = build_snapshot(document["pages"], start=document["start"], end=document["end_exclusive"],
                              as_of=document["as_of"], evidence_kind=document["evidence_kind"]).document
        material = {key: value for key, value in base.items() if key not in
                    {"source_format", "dataset_series_id", "timestamp_semantics", "lineage", "lineage_status"}}
        expected = _versioned(material, source_format="OKX_JSON", series=base["dataset_series_id"],
                              lineage=document["lineage"]).document
    elif document.get("source_format") == "CSV":
        csv_input = document["csv_input"]
        if type(csv_input) is not dict or set(csv_input) != {"raw_base64", "metadata"}:
            raise ValueError("snapshot_csv_input_invalid")
        try:
            raw = base64.b64decode(csv_input["raw_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("snapshot_csv_raw_base64_invalid") from exc
        base, series = _csv_base(raw, csv_input["metadata"])
        expected = _versioned(base, source_format="CSV", series=series, lineage=document["lineage"]).document
    else:
        raise ValueError("snapshot_source_format_invalid")
    if digest(expected) != digest(document):
        raise ValueError("snapshot_content_or_receipt_mismatch")
    return expected


def verify_lineage(child: DatasetSnapshot | dict, parent: DatasetSnapshot | dict) -> dict:
    current = verify_snapshot(child.document if type(child) is DatasetSnapshot else child)
    previous = verify_snapshot(parent.document if type(parent) is DatasetSnapshot else parent)
    if current["schema_version"] != SCHEMA:
        raise ValueError("legacy_snapshot_has_no_version_lineage")
    expected = _lineage_for(previous, series=current["dataset_series_id"], base=current)
    if current["lineage"] != expected or current["snapshot_id"] == previous["snapshot_id"]:
        raise ValueError("snapshot_predecessor_link_mismatch")
    return {"status": "VERIFIED", "snapshot_id": current["snapshot_id"], **expected}


def load_snapshot(path: str | Path) -> DatasetSnapshot:
    return DatasetSnapshot(verify_snapshot(read_document(path)))


def save_snapshot(snapshot: DatasetSnapshot, directory: str | Path) -> Path:
    document = verify_snapshot(snapshot.document)
    return Path(save_json_report(document, directory, "dataset", artifact_id=document["snapshot_id"]))


def import_capture(path: str | Path, *, predecessor: DatasetSnapshot | dict | None = None) -> DatasetSnapshot:
    capture = read_document(path)
    if capture.get("schema_version") == "csv-ohlcv-capture-v1":
        if set(capture) != {"schema_version", "raw_base64", "metadata"}:
            raise ValueError("csv_capture_fields_invalid")
        try:
            raw = base64.b64decode(capture["raw_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("csv_capture_raw_base64_invalid") from exc
        return build_csv_snapshot(raw, capture["metadata"], predecessor=predecessor)
    if set(capture) != {"schema_version", "pages", "start", "end_exclusive", "as_of", "evidence_kind"}:
        raise ValueError("capture_fields_invalid")
    if capture["schema_version"] != "okx-public-capture-v1":
        raise ValueError("capture_schema_invalid")
    return build_snapshot(capture["pages"], start=capture["start"], end=capture["end_exclusive"],
                          as_of=capture["as_of"], evidence_kind=capture["evidence_kind"], predecessor=predecessor)
