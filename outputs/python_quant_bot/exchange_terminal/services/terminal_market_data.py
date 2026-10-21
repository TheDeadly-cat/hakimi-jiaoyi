"""Read existing terminal daily caches without refreshing, repairing or granting access.

One snapshot uses one database, interval, session and provider group. Provider
completion flags are retained as evidence, not external authentication. These
snapshots belong to the original terminal research engine, not the narrower
dev8 US-equity importer (which requires separate raw-price/source declarations).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
from typing import Callable


MAX_ROWS = 5000
MAX_SYMBOLS = 1000
_SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,14}(?:[.-][A-Z0-9]{1,12}){0,2}\Z")
_CRYPTO = re.compile(r"[A-Z][A-Z0-9]{0,14}-(?:USDT|USDC|USD|BTC|ETH)(?:-SWAP)?\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_BASE_FIELDS = ("symbol", "trading_date", "ts_ms", "open", "high", "low", "close", "volume", "source")
_PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}


class _Unavailable(RuntimeError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _symbol(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("terminal_market_symbol_invalid")
    clean = value.strip().upper()
    if not _SYMBOL.fullmatch(clean):
        raise ValueError("terminal_market_symbol_invalid")
    return clean


def _asset_class(symbol):
    if _CRYPTO.fullmatch(symbol):
        return "CRYPTO"
    if symbol.startswith("HK."):
        return "HK_EQUITY"
    # A ticker alone is not proof of a US listing, exchange or instrument type.
    return "EQUITY"


def _path(value):
    path = Path(os.path.abspath(os.path.expanduser(str(value))))
    if str(path).startswith("\\\\"):
        raise _Unavailable("REMOTE_DATABASE_PATH_NOT_SUPPORTED")
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise _Unavailable("DATABASE_LINK_REJECTED")
    return path.resolve()


def _state(path):
    path = _path(path)
    if not path.is_file():
        raise _Unavailable("DATABASE_MISSING")
    result = []
    for suffix in ("", "-wal", "-journal"):
        item = _path(str(path) + suffix)
        try:
            info = item.stat()
        except FileNotFoundError:
            result.append(None)
            continue
        if not stat.S_ISREG(info.st_mode):
            raise _Unavailable("DATABASE_NOT_REGULAR_FILE")
        if suffix and info.st_size:
            raise _Unavailable("DATABASE_PENDING_JOURNAL")
        result.append((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return tuple(result)


def _file_identity(path, reference):
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return {"reference": reference, "sha256": value.hexdigest(), "bytes": path.stat().st_size}


@contextmanager
def _read_database(path, reference):
    before = _state(path)
    identity = _file_identity(path, reference)
    connection = None
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        # Bound malformed/corrupt database query work as well as returned rows.
        budget = [0]
        def progress():
            budget[0] += 1
            return int(budget[0] > 20000)
        connection.set_progress_handler(progress, 1000)
        yield connection, identity
        if _state(path) != before:
            raise _Unavailable("DATABASE_CHANGED_DURING_READ")
    finally:
        if connection is not None:
            connection.close()


def _completion(value):
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return value == 1
    if type(value) is str:
        value = value.strip().lower()
        if value in {"1", "true", "complete", "completed", "confirmed", "closed", "final"}:
            return True
        if value in {"0", "false", "incomplete", "partial", "provisional", "open"}:
            return False
    return None


def _basis(kind, source):
    provider = source.lower()
    if kind in {"btc", "crypto"}:
        return "PROVIDER_CRYPTO_PRICE" if "okx" in provider else "UNKNOWN"
    if "futu" in provider:
        return "FORWARD_ADJUSTED_QFQ"
    if "yahoo_adjusted" in provider:
        return "FORWARD_ADJUSTED_TOTAL_RETURN"
    if "yahoo" in provider:
        return "YAHOO_CHART_CLOSE_UNVERIFIED"
    if "stooq" in provider:
        return "STOOQ_CLOSE_UNVERIFIED"
    return "UNKNOWN"


def _source_rank(source):
    value = source.lower()
    return next((rank for rank, text in enumerate(("futu", "yahoo_adjusted", "yahoo", "stooq", "okx")) if text in value), 9)


class TerminalMarketReader:
    def __init__(self, runtime_dir, *, btc_paths=None, now_ms: Callable[[], int] | None = None):
        self.runtime_dir = _path(runtime_dir)
        self.btc_paths = tuple(_path(path) for path in (btc_paths if btc_paths is not None else (
            self.runtime_dir / "jiaoyiguowangshuju" / "btc_daily_prices.sqlite",
            self.runtime_dir / "btc_daily_prices_cache.sqlite",
        )))
        if len(self.btc_paths) > 8 or len(set(self.btc_paths)) != len(self.btc_paths):
            raise ValueError("terminal_market_btc_paths_invalid")
        # Accepted for caller consistency, but current time is never data identity.
        self.now_ms = now_ms

    def _sources(self, symbol=None):
        if symbol is None or symbol == "BTC-USDT":
            for index, path in enumerate(self.btc_paths):
                yield {"kind": "btc", "path": path, "reference": self._reference(path),
                       "table": "btc_daily_prices", "completion": "confirmed", "priority": index}
        if symbol is None or _asset_class(symbol) == "CRYPTO":
            path = self.runtime_dir / "market_history_cache.sqlite"
            yield {"kind": "crypto", "path": path, "reference": self._reference(path),
                   "table": "market_daily_candles", "completion": "complete", "priority": 20}
        if symbol is None or _asset_class(symbol) != "CRYPTO":
            path = self.runtime_dir / "stock_candles_cache.sqlite"
            yield {"kind": "stock", "path": path, "reference": self._reference(path),
                   "table": "stock_candles", "completion": "complete", "priority": 30}

    def _reference(self, path):
        if path.is_relative_to(self.runtime_dir):
            return "runtime/" + path.relative_to(self.runtime_dir).as_posix()
        return "configured-btc/" + sha256(str(path).encode()).hexdigest()[:20] + "/" + path.name

    @staticmethod
    def _schema(connection, source):
        columns = {row[1] for row in connection.execute("PRAGMA table_info(" + source["table"] + ")")}
        if source["completion"] not in columns:
            raise _Unavailable("COMPLETION_EVIDENCE_COLUMN_MISSING")
        required = set(_BASE_FIELDS) | {source["completion"]}
        if source["kind"] == "stock":
            required |= {"interval", "query_session"}
        if not required <= columns:
            raise _Unavailable("DATABASE_SCHEMA_UNSUPPORTED")
        return columns

    @staticmethod
    def _where(source, symbol=None, group=None):
        parts, params = [], []
        if symbol is not None:
            parts.append("symbol = ?")
            params.append(symbol)
        if source["kind"] == "btc":
            parts.append("symbol = 'BTC-USDT'")
        if source["kind"] == "stock":
            parts.extend(["interval IN ('1d','1dutc')", "query_session IN ('regular','all')"])
        if group:
            parts.append("source = ?")
            params.append(group["source"])
            if source["kind"] == "stock":
                parts.extend(["interval = ?", "query_session = ?"])
                params.extend([group["interval"], group["session"]])
        return (" WHERE " + " AND ".join(parts) if parts else ""), params

    def _groups(self, source, symbol=None):
        with _read_database(source["path"], source["reference"]) as (connection, identity):
            self._schema(connection, source)
            where, params = self._where(source, symbol)
            dimensions = "symbol,source,interval,query_session" if source["kind"] == "stock" else "symbol,source"
            # GROUP BY uses only names from the fixed schemas above, not caller text.
            sql = ("SELECT " + dimensions + ", COUNT(*) AS row_count, MIN(trading_date) AS first_date, "
                   "MAX(trading_date) AS last_date, SUM(CASE WHEN " + source["completion"] + " = 1 THEN 1 ELSE 0 END) AS completed_count "
                   "FROM " + source["table"] + where + " GROUP BY " + dimensions + " ORDER BY " + dimensions + " LIMIT ?")
            rows = [dict(row) for row in connection.execute(sql, [*params, MAX_SYMBOLS + 1])]
        if len(rows) > MAX_SYMBOLS:
            raise _Unavailable("CATALOG_GROUP_LIMIT_EXCEEDED")
        groups = []
        for row in rows:
            try:
                clean = _symbol(row["symbol"])
            except ValueError:
                continue
            if source["kind"] != "stock" and _asset_class(clean) != "CRYPTO":
                continue
            if source["kind"] == "stock" and _asset_class(clean) == "CRYPTO":
                continue
            provider = row["source"] if type(row["source"]) is str else ""
            if not provider.strip() or len(provider) > 200:
                raise _Unavailable("SOURCE_LINEAGE_INVALID")
            groups.append({**row, "symbol": clean, "source": provider,
                           "interval": row.get("interval", "1d"),
                           "session": row.get("query_session", "utc"), "file_identity": identity})
        return groups

    @staticmethod
    def _rank(source, group):
        return (source["priority"], group["session"] != "regular" if source["kind"] == "stock" else False,
                group["interval"] != "1d", not bool(group["completed_count"]),
                _source_rank(group["source"]), -int(group["completed_count"]), group["source"])

    @staticmethod
    def _selection(source, group, limit):
        return {"storage": source["reference"], "table": source["table"], "symbol": group["symbol"],
                "provider": group["source"], "interval": group["interval"], "session": group["session"], "limit": limit}

    def _source_view(self, source, group):
        selection = self._selection(source, group, 2000)
        return {"source_id": "terminal-cache:" + _digest({k: v for k, v in selection.items() if k != "limit"}),
                "provider": group["source"], "session": group["session"], "interval": group["interval"],
                "price_basis": _basis(source["kind"], group["source"]),
                "completed_count": group["completed_count"], "source_reference": source["reference"],
                "coverage": {"first_date": group["first_date"], "last_date": group["last_date"],
                             "row_count": group["row_count"]},
                "available": bool(group["completed_count"]), "source_authenticated": False}

    def _discover(self, symbol, *, stop_on_default_error=False):
        candidates, diagnostics = [], []
        default_candidates, default_error = None, None
        for source in self._sources(symbol):
            try:
                groups = self._groups(source, symbol)
            except (_Unavailable, sqlite3.Error, OSError) as error:
                diagnostic = self._diagnostic(source, error)
                diagnostics.append(diagnostic)
                if default_candidates is None and default_error is None and diagnostic["code"] != "DATABASE_MISSING":
                    default_error = diagnostic
                    if stop_on_default_error:
                        break
                continue
            candidates.extend((self._rank(source, group), source, group) for group in groups)
            if groups and source["kind"] == "btc" and default_candidates is None and default_error is None:
                # Preserve the original BTC-primary default while still listing
                # other single-source choices for an explicit user selection.
                default_candidates = list(candidates)
        candidates.sort(key=lambda item: item[0])
        return candidates, diagnostics, default_candidates, default_error

    def sources(self, symbol):
        candidates, _, _, _ = self._discover(_symbol(symbol))
        return [self._source_view(source, group) for _, source, group in candidates]

    def catalog(self):
        choices, diagnostics = {}, []
        for source in self._sources():
            try:
                groups = self._groups(source)
            except (_Unavailable, sqlite3.Error, OSError) as error:
                diagnostics.append(self._diagnostic(source, error))
                continue
            for group in groups:
                rank = self._rank(source, group)
                if group["symbol"] not in choices or rank < choices[group["symbol"]][0]:
                    choices[group["symbol"]] = rank, source, group
        items = []
        for symbol, (_, source, group) in sorted(choices.items()):
            selection = self._selection(source, group, 2000)
            items.append({"symbol": symbol, "asset_class": _asset_class(symbol), "available": bool(group["completed_count"]),
                          "source_id": "terminal-cache:" + _digest({k: v for k, v in selection.items() if k != "limit"}),
                          "source": group["source"], "source_reference": source["reference"],
                          "price_basis": _basis(source["kind"], group["source"]), "interval": group["interval"],
                          "session": group["session"], "row_count": group["row_count"],
                          "completed_count": group["completed_count"], "first_date": group["first_date"],
                          "last_date": group["last_date"], "status": "REVIEW", "source_authenticated": False})
        return {"items": items, "diagnostics": diagnostics, "source": "LOCAL_TERMINAL_CACHE", **_PERMISSIONS}

    def list_symbols(self):
        return [row["symbol"] for row in self.catalog()["items"]]

    @staticmethod
    def _diagnostic(source, error):
        code = str(error) if isinstance(error, _Unavailable) else "DATABASE_READ_FAILED"
        return {"reference": source["reference"], "status": "UNAVAILABLE", "code": code}

    @staticmethod
    def _blocked(symbol, limit, blockers, diagnostics=None, *, available_sources=None, requested_source_id=None):
        quality = {"status": "BLOCK", "blockers": blockers, "warnings": [], "source_authenticated": False,
                   "core_us_equity_import_allowed": False, "research_admission": "NOT_GRANTED", **_PERMISSIONS}
        body = {"symbol": symbol, "bar": "1D", "source_id": None, "rows": [],
                "meta": {"asset_class": _asset_class(symbol), "requested_limit": limit,
                         "diagnostics": diagnostics or []}, "quality": quality, "excluded_incomplete_count": 0}
        if requested_source_id is not None:
            body["meta"]["requested_source_id"] = requested_source_id
        return {**body, "digest": _digest(body), "available_sources": available_sources or [],
                "source_diagnostics": diagnostics or []}

    def __call__(self, symbol, limit=2000, source_id=None):
        symbol = _symbol(symbol)
        if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
            raise ValueError("terminal_market_limit_must_be_1_to_5000")
        if source_id is not None and (type(source_id) is not str or not re.fullmatch(r"terminal-cache:[a-f0-9]{64}", source_id)):
            return self._blocked(symbol, limit, ["SOURCE_SELECTION_INVALID"])
        candidates, diagnostics, default_candidates, default_error = self._discover(symbol, stop_on_default_error=source_id is None)
        available = [self._source_view(source, group) for _, source, group in candidates]
        if source_id is not None:
            candidates = [item for item in candidates if self._source_view(item[1], item[2])["source_id"] == source_id]
            if not candidates:
                return self._blocked(symbol, limit, ["REQUESTED_SOURCE_UNAVAILABLE"], diagnostics,
                                     available_sources=available, requested_source_id=source_id)
        elif default_error is not None:
            # Do not silently hide a pending primary DB behind an older cache.
            return self._blocked(symbol, limit, [default_error["code"]], diagnostics, available_sources=available)
        elif default_candidates is not None:
            candidates = default_candidates
        if not candidates:
            return self._blocked(symbol, limit, ["LOCAL_DAILY_HISTORY_UNAVAILABLE"], diagnostics, available_sources=available)
        _, source, group = min(candidates, key=lambda item: item[0])
        selection = self._selection(source, group, limit)
        try:
            with _read_database(source["path"], source["reference"]) as (connection, identity):
                if identity != group["file_identity"]:
                    raise _Unavailable("DATABASE_CHANGED_BETWEEN_SELECTION_AND_READ")
                columns = self._schema(connection, source)
                selected = ["trading_date", "ts_ms", "open", "high", "low", "close", "volume", "source", source["completion"]]
                if "fetched_at" in columns:
                    selected.append("fetched_at")
                where, params = self._where(source, symbol, group)
                sql = "SELECT " + ",".join(selected) + " FROM " + source["table"] + where + " ORDER BY ts_ms DESC LIMIT ?"
                raw = [dict(row) for row in connection.execute(sql, [*params, limit])]
        except (_Unavailable, sqlite3.Error, OSError) as error:
            diagnostic = self._diagnostic(source, error)
            return self._blocked(symbol, limit, [diagnostic["code"]], [diagnostic],
                                 available_sources=available, requested_source_id=source_id)
        rows, invalid, unknown, excluded = [], 0, 0, 0
        for row in reversed(raw):
            complete = _completion(row.get(source["completion"]))
            if complete is not True:
                excluded += 1
                unknown += int(complete is None)
                continue
            day, stamp = row["trading_date"], row["ts_ms"]
            values = [row[key] for key in ("open", "high", "low", "close", "volume")]
            try:
                if type(day) is not str or not _DATE.fullmatch(day) or date.fromisoformat(day).isoformat() != day:
                    raise ValueError()
                if type(stamp) is not int or stamp <= 0:
                    raise ValueError()
                if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
                    raise ValueError()
                opening, high, low, close, volume = values
                if min(values[:4]) <= 0 or volume < 0 or high < max(opening, close) or low > min(opening, close) or low > high:
                    raise ValueError()
                parsed = {"date": day, "ts_ms": stamp, **dict(zip(("open", "high", "low", "close", "volume"), values)),
                          "complete": True, "provisional": False, "source": group["source"]}
                if "fetched_at" in row:
                    if type(row["fetched_at"]) is not int or row["fetched_at"] < 0:
                        raise ValueError()
                    parsed["fetched_at"] = row["fetched_at"]
                rows.append(parsed)
            except (ValueError, OverflowError):
                invalid += 1
        blockers = []
        if invalid:
            blockers.append("INVALID_DAILY_ROWS_PRESENT")
        if len({row["date"] for row in rows}) != len(rows) or any(
                right["ts_ms"] <= left["ts_ms"] or right["date"] <= left["date"] for left, right in zip(rows, rows[1:])):
            blockers.append("DAILY_DATES_OR_TIMESTAMPS_NOT_UNIQUE_ORDERED")
        if not rows:
            blockers.append("NO_EXPLICITLY_COMPLETED_DAILY_ROWS")
        if not group["source"].strip():
            blockers.append("SOURCE_LINEAGE_MISSING")
        if any(token in group["source"].lower() for token in ("quick_preview", "preview_seed", "offline-seed", "offline_seed", "synthetic")):
            blockers.append("PREVIEW_OR_SYNTHETIC_SOURCE_NOT_MARKET_HISTORY")
        basis = _basis(source["kind"], group["source"])
        warnings = ["LOCAL_CACHE_NOT_EXTERNALLY_AUTHENTICATED", "COMPLETION_IS_RETAINED_PROVIDER_FLAG",
                    "FULL_CALENDAR_AND_SECURITY_IDENTITY_NOT_VERIFIED", "CORPORATE_ACTION_COVERAGE_NOT_VERIFIED"]
        if basis == "UNKNOWN" or basis.endswith("UNVERIFIED"):
            warnings.append("PRICE_BASIS_UNVERIFIED")
        if excluded:
            warnings.append("INCOMPLETE_OR_UNCONFIRMED_ROWS_EXCLUDED")
        meta = {"asset_class": _asset_class(symbol), "instrument_type": "UNKNOWN", "exchange": "UNKNOWN",
                "interval": group["interval"], "session": group["session"], "price_basis": basis,
                "source_lineage": [group["source"]], "origin_reference": source["reference"],
                "volume_unit": "UNKNOWN", "volume_basis": "ORIGINAL_PROVIDER_FIELD_UNVERIFIED",
                "file_identity": identity, "selection": selection, "requested_limit": limit,
                "loaded_row_count": len(raw), "returned_row_count": len(rows) if not blockers else 0,
                "invalid_row_count": invalid, "unknown_completion_count": unknown,
                "completion_evidence_field": source["completion"], "excluded_count_scope": "LATEST_REQUESTED_ROWS",
                "source_authentication": "NOT_EXTERNALLY_AUTHENTICATED", "diagnostics": []}
        quality = {"status": "BLOCK" if blockers else "REVIEW", "blockers": blockers, "warnings": warnings,
                   "source_authenticated": False, "research_admission": "NOT_GRANTED",
                   "core_us_equity_import_allowed": False,
                   "core_us_equity_import_blockers": ["EXPLICIT_RAW_PRICE_SECURITY_CALENDAR_AND_ACTION_MANIFEST_REQUIRED"],
                   **_PERMISSIONS}
        body = {"symbol": symbol, "bar": "1D", "source_id": "terminal-cache:" + _digest({k: v for k, v in selection.items() if k != "limit"}),
                "rows": rows if not blockers else [], "meta": meta, "quality": quality,
                "excluded_incomplete_count": excluded}
        # The selection menu and availability of other databases are not part
        # of the chosen snapshot. The chosen DB's byte identity still is.
        return {**body, "digest": _digest(body), "available_sources": available,
                "source_diagnostics": diagnostics}
