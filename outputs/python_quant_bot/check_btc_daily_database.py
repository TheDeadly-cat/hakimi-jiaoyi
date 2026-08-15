from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
from pathlib import Path


DEFAULT_OUTPUT_DIR = r"Z:\jiaoyiguowangshuju"


def inspect_sqlite(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path.absolute().as_uri() + "?mode=ro", uri=True)
    try:
        row = conn.execute("""
            SELECT COUNT(*), MIN(trading_date), MAX(trading_date), MIN(close), MAX(close)
            FROM btc_daily_prices
        """).fetchone()
        latest = conn.execute("""
            SELECT trading_date, open, high, low, close, volume, confirmed
            FROM btc_daily_prices
            ORDER BY trading_date DESC
            LIMIT 5
        """).fetchall()
        return {
            "database": str(db_path),
            "rows": row[0],
            "first_date": row[1],
            "last_date": row[2],
            "min_close": row[3],
            "max_close": row[4],
            "latest_rows": latest,
        }
    finally:
        conn.close()


def inspect_sqlite_with_cache(db_path: Path) -> dict:
    try:
        result = inspect_sqlite(db_path)
        result["access"] = "direct_readonly"
        return result
    except Exception as exc:
        cache_dir = Path(__file__).resolve().parent / "runtime"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "btc_daily_prices_check.sqlite"
        shutil.copyfile(db_path, cache_path)
        result = inspect_sqlite(cache_path)
        result["database"] = str(db_path)
        result["cache_path"] = str(cache_path)
        result["access"] = "copied_for_inspection"
        result["warning"] = f"direct open failed: {exc}"
        return result


def inspect_csv(csv_path: Path) -> dict:
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    first = rows[0] if rows else {}
    last = rows[-1] if rows else {}
    return {
        "csv": str(csv_path),
        "rows": len(rows),
        "first_date": first.get("date"),
        "first_close": first.get("close"),
        "last_date": last.get("date"),
        "last_close": last.get("close"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect BTC daily price database and CSV files.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    db_path = output_dir / "btc_daily_prices.sqlite"
    csv_path = output_dir / "btc_daily_prices.csv"
    result = {"output_dir": str(output_dir)}

    if db_path.exists():
        try:
            result["sqlite"] = inspect_sqlite_with_cache(db_path)
        except Exception as exc:
            result["sqlite_error"] = str(exc)
    else:
        result["sqlite_error"] = "database file not found"

    if csv_path.exists():
        try:
            result["csv"] = inspect_csv(csv_path)
        except Exception as exc:
            result["csv_error"] = str(exc)
    else:
        result["csv_error"] = "csv file not found"

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
