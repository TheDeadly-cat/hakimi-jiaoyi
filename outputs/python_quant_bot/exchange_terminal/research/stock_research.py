from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Callable

try:
    from config import STOCK_MARKETS
    from market_data.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
    from market_data.stock_candles_io import read_stock_persistent_candle_cache
    from market_data.stocks import stock_meta, stock_session_from_ts, stock_timezone, yahoo_stock_symbol
    from utils import average, now_ms, pct
except ModuleNotFoundError:
    from exchange_terminal.config import STOCK_MARKETS
    from exchange_terminal.market_data.stock_candle_quality import analyze_stock_candle_series, stock_candle_quality_public
    from exchange_terminal.market_data.stock_candles_io import read_stock_persistent_candle_cache
    from exchange_terminal.market_data.stocks import stock_meta, stock_session_from_ts, stock_timezone, yahoo_stock_symbol
    from exchange_terminal.utils import average, now_ms, pct


QuoteReader = Callable[[str], dict[str, Any]]
StatusRowBuilder = Callable[[str, str, str, str], dict[str, Any]]
QuoteSummaryReader = Callable[[str], dict[str, Any]]
CalendarEventsReader = Callable[[str, dict[str, Any]], list[dict[str, Any]]]
FundamentalSnapshotBuilder = Callable[[str, dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]


def default_status_row(name: str, status: str, detail: str, priority: str = "P2") -> dict[str, Any]:
    clean_status = status if status in {"PASS", "WATCH", "BLOCK"} else "WATCH"
    return {"name": name, "status": clean_status, "detail": detail, "priority": priority}


def stock_news_items_fast(symbol: str, quote: dict[str, Any], unusual: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    meta = stock_meta(symbol)
    news: list[dict[str, Any]] = []
    yahoo_symbol = yahoo_stock_symbol(meta["symbol"])
    urls = [
        ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?" + urllib.parse.urlencode({"s": yahoo_symbol, "region": "US", "lang": "en-US"})),
        ("Yahoo Finance Market", "https://feeds.finance.yahoo.com/rss/2.0/headline?" + urllib.parse.urlencode({"s": "^GSPC", "region": "US", "lang": "en-US"})),
    ]
    seen: set[str] = set()
    for source, url in urls:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HakimiTrade/2.0"})
            with urllib.request.urlopen(request, timeout=0.8) as response:
                root = ET.fromstring(response.read())
            for item in root.findall(".//item")[:limit]:
                title = (item.findtext("title") or "").strip()
                if title and title not in seen:
                    seen.add(title)
                    news.append({
                        "source": source,
                        "title": title,
                        "link": (item.findtext("link") or "").strip(),
                        "published": (item.findtext("pubDate") or "").strip(),
                        "category": "股票新闻",
                    })
                if len(news) >= limit:
                    return news[:limit]
        except Exception:
            continue
    return stock_local_news_items(meta["symbol"], quote, unusual, limit)


def stock_local_news_items(symbol: str, quote: dict[str, Any], unusual: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    meta = stock_meta(symbol)
    change = pct(quote.get("change24h_pct", 0.0))
    return [
        {"source": "本地股票摘要", "title": f"{meta['symbol']} {meta.get('name', '')}: 现价 {pct(quote.get('last')):.2f}, 当日 {change:+.2f}%", "published": quote.get("date", ""), "link": "", "category": "行情快照"},
        {"source": "本地股票摘要", "title": f"{meta.get('sector', 'Stock')} 同业联动需要复核：观察同组股票是否同步放量或分化。", "published": "", "link": "", "category": "行业联动"},
        {"source": "异常成交摘要", "title": unusual.get("headline", "等待成交量、跳空、振幅异常样本。"), "published": unusual.get("updated_label", ""), "link": "", "category": "异常成交"},
    ][:limit]


def stock_quality_age_label(ts: Any) -> str:
    stamp = int(pct(ts, 0))
    if stamp <= 0:
        return "无时间戳"
    age_ms = max(0, now_ms() - stamp)
    minutes = age_ms / 60000
    if minutes < 2:
        return "2分钟内"
    if minutes < 60:
        return f"{minutes:.0f}分钟前"
    hours = minutes / 60
    if hours < 48:
        return f"{hours:.1f}小时前"
    return f"{hours / 24:.1f}天前"


def stock_quality_age_ms(ts: Any) -> int:
    stamp = int(pct(ts, 0))
    return max(0, now_ms() - stamp) if stamp > 0 else 0


def stock_quality_card(key: str, label: str, status: str, value: str, detail: str, tone: str = "flat") -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "value": value,
        "detail": detail,
        "tone": tone,
    }


def stock_research_quality_fast(
    symbol: str,
    quote: dict[str, Any],
    session: dict[str, Any],
    daily_swing: dict[str, Any],
    news: list[dict[str, Any]],
    calendar_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote_source = str(quote.get("source") or "quote")
    quote_ts = quote.get("ts") or quote.get("latest_ts") or 0
    quote_lower = quote_source.lower()
    quote_is_seed = "offline" in quote_lower or "seed" in quote_lower
    quote_is_cache = "cache" in quote_lower or "sqlite" in quote_lower
    quote_age_ms = stock_quality_age_ms(quote_ts)
    quote_is_old = quote_age_ms > 12 * 60 * 60 * 1000
    quote_quality = quote.get("quote_quality") if isinstance(quote.get("quote_quality"), dict) else {}
    quote_review = bool(quote_quality.get("quarantined"))
    quote_degraded = str(quote_quality.get("status") or "").upper() == "DEGRADED"
    quote_status = "REVIEW" if quote_review else "OLD_CACHE" if quote_is_old and quote_is_cache else "CACHE" if quote_is_cache else "SEED" if quote_is_seed else "DELAYED" if quote_is_old or quote_degraded else "READY"
    quote_tone = "down" if quote_review or quote_is_seed or quote_is_old else "flat" if quote_is_cache or quote_degraded else "up"
    session_rows = session.get("rows", []) if isinstance(session, dict) else []
    session_ready = len([row for row in session_rows if row.get("status") == "READY"])
    local_news = len([row for row in news if str(row.get("source", "")).startswith("本地") or row.get("source") == "异常成交摘要"])
    external_news = max(0, len(news) - local_news)
    external_events = len([
        row for row in calendar_rows
        if "等待外部" not in str(row.get("title", "")) and str(row.get("category", "")) not in {"基本面", "异常成交"}
    ])
    cards = [
        stock_quality_card(
            "quote",
            "报价",
            quote_status,
            quote_source,
            f"{stock_quality_age_label(quote_ts)} / {quote_quality.get('change_basis_label') or '涨跌基准待确认'} / 最新价 {pct(quote.get('last', 0.0)):.2f}",
            quote_tone,
        ),
        stock_quality_card(
            "daily",
            "日线",
            "READY" if daily_swing.get("ok") else "WAIT",
            str(daily_swing.get("source") or "daily"),
            daily_swing.get("summary") or "等待日线缓存",
            daily_swing.get("tone", "flat"),
        ),
        stock_quality_card(
            "session",
            "盘前盘后",
            "READY" if session_ready else "WAIT",
            f"{session_ready}/{len(session_rows) or 4}",
            f"{session.get('source') or 'session'} / {session.get('latest_at') or stock_quality_age_label(session.get('latest_ts'))}",
            "up" if session_ready >= 2 else "flat" if session_ready else "down",
        ),
        stock_quality_card(
            "news",
            "新闻",
            "WAIT" if external_news == 0 else "READY",
            f"{external_news}外部/{local_news}本地",
            "首屏先用本地摘要；等待异步 RSS/Yahoo 新闻补全。" if external_news == 0 else "外部新闻已返回，仍需人工核对来源和时间。",
            "up" if external_news else "flat",
        ),
        stock_quality_card(
            "calendar",
            "财报事件",
            "WAIT" if external_events == 0 else "READY",
            f"{external_events}外部/{len(calendar_rows)}总计",
            "首屏为本地事件框架；等待异步财报、估值、评级数据补全。" if external_events == 0 else "财报/估值/评级已由外部摘要补全。",
            "up" if external_events else "flat",
        ),
    ]
    ready = len([row for row in cards if row["status"] in {"READY", "CACHE", "DELAYED"}])
    blocked = len([row for row in cards if row["status"] == "SEED"])
    degraded = len([row for row in cards if row["status"] in {"OLD_CACHE", "REVIEW"}])
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "summary": f"股票数据可信度：{ready}/{len(cards)} 项可用，{degraded} 项旧缓存，{blocked} 项离线兜底；全部结论仅研究观察。",
        "cards": cards,
        "source": "local_first",
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "updated_at": now_ms(),
    }


def stock_news_calendar_quality_fast(
    symbol: str,
    news: list[dict[str, Any]],
    events: list[dict[str, Any]],
    fundamentals: dict[str, Any],
    source: str,
    latency_ms: int,
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    external_news = len([row for row in news if not str(row.get("source", "")).startswith("本地") and row.get("source") != "异常成交摘要"])
    fundamental_rows = fundamentals.get("rows", []) if isinstance(fundamentals, dict) else []
    fundamental_summary = fundamentals.get("summary", "") if isinstance(fundamentals, dict) else ""
    fundamentals_external = bool(fundamental_rows) and source != "local" and "暂未返回" not in str(fundamental_summary)
    external_events = len([
        row for row in events
        if "等待外部" not in str(row.get("title", "")) and str(row.get("category", "")) not in {"基本面", "异常成交"}
    ])
    cards = [
        stock_quality_card(
            "news",
            "新闻",
            "READY" if external_news else "WAIT",
            f"{external_news}外部/{len(news)}总计",
            f"{source} / {latency_ms}ms；新闻只做催化线索，不等于交易结论。",
            "up" if external_news else "flat",
        ),
        stock_quality_card(
            "calendar",
            "财报事件",
            "READY" if external_events else "WAIT",
            f"{external_events}外部/{len(events)}总计",
            "外部财报、估值、评级数据已补全。" if external_events else "外部财报日历暂未返回，继续显示本地观察框架。",
            "up" if external_events else "flat",
        ),
        stock_quality_card(
            "fundamentals",
            "基本面",
            "READY" if fundamentals_external else "WAIT",
            f"{len(fundamental_rows)}项",
            fundamental_summary or "等待基本面数据",
            "up" if fundamentals_external else "flat",
        ),
    ]
    ready = len([row for row in cards if row["status"] == "READY"])
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "summary": f"异步研究数据：{ready}/{len(cards)} 项外部补全，来源 {source}。",
        "cards": cards,
        "source": source,
        "latency_ms": latency_ms,
        "updated_at": now_ms(),
    }


def stock_news_calendar_async(
    symbol: str,
    quote_reader: QuoteReader,
    quote_summary_reader: QuoteSummaryReader,
    calendar_events_reader: CalendarEventsReader,
    fundamental_snapshot_builder: FundamentalSnapshotBuilder,
    limit: int = 8,
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    quote = quote_reader(meta["symbol"])
    unusual = stock_unusual_activity_fast(meta["symbol"], quote)
    started = now_ms()
    news = stock_news_items_fast(meta["symbol"], quote, unusual, limit)
    quote_summary = quote_summary_reader(meta["symbol"])
    events = calendar_events_reader(meta["symbol"], quote_summary)
    if not events:
        events = stock_calendar_events_fast(meta["symbol"], quote, unusual)
    fundamentals = fundamental_snapshot_builder(meta["symbol"], quote_summary, quote, unusual) if quote_summary else {
        "ok": True,
        "symbol": meta["symbol"],
        "rows": stock_calendar_events_fast(meta["symbol"], quote, unusual),
        "summary": "财报和基本面深度数据暂未返回，先使用本地行情事件。",
    }
    merged_events = [*fundamentals.get("rows", [])[:4], *events[:6]]
    source = "rss/yahoo" if quote_summary or any(row.get("source") != "本地股票摘要" for row in news) else "local"
    latency_ms = now_ms() - started
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "news": news[:limit],
        "events": merged_events[:12],
        "fundamentals": fundamentals,
        "data_quality": stock_news_calendar_quality_fast(meta["symbol"], news[:limit], merged_events[:12], fundamentals, source, latency_ms),
        "source": source,
        "latency_ms": latency_ms,
        "updated_at": now_ms(),
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


def stock_session_snapshot_fast(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
    meta = stock_meta(symbol)
    payload = read_stock_persistent_candle_cache(meta["symbol"], 260, "1m", "all") or {
        "rows": [],
        "source": quote.get("source", "quote"),
        "latest_ts": quote.get("ts", now_ms()),
    }
    rows = list(payload.get("rows") or [])
    latest_ts = int(pct(payload.get("latest_ts", 0), 0)) or max(
        [int(pct(row.get("ts", 0), 0)) for row in rows] or [int(pct(quote.get("ts", now_ms()), now_ms()))]
    )
    latest_date = datetime.fromtimestamp(latest_ts / 1000, stock_timezone(meta["symbol"])).strftime("%Y-%m-%d") if latest_ts else ""
    sessions: dict[str, list[dict[str, Any]]] = {"pre": [], "regular": [], "post": [], "overnight": []}
    for row in rows:
        ts = int(pct(row.get("ts", 0), 0))
        if latest_date and ts and datetime.fromtimestamp(ts / 1000, stock_timezone(meta["symbol"])).strftime("%Y-%m-%d") != latest_date:
            continue
        key = str(row.get("session") or stock_session_from_ts(ts, meta["symbol"]))
        if key in sessions:
            sessions[key].append(row)

    def make_row(label: str, key: str) -> dict[str, Any]:
        items = sessions.get(key, [])
        if not items:
            return {"label": label, "session": key, "status": "WAIT", "detail": "暂无该时段样本", "tone": "flat"}
        first = pct(items[0].get("open", items[0].get("close", 0)))
        last = pct(items[-1].get("close", first))
        change = (last / max(first, 1e-9) - 1) * 100 if first > 0 and last > 0 else 0.0
        volume = sum(pct(item.get("volume", 0)) for item in items)
        return {
            "label": label,
            "session": key,
            "status": "READY",
            "detail": f"收 {last:.2f} / {change:+.2f}% / 量 {volume:.0f}",
            "change_pct": round(change, 2),
            "last": round(last, 4),
            "volume": round(volume, 2),
            "tone": "up" if change > 0 else "down" if change < 0 else "flat",
        }

    return {
        "ok": True,
        "symbol": meta["symbol"],
        "source": payload.get("origin_source") or payload.get("source") or quote.get("source", "stock"),
        "latest_ts": latest_ts,
        "latest_at": payload.get("latest_at", quote.get("time", "")),
        "updated_label": payload.get("latest_at") or quote.get("time", ""),
        "quote": quote,
        "rows": [make_row("盘前", "pre"), make_row("盘中", "regular"), make_row("盘后", "post"), make_row("夜盘", "overnight")],
        "summary": f"{meta['symbol']} 分时、盘前和盘后来自本地K线缓存，仅用于研究观察。",
    }


def stock_unusual_activity_fast(symbol: str, quote: dict[str, Any]) -> dict[str, Any]:
    meta = stock_meta(symbol)
    payload = read_stock_persistent_candle_cache(meta["symbol"], 90, "1d", "regular") or {
        "rows": [],
        "source": quote.get("source", "quote"),
        "latest_ts": quote.get("ts", now_ms()),
    }
    raw_rows = list(payload.get("rows") or [])
    candle_quality = analyze_stock_candle_series(raw_rows, minimum_analysis_rows=20)
    rows = list(candle_quality.get("analysis_rows") or [])
    latest = rows[-1] if rows else {}
    prev = rows[-2] if len(rows) >= 2 else {}
    quote_quality = quote.get("quote_quality") if isinstance(quote.get("quote_quality"), dict) else {}
    use_quote_ohlc = bool(candle_quality.get("has_break")) and len(rows) < 2 and not quote_quality.get("quarantined")
    volumes = [pct(row.get("volume", 0.0)) for row in rows if pct(row.get("volume", 0.0)) > 0]
    recent_volume = pct(quote.get("vol24h", latest.get("volume", 0.0))) if use_quote_ohlc else pct(latest.get("volume", quote.get("vol24h", 0.0)))
    baseline = average(volumes[-21:-1]) if len(volumes) >= 22 else average(volumes[:-1]) if len(volumes) > 1 else recent_volume
    volume_ratio = recent_volume / max(baseline, 1e-9) if baseline > 0 and recent_volume > 0 else 1.0
    open_price = pct(quote.get("open24h", latest.get("open", 0.0))) if use_quote_ohlc else pct(latest.get("open", quote.get("open24h", 0.0)))
    high = pct(quote.get("high24h", latest.get("high", 0.0))) if use_quote_ohlc else pct(latest.get("high", quote.get("high24h", 0.0)))
    low = pct(quote.get("low24h", latest.get("low", 0.0))) if use_quote_ohlc else pct(latest.get("low", quote.get("low24h", 0.0)))
    close = pct(quote.get("last", latest.get("close", 0.0))) if use_quote_ohlc else pct(latest.get("close", quote.get("last", 0.0)))
    quote_is_quarantined = bool(quote_quality.get("quarantined"))
    quote_change = 0.0 if candle_quality.get("has_break") and len(rows) < 2 and quote_is_quarantined else pct(quote.get("change24h_pct", 0.0))
    quote_prev_close = 0.0 if quote_is_quarantined else pct(quote.get("prevClose", quote_quality.get("previous_close", 0.0)))
    prev_close = pct(prev.get("close", quote_prev_close))
    has_comparable_previous = len(rows) >= 2 and prev_close > 0
    change = (close / max(prev_close, 1e-9) - 1) * 100 if close > 0 and has_comparable_previous else quote_change
    range_pct = (high / max(low, 1e-9) - 1) * 100 if high > 0 and low > 0 else abs(change)
    gap_basis = prev_close if has_comparable_previous else quote_prev_close
    gap_pct = (open_price / max(gap_basis, 1e-9) - 1) * 100 if open_price > 0 and gap_basis > 0 else 0.0
    flags: list[str] = []
    if candle_quality.get("has_break"):
        flags.append("日线复权断点待核")
    if volume_ratio >= 1.6 and len(volumes) > 1:
        flags.append(f"成交量 {volume_ratio:.2f}x")
    if abs(gap_pct) >= 1.2:
        flags.append(f"跳空 {gap_pct:+.2f}%")
    if range_pct >= 3.2:
        flags.append(f"日内振幅 {range_pct:.2f}%")
    if abs(change) >= 2.5:
        flags.append(f"价格异动 {change:+.2f}%")
    headline = f"{meta['symbol']} " + (" / ".join(flags) if flags else "暂无明显异常成交，继续观察量价确认。")
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "headline": headline,
        "volume_ratio": round(volume_ratio, 2),
        "gap_pct": round(gap_pct, 2),
        "range_pct": round(range_pct, 2),
        "change_pct": round(change, 2),
        "recent_volume": round(recent_volume, 2),
        "baseline_volume": round(baseline, 2),
        "flags": flags,
        "data_quality": stock_candle_quality_public(candle_quality),
        "updated_label": payload.get("latest_at", "") or quote.get("time", ""),
        "rows": [
            {"symbol": meta["symbol"], "label": "成交量倍率", "value": f"{volume_ratio:.2f}x" if len(volumes) > 1 else "待核", "change24h_pct": volume_ratio - 1, "reason": "最近一日成交量相对20日均量" if len(volumes) > 1 else "复权断点后样本不足，暂停量比判断"},
            {"symbol": meta["symbol"], "label": "跳空", "value": f"{gap_pct:+.2f}%", "change24h_pct": gap_pct, "reason": "今日开盘相对前收"},
            {"symbol": meta["symbol"], "label": "振幅", "value": f"{range_pct:.2f}%", "change24h_pct": range_pct, "reason": "日内高低点区间"},
        ],
    }


def stock_daily_swing_fast(symbol: str, quote: dict[str, Any], unusual: dict[str, Any]) -> dict[str, Any]:
    meta = stock_meta(symbol)
    payload = read_stock_persistent_candle_cache(meta["symbol"], 260, "1d", "regular") or {
        "rows": [],
        "source": quote.get("source", "quote"),
        "latest_ts": quote.get("ts", now_ms()),
    }
    raw_rows = [
        row for row in list(payload.get("rows") or [])
        if pct(row.get("close", 0.0)) > 0 and pct(row.get("high", 0.0)) > 0 and pct(row.get("low", 0.0)) > 0
    ]
    candle_quality = analyze_stock_candle_series(raw_rows, minimum_analysis_rows=20)
    rows = list(candle_quality.get("analysis_rows") or [])
    close = pct(rows[-1].get("close", quote.get("last", 0.0))) if rows else pct(quote.get("last", 0.0))
    if not rows or close <= 0:
        return {
            "ok": False,
            "symbol": meta["symbol"],
            "stage": "等待日线样本",
            "summary": "日线缓存不足，先只做价格和分时观察。",
            "source": payload.get("source") or quote.get("source", "stock"),
            "cards": [
                {"label": "日线波段", "value": "等待", "detail": "需要日线K线缓存", "tone": "flat"},
            ],
            "waiting_conditions": ["等待日线样本补齐后再判断波段结构。"],
        }

    if candle_quality.get("has_break") and not candle_quality.get("analysis_ready"):
        segment_rows = int(candle_quality.get("segment_rows") or 0)
        warning = str(candle_quality.get("warning") or "检测到日线价格尺度断点。")
        quote_change = pct(quote.get("change24h_pct", 0.0))
        return {
            "ok": False,
            "symbol": meta["symbol"],
            "stage": "复权断点待核",
            "tone": "flat",
            "source": payload.get("origin_source") or payload.get("source") or quote.get("source", "stock"),
            "latest_at": payload.get("latest_at", quote.get("time", "")),
            "close": round(close, 4),
            "summary": f"{warning} 断点后仅 {segment_rows} 根日线，暂停20/60日趋势和支撑压力计算。",
            "cards": [
                {"label": "日线波段", "value": "暂停计算", "detail": f"断点后 {segment_rows} 根K线，至少需要20根同口径样本", "tone": "flat"},
                {"label": "数据尺度", "value": "待核", "detail": warning, "tone": "down"},
                {"label": "当前报价", "value": f"{close:.2f}", "detail": f"当日 {quote_change:+.2f}%，仅用于当前行情观察", "tone": "up" if quote_change > 0 else "down" if quote_change < 0 else "flat"},
            ],
            "evidence": [warning, f"断点后可比日线样本：{segment_rows} 根。"],
            "counter_evidence": ["当前报价可用于盘中观察，但不能与断点前日线直接比较。"],
            "waiting_conditions": [
                "重新拉取统一前复权或统一不复权的日线序列。",
                "至少积累20根同口径日线后，再恢复波段、均线和支撑压力判断。",
                "修复前只观察当日价格、分时和盘口，不采用旧日线涨幅结论。",
            ],
            "data_quality": stock_candle_quality_public(candle_quality),
            "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        }

    closes = [pct(row.get("close", 0.0)) for row in rows]
    volumes = [pct(row.get("volume", 0.0)) for row in rows if pct(row.get("volume", 0.0)) > 0]

    def avg_last(count: int) -> float:
        values = closes[-count:]
        return average(values) if values else close

    ma20 = avg_last(20)
    ma50 = avg_last(50 if len(closes) >= 50 else min(len(closes), 20))
    ma200 = avg_last(200 if len(closes) >= 200 else min(len(closes), 60))
    window20 = rows[-20:] if len(rows) >= 20 else rows
    window60 = rows[-60:] if len(rows) >= 60 else rows
    support20 = min(pct(row.get("low", close)) for row in window20)
    resistance20 = max(pct(row.get("high", close)) for row in window20)
    support60 = min(pct(row.get("low", close)) for row in window60)
    resistance60 = max(pct(row.get("high", close)) for row in window60)
    base20 = pct(window20[0].get("close", close)) if window20 else close
    change20 = (close / max(base20, 1e-9) - 1) * 100 if base20 > 0 else 0.0
    range20 = (resistance20 / max(support20, 1e-9) - 1) * 100 if resistance20 > 0 and support20 > 0 else 0.0
    position20 = ((close - support20) / max(resistance20 - support20, 1e-9)) * 100 if resistance20 > support20 else 50.0
    breakout_room = (resistance20 / max(close, 1e-9) - 1) * 100 if resistance20 > 0 else 0.0
    downside_room = (close / max(support20, 1e-9) - 1) * 100 if support20 > 0 else 0.0
    drawdown60 = (close / max(resistance60, 1e-9) - 1) * 100 if resistance60 > 0 else 0.0
    volume_ratio = pct(unusual.get("volume_ratio", 1.0), 1.0)
    recent_volume = volumes[-1] if volumes else pct(quote.get("vol24h", 0.0))
    avg_volume20 = average(volumes[-21:-1]) if len(volumes) >= 22 else average(volumes[:-1]) if len(volumes) > 1 else recent_volume

    if close > ma20 > ma50 and change20 > 0:
        stage = "上升波段"
        tone = "up"
    elif close < ma20 < ma50 and change20 < 0:
        stage = "下降波段"
        tone = "down"
    elif close > ma20 and ma20 <= ma50:
        stage = "反弹修复"
        tone = "flat"
    elif close < ma20 and ma20 >= ma50:
        stage = "回调测试"
        tone = "flat"
    elif range20 >= 8:
        stage = "宽幅震荡"
        tone = "flat"
    else:
        stage = "区间整理"
        tone = "flat"

    ma_detail = f"MA20 {ma20:.2f} / MA50 {ma50:.2f}"
    if len(closes) >= 120:
        ma_detail += f" / MA200 {ma200:.2f}"
    volume_state = "放量确认" if volume_ratio >= 1.35 else "缩量观察" if volume_ratio <= 0.75 else "量能中性"
    support_detail = f"20日 {support20:.2f} / 60日 {support60:.2f}"
    resistance_detail = f"20日 {resistance20:.2f} / 60日 {resistance60:.2f}"
    waiting = [
        "等待日线收盘确认，不把盘中波动当成趋势完成。",
        f"向上需要有效站上 {resistance20:.2f} 且量能不低于20日均量。",
        f"向下跌破 {support20:.2f} 后需要降低波段判断强度。",
        "若价格贴近压力但量能不足，优先按假突破风险处理。",
    ]
    evidence = [
        f"日线阶段：{stage}，近20日 {change20:+.2f}%。",
        f"价格处在20日区间约 {max(0, min(100, position20)):.0f}% 分位。",
        f"量能：{volume_state}，最近/20日均量约 {volume_ratio:.2f}x。",
        f"20日支撑 {support20:.2f}，20日压力 {resistance20:.2f}。",
    ]
    counter = [
        "样本来自本地日线缓存，实时性以数据质量卡为准。",
        f"距20日压力 {breakout_room:+.2f}%，距20日支撑 {downside_room:+.2f}%。",
        f"相对60日高点 {drawdown60:+.2f}%，需要防止高位回撤。",
    ]
    cards = [
        {"label": "日线阶段", "value": stage, "detail": f"20日 {change20:+.2f}% / 位置 {max(0, min(100, position20)):.0f}%", "tone": tone},
        {"label": "压力区", "value": f"{resistance20:.2f}", "detail": resistance_detail, "tone": "down"},
        {"label": "支撑区", "value": f"{support20:.2f}", "detail": support_detail, "tone": "up"},
        {"label": "均线结构", "value": "多头" if close > ma20 > ma50 else "空头" if close < ma20 < ma50 else "缠绕", "detail": ma_detail, "tone": "up" if close > ma20 > ma50 else "down" if close < ma20 < ma50 else "flat"},
        {"label": "量能确认", "value": volume_state, "detail": f"{volume_ratio:.2f}x / 20均 {avg_volume20:.0f}", "tone": "up" if volume_ratio >= 1.35 else "down" if volume_ratio <= 0.75 else "flat"},
    ]
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "stage": stage,
        "tone": tone,
        "source": payload.get("origin_source") or payload.get("source") or quote.get("source", "stock"),
        "latest_at": payload.get("latest_at", quote.get("time", "")),
        "close": round(close, 4),
        "ma20": round(ma20, 4),
        "ma50": round(ma50, 4),
        "ma200": round(ma200, 4),
        "support20": round(support20, 4),
        "resistance20": round(resistance20, 4),
        "support60": round(support60, 4),
        "resistance60": round(resistance60, 4),
        "change20_pct": round(change20, 2),
        "range20_pct": round(range20, 2),
        "position20_pct": round(max(0, min(100, position20)), 1),
        "breakout_room_pct": round(breakout_room, 2),
        "downside_room_pct": round(downside_room, 2),
        "volume_ratio": round(volume_ratio, 2),
        "summary": f"{meta['symbol']} 日线：{stage}，20日 {change20:+.2f}%，支撑 {support20:.2f} / 压力 {resistance20:.2f}。",
        "cards": cards,
        "evidence": evidence,
        "counter_evidence": counter,
        "waiting_conditions": waiting,
        "data_quality": stock_candle_quality_public(candle_quality),
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


def stock_sector_linkage_fast(
    symbol: str,
    quote_reader: QuoteReader,
    stock_quote_cache_rows: list[dict[str, Any]] | None = None,
    stock_quote_cache_time: int = 0,
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    sector = str(meta.get("sector") or "Stock")
    peers = [
        item for item in STOCK_MARKETS
        if item["symbol"] != meta["symbol"] and (item.get("sector") == sector or item.get("market") == meta.get("market"))
    ][:6]
    cached_rows = {
        str(row.get("symbol", "")).upper(): row
        for row in (stock_quote_cache_rows or [])
        if now_ms() - int(stock_quote_cache_time or 0) < 600000
    }
    rows: list[dict[str, Any]] = []
    for peer in peers:
        quote = cached_rows.get(peer["symbol"]) or quote_reader(peer["symbol"])
        rows.append({
            "symbol": peer["symbol"],
            "name": peer.get("name", peer["symbol"]),
            "sector": peer.get("sector", ""),
            "last": pct(quote.get("last", 0.0)),
            "change24h_pct": pct(quote.get("change24h_pct", 0.0)),
            "volume": pct(quote.get("vol24h", 0.0)),
            "source": quote.get("source", ""),
            "reason": peer.get("sector", ""),
        })
    avg_change = average([row["change24h_pct"] for row in rows]) if rows else 0.0
    up_count = len([row for row in rows if row["change24h_pct"] > 0])
    down_count = len([row for row in rows if row["change24h_pct"] < 0])
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "sector": sector,
        "avg_change_pct": round(avg_change, 2),
        "summary": f"{sector} 同组：{up_count}涨 {down_count}跌，均值 {avg_change:+.2f}%",
        "rows": sorted(rows, key=lambda row: abs(row["change24h_pct"]), reverse=True),
    }


def related_stock_sectors(sector: str) -> list[str]:
    text = str(sector or "Stock")
    chain_map = {
        "AI Chip": ["AI Chip", "AI Server", "Semi Equipment", "Semiconductor Foundry", "Semiconductor Design", "Semiconductor IP", "Memory / Storage"],
        "AI Server": ["AI Server", "AI Chip", "Memory / Storage", "Semi Equipment"],
        "Semi Equipment": ["Semi Equipment", "AI Chip", "Semiconductor Foundry", "Semiconductor Design"],
        "Semiconductor Foundry": ["Semiconductor Foundry", "AI Chip", "Semi Equipment", "Semiconductor Design"],
        "Semiconductor Design": ["Semiconductor Design", "AI Chip", "Semiconductor IP", "Semiconductor Foundry"],
        "Semiconductor IP": ["Semiconductor IP", "Semiconductor Design", "AI Chip"],
        "Memory / Storage": ["Memory / Storage", "AI Server", "AI Chip", "Semiconductor Foundry"],
        "Mega Cap Tech": ["Mega Cap Tech", "AI Chip", "EV", "Index ETF"],
        "EV": ["EV", "AI Chip", "Mega Cap Tech", "Smart Hardware"],
        "Space / SpaceX proxy": ["Space / SpaceX proxy", "Mega Cap Tech", "AI Chip"],
        "HK Power": ["HK Power", "EV", "Smart Hardware"],
        "China Internet": ["China Internet", "Smart Hardware", "EV"],
    }
    return chain_map.get(text, [text])


def stock_chain_role(sector: str) -> str:
    text = str(sector or "Stock")
    role_map = {
        "AI Chip": "核心芯片",
        "AI Server": "服务器/整机",
        "Semi Equipment": "设备",
        "Semiconductor Foundry": "代工",
        "Semiconductor Design": "芯片设计",
        "Semiconductor IP": "IP/架构",
        "Memory / Storage": "存储/HBM",
        "Mega Cap Tech": "平台/需求端",
        "EV": "电动化需求",
        "Space / SpaceX proxy": "航天链",
        "HK Power": "电力运营",
        "China Internet": "互联网平台",
        "Smart Hardware": "硬件/终端",
        "Index ETF": "指数环境",
        "BTC Proxy": "加密映射",
    }
    return role_map.get(text, text or "产业链")


def stock_chain_label(sector: str) -> str:
    text = str(sector or "Stock")
    if text in {"AI Chip", "AI Server", "Semi Equipment", "Semiconductor Foundry", "Semiconductor Design", "Semiconductor IP", "Memory / Storage"}:
        return "半导体 / AI算力链"
    if text == "HK Power":
        return "港股电力链"
    if text in {"Mega Cap Tech", "EV", "Smart Hardware"}:
        return "科技消费链"
    if text == "Space / SpaceX proxy":
        return "商业航天链"
    return "产业链"


def stock_chain_segment_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        role = str(row.get("role") or stock_chain_role(str(row.get("sector") or "")))
        sector = str(row.get("sector") or "")
        key = f"{role}|{sector}"
        buckets.setdefault(key, []).append(row)

    segments: list[dict[str, Any]] = []
    for items in buckets.values():
        first = items[0]
        changes = [pct(item.get("change24h_pct", 0.0)) for item in items]
        avg_change = average(changes) if changes else 0.0
        up_count = len([value for value in changes if value > 0])
        down_count = len([value for value in changes if value < 0])
        leaders = sorted(items, key=lambda item: abs(pct(item.get("change24h_pct", 0.0))), reverse=True)[:4]
        tone = "up" if avg_change > 0.4 else "down" if avg_change < -0.4 else "flat"
        segments.append({
            "role": first.get("role") or stock_chain_role(str(first.get("sector") or "")),
            "sector": first.get("sector", ""),
            "avg_change_pct": round(avg_change, 2),
            "up_count": up_count,
            "down_count": down_count,
            "count": len(items),
            "tone": tone,
            "symbols": [item.get("symbol", "") for item in leaders if item.get("symbol")],
            "summary": f"{first.get('role') or stock_chain_role(str(first.get('sector') or ''))}：{len(items)}样本，{up_count}涨 {down_count}跌，均值 {avg_change:+.2f}%",
        })
    return sorted(segments, key=lambda row: (abs(pct(row.get("avg_change_pct", 0.0))), int(row.get("count", 0))), reverse=True)


def stock_industry_chain_fast(
    symbol: str,
    quote_reader: QuoteReader,
    stock_quote_cache_rows: list[dict[str, Any]] | None = None,
    stock_quote_cache_time: int = 0,
) -> dict[str, Any]:
    meta = stock_meta(symbol)
    sectors = related_stock_sectors(str(meta.get("sector") or "Stock"))
    cached_rows = {
        str(row.get("symbol", "")).upper(): row
        for row in (stock_quote_cache_rows or [])
        if now_ms() - int(stock_quote_cache_time or 0) < 600000
    }
    peers = [
        item for item in STOCK_MARKETS
        if item["symbol"] != meta["symbol"] and item.get("sector") in sectors
    ][:16]
    rows: list[dict[str, Any]] = []
    for peer in peers:
        quote = cached_rows.get(peer["symbol"]) or quote_reader(peer["symbol"])
        role = stock_chain_role(str(peer.get("sector") or ""))
        rows.append({
            "symbol": peer["symbol"],
            "name": peer.get("name", peer["symbol"]),
            "sector": peer.get("sector", ""),
            "role": role,
            "last": pct(quote.get("last", 0.0)),
            "change24h_pct": pct(quote.get("change24h_pct", 0.0)),
            "volume": pct(quote.get("vol24h", 0.0)),
            "source": quote.get("source", ""),
            "reason": f"{role} / {'同产业链' if peer.get('sector') != meta.get('sector') else '同细分行业'}",
        })
    avg_change = average([row["change24h_pct"] for row in rows]) if rows else 0.0
    top = sorted(rows, key=lambda row: abs(row["change24h_pct"]), reverse=True)
    segments = stock_chain_segment_rows(rows)
    return {
        "ok": True,
        "symbol": meta["symbol"],
        "sector": meta.get("sector", "Stock"),
        "chain_label": stock_chain_label(str(meta.get("sector") or "Stock")),
        "related_sectors": sectors,
        "avg_change_pct": round(avg_change, 2),
        "summary": f"{stock_chain_label(str(meta.get('sector') or 'Stock'))} {len(rows)} 个样本，均值 {avg_change:+.2f}%",
        "segments": segments,
        "rows": top,
    }


def stock_calendar_events_fast(symbol: str, quote: dict[str, Any], unusual: dict[str, Any]) -> list[dict[str, Any]]:
    meta = stock_meta(symbol)
    return [
        {"time": "行情", "title": f"{pct(quote.get('last')):.2f} / {pct(quote.get('change24h_pct')):+.2f}%", "impact": "当前股价和当日涨跌幅，用于判断跳空、趋势延续和回补压力。", "tone": "up" if pct(quote.get("change24h_pct")) > 0 else "down" if pct(quote.get("change24h_pct")) < 0 else "flat", "category": "基本面"},
        {"time": "财报窗口", "title": "等待外部财报日历", "impact": "后续接入正式财报日历；当前先观察盘前盘后和新闻催化。", "category": "财报"},
        {"time": "风险因子", "title": "Beta / 空头 / 机构持仓待接入", "impact": "本轮先保证行情研究不卡顿，深度基本面数据后续异步接入。", "category": "风险"},
        {"time": "量能风险", "title": f"{unusual.get('volume_ratio', 1.0):.2f}x / Gap {unusual.get('gap_pct', 0.0):+.2f}%", "impact": f"日内振幅 {unusual.get('range_pct', 0.0):.2f}%，观察放量是否由新闻、财报或行业联动解释。", "tone": "up" if unusual.get("flags") else "flat", "category": "异常成交"},
    ]


def session_catalyst_summary(session: dict[str, Any]) -> tuple[str, str, str]:
    rows = session.get("rows", []) if isinstance(session, dict) else []
    ready = [row for row in rows if row.get("status") == "READY"]
    changes = [pct(row.get("change_pct", 0.0)) for row in ready]
    tone = "up" if any(value > 0.4 for value in changes) else "down" if any(value < -0.4 for value in changes) else "flat"
    value = f"{len(ready)}/{len(rows) or 4} READY"
    detail = " / ".join(f"{row.get('label', '--')} {pct(row.get('change_pct', 0.0)):+.2f}%" for row in ready[:3]) or "等待盘前/盘中/盘后样本"
    return value, detail, tone


def stock_event_catalysts_fast(
    symbol: str,
    meta: dict[str, Any],
    quote: dict[str, Any],
    session: dict[str, Any],
    unusual: dict[str, Any],
    linkage: dict[str, Any],
    industry_chain: dict[str, Any],
    news: list[dict[str, Any]],
    calendar_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    price_change = pct(quote.get("change24h_pct", 0.0))
    session_value, session_detail, session_tone = session_catalyst_summary(session)
    chain_change = pct(industry_chain.get("avg_change_pct", 0.0))
    sector_change = pct(linkage.get("avg_change_pct", 0.0))
    chain_segments = industry_chain.get("segments") if isinstance(industry_chain.get("segments"), list) else []
    strong_segment = chain_segments[0] if chain_segments else {}
    segment_detail = f" / 强段 {strong_segment.get('role')} {pct(strong_segment.get('avg_change_pct', 0.0)):+.2f}%" if strong_segment else ""
    volume_ratio = pct(unusual.get("volume_ratio", 1.0), 1.0)
    gap_pct = pct(unusual.get("gap_pct", 0.0))
    range_pct = pct(unusual.get("range_pct", 0.0))
    event_titles = " / ".join(row.get("title", "") for row in calendar_rows[:2] if row.get("title")) or "等待外部财报日历"
    news_title = next((row.get("title", "") for row in news if row.get("title")), "等待股票新闻源")
    rows = [
        {
            "key": "earnings_news",
            "label": "财报 / 新闻",
            "status": "READY" if news or calendar_rows else "WAIT",
            "value": f"{len(news)}新闻 / {len(calendar_rows)}事件",
            "detail": f"{event_titles} / {news_title}",
            "tone": "up" if news and calendar_rows else "flat",
            "watch": "确认新闻是否解释放量、跳空或趋势延续；财报窗口前后降低结论强度。",
        },
        {
            "key": "session_flow",
            "label": "盘前 / 盘后",
            "status": "READY" if "READY" in session_value else "WAIT",
            "value": session_value,
            "detail": session_detail,
            "tone": session_tone,
            "watch": "盘前盘后流动性薄，必须等盘中量价确认。",
        },
        {
            "key": "industry_chain",
            "label": "行业链",
            "status": "READY" if industry_chain.get("rows") else "WAIT",
            "value": f"{chain_change:+.2f}%",
            "detail": f"{industry_chain.get('summary', '')} / 同组 {sector_change:+.2f}%{segment_detail}",
            "tone": "up" if chain_change > 0.4 else "down" if chain_change < -0.4 else "flat",
            "watch": "确认同细分行业、上下游和指数是否同向；分化时降低趋势置信。",
        },
        {
            "key": "unusual_trade",
            "label": "异常成交",
            "status": "WATCH" if unusual.get("flags") or range_pct >= 3 else "CALM",
            "value": f"{volume_ratio:.2f}x",
            "detail": f"跳空 {gap_pct:+.2f}% / 振幅 {range_pct:.2f}% / 价格 {price_change:+.2f}%",
            "tone": "up" if volume_ratio >= 1.4 and price_change > 0 else "down" if volume_ratio >= 1.4 and price_change < 0 else "flat",
            "watch": "放量后等第二根K线确认；大振幅时警惕假突破和滑点。",
        },
        {
            "key": "data_quality",
            "label": "数据质量",
            "status": "RESEARCH_ONLY",
            "value": str(quote.get("source") or session.get("source") or "stock"),
            "detail": f"{session.get('latest_at') or quote.get('time') or unusual.get('updated_label') or '等待最新时间'} / 实盘硬墙开启",
            "tone": "flat",
            "watch": "Futu离线或旧缓存时只做观察；等待实时源复核。",
        },
    ]
    focus = " / ".join(f"{row['label']}:{row['value']}" for row in rows[:4])
    return {
        "ok": True,
        "symbol": symbol,
        "summary": focus,
        "rows": rows,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
    }


def stock_research_panel(
    symbol: str,
    quote_reader: QuoteReader,
    status_row_builder: StatusRowBuilder | None = None,
    stock_quote_cache_rows: list[dict[str, Any]] | None = None,
    stock_quote_cache_time: int = 0,
) -> dict[str, Any]:
    status_row = status_row_builder or default_status_row
    meta = stock_meta(symbol)
    quote = quote_reader(meta["symbol"])
    session = stock_session_snapshot_fast(meta["symbol"], quote)
    unusual = stock_unusual_activity_fast(meta["symbol"], quote)
    daily_swing = stock_daily_swing_fast(meta["symbol"], quote, unusual)
    linkage = stock_sector_linkage_fast(meta["symbol"], quote_reader, stock_quote_cache_rows, stock_quote_cache_time)
    industry_chain = stock_industry_chain_fast(meta["symbol"], quote_reader, stock_quote_cache_rows, stock_quote_cache_time)
    news = stock_local_news_items(meta["symbol"], quote, unusual, 8)
    calendar_rows = stock_calendar_events_fast(meta["symbol"], quote, unusual)
    catalysts = stock_event_catalysts_fast(meta["symbol"], meta, quote, session, unusual, linkage, industry_chain, news, calendar_rows)
    quality = stock_research_quality_fast(meta["symbol"], quote, session, daily_swing, news, calendar_rows)
    session_rows = [
        {"symbol": row["label"], "change24h_pct": pct(row.get("change_pct", 0.0)), "volume": pct(row.get("volume", 0.0)), "reason": row.get("detail", "")}
        for row in session.get("rows", [])
    ]
    mover_blocks = [
        {"title": "行业联动", "rows": linkage.get("rows", [])[:5], "summary": linkage.get("summary", "")},
        {"title": "产业链", "rows": industry_chain.get("rows", [])[:5], "summary": industry_chain.get("summary", "")},
        {"title": "异常成交", "rows": unusual.get("rows", [])[:5], "summary": unusual.get("headline", "")},
        {"title": "盘前盘后", "rows": session_rows, "summary": session.get("summary", "")},
    ]
    stock_cards = [
        {"label": "股票新闻", "value": "异步", "detail": "首屏先用本地摘要，外部新闻稍后补全。", "tone": "flat"},
        {"label": "日线波段", "value": daily_swing.get("stage", "--"), "detail": daily_swing.get("summary", "等待日线样本"), "tone": daily_swing.get("tone", "flat")},
        {"label": "财报/事件", "value": str(len(calendar_rows)), "detail": "财报窗口、估值、风险和量能观察。", "tone": "flat"},
        {"label": "行业联动", "value": linkage.get("summary", "--"), "detail": "观察同组股票同步或分化。", "tone": "up" if pct(linkage.get("avg_change_pct", 0.0)) > 0 else "down" if pct(linkage.get("avg_change_pct", 0.0)) < 0 else "flat"},
        {"label": "产业链", "value": industry_chain.get("summary", "--"), "detail": "上下游和同细分样本，用于过滤单股噪声。", "tone": "up" if pct(industry_chain.get("avg_change_pct", 0.0)) > 0 else "down" if pct(industry_chain.get("avg_change_pct", 0.0)) < 0 else "flat"},
        {"label": "异常成交", "value": f"{unusual.get('volume_ratio', 1.0)}x", "detail": unusual.get("headline", ""), "tone": "up" if unusual.get("flags") else "flat"},
    ]
    focus_payload = {
        "symbol": meta["symbol"],
        "summary": f"{meta['symbol']} 股票研究：{meta.get('name')} / {meta.get('sector')} / {linkage.get('summary')} / {unusual.get('headline')}",
        "cards": stock_cards,
        "checklist": [
            status_row("股票新闻源", "PASS" if news else "WATCH", f"{len(news)} 条公司/市场新闻或本地摘要", "P0"),
            status_row("价格一致性", "PASS", f"摘要价来自本地K线缓存：{pct(quote.get('last')):.2f}", "P0"),
            status_row("日线波段", "PASS" if daily_swing.get("ok") else "WATCH", daily_swing.get("summary", "等待日线样本"), "P0"),
            status_row("盘前盘后", "PASS" if any(row.get("status") == "READY" for row in session.get("rows", [])) else "WATCH", session.get("summary", ""), "P1"),
            status_row("行业联动", "PASS" if linkage.get("rows") else "WATCH", linkage.get("summary", ""), "P1"),
            status_row("事件催化雷达", "PASS" if catalysts.get("rows") else "WATCH", catalysts.get("summary", ""), "P1"),
            status_row("异常成交", "WATCH" if unusual.get("flags") else "PASS", unusual.get("headline", ""), "P1"),
        ],
        "prompts": [
            f"请按股票研究逻辑分析 {meta['symbol']}：新闻、财报、盘前盘后、行业联动、异常成交分别支持做多还是做空？",
            f"{meta['symbol']} 当前如果只做观察、不下单，最重要的等待条件是什么？请结合财报窗口、成交量和同业走势。",
            f"请复核 {meta['symbol']} 的异常成交：量比、跳空、振幅、行业同步性是否足够支持趋势延续？",
            f"请把 {meta['symbol']} 的股票风险拆成：财报风险、盘前盘后流动性、行业分化、假突破、止损失效条件。",
        ],
    }
    return {
        "ok": True,
        "mode": "stock_research",
        "symbol": meta["symbol"],
        "summary": f"股票研究面板已更新：{meta['symbol']}，价格、新闻、盘前盘后、行业联动、异常成交均按股票逻辑汇总。",
        "focus": focus_payload,
        "news": news[:8],
        "events": calendar_rows[:8],
        "hot": linkage.get("rows", [])[:8],
        "gainers": sorted(linkage.get("rows", []), key=lambda item: item.get("change24h_pct", 0), reverse=True)[:8],
        "losers": sorted(linkage.get("rows", []), key=lambda item: item.get("change24h_pct", 0))[:8],
        "volume": sorted(linkage.get("rows", []), key=lambda item: item.get("volume", 0), reverse=True)[:8],
        "mover_blocks": mover_blocks,
        "stock": {
            "meta": meta,
            "quote": quote,
            "session": session,
            "unusual": unusual,
            "daily_swing": daily_swing,
            "linkage": linkage,
            "industry_chain": industry_chain,
            "catalysts": catalysts,
            "quality": quality,
            "calendar": calendar_rows[:12],
            "fundamentals": {
                "ok": True,
                "symbol": meta["symbol"],
                "rows": calendar_rows,
                "summary": " / ".join(f"{row['time']} {row['title']}" for row in calendar_rows[:3]),
            },
        },
        "async_research": {"news_calendar": "pending", "source": "local_first"},
        "data_quality": quality,
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "live_trading_allowed": False,
        "updated_at": now_ms(),
    }
