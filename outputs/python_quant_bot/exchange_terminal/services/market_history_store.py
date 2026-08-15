from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable

try:
    from market_data.candle_contract import explicit_boolean
except ModuleNotFoundError:
    from exchange_terminal.market_data.candle_contract import explicit_boolean


MARKET_HISTORY_STORE_VERSION = "market-history-store-v2"
MARKET_HISTORY_MANIFEST_VERSION = "market-history-manifest-v1"
MARKET_HISTORY_DATASET_EVIDENCE_VERSION = "market-history-dataset-evidence-v1"
_MARKET_HISTORY_WRITE_LOCK = threading.RLock()


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _timestamp_ms(value: Any) -> int:
    number = _finite_number(value)
    if number is None or number <= 0:
        return 0
    result = int(number)
    return result * 1000 if result < 10_000_000_000 else result


def _utc_date(ts_ms: int) -> str:
    if ts_ms <= 0:
        return ""
    try:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return ""


def _completion_contract(row: dict[str, Any], default_complete: bool) -> tuple[bool, bool, bool]:
    for field in ("complete", "confirm", "confirmed"):
        if field in row:
            parsed = explicit_boolean(row.get(field))
            return parsed is True, parsed is not None, parsed is not None
    if "provisional" in row:
        parsed = explicit_boolean(row.get("provisional"))
        return parsed is False, parsed is not None, parsed is not None
    return default_complete is True, False, True


def _semantic_candle(row: dict[str, Any], *, include_source: bool = True) -> dict[str, Any]:
    payload = {
        "date": str(row.get("date") or ""),
        "ts_ms": int(row.get("ts_ms") or 0),
        "open": float(row.get("open") or 0),
        "high": float(row.get("high") or 0),
        "low": float(row.get("low") or 0),
        "close": float(row.get("close") or 0),
        "volume": float(row.get("volume") or 0),
        "complete": bool(row.get("complete") is True or row.get("complete") == 1),
    }
    if include_source:
        payload["source"] = str(row.get("source") or "")
    return payload


def normalize_history_candle(
    row: Any,
    *,
    source: str = "",
    default_complete: bool = False,
    require_utc_date: bool = False,
) -> dict[str, Any] | None:
    if isinstance(row, (list, tuple)):
        if len(row) < 5:
            return None
        raw = {
            "ts_ms": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5] if len(row) > 5 else 0,
        }
        if len(row) > 8:
            raw["confirm"] = row[8]
        source_name = str(source or "okx")
    elif isinstance(row, dict):
        raw = dict(row)
        source_name = str(source or raw.get("source") or raw.get("origin_source") or "")
    else:
        return None

    ts_ms = 0
    for field in ("ts_ms", "ts", "time"):
        if raw.get(field) not in (None, ""):
            ts_ms = _timestamp_ms(raw.get(field))
            break
    if ts_ms <= 0:
        return None

    close = _finite_number(raw.get("close"))
    open_price = _finite_number(raw.get("open"))
    high = _finite_number(raw.get("high"))
    low = _finite_number(raw.get("low"))
    volume = _finite_number(raw.get("volume", raw.get("volume_quote", raw.get("vol", 0))))
    if any(value is None for value in (open_price, high, low, close, volume)):
        return None
    assert open_price is not None and high is not None and low is not None and close is not None and volume is not None
    if min(open_price, high, low, close) <= 0 or volume < 0:
        return None
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        return None

    complete, complete_attested, completion_valid = _completion_contract(raw, default_complete)
    if not completion_valid:
        return None
    computed_date = _utc_date(ts_ms)
    supplied_date = str(raw.get("date") or raw.get("trading_date") or "").strip()
    date = supplied_date or computed_date
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None
    if require_utc_date and date != computed_date:
        return None

    payload = {
        "date": date,
        "ts_ms": ts_ms,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "complete": complete,
        "complete_attested": complete_attested,
        "source": source_name,
    }
    payload["row_hash"] = canonical_hash(_semantic_candle(payload))
    return payload


def build_history_dataset_evidence(
    *,
    symbol: str,
    rows: list[Any],
    source: str,
    dataset_lineage_id: str = "",
    cache_manifest: dict[str, Any] | None = None,
    cache_admitted: bool = False,
) -> dict[str, Any]:
    clean_symbol = str(symbol or "").strip().upper()
    clean_source = str(source or "").strip()
    clean_lineage_id = str(dataset_lineage_id or "").strip()
    blockers: list[str] = []
    normalized_rows: list[dict[str, Any]] = []
    invalid_count = 0
    for row in rows or []:
        row_source = (
            str(row.get("source") or row.get("origin_source") or clean_source)
            if isinstance(row, dict)
            else clean_source
        )
        normalized = normalize_history_candle(
            row,
            source=row_source,
            default_complete=False,
            require_utc_date=True,
        )
        if not normalized:
            invalid_count += 1
            continue
        if normalized["complete"]:
            normalized_rows.append(normalized)

    normalized_rows.sort(key=lambda item: int(item["ts_ms"]))
    dates = [str(item["date"]) for item in normalized_rows]
    timestamps = [int(item["ts_ms"]) for item in normalized_rows]
    if not clean_symbol:
        blockers.append("market_history_symbol_missing")
    if not clean_source:
        blockers.append("market_history_source_missing")
    if invalid_count:
        blockers.append(f"market_history_invalid_rows:{invalid_count}")
    if not normalized_rows:
        blockers.append("market_history_completed_rows_missing")
    if len(set(dates)) != len(dates) or len(set(timestamps)) != len(timestamps):
        blockers.append("market_history_duplicate_rows")
    if len(clean_lineage_id) > 160:
        blockers.append("market_history_lineage_id_invalid")

    cache = dict(cache_manifest) if isinstance(cache_manifest, dict) else {}
    if cache_admitted and str(cache.get("status") or "MISSING") == "BLOCK":
        blockers.append("blocked_market_history_cache_admitted")

    semantic_rows = [_semantic_candle(item) for item in normalized_rows]
    data_hash = canonical_hash(semantic_rows)
    lineage_hash = canonical_hash({
        "dataset_lineage_id": clean_lineage_id,
        "symbol": clean_symbol,
        "source": clean_source,
        "data_hash": data_hash,
    }) if clean_lineage_id else ""
    status = "BLOCK" if blockers else "PASS" if clean_lineage_id else "REVIEW"
    evidence = {
        "schema_version": MARKET_HISTORY_DATASET_EVIDENCE_VERSION,
        "status": status,
        "classification": (
            "FROZEN_DATASET"
            if status == "PASS"
            else "DATASET_INVALID"
            if status == "BLOCK"
            else "INTERACTIVE_DATASET_NOT_FROZEN"
        ),
        "symbol": clean_symbol,
        "source": clean_source,
        "dataset_lineage_id": clean_lineage_id,
        "lineage_hash": lineage_hash,
        "row_count": len(normalized_rows),
        "first": dates[0] if dates else "",
        "last": dates[-1] if dates else "",
        "data_hash": data_hash,
        "invalid_count": invalid_count,
        "cache_admitted": cache_admitted is True,
        "cache_manifest": {
            key: cache.get(key)
            for key in (
                "schema_version",
                "status",
                "symbol",
                "row_count",
                "complete_count",
                "incomplete_count",
                "invalid_count",
                "first",
                "last",
                "sources",
                "data_hash",
            )
            if key in cache
        },
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": [] if clean_lineage_id else ["dataset_lineage_id_required_for_immutable_freeze"],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    evidence["evidence_hash"] = canonical_hash(evidence)
    return evidence


def source_priority(source: str) -> int:
    text = str(source or "").strip().lower()
    if "okx_history" in text:
        return 50
    if "okx_market" in text or text == "okx":
        return 45
    if "binance" in text:
        return 30
    if "local" in text or "csv" in text:
        return 20
    return 10 if text else 0


def fetch_okx_daily_history_pages(
    reader: Callable[[str, dict[str, str]], tuple[list[Any], str]],
    symbol: str,
    limit: int,
) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    clean_symbol = str(symbol or "").strip().upper()
    clean_limit = max(1, min(int(limit), 6_000))
    page_limit = min(max(clean_limit, 100), 300)
    maximum_pages = max(1, min(24, math.ceil(clean_limit / page_limit) + 2))
    after = ""
    selected_source = ""
    attempts: list[dict[str, Any]] = []
    rows_by_ts: dict[int, dict[str, Any]] = {}

    for page_index in range(maximum_pages):
        page: list[Any] = []
        page_source = ""
        for path, source_name in (
            ("/api/v5/market/history-candles", "okx_history_candles"),
            ("/api/v5/market/candles", "okx_market_candles"),
        ):
            query = {"instId": clean_symbol, "bar": "1Dutc", "limit": str(page_limit)}
            if after:
                query["after"] = after
            page, error = reader(path, query)
            attempts.append({
                "page": page_index + 1,
                "source": source_name,
                "path": path,
                "after": after,
                "rows": len(page),
                "error": str(error or "")[:160],
            })
            if page:
                page_source = source_name
                selected_source = selected_source or source_name
                break
        if not page:
            break

        for raw in page:
            normalized = normalize_history_candle(
                raw,
                source=page_source,
                default_complete=False,
                require_utc_date=True,
            )
            if normalized:
                rows_by_ts[int(normalized["ts_ms"])] = normalized

        cursor = str(page[-1][0]) if isinstance(page[-1], (list, tuple)) and page[-1] else ""
        if not cursor and isinstance(page[-1], dict):
            cursor = str(page[-1].get("ts_ms") or page[-1].get("ts") or "")
        if len(rows_by_ts) >= clean_limit or not cursor or cursor == after:
            break
        try:
            if after and int(cursor) >= int(after):
                attempts.append({
                    "page": page_index + 1,
                    "source": page_source,
                    "path": "pagination_guard",
                    "after": after,
                    "rows": 0,
                    "error": "non_monotonic_after_cursor",
                })
                break
        except ValueError:
            break
        after = cursor

    ordered = [rows_by_ts[key] for key in sorted(rows_by_ts)]
    return ordered[-clean_limit:], selected_source, attempts


class MarketHistoryStore:
    def __init__(
        self,
        db_path: Path | str,
        *,
        now_ms: Callable[[], int] | None = None,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms or (lambda: time.time_ns() // 1_000_000)
        self.read_only = read_only is True

    def connect(self, *, write: bool = False) -> sqlite3.Connection:
        if write and self.read_only:
            raise PermissionError("market history store is read-only")
        if write:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.db_path, timeout=15)
            try:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA busy_timeout=15000")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                self._initialize(connection)
                return connection
            except Exception:
                connection.close()
                raise
        if not self.db_path.exists():
            raise FileNotFoundError(str(self.db_path))
        connection = sqlite3.connect(
            f"file:{self.db_path.resolve().as_posix()}?mode=ro",
            uri=True,
            timeout=15,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA busy_timeout=15000")
            return connection
        except Exception:
            connection.close()
            raise

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_daily_candles (
                symbol TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                ts_ms INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL DEFAULT 0,
                complete INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL,
                fetched_at INTEGER NOT NULL,
                PRIMARY KEY (symbol, trading_date)
            );
            CREATE INDEX IF NOT EXISTS idx_market_daily_symbol_ts
            ON market_daily_candles(symbol, ts_ms);
            CREATE TABLE IF NOT EXISTS market_history_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS market_daily_candle_revisions (
                revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                observed_at INTEGER NOT NULL,
                action TEXT NOT NULL,
                source TEXT NOT NULL,
                existing_source TEXT NOT NULL,
                before_hash TEXT NOT NULL,
                after_hash TEXT NOT NULL,
                reason TEXT NOT NULL,
                row_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_market_revision_symbol_date
            ON market_daily_candle_revisions(symbol, trading_date, revision_id);
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO market_history_meta(key, value) VALUES ('schema_version', ?)",
            (MARKET_HISTORY_STORE_VERSION,),
        )
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(market_daily_candles)")}
        if "complete" not in columns:
            connection.execute(
                "ALTER TABLE market_daily_candles ADD COLUMN complete INTEGER NOT NULL DEFAULT 1"
            )
        connection.commit()

    @staticmethod
    def _existing_payload(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "date": str(row["trading_date"] or ""),
            "ts_ms": int(row["ts_ms"] or 0),
            "open": float(row["open"] or 0),
            "high": float(row["high"] or 0),
            "low": float(row["low"] or 0),
            "close": float(row["close"] or 0),
            "volume": float(row["volume"] or 0),
            "complete": int(row["complete"] or 0) == 1,
            "source": str(row["source"] or ""),
        }

    @staticmethod
    def _revision(
        connection: sqlite3.Connection,
        *,
        symbol: str,
        observed_at: int,
        action: str,
        incoming: dict[str, Any],
        existing: dict[str, Any],
        reason: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO market_daily_candle_revisions(
                symbol, trading_date, observed_at, action, source, existing_source,
                before_hash, after_hash, reason, row_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                incoming["date"],
                observed_at,
                action,
                str(incoming.get("source") or ""),
                str(existing.get("source") or ""),
                canonical_hash(_semantic_candle(existing)),
                canonical_hash(_semantic_candle(incoming)),
                reason,
                json.dumps(_semantic_candle(incoming), ensure_ascii=True, sort_keys=True),
            ),
        )

    def upsert(self, symbol: str, rows: list[Any], source: str) -> dict[str, Any]:
        clean_symbol = str(symbol or "").strip().upper()
        source_name = str(source or "unknown").strip() or "unknown"
        normalized_by_date: dict[str, dict[str, Any]] = {}
        invalid = 0
        for raw in rows or []:
            normalized = normalize_history_candle(
                raw,
                source=source_name,
                default_complete=False,
                require_utc_date=True,
            )
            if not normalized:
                invalid += 1
                continue
            previous = normalized_by_date.get(normalized["date"])
            if previous is None or (not previous["complete"] and normalized["complete"]):
                normalized_by_date[normalized["date"]] = normalized
            elif previous["complete"] == normalized["complete"] and normalized["ts_ms"] >= previous["ts_ms"]:
                normalized_by_date[normalized["date"]] = normalized

        report = {
            "schema_version": MARKET_HISTORY_STORE_VERSION,
            "status": "PASS",
            "symbol": clean_symbol,
            "source": source_name,
            "received": len(rows or []),
            "valid": len(normalized_by_date),
            "stored": 0,
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "rejected": 0,
            "invalid": invalid,
            "read_only": self.read_only,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if self.read_only:
            return {**report, "status": "BLOCK", "blockers": ["market_history_store_read_only"]}
        if not clean_symbol or not normalized_by_date:
            return {
                **report,
                "status": "BLOCK",
                "blockers": ["market_history_symbol_missing"] if not clean_symbol else ["market_history_rows_invalid"],
            }

        observed_at = int(self.now_ms())
        _MARKET_HISTORY_WRITE_LOCK.acquire()
        try:
            connection = self.connect(write=True)
        except (sqlite3.Error, OSError) as exc:
            _MARKET_HISTORY_WRITE_LOCK.release()
            return {
                **report,
                "status": "BLOCK",
                "stored": 0,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "rejected": 0,
                "blockers": ["market_history_database_write_failed"],
                "error": f"{type(exc).__name__}: {exc}",
            }
        except Exception:
            _MARKET_HISTORY_WRITE_LOCK.release()
            raise
        try:
            connection.execute("BEGIN IMMEDIATE")
            for incoming in sorted(normalized_by_date.values(), key=lambda item: int(item["ts_ms"])):
                existing_row = connection.execute(
                    "SELECT * FROM market_daily_candles WHERE symbol = ? AND trading_date = ?",
                    (clean_symbol, incoming["date"]),
                ).fetchone()
                if existing_row is None:
                    connection.execute(
                        """
                        INSERT INTO market_daily_candles(
                            symbol, trading_date, ts_ms, open, high, low, close,
                            volume, complete, source, fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            clean_symbol,
                            incoming["date"],
                            incoming["ts_ms"],
                            incoming["open"],
                            incoming["high"],
                            incoming["low"],
                            incoming["close"],
                            incoming["volume"],
                            int(incoming["complete"]),
                            source_name,
                            observed_at,
                        ),
                    )
                    report["inserted"] += 1
                    continue

                existing = self._existing_payload(existing_row)
                existing_data_hash = canonical_hash(_semantic_candle(existing, include_source=False))
                incoming_data_hash = canonical_hash(_semantic_candle(incoming, include_source=False))
                incoming_priority = source_priority(source_name)
                existing_priority = source_priority(existing["source"])
                if existing_data_hash == incoming_data_hash:
                    if incoming_priority >= existing_priority:
                        connection.execute(
                            """
                            UPDATE market_daily_candles
                            SET source = ?, fetched_at = ?
                            WHERE symbol = ? AND trading_date = ?
                            """,
                            (source_name, observed_at, clean_symbol, incoming["date"]),
                        )
                    report["unchanged"] += 1
                    continue

                reject_reason = ""
                if existing["complete"] and not incoming["complete"]:
                    reject_reason = "completed_candle_cannot_regress_to_incomplete"
                elif existing["complete"] and incoming_priority < existing_priority:
                    reject_reason = "lower_priority_source_cannot_replace_completed_candle"
                elif (
                    existing["complete"] == incoming["complete"]
                    and incoming_priority < existing_priority
                ):
                    reject_reason = "lower_priority_source_cannot_replace_equal_completion_state"
                if reject_reason:
                    self._revision(
                        connection,
                        symbol=clean_symbol,
                        observed_at=observed_at,
                        action="REJECTED",
                        incoming=incoming,
                        existing=existing,
                        reason=reject_reason,
                    )
                    report["rejected"] += 1
                    continue

                reason = (
                    "completed_candle_replaces_incomplete"
                    if incoming["complete"] and not existing["complete"]
                    else "same_or_higher_priority_revision"
                )
                self._revision(
                    connection,
                    symbol=clean_symbol,
                    observed_at=observed_at,
                    action="ACCEPTED",
                    incoming=incoming,
                    existing=existing,
                    reason=reason,
                )
                connection.execute(
                    """
                    UPDATE market_daily_candles
                    SET ts_ms = ?, open = ?, high = ?, low = ?, close = ?, volume = ?,
                        complete = ?, source = ?, fetched_at = ?
                    WHERE symbol = ? AND trading_date = ?
                    """,
                    (
                        incoming["ts_ms"],
                        incoming["open"],
                        incoming["high"],
                        incoming["low"],
                        incoming["close"],
                        incoming["volume"],
                        int(incoming["complete"]),
                        source_name,
                        observed_at,
                        clean_symbol,
                        incoming["date"],
                    ),
                )
                report["updated"] += 1
            connection.commit()
        except (sqlite3.Error, OSError) as exc:
            connection.rollback()
            return {
                **report,
                "status": "BLOCK",
                "stored": 0,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "rejected": 0,
                "blockers": ["market_history_database_write_failed"],
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            try:
                connection.close()
            finally:
                _MARKET_HISTORY_WRITE_LOCK.release()

        report["stored"] = report["inserted"] + report["updated"] + report["unchanged"]
        report["status"] = "PASS" if report["stored"] > 0 and report["rejected"] == 0 and invalid == 0 else "REVIEW"
        report["blockers"] = []
        if invalid:
            report["blockers"].append(f"invalid_rows:{invalid}")
        if report["rejected"]:
            report["blockers"].append(f"rejected_revisions:{report['rejected']}")
        return report

    def read(self, symbol: str, limit: int = 500) -> dict[str, Any]:
        clean_symbol = str(symbol or "").strip().upper()
        if not self.db_path.exists():
            return {
                "ok": False,
                "status": "MISSING",
                "source": "local_market_cache",
                "path": str(self.db_path),
                "symbol": clean_symbol,
                "rows": [],
                "error": "cache database missing",
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        connection: sqlite3.Connection | None = None
        try:
            connection = self.connect(write=False)
            raw_rows = connection.execute(
                """
                SELECT * FROM (
                    SELECT trading_date AS date, ts_ms, open, high, low, close,
                           volume, complete, source, fetched_at
                    FROM market_daily_candles
                    WHERE symbol = ?
                    ORDER BY ts_ms DESC
                    LIMIT ?
                )
                ORDER BY ts_ms ASC
                """,
                (clean_symbol, max(1, int(limit))),
            ).fetchall()
        except (sqlite3.Error, OSError) as exc:
            return {
                "ok": False,
                "status": "BLOCK",
                "source": "local_market_cache",
                "path": str(self.db_path),
                "symbol": clean_symbol,
                "rows": [],
                "error": f"{type(exc).__name__}: {exc}",
                "warning": "market history cache database could not be read",
                "read_only": True,
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        finally:
            if connection is not None:
                connection.close()

        rows: list[dict[str, Any]] = []
        invalid = 0
        for raw in raw_rows:
            payload = dict(raw)
            normalized = normalize_history_candle(
                payload,
                source=str(payload.get("source") or ""),
                default_complete=False,
                require_utc_date=True,
            )
            if not normalized:
                invalid += 1
                continue
            rows.append({
                **_semantic_candle(normalized),
                "row_hash": normalized["row_hash"],
                "fetched_at": int(payload.get("fetched_at") or 0),
            })
        manifest = self._manifest(clean_symbol, rows, invalid)
        return {
            "ok": bool(rows) and invalid == 0,
            "status": manifest["status"],
            "source": "local_market_cache",
            "path": str(self.db_path),
            "symbol": clean_symbol,
            "rows": rows,
            "manifest": manifest,
            "fallback": True,
            "cached": True,
            "warning": f"invalid cached rows rejected: {invalid}" if invalid else "",
            "read_only": True,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    @staticmethod
    def _manifest(symbol: str, rows: list[dict[str, Any]], invalid: int) -> dict[str, Any]:
        complete_rows = [row for row in rows if row.get("complete") is True]
        if invalid:
            status = "BLOCK"
        elif len(complete_rows) >= 240:
            status = "READY"
        elif len(complete_rows) >= 80:
            status = "PARTIAL"
        else:
            status = "MISSING"
        data_rows = [_semantic_candle(row) for row in rows]
        return {
            "schema_version": MARKET_HISTORY_MANIFEST_VERSION,
            "status": status,
            "symbol": symbol,
            "row_count": len(rows),
            "complete_count": len(complete_rows),
            "incomplete_count": len(rows) - len(complete_rows),
            "invalid_count": invalid,
            "first": rows[0]["date"] if rows else "",
            "last": rows[-1]["date"] if rows else "",
            "sources": sorted({str(row.get("source") or "") for row in rows if row.get("source")}),
            "latest_fetched_at": max((int(row.get("fetched_at") or 0) for row in rows), default=0),
            "data_hash": canonical_hash(data_rows),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def stats(self, symbol: str) -> dict[str, Any]:
        payload = self.read(symbol, 10_000)
        manifest = dict(payload.get("manifest") or {})
        return {
            "symbol": str(symbol or "").strip().upper(),
            "rows": int(manifest.get("row_count") or 0),
            "complete_rows": int(manifest.get("complete_count") or 0),
            "incomplete_rows": int(manifest.get("incomplete_count") or 0),
            "invalid_rows": int(manifest.get("invalid_count") or 0),
            "first": str(manifest.get("first") or ""),
            "last": str(manifest.get("last") or ""),
            "fetched_at": int(manifest.get("latest_fetched_at") or 0),
            "source": "local_market_cache" if payload.get("rows") else "missing",
            "sources": list(manifest.get("sources") or []),
            "data_hash": str(manifest.get("data_hash") or ""),
            "status": str(manifest.get("status") or "MISSING"),
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def revision_summary(self, symbol: str = "") -> dict[str, Any]:
        clean_symbol = str(symbol or "").strip().upper()
        if not self.db_path.exists():
            return {"status": "MISSING", "accepted": 0, "rejected": 0, "rows": []}
        connection: sqlite3.Connection | None = None
        try:
            connection = self.connect(write=False)
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_daily_candle_revisions'"
            ).fetchone()
            if not table_exists:
                return {"status": "LEGACY", "accepted": 0, "rejected": 0, "rows": []}
            query = "SELECT * FROM market_daily_candle_revisions"
            params: tuple[Any, ...] = ()
            if clean_symbol:
                query += " WHERE symbol = ?"
                params = (clean_symbol,)
            query += " ORDER BY revision_id DESC LIMIT 100"
            rows = [dict(row) for row in connection.execute(query, params).fetchall()]
        except (sqlite3.Error, OSError) as exc:
            return {
                "status": "BLOCK",
                "accepted": 0,
                "rejected": 0,
                "rows": [],
                "error": f"{type(exc).__name__}: {exc}",
                "read_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        finally:
            if connection is not None:
                connection.close()
        accepted = len([row for row in rows if row.get("action") == "ACCEPTED"])
        rejected = len([row for row in rows if row.get("action") == "REJECTED"])
        return {
            "status": "REVIEW" if rejected else "PASS",
            "accepted": accepted,
            "rejected": rejected,
            "rows": rows,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
