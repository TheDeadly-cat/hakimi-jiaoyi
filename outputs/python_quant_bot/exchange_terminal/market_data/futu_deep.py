from __future__ import annotations

import time
from typing import Any

try:
    from config import FUTU_HOST, FUTU_PORT, LIVE_TRADING_HARD_BLOCK
    from market_data.futu import futu_status_snapshot, import_futu_sdk
    from market_data.stocks import futu_code, stock_meta
    from utils import clean_json_value, now_ms, pct
except ModuleNotFoundError:
    from exchange_terminal.config import FUTU_HOST, FUTU_PORT, LIVE_TRADING_HARD_BLOCK
    from exchange_terminal.market_data.futu import futu_status_snapshot, import_futu_sdk
    from exchange_terminal.market_data.stocks import futu_code, stock_meta
    from exchange_terminal.utils import clean_json_value, now_ms, pct


FUTU_DEEP_CACHE: dict[str, dict[str, Any]] = {}


def futu_frame_records(data: Any, limit: int = 20, tail: bool = False) -> list[dict[str, Any]]:
    if data is None:
        return []
    try:
        frame = data.tail(limit) if tail and hasattr(data, "tail") else data.head(limit) if hasattr(data, "head") else data
        if hasattr(frame, "to_dict"):
            return clean_json_value(frame.to_dict("records"))
        if isinstance(frame, list):
            return clean_json_value(frame[:limit])
        if isinstance(frame, dict):
            return [clean_json_value(frame)]
    except Exception:
        return []
    return []


def futu_order_book_levels(payload: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return {"bids": [], "asks": []}

    def levels(key: str) -> list[dict[str, Any]]:
        result = []
        for index, row in enumerate(payload.get(key) or [], 1):
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            result.append({
                "level": index,
                "price": pct(row[0]),
                "volume": pct(row[1]),
                "orders": int(pct(row[2], 0)) if len(row) > 2 else 0,
            })
        return result

    return {"bids": levels("Bid"), "asks": levels("Ask")}


def pick_row_value(row: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    for key in keys:
        value = row.get(key)
        if key in row and value is not None and value != "":
            return value
    return default


def compact_stock_watch_detail(meta: dict[str, Any], code: str, snapshot: dict[str, Any], market_state: str) -> dict[str, Any]:
    return clean_json_value({
        "symbol": meta.get("symbol"),
        "futu_code": code,
        "name": snapshot.get("name") or meta.get("name"),
        "market": meta.get("market"),
        "exchange": meta.get("exchange"),
        "sector": meta.get("sector"),
        "quote": meta.get("quote"),
        "market_state": market_state,
        "sec_status": snapshot.get("sec_status") or snapshot.get("security_status"),
        "listing_date": snapshot.get("listing_date"),
        "lot_size": snapshot.get("lot_size"),
        "price_spread": snapshot.get("price_spread"),
        "issued_shares": pct(snapshot.get("issued_shares")),
        "outstanding_shares": pct(snapshot.get("outstanding_shares")),
        "total_market_val": pct(snapshot.get("total_market_val")),
        "circular_market_val": pct(snapshot.get("circular_market_val")),
        "session_prices": {
            "pre": pct(snapshot.get("pre_price")),
            "regular": pct(snapshot.get("last_price")),
            "post": pct(snapshot.get("after_price")),
            "overnight": pct(snapshot.get("overnight_price")),
        },
        "update_time": snapshot.get("update_time") or snapshot.get("data_date"),
    })


def compact_valuation_detail(snapshot: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    trend = payload.get("trend") if isinstance(payload, dict) else {}
    trend = trend if isinstance(trend, dict) else {}
    history = []
    items = trend.get("historical_items") if isinstance(trend.get("historical_items"), list) else []
    for item in items[-12:]:
        if not isinstance(item, dict):
            continue
        history.append({
            "time": item.get("time") or item.get("date") or item.get("timestamp"),
            "value": pct(item.get("value") or item.get("val")),
        })

    return clean_json_value({
        "valuation_type": payload.get("valuation_type") if isinstance(payload, dict) else "",
        "valuation_update": (payload.get("last_update_time_str") or payload.get("last_update_time")) if isinstance(payload, dict) else "",
        "pe_ttm_ratio": pct(snapshot.get("pe_ttm_ratio")),
        "pe_ratio": pct(snapshot.get("pe_ratio")),
        "pb_ratio": pct(snapshot.get("pb_ratio")),
        "dividend_ratio_ttm": pct(snapshot.get("dividend_ratio_ttm")),
        "ey_ratio": pct(snapshot.get("ey_ratio")),
        "total_market_val": pct(snapshot.get("total_market_val")),
        "circular_market_val": pct(snapshot.get("circular_market_val")),
        "current_value": pct(trend.get("current_value")),
        "average_value": pct(trend.get("average_value")),
        "avg_minus_1_stddev": pct(trend.get("avg_minus_1_stddev")),
        "avg_plus_1_stddev": pct(trend.get("avg_plus_1_stddev")),
        "forward_value": pct(trend.get("forward_value")),
        "valuation_percentile": pct(trend.get("valuation_percentile")),
        "history": history,
    })


def summarize_stock_unusual_record(row: dict[str, Any], source: str) -> dict[str, Any]:
    label = str(pick_row_value(row, [
        "unusual_type", "type", "signal_type", "indicator_type", "indicator_name", "event_type", "title",
    ], source))
    value = str(pick_row_value(row, [
        "description", "desc", "content", "signal_name", "name", "value", "price", "volume",
    ], "--"))
    detail = str(pick_row_value(row, [
        "time", "update_time", "date", "market_time", "security_name", "code",
    ], source))
    tone = "up" if any(token in value.lower() for token in ["buy", "rise", "up", "bull", "增", "涨"]) else "down" if any(token in value.lower() for token in ["sell", "fall", "down", "bear", "减", "跌"]) else "flat"
    return {"label": label[:18], "value": value[:64], "detail": detail[:32], "tone": tone, "source": source}


def build_stock_unusual(
    snapshot: dict[str, Any],
    order_book: dict[str, list[dict[str, Any]]],
    ticker: list[dict[str, Any]],
    technical: list[dict[str, Any]],
    financial: list[dict[str, Any]],
    short_interest: list[dict[str, Any]],
    daily_short: list[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    bids = order_book.get("bids") or []
    asks = order_book.get("asks") or []
    bid_volume = sum(pct(row.get("volume")) for row in bids)
    ask_volume = sum(pct(row.get("volume")) for row in asks)
    imbalance = (bid_volume - ask_volume) / max(bid_volume + ask_volume, 1) * 100
    top_bid = pct((bids[0] or {}).get("price")) if bids else 0
    top_ask = pct((asks[0] or {}).get("price")) if asks else 0
    spread_pct = (top_ask - top_bid) / max((top_ask + top_bid) / 2, 1) * 100 if top_bid and top_ask else 0
    if top_bid and top_ask:
        rows.append({
            "label": "盘口价差",
            "value": f"{spread_pct:.3f}%",
            "detail": f"{top_bid:.2f} / {top_ask:.2f}",
            "tone": "down" if spread_pct > 0.08 else "up",
            "source": "order_book",
        })
    if bids or asks:
        rows.append({
            "label": "买卖盘倾斜",
            "value": f"{imbalance:+.1f}%",
            "detail": f"买{bid_volume:.0f} / 卖{ask_volume:.0f}",
            "tone": "up" if imbalance > 0 else "down" if imbalance < 0 else "flat",
            "source": "order_book",
        })
    if ticker:
        buy_volume = sum(pct(row.get("volume")) for row in ticker if str(row.get("ticker_direction")).upper() == "BUY")
        sell_volume = sum(pct(row.get("volume")) for row in ticker if str(row.get("ticker_direction")).upper() == "SELL")
        rows.append({
            "label": "逐笔主动性",
            "value": f"{buy_volume - sell_volume:+.0f}",
            "detail": f"买{buy_volume:.0f} / 卖{sell_volume:.0f}",
            "tone": "up" if buy_volume > sell_volume else "down" if sell_volume > buy_volume else "flat",
            "source": "ticker",
        })
    amplitude = pct(snapshot.get("amplitude"))
    if amplitude:
        rows.append({
            "label": "日内振幅",
            "value": f"{amplitude:.2f}%",
            "detail": snapshot.get("update_time") or "",
            "tone": "down" if amplitude > 4 else "flat",
            "source": "snapshot",
        })

    for row in technical[:4]:
        rows.append(summarize_stock_unusual_record(row, "技术异动"))
    for row in financial[:4]:
        rows.append(summarize_stock_unusual_record(row, "财务异动"))
    for row in short_interest[:2]:
        rows.append(summarize_stock_unusual_record(row, "空头持仓"))
    for row in daily_short[:2]:
        rows.append(summarize_stock_unusual_record(row, "卖空成交"))

    return clean_json_value({
        "rows": rows[:12],
        "technical": technical[:8],
        "financial": financial[:8],
        "short_interest": short_interest[:6],
        "daily_short": daily_short[:6],
        "imbalance_pct": round(imbalance, 2),
        "spread_pct": round(spread_pct, 4),
    })


def build_stock_ai_news_summary(
    meta: dict[str, Any],
    snapshot: dict[str, Any],
    valuation: dict[str, Any],
    flow_total: float,
    main_flow_total: float,
    unusual: dict[str, Any],
) -> dict[str, Any]:
    change_pct = pct(snapshot.get("change_rate"))
    percentile = pct(valuation.get("valuation_percentile"))
    if change_pct > 0 and flow_total >= 0:
        bias = "偏多观察"
    elif change_pct < 0 and flow_total <= 0:
        bias = "偏空观察"
    else:
        bias = "分歧观察"
    confidence = min(86, 48 + abs(change_pct) * 4 + min(abs(flow_total) / 1_000_000, 18))
    bullets = [
        f"价格变化 {change_pct:+.2f}%，资金净流入 {flow_total:.0f}，主力净额 {main_flow_total:.0f}。",
        f"估值分位 {percentile:.1f}%，PE TTM {pct(valuation.get('pe_ttm_ratio')):.2f}，PB {pct(valuation.get('pb_ratio')):.2f}。",
    ]
    top_unusual = (unusual.get("rows") or [])[:2]
    for row in top_unusual:
        bullets.append(f"{row.get('label')}: {row.get('value')} {row.get('detail')}".strip())
    return {
        "source": "本地AI摘要",
        "bias": bias,
        "confidence": round(confidence, 1),
        "summary": f"{meta.get('symbol')} 当前为{bias}：把价格、资金、估值和盘口异动合并观察，不直接触发实盘下单。",
        "bullets": bullets[:5],
        "updated_at": now_ms(),
    }


def cache_futu_deep(symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    key = stock_meta(symbol)["symbol"]
    FUTU_DEEP_CACHE[key] = {"time": now_ms(), "payload": payload}
    return payload


def read_futu_deep_stock(symbol: str = "AAPL", force: bool = False, max_age_ms: int = 30000) -> dict[str, Any]:
    text = (symbol or "AAPL").upper()
    meta = stock_meta(text)
    code = futu_code(text)
    cached = FUTU_DEEP_CACHE.get(meta["symbol"]) or {}
    if not force and now_ms() - int(cached.get("time") or 0) < max_age_ms and isinstance(cached.get("payload"), dict):
        payload = dict(cached["payload"])
        payload["cached"] = True
        return payload
    status = futu_status_snapshot()
    if not status.get("opend_online"):
        return cache_futu_deep(meta["symbol"], {"ok": False, "symbol": meta["symbol"], "source": "futu", "status": status, "error": status.get("message", "OpenD offline")})
    futu, _ = import_futu_sdk()
    if not futu:
        return cache_futu_deep(meta["symbol"], {"ok": False, "symbol": meta["symbol"], "source": "futu", "status": status, "error": "futu-api not installed"})

    errors: list[dict[str, str]] = []
    quote_ctx = None

    def record_error(block: str, error: Any) -> None:
        message = str(error or "")
        if message:
            errors.append({"block": block, "error": message[:240]})

    def call_records(block: str, fn: Any, limit: int = 20, tail: bool = False) -> list[dict[str, Any]]:
        try:
            result = fn()
            ret, data = result[0], result[1] if len(result) > 1 else None
            if ret != futu.RET_OK:
                record_error(block, data)
                return []
            return futu_frame_records(data, limit, tail)
        except Exception as exc:
            record_error(block, exc)
            return []

    try:
        quote_ctx = futu.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        market_state = call_records("market_state", lambda: quote_ctx.get_market_state([code]), 1)
        snapshot_rows = call_records("market_snapshot", lambda: quote_ctx.get_market_snapshot([code]), 1)
        snapshot = snapshot_rows[0] if snapshot_rows else {}

        subtypes = [
            futu.SubType.ORDER_BOOK,
            futu.SubType.TICKER,
            futu.SubType.RT_DATA,
            futu.SubType.BROKER,
        ]
        try:
            ret, sub_msg = quote_ctx.subscribe([code], subtypes, is_first_push=False, subscribe_push=False, extended_time=True)
            if ret != futu.RET_OK:
                record_error("subscribe", sub_msg)
            else:
                time.sleep(0.25)
        except Exception as exc:
            record_error("subscribe", exc)

        order_book_raw: dict[str, Any] = {}
        try:
            ret, data = quote_ctx.get_order_book(code, num=10)
            if ret == futu.RET_OK and isinstance(data, dict):
                order_book_raw = data
            else:
                record_error("order_book", data)
        except Exception as exc:
            record_error("order_book", exc)

        ticker = call_records("rt_ticker", lambda: quote_ctx.get_rt_ticker(code, num=20), 20, True)
        rt_data = call_records("rt_data", lambda: quote_ctx.get_rt_data(code), 30, True)
        broker_queue = call_records("broker_queue", lambda: quote_ctx.get_broker_queue(code), 20, False)
        capital_flow = call_records("capital_flow", lambda: quote_ctx.get_capital_flow(code), 60, True)
        capital_distribution_rows = call_records("capital_distribution", lambda: quote_ctx.get_capital_distribution(code), 1)
        capital_distribution = capital_distribution_rows[0] if capital_distribution_rows else {}
        order_book = futu_order_book_levels(order_book_raw)

        valuation_payload: dict[str, Any] = {}
        try:
            ret, data = quote_ctx.get_valuation_detail(code)
            if ret == futu.RET_OK and isinstance(data, dict):
                valuation_payload = clean_json_value(data)
            elif ret != futu.RET_OK:
                record_error("valuation_detail", data)
        except Exception as exc:
            record_error("valuation_detail", exc)

        institutional = call_records("shareholders_institutional", lambda: quote_ctx.get_shareholders_institutional(code, num=10), 10)
        rating = call_records("research_rating", lambda: quote_ctx.get_research_rating_summary(code, num=10), 10)
        technical_unusual = call_records("technical_unusual", lambda: quote_ctx.get_technical_unusual(code), 8)
        financial_unusual = call_records("financial_unusual", lambda: quote_ctx.get_financial_unusual(code), 8)
        short_interest = call_records("short_interest", lambda: quote_ctx.get_short_interest(code, num=6), 6)
        daily_short = call_records("daily_short_volume", lambda: quote_ctx.get_daily_short_volume(code, num=6), 6)

        flow_total = round(sum(pct(row.get("in_flow")) for row in capital_flow), 2)
        main_flow_total = round(sum(pct(row.get("super_in_flow")) + pct(row.get("big_in_flow")) for row in capital_flow), 2)
        dist = {
            "super_net": round(pct(capital_distribution.get("capital_in_super")) - pct(capital_distribution.get("capital_out_super")), 2),
            "big_net": round(pct(capital_distribution.get("capital_in_big")) - pct(capital_distribution.get("capital_out_big")), 2),
            "mid_net": round(pct(capital_distribution.get("capital_in_mid")) - pct(capital_distribution.get("capital_out_mid")), 2),
            "small_net": round(pct(capital_distribution.get("capital_in_small")) - pct(capital_distribution.get("capital_out_small")), 2),
            "update_time": capital_distribution.get("update_time", ""),
        }

        state_text = (market_state[0] or {}).get("market_state", "") if market_state else ""
        last_price = pct(snapshot.get("last_price"))
        prev_close = pct(snapshot.get("prev_close_price"))
        change_pct = (last_price / prev_close - 1) * 100 if last_price > 0 and prev_close > 0 else pct(snapshot.get("change_rate"))
        watch_detail = compact_stock_watch_detail(meta, code, snapshot, state_text)
        valuation = compact_valuation_detail(snapshot, valuation_payload)
        unusual = build_stock_unusual(snapshot, order_book, ticker, technical_unusual, financial_unusual, short_interest, daily_short)
        ai_news_summary = build_stock_ai_news_summary(meta, snapshot, valuation, flow_total, main_flow_total, unusual)
        metrics = [
            {"label": "最新", "value": last_price, "format": "price"},
            {"label": "涨跌", "value": round(change_pct, 2), "format": "pct", "tone": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"},
            {"label": "盘前", "value": pct(snapshot.get("pre_price")), "format": "price"},
            {"label": "盘后", "value": pct(snapshot.get("after_price")), "format": "price"},
            {"label": "夜盘", "value": pct(snapshot.get("overnight_price")), "format": "price"},
            {"label": "量比", "value": pct(snapshot.get("volume_ratio")), "format": "x"},
            {"label": "换手", "value": pct(snapshot.get("turnover_rate")), "format": "pct"},
            {"label": "振幅", "value": pct(snapshot.get("amplitude")), "format": "pct"},
            {"label": "PE TTM", "value": pct(snapshot.get("pe_ttm_ratio")), "format": "plain"},
            {"label": "PB", "value": pct(snapshot.get("pb_ratio")), "format": "plain"},
            {"label": "市值", "value": pct(snapshot.get("total_market_val")), "format": "compact"},
            {"label": "52周区间", "value": f"{pct(snapshot.get('lowest52weeks_price')):.2f} / {pct(snapshot.get('highest52weeks_price')):.2f}", "format": "text"},
        ]

        return cache_futu_deep(meta["symbol"], {
            "ok": True,
            "symbol": meta["symbol"],
            "name": snapshot.get("name") or meta.get("name"),
            "futu_code": code,
            "source": "futu",
            "market_state": state_text,
            "summary": f"{meta['symbol']} · {state_text or '--'} · FutuOpenD 增强数据",
            "snapshot": snapshot,
            "metrics": metrics,
            "watch_detail": watch_detail,
            "valuation": valuation,
            "unusual": unusual,
            "institutional": institutional,
            "rating": rating,
            "ai_news_summary": ai_news_summary,
            "order_book": order_book,
            "ticker": ticker,
            "rt_data": rt_data,
            "capital_flow": {
                "rows": capital_flow,
                "net_total": flow_total,
                "main_net_total": main_flow_total,
                "latest_time": capital_flow[-1].get("capital_flow_item_time", "") if capital_flow else "",
            },
            "capital_distribution": {
                "raw": capital_distribution,
                "net": dist,
            },
            "broker_queue": broker_queue,
            "errors": errors[:8],
            "updated_at": now_ms(),
            "live_trading_hard_block": LIVE_TRADING_HARD_BLOCK,
        })
    except Exception as exc:
        return cache_futu_deep(meta["symbol"], {"ok": False, "symbol": meta["symbol"], "source": "futu", "status": status, "error": str(exc), "errors": errors})
    finally:
        try:
            if quote_ctx:
                quote_ctx.close()
        except Exception:
            pass
