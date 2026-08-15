from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


OKX_BASE_URL = "https://www.okx.com"
DEFAULT_OUTPUT_DIR = r"Z:\jiaoyiguowangshuju"
DEFAULT_INST_ID = "BTC-USDT"
DEFAULT_START_DATE = "2013-01-01"
DEFAULT_BAR = "1Dutc"


@dataclass(frozen=True)
class Candle:
    symbol: str
    trading_date: str
    ts_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_ccy: float
    volume_quote: float
    confirmed: int
    source: str = "okx"


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def ms_to_date(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).date().isoformat()


def date_to_ms(value: date) -> int:
    return int(datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp() * 1000)


def fetch_okx_history_page(inst_id: str, bar: str, limit: int, after: int | None = None) -> list[list[str]]:
    params: dict[str, str | int] = {
        "instId": inst_id,
        "bar": bar,
        "limit": min(max(limit, 1), 300),
    }
    if after is not None:
        params["after"] = after
    url = f"{OKX_BASE_URL}/api/v5/market/history-candles?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "Python-Quant-Bot-History-Builder/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != "0":
        raise RuntimeError(f"OKX API error: {payload.get('code')} {payload.get('msg')}")
    return payload.get("data", [])


def row_to_candle(symbol: str, row: list[str]) -> Candle:
    ts_ms = int(row[0])
    return Candle(
        symbol=symbol,
        trading_date=ms_to_date(ts_ms),
        ts_ms=ts_ms,
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5] or 0),
        volume_ccy=float(row[6] or 0) if len(row) > 6 else 0.0,
        volume_quote=float(row[7] or 0) if len(row) > 7 else 0.0,
        confirmed=int(row[8] or 0) if len(row) > 8 else 0,
    )


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            symbol TEXT PRIMARY KEY,
            market TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS btc_daily_prices (
            symbol TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            ts_ms INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            volume_ccy REAL NOT NULL,
            volume_quote REAL NOT NULL,
            confirmed INTEGER NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (symbol, trading_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS download_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            rows_written INTEGER NOT NULL,
            pages_fetched INTEGER NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_btc_daily_prices_date ON btc_daily_prices (trading_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_btc_daily_prices_ts ON btc_daily_prices (ts_ms)")
    conn.commit()
    return conn


def upsert_candles(conn: sqlite3.Connection, candles: list[Candle]) -> int:
    now = utc_now_text()
    rows = [
        (
            candle.symbol,
            candle.trading_date,
            candle.ts_ms,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
            candle.volume_ccy,
            candle.volume_quote,
            candle.confirmed,
            candle.source,
            now,
            now,
        )
        for candle in candles
    ]
    conn.executemany("""
        INSERT INTO btc_daily_prices (
            symbol, trading_date, ts_ms, open, high, low, close,
            volume, volume_ccy, volume_quote, confirmed, source,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, trading_date) DO UPDATE SET
            ts_ms = excluded.ts_ms,
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            close = excluded.close,
            volume = excluded.volume,
            volume_ccy = excluded.volume_ccy,
            volume_quote = excluded.volume_quote,
            confirmed = excluded.confirmed,
            source = excluded.source,
            updated_at = excluded.updated_at
    """, rows)
    conn.commit()
    return len(rows)


def export_csv(conn: sqlite3.Connection, symbol: str, csv_path: Path) -> int:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = conn.execute("""
        SELECT trading_date, ts_ms, open, high, low, close, volume, volume_ccy, volume_quote, confirmed, source
        FROM btc_daily_prices
        WHERE symbol = ?
        ORDER BY trading_date ASC
    """, (symbol,))
    rows = cursor.fetchall()
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "ts_ms", "open", "high", "low", "close", "volume", "volume_ccy", "volume_quote", "confirmed", "source"])
        writer.writerows(rows)
    return len(rows)


def summarize(conn: sqlite3.Connection, symbol: str) -> dict:
    cursor = conn.execute("""
        SELECT COUNT(*), MIN(trading_date), MAX(trading_date), MIN(close), MAX(close)
        FROM btc_daily_prices
        WHERE symbol = ?
    """, (symbol,))
    count, min_date, max_date, min_close, max_close = cursor.fetchone()
    return {
        "symbol": symbol,
        "rows": count or 0,
        "first_date": min_date,
        "last_date": max_date,
        "min_close": min_close,
        "max_close": max_close,
    }


def record_run(conn: sqlite3.Connection, symbol: str, start_date: str, end_date: str, rows: int, pages: int, status: str, message: str) -> None:
    conn.execute("""
        INSERT INTO download_runs (symbol, start_date, end_date, rows_written, pages_fetched, status, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol, start_date, end_date, rows, pages, status, message, utc_now_text()))
    conn.commit()


def build_database(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output_dir)
    db_path = output_dir / args.database_name
    csv_path = output_dir / args.csv_name
    start = parse_date(args.start_date)
    end = parse_date(args.end_date) if args.end_date else datetime.now(UTC).date()
    if start > end:
        raise ValueError("start_date must be earlier than end_date")

    conn = connect_database(db_path)
    conn.execute(
        "INSERT OR IGNORE INTO symbols (symbol, market, source, created_at) VALUES (?, ?, ?, ?)",
        (args.inst_id, "crypto", "okx", utc_now_text()),
    )
    conn.commit()

    if args.init_only:
        exported = export_csv(conn, args.inst_id, csv_path)
        message = f"initialized only; database={db_path}; csv={csv_path}; csv_rows={exported}"
        record_run(conn, args.inst_id, start.isoformat(), end.isoformat(), 0, 0, "initialized", message)
        result = summarize(conn, args.inst_id)
        result.update({
            "database": str(db_path),
            "csv": str(csv_path),
            "rows_written_this_run": 0,
            "pages_fetched": 0,
            "status": "initialized",
        })
        conn.close()
        return result

    rows_written = 0
    pages_fetched = 0
    after = date_to_ms(end + timedelta(days=1))
    oldest_seen: int | None = None
    start_ms = date_to_ms(start)

    try:
        while True:
            page = fetch_okx_history_page(args.inst_id, args.bar, args.limit, after=after)
            pages_fetched += 1
            if not page:
                break

            candles = [row_to_candle(args.inst_id, row) for row in page]
            filtered = [
                candle for candle in candles
                if start.isoformat() <= candle.trading_date <= end.isoformat()
            ]
            if filtered:
                rows_written += upsert_candles(conn, filtered)

            page_oldest = min(candle.ts_ms for candle in candles)
            if oldest_seen is not None and page_oldest >= oldest_seen:
                break
            oldest_seen = page_oldest
            if page_oldest < start_ms:
                break
            if args.max_pages and pages_fetched >= args.max_pages:
                break
            after = page_oldest
            time.sleep(max(args.sleep_seconds, 0))

        exported = export_csv(conn, args.inst_id, csv_path)
        message = f"database={db_path}; csv={csv_path}; csv_rows={exported}"
        record_run(conn, args.inst_id, start.isoformat(), end.isoformat(), rows_written, pages_fetched, "success", message)
        result = summarize(conn, args.inst_id)
        result.update({
            "database": str(db_path),
            "csv": str(csv_path),
            "rows_written_this_run": rows_written,
            "pages_fetched": pages_fetched,
            "status": "success",
        })
        return result
    except Exception as exc:
        record_run(conn, args.inst_id, start.isoformat(), end.isoformat(), rows_written, pages_fetched, "failed", str(exc))
        raise
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a BTC daily price SQLite database from OKX daily candles.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--database-name", default="btc_daily_prices.sqlite")
    parser.add_argument("--csv-name", default="btc_daily_prices.csv")
    parser.add_argument("--inst-id", default=DEFAULT_INST_ID)
    parser.add_argument("--bar", default=DEFAULT_BAR)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default="")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--init-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    result = build_database(parse_args())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
