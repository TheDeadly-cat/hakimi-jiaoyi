from __future__ import annotations

import math
import re
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from hakimi_research.terminal_config import STOCK_MARKETS


STOCK_METADATA_CONTRACT_VERSION = "stock-metadata-v1"

_PLAIN_US_EQUITY = re.compile(r"^[A-Z][A-Z0-9]{0,4}(?:[.-][A-Z])?$")
_FUTU_EQUITY = re.compile(r"^(?:US\.[A-Z][A-Z0-9.-]{0,9}|HK\.\d{5})$")
_PLAIN_CRYPTO_BASES = {"BTC", "ETH", "SOL", "BNB", "DOGE"}


def _native_text(value: Any, default: str = "") -> str:
    return value if type(value) is str else default


def _symbol_text(value: Any, default: str = "") -> str:
    return _native_text(value, default).upper()


def _timestamp_seconds(value: Any) -> float:
    if type(value) in {int, float}:
        parsed = float(value)
    elif type(value) is str:
        try:
            parsed = float(value)
        except ValueError:
            return 0.0
    else:
        return 0.0
    return parsed / 1000 if math.isfinite(parsed) else 0.0


def is_stock_symbol(symbol: str) -> bool:
    if type(symbol) is not str:
        return False
    text = symbol.upper()
    for item in STOCK_MARKETS:
        if type(item) is not dict:
            continue
        if _symbol_text(item.get("symbol")) == text or _symbol_text(item.get("futu")) == text:
            return True
    if not text or "-" in text or text in _PLAIN_CRYPTO_BASES:
        return False
    return bool(_PLAIN_US_EQUITY.fullmatch(text) or _FUTU_EQUITY.fullmatch(text))


def stock_meta(symbol: str) -> dict[str, Any]:
    text = _symbol_text(symbol, "AAPL") or "AAPL"
    for item in STOCK_MARKETS:
        if type(item) is not dict:
            continue
        if _symbol_text(item.get("symbol")) == text or _symbol_text(item.get("futu")) == text:
            return dict(item)
    if "." in text:
        market = text.split(".", 1)[0]
        return {
            "symbol": text,
            "futu": text,
            "yahoo": text,
            "name": text,
            "exchange": market,
            "market": market,
            "quote": "USD",
            "sector": "Stock",
        }
    return {
        "symbol": text,
        "futu": f"US.{text}",
        "yahoo": text,
        "stooq": f"{text.lower()}.us",
        "name": text,
        "exchange": "US",
        "market": "US",
        "quote": "USD",
        "sector": "Stock",
    }


def futu_code(symbol: str) -> str:
    meta = stock_meta(symbol)
    return _symbol_text(meta.get("futu"), _symbol_text(symbol))


def yahoo_stock_symbol(symbol: str) -> str:
    meta = stock_meta(symbol)
    return _symbol_text(meta.get("yahoo"), _symbol_text(symbol))


def stock_source_symbol(symbol: str) -> str:
    meta = stock_meta(symbol)
    stooq = _native_text(meta.get("stooq"))
    if stooq:
        return stooq.lower()
    return _native_text(meta.get("yahoo"), _native_text(symbol)).lower()


def normalize_stock_interval(interval: str) -> tuple[str, str]:
    text = _native_text(interval, "1d").lower()
    mapping = {
        "1m": ("1m", "1d"),
        "5m": ("5m", "5d"),
        "15m": ("15m", "10d"),
        "30m": ("30m", "30d"),
        "1h": ("60m", "60d"),
        "60m": ("60m", "60d"),
        "4h": ("60m", "60d"),
        "1d": ("1d", "2y"),
        "1dutc": ("1d", "2y"),
    }
    return mapping.get(text, ("1d", "2y"))


def stock_timezone(symbol: str) -> ZoneInfo:
    market = _symbol_text(stock_meta(symbol).get("market"), "US")
    if market == "HK":
        return ZoneInfo("Asia/Hong_Kong")
    if market in {"CN", "SH", "SZ"}:
        return ZoneInfo("Asia/Shanghai")
    return ZoneInfo("America/New_York")


def stock_session_from_ts(ts_ms: int, symbol: str = "AAPL") -> str:
    market = _symbol_text(stock_meta(symbol).get("market"), "US")
    seconds = _timestamp_seconds(ts_ms)
    try:
        local_time = datetime.fromtimestamp(seconds, stock_timezone(symbol))
        total = local_time.hour * 60 + local_time.minute
    except (OSError, OverflowError, ValueError):
        utc = time.gmtime(seconds)
        total = utc.tm_hour * 60 + utc.tm_min
    if market in {"HK", "CN", "SH", "SZ"}:
        if 9 * 60 <= total < 9 * 60 + 30:
            return "pre"
        if 9 * 60 + 30 <= total < 12 * 60 or 13 * 60 <= total < 16 * 60:
            return "regular"
        if 16 * 60 <= total < 18 * 60:
            return "post"
        return "overnight"
    if 4 * 60 <= total < 9 * 60 + 30:
        return "pre"
    if 9 * 60 + 30 <= total < 16 * 60:
        return "regular"
    if 16 * 60 <= total < 20 * 60:
        return "post"
    return "overnight"


def stock_session_label(session: str) -> str:
    return {
        "all": "全部",
        "pre": "盘前",
        "regular": "盘中",
        "post": "盘后",
        "overnight": "夜盘",
    }.get(_native_text(session), "全部")


__all__ = [
    "STOCK_METADATA_CONTRACT_VERSION",
    "futu_code",
    "is_stock_symbol",
    "normalize_stock_interval",
    "stock_meta",
    "stock_session_from_ts",
    "stock_session_label",
    "stock_source_symbol",
    "stock_timezone",
    "yahoo_stock_symbol",
]
