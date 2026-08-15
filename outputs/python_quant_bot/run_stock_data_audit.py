from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exchange_terminal import config
from exchange_terminal.market_data.stock_candles_io import (
    audit_stock_daily_sources,
    stock_data_revision_summary,
)


DEFAULT_SYMBOLS = [
    "SPY", "AAPL", "NVDA", "MSFT", "MU", "WDC", "AMZN",
    "GOOGL", "META", "AVGO", "TSLA", "AMD", "ASML", "TSM",
]


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit frozen stock daily data against an independent provider.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--limit", type=int, default=1600)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--output", default="")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = list(dict.fromkeys(
        item.strip().upper() for item in str(args.symbols or "").split(",") if item.strip()
    ))
    results: list[dict[str, Any]] = []
    for symbol in symbols:
        result: dict[str, Any] = {}
        for attempt in range(max(int(args.retries), 0) + 1):
            result = audit_stock_daily_sources(symbol, max(int(args.limit), 120))
            if result.get("status") != "BLOCK" or not result.get("secondary_error"):
                break
            if attempt < int(args.retries):
                time.sleep(0.75 * (attempt + 1))
        results.append(result)
        time.sleep(0.15)

    counts = {
        status: sum(1 for item in results if str(item.get("status") or "BLOCK") == status)
        for status in ("PASS", "REVIEW", "BLOCK")
    }
    status = "BLOCK" if counts["BLOCK"] else "REVIEW" if counts["REVIEW"] else "PASS"
    report = {
        "schema_version": "stock-data-audit-report-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "symbols": symbols,
        "counts": counts,
        "results": results,
        "ledger": stock_data_revision_summary(),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    report["report_hash"] = canonical_hash({key: value for key, value in report.items() if key != "created_at"})
    output = Path(args.output) if args.output else Path(config.RUNTIME_DIR) / "reports" / f"stock_data_audit_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": status,
        "counts": counts,
        "report_hash": report["report_hash"],
        "output": str(output),
        "live_order_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 2 if args.strict and status == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
