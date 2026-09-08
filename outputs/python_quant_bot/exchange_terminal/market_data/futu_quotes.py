from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

try:
    from config import FUTU_HOST, FUTU_PORT
    from market_data.futu import (
        futu_history_ktype,
        futu_history_window,
        futu_status_snapshot,
        import_futu_sdk,
        normalize_futu_quote,
        parse_futu_time_key,
        update_futu_status_cache,
    )
    from hakimi_research.stock_metadata import (
        futu_code,
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_timezone,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        clean_stock_session,
        filter_stock_rows_by_session,
        stock_cache_interval,
        stock_candle_complete_at,
        stock_candle_stale_warning,
        stock_daily_should_have_intraday,
    )
    from market_data.provider_health import provider_call_allowed, record_provider_call
    from utils import now_ms, pct
except ModuleNotFoundError:
    from hakimi_research.terminal_config import FUTU_HOST, FUTU_PORT
    from exchange_terminal.market_data.futu import (
        futu_history_ktype,
        futu_history_window,
        futu_status_snapshot,
        import_futu_sdk,
        normalize_futu_quote,
        parse_futu_time_key,
        update_futu_status_cache,
    )
    from hakimi_research.stock_metadata import (
        futu_code,
        normalize_stock_interval,
        stock_meta,
        stock_session_from_ts,
        stock_session_label,
        stock_timezone,
    )
    from hakimi_research.stock_candles import (
        aggregate_stock_rows,
        clean_stock_session,
        filter_stock_rows_by_session,
        stock_cache_interval,
        stock_candle_complete_at,
        stock_candle_stale_warning,
        stock_daily_should_have_intraday,
    )
    from exchange_terminal.market_data.provider_health import provider_call_allowed, record_provider_call
    from hakimi_research.terminal_utils import now_ms, pct


QuoteReader = Callable[[str], dict[str, Any]]


def read_futu_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    status = futu_status_snapshot()
    if not status.get("opend_online"):
        return {}
    futu, _ = import_futu_sdk()
    if not futu:
        return {}
    allowed, _retry_after_ms = provider_call_allowed("futu", "snapshot", "batch")
    if not allowed:
        return {}
    code_to_symbol = {futu_code(symbol): stock_meta(symbol)["symbol"] for symbol in symbols}
    quote_ctx = None
    started = time.perf_counter()
    try:
        quote_ctx = futu.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        ret, data = quote_ctx.get_market_snapshot(list(code_to_symbol.keys()))
        if ret != futu.RET_OK or data is None:
            error = f"snapshot failed: {data}"
            record_provider_call("futu", "snapshot", success=False, latency_ms=(time.perf_counter() - started) * 1000, error=error, scope="batch")
            update_futu_status_cache(online=False, message=error)
            return {}
        rows = data.to_dict("records") if hasattr(data, "to_dict") else []
        market_states: dict[str, str] = {}
        market_state_warning = ""
        state_started = time.perf_counter()
        try:
            state_ret, state_data = quote_ctx.get_market_state(list(code_to_symbol.keys()))
            if state_ret == futu.RET_OK and state_data is not None:
                state_rows = state_data.to_dict("records") if hasattr(state_data, "to_dict") else []
                market_states = {
                    str(item.get("code") or "").upper(): str(item.get("market_state") or "")
                    for item in state_rows
                    if item.get("code")
                }
                record_provider_call("futu", "market_state", success=True, latency_ms=(time.perf_counter() - state_started) * 1000, scope="batch")
            else:
                market_state_warning = f"market state failed: {state_data}"
                record_provider_call("futu", "market_state", success=False, latency_ms=(time.perf_counter() - state_started) * 1000, error=market_state_warning, scope="batch")
        except Exception as exc:
            market_state_warning = f"market state failed: {exc}"
            record_provider_call("futu", "market_state", success=False, latency_ms=(time.perf_counter() - state_started) * 1000, error=market_state_warning, scope="batch")
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            code = str(row.get("code", "")).upper()
            symbol = code_to_symbol.get(code, code)
            normalized = normalize_futu_quote({**row, "market_state": market_states.get(code, "")}, symbol)
            if market_state_warning:
                normalized["market_state_warning"] = market_state_warning
            result[symbol] = normalized
        record_provider_call(
            "futu",
            "snapshot",
            success=bool(result),
            latency_ms=(time.perf_counter() - started) * 1000,
            error="snapshot returned no rows" if not result else "",
            scope="batch",
        )
        update_futu_status_cache(online=True, sdk_installed=True, message=f"Futu snapshot {len(result)} symbols")
        return result
    except Exception as exc:
        record_provider_call("futu", "snapshot", success=False, latency_ms=(time.perf_counter() - started) * 1000, error=str(exc), scope="batch")
        update_futu_status_cache(online=False, sdk_installed=True, message=f"Futu error: {exc}")
        return {}
    finally:
        try:
            if quote_ctx:
                quote_ctx.close()
        except Exception:
            pass


def augment_futu_candles_with_snapshot(
    symbol: str,
    rows: list[dict[str, Any]],
    interval: str,
    session: str,
    limit: int,
    quote_reader: QuoteReader | None = None,
) -> list[dict[str, Any]]:
    if not rows or not quote_reader:
        return rows
    quote = quote_reader(symbol)
    if str(quote.get("source") or "").lower() != "futu":
        return rows
    last = pct(quote.get("last", 0.0))
    if last <= 0:
        return rows
    normalized_interval = stock_cache_interval(interval)
    ts = int(quote.get("ts") or now_ms())
    current_session = stock_session_from_ts(ts, symbol)
    clean_session = clean_stock_session(session)
    if clean_session != "all" and current_session != clean_session:
        return rows
    local_dt = datetime.fromtimestamp(ts / 1000, stock_timezone(symbol))
    if normalized_interval in {"1d", "1dutc"}:
        if not stock_daily_should_have_intraday(symbol):
            return rows
        bucket_dt = datetime(local_dt.year, local_dt.month, local_dt.day, tzinfo=stock_timezone(symbol))
        bucket_ts = int(bucket_dt.timestamp() * 1000)
        date_text = bucket_dt.strftime("%Y-%m-%d")
        open_price = pct(quote.get("open24h", 0.0), last) or last
        high = pct(quote.get("high24h", 0.0), last) or last
        low = pct(quote.get("low24h", 0.0), last) or last
        volume = pct(quote.get("vol24h", 0.0))
        row_session = "regular"
    else:
        bucket_ms = {
            "1m": 60_000,
            "5m": 5 * 60_000,
            "15m": 15 * 60_000,
            "30m": 30 * 60_000,
            "60m": 60 * 60_000,
            "4h": 4 * 60 * 60_000,
        }.get(normalized_interval, 60_000)
        bucket_ts = ts // bucket_ms * bucket_ms
        date_text = local_dt.strftime("%Y-%m-%d")
        open_price = last
        high = last
        low = last
        volume = 0.0
        row_session = current_session
    current_row = {
        "ts": bucket_ts,
        "date": date_text,
        "open": open_price,
        "high": high,
        "low": low,
        "close": last,
        "volume": volume,
        "source": "futu",
        "session": row_session,
        "complete": False,
        "provisional": True,
    }
    merged = [row for row in rows if int(row.get("ts") or 0) != bucket_ts and str(row.get("date") or "") != date_text]
    if normalized_interval not in {"1d", "1dutc"}:
        merged = [row for row in rows if int(row.get("ts") or 0) != bucket_ts]
    merged.append(current_row)
    merged.sort(key=lambda item: int(item.get("ts") or 0))
    return merged[-limit:]


def read_futu_stock_candles(
    symbol: str,
    limit: int = 260,
    interval: str = "1d",
    session: str = "all",
    quote_reader: QuoteReader | None = None,
) -> dict[str, Any]:
    status = futu_status_snapshot()
    if not status.get("opend_online"):
        return {"ok": False, "rows": [], "source": "futu", "error": status.get("message", "OpenD offline")}
    futu, _ = import_futu_sdk()
    if not futu:
        return {"ok": False, "rows": [], "source": "futu", "error": "futu-api not installed"}
    code = futu_code(symbol)
    clean_session = clean_stock_session(session)
    normalized_interval, _ = normalize_stock_interval(interval)
    ktype = futu_history_ktype(normalized_interval)
    start_date, end_date = futu_history_window(symbol, normalized_interval, limit)
    health_scope = f"{stock_meta(symbol)['symbol']}|{normalized_interval}|{clean_session}"
    allowed, retry_after_ms = provider_call_allowed("futu", "history", health_scope)
    if not allowed:
        return {"ok": False, "rows": [], "source": "futu", "error": "Futu history cooldown", "retry_after_ms": retry_after_ms}
    quote_ctx = None
    rows: list[dict[str, Any]] = []
    captured_at_ms = now_ms()
    started = time.perf_counter()
    try:
        quote_ctx = futu.OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        page_key: Any = None
        page_count = 0
        while page_count < 20:
            ret, data, next_page_key = quote_ctx.request_history_kline(
                code,
                start=start_date,
                end=end_date,
                ktype=ktype,
                autype="qfq",
                max_count=min(max(int(limit) * 2, 120), 1000),
                extended_time=True,
                page_req_key=page_key,
            )
            if ret != futu.RET_OK or data is None:
                error = str(data)
                record_provider_call("futu", "history", success=False, latency_ms=(time.perf_counter() - started) * 1000, error=error, scope=health_scope)
                return {"ok": False, "rows": [], "source": "futu", "error": error}
            for row in data.to_dict("records"):
                ts_ms = parse_futu_time_key(row.get("time_key"), symbol)
                if ts_ms <= 0:
                    continue
                close = pct(row.get("close", 0))
                if close <= 0:
                    continue
                rows.append({
                    "ts": ts_ms,
                    "date": str(row.get("time_key", ""))[:10],
                    "open": pct(row.get("open", close)),
                    "high": pct(row.get("high", close)),
                    "low": pct(row.get("low", close)),
                    "close": close,
                    "volume": pct(row.get("volume", 0)),
                    "turnover": pct(row.get("turnover", 0)),
                    "source": "futu",
                    "session": "regular" if ktype == "K_DAY" else stock_session_from_ts(ts_ms, symbol),
                    "complete": stock_candle_complete_at(
                        symbol,
                        normalized_interval,
                        ts_ms,
                        str(row.get("time_key", ""))[:10],
                        at_ms=captured_at_ms,
                    ),
                })
            page_count += 1
            if next_page_key is None or next_page_key == page_key:
                break
            page_key = next_page_key
        rows = list({int(row["ts"]): row for row in rows}.values())
        rows.sort(key=lambda item: int(item.get("ts") or 0))
    except Exception as exc:
        record_provider_call("futu", "history", success=False, latency_ms=(time.perf_counter() - started) * 1000, error=str(exc), scope=health_scope)
        return {"ok": False, "rows": [], "source": "futu", "error": str(exc)}
    finally:
        try:
            if quote_ctx:
                quote_ctx.close()
        except Exception:
            pass
    if (interval or "").lower() == "4h" and ktype == "K_60M":
        rows = aggregate_stock_rows(rows, 4 * 60 * 60 * 1000)
        normalized_interval = "4h"
    rows = filter_stock_rows_by_session(rows, clean_session)
    rows = augment_futu_candles_with_snapshot(symbol, rows, normalized_interval, clean_session, limit, quote_reader)
    stale_warning = stock_candle_stale_warning(rows, normalized_interval, symbol)
    if clean_session == "all" and normalized_interval not in {"1d", "1dutc"}:
        regular_rows = filter_stock_rows_by_session(rows, "regular")
        regular_warning = stock_candle_stale_warning(regular_rows, normalized_interval, symbol)
        if not regular_rows:
            stale_warning = "Futu all-session history missing regular session"
        elif regular_warning:
            stale_warning = f"Futu all-session regular history is stale: {regular_warning}"
    if stale_warning:
        record_provider_call("futu", "history", success=False, latency_ms=(time.perf_counter() - started) * 1000, error=stale_warning, scope=health_scope)
        return {"ok": False, "rows": [], "source": "futu", "error": stale_warning}
    session_counts: dict[str, int] = {"pre": 0, "regular": 0, "post": 0, "overnight": 0}
    for row in rows:
        if row.get("session") in session_counts:
            session_counts[row["session"]] += 1
    record_provider_call(
        "futu",
        "history",
        success=bool(rows),
        latency_ms=(time.perf_counter() - started) * 1000,
        error="history returned no rows" if not rows else "",
        scope=health_scope,
    )
    return {
        "ok": True,
        "symbol": stock_meta(symbol)["symbol"],
        "source": "futu",
        "adjustment_basis": "FORWARD_ADJUSTED_QFQ",
        "corporate_action_coverage": "EMBEDDED_PROVIDER_CONTRACT",
        "corporate_actions": [],
        "interval": normalized_interval,
        "session": clean_session,
        "session_label": stock_session_label(clean_session),
        "session_counts": session_counts,
        "rows": rows[-limit:],
        "provider_observation_scope": "QUERY_WINDOW",
        "provider_observation_window": {
            "requested_limit": int(limit),
            "requested_start": start_date,
            "requested_end": end_date,
            "fetched_rows": len(rows),
            "returned_rows": len(rows[-limit:]),
        },
        "updated_at": now_ms(),
    }
