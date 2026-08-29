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

from quant_bot.config import BotConfig

logger = logging.getLogger(__name__)


TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def okx_bar(timeframe: str) -> str:
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


class SyntheticDataProvider(MarketDataProvider):
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


class CsvDataProvider(MarketDataProvider):
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


class OkxPublicDataProvider(MarketDataProvider):
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


def build_data_provider(config: BotConfig) -> MarketDataProvider:
    provider = config.data.provider.lower()
    if provider == "okx":
        return OkxPublicDataProvider(cache_dir=config.data.cache_dir, use_cache=config.data.use_cache)
    if provider == "csv":
        return CsvDataProvider(config.data.csv_path)
    if provider == "synthetic":
        raise RuntimeError("Synthetic market data is test-only and cannot be selected by product configuration.")
    raise ValueError(f"Unsupported market data provider: {provider}")
