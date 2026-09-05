from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

try:
    from config import STOCK_MARKETS
except ModuleNotFoundError:
    from hakimi_research.terminal_config import STOCK_MARKETS


_PLAIN_US_EQUITY = re.compile(r"^[A-Z][A-Z0-9]{0,4}(?:[.-][A-Z])?$")
_FUTU_EQUITY = re.compile(r"^(?:US\.[A-Z][A-Z0-9.-]{0,9}|HK\.\d{5})$")
_PLAIN_CRYPTO_BASES = {"BTC", "ETH", "SOL", "BNB", "DOGE"}


def is_stock_symbol(symbol: str) -> bool:
    text = (symbol or "").upper()
    if any(item["symbol"] == text or item.get("futu") == text for item in STOCK_MARKETS):
        return True
    if not text or "-" in text or text in _PLAIN_CRYPTO_BASES:
        return False
    return bool(_PLAIN_US_EQUITY.fullmatch(text) or _FUTU_EQUITY.fullmatch(text))


def stock_meta(symbol: str) -> dict[str, Any]:
    text = (symbol or "AAPL").upper()
    for item in STOCK_MARKETS:
        if item["symbol"] == text or item.get("futu") == text:
            return item
    if "." in text:
        market = text.split(".", 1)[0]
        return {"symbol": text, "futu": text, "yahoo": text, "name": text, "exchange": market, "market": market, "quote": "USD", "sector": "Stock"}
    return {"symbol": text, "futu": f"US.{text}", "yahoo": text, "stooq": f"{text.lower()}.us", "name": text, "exchange": "US", "market": "US", "quote": "USD", "sector": "Stock"}


def futu_code(symbol: str) -> str:
    return str(stock_meta(symbol).get("futu") or symbol).upper()


def yahoo_stock_symbol(symbol: str) -> str:
    return str(stock_meta(symbol).get("yahoo") or symbol).upper()


def stock_source_symbol(symbol: str) -> str:
    meta = stock_meta(symbol)
    if meta.get("stooq"):
        return str(meta["stooq"]).lower()
    return str(meta.get("yahoo") or symbol).lower()


def normalize_stock_interval(interval: str) -> tuple[str, str]:
    text = (interval or "1d").lower()
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
    market = str(stock_meta(symbol).get("market") or "US").upper()
    if market == "HK":
        return ZoneInfo("Asia/Hong_Kong")
    if market in {"CN", "SH", "SZ"}:
        return ZoneInfo("Asia/Shanghai")
    return ZoneInfo("America/New_York")


def stock_session_from_ts(ts_ms: int, symbol: str = "AAPL") -> str:
    market = str(stock_meta(symbol).get("market") or "US").upper()
    try:
        local_time = datetime.fromtimestamp(ts_ms / 1000, stock_timezone(symbol))
        total = local_time.hour * 60 + local_time.minute
    except Exception:
        utc = time.gmtime(ts_ms / 1000)
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
    }.get(session, "全部")
