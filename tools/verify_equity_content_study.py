"""Independent retained C/D review: stdlib only, no strategy/backtest imports."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def verify(study_root, packet_path, originals, output):
    module_path = Path(__file__).resolve().parents[1] / "scripts/reconcile_research_ledger.py"
    spec = importlib.util.spec_from_file_location("standalone_decimal_ledger", module_path)
    ledger = importlib.util.module_from_spec(spec); spec.loader.exec_module(ledger)
    study = read(study_root / "study.private.json")
    if study["study_hash"] != digest({k: v for k, v in study.items() if k != "study_hash"}):
        raise ValueError("independent_study_hash_mismatch")
    packet = read(packet_path)
    if study["packet_hash"] != packet["packet_hash"] or packet["packet_hash"] != digest({k: v for k, v in packet.items() if k != "packet_hash"}):
        raise ValueError("independent_packet_hash_mismatch")
    sources = read(study_root / "inputs-before.private.json")
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha for path, sha in sources.items()):
        raise ValueError("independent_original_bytes_changed")
    snapshots = {}
    for phase in ("actual-study-first", "actual-study-final"):
        for path in (originals / phase).rglob("equity_dataset_*.json"):
            snapshots[path.stem.removeprefix("equity_dataset_")] = path
    rows, reports, checks, maximum = [], [], 0, Decimal(0)
    for cell in study["cells"]:
        candidate = next(c for c in packet["events"] if c["fiscal_quarter"] == cell["fiscal_quarter"])
        snapshot_path = snapshots[cell["snapshot_id"]]
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"), parse_float=Decimal)
        sessions = snapshot["sessions"]
        release = stamp(candidate["first_public_at"])
        previous = max(i for i, s in enumerate(sessions) if stamp(s["close_utc"]) <= release)
        confirmation = next(i for i, s in enumerate(sessions) if stamp(s["open_utc"]) >= release + timedelta(seconds=120))
        decision = stamp(sessions[confirmation]["close_utc"]) + timedelta(seconds=60)
        next_session = next(s for s in sessions if stamp(s["open_utc"]) > decision)
        c_buy = (Decimal(str(snapshot["candles"][confirmation][4])) > Decimal(str(snapshot["candles"][previous][4]))
                 and cell["score_start"] <= next_session["date"] <= cell["score_end"])
        facts = {f["name"]: f for f in candidate["facts"]}
        def amount(name):
            return Decimal(facts[name]["value"]) * Decimal(facts[name]["scale"])
        content_positive = amount("next_revenue_guidance_midpoint") > amount("actual_revenue")
        checked_pair = {}
        for variant, expected_buy in (("C", c_buy), ("D", c_buy and content_positive)):
            path = study_root / cell["fiscal_quarter"] / ("cost-" + str(cell["cost_multiplier"])) / variant / (
                "content_research_" + cell["report_hashes"][variant] + ".json")
            data = read(path)
            if data["report_hash"] != cell["report_hashes"][variant] or data["report_hash"] != digest({k: v for k, v in data.items() if k != "report_hash"}):
                raise ValueError("independent_report_hash_mismatch")
            report = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
            buy_fills = [f for f in report["result"]["fills"] if f["action"] == "BUY"]
            buy_signals = [s for s in report["result"]["signals"] if s["action"] == "BUY"]
            if len(buy_fills) != int(expected_buy) or len(buy_signals) != int(expected_buy):
                raise ValueError("independent_expected_entry_mismatch")
            if expected_buy and (stamp(buy_fills[0]["fill_time"]) != stamp(next_session["open_utc"])
                    or stamp(buy_signals[0]["time"]) != decision):
                raise ValueError("independent_entry_clock_mismatch")
            receipt = ledger.reconcile(report, snapshot)
            if receipt["status"] != "PASS":
                raise ValueError("independent_recorded_ledger_failed")
            checks += receipt["checks"] + 4
            maximum = max(maximum, Decimal(receipt["maximum_absolute_numeric_error"]))
            for key, value in cell["metrics"][variant].items():
                if data["result"][key] != value:
                    raise ValueError("independent_public_metrics_projection_mismatch")
            reports.append(receipt)
            checked_pair[variant] = data["result"]
        if not cell["content_changed_entry"]:
            for field in ("fills", "orders", "signals", "equity_curve", "return_series"):
                if checked_pair["C"][field] != checked_pair["D"][field]:
                    raise ValueError("independent_same_decision_unequal_economic_path")
        rows.append({"fiscal_quarter": cell["fiscal_quarter"], "cost_multiplier": cell["cost_multiplier"],
                     "price_condition": c_buy, "guidance_condition": content_positive,
                     "content_changed_entry": c_buy and not content_positive})
    result = {"schema_version": "independent-content-study-review-v1", "study_hash": study["study_hash"],
        "status": "PASS", "reports": len(reports), "checks": checks, "maximum_absolute_numeric_error": str(maximum),
        "decision_rows": rows, "original_files_unchanged": len(sources), "new_backtests": 0,
        "new_external_requests": 0, "numerical_engine_imported": False,
        "reviewer_kind": "SEPARATE_STDLIB_IMPLEMENTATION_NOT_ANOTHER_HUMAN_ATTESTATION",
        "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ledger_script_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest()}
    result["review_hash"] = digest(result)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("study-root", "packet", "original-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.study_root, args.packet, args.original_root, args.output)
    print(json.dumps({k: result[k] for k in ("status", "reports", "checks", "maximum_absolute_numeric_error", "review_hash")}, indent=2))
