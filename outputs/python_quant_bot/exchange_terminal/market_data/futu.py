from __future__ import annotations

import os
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from config import ALLOW_STOCK_FALLBACK, FUTU_HOST, FUTU_PORT, LIVE_TRADING_HARD_BLOCK, STOCK_MARKETS
    from hakimi_research.stock_session import with_stock_session_contract
    from hakimi_research.stock_metadata import normalize_stock_interval, stock_meta, stock_timezone
    from utils import now_ms, pct
except ModuleNotFoundError:
    from hakimi_research.terminal_config import ALLOW_STOCK_FALLBACK, FUTU_HOST, FUTU_PORT, LIVE_TRADING_HARD_BLOCK, STOCK_MARKETS
    from hakimi_research.stock_session import with_stock_session_contract
    from hakimi_research.stock_metadata import normalize_stock_interval, stock_meta, stock_timezone
    from hakimi_research.terminal_utils import now_ms, pct


FUTU_STATUS_CACHE: dict[str, Any] = {"time": 0, "online": False, "message": "unchecked"}
_FUTU_SDK_IMPORT_LOCK = threading.Lock()


def reset_futu_status_cache(message: str = "unchecked") -> None:
    FUTU_STATUS_CACHE.update({"time": 0, "online": False, "message": message})


def update_futu_status_cache(*, online: bool, message: str, sdk_installed: bool | None = None) -> None:
    payload: dict[str, Any] = {
        "time": now_ms(),
        "online": bool(online),
        "message": message,
    }
    if sdk_installed is not None:
        payload["sdk_installed"] = bool(sdk_installed)
    FUTU_STATUS_CACHE.update(payload)


def futu_socket_online(timeout: float = 0.45) -> tuple[bool, str]:
    try:
        with socket.create_connection((FUTU_HOST, FUTU_PORT), timeout=timeout):
            return True, f"OpenD {FUTU_HOST}:{FUTU_PORT} online"
    except Exception as exc:
        return False, f"OpenD offline: {exc}"


def import_futu_sdk() -> tuple[Any | None, str]:
    runtime_appdata = Path(
        os.getenv("FUTU_PY_APPDATA")
        or Path(__file__).resolve().parents[2] / "runtime" / "futu_sdk_appdata"
    )
    with _FUTU_SDK_IMPORT_LOCK:
        previous_appdata = os.environ.get("appdata")
        try:
            runtime_appdata.mkdir(parents=True, exist_ok=True)
            os.environ["appdata"] = str(runtime_appdata)
            import futu  # type: ignore
            return futu, "futu-api installed"
        except Exception as exc:
            return None, f"futu-api import failed: {exc}"
        finally:
            if previous_appdata is None:
                os.environ.pop("appdata", None)
            else:
                os.environ["appdata"] = previous_appdata


def futu_market_counts() -> dict[str, int]:
    counts: dict[str, int] = {"US": 0, "HK": 0, "CN": 0}
    for item in STOCK_MARKETS:
        market = str(item.get("market") or "US")
        counts[market] = counts.get(market, 0) + 1
    return counts


def enrich_futu_status(payload: dict[str, Any]) -> dict[str, Any]:
    online = bool(payload.get("opend_online"))
    sdk_ready = bool(payload.get("sdk_installed"))
    payload["markets"] = futu_market_counts()
    payload["capabilities"] = [
        "market_snapshot",
        "history_kline",
        "extended_session_kline",
        "order_book",
        "rt_ticker",
        "capital_flow",
        "capital_distribution",
        "valuation_snapshot",
        "stock_strategy_research",
        "paper_execution_only",
    ]
    payload["steps"] = [
        {
            "label": "Python SDK",
            "state": "ok" if sdk_ready else "missing",
            "detail": "futu-api 已安装" if sdk_ready else "需要安装 futu-api",
        },
        {
            "label": "FutuOpenD",
            "state": "ok" if online else "offline",
            "detail": f"{payload.get('host')}:{payload.get('port')}",
        },
        {
            "label": "行情通道",
            "state": "ready" if online else "fallback",
            "detail": "富途实时/历史行情" if online else (
                "外部兜底源开启" if ALLOW_STOCK_FALLBACK else "当前使用离线种子占位，等待 OpenD"
            ),
        },
        {
            "label": "股票池",
            "state": "ready",
            "detail": f"US/HK/CN 共 {len(STOCK_MARKETS)} 个标的",
        },
        {
            "label": "实盘交易",
            "state": "blocked" if LIVE_TRADING_HARD_BLOCK else "ready",
            "detail": "当前版本只允许行情、策略研究、模拟执行" if LIVE_TRADING_HARD_BLOCK else "需要二次授权",
        },
    ]
    payload["setup_hint"] = (
        "启动 FutuOpenD 并保持 127.0.0.1:11111 可访问后，股票行情会自动切到 Futu。"
        if not online else
        "FutuOpenD 已连通，股票快照和 K 线优先使用富途通道。"
    )
    payload["fallback_network_enabled"] = ALLOW_STOCK_FALLBACK
    return payload


def futu_status_cache_ms() -> int:
    return 5000 if FUTU_STATUS_CACHE.get("online") else 120000


def futu_status_snapshot(force: bool = False) -> dict[str, Any]:
    if not force and now_ms() - int(FUTU_STATUS_CACHE.get("time") or 0) < futu_status_cache_ms():
        return enrich_futu_status({
            "ok": True,
            "host": FUTU_HOST,
            "port": FUTU_PORT,
            "sdk_installed": bool(FUTU_STATUS_CACHE.get("sdk_installed")),
            "opend_online": bool(FUTU_STATUS_CACHE.get("online")),
            "source": "futu" if FUTU_STATUS_CACHE.get("online") else "fallback",
            "message": FUTU_STATUS_CACHE.get("message", "unchecked"),
            "stock_count": len(STOCK_MARKETS),
            "live_trading_hard_block": LIVE_TRADING_HARD_BLOCK,
            "updated_at": FUTU_STATUS_CACHE.get("time", 0),
        })
    futu, import_msg = import_futu_sdk()
    port_online, port_msg = futu_socket_online()
    update_futu_status_cache(
        online=bool(futu and port_online),
        sdk_installed=bool(futu),
        message=port_msg if futu else import_msg,
    )
    return futu_status_snapshot(False)


def futu_universe_snapshot() -> dict[str, Any]:
    status = futu_status_snapshot()
    return {
        "ok": True,
        "status": status,
        "stocks": [
            {
                "symbol": item["symbol"],
                "futu": item.get("futu", item["symbol"]),
                "yahoo": item.get("yahoo", item["symbol"]),
                "name": item["name"],
                "exchange": item.get("exchange", ""),
                "market": item.get("market", "US"),
                "quote": item.get("quote", "USD"),
                "sector": item.get("sector", "Stock"),
            }
            for item in STOCK_MARKETS
        ],
    }


def futu_history_ktype(interval: str) -> str:
    text = (interval or "1d").lower()
    return {
        "1m": "K_1M",
        "5m": "K_5M",
        "15m": "K_15M",
        "30m": "K_30M",
        "1h": "K_60M",
        "60m": "K_60M",
        "4h": "K_60M",
        "1d": "K_DAY",
        "1dutc": "K_DAY",
    }.get(text, "K_DAY")


def futu_history_window(symbol: str, interval: str, limit: int) -> tuple[str, str]:
    tz = stock_timezone(symbol or "AAPL")
    end_dt = datetime.now(tz) + timedelta(days=1)
    normalized, _ = normalize_stock_interval(interval)
    if normalized == "1m":
        days = max(5, min(15, int(limit / 80) + 3))
    elif normalized in {"5m", "15m", "30m"}:
        days = max(15, min(45, int(limit / 40) + 10))
    elif normalized in {"60m", "4h"}:
        days = max(90, min(260, int(limit / 4) + 60))
    else:
        days = max(420, min(1600, int(limit * 2.2)))
    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def parse_futu_time_key(value: Any, symbol: str) -> int:
    text = value.strip() if type(value) is str else ""
    if not text:
        return 0
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return int(dt.replace(tzinfo=stock_timezone(symbol)).timestamp() * 1000)
        except ValueError:
            continue
    return 0


def normalize_futu_quote(row: dict[str, Any], symbol: str) -> dict[str, Any]:
    meta = stock_meta(symbol)
    last = pct(row.get("last_price", row.get("last", 0)))
    open_price = pct(row.get("open_price", row.get("open", 0)))
    prev_close = pct(row.get("prev_close_price", row.get("prev_close", 0)))
    high = pct(row.get("high_price", row.get("high", last)))
    low = pct(row.get("low_price", row.get("low", last)))
    volume = pct(row.get("volume", 0))
    turnover = pct(row.get("turnover", 0))
    change_rate = row.get("change_rate", None)
    if change_rate is None:
        base = prev_close or open_price
        change_rate = (last / base - 1) * 100 if last > 0 and base > 0 else 0.0
    quote = {
        "symbol": meta["symbol"],
        "instId": meta.get("futu", meta["symbol"]),
        "name": row.get("stock_name") or row.get("name") or meta["name"],
        "quote": meta.get("quote", "USD"),
        "type": "stock",
        "category": "stocks",
        "source": "futu",
        "exchange": meta.get("exchange", "US"),
        "market": meta.get("market", "US"),
        "sector": meta.get("sector", "Stock"),
        "status": "ONLINE" if last > 0 else "OFFLINE",
        "last": last,
        "open24h": open_price or prev_close,
        "high24h": high,
        "low24h": low,
        "vol24h": volume,
        "volCcy24h": turnover or volume,
        "bidPx": pct(row.get("bid_price", row.get("bidPx", 0))),
        "askPx": pct(row.get("ask_price", row.get("askPx", 0))),
        "prevClose": prev_close,
        "change_basis": "previous_close" if prev_close > 0 else "provider",
        "change24h_pct": round(float(change_rate or 0), 2),
        "ts": parse_futu_time_key(row.get("update_time"), meta["symbol"]),
        "date": str(row.get("update_time", ""))[:10],
        "time": str(row.get("update_time", ""))[11:19],
        "futu_code": meta.get("futu", meta["symbol"]),
        "market_state": str(row.get("market_state") or ""),
        "sec_status": str(row.get("sec_status") or "NORMAL"),
        "suspension": bool(row.get("suspension")),
        "pre_price": pct(row.get("pre_price", 0)),
        "pre_change_rate": pct(row.get("pre_change_rate", 0)),
        "pre_volume": pct(row.get("pre_volume", 0)),
        "pre_turnover": pct(row.get("pre_turnover", 0)),
        "after_price": pct(row.get("after_price", 0)),
        "after_change_rate": pct(row.get("after_change_rate", 0)),
        "after_volume": pct(row.get("after_volume", 0)),
        "after_turnover": pct(row.get("after_turnover", 0)),
        "overnight_price": pct(row.get("overnight_price", 0)),
        "overnight_change_rate": pct(row.get("overnight_change_rate", 0)),
        "overnight_volume": pct(row.get("overnight_volume", 0)),
        "overnight_turnover": pct(row.get("overnight_turnover", 0)),
    }
    return with_stock_session_contract(
        quote,
        meta["symbol"],
        market_state=str(row.get("market_state") or ""),
        now_ms_value=now_ms(),
    )
