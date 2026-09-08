"""Build explicit synthetic canonical inputs for 5k/20k full-pipeline profiles."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from hakimi_research.dataset_registry import import_capture, save_snapshot, utc_text
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.experiment import ExperimentSpec
from hakimi_research.reporting import save_json_report


def deny_network(event, _args):
    if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
        raise RuntimeError("synthetic_profile_network_access_denied")


def capture_document(count):
    if type(count) is not int or not 73 <= count <= 20000:
        raise ValueError("synthetic_profile_rows_must_be_integer_between_73_and_20000")
    # Same NumPy expression and numeric construction as profile_research_core.py.
    steps = np.arange(count, dtype=float)
    close = 100 + 3 * np.sin(steps / 30) + 0.002 * steps
    opening = np.roll(close, 1)
    opening[0] = close[0]
    high, low = np.maximum(opening, close) + 0.25, np.minimum(opening, close) - 0.25
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    end = start + pd.Timedelta(hours=count)
    rows = [[str(int((start + pd.Timedelta(hours=i)).timestamp() * 1000)),
             *[str(float(value)) for value in (opening[i], high[i], low[i], close[i])],
             "1000.0", str(float(1000 * close[i])), str(float(1000 * close[i])), "1"] for i in range(count)]
    descending = rows[::-1]
    pages = []
    cursor = int(end.timestamp() * 1000)
    for offset in range(0, count, 300):
        batch = descending[offset:offset + 300]
        raw = canonical_bytes({"code": "0", "msg": "", "data": batch})
        pages.append({"raw_base64": base64.b64encode(raw).decode("ascii"),
                      "origin": "https://www.okx.com", "endpoint": "/api/v5/market/history-candles",
                      "params": {"instId": "BTC-USDT", "bar": "1H", "limit": 300, "after": cursor},
                      "retrieved_at": utc_text(end + pd.Timedelta(hours=24))})
        cursor = int(batch[-1][0])
    return {"schema_version": "okx-public-capture-v1", "start": utc_text(start),
            "end_exclusive": utc_text(end), "as_of": utc_text(end),
            "evidence_kind": "SYNTHETIC_TEST", "pages": pages}


def build(count, output):
    capture = capture_document(count)
    capture_path = Path(save_json_report(capture, output / "captures", "synthetic_capture", artifact_id=digest(capture)))
    snapshot = import_capture(capture_path)
    if snapshot.document["evidence_kind"] != "SYNTHETIC_TEST":
        raise ValueError("synthetic_evidence_label_required")
    snapshot_path = save_snapshot(snapshot, output / "datasets")
    spec = ExperimentSpec.from_document({"schema_version": "research-experiment-spec-v1",
        "name": f"synthetic-pipeline-profile-{count}-rows", "snapshot_id": snapshot.snapshot_id,
        "strategy": {"name": "dual_ma", "params": {"fast_window": 20, "slow_window": 60,
            "position_pct": 0.25, "stop_loss_pct": 0.03, "take_profit_pct": 0.08}},
        "score_start": "2024-01-04T00:00:00Z", "score_end": capture["end_exclusive"],
        "initial_cash": 10000, "fee_rate": 0.0008, "slippage_pct": 0.0005,
        "risk": {"max_position_pct": 0.35, "max_single_loss_pct": 0.03, "max_daily_loss_pct": 0.05,
                 "max_leverage": 1, "min_cash_pct": 0.05},
        "end_policy": "MARK_TO_MARKET", "purpose": "SYNTHETIC_REGRESSION",
        "execution_policy": "STANDARD_STRATEGY_RISK"})
    spec_path = Path(save_json_report(spec.document, output / "specs", "spec", artifact_id=digest(spec.document)))
    receipt = {"schema_version": "synthetic-pipeline-fixture-v1", "rows": count, "context_rows": 72,
               "scored_rows": count - 72, "evidence_kind": "SYNTHETIC_TEST",
               "formula": "close=100+3*sin(arange(rows)/30)+0.002*arange(rows); open=previous_close (first=open=close); high=max(open,close)+0.25; low=min(open,close)-0.25; base_volume=1000",
               "snapshot_id": snapshot.snapshot_id, "data_hash": snapshot.document["data_hash"],
               "spec_hash": digest(spec.document), "capture_file_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
               "snapshot_file_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
               "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "market_effectiveness_assessed": False, "provider_network_calls": 0,
               "research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
    receipt_path = save_json_report(receipt, output, "synthetic_fixture", artifact_id=digest(receipt))
    return {"capture": str(capture_path), "snapshot": str(snapshot_path), "spec": str(spec_path), "receipt": receipt_path}


if __name__ == "__main__":
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, choices=(5000, 20000), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.rows, args.output_dir), ensure_ascii=False))
