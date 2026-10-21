"""Read-only insights over retained daily inputs. No market fetch, order or report write.

Derived observations keep their own identity; they never replace archived results.
Configured peer groups are explicitly NOT point-in-time industry membership evidence.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path

from . import causal_structure, indicator_math
from .market_calendar import build_market_calendar_contract
from .portfolio_risk import aligned_return_correlation


VERSION = "terminal-insights-v1"
LOADED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
_DEPENDENCY_FILES = {name: Path(__file__).with_name(name) for name in ("market_calendar.py", "portfolio_risk.py")}
_DEPENDENCY_FILES["candle_contract.py"] = Path(__file__).parents[1] / "market_data" / "candle_contract.py"
_DEPENDENCY_HASHES = {name: sha256(path.read_bytes()).hexdigest() for name, path in _DEPENDENCY_FILES.items()}
CARD_DEFINITIONS = (
    ("sma", "简单均线 SMA", {"window": 20}, 20, "最近 n 个收盘价的算术平均。", "观察价格相对近期均价的位置。", "需要完整窗口；均线有滞后，单次穿越不代表趋势成立。"),
    ("ema", "指数均线 EMA", {"window": 20}, 1, "α=2/(n+1)，第一项有效收盘价作为起点。", "观察近期价格方向；最近价格权重较高。", "缺值后从首个有效值重新起算；短历史会受起点影响。"),
    ("bollinger", "布林带 BOLL", {"window": 20, "std_mult": 2}, 20, "SMA ± 倍数 × 总体标准差（ddof=0）。", "观察价格相对均值的偏离和波动收缩。", "触及上轨不等于卖出，触及下轨不等于买入。"),
    ("macd", "MACD", {"fast": 12, "slow": 26, "signal": 9}, 1, "快 EMA − 慢 EMA；信号线为差值 EMA；柱值=差值−信号，不乘 2。", "辅助观察趋势动量变化。", "震荡区可能反复交叉；短历史受 EMA 初值影响。"),
    ("rsi", "RSI · 简单滚动口径", {"window": 14}, 15, "涨跌额各取 SMA，再按 100−100/(1+平均涨额/平均跌额) 计算。", "辅助观察近期涨跌力量。", "本项目使用 SMA，非 Wilder/RMA；平盘=50，仅涨=100，仅跌=0。不能直接对比其他平台默认值。"),
    ("atr", "ATR · 简单滚动口径", {"window": 14}, 15, "TR=max(高−低, |高−前收|, |低−前收|)，ATR=SMA(TR)。", "衡量波动幅度，可用于研究止损距离。", "必须有前收盘价；本项目使用 SMA，非 Wilder/RMA。ATR 不表示涨跌方向。"),
    ("momentum", "区间动量", {"window": 20}, 21, "当前收盘/向前 n 根收盘−1，原值为比例。", "观察同一标的固定窗口的价格变化。", "界面换算为百分比；不能当作含分红、成本的总收益。"),
)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode()).hexdigest()


def _day(value):
    if not isinstance(value, str) or len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("insights_date_invalid")
    return date.fromisoformat(value)


def _availability_lag(meta):
    value = meta.get("bar_availability_lag_seconds", 0)
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 31536000:
        raise ValueError("日线可用延迟必须为有限非负秒数，且不超过一年。")
    return timedelta(seconds=value)


def _period(day, frame):
    if frame == "1W":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    return day.replace(day=1), day.replace(day=monthrange(day.year, day.month)[1])


def _calendar_context(frozen, configured):
    meta = frozen["meta"]
    asset = str(meta.get("asset_class", "")).upper()
    declared_market = str(meta.get("market") or "").upper()
    configured_market = str(configured.get("market") or "").upper()
    if declared_market and configured_market and declared_market != configured_market:
        raise ValueError("证券市场声明与项目配置冲突，不能自动选交易日历。")
    market = declared_market or configured_market
    currency = str(meta.get("currency") or meta.get("security", {}).get("currency") or configured.get("quote") or "").upper()
    if meta.get("currency") and configured.get("quote") and meta["currency"].upper() != configured["quote"].upper():
        raise ValueError("证券币种声明与项目配置冲突。")
    if asset == "US_EQUITY":
        if market and market != "US":
            raise ValueError("证券资产类别与市场冲突。")
        market = "US"
    name = {"US": "XNYS", "HK": "XHKG"}.get(market)
    if asset in {"CRYPTO", "CRYPTO_SPOT"}:
        # Existing terminal crypto daily inputs are UTC; no equity fallback.
        if str(meta.get("timezone", "UTC")).upper() not in {"UTC", "ETC/UTC"}:
            raise ValueError("加密日线时区不是 UTC，尚不支持聚合。")
        name, market = "24/7-UTC", "CRYPTO"
    if not name:
        raise ValueError("缺少可核对的市场日历；请使用证券身份完整的输入。")
    if name != "24/7-UTC" and str(meta.get("session", "")).upper() != "REGULAR":
        raise ValueError("股票多周期与同业比较仅支持常规交易时段日线。")
    return {"calendar_name": name, "market": market, "currency": currency,
            "identity_basis": "INPUT_METADATA" if declared_market or asset == "US_EQUITY" else "PROJECT_CONFIGURATION"}


def _schedule(context, start, end):
    if context["calendar_name"] == "24/7-UTC":
        sessions = []
        day = start
        while day <= end:
            sessions.append({"date": day.isoformat(), "close_utc": (datetime.combine(day + timedelta(days=1), datetime.min.time(), timezone.utc)).isoformat()})
            day += timedelta(days=1)
        return sessions
    contract = build_market_calendar_contract(calendar_name=context["calendar_name"],
                                              start_date=start.isoformat(), end_date=end.isoformat())
    if contract["status"] != "PASS":
        raise ValueError("交易日历不可用：" + ";".join(contract["blockers"]))
    return contract["schedule"]


def _completed_prefix(frozen, as_of):
    if frozen.get("quality", {}).get("status") != "REVIEW" or frozen.get("bar", "").upper() not in {"1D", "1DUTC"}:
        raise ValueError("仅支持已接受的封存日线研究输入。")
    rows = frozen.get("rows", [])
    if _day(as_of) > datetime.now(timezone.utc).date():
        raise ValueError("观察日期尚未到达，不能计算未来日线。")
    if not rows or not rows[0]["date"] <= as_of <= rows[-1]["date"]:
        raise ValueError("观察日期超出这份封存行情的范围。")
    prefix = [row for row in rows if row["date"] <= as_of]
    causal_structure._validated_rows(prefix)
    return prefix


def indicator_cards(rows=None):
    indicator_math.assert_loaded_source_current()
    values = {}
    if rows:
        closes = [row["close"] for row in rows]
        line, signal, hist = indicator_math.macd(closes)
        values = {"sma": indicator_math.sma(closes, 20)[-1], "ema": indicator_math.ema(closes, 20)[-1],
                  "bollinger": indicator_math.bollinger(closes)[-1],
                  "macd": {"line": line[-1], "signal": signal[-1], "hist": hist[-1]},
                  "rsi": indicator_math.rsi(closes)[-1], "atr": indicator_math.atr(rows)[-1],
                  "momentum": indicator_math.momentum(closes)[-1]}
    return [{"key": key, "title": title, "params": params, "minimum_rows": minimum,
             "formula": formula, "use": use, "limitation": limitation, "value": values.get(key),
             "status": "NO_INPUT" if rows is None else "WARMUP" if values.get(key) is None else "AVAILABLE",
             "observed_rows": len(rows) if rows is not None else 0,
             "bar_date": rows[-1]["date"] if rows else None,
             "formula_version": indicator_math.FORMULA_VERSION,
             "source_url": "https://www.tradingview.com/charting-library-docs/latest/custom_studies/PineJS-Utility-Functions/",
             "source_note": "官方概念对照；本项目公式以上述版本为准，并非复制第三方受保护指标。"}
            for key, title, params, minimum, formula, use, limitation in CARD_DEFINITIONS]


def structure_frames(frozen, as_of, configured):
    rows = _completed_prefix(frozen, as_of)
    context = _calendar_context(frozen, configured)
    if context["calendar_name"] == "24/7-UTC":
        for row in rows:
            stamp = row.get("ts_ms")
            midnight = int(datetime.combine(_day(row["date"]), datetime.min.time(), timezone.utc).timestamp() * 1000)
            if type(stamp) is not int or stamp != midnight:
                raise ValueError("加密日线时间戳未与 UTC 日界线对齐，不能推断周/月完成。")
    start = min(_period(_day(rows[0]["date"]), "1W")[0], _period(_day(rows[0]["date"]), "1M")[0])
    end = max(_period(_day(as_of), "1W")[1], _period(_day(as_of), "1M")[1])
    schedule = _schedule(context, start, end)
    now = datetime.now(timezone.utc)
    availability_lag = _availability_lag(frozen["meta"])
    available_dates = {row["date"] for row in schedule
                       if datetime.fromisoformat(row["close_utc"].replace("Z", "+00:00")) + availability_lag <= now}
    future = [row["date"] for row in rows if row["date"] not in available_dates]
    if future:
        raise ValueError("含尚未收盘或不属于该市场交易日的日线，不能计算：" + ",".join(future[:3]))
    expected = [item["date"] for item in schedule if rows[0]["date"] <= item["date"] <= as_of]
    observed = {row["date"] for row in rows}
    missing = [day for day in expected if day not in observed]
    if missing:
        raise ValueError("封存日线缺少应有交易日，不能跨缺口形成结构：" + ",".join(missing[:5]))
    frames = []
    for frame in ("1D", "1W", "1M"):
        aggregated, excluded = [], []
        if frame == "1D":
            aggregated = rows
        else:
            groups = {}
            for row in rows:
                bounds = _period(_day(row["date"]), frame)
                groups.setdefault(bounds, []).append(row)
            for (begin, finish), members in groups.items():
                expected_group = [item["date"] for item in schedule if begin.isoformat() <= item["date"] <= finish.isoformat()]
                if not expected_group or [row["date"] for row in members] != expected_group:
                    excluded.append({"period_start": begin.isoformat(), "period_end": finish.isoformat(),
                                     "reason": "周期尚未结束或首段日线不完整"})
                    continue
                aggregated.append({"date": members[-1]["date"], "open": members[0]["open"],
                                   "high": max(row["high"] for row in members), "low": min(row["low"] for row in members),
                                   "close": members[-1]["close"], "complete": True, "provisional": False})
        if not aggregated:
            frames.append({"frame": frame, "status": "INSUFFICIENT", "reason": "尚无完整周期", "bar_count": 0,
                           "excluded_periods": excluded, "support": None, "resistance": None})
            continue
        structure = causal_structure.project_causal_structure(aggregated)
        pivots = structure["pivots"]
        highs = [mark for mark in pivots if mark["kind"] == "HIGH"]
        lows = [mark for mark in pivots if mark["kind"] == "LOW"]
        high, low = highs[-1] if highs else None, lows[-1] if lows else None
        last = aggregated[-1]
        state = "未形成完整高低点结构"
        pivot_pattern, structure_break = None, None
        if high and low:
            pivot_pattern = "上升组合 HH / HL" if high["classification"] == "HH" and low["classification"] == "HL" else (
                "下降组合 LH / LL" if high["classification"] == "LH" and low["classification"] == "LL" else "混合高低点组合")
            state = "最近确认高低点：" + pivot_pattern
            # Only this timeframe's completed close can invalidate its structure.
            # The as-of daily quote is used for distance, never weekly/monthly confirmation.
            if last["close"] < low["price"]:
                structure_break = {"kind": "BELOW_SUPPORT", "date": last["date"], "close": last["close"],
                                   "level": low["price"], "level_confirmed_at": low["confirmed_at_date"]}
                state = "本周期收盘已跌破支撑 · 原组合待重评"
            elif last["close"] > high["price"]:
                structure_break = {"kind": "ABOVE_RESISTANCE", "date": last["date"], "close": last["close"],
                                   "level": high["price"], "level_confirmed_at": high["confirmed_at_date"]}
                state = "本周期收盘已站上压力 · 等待新结构确认"
        frames.append({"frame": frame, "status": "AVAILABLE" if high and low else "INSUFFICIENT", "state": state,
                       "pivot_pattern": pivot_pattern, "structure_break": structure_break,
                       "reason": "至少 7 根完整周期才可能确认首个枢轴；每侧 3 根，仍可能没有唯一极值。" if not high or not low else "",
                       "bar_count": len(aggregated), "last_completed_date": last["date"], "last_close": last["close"],
                       "support": low, "resistance": high, "excluded_periods": excluded,
                       "as_of_close": rows[-1]["close"], "as_of_close_date": rows[-1]["date"],
                       "distance_to_support_pct": (rows[-1]["close"] / low["price"] - 1) * 100 if low else None,
                       "distance_to_resistance_pct": (rows[-1]["close"] / high["price"] - 1) * 100 if high else None,
                       "latest_breakout": structure["breakouts"][-1] if structure["breakouts"] else None,
                       "confirmed_events": pivots[-12:], "period_rows_hash": _digest(aggregated)})
    return {"calendar": context, "frames": frames, "prefix_rows_hash": _digest(rows), "prefix_row_count": len(rows),
            "observed_through": rows[-1]["date"], "as_of_close": rows[-1]["close"], "as_of": as_of,
            "calendar_schedule_hash": _digest(schedule),
            "params": {"left_window": 3, "right_window": 3}}


def compare_peers(inputs, start, end, configurations):
    begin, finish = _day(start), _day(end)
    if begin >= finish or not 2 <= len(inputs) <= 8:
        raise ValueError("请选择 2 至 8 个不同标的，并设置起始日期早于结束日期。")
    symbols = [item["symbol"] for item in inputs]
    if len(set(symbols)) != len(symbols):
        raise ValueError("同一标的只能选择一份封存行情。")
    contexts, samples = [], []
    for item in inputs:
        prefix = _completed_prefix(item, end)
        context = _calendar_context(item, configurations.get(item["symbol"], {}))
        currency = context["currency"]
        if context["market"] == "CRYPTO" or len(currency) != 3 or not currency.isalpha() or currency in {"XXX", "UNK"}:
            raise ValueError("同行业比较仅支持市场、币种可识别的股票输入。")
        samples.append([row for row in prefix if start <= row["date"] <= end])
        contexts.append(context)
    meta_keys = ("price_basis", "session")
    for key in meta_keys:
        declarations = [str(item["meta"].get(key) or "").upper() for item in inputs]
        if not declarations[0] or declarations[0] == "UNKNOWN" or len(set(declarations)) != 1:
            raise ValueError("价格口径或交易时段不同 / 未声明，不能比较：" + key)
    sources = [json.dumps(item["meta"].get("source_lineage", []), sort_keys=True) for item in inputs]
    if len(set(sources)) != 1 or sources[0] == "[]":
        raise ValueError("请使用相同来源的封存行情，当前不拼接不同供应商。")
    if len({(context["market"], context["currency"]) for context in contexts}) != 1:
        raise ValueError("不同市场或币种不可直接比较；本功能不估算汇率。")
    schedule = _schedule(contexts[0], begin, finish)
    dates = [row["date"] for row in schedule]
    now = datetime.now(timezone.utc)
    for item in inputs:
        lag = _availability_lag(item["meta"])
        if any(datetime.fromisoformat(row["close_utc"].replace("Z", "+00:00")) + lag > now for row in schedule):
            raise ValueError("比较区间含尚未收盘或尚未到声明可用时间的交易日。")
    if len(dates) < 2:
        raise ValueError("比较区间至少需要两个完成交易日。")
    for item, rows in zip(inputs, samples):
        if [row["date"] for row in rows] != dates:
            raise ValueError(item["symbol"] + " 的区间日线不完整或未对齐；请缩短区间或补充原输入。")
    groups = [configurations.get(symbol, {}).get("sector") for symbol in symbols]
    same_group = bool(groups[0]) and len(set(groups)) == 1
    group_records = [{key: configurations.get(symbol, {}).get(key) for key in ("symbol", "sector", "market", "quote")} for symbol in symbols]
    baseline_return = 100 * (samples[0][-1]["close"] / samples[0][0]["close"] - 1)
    result_rows = []
    for item, rows in zip(inputs, samples):
        change = 100 * (rows[-1]["close"] / rows[0]["close"] - 1)
        correlation = aligned_return_correlation(samples[0], rows, lookback=max(2, len(rows) - 1), minimum_overlap=20)
        result_rows.append({"symbol": item["symbol"], "input_id": item["id"], "group": configurations.get(item["symbol"], {}).get("sector"),
                            "start_close": rows[0]["close"], "end_close": rows[-1]["close"], "price_change_pct": change,
                            "difference_from_baseline_pp": change - baseline_return,
                            "correlation": correlation, "prefix_rows_hash": _digest(rows),
                            "series": [{"date": row["date"], "value": row["close"] / rows[0]["close"] * 100} for row in rows]})
    ordered = sorted(result_rows, key=lambda row: (-row["price_change_pct"], row["symbol"]))
    for rank, item in enumerate(ordered, 1):
        item["rank"] = rank
    return {"status": "REVIEW", "rows": ordered, "start_date": dates[0], "end_date": dates[-1],
            "calendar_schedule_hash": _digest(schedule),
            "requested_start": start, "requested_end": end, "bar_count": len(dates), "baseline_symbol": symbols[0],
            "market": contexts[0]["market"], "currency": contexts[0]["currency"],
            "price_basis": inputs[0]["meta"]["price_basis"], "session": inputs[0]["meta"]["session"],
            "group": groups[0] if same_group else None, "group_status": "PROJECT_CONFIG_GROUP" if same_group else "USER_SELECTION",
            "group_records": group_records, "group_source_hash": _digest(group_records), "historical_membership_verified": False,
            "interpretation": ["项目配置分组不是权威行业分类，也不是历史时点行业成分。",
                               "结果按所选封存价格口径计算同窗变化，不额外计入分红或交易成本，也不证明投资优势。",
                               "来源与复权声明仍待核验；相同声明不等于已通过公司行为或市场数据认证。",
                               "相关性按共同交易日收益计算；至少 20 个收益样本，不足时保留不可用。"]}


class TerminalInsightsService:
    def __init__(self, terminal, group_reader=None):
        self.terminal = terminal
        self.group_reader = group_reader or (lambda: [])

    def _groups(self):
        return {row["symbol"]: {key: row.get(key, "") for key in ("symbol", "name", "market", "quote", "sector")}
                for row in self.group_reader() if isinstance(row, dict) and isinstance(row.get("symbol"), str)}

    def read(self, resource, identity=None):
        if sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_SOURCE_SHA256:
            raise ValueError("insights_source_changed_restart_required")
        if any(sha256(path.read_bytes()).hexdigest() != _DEPENDENCY_HASHES[name] for name, path in _DEPENDENCY_FILES.items()):
            raise ValueError("insights_dependency_changed_restart_required")
        causal_structure.assert_loaded_source_current()
        indicator_math.assert_loaded_source_current()
        groups = self._groups()
        body = {"schema_version": VERSION, "derived": True, "research_only": True, "order_authorized": False,
                "availability_scope": "FROZEN_PREFIX_NOT_POINT_IN_TIME_ARCHIVE",
                "new_economic_runs": 0, "source_hashes": {"terminal_insights": LOADED_SOURCE_SHA256,
                    "causal_structure": causal_structure.LOADED_SOURCE_SHA256, "indicator_math": indicator_math.LOADED_SOURCE_SHA256,
                    **_DEPENDENCY_HASHES}}
        if resource == "terminal_insights" and identity is None:
            body.update(status="CATALOG", groups=list(groups.values()), cards=indicator_cards(), contract=indicator_math.CONTRACT)
        elif resource == "terminal_insights":
            parts = identity.split("/")
            if len(parts) != 2:
                raise ValueError("insights_request_invalid")
            frozen = self.terminal._input(parts[0])
            prefix = _completed_prefix(frozen, parts[1])
            body.update(input_id=frozen["id"], symbol=frozen["symbol"], as_of=parts[1],
                        contract=indicator_math.CONTRACT, input_meta=frozen["meta"], prefix_rows_hash=_digest(prefix))
            try:
                body.update(structure_frames(frozen, parts[1], groups.get(frozen["symbol"], {})),
                            status="REVIEW", cards=indicator_cards(prefix))
            except ValueError as exc:
                body.update(status="STRUCTURE_UNAVAILABLE", reason=str(exc), frames=[],
                            cards=[{**card, "status": "DATA_UNAVAILABLE", "reason": str(exc),
                                    "observed_rows": len(prefix)} for card in indicator_cards()])
        elif resource == "terminal_peers":
            parts = identity.split("/") if isinstance(identity, str) else []
            if len(parts) != 3 or not 2 <= len(parts[2].split(",")) <= 8:
                raise ValueError("insights_peer_request_invalid")
            inputs = [self.terminal._input(item) for item in parts[2].split(",")]
            body.update(compare_peers(inputs, parts[0], parts[1], groups))
        else:
            raise ValueError("insights_resource_unknown")
        return {**body, "record_hash": _digest(body)}
