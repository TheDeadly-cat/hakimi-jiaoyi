"""Read retained C/D paths at frozen 1/3/5-session horizons; no backtests or I/O APIs."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.equity_content_protocol import digest, validate_approval

PROTOCOL_HASH = "39d044de7ab10913f3d46582ebc6e556b149971343b62ff38cf97832c28844bf"
HORIZONS = (1, 3, 5)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def number(value):
    result = Decimal(str(value))
    if type(value) is bool or not result.is_finite():
        raise ValueError("path_finite_number_required")
    return result


def sealed(value, field, hash_function=digest):
    if value[field] != hash_function({k: v for k, v in value.items() if k != field}):
        raise ValueError("path_input_identity_mismatch:" + field)


def paths(snapshot, report):
    """Valuation of recorded entry inventory; never create hypothetical fills."""
    with localcontext() as context:
        context.prec = 40
        return _paths(snapshot, report)


def _paths(snapshot, report):
    buys = [f for f in report["result"]["fills"] if f["action"] == "BUY"]
    if len(buys) > 1:
        raise ValueError("path_one_C_entry_required")
    if not buys:
        return {"status": "NO_RECORDED_ENTRY", "horizons": [{"sessions": n, "status": "NO_ENTRY", "values": None} for n in HORIZONS]}
    buy = buys[0]
    sells = [f for f in report["result"]["fills"] if f["action"] == "SELL"]
    if len(sells) > 1:
        raise ValueError("path_single_retained_exit_required")
    sessions, candles = snapshot["sessions"], snapshot["candles"]
    entry = next(i for i, s in enumerate(sessions) if stamp(s["open_utc"]) == stamp(buy["fill_time"]))
    if (stamp(buy["signal_time"]) >= stamp(buy["fill_time"])
            or not report["spec"]["score_start_session"] <= sessions[entry]["date"] <= report["spec"]["score_end_session"]):
        raise ValueError("path_entry_clock_or_score_mismatch")
    reference = number(candles[entry][1])
    if reference <= 0:
        raise ValueError("path_positive_entry_reference_required")
    initial = number(report["spec"]["initial_cash"])
    quantity, cash = number(buy["quantity"]), number(buy["cash_after"])
    sold_at = stamp(sells[0]["fill_time"]) if sells else None
    exit_index = next((i for i, s in enumerate(sessions) if stamp(s["open_utc"]) == sold_at), None)
    if sells and (exit_index is None or exit_index < entry):
        raise ValueError("path_exit_session_invalid")
    horizon_rows = []
    for n in HORIZONS:
        end = entry + n - 1
        if end >= len(sessions) or sessions[end]["date"] > report["spec"]["score_end_session"]:
            horizon_rows.append({"sessions": n, "status": "MISSING_OR_OUTSIDE_ORIGINAL_SCORE", "values": None})
            continue
        rows = candles[entry:end + 1]
        close = number(rows[-1][4])
        later = candles[exit_index + 1:end + 1] if exit_index is not None and end > exit_index else []
        values = {"close_price_change": str(close / reference - 1),
            "full_horizon_high_change": str(max(number(r[2]) for r in rows) / reference - 1),
            "full_horizon_low_change": str(min(number(r[3]) for r in rows) / reference - 1),
            "retained_entry_mark_return": str((cash + quantity * close) / initial - 1),
            "recorded_original_score_return": str(number(report["result"]["total_return"])),
            "post_exit_full_session_high_change": str(max(number(r[2]) for r in later) / reference - 1) if later else None,
            "post_exit_full_session_low_change": str(min(number(r[3]) for r in later) / reference - 1) if later else None}
        horizon_rows.append({"sessions": n, "status": "OBSERVED_RETAINED_PATH", "close_session": sessions[end]["date"],
            "values": values, "source_rows": {"snapshot_id": snapshot["snapshot_id"], "entry_candle_index": entry,
                "last_candle_index": end, "post_exit_first_index": exit_index + 1 if later else None,
                "reference_price_field": "candles[entry][1]", "mark_price_field": "candles[last][4]",
                "report_hash": report["report_hash"], "retained_buy_fill_index": report["result"]["fills"].index(buy)},
            "intrabar_extrema_order": "UNKNOWN", "post_exit_same_day_remainder": "UNKNOWN",
            "valuation_kind": "RETAINED_ENTRY_MARK_ONLY_NOT_A_NO_STOP_BACKTEST_OR_EXECUTABLE_EXIT"})
    return {"status": "RECORDED_ENTRY", "entry_session": sessions[entry]["date"],
        "signal_available_at": buy["signal_time"], "entry_at": buy["fill_time"],
        "exit_session": sessions[exit_index]["date"] if exit_index is not None else None,
        "exit_basis": sells[0]["fill_basis"] if sells else "OPEN_AT_END",
        "entry_fee": str(number(buy["fee"])), "exit_fee": str(sum((number(f["fee"]) for f in sells), Decimal(0))),
        "recorded_realized_pnl": str(number(report["result"]["realized_pnl"])),
        "recorded_close_exposure_ratio": str(number(report["result"]["exposure_ratio"])),
        "intraday_exposure_not_zero": True, "holding_time_exact": None, "horizons": horizon_rows}


def condition_view(snapshot, candidate):
    sessions, candles = snapshot["sessions"], snapshot["candles"]
    release = stamp(candidate["first_public_at"])
    available = release + timedelta(seconds=120)
    previous = max(i for i, s in enumerate(sessions) if stamp(s["close_utc"]) <= release)
    confirmation = next(i for i, s in enumerate(sessions) if stamp(s["open_utc"]) >= available)
    change = number(candles[confirmation][4]) / number(candles[previous][4]) - 1
    return {"price_condition": change > 0, "confirmation_close_change": str(change),
        "confirmation_session": sessions[confirmation]["date"],
        "confirmation_available_at": (stamp(sessions[confirmation]["close_utc"]) + timedelta(seconds=60)).isoformat(),
        "source_rows": {"snapshot_id": snapshot["snapshot_id"], "pre_release_candle_index": previous,
                        "confirmation_candle_index": confirmation}}


def produce(args):
    # Validation only; this module never imports or runs the backtest engine.
    from hakimi_research.equity_dataset import verify_equity_snapshot
    from hakimi_research.documents import digest as canonical_digest
    for original in (args.study_root, args.original_root, args.packet.parent):
        if args.output.resolve().is_relative_to(original.resolve()):
            raise ValueError("path_output_must_be_separate_from_originals")
    before = {}
    def tracked_read(path):
        raw = Path(path).read_bytes(); identity = str(Path(path).resolve())
        current = hashlib.sha256(raw).hexdigest()
        if identity in before and before[identity] != current:
            raise ValueError("path_input_changed_during_read")
        before[identity] = current
        return json.loads(raw)
    protocol, study = tracked_read(args.protocol), tracked_read(args.study_root / "study.private.json")
    sealed(protocol, "protocol_hash"); sealed(study, "study_hash", canonical_digest)
    if protocol["protocol_hash"] != PROTOCOL_HASH or study["study_hash"] != protocol["source_study_hash"]:
        raise ValueError("path_frozen_protocol_or_study_changed")
    packet, approval = tracked_read(args.packet), tracked_read(args.approval)
    # Existing core reports use ASCII-escaped canonical JSON; review packets
    # have their own UTF-8 convention. Preserve both receipt identities.
    if packet["packet_hash"] != protocol["source_packet_hash"] or canonical_digest(approval) != study["approval_hash"]:
        raise ValueError("path_approval_binding_changed")
    approved = validate_approval(packet, approval)
    if len(approved) != 10:
        raise ValueError("path_original_ten_field_approvals_required")
    snapshots = {}
    for phase in ("actual-study-first", "actual-study-final"):
        for path in (args.original_root / phase).rglob("equity_dataset_*.json"):
            snapshots[path.stem.removeprefix("equity_dataset_")] = path
    events = []
    for candidate in packet["events"]:
        sealed(candidate, "candidate_hash")
        quarter = candidate["fiscal_quarter"]
        facts = {f["name"]: f for f in candidate["facts"]}
        above = number(facts["next_revenue_guidance_midpoint"]["value"]) * number(facts["next_revenue_guidance_midpoint"]["scale"]) > number(facts["actual_revenue"]["value"]) * number(facts["actual_revenue"]["scale"])
        event = {"fiscal_quarter": quarter, "event_id": candidate["event_id"], "candidate_hash": candidate["candidate_hash"],
            "source_url": candidate["source_url"], "raw_source_sha256": candidate["raw_sha256"],
            "facts": [{k: f[k] for k in ("name", "value", "scale", "unit", "currency", "fiscal_period", "basis", "precision")} for f in candidate["facts"]],
            "field_review": "APPROVED_LISTED_FIELDS_IN_2026", "first_public_at": candidate["first_public_at"],
            "model_event_available_at": (stamp(candidate["first_public_at"]) + timedelta(seconds=120)).isoformat(),
            "actual_retrieved_at": candidate["retrieved_at"], "actual_extraction_completed_at": candidate["extraction_completed_at"],
            "content_condition": above, "cost_cases": []}
        cells = [c for c in study["cells"] if c["fiscal_quarter"] == quarter]
        if not cells:
            exclusion = next(e for e in study["excluded_events"] if e["fiscal_quarter"] == quarter)
            event.update(status="DATA_EXCLUDED", exclusion=exclusion, price_condition=None, horizons=None)
            events.append(event); continue
        for cell in cells:
            snapshot_path = snapshots[cell["snapshot_id"]]
            snapshot = verify_equity_snapshot(tracked_read(snapshot_path))
            pair = {}
            for variant in ("C", "D"):
                path = args.study_root / quarter / ("cost-" + str(cell["cost_multiplier"])) / variant / ("content_research_" + cell["report_hashes"][variant] + ".json")
                report = tracked_read(path); sealed(report, "report_hash", canonical_digest)
                if (report["report_hash"] != cell["report_hashes"][variant] or report["result_hash"] != canonical_digest(report["result"])
                        or report["dataset"]["snapshot_id"] != snapshot["snapshot_id"] or report["dataset"]["data_hash"] != snapshot["data_hash"]):
                    raise ValueError("path_report_snapshot_identity_mismatch")
                pair[variant] = report
            event.update(condition_view(snapshot, candidate))
            c_buy, d_buy = (any(f["action"] == "BUY" for f in pair[v]["result"]["fills"]) for v in ("C", "D"))
            stopped = any(f["action"] == "SELL" and f["fill_basis"] in {"INTRABAR_STOP", "GAP_OPEN"} for f in pair["C"]["result"]["fills"])
            event["status"] = ("CONTENT_VETO" if c_buy and not d_buy else
                ("ENTERED_STOPPED" if stopped else "ENTERED_MARKED") if c_buy else "NO_PRICE_SIGNAL")
            event["content_changed_decision"] = c_buy != d_buy
            event["cost_cases"].append({"cost_multiplier": cell["cost_multiplier"], "fee_rate": pair["C"]["spec"]["fee_rate"],
                "slippage_pct": pair["C"]["spec"]["slippage_pct"], "report_hashes": cell["report_hashes"],
                "C_return": pair["C"]["result"]["total_return"], "D_return": pair["D"]["result"]["total_return"],
                "disabled_D_byte_identical_C": cell["disabled_D_byte_identical_C"], "C_path": paths(snapshot, pair["C"])})
        events.append(event)
    if len(events) != 10 or sum(e["status"] == "DATA_EXCLUDED" for e in events) != 3:
        raise ValueError("path_fixed_coverage_changed")
    result = {"schema_version": "equity-fixed-path-diagnosis-v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_hash": PROTOCOL_HASH, "source_study_hash": study["study_hash"], "approval_hash": study["approval_hash"],
        "events": events, "new_backtests": 0, "new_market_requests": 0, "order_allowed": False,
        "input_files_unchanged": len(before), "tool_sha256": sha(Path(__file__)),
        "limits": ["Already-seen AMD development events; no independent population or unseen validation.",
            "Horizon marks retain entry costs but omit hypothetical exit costs; no hypothetical fills or no-stop strategy replay.",
            "Daily highs/lows have unknown intrabar order; post-exit extrema exclude the entire exit session.",
            "Current HTML, 2026 human review and assumed historical latency are distinct evidence."]}
    result["diagnosis_hash"] = digest(result)
    if any(sha(p) != h for p, h in before.items()):
        raise ValueError("path_input_changed_during_read")
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in (("path-results.json", result), ("input-files.private.json", before)):
        with (args.output / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "study-root", "packet", "approval", "original-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    def offline(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.gethostbyname"}:
            raise RuntimeError("path_diagnostics_network_forbidden")
    sys.addaudithook(offline)
    result = produce(parser.parse_args())
    print(json.dumps({"diagnosis_hash": result["diagnosis_hash"], "events": len(result["events"]),
                      "new_backtests": 0, "new_market_requests": 0}, indent=2))
