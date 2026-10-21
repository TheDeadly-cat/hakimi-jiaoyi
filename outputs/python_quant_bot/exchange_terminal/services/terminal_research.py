"""Frozen original-terminal research tasks alongside the accepted equity kernel.

No strategy ID translation, market fetching during execution, or execution
authorization is provided here. The caller supplies the original pure runner.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
from threading import RLock

from .strategy_risk_profiles import strategy_research_risk_profile
from .terminal_ai_evidence import validate_ai_evidence, ai_evidence_binding
from .strategy_signals import SIGNAL_ENGINE_VERSION, strategy_startup_candles_for_params
from .indicator_math import CONTRACT as INDICATOR_CONTRACT
from .terminal_judgment import TerminalJudgmentService
from .terminal_exit_research import TerminalExitResearchService


ENGINE_ID = "terminal." + SIGNAL_ENGINE_VERSION
READABLE_ENGINE_IDS = {ENGINE_ID, "terminal.causal-long-only-signals-v6"}
EXECUTION_MODEL = "signal-close-next-open-ohlc-conservative-v3"
PERMISSIONS = {"research_only": True, "paper_authorized": False, "paper_allowed": False,
               "live_order_allowed": False, "live_allowed": False, "order_allowed": False}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_FAMILY = re.compile(r"[0-9a-f]{32}\Z")
_CONFIG_FIELDS = ("engine_id", "strategy_id", "strategy_params", "risk", "costs", "input_id", "fingerprint",
                  "execution_model", "engine_source_identity", "initial_cash", "direction_mode", "end_policy", "warmup_rows")
_LABELS = {"fast_window": "快均线周期", "slow_window": "慢均线周期", "window": "观察周期",
           "std_mult": "标准差倍数", "fast": "快线周期", "slow": "慢线周期", "signal": "信号周期",
           "oversold": "超卖阈值", "overbought": "超买阈值", "threshold": "信号阈值"}
_SIGNAL_DEFAULTS = {
    "dual_ma": {"fast_window": 20, "slow_window": 60},
    "bollinger": {"window": 20, "std_mult": 2.0},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
    "rsi": {"window": 14, "oversold": 30, "overbought": 70},
    "momentum": {"window": 20, "threshold": .015},
    "livermore": {"pivot_window": 60, "confirm_pct": .006},
    "turtle": {"entry_window": 20, "exit_window": 10},
    "darvas": {"box_window": 40, "confirm_pct": .004},
    "volume_trend": {"trend_window": 100, "fast_window": 20, "breakout_window": 40, "exit_window": 20,
                     "volume_window": 20, "atr_window": 14, "volume_ratio": 1.1,
                     "min_atr_pct": .01, "max_atr_pct": .08, "max_extension_pct": .12},
    "trend_pullback": {"trend_window": 100, "fast_window": 20, "breakout_window": 20, "exit_window": 10,
                       "volume_window": 20, "atr_window": 14},
    "squeeze_breakout": {"atr_short_window": 10, "atr_long_window": 50, "volume_short_window": 10,
                         "volume_long_window": 50, "breakout_window": 20, "trend_window": 100, "exit_window": 15,
                         "squeeze_atr_ratio": .70, "volume_contraction_ratio": .75, "range_expansion_ratio": 1.40,
                         "volume_expansion_ratio": 1.35, "max_breakout_atr": 2.0, "atr_stop_mult": 2.5},
}
_MINIMUMS = {
    "dual_ma": {"fast_window": 2, "slow_window": 3}, "bollinger": {"window": 10, "std_mult": .5},
    "macd": {"fast": 2, "slow": 3, "signal": 2}, "rsi": {"window": 5, "oversold": 1e-12, "overbought": 1e-12},
    "momentum": {"window": 5, "threshold": 1e-12}, "livermore": {"pivot_window": 20, "confirm_pct": 1e-12},
    "turtle": {"entry_window": 10, "exit_window": 5}, "darvas": {"box_window": 20, "confirm_pct": 1e-12},
    "volume_trend": {"trend_window": 30, "fast_window": 5, "breakout_window": 10, "exit_window": 5,
                     "volume_window": 5, "atr_window": 5, "volume_ratio": .5,
                     "min_atr_pct": 1e-12, "max_atr_pct": 1e-12, "max_extension_pct": 1e-12},
    "trend_pullback": {"trend_window": 60, "fast_window": 10, "breakout_window": 10, "exit_window": 5,
                       "volume_window": 10, "atr_window": 5},
    "squeeze_breakout": {"atr_short_window": 3, "atr_long_window": 8, "volume_short_window": 3,
                         "volume_long_window": 8, "breakout_window": 10, "trend_window": 30, "exit_window": 5,
                         "squeeze_atr_ratio": .1, "volume_contraction_ratio": .1, "range_expansion_ratio": 1,
                         "volume_expansion_ratio": 1, "max_breakout_atr": .25, "atr_stop_mult": .5},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _detached(value):
    return json.loads(_bytes(value))


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _seal(value, key="id"):
    return {**value, key: _digest(value)}


def _fields(value, allowed, required=()):
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError("terminal_request_fields_invalid")


def _number(value, key, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("terminal_parameter_out_of_range:" + key)
    return value


def _task_configuration(task):
    return {**{key: deepcopy(task[key]) for key in _CONFIG_FIELDS},
            **{key: deepcopy(task[key]) for key in ("ai_evidence", "ai_evidence_binding", "indicator_contract") if key in task}}


def _engine_source_identity():
    root = Path(__file__).resolve().parent
    return {name: sha256((root / name).read_bytes()).hexdigest()
            for name in ("backtest_engine.py", "strategy_signals.py", "market_calendar.py", "indicator_math.py")}


def _provider_source(meta, rows):
    lineage = meta.get("source_lineage")
    lineage = [lineage] if type(lineage) is str else lineage
    if type(lineage) is not list or not lineage or any(type(value) is not str or not value.strip() for value in lineage):
        raise ValueError("terminal_market_provider_unknown")
    names = list(dict.fromkeys([*lineage, *(row.get("source") for row in rows)]))
    if len(names) != 1 or type(names[0]) is not str or not names[0].strip():
        raise ValueError("terminal_market_provider_lineage_conflict")
    if any(marker in names[0].lower() for marker in ("quick_preview", "preview_seed", "offline-seed", "synthetic")):
        raise ValueError("terminal_synthetic_or_preview_source_blocked")
    return names[0]


def validate_terminal_strategy_params(strategy_dict, supplied):
    """Return explicit native signal parameters; reject values the engine clamps.

    The original engine uses ``value or default`` for several zero-valued
    thresholds. Those zeros are rejected, never displayed as an effective zero.
    Historical metadata fields remain unchanged; execution risk is separate.
    This validator does not grant new-research or execution capability.
    """
    identity = strategy_dict.get("id")
    if identity not in _SIGNAL_DEFAULTS:
        raise ValueError("terminal_strategy_parameter_contract_unavailable")
    declared = _detached(strategy_dict.get("params", {}))
    defaults = _SIGNAL_DEFAULTS[identity]
    _fields(supplied, set(declared) | set(defaults))
    for key in set(supplied) - set(defaults):
        if supplied[key] != declared[key]:
            raise ValueError("terminal_legacy_metadata_not_signal_parameter:" + key)
    values = {**declared, **defaults, **{key: value for key, value in declared.items() if key in defaults}, **_detached(supplied)}
    for key, default in defaults.items():
        value = values[key]
        integer = "window" in key or key in {"fast", "slow", "signal"}
        maximum = 100 if key in {"oversold", "overbought"} else 10000 if integer else 1e6
        _number(value, key, _MINIMUMS[identity][key], maximum)
        if integer and type(value) is not int:
            raise ValueError("terminal_integer_parameter_required:" + key)
    if identity == "dual_ma" and values["fast_window"] >= values["slow_window"]:
        raise ValueError("terminal_fast_window_must_be_smaller_than_slow_window")
    if identity == "macd" and values["fast"] >= values["slow"]:
        raise ValueError("terminal_fast_must_be_smaller_than_slow")
    if identity == "rsi" and values["oversold"] >= values["overbought"]:
        raise ValueError("terminal_rsi_threshold_order_invalid")
    if identity == "volume_trend" and values["max_atr_pct"] < values["min_atr_pct"]:
        raise ValueError("terminal_atr_threshold_order_invalid")
    if identity == "squeeze_breakout" and (values["atr_long_window"] < values["atr_short_window"] + 5
            or values["volume_long_window"] < values["volume_short_window"] + 5):
        raise ValueError("terminal_squeeze_long_window_would_be_clamped")
    return values


def _core_chart(snapshot, fills, *, run_id, report_hash):
    """Called only after the accepted run verifier has checked this snapshot."""
    def stamp(value):
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("terminal_core_replay_explicit_clock_required")
        return int(parsed.timestamp() * 1000)
    if snapshot.get("market") != "us_equity" or len(snapshot["candles"]) != len(snapshot["sessions"]):
        raise ValueError("terminal_core_replay_calendar_binding_invalid")
    rows, sessions = [], {}
    for candle, session in zip(snapshot["candles"], snapshot["sessions"]):
        timestamp = stamp(candle[0])
        if timestamp != stamp(session["open_utc"]):
            raise ValueError("terminal_core_replay_session_clock_conflict")
        sessions[timestamp] = session["date"]
        rows.append({"date": session["date"], "ts_ms": timestamp, "open": candle[1], "high": candle[2],
                     "low": candle[3], "close": candle[4], "volume": candle[5], "complete": True, "provisional": False})
    trades = []
    for original in fills:
        timestamp = stamp(original["fill_time"])
        if timestamp not in sessions or original["action"] not in {"BUY", "SELL"}:
            raise ValueError("terminal_core_replay_fill_session_binding_invalid")
        trades.append({**_detached(original), "date": sessions[timestamp], "ts_ms": timestamp,
                       "side": original["action"], "quantity": original["filled_quantity"] if "filled_quantity" in original else original["quantity"]})
    security = snapshot["security"]
    meta = {"asset_class": "US_EQUITY", "interval": "1D", "session": "REGULAR",
            "price_basis": snapshot["price_basis"], "volume_unit": snapshot["volume_unit"],
            "timezone": snapshot["timezone"], "security_id": security["security_id"], "exchange": security["exchange"],
            "currency": security["currency"], "security": _detached(security),
            "source_lineage": snapshot["snapshot_id"], "snapshot_schema": snapshot["schema_version"],
            "origin_reference": snapshot.get("price_source", {}).get("reference"), "source_authenticated": False}
    return {"rows": rows, "trades": trades, "meta": meta, "symbol": security["symbol"],
            "input_id": snapshot["snapshot_id"], "run_id": run_id, "report_hash": report_hash, "source": "FROZEN_RUN_INPUT"}


def _core_input_adapter(snapshot, identity, file_hash):
    """Adapt a verified snapshot, retaining its admission and availability gates.

    This is a separate reference receipt. The accepted snapshot and its embedded
    manifest/CSV are retained as their original bytes, never rewritten as native
    cache data. Native strategies still use their own execution model.
    """
    from .backtest_engine import prepare_backtest_dataset

    blockers = list(snapshot["research_admission"]["block_reasons"])
    if snapshot["research_admission"]["allowed"] is not True:
        blockers.append("core_research_admission_blocked")
    if (snapshot["evidence_kind"] != "IMPORTED_UNVERIFIED"
            or snapshot["research_admission"]["synthetic_only"] is not False):
        blockers.append("core_synthetic_or_unrecognized_evidence_blocked")
    provenance = [snapshot["security"]["security_id"]]
    for source in (snapshot["price_source"], snapshot["security_identity"]["source"],
                   snapshot["calendar"]["source"], snapshot["corporate_actions"]["source"]):
        provenance.extend((source["name"], source["reference"]))
    if any(any(marker in text.lower() for marker in ("synthetic", "quick_preview", "preview_seed", "offline-seed", "test_fixture"))
           or re.search(r"(?:^|[/:._ -])seed(?:$|[/:._ -])", text.lower()) for text in provenance):
        blockers.append("core_synthetic_or_preview_source_blocked")
    sessions = snapshot["sessions"]
    lag = timedelta(seconds=snapshot["bar_availability_lag_seconds"])
    for previous, following in zip(sessions, sessions[1:]):
        close = datetime.fromisoformat(previous["close_utc"].replace("Z", "+00:00"))
        opened = datetime.fromisoformat(following["open_utc"].replace("Z", "+00:00"))
        if close + lag >= opened:
            blockers.append("core_bar_unavailable_before_next_open")
            break
    chart = _core_chart(snapshot, [], run_id=None, report_hash=None)
    provider = snapshot["price_source"]["name"]
    rows = [{**row, "source": provider} for row in chart["rows"]]
    meta = {**chart["meta"], "source_lineage": [provider], "core_snapshot_id": snapshot["snapshot_id"],
            "as_of": snapshot["as_of"], "retrieved_at": snapshot["retrieved_at"],
            "availability_policy": snapshot["availability_policy"],
            "bar_availability_lag_seconds": snapshot["bar_availability_lag_seconds"],
            "security_identity": snapshot["security_identity"], "calendar": snapshot["calendar"],
            "corporate_actions": snapshot["corporate_actions"], "sessions": sessions,
            "price_source": {key: snapshot["price_source"][key] for key in ("name", "reference", "retrieved_at", "raw_sha256", "truth_status")},
            "core_research_admission": snapshot["research_admission"], "evidence_kind": snapshot["evidence_kind"],
            "source_authentication": snapshot["source_authentication"]}
    try:
        _provider_source(meta, rows)
    except ValueError as exc:
        blockers.append(str(exc))
    # Run only the original data validator, never the strategy/economic runner.
    validation = prepare_backtest_dataset(rows, symbol=chart["symbol"], source=provider,
                                          timeframe="1D", minimum_rows=1, market="stock")
    blockers.extend("native_data:" + reason for reason in validation["manifest"]["blockers"])
    blockers = list(dict.fromkeys(blockers))
    reference = {"core_input_id": identity, "snapshot_hash": snapshot["snapshot_id"],
                 "file_sha256": file_hash, "source_manifest_hash": snapshot["raw_input"]["manifest_sha256"],
                 "csv_sha256": snapshot["raw_input"]["csv_sha256"], "original_schema": snapshot["schema_version"],
                 "original_bytes_path": "terminal-inputs/core-originals/" + file_hash + ".json",
                 "original_rewritten": False}
    quality = {"status": "BLOCK" if blockers else "REVIEW", "blockers": blockers,
               "warnings": ["原始导入声明与价格未经过独立来源认证；只可用于原策略描述性研究。",
                            "原策略使用自身成交与风控规则，不能与其他引擎视为同一执行模型。"],
               "source_authenticated": False, "research_only": True, "core_us_equity_import_allowed": False}
    return _seal({"schema_version": "hakimi-terminal-input-v1", "symbol": chart["symbol"], "bar": "1D",
                  "source_id": "core-price-snapshot:" + snapshot["snapshot_id"], "source": provider,
                  "source_digest": snapshot["snapshot_id"], "rows": rows, "meta": meta, "quality": quality,
                  "core_reference": reference, "excluded_incomplete_count": 0, "permissions": dict(PERMISSIONS)})


class TerminalResearchService:
    def __init__(self, service, market_reader, catalog, runner, fingerprint, history_reader=None):
        self.core = service
        self.workspace = Path(service.workspace).absolute()
        self.market_reader, self.catalog, self.runner, self.fingerprint = market_reader, catalog, runner, fingerprint
        self.history_reader = history_reader
        self._lock = RLock()
        self._safe(self.workspace)
        self.judgments = TerminalJudgmentService(self)
        self.exit_research = TerminalExitResearchService(self)

    def _safe(self, path):
        path = Path(path).absolute()
        if path != self.workspace and not path.is_relative_to(self.workspace):
            raise ValueError("terminal_path_outside_workspace")
        for prefix in (path, *path.parents):
            try:
                info = prefix.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError("terminal_reparse_path_not_supported")
        return path

    def _read(self, path, *, key="id", schema=None):
        path = self._safe(path)
        value = json.loads(path.read_bytes())
        if type(value) is not dict or not _HASH.fullmatch(str(value.get(key, ""))):
            raise ValueError("terminal_record_identity_invalid")
        body = {name: item for name, item in value.items() if name != key}
        if _digest(body) != value[key] or (schema is not None and value.get("schema_version") != schema):
            raise ValueError("terminal_record_changed_or_schema_invalid")
        return value

    def _write(self, path, value):
        self._write_bytes(path, _bytes(value))

    def _write_bytes(self, path, raw):
        path = self._safe(path)
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError("terminal_immutable_file_conflict")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._safe(path.with_name("." + path.name + "." + secrets.token_hex(12) + ".pending"))
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # Atomic publication with no replacement on Windows and POSIX.
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise ValueError("terminal_immutable_file_conflict")
        finally:
            temporary.unlink(missing_ok=True)

    def _catalog(self):
        value = self.catalog()
        rows = value.get("items", value.get("strategies", [])) if isinstance(value, dict) else value
        if not isinstance(rows, list):
            raise ValueError("terminal_catalog_invalid")
        items = []
        seen = set()
        for original in rows:
            item = _detached(original)
            identity = item.get("id")
            if type(identity) is not str or not identity or identity in seen:
                raise ValueError("terminal_catalog_identity_invalid")
            seen.add(identity)
            capability = item.get("capability", item.get("validation", {}))
            if type(capability) is not dict:
                capability = {}
            params = item.get("params", {})
            if type(params) is not dict:
                raise ValueError("terminal_catalog_parameters_invalid")
            if identity in _SIGNAL_DEFAULTS:
                params = validate_terminal_strategy_params(item, {})
            research_risk = strategy_research_risk_profile(identity, {"position_pct": 25.0,
                "take_profit_pct": 0.0, "stop_loss_pct": 8.0, "fee_rate": .0005, "slippage_bps": 2.0})["risk"]
            default_risk = {key: research_risk[key] for key in ("position_pct", "take_profit_pct", "stop_loss_pct", "leverage")}
            item.update(engine_id=ENGINE_ID, capability=capability, params=params,
                        parameter_fields=[{"key": key, "label": _LABELS.get(key, key),
                                           "type": "integer" if type(number) is int else "number", "unit": "native", "value": number}
                                          for key, number in params.items() if key in _SIGNAL_DEFAULTS.get(identity, {})],
                        default_risk=default_risk, default_costs={"fee_rate": .0005, "slippage_bps": 2.0},
                        parameter_note="信号参数使用原策略原生单位；执行仓位和止盈止损以独立风控字段为准。",
                        equivalent_core_strategy=None, permissions=dict(PERMISSIONS))
            items.append(item)
        return {"items": items, "core_items": self.core.read("strategies").get("items", []),
                "warnings": [], "engine_id": ENGINE_ID, "new_economic_runs": 0,
                "interpretation": "原策略与股票量化策略保留各自规则，不按同名策略自动替换。"}

    def _strategy(self, identity, *, new_work=False):
        matches = [item for item in self._catalog()["items"] if item["id"] == identity]
        if len(matches) != 1:
            raise ValueError("terminal_unknown_strategy_no_fallback")
        item = matches[0]
        cap = item["capability"]
        if new_work and (cap.get("backtest_supported") is not True or cap.get("new_research_allowed") is not True):
            raise ValueError("terminal_strategy_new_research_blocked:" + str(cap.get("paper_blocker") or cap.get("blocker") or identity))
        return item

    @staticmethod
    def _symbol(value):
        if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9.^:_-]{1,40}", value):
            raise ValueError("terminal_symbol_invalid")
        return value.upper()

    def _market(self, symbol, limit=2000, source_id=None):
        symbol = self._symbol(symbol)
        if type(limit) is not int or not 1 <= limit <= 5000:
            raise ValueError("terminal_market_limit_invalid")
        if source_id is not None and (type(source_id) is not str or not source_id or len(source_id) > 300 or any(ord(c) < 32 for c in source_id)):
            raise ValueError("terminal_market_source_id_invalid")
        value = _detached(self.market_reader(symbol, limit=limit, **({"source_id": source_id} if source_id is not None else {})))
        if (type(value) is not dict or value.get("symbol") != symbol or value.get("bar") != "1D"
                or not _HASH.fullmatch(str(value.get("digest", "")))
                or type(value.get("rows")) is not list or type(value.get("meta")) is not dict
                or type(value.get("quality")) is not dict):
            raise ValueError("terminal_market_snapshot_invalid")
        if value["quality"].get("status") != "BLOCK" and (type(value.get("source_id")) is not str or not value["source_id"]):
            raise ValueError("terminal_market_source_unknown")
        if source_id is not None and value["quality"].get("status") != "BLOCK" and value["source_id"] != source_id:
            raise ValueError("terminal_market_source_selection_changed")
        value["permissions"] = dict(PERMISSIONS)
        value["new_economic_runs"] = 0
        return value

    def _freeze(self, payload):
        _fields(payload, {"symbol", "limit", "expected_digest", "source_id"}, {"symbol", "expected_digest"})
        if not _HASH.fullmatch(str(payload["expected_digest"])):
            raise ValueError("terminal_expected_market_digest_required")
        value = self._market(payload["symbol"], payload.get("limit", 2000), payload.get("source_id"))
        if value["digest"] != payload["expected_digest"]:
            raise ValueError("terminal_market_changed_preview_again")
        if value["quality"].get("status") != "REVIEW" or type(value.get("source_id")) is not str or not value["source_id"]:
            raise ValueError("terminal_market_blocked:" + ";".join(value["quality"].get("blockers", [])))
        rows, excluded = [], int(value.get("excluded_incomplete_count", 0))
        previous_time = None
        dates = set()
        for original in value["rows"]:
            if type(original) is not dict:
                raise ValueError("terminal_market_row_invalid")
            if original.get("complete") is not True or original.get("provisional") is not False:
                excluded += 1
                continue
            row = _detached(original)
            session = row.get("date")
            if type(session) is not str or date.fromisoformat(session).isoformat() != session or session in dates:
                raise ValueError("terminal_market_session_invalid")
            stamp = row.get("ts_ms")
            if type(stamp) is not int or stamp <= 0 or (previous_time is not None and stamp <= previous_time):
                raise ValueError("terminal_market_chronology_invalid")
            for field in ("open", "high", "low", "close"):
                _number(row.get(field), field, 1e-12, 1e100)
            _number(row.get("volume"), "volume", 0, 1e100)
            if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]) or row["low"] > row["high"]:
                raise ValueError("terminal_market_ohlc_invalid")
            previous_time = stamp
            dates.add(session)
            rows.append(row)
        quality = _detached(value["quality"])
        if quality.get("status") not in {"REVIEW", "BLOCK"}:
            quality.update(status="BLOCK", blockers=[*quality.get("blockers", []), "unknown_market_quality_status"])
        if not rows:
            quality.update(status="BLOCK", blockers=[*quality.get("blockers", []), "no_completed_rows"])
        provider_source = _provider_source(value["meta"], rows)
        # Cache provenance is retained, never promoted into authenticated data.
        quality.update(source_authenticated=False, research_only=True, core_us_equity_import_allowed=False)
        record = _seal({"schema_version": "hakimi-terminal-input-v1", "symbol": value["symbol"], "bar": "1D",
                        "source_id": value["source_id"], "source": provider_source, "source_digest": value["digest"], "rows": rows,
                        "meta": value["meta"], "quality": quality, "excluded_incomplete_count": excluded,
                        "permissions": dict(PERMISSIONS)})
        self._write(self.workspace / "terminal-inputs" / (record["id"] + ".json"), record)
        return self._input_view(record)

    def _input(self, identity):
        if type(identity) is not str or not _HASH.fullmatch(identity):
            raise ValueError("terminal_input_id_invalid")
        value = self._read(self.workspace / "terminal-inputs" / (identity + ".json"), schema="hakimi-terminal-input-v1")
        if value["id"] != identity:
            raise ValueError("terminal_input_identity_conflict")
        reference = value.get("core_reference")
        if reference is not None:
            file_hash = reference.get("file_sha256")
            if not _HASH.fullmatch(str(file_hash)):
                raise ValueError("terminal_core_original_identity_invalid")
            path = self._safe(self.workspace / "terminal-inputs" / "core-originals" / (file_hash + ".json"))
            raw, snapshot = self._verified_core_document(path)
            if sha256(raw).hexdigest() != file_hash:
                raise ValueError("terminal_core_original_bytes_changed")
            expected = _core_input_adapter(snapshot, reference.get("core_input_id"), file_hash)
            if expected != value or expected["quality"]["status"] != "REVIEW":
                raise ValueError("terminal_core_reference_changed_or_blocked")
        return value

    @staticmethod
    def _verified_core_document(path):
        from hakimi_terminal_research.documents import parse_document
        from hakimi_terminal_research.equity_dataset import verify_equity_snapshot
        with path.open("rb") as stream:
            raw = stream.read(64 * 1024 * 1024 + 1)
        return raw, verify_equity_snapshot(parse_document(raw))

    def _core_input(self, identity):
        if type(identity) is not str or not re.fullmatch(r"[0-9a-f]{24}", identity):
            raise ValueError("terminal_core_input_id_invalid")
        path = self._safe(self.core._lookup("inputs", identity))
        raw, snapshot = self._verified_core_document(path)
        return raw, _core_input_adapter(snapshot, identity, sha256(raw).hexdigest())

    def _core_inputs(self, identity=None):
        inventory = self.core.read("inputs") if identity is None else {"items": [self.core.read("inputs", identity)], "warnings": []}
        items, warnings = [], list(inventory.get("warnings", []))
        for original in inventory["items"]:
            if original.get("kind") != "PRICE_SNAPSHOT":
                continue
            item = {"id": original["id"], "input_id": original["id"], "label": original.get("label", ""),
                    "symbol": original["security"]["symbol"], "available": False, "status": "BLOCKED", "blockers": [],
                    "file_sha256": original["file_sha256"], "snapshot_hash": original["input_id"],
                    "core_snapshot_id": original["input_id"], "evidence_kind": original["evidence_kind"],
                    "source_manifest_hash": None, "date_start": original["coverage_start"],
                    "date_end": original["coverage_end"], "row_count": original["sessions"], "meta": {},
                    "permissions": dict(PERMISSIONS)}
            try:
                _, record = self._core_input(original["id"])
                if (record["core_reference"]["file_sha256"] != original["file_sha256"]
                        or record["source_digest"] != original["input_id"]):
                    raise ValueError("terminal_core_input_changed_refresh_list")
                item.update(available=record["quality"]["status"] == "REVIEW", blockers=record["quality"]["blockers"],
                            meta=record["meta"], source_manifest_hash=record["core_reference"]["source_manifest_hash"])
                item["status"] = "AVAILABLE" if item["available"] else "BLOCKED"
            except (ValueError, OSError, KeyError, TypeError) as exc:
                item["blockers"] = [str(exc)]
            items.append(item)
        return {"items": items, "warnings": warnings, "new_economic_runs": 0, "permissions": dict(PERMISSIONS)}

    def _import_core_input(self, payload):
        _fields(payload, {"input_id"}, {"input_id"})
        raw, record = self._core_input(payload["input_id"])
        if record["quality"]["status"] != "REVIEW":
            raise ValueError("terminal_core_input_blocked:" + ";".join(record["quality"]["blockers"]))
        # Retain precisely the bytes which were verified above, independent of a
        # later edit/deletion of the source file. No core file is modified.
        path = self.workspace / "terminal-inputs" / "core-originals" / (record["core_reference"]["file_sha256"] + ".json")
        self._write_bytes(path, raw)
        self._write(self.workspace / "terminal-inputs" / (record["id"] + ".json"), record)
        return self._input_view(record)

    @staticmethod
    def _input_view(value, *, rows=True):
        view = dict(value)
        data = value["rows"]
        view.update(input_id=value["id"], digest=value["source_digest"], row_count=len(data),
                    date_start=data[0]["date"] if data else None, date_end=data[-1]["date"] if data else None,
                    evidence_status="UNVERIFIED", new_economic_runs=0, permissions=dict(PERMISSIONS))
        if not rows:
            view.pop("rows", None)
        return view

    def _family(self, identity):
        if type(identity) is not str or not _FAMILY.fullmatch(identity):
            raise ValueError("terminal_family_id_invalid")
        root = self._safe(self.workspace / "terminal-tasks" / identity)
        header = self._read(root / "family.json", key="family_hash", schema="hakimi-terminal-family-v1")
        if header["family_id"] != identity:
            raise ValueError("terminal_family_identity_conflict")
        previous, selected, state, version = None, None, None, 0
        events = sorted((root / "journal").glob("*.json"))
        for sequence, path in enumerate(events, 1):
            event = self._read(path, schema="hakimi-terminal-task-event-v1")
            if (path.name != f"{sequence:06d}.json" or event["sequence"] != sequence or event["previous_hash"] != previous
                    or event["family_id"] != identity or event["state"] not in {"ENABLED", "PAUSED"}):
                raise ValueError("terminal_task_journal_invalid")
            task = self._task_record(event["task_id"], family_id=identity)
            if event["action"] in {"CREATE", "REVISE"}:
                if ((sequence == 1) != (event["action"] == "CREATE") or task["version"] != version + 1
                        or task["parent_task_id"] != selected or (state is not None and event["state"] != state)):
                    raise ValueError("terminal_task_version_chain_invalid")
                selected, version = task["id"], task["version"]
            elif event["action"] != "STATE" or event["task_id"] != selected:
                raise ValueError("terminal_task_state_chain_invalid")
            previous, state = event["id"], event["state"]
        if selected is None:
            raise ValueError("terminal_task_commit_incomplete_no_retry")
        return {"root": root, "header": header, "task_id": selected, "state": state,
                "version": version, "sequence": len(events), "last_event": previous}

    def _task_record(self, identity, *, family_id=None):
        if type(identity) is not str or not _HASH.fullmatch(identity):
            raise ValueError("terminal_task_id_invalid")
        roots = ([self.workspace / "terminal-tasks" / family_id] if family_id is not None
                 else sorted((self.workspace / "terminal-tasks").glob("*")))
        matches = [self._safe(root / "versions" / (identity + ".json")) for root in roots
                   if self._safe(root / "versions" / (identity + ".json")).is_file()]
        if len(matches) != 1:
            raise ValueError("terminal_task_not_found_or_ambiguous")
        value = self._read(matches[0], schema="hakimi-terminal-task-v1")
        if (value["id"] != identity or value["family_id"] != matches[0].parent.parent.name
                or value["engine_id"] not in READABLE_ENGINE_IDS):
            raise ValueError("terminal_task_identity_conflict")
        return value

    def _task_view(self, task, family=None):
        family = family or self._family(task["family_id"])
        requires_revision = (task["engine_id"] != ENGINE_ID
                             or task["engine_source_identity"] != _engine_source_identity()
                             or task["fingerprint"] != self.fingerprint(task["strategy_id"], deepcopy(task["strategy_params"])))
        return {**task, "task_id": task["id"], "name": task["title"], "state": family["state"],
                "selected": task["id"] == family["task_id"], "selected_task_id": family["task_id"],
                "input_summary": self._input_view(self._input(task["input_id"]), rows=False),
                "requires_revision": requires_revision,
                "run_compatibility": "CREATE_NEW_VERSION" if requires_revision else "CURRENT",
                "permissions": dict(PERMISSIONS), "new_economic_runs": 0}

    def _event(self, family, task_id, action, state):
        header = family["header"]
        event = _seal({"schema_version": "hakimi-terminal-task-event-v1", "family_id": header["family_id"],
                       "sequence": family["sequence"] + 1, "previous_hash": family["last_event"],
                       "task_id": task_id, "action": action, "state": state})
        self._write(family["root"] / "journal" / f"{event['sequence']:06d}.json", event)

    def _save_task(self, payload):
        _fields(payload, {"name", "strategy_id", "strategy_params", "input_id", "risk", "costs", "parent_task_id", "ai_evidence"},
                {"name", "strategy_id", "input_id", "risk", "costs"})
        name = payload["name"]
        if type(name) is not str or not name.strip() or len(name) > 120 or any(ord(c) < 32 for c in name):
            raise ValueError("terminal_task_name_invalid")
        strategy = self._strategy(payload["strategy_id"], new_work=True)
        params = validate_terminal_strategy_params(strategy, payload.get("strategy_params", {}))
        risk, costs = _detached(payload["risk"]), _detached(payload["costs"])
        _fields(risk, {"position_pct", "take_profit_pct", "stop_loss_pct", "leverage"}, {"position_pct", "take_profit_pct", "stop_loss_pct", "leverage"})
        _fields(costs, {"fee_rate", "slippage_bps"}, {"fee_rate", "slippage_bps"})
        _number(risk["position_pct"], "position_pct", .000001, 100)
        _number(risk["take_profit_pct"], "take_profit_pct", 0, 1000)
        _number(risk["stop_loss_pct"], "stop_loss_pct", 0, 100)
        if type(risk["leverage"]) not in (int, float) or risk["leverage"] != 1:
            raise ValueError("terminal_research_requires_leverage_one")
        _number(costs["fee_rate"], "fee_rate", 0, .02)
        _number(costs["slippage_bps"], "slippage_bps", 0, 500)
        data = self._input(payload["input_id"])
        ai_reference = {}
        if "ai_evidence" in payload:
            evidence = validate_ai_evidence(payload["ai_evidence"], data)
            ai_reference = {"ai_evidence": evidence, "ai_evidence_binding": ai_evidence_binding(evidence, data)}
        fingerprint = self.fingerprint(strategy["id"], deepcopy(params))
        if type(fingerprint) is not str or not _HASH.fullmatch(fingerprint):
            raise ValueError("terminal_strategy_fingerprint_invalid")
        parent_id = payload.get("parent_task_id")
        if parent_id is not None:
            previous = self._task_record(parent_id)
            family = self._family(previous["family_id"])
            if family["task_id"] != parent_id:
                raise ValueError("terminal_task_version_changed_reload_first")
            family_id, version = previous["family_id"], family["version"] + 1
        else:
            family_id, version = secrets.token_hex(16), 1
            root = self._safe(self.workspace / "terminal-tasks" / family_id)
            header = _seal({"schema_version": "hakimi-terminal-family-v1", "family_id": family_id}, "family_hash")
            family = {"root": root, "header": header, "sequence": 0, "last_event": None, "state": "ENABLED"}
        task = _seal({"schema_version": "hakimi-terminal-task-v1", "family_id": family_id, "version": version,
                      "parent_task_id": parent_id, "title": name.strip(), "engine_id": ENGINE_ID,
                      "strategy_id": strategy["id"], "strategy_name": strategy.get("name", strategy["id"]),
                      "strategy_params": params, "risk": risk, "costs": costs, "input_id": data["id"],
                      "symbol": data["symbol"], "fingerprint": fingerprint, "execution_model": EXECUTION_MODEL,
                      "engine_source_identity": _engine_source_identity(),
                      "indicator_contract": deepcopy(INDICATOR_CONTRACT),
                      "initial_cash": 10000.0, "direction_mode": "LONG_ONLY", "end_policy": "MARK_TO_MARKET",
                      "warmup_rows": strategy_startup_candles_for_params(strategy["id"], params),
                      **ai_reference, "permissions": dict(PERMISSIONS)})
        if version == 1:
            self._write(family["root"] / "family.json", family["header"])
        self._write(family["root"] / "versions" / (task["id"] + ".json"), task)
        self._event(family, task["id"], "CREATE" if version == 1 else "REVISE", family["state"])
        return self._task_view(task)

    def _set_state(self, payload):
        _fields(payload, {"family_id", "state", "expected_task_id"}, {"family_id", "state", "expected_task_id"})
        if payload["state"] not in {"ENABLED", "PAUSED"}:
            raise ValueError("terminal_task_state_invalid")
        family = self._family(payload["family_id"])
        if family["task_id"] != payload["expected_task_id"]:
            raise ValueError("terminal_task_version_changed_reload_first")
        if family["state"] != payload["state"]:
            self._event(family, family["task_id"], "STATE", payload["state"])
        return self._task_view(self._task_record(family["task_id"]))

    def _report_view(self, report, *, detail=True):
        value = {**report, "run_id": report["id"], "report_hash": report["id"], "permissions": dict(PERMISSIONS)}
        if detail and report.get("status") == "COMPLETED":
            data = self._input(report["configuration"]["input_id"])
            value["chart"] = {"rows": data["rows"], "trades": report["result"].get("trades", []),
                              "meta": data["meta"], "symbol": data["symbol"], "input_id": data["id"],
                               "run_id": report["id"], "report_hash": report["id"], "source": "FROZEN_RUN_INPUT",
                               "indicator_contract": deepcopy(report["configuration"].get("indicator_contract")),
                               "engine_id": report["engine_id"]}
        return value

    def _verified_report(self, root):
        root = self._safe(root)
        report = self._read(root / "report.json", schema="hakimi-terminal-run-v1")
        started = self._read(root / "started.json", schema="hakimi-terminal-run-start-v1")
        task = self._task_record(report["task_id"])
        expected_operation = _digest({"task_id": task["id"], "input_id": task["input_id"], "fingerprint": task["fingerprint"]})
        if (root.name != expected_operation or report["operation_id"] != expected_operation
                or started["operation_id"] != expected_operation or started["task_id"] != task["id"]
                or started["input_id"] != task["input_id"] or report["family_id"] != task["family_id"]
                or report["version"] != task["version"] or report["started_at"] != started["started_at"]
                or report["engine_id"] != task["engine_id"] or report["strategy_id"] != task["strategy_id"]
                or report["configuration"] != _task_configuration(task)
                or report["input_summary"] != self._input_view(self._input(task["input_id"]), rows=False)):
            raise ValueError("terminal_saved_run_binding_conflict")
        return report

    def _run(self, payload):
        _fields(payload, {"task_id"}, {"task_id"})
        task = self._task_record(payload["task_id"])
        family = self._family(task["family_id"])
        if family["task_id"] != task["id"]:
            raise ValueError("terminal_task_version_changed_reload_first")
        if family["state"] != "ENABLED":
            raise ValueError("terminal_task_paused")
        self._strategy(task["strategy_id"], new_work=True)
        if task["engine_id"] != ENGINE_ID:
            raise ValueError("terminal_strategy_implementation_changed_create_new_version")
        current_fingerprint = self.fingerprint(task["strategy_id"], deepcopy(task["strategy_params"]))
        if current_fingerprint != task["fingerprint"]:
            raise ValueError("terminal_strategy_implementation_changed_create_new_version")
        if task["engine_source_identity"] != _engine_source_identity():
            raise ValueError("terminal_execution_source_changed_create_new_version")
        data = self._input(task["input_id"])
        if data["quality"].get("status") != "REVIEW":
            raise ValueError("terminal_input_blocked:" + ";".join(data["quality"].get("blockers", [])))
        if len(data["rows"]) <= task["warmup_rows"]:
            raise ValueError("terminal_insufficient_completed_history_for_warmup")
        provider_source = _provider_source(data["meta"], data["rows"])
        operation_id = _digest({"task_id": task["id"], "input_id": data["id"], "fingerprint": current_fingerprint})
        root = self._safe(self.workspace / "terminal-runs" / operation_id)
        if (root / "report.json").exists():
            report = self._verified_report(root)
            if report["operation_id"] != operation_id or report["task_id"] != task["id"]:
                raise ValueError("terminal_run_binding_conflict")
            return {**self._report_view(report), "reused": True, "new_economic_runs": 0}
        if (root / "started.json").exists():
            self._read(root / "started.json", schema="hakimi-terminal-run-start-v1")
            return {"id": operation_id, "operation_id": operation_id, "task_id": task["id"], "status": "UNKNOWN",
                    "automatic_retry": False, "message": "此前运行未留下完整结果；保留原记录，不会自动重跑。",
                    "permissions": dict(PERMISSIONS)}
        started = _seal({"schema_version": "hakimi-terminal-run-start-v1", "operation_id": operation_id,
                         "task_id": task["id"], "input_id": data["id"], "started_at": _now(), "automatic_retry": False})
        self._write(root / "started.json", started)
        market = {"ok": True, "symbol": data["symbol"], "rows": deepcopy(data["rows"]), "source": provider_source,
                  "source_id": data["source_id"], "digest": data["source_digest"], "meta": deepcopy(data["meta"]),
                  "quality": deepcopy(data["quality"]), "data_points": len(data["rows"]), "complete": True,
                  "input_id": data["id"], "frozen_input": True}
        configuration = _task_configuration(task)
        try:
            result = _detached(self.runner(strategy_id=task["strategy_id"], symbol=data["symbol"],
                limit=len(data["rows"]), market_payload=market, strategy_params=deepcopy(task["strategy_params"]),
                **task["risk"], **task["costs"]))
            if type(result) is not dict or result.get("ok") is not True:
                raise ValueError("terminal_runner_did_not_complete:" + str(result.get("error", "invalid_result") if isinstance(result, dict) else "invalid_result"))
            if (type(result.get("order_event_count")) is int and result["order_event_count"] != len(result.get("trades", []))
                    or type(result.get("evaluation_window", {}).get("evaluated_rows")) is int
                    and result["evaluation_window"]["evaluated_rows"] != len(result.get("equity_curve", []))):
                raise ValueError("terminal_runner_history_truncated")
            status, error = "COMPLETED", None
        except Exception as exc:
            result, status, error = None, "UNKNOWN", str(exc)[:2000]
        report = _seal({"schema_version": "hakimi-terminal-run-v1", "operation_id": operation_id,
                        "task_id": task["id"], "family_id": task["family_id"], "version": task["version"],
                        "title": task["title"], "strategy_id": task["strategy_id"], "engine_id": ENGINE_ID,
                        "started_at": started["started_at"], "configuration": configuration,
                        "input_summary": self._input_view(data, rows=False), "quality": data["quality"],
                        "evidence_status": "UNVERIFIED", "status": status, "error": error, "result": result,
                        "automatic_retry": False, "permissions": dict(PERMISSIONS),
                        "limitations": ["原策略使用原信号和成交模型；与同名股票量化策略并非等价规则。",
                                        "本地行情来源未认证，结果仅供研究，不提供模拟或实盘授权。"]})
        self._write(root / "report.json", report)
        return {**self._report_view(report), "reused": False}

    def _list(self, resource):
        items, warnings = [], []
        root = self._safe(self.workspace / resource.replace("_", "-"))
        if not root.exists():
            return {"items": [], "warnings": [], "new_economic_runs": 0}
        paths = sorted(root.glob("*.json")) if resource == "terminal_inputs" else sorted(root.iterdir())
        for path in paths:
            try:
                self._safe(path)
                if resource == "terminal_inputs":
                    items.append(self._input_view(self._input(path.stem), rows=False))
                elif resource == "terminal_tasks":
                    family = self._family(path.name)
                    items.append(self._task_view(self._task_record(family["task_id"]), family))
                elif (path / "report.json").is_file():
                    items.append(self._report_view(self._verified_report(path), detail=False))
                elif (path / "started.json").is_file():
                    started = self._read(path / "started.json", schema="hakimi-terminal-run-start-v1")
                    items.append({**started, "id": path.name, "status": "UNKNOWN", "automatic_retry": False,
                                  "message": "运行记录未完整提交；不会自动重试。", "permissions": dict(PERMISSIONS)})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append(path.name + ": " + str(exc))
        return {"items": items, "warnings": warnings, "new_economic_runs": 0}

    def _core_replay(self, identity):
        # The accepted verifier, rather than matching a market symbol, owns this
        # binding. This returns the exact retained security/calendar metadata.
        from hakimi_terminal_research.offline_app import verify_run
        path = self.core._lookup("runs", identity)
        self.core._guard_tree(path)
        manifest, report, snapshot = verify_run(path)
        detail = self.core.read("runs", identity)
        chart = _core_chart(snapshot.document, detail["fills"], run_id=manifest["run_id"], report_hash=report["report_hash"])
        return {"id": identity, "engine_id": "research.accepted-equity", "run_id": manifest["run_id"],
                "report_hash": report["report_hash"], "task_id": manifest["task_id"],
                "snapshot": _detached(snapshot.document), "configuration": detail["configuration"],
                **chart, "chart": chart,
                "permissions": dict(PERMISSIONS), "new_economic_runs": 0}

    def _compare(self, payload):
        _fields(payload, {"run_ids"}, {"run_ids"})
        ids = payload["run_ids"]
        if type(ids) is not list or not 2 <= len(ids) <= 10 or any(type(item) is not str for item in ids) or len(set(ids)) != len(ids):
            raise ValueError("terminal_comparison_requires_distinct_saved_runs")
        rows = []
        for identity in ids:
            if re.fullmatch(r"[0-9a-f]{24}", identity):
                detail = self.core.read("runs", identity)
                summary = detail["summary"]
                rows.append({"id": identity, "engine_id": "research.accepted-equity", "title": summary.get("task_display_name"),
                             "version": summary.get("task_version_number"), "configuration": detail["configuration"],
                             "metrics": {"total_return_pct": summary["total_return"] * 100,
                                         "max_drawdown_pct": summary["max_drawdown"] * 100,
                                         "total_fees": summary["total_fees"]}, "conditions": None})
                continue
            report = self.read("terminal_runs", identity)
            if report.get("status") != "COMPLETED":
                raise ValueError("terminal_comparison_incomplete_run")
            config, result = report["configuration"], report["result"]
            rows.append({"id": identity, "engine_id": report["engine_id"], "title": report["title"],
                         "version": report["version"], "configuration": config,
                         "metrics": {key: result.get(key) for key in ("total_return_pct", "max_drawdown_pct", "total_fees", "final_equity", "order_event_count")},
                         "conditions": {"input_id": config["input_id"], "costs": config["costs"],
                                        "execution_model": config["execution_model"], "initial_cash": config["initial_cash"],
                                        "engine_source_identity": config["engine_source_identity"],
                                        "direction_mode": config["direction_mode"], "end_policy": config["end_policy"],
                                        "warmup_rows": config["warmup_rows"],
                                        "evaluation_window": result.get("evaluation_window")}})
        same_engine = all(row["engine_id"] == rows[0]["engine_id"] for row in rows)
        if same_engine and rows[0]["engine_id"] == "research.accepted-equity":
            return self.core.mutate("compare", payload)
        mismatches = []
        for index, row in enumerate(rows[1:], 2):
            fields = []
            if row["engine_id"] != rows[0]["engine_id"]:
                fields.append("engine_id")
            if row["conditions"] != rows[0]["conditions"]:
                fields.extend(key for key in (rows[0]["conditions"] or {}) if (row["conditions"] or {}).get(key) != rows[0]["conditions"][key])
                if not fields:
                    fields.append("comparison_contract")
            if fields:
                mismatches.append({"row": index, "fields": fields})
        comparable = same_engine and not mismatches
        differences = []
        if comparable:
            for index, row in enumerate(rows[1:], 2):
                differences.append({"row": index, **{key: row["metrics"][key] - rows[0]["metrics"][key]
                                    for key in row["metrics"] if type(row["metrics"][key]) in (int, float)
                                    and type(rows[0]["metrics"].get(key)) in (int, float)}})
        return {"schema_version": "hakimi-terminal-comparison-v1", "status": "COMPARABLE_CONDITIONS" if comparable else "NOT_COMPARABLE",
                "rows": rows, "mismatches": mismatches, "differences_from_first": differences,
                "new_economic_runs": 0, "shared_portfolio": False, "permissions": dict(PERMISSIONS),
                "interpretation": ["不同引擎或数据与评分条件不同时，只并排展示，不计算收益差。",
                                   "每项是独立本金的描述性研究，未认证数据与结果不能授予模拟或实盘权限。"]}

    def read(self, resource, identity=None):
        if resource in {"terminal_exit_experiments", "terminal_exit_runs", "terminal_exit_replay",
                        "terminal_structure_replay"}:
            with self._lock:
                return self.exit_research.read(resource, identity)
        if resource in {"terminal_judgments", "terminal_judgment_replay"}:
            with self._lock:
                return self.judgments.read(resource, identity)
        if resource == "terminal_catalog":
            return self._catalog()
        if resource == "terminal_core_inputs":
            return self._core_inputs(identity)
        if resource == "terminal_market":
            if type(identity) is not str:
                raise ValueError("terminal_symbol_required")
            symbol, _, source_id = identity.partition("/")
            return self._market(symbol, source_id=source_id or None)
        if resource == "core_replay":
            return self._core_replay(identity)
        if resource == "terminal_history":
            return self.history_reader(identity) if self.history_reader is not None else {"items": [], "warnings": ["terminal_history_reader_unavailable"], "new_economic_runs": 0}
        if resource == "terminal_reports":
            reader = getattr(self.history_reader, "reports", None)
            if not callable(reader):
                return {"items": [], "warnings": ["terminal_report_file_reader_unavailable"], "new_economic_runs": 0}
            return reader(identity)
        if resource in {"terminal_inputs", "terminal_tasks", "terminal_runs"}:
            if identity is None:
                return self._list(resource)
            if resource == "terminal_inputs":
                return self._input_view(self._input(identity))
            if resource == "terminal_tasks":
                if _FAMILY.fullmatch(str(identity)):
                    family = self._family(identity)
                    return self._task_view(self._task_record(family["task_id"]), family)
                return self._task_view(self._task_record(identity))
            if not _HASH.fullmatch(str(identity)):
                raise ValueError("terminal_run_id_invalid")
            for row in self._list("terminal_runs")["items"]:
                if row["id"] == identity:
                    return self._report_view(row) if row.get("schema_version") == "hakimi-terminal-run-v1" else row
            raise ValueError("terminal_run_not_found")
        return self.core.read(resource, identity)

    def mutate(self, action, payload):
        handlers = {"terminal_freeze_market": self._freeze, "terminal_save_task": self._save_task,
                    "terminal_import_core_input": self._import_core_input,
                    "terminal_set_task_state": self._set_state, "terminal_run_task": self._run,
                     "terminal_compare": self._compare,
                     "terminal_save_judgment": self.judgments.save,
                     "terminal_append_judgment_event": self.judgments.append,
                     "terminal_register_exit_experiment": self.exit_research.register,
                     "terminal_run_exit_experiment": self.exit_research.run}
        if action not in handlers:
            return self.core.mutate(action, payload)
        with self._lock:
            return handlers[action](_detached(payload))
