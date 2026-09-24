"""Read retained quote receipts only; never fetch, repair, or admit market data."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slots(session):
    """Declared END-label interpretation; labels alone do not prove trade coverage."""
    opening = datetime.fromisoformat(session["open_utc"].replace("Z", "+00:00"))
    closing = datetime.fromisoformat(session["close_utc"].replace("Z", "+00:00"))
    result, point = [], opening
    while point < closing:
        point = min(point + timedelta(hours=1), closing)
        result.append(point.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S"))
    return result


def inspect_window(daily, hourly, calendar):
    sessions = [row for row in calendar["days"] if row["kind"] == "OPEN"]
    session_dates = [row["date"] for row in sessions]
    daily_dates = [row["time_key"][:10] for row in daily]
    groups = {}
    for row in hourly:
        groups.setdefault(row["time_key"][:10], []).append(row)
    if daily_dates != session_dates or list(groups) != session_dates:
        raise ValueError("source_diagnostics_session_coverage_or_order_mismatch")
    duplicate_labels = len(hourly) - len({row["time_key"] for row in hourly})
    if duplicate_labels or len(set(daily_dates)) != len(daily_dates):
        raise ValueError("source_diagnostics_duplicate_bar_labels")
    differences, volume_deltas = [], []
    for day, session in zip(daily, sessions):
        rows = groups[session["date"]]
        expected = slots(session)
        if [row["time_key"] for row in rows] != expected:
            raise ValueError("source_diagnostics_end_label_grid_mismatch:" + session["date"])
        for row in [day, *rows]:
            values = {key: Decimal(str(row[key])) for key in ("open", "high", "low", "close", "volume")}
            if not all(value.is_finite() and value > 0 for value in values.values()):
                raise ValueError("source_diagnostics_invalid_number")
            if not values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"]:
                raise ValueError("source_diagnostics_incoherent_OHLC")
        aggregate = {"open": Decimal(str(rows[0]["open"])), "close": Decimal(str(rows[-1]["close"])),
                     "high": max(Decimal(str(row["high"])) for row in rows),
                     "low": min(Decimal(str(row["low"])) for row in rows)}
        volume_delta = Decimal(str(day["volume"])) - sum(Decimal(str(row["volume"])) for row in rows)
        volume_deltas.append(volume_delta)
        for field, computed in aggregate.items():
            original = Decimal(str(day[field]))
            if original == computed:
                continue
            extrema_rows = [row for row in rows if Decimal(str(row[field])) == computed]
            delta = original - computed
            differences.append({"date": session["date"], "field": field,
                "daily_value": str(original), "RTH_aggregate_value": str(computed),
                "daily_minus_RTH": str(delta), "absolute_delta_bps_of_daily": str(abs(delta / original) * 10000),
                "extremum_labels": [row["time_key"] for row in extrema_rows],
                "last_partial_bar_label": expected[-1], "last_partial_bar_included": True,
                "early_close": session["early_close"], "observed_bar_count": len(rows),
                "daily_minus_RTH_volume": str(volume_delta), "cause_status": "UNKNOWN",
                "impact": "STOP_OR_TARGET_TRIGGER_AND_FILL_PRICE_MAY_DIFFER_NO_COUNTERFACTUAL_RUN",
                "decision": "KEEP_ORIGINAL_EVENT_EXCLUDED"})
    return {"sessions": len(sessions), "daily_rows": len(daily), "hourly_rows": len(hourly),
        "duplicate_bar_labels": duplicate_labels, "declared_end_label_grid_complete": True,
        "early_close_sessions": sum(row["early_close"] for row in sessions),
        "volume_difference_sessions": sum(value != 0 for value in volume_deltas),
        "volume_delta_direction": dict(Counter("positive" if value > 0 else "negative" if value < 0 else "zero" for value in volume_deltas)),
        "differences": differences}


def diagnose(root, collection_review, prepared):
    root = Path(root).resolve()
    roots = [root / ("provider-collection-20260920-" + suffix) for suffix in ("first", "continuation", "remaining")]
    reviewed = read(collection_review)
    files, responses, requests = {}, {}, {}
    for row in reviewed["request_receipt_hashes"]:
        label = row["label"]
        prefix = f'{row["sequence"]:02d}-{label}'
        for suffix, hash_key in (("started", "start_sha256"), ("response", "response_sha256")):
            candidates = [directory / (prefix + "." + suffix + ".private.json") for directory in roots]
            matches = [path for path in candidates if path.is_file()]
            if len(matches) != 1 or sha(matches[0]) != row[hash_key]:
                raise ValueError("source_diagnostics_receipt_identity_mismatch:" + prefix)
            files[str(matches[0])] = row[hash_key]
            content = read(matches[0])
            if suffix == "started":
                requests[label] = content
            else:
                responses[label] = content
                reply = content["returned_reply"]
                if reply["ret"] != 0 or reply.get("page_req_key") is not None:
                    raise ValueError("source_diagnostics_failed_or_incomplete_reply:" + label)
    windows = []
    for event in read(prepared)["events"]:
        quarter = event["fiscal_quarter"]
        calendar_path = root / "prepared-inputs" / quarter / "calendar.private.json"
        files[str(calendar_path)] = sha(calendar_path)
        calendar = read(calendar_path)
        source_ids = {}
        for kind in ("K_DAY", "K_60M"):
            label = quarter + "-" + kind
            request = requests[label]["request"]["kwargs"]
            expected = {"code": "US.AMD", "start": event["snapshot_start"], "end": event["score_end"],
                "ktype": kind, "autype": "None", "page_req_key": None, "extended_time": False, "session": "RTH",
                "max_count": 38 if kind == "K_DAY" else event["max_K60M_rows"]}
            if request != expected:
                raise ValueError("source_diagnostics_request_scope_mismatch:" + label)
            identity = next(row for row in reviewed["request_receipt_hashes"] if row["label"] == label)
            source_ids[kind] = {"request_sha256": identity["start_sha256"], "response_sha256": identity["response_sha256"],
                "request": request, "request_started_at": requests[label]["started_at"],
                "response_completed_at": responses[label]["completed_at"], "next_page_key": None,
                "provider_revision_id": "NOT_PRESENT_IN_RETAINED_SDK_ROWS"}
        result = inspect_window(responses[quarter + "-K_DAY"]["returned_reply"]["rows"],
                                responses[quarter + "-K_60M"]["returned_reply"]["rows"], calendar)
        windows.append({"fiscal_quarter": quarter, "source_identities": source_ids,
            "calendar_sha256": files[str(calendar_path)], **result})
    if any(sha(path) != digest for path, digest in files.items()):
        raise ValueError("source_diagnostics_input_changed")
    return {"schema_version": "equity-retained-source-diagnostics-v1", "scope": "READ_ONLY_EXISTING_TEN_WINDOWS",
        "sdk_version": "10.7.6708", "opend_build_identity": "NOT_BOUND_IN_QUOTE_RECEIPTS",
        "new_provider_requests": 0, "request_response_pairs_verified": len(responses),
        "original_bytes_unchanged": True, "input_file_sha256": files, "windows": windows,
        "target_price_series": "RAW_UNADJUSTED_DAILY_DERIVED_FROM_RETAINED_RTH_K60M",
        "crosscheck_price_series": "PROVIDER_K_DAY_RAW_UNADJUSTED",
        "revision_identity_limit": "Local hashes and retrieval times bind bytes; they are not provider revision identifiers.",
        "semantic_limit": "Matching request parameters and complete label grids do not prove identical provider trade inclusion rules.",
        "new_snapshot_admissions": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--collection-review", type=Path, required=True)
    parser.add_argument("--prepared-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.private_root.resolve()):
        parser.error("write diagnostics outside the original evidence root")
    result = diagnose(args.private_root, args.collection_review, args.prepared_inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"windows": len(result["windows"]), "differences": sum(len(row["differences"]) for row in result["windows"]),
        "new_requests": 0, "original_bytes_unchanged": True}))


if __name__ == "__main__":
    main()
