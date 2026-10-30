"""Pure factor explanations for current original-terminal strategy candidates.

The service supplies its verified raw native input and current rule identity.
No files, markets, positions or reports are fetched here. Signals come from the
actual signal factory; explanations are checked against its unrounded decision.
This is neither a historical-performance ranking nor order authorization.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import re
from zoneinfo import ZoneInfo

from . import indicator_math, strategy_signals as signals


SCHEMA = "hakimi-terminal-strategy-diagnostic-v1"
CATALOG_ORDER = ("dual_ma", "bollinger", "macd", "rsi", "momentum", "volume_trend", "livermore", "turtle", "darvas")
GROUPS = (("ENTRY_MATCH", "满足开仓规则的候选"), ("EXIT_MATCH", "满足退出规则的候选"),
          ("WAITING", "暂时等待"), ("INSUFFICIENT", "资料不足"))
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _seal(value, key="diagnostic_id"):
    return {**value, key: sha256(_bytes(value)).hexdigest()}


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _day(value):
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None or date.fromisoformat(value).isoformat() != value:
        raise ValueError("candidate_session_date_invalid")
    return date.fromisoformat(value)


def _clock(value):
    if type(value) is not str:
        raise ValueError("candidate_explicit_clock_required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("candidate_explicit_clock_required")
    return parsed.astimezone(timezone.utc)


def _number(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else True)


def _spec(spec):
    # Lazy access after service module initialization avoids an import cycle.
    from .terminal_research import validate_terminal_strategy_params
    required = {"id", "name", "params", "engine_id", "fingerprint", "engine_source_identity"}
    if type(spec) is not dict or set(spec) != required or spec["id"] not in CATALOG_ORDER:
        raise ValueError("candidate_current_nine_strategy_spec_required")
    identity = spec["id"]
    capability = signals.strategy_validation_capability(identity)
    if capability["new_research_allowed"] is not True or spec["engine_id"] != "terminal." + signals.SIGNAL_ENGINE_VERSION:
        raise ValueError("candidate_current_engine_required")
    if type(spec["name"]) is not str or not spec["name"] or not _hash(spec["fingerprint"]):
        raise ValueError("candidate_rule_identity_required")
    sources = spec["engine_source_identity"]
    if (type(sources) is not dict or not {"strategy_signals.py", "indicator_math.py"}.issubset(sources)
            or any(not _hash(value) for value in sources.values())
            or sources["indicator_math.py"] != indicator_math.LOADED_SOURCE_SHA256):
        raise ValueError("candidate_indicator_source_identity_mismatch")
    if type(spec["params"]) is not dict:
        raise ValueError("candidate_validated_parameters_required")
    params = validate_terminal_strategy_params({"id": identity, "params": deepcopy(spec["params"])}, deepcopy(spec["params"]))
    if _bytes(params) != _bytes(spec["params"]):
        raise ValueError("candidate_parameters_must_already_be_normalized")
    return deepcopy(spec), capability


def _input(record, cutoff, observed):
    from .terminal_research import _provider_source
    if (type(record) is not dict or record.get("schema_version") != "hakimi-terminal-input-v1"
            or not _hash(record.get("id")) or not _hash(record.get("source_digest"))
            or record["id"] != sha256(_bytes({k: v for k, v in record.items() if k != "id"})).hexdigest()):
        raise ValueError("candidate_verified_raw_native_record_required")
    if "core_reference" in record and "daily_reference" in record:
        raise ValueError("candidate_ambiguous_input_reference")
    if record.get("bar") != "1D" or type(record.get("meta")) is not dict or type(record.get("quality")) is not dict:
        raise ValueError("candidate_daily_input_required")
    rows, meta, quality = record.get("rows"), record["meta"], record["quality"]
    if type(rows) is not list or not rows or len(rows) > 5000:
        raise ValueError("candidate_bounded_nonempty_history_required")
    cutoff_day = _day(cutoff)
    if type(quality.get("blockers")) is not list or any(type(value) is not str for value in quality["blockers"]):
        raise ValueError("candidate_quality_blockers_invalid")
    blockers = list(quality["blockers"])
    if quality.get("status") != "REVIEW":
        blockers.append("INPUT_NOT_ADMITTED")
    if meta.get("evidence_kind") == "SYNTHETIC_TEST":
        blockers.append("SYNTHETIC_INPUT_NOT_ADMITTED")
    if type(record.get("source")) is not str or not record["source"]:
        raise ValueError("candidate_source_required")
    if any(marker in record["source"].lower() for marker in ("synthetic", "quick_preview", "preview_seed", "offline-seed")):
        blockers.append("PREVIEW_OR_SYNTHETIC_SOURCE")
    zone = ZoneInfo(meta["timezone"]) if type(meta.get("timezone")) is str else None
    if zone is None:
        blockers.append("SESSION_TIMEZONE_UNRECORDED")
    previous = None
    for row in rows:
        if type(row) is not dict or row.get("complete") is not True or row.get("provisional") is not False:
            raise ValueError("candidate_incomplete_or_provisional_row")
        day = _day(row.get("date"))
        stamp = row.get("ts_ms")
        if type(stamp) is not int or stamp <= 0 or previous is not None and (day <= previous[0] or stamp <= previous[1]):
            raise ValueError("candidate_chronology_invalid")
        if row.get("source") != record["source"]:
            raise ValueError("candidate_source_lineage_mismatch")
        if (any(not _number(row.get(key), positive=True) for key in ("open", "high", "low", "close"))
                or not _number(row.get("volume")) or row["volume"] < 0
                or row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"])):
            raise ValueError("candidate_ohlcv_invalid")
        if zone is not None and datetime.fromtimestamp(stamp / 1000, timezone.utc).astimezone(zone).date() != day:
            raise ValueError("candidate_session_timestamp_mismatch")
        previous = day, stamp
    try:
        if _provider_source(meta, rows) != record["source"]:
            raise ValueError("candidate_source_lineage_mismatch")
    except ValueError as error:
        blockers.append(str(error))
    prefix = [deepcopy(row) for row in rows if row["date"] <= cutoff]
    if not prefix or prefix[-1]["date"] != cutoff:
        raise ValueError("candidate_cutoff_must_be_recorded_session")
    if datetime.fromtimestamp(prefix[-1]["ts_ms"] / 1000, timezone.utc) > observed or cutoff_day > observed.date():
        raise ValueError("candidate_future_data_not_available")
    for field in ("as_of", "retrieved_at"):
        if meta.get(field) is not None and _clock(meta[field]) > observed:
            raise ValueError("candidate_observed_before_retained_source")
    last_available = None
    sessions = meta.get("sessions")
    lag = meta.get("bar_availability_lag_seconds")
    if sessions is not None:
        if (type(sessions) is not list or any(type(session) is not dict for session in sessions)
                or not _number(lag) or not 0 <= lag <= 7*86400):
            raise ValueError("candidate_session_availability_invalid")
        expected = [session for session in sessions if session.get("date", "") <= cutoff]
        if [session.get("date") for session in expected] != [row["date"] for row in prefix]:
            raise ValueError("candidate_declared_session_gap")
        for row, session in zip(prefix, expected):
            opened, closed = _clock(session.get("open_utc")), _clock(session.get("close_utc"))
            available = closed + timedelta(seconds=lag)
            if int(opened.timestamp() * 1000) != row["ts_ms"] or closed <= opened:
                raise ValueError("candidate_session_clock_mismatch")
            if available > observed:
                raise ValueError("candidate_bar_not_yet_available")
            last_available = available
    elif cutoff_day == (observed.astimezone(zone).date() if zone else observed.date()):
        blockers.append("CURRENT_DAY_COMPLETION_CLOCK_UNRECORDED")
    freshness = {"context": "SAVED_HISTORICAL_INPUT", "live_quote_verified": False,
        "cutoff_session": cutoff, "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "snapshot_as_of": meta.get("as_of"), "retrieved_at": meta.get("retrieved_at"),
        "last_bar_available_at": last_available.isoformat().replace("+00:00", "Z") if last_available else None,
        "elapsed_seconds_since_bar_available": (observed - last_available).total_seconds() if last_available else None,
        "elapsed_calendar_days": (observed.astimezone(zone).date() - cutoff_day).days if zone else None,
        "trading_session_age": None, "immediate_execution_eligible": False}
    return prefix, list(dict.fromkeys(blockers)), freshness


def _factor(key, label, value, operator, threshold, role, position, *, unit="price", window=None):
    value_known = _number(value)
    threshold_known = _number(threshold) or type(threshold) is list and len(threshold) == 2 and all(_number(v) for v in threshold)
    available = value_known and threshold_known
    passed = None
    if available:
        passed = {">": lambda: value > threshold, "<": lambda: value < threshold,
                  ">=": lambda: value >= threshold, "<=": lambda: value <= threshold,
                  "between_inclusive": lambda: threshold[0] <= value <= threshold[1]}[operator]()
    return {"key": key, "label": label, "value": value if value_known else None, "operator": operator,
        "threshold": deepcopy(threshold) if threshold_known else None, "passed": passed,
        "status": "AVAILABLE" if available else "INSUFFICIENT_HISTORY", "unit": unit, "window": window,
        "role": role, "applies_to_position": position if role == "EXIT" else not position}


def _factors(identity, rows, params, position):
    closes = [float(row["close"]) for row in rows]
    price, count = closes[-1], len(closes)
    result = []
    def add(key, label, value, op, threshold, role="ENTRY", unit="price", window=None):
        result.append(_factor(key, label, value, op, threshold, role, position, unit=unit, window=window))
    def average(n):
        return signals._average(closes[-n:]) if count >= n else None
    def prior(n, field, fn):
        return fn(float(row[field]) for row in rows[-n-1:-1]) if count >= n + 1 else None
    if identity == "dual_ma":
        fast, slow = average(params["fast_window"]), average(params["slow_window"])
        add("fast_above_slow", "快均线高于慢均线", fast, ">", slow, window=[params["fast_window"],params["slow_window"]])
        add("fast_below_slow", "快均线低于慢均线", fast, "<", slow, "EXIT", window=[params["fast_window"],params["slow_window"]])
    elif identity == "bollinger":
        n = params["window"]
        band = indicator_math.bollinger(closes[-n:], n, params["std_mult"])[-1] if count >= n else None
        add("below_lower_band", "收盘低于布林下轨", price, "<", band["lower"] if band else None, window=n)
        add("above_mid_band", "收盘高于布林中轨", price, ">", band["mid"] if band else None, "EXIT", window=n)
    elif identity == "macd":
        previous, previous_signal, line, signal = signals._macd_state(closes, params["fast"], params["slow"], params["signal"]) if count >= 2 else (None,None,None,None)
        histogram = line-signal if count >= 2 else None
        previous_histogram = previous-previous_signal if count >= 2 else None
        window = [params["fast"],params["slow"],params["signal"]]
        add("macd_above_signal", "MACD 高于信号线", line, ">", signal, window=window)
        add("histogram_positive", "MACD 柱值为正", histogram, ">", 0.0, window=window)
        add("histogram_not_declining", "柱值不低于上一根", histogram, ">=", previous_histogram, window=window)
        add("macd_below_signal", "MACD 低于信号线", line, "<", signal, "EXIT", window=window)
    elif identity == "rsi":
        n = params["window"]
        value = indicator_math.rsi(closes[-n-1:], n)[-1] if count >= n + 1 else None
        add("rsi_oversold", "RSI 低于超卖阈值", value, "<", params["oversold"], unit="oscillator_points", window=n)
        add("rsi_overbought", "RSI 高于超买阈值", value, ">", params["overbought"], "EXIT", "oscillator_points", n)
    elif identity == "momentum":
        n = params["window"]
        value = price / max(closes[-n-1], 1e-12) - 1.0 if count >= n + 1 else None
        add("momentum_positive", "动量高于正阈值", value, ">", params["threshold"], unit="ratio", window=n)
        add("momentum_negative", "动量低于负阈值", value, "<", -params["threshold"], "EXIT", "ratio", n)
    elif identity in {"livermore", "turtle", "darvas"}:
        entry = params[{"livermore":"pivot_window","turtle":"entry_window","darvas":"box_window"}[identity]]
        exit_window = min(30,entry) if identity == "livermore" else params["exit_window"] if identity == "turtle" else entry
        high, low = prior(entry,"close",max), prior(exit_window,"close",min)
        confirmation = 1.0 + params["confirm_pct"] if identity != "turtle" else 1.0
        add("close_breakout", "收盘突破前段收盘上界", price, ">", high * confirmation if high is not None else None, window=entry)
        add("close_exit", "收盘跌破前段防守下界", price, "<", low * (.995 if identity == "livermore" else 1.0) if low is not None else None, "EXIT", window=exit_window)
    else:
        bars = signals._normalized_bars(rows)
        fast, trend = average(params["fast_window"]), average(params["trend_window"])
        volume_n, atr_n = params["volume_window"], params["atr_window"]
        average_volume = signals._average([row["volume"] for row in bars[-volume_n-1:-1]]) if count >= volume_n+1 else None
        volume_ratio = (bars[-1]["volume"] / average_volume if average_volume > 0 else 0.0) if average_volume is not None else None
        atr = signals._average_true_range(bars, atr_n) / max(price,1e-12) if count >= atr_n+1 else None
        extension = price / max(fast,1e-12) - 1 if fast is not None else None
        add("price_breakout", "收盘突破前段最高价", price, ">", prior(params["breakout_window"],"high",max), window=params["breakout_window"])
        add("fast_above_trend", "快均线高于趋势均线", fast, ">", trend, window=[params["fast_window"],params["trend_window"]])
        add("price_above_trend", "收盘高于趋势均线", price, ">", trend, window=params["trend_window"])
        add("volume_confirmed", "量比达到下限", volume_ratio, ">=", params["volume_ratio"], unit="multiplier", window=volume_n)
        add("volatility_valid", "ATR 比例位于允许区间", atr, "between_inclusive", [params["min_atr_pct"],params["max_atr_pct"]], unit="ratio", window=atr_n)
        add("not_overextended", "向上偏离未超过上限", extension, "<=", params["max_extension_pct"], unit="ratio", window=params["fast_window"])
        add("structure_exit", "收盘跌破前段最低价", price, "<", prior(params["exit_window"],"low",min), "EXIT", window=params["exit_window"])
    return result


def diagnose_strategy(frozen_input, strategy_spec, *, cutoff_session, observed_at, position_context):
    """Describe one verified input/current rule, with no implicit position cost."""
    spec, capability = _spec(strategy_spec)
    observed = _clock(observed_at)
    rows, blockers, freshness = _input(frozen_input, cutoff_session, observed)
    if (type(position_context) is not dict or set(position_context) - {"has_position","entry_price","last_scale_price"}
            or type(position_context.get("has_position")) is not bool
            or any(not _number(position_context[key], positive=True) for key in ("entry_price","last_scale_price") if key in position_context)):
        raise ValueError("candidate_explicit_position_context_required")
    position = position_context["has_position"]
    identity, params = spec["id"], spec["params"]
    history = rows if capability["signal_input"] == "BARS" else [float(row["close"]) for row in rows]
    # These nine strategies do not consume position cost in signal decisions.
    # Zero is solely the existing unused function argument, never a cost claim.
    actual = signals.build_strategy_signal_fn(identity, params)(history, float(rows[-1]["close"]), position,
        position_context.get("entry_price",0.0), position_context.get("last_scale_price",0.0))
    factors = _factors(identity, rows, params, position)
    for factor in factors:
        factor.update(cutoff_session=cutoff_session)
    active = [factor for factor in factors if factor["applies_to_position"]]
    expected = ("EXIT" if position else "BUY") if all(factor["passed"] is True for factor in active) else "HOLD"
    if actual.get("reason") == "insufficient_history":
        expected = "HOLD"
    parity = actual.get("action") == expected and actual.get("reason") not in {"invalid_indicator_history","invalid_bar_history","unsupported_strategy","signal_input_mismatch"}
    warmup = signals.strategy_startup_candles_for_params(identity, params)
    required = warmup + 2
    if len(rows) < required:
        blockers.append("INSUFFICIENT_RESEARCH_WARMUP_AND_NEXT_BAR")
    if not parity:
        blockers.append("DIAGNOSTIC_MISMATCH")
    status = "DIAGNOSTIC_MISMATCH" if not parity else "DATA_INSUFFICIENT" if blockers else "READY"
    group = ("INSUFFICIENT" if blockers else "ENTRY_MATCH" if actual["action"] == "BUY" and not position
             else "EXIT_MATCH" if actual["action"] == "EXIT" and position else "WAITING")
    return _seal({"schema_version":SCHEMA,"status":status,"group":group,"strategy_id":identity,"name":spec["name"],
        "strategy_params":params,"engine_id":spec["engine_id"],"fingerprint":spec["fingerprint"],
        "engine_source_identity":spec["engine_source_identity"],"indicator_contract":deepcopy(indicator_math.CONTRACT),
        "signal_engine_version":signals.SIGNAL_ENGINE_VERSION,"input_id":frozen_input["id"],"source_digest":frozen_input["source_digest"],
        "symbol":frozen_input["symbol"],"cutoff_session":cutoff_session,"freshness":freshness,
        "position_context":deepcopy(position_context),"position_cost_used_by_rule":False,
        "position_cost_status":"RECORDED" if "entry_price" in position_context else "UNRECORDED",
        "signal":deepcopy(actual),"factors":factors,"decision_matches_factors":parity,
        "complete_rows":len(rows),"warmup_rows":warmup,"required_rows":required,"missing_rows":max(0,required-len(rows)),
        "blockers":list(dict.fromkeys(blockers)),"selection_note":"比较两条均线，规则较简单，便于逐项核对。" if identity == "dual_ma" else None,
        "historical_performance":{"status":"NOT_ASSESSED","used_for_ordering":False},
        "limitations":["这是所选封存数据截止日的规则诊断，不是实时买卖指令。","持仓成本、固定止盈止损及订单资格由独立预览核对；这里不补造价格。",
                        "规则触发不代表策略有效；未评估历史收益优劣。"],
        "source_authenticated":False,"new_economic_runs":0,"permissions":dict(_PERMISSIONS)})


def recommend_candidates(diagnostics):
    """Fixed groups/catalog order; no forced first choice or performance score."""
    if type(diagnostics) is not list:
        raise ValueError("candidate_diagnostics_list_required")
    items, identities, context = [], set(), None
    for item in diagnostics:
        if (type(item) is not dict or item.get("schema_version") != SCHEMA or item.get("strategy_id") not in CATALOG_ORDER
                or not _hash(item.get("diagnostic_id")) or item["diagnostic_id"] != sha256(_bytes({k:v for k,v in item.items() if k != "diagnostic_id"})).hexdigest()
                or item.get("group") not in dict(GROUPS) or item["strategy_id"] in identities):
            raise ValueError("candidate_diagnostic_identity_invalid")
        binding = _bytes({key:item[key] for key in ("input_id","cutoff_session","freshness","position_context","engine_id","engine_source_identity")})
        if context is not None and context != binding:
            raise ValueError("candidate_mixed_data_or_rule_context")
        context = binding
        identities.add(item["strategy_id"])
        items.append(deepcopy(item))
    items.sort(key=lambda item:CATALOG_ORDER.index(item["strategy_id"]))
    return {"schema_version":"hakimi-terminal-strategy-candidates-v1",
        "groups":[{"key":key,"label":label,"items":[item for item in items if item["group"] == key]} for key,label in GROUPS],
        "ordering":"FIXED_CATALOG_ORDER_WITHIN_GROUP","selected_strategy_id":None,
        "historical_performance":{"status":"NOT_ASSESSED","used_for_ordering":False},
        "new_economic_runs":0,"permissions":dict(_PERMISSIONS)}
