from __future__ import annotations

import json
import logging
import math
import time
import urllib.parse
import urllib.request
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
        safe_symbol = symbol.replace("/", "-").replace(":", "-")
        return self.cache_dir / f"{safe_symbol}_{timeframe}.csv"

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
        candles = []
        for row in reversed(rows):
            candles.append({
                "time": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5] or 0),
            })
        if not candles:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        return pd.DataFrame(candles).set_index("time").sort_index()

    def _fetch_page(self, endpoint: str, symbol: str, timeframe: str, limit: int, after: int | None = None) -> pd.DataFrame:
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
        return validate_market_data_frame(super()._rows_to_frame(rows))

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
    "MarketDataProvider",
    "CsvDataProvider",
    "OkxPublicDataProvider",
    "SyntheticDataProvider",
    "build_data_provider",
    "okx_bar",
    "validate_market_data_frame",
    "market_data_fingerprint",
]
