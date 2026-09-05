from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime
from statistics import median
from typing import Any

try:
    from config import (
        CORPORATE_ACTION_DB,
        MARKET_DATA_REVISION_DB,
        RUNTIME_READ_ONLY,
        STOCK_CANDLE_CACHE_DB,
        STOCK_EXTERNAL_PROVIDER_ORDER,
        STOCK_HISTORY_TIMEOUT,
    )
    from hakimi_research.stock_metadata import (
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_source_symbol,
        stock_timezone,
        yahoo_stock_symbol,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        clean_stock_session,
        filter_stock_rows_by_session,
        latest_stock_candle_ts,
        normalize_stock_cache_candle,
        stock_cache_fresh_ms,
        stock_cache_interval,
        stock_candle_complete_at,
        stock_candle_stale_warning,
        stock_current_session_date,
        stock_payload_needs_session_refresh,
        with_stock_freshness,
    )
    from hakimi_research.candle_contract import candle_is_complete
    from market_data.provider_health import provider_call_allowed, record_provider_call
    from services.corporate_action_ledger import (
        CorporateActionLedger,
        build_adjustment_evidence,
        parse_yahoo_corporate_actions,
    )
    from services.market_data_revision_ledger import (
        MarketDataRevisionLedger,
        build_cross_source_evidence,
        build_market_data_snapshot,
    )
    from services.sqlite_runtime import connect_runtime_sqlite, require_runtime_writable
    from utils import now_ms, pct
except ModuleNotFoundError:
    from hakimi_research.terminal_config import (
        CORPORATE_ACTION_DB,
        MARKET_DATA_REVISION_DB,
        RUNTIME_READ_ONLY,
        STOCK_CANDLE_CACHE_DB,
        STOCK_EXTERNAL_PROVIDER_ORDER,
        STOCK_HISTORY_TIMEOUT,
    )
    from hakimi_research.stock_metadata import (
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_source_symbol,
        stock_timezone,
        yahoo_stock_symbol,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        clean_stock_session,
        filter_stock_rows_by_session,
        latest_stock_candle_ts,
        normalize_stock_cache_candle,
        stock_cache_fresh_ms,
        stock_cache_interval,
        stock_candle_complete_at,
        stock_candle_stale_warning,
        stock_current_session_date,
        stock_payload_needs_session_refresh,
        with_stock_freshness,
    )
    from hakimi_research.candle_contract import candle_is_complete
    from exchange_terminal.market_data.provider_health import provider_call_allowed, record_provider_call
    from exchange_terminal.services.corporate_action_ledger import (
        CorporateActionLedger,
        build_adjustment_evidence,
        parse_yahoo_corporate_actions,
    )
    from exchange_terminal.services.market_data_revision_ledger import (
        MarketDataRevisionLedger,
        build_cross_source_evidence,
        build_market_data_snapshot,
    )
    from exchange_terminal.services.sqlite_runtime import connect_runtime_sqlite, require_runtime_writable
    from hakimi_research.terminal_utils import now_ms, pct

from hakimi_research.stock_candle_revision_policy import (
    canonical_adjusted_price as _canonical_adjusted_price,
    infer_adjustment_basis,
    prepare_stock_candle_revision_policy,
    series_adjustment_contract as _series_adjustment_contract,
    stock_candle_source_priority as _stock_candle_source_priority,
)


STOCK_EXTERNAL_FAILURE_CACHE: dict[str, dict[str, Any]] = {}
CORPORATE_ACTION_LEDGER = CorporateActionLedger(CORPORATE_ACTION_DB, now_ms, read_only=RUNTIME_READ_ONLY)
MARKET_DATA_REVISION_LEDGER = MarketDataRevisionLedger(MARKET_DATA_REVISION_DB, now_ms, read_only=RUNTIME_READ_ONLY)
_COMPATIBLE_FORWARD_ADJUSTED_BASES = {
    "FORWARD_ADJUSTED_QFQ",
    "FORWARD_ADJUSTED_TOTAL_RETURN",
}
_YAHOO_ADJUSTED_VOLUME_MIGRATION_VERSION = "yahoo-adjusted-volume-inverse-v2"
_PROVIDER_OBSERVATION_SCOPES = {"AUTHORITATIVE_FULL", "QUERY_WINDOW"}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_only_stock_snapshot_attestation(
    snapshot: dict[str, Any],
    *,
    reference_provider: str = "accepted_stock_cache",
    reference_role: str = "ACCEPTED_CACHE",
) -> dict[str, Any]:
    latest = MARKET_DATA_REVISION_LEDGER.latest_snapshot(
        symbol=str(snapshot.get("symbol") or ""),
        provider=reference_provider,
        role=reference_role,
        interval=str(snapshot.get("interval") or "1d"),
        session=str(snapshot.get("session") or "regular"),
    )
    reference = dict(latest.get("snapshot") or {})
    observed_rows = [dict(row) for row in snapshot.get("rows") or [] if isinstance(row, dict)]
    reference_rows = [dict(row) for row in reference.get("rows") or [] if isinstance(row, dict)]
    reference_by_date = {
        str(row.get("date") or ""): str(row.get("row_hash") or "")
        for row in reference_rows
        if str(row.get("date") or "")
    }
    missing_dates = [
        str(row.get("date") or "")
        for row in observed_rows
        if str(row.get("date") or "") not in reference_by_date
    ]
    changed_dates = [
        str(row.get("date") or "")
        for row in observed_rows
        if str(row.get("date") or "") in reference_by_date
        and str(row.get("row_hash") or "") != reference_by_date[str(row.get("date") or "")]
    ]
    blockers: list[str] = []
    if not reference_rows:
        blockers.append("recorded_reference_snapshot_missing")
    if str(latest.get("state_status") or "BLOCK") != "PASS":
        blockers.append(f"recorded_reference_state:{latest.get('state_status') or 'MISSING'}")
    if str(latest.get("blocking_event_hash") or ""):
        blockers.append("recorded_reference_has_unresolved_revision")
    if missing_dates:
        blockers.append(f"rows_missing_from_recorded_reference:{len(missing_dates)}")
    if changed_dates:
        blockers.append(f"rows_changed_from_recorded_reference:{len(changed_dates)}")
    if str(snapshot.get("adjustment_basis") or "") != str(reference.get("adjustment_basis") or ""):
        blockers.append("recorded_reference_adjustment_basis_mismatch")
    if str(snapshot.get("corporate_actions_hash") or "") != str(reference.get("corporate_actions_hash") or ""):
        blockers.append("recorded_reference_corporate_actions_mismatch")
    exact = (
        not blockers
        and str(snapshot.get("rows_hash") or "") == str(reference.get("rows_hash") or "")
        and int(snapshot.get("row_count") or 0) == int(reference.get("row_count") or 0)
    )
    payload = {
        "schema_version": "read-only-stock-snapshot-attestation-v1",
        "status": "PASS" if not blockers else "BLOCK",
        "classification": "READ_ONLY_RECORDED_EXACT_MATCH" if exact else "READ_ONLY_RECORDED_SUBSET_MATCH" if not blockers else "READ_ONLY_REFERENCE_MISMATCH",
        "scope_key": str(latest.get("scope_key") or ""),
        "blocking_event_hash": str(latest.get("blocking_event_hash") or ""),
        "current": {key: value for key, value in snapshot.items() if key != "rows"},
        "recorded_reference": {key: value for key, value in reference.items() if key != "rows"},
        "observed_row_count": len(observed_rows),
        "recorded_row_count": len(reference_rows),
        "missing_dates": missing_dates[:20],
        "changed_dates": changed_dates[:20],
        "blockers": blockers,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["attestation_hash"] = _canonical_hash(payload)
    return payload


def enrich_stock_series_contract(
    payload: dict[str, Any],
    symbol: str,
    interval: str,
    session: str,
    *,
    persist: bool = False,
) -> dict[str, Any]:
    enriched = dict(payload or {})
    source = str(enriched.get("origin_source") or enriched.get("source") or "")
    basis = infer_adjustment_basis(source, str(enriched.get("adjustment_basis") or ""))
    action_coverage = str(enriched.get("corporate_action_coverage") or "")
    actions = list(enriched.get("corporate_actions") or CORPORATE_ACTION_LEDGER.actions(symbol))
    evidence = build_adjustment_evidence(
        symbol=symbol,
        rows=list(enriched.get("rows") or []),
        source=source,
        adjustment_basis=basis,
        corporate_actions=actions,
        corporate_action_coverage=action_coverage,
        interval=stock_cache_interval(interval),
        session=clean_stock_session(session),
    )
    if persist:
        CORPORATE_ACTION_LEDGER.record(
            symbol=symbol,
            provider=source,
            actions=actions,
            evidence=evidence,
        )
    return {
        **enriched,
        "adjustment_basis": basis,
        "corporate_action_coverage": action_coverage or evidence.get("corporate_action_coverage", ""),
        "corporate_actions": actions,
        "adjustment_evidence": evidence,
    }


def ensure_stock_candle_cache_db(*, write: bool = False) -> sqlite3.Connection:
    if RUNTIME_READ_ONLY:
        require_runtime_writable(
            read_only=write,
            service="stock_candle_cache",
        )
        conn = connect_runtime_sqlite(STOCK_CANDLE_CACHE_DB, read_only=True)
        conn.row_factory = sqlite3.Row
        return conn

    conn = connect_runtime_sqlite(STOCK_CANDLE_CACHE_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_candles (
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            query_session TEXT NOT NULL,
            row_session TEXT DEFAULT '',
            ts_ms INTEGER NOT NULL,
            trading_date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL DEFAULT 0,
            complete INTEGER NOT NULL DEFAULT 1,
            source TEXT NOT NULL,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (symbol, interval, query_session, ts_ms)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_candles_symbol_interval_ts
        ON stock_candles(symbol, interval, query_session, ts_ms)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_candle_cache_migrations (
            migration_key TEXT PRIMARY KEY,
            migration_version TEXT NOT NULL,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            query_session TEXT NOT NULL,
            source_family TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            price_scale REAL NOT NULL,
            before_hash TEXT NOT NULL,
            after_hash TEXT NOT NULL,
            applied_at INTEGER NOT NULL
        )
    """)
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(stock_candles)").fetchall()}
    if "complete" not in columns:
        conn.execute("ALTER TABLE stock_candles ADD COLUMN complete INTEGER NOT NULL DEFAULT 1")
    indexes = {str(row[1]) for row in conn.execute("PRAGMA index_list(stock_candles)").fetchall()}
    if "idx_stock_daily_unique_date" not in indexes:
        conn.execute("""
            DELETE FROM stock_candles
            WHERE interval IN ('1d', '1dutc')
              AND rowid NOT IN (
                  SELECT rowid FROM (
                      SELECT
                          rowid,
                          ROW_NUMBER() OVER (
                              PARTITION BY symbol, interval, query_session, trading_date
                              ORDER BY fetched_at DESC,
                                  CASE WHEN LOWER(source) = 'futu' THEN 0 ELSE 1 END,
                                  rowid DESC
                          ) AS rank
                      FROM stock_candles
                      WHERE interval IN ('1d', '1dutc')
                  ) ranked
                  WHERE rank = 1
              )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX idx_stock_daily_unique_date
            ON stock_candles(symbol, interval, query_session, trading_date)
            WHERE interval IN ('1d', '1dutc')
        """)
    conn.commit()
    return conn


def prepare_stock_candle_cache_rows(
    symbol: str,
    interval: str,
    session: str,
    rows: list[Any],
    source: str,
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    native_rows = rows if type(rows) is list else []
    normalized = [
        item for item in (normalize_stock_cache_candle(row, meta["symbol"]) for row in native_rows)
        if item and item.get("ts")
    ]
    if normalized_interval not in {"1d", "1dutc"} or not normalized:
        return prepare_stock_candle_revision_policy(normalized, [], source, normalized_interval)

    conn = ensure_stock_candle_cache_db()
    try:
        existing_rows = [dict(row) for row in conn.execute(
            """
            SELECT ts_ms AS ts, trading_date AS date, open, high, low, close,
                   volume, complete, row_session AS session, source
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
            ORDER BY trading_date
            """,
            (meta["symbol"], normalized_interval, clean_session),
        ).fetchall()]
    finally:
        conn.close()
    return prepare_stock_candle_revision_policy(
        normalized,
        existing_rows,
        source,
        normalized_interval,
    )


def upsert_stock_candle_cache(
    symbol: str,
    interval: str,
    session: str,
    rows: list[Any],
    source: str,
    *,
    prepared: bool = False,
) -> int:
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    normalized = (
        [dict(row) for row in rows]
        if prepared
        else list(prepare_stock_candle_cache_rows(symbol, interval, session, rows, source)["rows"])
    )
    if not normalized:
        return 0
    fetched_at = now_ms()
    conn = ensure_stock_candle_cache_db(write=True)
    try:
        before_changes = conn.total_changes
        conn.executemany("""
            INSERT INTO stock_candles
                (symbol, interval, query_session, row_session, ts_ms, trading_date, open, high, low, close, volume, complete, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO UPDATE SET
                row_session=excluded.row_session,
                ts_ms=excluded.ts_ms,
                trading_date=excluded.trading_date,
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                volume=excluded.volume,
                complete=excluded.complete,
                source=excluded.source,
                fetched_at=excluded.fetched_at
            WHERE
                (
                CASE
                    WHEN LOWER(excluded.source) LIKE '%futu%' THEN 40
                    WHEN LOWER(excluded.source) LIKE '%yahoo_adjusted%' THEN 30
                    WHEN LOWER(excluded.source) LIKE '%yahoo%' THEN 20
                    WHEN LOWER(excluded.source) LIKE '%stooq%' THEN 10
                    ELSE 0
                END >
                CASE
                    WHEN LOWER(stock_candles.source) LIKE '%futu%' THEN 40
                    WHEN LOWER(stock_candles.source) LIKE '%yahoo_adjusted%' THEN 30
                    WHEN LOWER(stock_candles.source) LIKE '%yahoo%' THEN 20
                    WHEN LOWER(stock_candles.source) LIKE '%stooq%' THEN 10
                    ELSE 0
                END
                AND (
                    stock_candles.interval NOT IN ('1d', '1dutc')
                    OR stock_candles.complete = 0
                    OR (
                        (
                            LOWER(excluded.source) LIKE '%futu%'
                            OR LOWER(excluded.source) LIKE '%yahoo_adjusted%'
                        )
                        AND NOT (
                            LOWER(stock_candles.source) LIKE '%futu%'
                            OR LOWER(stock_candles.source) LIKE '%yahoo_adjusted%'
                        )
                    )
                )
                )
                OR (
                    CASE
                        WHEN LOWER(excluded.source) LIKE '%futu%' THEN 40
                        WHEN LOWER(excluded.source) LIKE '%yahoo_adjusted%' THEN 30
                        WHEN LOWER(excluded.source) LIKE '%yahoo%' THEN 20
                        WHEN LOWER(excluded.source) LIKE '%stooq%' THEN 10
                        ELSE 0
                    END =
                    CASE
                        WHEN LOWER(stock_candles.source) LIKE '%futu%' THEN 40
                        WHEN LOWER(stock_candles.source) LIKE '%yahoo_adjusted%' THEN 30
                        WHEN LOWER(stock_candles.source) LIKE '%yahoo%' THEN 20
                        WHEN LOWER(stock_candles.source) LIKE '%stooq%' THEN 10
                        ELSE 0
                    END
                    AND (
                        stock_candles.interval NOT IN ('1d', '1dutc')
                        OR stock_candles.complete = 0
                    )
                )
        """, [
            (
                meta["symbol"],
                normalized_interval,
                clean_session,
                row.get("session") or "",
                int(row["ts"]),
                row["date"],
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row.get("volume") or 0),
                int(candle_is_complete(row, default_if_missing=False)),
                source,
                fetched_at,
            )
            for row in normalized
        ])
        conn.commit()
        return conn.total_changes - before_changes
    finally:
        conn.close()


def migrate_legacy_yahoo_adjusted_volume_cache(
    symbol: str,
    rows: list[Any],
    interval: str = "1d",
    session: str = "regular",
) -> dict[str, Any]:
    """Repair legacy Yahoo adjusted volume without changing the frozen OHLC vintage."""
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    migration_key = ":".join((
        _YAHOO_ADJUSTED_VOLUME_MIGRATION_VERSION,
        meta["symbol"],
        normalized_interval,
        clean_session,
    ))
    result = {
        "schema_version": "stock-candle-cache-migration-v1",
        "migration_version": _YAHOO_ADJUSTED_VOLUME_MIGRATION_VERSION,
        "migration_key": migration_key,
        "symbol": meta["symbol"],
        "interval": normalized_interval,
        "session": clean_session,
        "status": "BLOCK",
        "updated_rows": 0,
    }
    if normalized_interval not in {"1d", "1dutc"}:
        return {**result, "blockers": ["daily_interval_required"]}

    raw_rows = [row for row in rows if isinstance(row, dict)]
    normalized = [
        item for item in (normalize_stock_cache_candle(row, meta["symbol"]) for row in raw_rows)
        if item and item.get("ts")
    ]
    if (
        not normalized
        or len(raw_rows) != len(rows)
        or len(normalized) != len(raw_rows)
        or any("yahoo_adjusted" not in str(row.get("source") or "").lower() for row in raw_rows)
    ):
        return {**result, "blockers": ["complete_yahoo_adjusted_refresh_required"]}
    incoming_by_date = {str(row.get("date") or ""): row for row in normalized if row.get("date")}

    conn = ensure_stock_candle_cache_db(write=True)
    try:
        conn.execute("BEGIN IMMEDIATE")
        prior = conn.execute(
            "SELECT * FROM stock_candle_cache_migrations WHERE migration_key = ?",
            (migration_key,),
        ).fetchone()
        if prior:
            conn.rollback()
            return {
                **result,
                "status": "ALREADY_APPLIED",
                "updated_rows": int(prior["row_count"] or 0),
                "price_scale": float(prior["price_scale"] or 0.0),
                "before_hash": str(prior["before_hash"] or ""),
                "after_hash": str(prior["after_hash"] or ""),
                "applied_at": int(prior["applied_at"] or 0),
                "blockers": [],
            }
        existing = [dict(row) for row in conn.execute(
            """
            SELECT trading_date, close, volume, source
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
              AND complete = 1 AND LOWER(source) LIKE '%yahoo_adjusted%'
            ORDER BY trading_date
            """,
            (meta["symbol"], normalized_interval, clean_session),
        ).fetchall()]
        if not existing:
            conn.rollback()
            return {**result, "blockers": ["legacy_yahoo_adjusted_rows_missing"]}
        if any(str(row.get("trading_date") or "") not in incoming_by_date for row in existing):
            conn.rollback()
            return {**result, "blockers": ["refresh_does_not_cover_all_legacy_rows"]}

        ratios = []
        for row in existing:
            incoming = incoming_by_date[str(row["trading_date"])]
            existing_close = float(row.get("close") or 0.0)
            incoming_close = float(incoming.get("close") or 0.0)
            if not all(math.isfinite(value) and value > 0 for value in (existing_close, incoming_close)):
                conn.rollback()
                return {**result, "blockers": ["invalid_overlap_close"]}
            ratios.append(existing_close / incoming_close)
        scale = median(ratios)
        dispersion = max(abs(value / scale - 1.0) for value in ratios)
        if not math.isfinite(scale) or not 0.02 <= scale <= 50.0:
            conn.rollback()
            return {**result, "blockers": ["daily_adjustment_vintage_scale_out_of_range"]}
        if dispersion > 0.0025:
            conn.rollback()
            return {**result, "blockers": ["daily_adjustment_vintage_overlap_is_not_uniform"]}

        before_rows = []
        after_rows = []
        updates = []
        for row in existing:
            trading_date = str(row["trading_date"])
            incoming_volume = float(incoming_by_date[trading_date].get("volume") or 0.0)
            existing_volume = float(row.get("volume") or 0.0)
            migrated_volume = incoming_volume / scale
            if not all(math.isfinite(value) and value >= 0 for value in (incoming_volume, existing_volume, migrated_volume)):
                conn.rollback()
                return {**result, "blockers": ["invalid_overlap_volume"]}
            before_rows.append((trading_date, float(row["close"]), existing_volume))
            after_rows.append((trading_date, float(row["close"]), migrated_volume))
            updates.append((migrated_volume, meta["symbol"], normalized_interval, clean_session, trading_date, row["source"]))

        before_hash = hashlib.sha256(json.dumps(before_rows, separators=(",", ":")).encode("utf-8")).hexdigest()
        after_hash = hashlib.sha256(json.dumps(after_rows, separators=(",", ":")).encode("utf-8")).hexdigest()
        changed = 0
        for update in updates:
            cursor = conn.execute(
                """
                UPDATE stock_candles SET volume = ?
                WHERE symbol = ? AND interval = ? AND query_session = ?
                  AND trading_date = ? AND source = ? AND complete = 1
                """,
                update,
            )
            changed += int(cursor.rowcount or 0)
        if changed != len(existing):
            conn.rollback()
            return {**result, "blockers": ["concurrent_cache_change_detected"]}

        applied_at = now_ms()
        conn.execute(
            """
            INSERT INTO stock_candle_cache_migrations
                (migration_key, migration_version, symbol, interval, query_session, source_family,
                 row_count, price_scale, before_hash, after_hash, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                migration_key,
                _YAHOO_ADJUSTED_VOLUME_MIGRATION_VERSION,
                meta["symbol"],
                normalized_interval,
                clean_session,
                "yahoo_adjusted",
                len(existing),
                scale,
                before_hash,
                after_hash,
                applied_at,
            ),
        )
        conn.commit()
        return {
            **result,
            "status": "PASS",
            "updated_rows": changed,
            "price_scale": scale,
            "maximum_price_ratio_dispersion": dispersion,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "applied_at": applied_at,
            "blockers": [],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def read_stock_persistent_candle_cache(symbol: str, limit: int, interval: str, session: str) -> dict[str, Any] | None:
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    if not STOCK_CANDLE_CACHE_DB.exists():
        return None
    conn = ensure_stock_candle_cache_db()
    derived_from_session = ""
    try:
        cursor = conn.execute("""
            SELECT * FROM (
                SELECT
                    ts_ms AS ts,
                    trading_date AS date,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    complete,
                    row_session AS session,
                    source,
                    fetched_at
                FROM stock_candles
                WHERE symbol = ? AND interval = ? AND query_session = ?
                ORDER BY ts_ms DESC
                LIMIT ?
            )
            ORDER BY ts ASC
        """, (meta["symbol"], normalized_interval, clean_session, max(1, int(limit))))
        rows = [dict(row) for row in cursor.fetchall()]
        if not rows and clean_session != "all":
            cursor = conn.execute("""
                SELECT * FROM (
                    SELECT
                        ts_ms AS ts,
                        trading_date AS date,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        complete,
                        row_session AS session,
                        source,
                        fetched_at
                    FROM stock_candles
                    WHERE symbol = ? AND interval = ? AND query_session = 'all' AND row_session = ?
                    ORDER BY ts_ms DESC
                    LIMIT ?
                )
                ORDER BY ts ASC
            """, (meta["symbol"], normalized_interval, clean_session, max(1, int(limit))))
            rows = [dict(row) for row in cursor.fetchall()]
            if rows:
                derived_from_session = "all"
    finally:
        conn.close()
    if not rows:
        return None
    if normalized_interval not in {"1d", "1dutc"}:
        for row in rows:
            close = pct(row.get("close", 0.0))
            volume = pct(row.get("volume", 0.0))
            high = pct(row.get("high", close), close)
            low = pct(row.get("low", close), close)
            source = str(row.get("source") or "").lower()
            span_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else 0.0
            if close > 0 and volume <= 0 and source == "futu" and span_pct >= 0.8:
                row["open"] = close
                row["high"] = close
                row["low"] = close
    fetched_at = max(int(row.get("fetched_at") or 0) for row in rows)
    source = rows[-1].get("source") or rows[0].get("source") or "stock_sqlite_cache"
    source_lineage = sorted(
        {str(row.get("source") or "").strip().lower() for row in rows if row.get("source")},
        key=lambda item: (-_stock_candle_source_priority(item), item),
    )
    adjustment_basis, action_coverage = _series_adjustment_contract(source_lineage)
    stale_warning = stock_candle_stale_warning(rows, normalized_interval, meta["symbol"])
    session_lag_warning = "stock cache behind current session" if stock_payload_needs_session_refresh({"rows": rows}, interval, meta["symbol"]) else ""
    read_at = now_ms()
    active_session = stock_session_from_ts(read_at, meta["symbol"])
    refresh_sensitive = clean_session == "all" or clean_session == active_session
    cache_expired = read_at - fetched_at > stock_cache_fresh_ms(normalized_interval) and refresh_sensitive
    cached_payload = with_stock_freshness({
        "ok": True,
        "symbol": meta["symbol"],
        "source": "stock_sqlite_cache",
        "origin_source": source,
        "origin_sources": source_lineage,
        "adjustment_basis": adjustment_basis,
        "corporate_action_coverage": action_coverage,
        "interval": normalized_interval,
        "session": clean_session,
        "session_label": stock_session_label(clean_session),
        "derived_from_session": derived_from_session,
        "rows": rows,
        "cached": True,
        "persistent_cache": True,
        "cache_age_ms": read_at - fetched_at,
        "updated_at": fetched_at,
        "path": str(STOCK_CANDLE_CACHE_DB),
        "warning": stale_warning or session_lag_warning or ("stale stock cache" if cache_expired else ""),
    }, interval, symbol)
    return enrich_stock_series_contract(cached_payload, meta["symbol"], normalized_interval, clean_session)


def stock_candle_cache_coverage(symbol: str, interval: str, session: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    empty = {
        "available": False,
        "symbol": meta["symbol"],
        "interval": normalized_interval,
        "session": clean_session,
        "row_count": 0,
        "first_ts": 0,
        "latest_ts": 0,
        "first_date": "",
        "latest_date": "",
        "last_fetched_at": 0,
        "data_age_ms": None,
        "cache_age_ms": None,
        "source_counts": {},
        "session_counts": {},
    }
    if not STOCK_CANDLE_CACHE_DB.exists():
        return empty
    conn = ensure_stock_candle_cache_db()
    try:
        summary = conn.execute("""
            SELECT
                COUNT(*) AS row_count,
                MIN(ts_ms) AS first_ts,
                MAX(ts_ms) AS latest_ts,
                MIN(trading_date) AS first_date,
                MAX(trading_date) AS latest_date,
                MAX(fetched_at) AS last_fetched_at
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
        """, (meta["symbol"], normalized_interval, clean_session)).fetchone()
        source_rows = conn.execute("""
            SELECT source, COUNT(*) AS row_count
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
            GROUP BY source
            ORDER BY row_count DESC, source ASC
        """, (meta["symbol"], normalized_interval, clean_session)).fetchall()
        session_rows = conn.execute("""
            SELECT COALESCE(NULLIF(row_session, ''), 'unknown') AS row_session, COUNT(*) AS row_count
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
            GROUP BY COALESCE(NULLIF(row_session, ''), 'unknown')
            ORDER BY row_count DESC, row_session ASC
        """, (meta["symbol"], normalized_interval, clean_session)).fetchall()
    finally:
        conn.close()
    row_count = int((summary or {}).get("row_count") or 0) if isinstance(summary, dict) else int(summary["row_count"] or 0)
    if row_count <= 0:
        return empty
    first_ts = int(summary["first_ts"] or 0)
    latest_ts = int(summary["latest_ts"] or 0)
    fetched_at = int(summary["last_fetched_at"] or 0)
    stamp = now_ms()
    return {
        **empty,
        "available": True,
        "row_count": row_count,
        "first_ts": first_ts,
        "latest_ts": latest_ts,
        "first_date": str(summary["first_date"] or ""),
        "latest_date": str(summary["latest_date"] or ""),
        "last_fetched_at": fetched_at,
        "data_age_ms": max(stamp - latest_ts, 0) if latest_ts else None,
        "cache_age_ms": max(stamp - fetched_at, 0) if fetched_at else None,
        "source_counts": {str(row["source"] or "unknown"): int(row["row_count"] or 0) for row in source_rows},
        "session_counts": {str(row["row_session"] or "unknown"): int(row["row_count"] or 0) for row in session_rows},
    }


def record_stock_revision_snapshot(
    *,
    symbol: str,
    provider: str,
    rows: list[dict[str, Any]],
    interval: str = "1d",
    session: str = "regular",
    role: str = "PROVIDER_OBSERVATION",
    adjustment_basis: str = "",
    corporate_actions_hash: str = "",
    through_date: str = "",
    observation_scope: str = "AUTHORITATIVE_FULL",
    dataset_lineage_id: str = "",
) -> dict[str, Any]:
    clean_role = str(role or "PROVIDER_OBSERVATION").upper()
    clean_observation_scope = str(observation_scope or "AUTHORITATIVE_FULL").strip().upper()
    if clean_observation_scope not in _PROVIDER_OBSERVATION_SCOPES:
        raise ValueError("provider_observation_scope_invalid")
    if clean_role != "PROVIDER_OBSERVATION" and clean_observation_scope != "AUTHORITATIVE_FULL":
        raise ValueError("query_window_scope_requires_provider_observation")
    snapshot = build_market_data_snapshot(
        symbol=symbol,
        provider=provider,
        rows=rows,
        interval=stock_cache_interval(interval),
        session=clean_stock_session(session),
        role=clean_role,
        adjustment_basis=adjustment_basis or infer_adjustment_basis(provider),
        corporate_actions_hash=corporate_actions_hash,
        completed_only=True,
        through_date=through_date,
        lineage_id=dataset_lineage_id,
    )
    if not snapshot.get("row_count"):
        return {
            "status": "BLOCK",
            "classification": "EMPTY_SNAPSHOT",
            "blockers": ["completed_market_data_rows_missing"],
            "current": {key: value for key, value in snapshot.items() if key != "rows"},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    if clean_role == "PROVIDER_OBSERVATION" and clean_observation_scope == "QUERY_WINDOW":
        latest = MARKET_DATA_REVISION_LEDGER.latest_snapshot(
            symbol=symbol,
            provider=provider,
            role="PROVIDER_OBSERVATION",
            interval=stock_cache_interval(interval),
            session=clean_stock_session(session),
        )
        previous = dict(latest.get("snapshot") or {})
        if previous and any(
            str(previous.get(key) or "").lower() != str(snapshot.get(key) or "").lower()
            for key in ("symbol", "provider_family", "role", "interval", "session")
        ):
            previous = {}
            latest = {}
        observed_window = {key: value for key, value in snapshot.items() if key != "rows"}
        if previous and str(previous.get("adjustment_basis") or "") != str(snapshot.get("adjustment_basis") or ""):
            return {
                "schema_version": snapshot.get("schema_version") or "",
                "status": "BLOCK",
                "classification": "QUERY_WINDOW_ADJUSTMENT_CONTRACT_MISMATCH",
                "scope_key": str(latest.get("scope_key") or ""),
                "blocking_event_hash": str(latest.get("blocking_event_hash") or ""),
                "current": {key: value for key, value in previous.items() if key != "rows"},
                "observed_window": observed_window,
                "observation_scope": clean_observation_scope,
                "blockers": ["query_window_adjustment_basis_changed"],
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        if previous:
            merged_rows = {
                str(row.get("date") or ""): row
                for row in previous.get("rows") or []
                if str(row.get("date") or "")
            }
            merged_rows.update({
                str(row.get("date") or ""): row
                for row in snapshot.get("rows") or []
                if str(row.get("date") or "")
            })
            snapshot = build_market_data_snapshot(
                symbol=symbol,
                provider=provider,
                rows=[merged_rows[key] for key in sorted(merged_rows)],
                interval=stock_cache_interval(interval),
                session=clean_stock_session(session),
                role=clean_role,
                adjustment_basis=adjustment_basis or infer_adjustment_basis(provider),
                corporate_actions_hash=corporate_actions_hash or str(previous.get("corporate_actions_hash") or ""),
                completed_only=True,
                through_date=through_date,
                lineage_id=dataset_lineage_id,
            )
            if str(snapshot.get("snapshot_hash") or "") == str(previous.get("snapshot_hash") or ""):
                unresolved_block = bool(str(latest.get("blocking_event_hash") or ""))
                window_unchanged = (
                    str(observed_window.get("snapshot_hash") or "")
                    == str(previous.get("snapshot_hash") or "")
                )
                return {
                    "schema_version": snapshot.get("schema_version") or "",
                    "status": "BLOCK" if unresolved_block else ("PASS" if window_unchanged else "REVIEW"),
                    "classification": "WINDOW_UNCHANGED" if window_unchanged else "WINDOW_SUBSET_IGNORED",
                    "scope_key": str(latest.get("scope_key") or ""),
                    "blocking_event_hash": str(latest.get("blocking_event_hash") or ""),
                    "current": {key: value for key, value in previous.items() if key != "rows"},
                    "observed_window": observed_window,
                    "observation_scope": clean_observation_scope,
                    "merged_history_row_count": int(snapshot.get("row_count") or 0),
                    "blockers": ["prior_unresolved_historical_revision"]
                    if unresolved_block else [],
                    "research_only": True,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
        result = MARKET_DATA_REVISION_LEDGER.record_snapshot(snapshot)
        return {
            **result,
            "observation_scope": clean_observation_scope,
            "observed_window": observed_window,
            "merged_history_row_count": int(snapshot.get("row_count") or 0),
        }
    return {
        **MARKET_DATA_REVISION_LEDGER.record_snapshot(snapshot),
        "observation_scope": clean_observation_scope,
    }


def attest_stock_backtest_rows(
    *,
    symbol: str,
    provider: str,
    rows: list[dict[str, Any]],
    adjustment_basis: str,
    corporate_actions_hash: str,
    dataset_lineage_id: str,
) -> dict[str, Any]:
    clean_lineage_id = str(dataset_lineage_id or "").strip()
    if not clean_lineage_id:
        return {
            "schema_version": "backtest-dataset-attestation-v1",
            "status": "BLOCK",
            "classification": "DATASET_LINEAGE_REQUIRED",
            "blockers": ["backtest_dataset_lineage_id_required"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    through_date = max((str(row.get("date") or "")[:10] for row in rows), default="")
    if RUNTIME_READ_ONLY:
        snapshot = build_market_data_snapshot(
            symbol=symbol,
            provider=provider,
            rows=rows,
            interval="1d",
            session="regular",
            role="BACKTEST_DATASET",
            adjustment_basis=adjustment_basis,
            corporate_actions_hash=corporate_actions_hash,
            completed_only=True,
            through_date=through_date,
            lineage_id=clean_lineage_id,
        )
        return _read_only_stock_snapshot_attestation(snapshot)
    return record_stock_revision_snapshot(
        symbol=symbol,
        provider=provider,
        rows=rows,
        interval="1d",
        session="regular",
        role="BACKTEST_DATASET",
        adjustment_basis=adjustment_basis,
        corporate_actions_hash=corporate_actions_hash,
        through_date=through_date,
        dataset_lineage_id=clean_lineage_id,
    )


def _read_cached_provider_daily_rows(symbol: str, provider_family: str) -> list[dict[str, Any]]:
    if not STOCK_CANDLE_CACHE_DB.exists():
        return []
    meta = stock_meta(symbol)
    family = str(provider_family or "").strip().lower()
    conn = ensure_stock_candle_cache_db()
    try:
        rows = conn.execute(
            """
            SELECT ts_ms AS ts, trading_date AS date, open, high, low, close,
                   volume, complete, row_session AS session, source, fetched_at,
                   query_session
            FROM stock_candles
            WHERE symbol = ? AND interval IN ('1d', '1dutc')
              AND LOWER(source) LIKE ?
            ORDER BY trading_date, fetched_at,
                     CASE query_session WHEN 'regular' THEN 2 WHEN 'all' THEN 1 ELSE 0 END
            """,
            (meta["symbol"], f"%{family}%"),
        ).fetchall()
    finally:
        conn.close()
    by_date: dict[str, dict[str, Any]] = {}
    for raw in rows:
        item = dict(raw)
        if not candle_is_complete(item, default_if_missing=False):
            continue
        by_date[str(item.get("date") or "")] = item
    return [by_date[key] for key in sorted(by_date) if key]


def _latest_provider_observation(symbol: str, provider: str) -> tuple[dict[str, Any], dict[str, Any]]:
    latest = MARKET_DATA_REVISION_LEDGER.latest_snapshot(
        symbol=symbol,
        provider=provider,
        role="PROVIDER_OBSERVATION",
        interval="1d",
        session="regular",
    )
    snapshot = dict(latest.get("snapshot") or {})
    if int(snapshot.get("row_count") or 0) <= 0 or not snapshot.get("rows"):
        return {}, {}
    revision = {
        "schema_version": snapshot.get("schema_version") or "",
        "status": str(latest.get("state_status") or "REVIEW"),
        "classification": "LATEST_RECORDED_SNAPSHOT",
        "scope_key": str(latest.get("scope_key") or ""),
        "blocking_event_hash": str(latest.get("blocking_event_hash") or ""),
        "updated_at": int(latest.get("updated_at") or 0),
        "current": {key: value for key, value in snapshot.items() if key != "rows"},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    return snapshot, revision


def attest_stock_candle_cache(symbol: str, interval: str = "1d", session: str = "regular") -> dict[str, Any]:
    normalized_interval = stock_cache_interval(interval)
    clean_session = clean_stock_session(session)
    if normalized_interval not in {"1d", "1dutc"} or not STOCK_CANDLE_CACHE_DB.exists():
        return {}
    meta = stock_meta(symbol)
    conn = ensure_stock_candle_cache_db()
    try:
        rows = [dict(row) for row in conn.execute(
            """
            SELECT ts_ms AS ts, trading_date AS date, open, high, low, close,
                   volume, complete, row_session AS session, source, fetched_at
            FROM stock_candles
            WHERE symbol = ? AND interval = ? AND query_session = ?
            ORDER BY trading_date
            """,
            (meta["symbol"], normalized_interval, clean_session),
        ).fetchall()]
    finally:
        conn.close()
    source_lineage = sorted({str(row.get("source") or "") for row in rows if row.get("source")})
    basis, _coverage = _series_adjustment_contract(source_lineage)
    corporate_actions_hash = str(
        (CORPORATE_ACTION_LEDGER.latest_evidence(meta["symbol"], normalized_interval, clean_session) or {}).get(
            "corporate_actions_hash"
        ) or ""
    )
    if RUNTIME_READ_ONLY:
        snapshot = build_market_data_snapshot(
            symbol=meta["symbol"],
            provider="accepted_stock_cache",
            rows=rows,
            interval=normalized_interval,
            session=clean_session,
            role="ACCEPTED_CACHE",
            adjustment_basis=basis,
            corporate_actions_hash=corporate_actions_hash,
            completed_only=True,
        )
        return _read_only_stock_snapshot_attestation(snapshot)
    return record_stock_revision_snapshot(
        symbol=meta["symbol"],
        provider="accepted_stock_cache",
        rows=rows,
        interval=normalized_interval,
        session=clean_session,
        role="ACCEPTED_CACHE",
        adjustment_basis=basis,
        corporate_actions_hash=corporate_actions_hash,
    )


def audit_stock_daily_sources(symbol: str, limit: int = 1600) -> dict[str, Any]:
    clean_symbol = stock_meta(symbol)["symbol"]
    primary, primary_revision = _latest_provider_observation(clean_symbol, "futu")
    secondary_payload = fetch_yahoo_stock_candles(clean_symbol, limit, "1d", "5y")
    secondary_rows = list(secondary_payload.get("rows") or [])
    secondary_cached = False
    secondary: dict[str, Any] = {}
    secondary_revision: dict[str, Any] = {}
    if secondary_rows:
        corporate_actions_hash = str(
            build_adjustment_evidence(
                symbol=clean_symbol,
                rows=secondary_rows,
                source="yahoo_adjusted",
                adjustment_basis=str(secondary_payload.get("adjustment_basis") or "FORWARD_ADJUSTED_TOTAL_RETURN"),
                corporate_actions=list(secondary_payload.get("corporate_actions") or []),
                corporate_action_coverage=str(secondary_payload.get("corporate_action_coverage") or ""),
            ).get("corporate_actions_hash") or ""
        )
        secondary_window = build_market_data_snapshot(
            symbol=clean_symbol,
            provider="yahoo_adjusted",
            rows=secondary_rows,
            interval="1d",
            session="regular",
            role="PROVIDER_OBSERVATION",
            adjustment_basis=str(secondary_payload.get("adjustment_basis") or "FORWARD_ADJUSTED_TOTAL_RETURN"),
            corporate_actions_hash=corporate_actions_hash,
        )
        if int(secondary_window.get("row_count") or 0) <= 0:
            return {
                "schema_version": "stock-daily-source-audit-v1",
                "symbol": clean_symbol,
                "status": "BLOCK",
                "blockers": ["independent_yahoo_completed_rows_missing"],
                "secondary_error": str(secondary_payload.get("error") or ""),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        secondary_revision = record_stock_revision_snapshot(
            symbol=clean_symbol,
            provider="yahoo_adjusted",
            rows=secondary_rows,
            interval="1d",
            session="regular",
            adjustment_basis=str(secondary_payload.get("adjustment_basis") or "FORWARD_ADJUSTED_TOTAL_RETURN"),
            corporate_actions_hash=corporate_actions_hash,
            observation_scope="QUERY_WINDOW",
        )
        secondary, _latest_secondary_revision = _latest_provider_observation(clean_symbol, "yahoo")
        if str(secondary.get("provider_family") or "").lower() != "yahoo":
            secondary = secondary_window
    else:
        secondary, secondary_revision = _latest_provider_observation(clean_symbol, "yahoo")
        secondary_cached = bool(secondary)
    if not primary or not secondary:
        blockers = []
        if not primary:
            blockers.append("futu_provider_vintage_missing")
        if not secondary:
            blockers.append("independent_yahoo_vintage_missing")
        return {
            "schema_version": "stock-daily-source-audit-v1",
            "symbol": clean_symbol,
            "status": "BLOCK",
            "blockers": blockers,
            "secondary_error": str(secondary_payload.get("error") or ""),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    evidence = build_cross_source_evidence(primary, secondary, required_overlap=120)
    evidence = MARKET_DATA_REVISION_LEDGER.record_cross_source(evidence)
    statuses = {
        str(primary_revision.get("status") or "REVIEW"),
        str(secondary_revision.get("status") or "REVIEW"),
        str(evidence.get("status") or "REVIEW"),
    }
    return {
        "schema_version": "stock-daily-source-audit-v1",
        "symbol": clean_symbol,
        "status": "BLOCK" if "BLOCK" in statuses else "REVIEW" if "REVIEW" in statuses else "PASS",
        "primary_revision": primary_revision,
        "secondary_revision": secondary_revision,
        "cross_source": evidence,
        "primary_observation_source": "revision_ledger",
        "secondary_observation_source": "revision_ledger" if secondary_cached else "provider_fetch",
        "secondary_cached": secondary_cached,
        "secondary_error": str(secondary_payload.get("error") or ""),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def stock_data_revision_summary(symbol: str = "") -> dict[str, Any]:
    return MARKET_DATA_REVISION_LEDGER.summary(symbol)


def stock_external_provider_order() -> list[str]:
    providers: list[str] = []
    for item in STOCK_EXTERNAL_PROVIDER_ORDER or ["yahoo", "stooq"]:
        key = str(item).strip().lower()
        if key in {"yahoo", "stooq"} and key not in providers:
            providers.append(key)
    return providers or ["yahoo", "stooq"]


def fetch_stooq_stock_candles(symbol: str, limit: int, normalized_interval: str, clean_session: str) -> dict[str, Any]:
    if normalized_interval != "1d" or clean_session not in {"all", "regular"}:
        return {"ok": False, "rows": [], "source": "stooq", "error": "interval or session unsupported"}
    url = "https://stooq.com/q/d/l/?" + urllib.parse.urlencode({"s": stock_source_symbol(symbol), "i": "d"})
    rows: list[dict[str, Any]] = []
    captured_at_ms = now_ms()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Python-Quant-Exchange-Terminal/0.1"})
        with urllib.request.urlopen(request, timeout=STOCK_HISTORY_TIMEOUT) as response:
            content = response.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            close = pct(row.get("Close", "0"))
            if close <= 0:
                continue
            date_text = row.get("Date", "")
            try:
                local_date = datetime.strptime(date_text, "%Y-%m-%d").replace(
                    tzinfo=stock_timezone(symbol)
                )
                ts = int(local_date.timestamp() * 1000)
            except (TypeError, ValueError, OverflowError, OSError):
                continue
            rows.append({
                "ts": ts,
                "date": date_text,
                "open": pct(row.get("Open", close)) or close,
                "high": pct(row.get("High", close)) or close,
                "low": pct(row.get("Low", close)) or close,
                "close": close,
                "volume": pct(row.get("Volume", "0")),
                "source": "stooq",
                "session": "regular",
                "complete": stock_candle_complete_at(
                    symbol,
                    normalized_interval,
                    ts,
                    date_text,
                    at_ms=captured_at_ms,
                ),
            })
    except Exception as exc:
        return {"ok": False, "rows": [], "source": "stooq", "error": str(exc)}
    return {
        "ok": bool(rows),
        "rows": rows[-max(int(limit) * 3, int(limit)):],
        "source": "stooq",
        "adjustment_basis": "STOOQ_CLOSE_UNVERIFIED",
        "corporate_action_coverage": "UNKNOWN",
        "corporate_actions": [],
    }


def fetch_yahoo_stock_candles(symbol: str, limit: int, normalized_interval: str, yahoo_range: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    captured_at_ms = now_ms()
    try:
        yahoo_url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(yahoo_stock_symbol(symbol)) + "?" + urllib.parse.urlencode({
            "range": yahoo_range,
            "interval": normalized_interval,
            "includePrePost": "true",
            "events": "div,splits",
        })
        request = urllib.request.Request(yahoo_url, headers={"User-Agent": "Mozilla/5.0 HakimiTrade/2.0"})
        with urllib.request.urlopen(request, timeout=STOCK_HISTORY_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        result = ((payload.get("chart") or {}).get("result") or [{}])[0]
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        adjusted_closes = (
            (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
        )
        daily_adjusted = normalized_interval == "1d" and bool(adjusted_closes)
        for index, ts in enumerate(timestamps):
            close = closes[index] if index < len(closes) else None
            if close is None:
                continue
            ts_ms = int(ts) * 1000
            open_price = opens[index] if index < len(opens) and opens[index] is not None else close
            high_price = highs[index] if index < len(highs) and highs[index] is not None else close
            low_price = lows[index] if index < len(lows) and lows[index] is not None else close
            volume = volumes[index] if index < len(volumes) and volumes[index] is not None else 0
            adjusted_close = adjusted_closes[index] if index < len(adjusted_closes) else None
            row_adjusted = bool(
                daily_adjusted
                and adjusted_close is not None
                and float(close) > 0
                and float(adjusted_close) > 0
            )
            adjustment_factor = (
                float(adjusted_close) / float(close)
                if row_adjusted
                else 1.0
            )
            row_source = "yahoo_adjusted" if row_adjusted else "yahoo"
            normalized_open = float(open_price) * adjustment_factor
            normalized_high = float(high_price) * adjustment_factor
            normalized_low = float(low_price) * adjustment_factor
            normalized_close = float(close) * adjustment_factor
            normalized_volume = float(volume)
            if row_adjusted:
                normalized_open = _canonical_adjusted_price(normalized_open)
                normalized_high = _canonical_adjusted_price(normalized_high)
                normalized_low = _canonical_adjusted_price(normalized_low)
                normalized_close = _canonical_adjusted_price(float(adjusted_close))
                normalized_volume = float(volume) / adjustment_factor
            rows.append({
                "ts": ts_ms,
                "date": time.strftime("%Y-%m-%d", time.gmtime(int(ts))),
                "open": normalized_open,
                "high": normalized_high,
                "low": normalized_low,
                "close": normalized_close,
                "volume": normalized_volume,
                "source": row_source,
                "session": "regular" if normalized_interval == "1d" else stock_session_from_ts(ts_ms, symbol),
                "complete": stock_candle_complete_at(
                    symbol,
                    normalized_interval,
                    ts_ms,
                    time.strftime("%Y-%m-%d", time.gmtime(int(ts))),
                    at_ms=captured_at_ms,
                ),
            })
    except Exception as exc:
        return {"ok": False, "rows": [], "source": "yahoo", "error": str(exc)}
    return {
        "ok": bool(rows),
        "rows": rows[-max(int(limit) * 3, int(limit)):],
        "source": "yahoo",
        "cache_source": "yahoo_adjusted" if normalized_interval == "1d" and rows and all(row.get("source") == "yahoo_adjusted" for row in rows) else "yahoo",
        "adjustment_basis": "FORWARD_ADJUSTED_TOTAL_RETURN" if normalized_interval == "1d" and rows and all(row.get("source") == "yahoo_adjusted" for row in rows) else "YAHOO_CHART_CLOSE_UNVERIFIED",
        "corporate_action_coverage": "EMBEDDED_PROVIDER_CONTRACT" if normalized_interval == "1d" and rows and all(row.get("source") == "yahoo_adjusted" for row in rows) else "PARTIAL_PROVIDER_EVENTS",
        "corporate_actions": parse_yahoo_corporate_actions(symbol, result if rows else {}),
    }


def stock_intraday_daily_row(symbol: str, limit: int, session: str = "all") -> dict[str, Any] | None:
    intraday = read_external_stock_candles(symbol, max(180, min(720, int(limit) * 4)), "1m", session)
    rows = list(intraday.get("rows") or [])
    if not rows:
        return None
    expected = stock_current_session_date(symbol)
    if not expected:
        return None
    day_rows = [
        row for row in rows
        if datetime.fromtimestamp(int(row.get("ts") or 0) / 1000, stock_timezone(symbol)).strftime("%Y-%m-%d") == expected
    ]
    if len(day_rows) < 3:
        return None
    close = float(day_rows[-1].get("close") or 0)
    if close <= 0:
        return None
    return {
        "ts": int(day_rows[0].get("ts") or latest_stock_candle_ts(day_rows)),
        "date": expected,
        "open": float(day_rows[0].get("open") or close),
        "high": max(float(row.get("high") or 0) for row in day_rows),
        "low": min(float(row.get("low") or close) for row in day_rows if float(row.get("low") or 0) > 0),
        "close": close,
        "volume": sum(float(row.get("volume") or 0) for row in day_rows),
        "source": f"{intraday.get('source', 'external')}_intraday_daily",
        "session": "regular",
        "complete": False,
        "provisional": True,
    }


def augment_stock_daily_with_intraday(payload: dict[str, Any], symbol: str, limit: int, interval: str, session: str) -> dict[str, Any]:
    normalized_interval = stock_cache_interval(interval)
    if normalized_interval not in {"1d", "1dutc"} or not stock_payload_needs_session_refresh(payload, interval, symbol):
        return payload
    row = stock_intraday_daily_row(symbol, limit, session)
    if not row:
        return payload
    rows = list(payload.get("rows") or [])
    rows = [item for item in rows if str(item.get("date") or "") != row["date"]]
    rows.append(row)
    rows.sort(key=lambda item: int(item.get("ts") or 0))
    return with_stock_freshness({
        **payload,
        "rows": rows[-limit:],
        "source": row["source"],
        "origin_source": payload.get("origin_source") or payload.get("source"),
        "provisional_daily": True,
        "note": "daily candle includes intraday provisional row",
    }, interval, symbol)


def read_external_stock_candles(symbol: str, limit: int, interval: str, session: str) -> dict[str, Any]:
    text = (symbol or "AAPL").upper()
    meta = stock_meta(text)
    normalized_interval, yahoo_range = normalize_stock_interval(interval)
    clean_session = clean_stock_session(session)
    failure_key = f"{meta['symbol']}|{normalized_interval}|{clean_session}|{','.join(stock_external_provider_order())}"
    cached_failure = STOCK_EXTERNAL_FAILURE_CACHE.get(failure_key) or {}
    if cached_failure and now_ms() - int(cached_failure.get("time") or 0) < 60_000:
        return {
            "ok": False,
            "rows": [],
            "source": "external",
            "errors": list(cached_failure.get("errors") or []),
            "cached_failure": True,
            "cache_age_ms": now_ms() - int(cached_failure.get("time") or 0),
        }
    errors: list[dict[str, Any]] = []
    for provider in stock_external_provider_order():
        scope = f"{meta['symbol']}|{normalized_interval}|{clean_session}"
        allowed, retry_after_ms = provider_call_allowed(provider, "history", scope)
        if not allowed:
            errors.append({"provider": provider, "error": "provider cooldown", "retry_after_ms": retry_after_ms})
            continue
        started = time.perf_counter()
        result = fetch_yahoo_stock_candles(text, limit, normalized_interval, yahoo_range) if provider == "yahoo" else fetch_stooq_stock_candles(text, limit, normalized_interval, clean_session)
        rows = list(result.get("rows") or [])
        interval_label = normalized_interval
        if rows and (interval or "").lower() == "4h" and normalized_interval == "60m":
            rows = aggregate_stock_rows(rows, 4 * 60 * 60 * 1000)
            interval_label = "4h"
        rows = filter_stock_rows_by_session(rows, clean_session)
        record_provider_call(
            provider,
            "history",
            success=bool(rows),
            latency_ms=(time.perf_counter() - started) * 1000,
            error=str(result.get("error") or "no rows for requested session") if not rows else "",
            scope=scope,
        )
        if rows:
            session_counts: dict[str, int] = {"pre": 0, "regular": 0, "post": 0, "overnight": 0}
            for row in rows:
                if row.get("session") in session_counts:
                    session_counts[row["session"]] += 1
            payload = with_stock_freshness({
                "ok": True,
                "symbol": meta["symbol"],
                "source": provider,
                "interval": interval_label,
                "session": clean_session,
                "session_label": stock_session_label(clean_session),
                "session_counts": session_counts,
                "rows": rows[-limit:],
                "adjustment_basis": result.get("adjustment_basis") or infer_adjustment_basis(provider),
                "corporate_action_coverage": result.get("corporate_action_coverage") or "UNKNOWN",
                "corporate_actions": list(result.get("corporate_actions") or []),
                "cache_source": result.get("cache_source") or provider,
                "provider_observation_scope": "QUERY_WINDOW",
                "provider_observation_window": {
                    "requested_limit": int(limit),
                    "provider_rows": len(rows),
                    "returned_rows": len(rows[-limit:]),
                },
                "updated_at": now_ms(),
            }, interval, text)
            STOCK_EXTERNAL_FAILURE_CACHE.pop(failure_key, None)
            payload = augment_stock_daily_with_intraday(payload, text, limit, interval, clean_session)
            return enrich_stock_series_contract(payload, text, interval_label, clean_session)
        errors.append({"provider": provider, "error": result.get("error") or "no rows"})
    STOCK_EXTERNAL_FAILURE_CACHE[failure_key] = {"time": now_ms(), "errors": errors}
    return {"ok": False, "rows": [], "source": "external", "errors": errors}
