from __future__ import annotations

import json
import hashlib
import logging
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from hakimi_research.config import BotConfig

logger = logging.getLogger(__name__)


TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

OKX_COMPLETED_CANDLE_SCHEMA_VERSION = "okx-completed-candle-filter-v1"
OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION = "okx-candle-source-receipt-v1"
OKX_SPOT_VOLUME_UNIT = "base_currency"
_OKX_CANDLE_FIELDS = (
    "ts",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "volume_currency",
    "volume_quote",
    "confirm",
)
_OKX_CANDLE_ENDPOINTS = frozenset(
    {
        "/api/v5/market/candles",
        "/api/v5/market/history-candles",
    }
)
_OKX_REQUEST_FIELDS = frozenset({"instId", "bar", "limit", "after", "before"})


def _require_okx_spot_symbol(symbol: object) -> str:
    if type(symbol) is not str:
        raise ValueError("research_data_okx_spot_symbol_exact_str_required")
    parts = symbol.split("-")
    if (
        len(parts) != 2
        or any(
            not part
            or not part.isascii()
            or not part.isalnum()
            or part != part.upper()
            for part in parts
        )
    ):
        raise ValueError("research_data_okx_spot_symbol_required")
    return symbol


def parse_okx_completed_candle_rows(
    rows: list,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Parse exact OKX candle rows and exclude every uncompleted candle."""

    if type(rows) is not list:
        raise ValueError("research_data_okx_rows_exact_list_required")
    source_rows: list[list[str]] = []
    candles: list[dict[str, object]] = []
    rejected_uncompleted = 0
    for row in rows:
        if type(row) is not list or len(row) != len(_OKX_CANDLE_FIELDS):
            raise ValueError("research_data_okx_candle_exact_nine_field_row_required")
        if any(type(value) is not str for value in row):
            raise ValueError("research_data_okx_candle_exact_string_fields_required")
        if any(not value or value != value.strip() for value in row):
            raise ValueError("research_data_okx_candle_canonical_string_fields_required")
        exact_row = list(row)
        if not exact_row[0].isascii() or not exact_row[0].isdigit():
            raise ValueError("research_data_okx_candle_timestamp_invalid")
        source_rows.append(exact_row)
        confirm = exact_row[8]
        if confirm == "0":
            rejected_uncompleted += 1
            continue
        if confirm != "1":
            raise ValueError("research_data_okx_candle_confirm_invalid")
        try:
            candle = {
                "time": pd.to_datetime(int(exact_row[0]), unit="ms", utc=True),
                "open": float(exact_row[1]),
                "high": float(exact_row[2]),
                "low": float(exact_row[3]),
                "close": float(exact_row[4]),
                "volume": float(exact_row[5]),
            }
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("research_data_okx_candle_numeric_field_invalid") from exc
        candles.append(candle)

    source_rows_sha256 = hashlib.sha256(
        json.dumps(
            source_rows,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()
    receipt: dict[str, object] = {
        "schema_version": OKX_COMPLETED_CANDLE_SCHEMA_VERSION,
        "source_field_order": list(_OKX_CANDLE_FIELDS),
        "source_row_count": len(source_rows),
        "accepted_complete_row_count": len(candles),
        "rejected_uncompleted_row_count": rejected_uncompleted,
        "rejection_reasons": (
            ["OKX_CANDLE_UNCOMPLETED"] if rejected_uncompleted else []
        ),
        "complete_only": True,
        "volume_unit": OKX_SPOT_VOLUME_UNIT,
        "source_rows_sha256": source_rows_sha256,
    }
    if not candles:
        frame = pd.DataFrame(
            {
                column: pd.Series(dtype="float64")
                for column in ("open", "high", "low", "close", "volume")
            },
            index=pd.DatetimeIndex([], tz="UTC", name="time"),
        )
        return frame, receipt
    frame = pd.DataFrame(reversed(candles)).set_index("time").sort_index()
    return validate_market_data_frame(frame), receipt


def _canonical_utc_time(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip() or not value.endswith("Z"):
        raise ValueError(f"research_data_{label}_canonical_utc_required")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"research_data_{label}_canonical_utc_required") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"research_data_{label}_canonical_utc_required")
    return value


def _canonical_okx_request(
    endpoint: object,
    params: object,
) -> tuple[str, dict[str, str | int], str]:
    if type(endpoint) is not str or endpoint not in _OKX_CANDLE_ENDPOINTS:
        raise ValueError("research_data_okx_candle_endpoint_invalid")
    if type(params) is not dict:
        raise ValueError("research_data_okx_candle_params_exact_dict_required")
    if any(type(key) is not str for key in params):
        raise ValueError("research_data_okx_candle_param_key_exact_str_required")
    keys = set(params)
    if (
        not {"instId", "bar", "limit"}.issubset(keys)
        or not keys.issubset(_OKX_REQUEST_FIELDS)
        or {"after", "before"}.issubset(keys)
    ):
        raise ValueError("research_data_okx_candle_params_shape_invalid")
    symbol = _require_okx_spot_symbol(params["instId"])
    bar = params["bar"]
    if type(bar) is not str or bar not in _OKX_BAR_MAP.values():
        raise ValueError("research_data_okx_candle_bar_invalid")
    limit = params["limit"]
    if type(limit) is not int or limit <= 0 or limit > 300:
        raise ValueError("research_data_okx_candle_limit_invalid")
    canonical: dict[str, str | int] = {
        "instId": symbol,
        "bar": bar,
        "limit": limit,
    }
    for cursor in ("after", "before"):
        if cursor not in params:
            continue
        value = params[cursor]
        if type(value) is not int or value <= 0:
            raise ValueError("research_data_okx_candle_cursor_invalid")
        canonical[cursor] = value
    timeframe = next(
        key for key, value in _OKX_BAR_MAP.items() if value == bar
    )
    return endpoint, canonical, timeframe


def _reject_json_constant(_value: str) -> None:
    raise ValueError("research_data_okx_response_nonfinite_rejected")


def parse_okx_candle_response(
    raw_response: bytes,
    *,
    endpoint: str,
    params: dict[str, str | int],
    retrieved_at: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Bind an exact OKX response envelope to its completed-candle projection."""

    if type(raw_response) is not bytes or not raw_response:
        raise ValueError("research_data_okx_raw_response_exact_nonempty_bytes_required")
    if len(raw_response) > 8 * 1024 * 1024:
        raise ValueError("research_data_okx_raw_response_size_limit_exceeded")
    exact_endpoint, exact_params, timeframe = _canonical_okx_request(
        endpoint,
        params,
    )
    exact_retrieved_at = _canonical_utc_time(
        retrieved_at,
        label="okx_retrieved_at",
    )
    try:
        payload = json.loads(
            raw_response.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("research_data_okx_response_json_invalid") from exc
    if type(payload) is not dict or set(payload) != {"code", "msg", "data"}:
        raise ValueError("research_data_okx_response_envelope_invalid")
    if type(payload["code"]) is not str or payload["code"] != "0":
        raise ValueError("research_data_okx_response_code_not_success")
    if type(payload["msg"]) is not str:
        raise ValueError("research_data_okx_response_message_exact_str_required")
    if type(payload["data"]) is not list:
        raise ValueError("research_data_okx_response_data_exact_list_required")
    frame, row_receipt = parse_okx_completed_candle_rows(payload["data"])
    core: dict[str, object] = {
        "schema_version": OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION,
        "endpoint": exact_endpoint,
        "params": exact_params,
        "retrieved_at": exact_retrieved_at,
        "raw_response_sha256": hashlib.sha256(raw_response).hexdigest(),
        "raw_response_size": len(raw_response),
        "market": "crypto_spot",
        "instrument_type": "SPOT",
        "symbol": exact_params["instId"],
        "timeframe": timeframe,
        "row_receipt": row_receipt,
        "research_only": True,
        "paper_allowed": False,
        "live_allowed": False,
    }
    receipt_hash = hashlib.sha256(
        json.dumps(
            core,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()
    return frame, {**core, "source_receipt_hash": receipt_hash}


def verify_okx_candle_source_receipt(
    receipt: object,
    raw_response: bytes,
    *,
    endpoint: str,
    params: dict[str, str | int],
    retrieved_at: str,
) -> bool:
    if type(receipt) is not dict:
        raise ValueError("research_data_okx_source_receipt_exact_dict_required")
    _frame, expected = parse_okx_candle_response(
        raw_response,
        endpoint=endpoint,
        params=params,
        retrieved_at=retrieved_at,
    )
    if receipt != expected:
        raise ValueError("research_data_okx_source_receipt_verification_failed")
    return True


def _okx_bar_core(timeframe: str) -> str:
    return {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }.get(timeframe.lower(), "1H")


class MarketDataProvider:
    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        raise NotImplementedError

    def get_latest(self, symbol: str, timeframe: str, lookback: int = 200) -> pd.DataFrame:
        return self.get_history(symbol, timeframe, lookback)


class _SyntheticDataProviderCore(MarketDataProvider):
    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        base = {
            "BTC-USDT": 68000,
            "ETH-USDT": 3500,
            "SOL-USDT": 150,
        }.get(symbol.replace("-SWAP", ""), 1000)
        now = int(time.time() * 1000)
        interval = TIMEFRAME_MS.get(timeframe, TIMEFRAME_MS["1h"])
        rows = []
        last_close = base
        phase = (now // interval) % 240
        for i in range(limit):
            t = i + phase
            wave = math.sin(t / 9.5) * base * 0.028 + math.cos(t / 21) * base * 0.012
            drift = (i - limit / 2) * base * 0.000025
            close = max(0.01, base + wave + drift)
            open_px = last_close if i else close * 0.998
            high = max(open_px, close) * (1 + 0.004)
            low = min(open_px, close) * (1 - 0.004)
            rows.append({
                "time": pd.to_datetime(now - (limit - i) * interval, unit="ms", utc=True),
                "open": open_px,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000 + abs(math.sin(t / 5)) * 5000,
            })
            last_close = close
        return pd.DataFrame(rows).set_index("time")


class _CsvDataProviderCore(MarketDataProvider):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        if not self.csv_path:
            raise ValueError("csv_path is required for csv data provider")
        data = pd.read_csv(self.csv_path)
        time_col = "time" if "time" in data.columns else data.columns[0]
        data[time_col] = pd.to_datetime(data[time_col], utc=True)
        data = data.set_index(time_col)
        expected = ["open", "high", "low", "close", "volume"]
        missing = [col for col in expected if col not in data.columns]
        if missing:
            raise ValueError(f"CSV missing columns: {missing}")
        return data[expected].tail(limit)


class _OkxPublicDataProviderCore(MarketDataProvider):
    base_url = "https://www.okx.com"

    def __init__(self, fallback: MarketDataProvider | None = None, cache_dir: str = "runtime/cache", use_cache: bool = True):
        self.fallback = fallback
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, symbol: str, timeframe: str) -> Path:
        safe_symbol = _require_okx_spot_symbol(symbol)
        return self.cache_dir / (
            f"{safe_symbol}_{timeframe}_"
            f"{OKX_COMPLETED_CANDLE_SCHEMA_VERSION}.csv"
        )

    def _load_cache(self, symbol: str, timeframe: str) -> pd.DataFrame:
        if not self.use_cache:
            return pd.DataFrame()
        path = self._cache_path(symbol, timeframe)
        if not path.exists():
            return pd.DataFrame()
        try:
            data = pd.read_csv(path)
            data["time"] = pd.to_datetime(data["time"], utc=True)
            return data.set_index("time").sort_index()
        except Exception:
            logger.exception("Failed to load market data cache: %s", path)
            return pd.DataFrame()

    def _save_cache(self, symbol: str, timeframe: str, data: pd.DataFrame) -> None:
        if not self.use_cache or data.empty:
            return
        path = self._cache_path(symbol, timeframe)
        data = data.sort_index()
        out = data.reset_index().rename(columns={data.index.name or "index": "time"})
        out.to_csv(path, index=False)

    def _get(self, path: str, params: dict[str, str | int]) -> list:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Python-Quant-Bot/0.1"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("code") != "0":
            raise RuntimeError(payload.get("msg") or payload.get("code"))
        return payload.get("data", [])

    def _rows_to_frame(self, rows: list) -> pd.DataFrame:
        frame, _receipt = parse_okx_completed_candle_rows(rows)
        return frame

    def _fetch_page(self, endpoint: str, symbol: str, timeframe: str, limit: int, after: int | None = None) -> pd.DataFrame:
        symbol = _require_okx_spot_symbol(symbol)
        params: dict[str, str | int] = {
            "instId": symbol,
            "bar": okx_bar(timeframe),
            "limit": min(limit, 300),
        }
        if after is not None:
            params["after"] = after
        return self._rows_to_frame(self._get(endpoint, params))

    def _fetch_remote_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        frames = []
        latest = self._fetch_page("/api/v5/market/candles", symbol, timeframe, limit)
        if not latest.empty:
            frames.append(latest)
        oldest_ms = int(latest.index.min().timestamp() * 1000) if not latest.empty else None
        while oldest_ms is not None and sum(len(frame) for frame in frames) < limit:
            page = self._fetch_page("/api/v5/market/history-candles", symbol, timeframe, limit, after=oldest_ms)
            if page.empty:
                break
            next_oldest_ms = int(page.index.min().timestamp() * 1000)
            frames.append(page)
            if next_oldest_ms >= oldest_ms:
                break
            oldest_ms = next_oldest_ms
        if not frames:
            return pd.DataFrame()
        data = pd.concat(frames).sort_index()
        return data[~data.index.duplicated(keep="last")].tail(limit)

    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        cached = self._load_cache(symbol, timeframe)
        try:
            remote = self._fetch_remote_history(symbol, timeframe, limit)
        except Exception as exc:
            logger.warning("OKX public market data fetch failed (%s); using cache or fallback data", exc)
            remote = pd.DataFrame()

        real_data = pd.concat([cached, remote]).sort_index() if not cached.empty or not remote.empty else pd.DataFrame()
        if not real_data.empty:
            real_data = real_data[~real_data.index.duplicated(keep="last")]
            self._save_cache(symbol, timeframe, real_data)
            if len(real_data) >= limit:
                return real_data.tail(limit)

            if self.fallback is not None:
                missing = limit - len(real_data)
                logger.warning(
                    "Insufficient real OKX history for %s %s: got %d, need %d. Using fallback for %d rows.",
                    symbol, timeframe, len(real_data), limit, missing
                )
                prefix = self.fallback.get_history(symbol, timeframe, missing)
                return pd.concat([prefix, real_data]).sort_index().tail(limit)
            logger.warning(
                "Insufficient real OKX history for %s %s: got %d, need %d; synthetic fallback is disabled.",
                symbol, timeframe, len(real_data), limit
            )
            raise RuntimeError(
                f"Insufficient real OKX history for {symbol} {timeframe}: got {len(real_data)}, need {limit}."
            )

        if self.fallback is None:
            raise RuntimeError("No real OKX data and synthetic fallback is disabled.")
        return self.fallback.get_history(symbol, timeframe, limit)


def _build_data_provider_core(config: BotConfig) -> MarketDataProvider:
    provider = config.data.provider.lower()
    if provider == "okx":
        return OkxPublicDataProvider(cache_dir=config.data.cache_dir, use_cache=config.data.use_cache)
    if provider == "csv":
        return CsvDataProvider(config.data.csv_path)
    if provider == "synthetic":
        raise RuntimeError("Synthetic market data is test-only and cannot be selected by product configuration.")
    raise ValueError(f"Unsupported market data provider: {provider}")
MARKET_DATA_SCHEMA_VERSION = "research-market-data-v1"

import hashlib as _hashlib
import json as _json
import math as _math

import numpy as _np

from hakimi_research.config import validate_research_config as _validate_research_config


_REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
_OKX_BAR_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1Dutc",
    "1w": "1Wutc",
}
_PANDAS_FREQUENCY_MAP = {
    "1m": "min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "12h": "12h",
    "1d": "D",
    "1w": "7D",
}
_SYNTHETIC_END = pd.Timestamp("2024-01-01T00:00:00Z")


def _data_fail(code: str) -> None:
    raise ValueError(code)


def _exact_text(value: object, *, label: str, nonempty: bool = True) -> str:
    if type(value) is not str:
        _data_fail(f"research_data_{label}_exact_str_required")
    if nonempty and not value:
        _data_fail(f"research_data_{label}_nonempty_required")
    return value


def _exact_count(value: object, *, label: str, maximum: int = 100_000) -> int:
    if type(value) is not int:
        _data_fail(f"research_data_{label}_exact_int_required")
    if value <= 0:
        _data_fail(f"research_data_{label}_positive_required")
    if value > maximum:
        _data_fail(f"research_data_{label}_above_maximum")
    return value


def _validate_request(
    symbol: object,
    timeframe: object,
    limit: object,
) -> tuple[str, str, int]:
    exact_symbol = _exact_text(symbol, label="symbol")
    exact_timeframe = _exact_text(timeframe, label="timeframe")
    if exact_timeframe not in _PANDAS_FREQUENCY_MAP:
        _data_fail("research_data_timeframe_unsupported")
    exact_limit = _exact_count(limit, label="limit")
    return exact_symbol, exact_timeframe, exact_limit


def validate_market_data_frame(
    data: pd.DataFrame,
    *,
    minimum_rows: int = 1,
) -> pd.DataFrame:
    if type(data) is not pd.DataFrame:
        _data_fail("research_data_exact_dataframe_required")
    exact_minimum = _exact_count(minimum_rows, label="minimum_rows")
    if len(data) < exact_minimum:
        _data_fail("research_data_insufficient_rows")
    missing = [column for column in _REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        _data_fail(f"research_data_missing_columns:{','.join(missing)}")
    if not isinstance(data.index, pd.DatetimeIndex):
        _data_fail("research_data_datetime_index_required")
    if data.index.tz is None:
        _data_fail("research_data_timezone_required")
    if data.index.hasnans:
        _data_fail("research_data_timestamp_nat_rejected")
    if not data.index.is_unique:
        _data_fail("research_data_duplicate_timestamp_rejected")
    if not data.index.is_monotonic_increasing:
        _data_fail("research_data_timestamp_order_rejected")

    frame = data.loc[:, list(_REQUIRED_COLUMNS)].copy(deep=True)
    frame.index = frame.index.tz_convert("UTC")
    frame.index.name = data.index.name or "time"
    for column in _REQUIRED_COLUMNS:
        if not pd.api.types.is_numeric_dtype(frame[column].dtype):
            _data_fail(f"research_data_{column}_numeric_dtype_required")
        if pd.api.types.is_bool_dtype(frame[column].dtype):
            _data_fail(f"research_data_{column}_bool_dtype_rejected")
    values = frame.loc[:, list(_REQUIRED_COLUMNS)].to_numpy(dtype=float, copy=True)
    if not _np.isfinite(values).all():
        _data_fail("research_data_nonfinite_ohlcv_rejected")
    frame = frame.astype({column: "float64" for column in _REQUIRED_COLUMNS})

    prices = frame.loc[:, ["open", "high", "low", "close"]]
    if (prices <= 0).any().any():
        _data_fail("research_data_nonpositive_price_rejected")
    if (frame["volume"] < 0).any():
        _data_fail("research_data_negative_volume_rejected")
    if (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any()
        or (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any()
    ):
        _data_fail("research_data_ohlc_relation_rejected")
    return frame


def market_data_fingerprint(data: pd.DataFrame) -> str:
    frame = validate_market_data_frame(data)
    records = []
    for timestamp, row in frame.iterrows():
        records.append(
            [
                timestamp.isoformat(),
                *[float(row[column]).hex() for column in _REQUIRED_COLUMNS],
            ]
        )
    payload = {
        "schema": MARKET_DATA_SCHEMA_VERSION,
        "columns": list(_REQUIRED_COLUMNS),
        "records": records,
    }
    encoded = _json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return _hashlib.sha256(encoded).hexdigest()


def okx_bar(timeframe: str) -> str:
    exact_timeframe = _exact_text(timeframe, label="timeframe")
    try:
        return _OKX_BAR_MAP[exact_timeframe]
    except KeyError as exc:
        raise ValueError("research_data_timeframe_unsupported") from exc


class CsvDataProvider(_CsvDataProviderCore):
    def __init__(self, csv_path: str):
        exact_path = _exact_text(csv_path, label="csv_path")
        super().__init__(exact_path)

    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        exact_symbol, exact_timeframe, exact_limit = _validate_request(
            symbol,
            timeframe,
            limit,
        )
        return validate_market_data_frame(
            super().get_history(exact_symbol, exact_timeframe, exact_limit)
        )

    def get_latest(
        self,
        symbol: str,
        timeframe: str,
        lookback: int = 200,
    ) -> pd.DataFrame:
        return self.get_history(symbol, timeframe, lookback)


class SyntheticDataProvider(_SyntheticDataProviderCore):
    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        exact_symbol, exact_timeframe, exact_limit = _validate_request(
            symbol,
            timeframe,
            limit,
        )
        digest = _hashlib.sha256(
            f"{exact_symbol}|{exact_timeframe}|{MARKET_DATA_SCHEMA_VERSION}".encode("utf-8")
        ).digest()
        phase = int.from_bytes(digest[:8], "big") / float(2**64)
        close_values = []
        for index in range(exact_limit):
            centered = index - (exact_limit - 1) / 2.0
            trend = centered * 0.12
            cycle = _math.sin((index + phase) * 0.31) * 18.0
            secondary = _math.cos((index + phase) * 0.07) * 6.0
            close_values.append(1_000.0 + trend + cycle + secondary)
        open_values = [close_values[0], *close_values[:-1]]
        high_values = [
            max(open_price, close_price) + 1.0 + abs(_math.sin(index + phase))
            for index, (open_price, close_price) in enumerate(zip(open_values, close_values))
        ]
        low_values = [
            min(open_price, close_price) - 1.0 - abs(_math.cos(index + phase))
            for index, (open_price, close_price) in enumerate(zip(open_values, close_values))
        ]
        volume_values = [
            1_000.0 + 500.0 * (1.0 + _math.sin((index + phase) * 0.19))
            for index in range(exact_limit)
        ]
        frame = pd.DataFrame(
            {
                "open": open_values,
                "high": high_values,
                "low": low_values,
                "close": close_values,
                "volume": volume_values,
            },
            index=pd.date_range(
                end=_SYNTHETIC_END,
                periods=exact_limit,
                freq=_PANDAS_FREQUENCY_MAP[exact_timeframe],
                tz="UTC",
            ),
        )
        frame.index.name = "time"
        return validate_market_data_frame(frame)

    def get_latest(
        self,
        symbol: str,
        timeframe: str,
        lookback: int = 200,
    ) -> pd.DataFrame:
        return self.get_history(symbol, timeframe, lookback)


class OkxPublicDataProvider(_OkxPublicDataProviderCore):
    def __init__(
        self,
        fallback: MarketDataProvider | None = None,
        cache_dir: str = "runtime/cache",
        use_cache: bool = True,
    ):
        if fallback is not None and not isinstance(fallback, MarketDataProvider):
            _data_fail("research_data_fallback_provider_required")
        exact_cache_dir = _exact_text(
            cache_dir,
            label="cache_dir",
            nonempty=bool(use_cache),
        )
        if type(use_cache) is not bool:
            _data_fail("research_data_use_cache_exact_bool_required")
        super().__init__(
            fallback=fallback,
            cache_dir=exact_cache_dir,
            use_cache=use_cache,
        )

    def _rows_to_frame(self, rows: list) -> pd.DataFrame:
        if type(rows) is not list:
            _data_fail("research_data_okx_rows_exact_list_required")
        frame = super()._rows_to_frame(rows)
        if frame.empty:
            return frame
        return validate_market_data_frame(frame)

    def get_history(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        exact_symbol, exact_timeframe, exact_limit = _validate_request(
            symbol,
            timeframe,
            limit,
        )
        return validate_market_data_frame(
            super().get_history(exact_symbol, exact_timeframe, exact_limit)
        )

    def get_latest(
        self,
        symbol: str,
        timeframe: str,
        lookback: int = 200,
    ) -> pd.DataFrame:
        return self.get_history(symbol, timeframe, lookback)


def build_data_provider(config: BotConfig) -> MarketDataProvider:
    if type(config) is not BotConfig:
        try:
            requested_provider = config.data.provider
        except AttributeError:
            requested_provider = None
        if type(requested_provider) is str and requested_provider == "synthetic":
            raise RuntimeError(
                "Synthetic market data is test-only and cannot be selected by product configuration."
            )
        _data_fail("research_data_exact_canonical_config_required")
    _validate_research_config(config)
    provider = config.data.provider
    if type(provider) is not str:
        _data_fail("research_data_provider_exact_str_required")
    if provider == "csv":
        return CsvDataProvider(config.data.csv_path)
    if provider == "okx":
        if config.market != "crypto_spot":
            _data_fail("research_data_okx_crypto_spot_market_required")
        return OkxPublicDataProvider(
            cache_dir=config.data.cache_dir,
            use_cache=config.data.use_cache,
        )
    if provider == "synthetic":
        raise RuntimeError(
            "Synthetic market data is test-only and cannot be selected by product configuration."
        )
    raise ValueError(f"Unsupported market data provider: {provider}")


__all__ = [
    "MARKET_DATA_SCHEMA_VERSION",
    "OKX_COMPLETED_CANDLE_SCHEMA_VERSION",
    "OKX_CANDLE_SOURCE_RECEIPT_SCHEMA_VERSION",
    "OKX_SPOT_VOLUME_UNIT",
    "MarketDataProvider",
    "CsvDataProvider",
    "OkxPublicDataProvider",
    "SyntheticDataProvider",
    "build_data_provider",
    "okx_bar",
    "validate_market_data_frame",
    "market_data_fingerprint",
    "parse_okx_completed_candle_rows",
    "parse_okx_candle_response",
    "verify_okx_candle_source_receipt",
]
