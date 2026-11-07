"""Additive, immutable judgments attached to verified frozen research inputs.

Judgments are observations, not orders or revisions of existing task/run files.
The indicator values are calculated once at creation and sealed with the then
loaded formula contract. Reading a judgment never recalculates those values.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
import re

from . import indicator_math


_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TASK_FAMILY = re.compile(r"[0-9a-f]{32}\Z")
_CORE_ID = re.compile(r"[0-9a-f]{24}\Z")
_CLIENT_REQUEST = re.compile(r"[A-Za-z0-9_-]{8,120}\Z")
_DIRECTIONS = frozenset({"LONG", "SHORT", "WAIT"})
_EVENT_TYPES = frozenset({"OBSERVATION", "TRIGGERED", "INVALIDATED", "USER_ACTION"})
_BINDING_KINDS = frozenset({"terminal_input", "terminal_task", "terminal_run", "core_run"})
_PARAM_DEFAULTS = {
    "sma": {"window": 20},
    "ema": {"window": 20},
    "bollinger": {"window": 20, "std_mult": 2.0},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
    "rsi": {"window": 14},
    "momentum": {"window": 20},
    "atr": {"window": 14},
}


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _copy(value):
    return json.loads(_bytes(value))


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _seal(value):
    return {**value, "id": _digest(value)}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fields(value, allowed, required=()):
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError("terminal_judgment_fields_invalid")


def _text(value, field, maximum, *, empty=False):
    if (type(value) is not str or len(value) > maximum or (not empty and not value.strip())
            or any(ord(char) < 32 and char not in "\n\t" for char in value)):
        raise ValueError("terminal_judgment_text_invalid:" + field)
    return value.strip()


def _day(value, field):
    if type(value) is not str:
        raise ValueError("terminal_judgment_date_invalid:" + field)
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("terminal_judgment_date_invalid:" + field) from exc
    return value


def _request_id(value):
    if type(value) is not str or not _CLIENT_REQUEST.fullmatch(value):
        raise ValueError("terminal_judgment_client_request_id_invalid")
    return value


def _params(raw):
    if raw is None:
        raw = {}
    _fields(raw, _PARAM_DEFAULTS)
    result = deepcopy(_PARAM_DEFAULTS)
    for name, supplied in raw.items():
        _fields(supplied, result[name])
        result[name].update(supplied)
    for name, values in result.items():
        for key, number in values.items():
            if key == "std_mult":
                if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= 100:
                    raise ValueError("terminal_judgment_indicator_parameter_invalid:" + name + "." + key)
            elif type(number) is not int or not 1 <= number <= 1000:
                raise ValueError("terminal_judgment_indicator_parameter_invalid:" + name + "." + key)
    if result["macd"]["fast"] >= result["macd"]["slow"]:
        raise ValueError("terminal_judgment_macd_fast_must_be_smaller")
    return result


def _prefix_rows(frozen_input, as_of):
    """Only observations available through a declared date, never later rows."""
    rows = frozen_input["rows"]
    if not rows or not rows[0]["date"] <= as_of <= rows[-1]["date"]:
        raise ValueError("terminal_judgment_as_of_outside_frozen_coverage")
    prefix = [row for row in rows if row["date"] <= as_of]
    if not prefix:
        raise ValueError("terminal_judgment_as_of_has_no_completed_rows")
    return prefix


def _indicator_snapshot(frozen_input, params, rows):
    """Use the frozen rows and current loaded implementation exactly once."""
    before = indicator_math.assert_loaded_source_current()
    closes = [row["close"] for row in rows]
    macd_line, macd_signal, macd_hist = indicator_math.macd(closes, **params["macd"])
    values = {
        "sma": indicator_math.sma(closes, **params["sma"])[-1],
        "ema": indicator_math.ema(closes, **params["ema"])[-1],
        "bollinger": indicator_math.bollinger(closes, **params["bollinger"])[-1],
        "macd": {"line": macd_line[-1], "signal": macd_signal[-1], "hist": macd_hist[-1]},
        "rsi": indicator_math.rsi(closes, **params["rsi"])[-1],
        "momentum": indicator_math.momentum(closes, **params["momentum"])[-1],
        "atr": indicator_math.atr(rows, **params["atr"])[-1],
    }
    if indicator_math.assert_loaded_source_current() != before:
        raise ValueError("terminal_judgment_indicator_source_changed_during_save")
    return {"derived": True, "provenance": "INDEPENDENT_INDICATOR_MATH",
            "contract": _copy(indicator_math.CONTRACT), "source_sha256": before,
            "params": _copy(params), "values": _copy(values),
            "bar_date": rows[-1]["date"], "input_id": frozen_input["id"]}


class TerminalJudgmentService:
    """Uses the terminal's existing safe paths, exclusive writes and global lock."""

    def __init__(self, terminal):
        self.terminal = terminal
        self.workspace = terminal.workspace

    def _root(self, identity):
        if type(identity) is not str or not _HASH.fullmatch(identity):
            raise ValueError("terminal_judgment_id_invalid")
        return self.terminal._safe(self.workspace / "terminal-judgments" / identity)

    def _intent_path(self, action, client_request_id):
        name = sha256((action + ":" + _request_id(client_request_id)).encode("utf-8")).hexdigest()
        return self.terminal._safe(self.workspace / "terminal-judgment-requests" / (name + ".json"))

    def _read_intent(self, path, action, payload_hash):
        intent = self.terminal._read(path, schema="hakimi-terminal-judgment-request-v1")
        if intent.get("action") != action or intent.get("payload_hash") != payload_hash:
            raise ValueError("terminal_judgment_request_id_conflict")
        return intent

    def _input(self, identity):
        frozen = self.terminal._input(identity)
        if frozen["quality"].get("status") != "REVIEW" or not frozen["rows"]:
            raise ValueError("terminal_judgment_frozen_input_blocked")
        return frozen

    def _binding(self, binding, frozen):
        _fields(binding, {"kind", "id"}, {"kind", "id"})
        kind, identity = binding["kind"], binding["id"]
        if kind not in _BINDING_KINDS or type(identity) is not str:
            raise ValueError("terminal_judgment_binding_invalid")
        if kind == "terminal_input":
            if identity != frozen["id"]:
                raise ValueError("terminal_judgment_binding_input_mismatch")
            receipt = {"kind": kind, "id": identity, "engine_id": "frozen-input-only",
                       "input_id": frozen["id"]}
            return receipt, None, None
        if kind == "terminal_task":
            if not _HASH.fullmatch(identity):
                raise ValueError("terminal_judgment_task_id_invalid")
            task = self.terminal._task_record(identity)
            self.terminal._family(task["family_id"])
            if task["input_id"] != frozen["id"]:
                raise ValueError("terminal_judgment_binding_input_mismatch")
            config_keys = ("engine_id", "strategy_id", "strategy_params", "risk", "costs",
                           "fingerprint", "execution_model", "engine_source_identity")
            optional_keys = ("ai_evidence", "ai_evidence_binding", "indicator_contract")
            config = {key: _copy(task[key]) for key in (*config_keys,
                      *(key for key in optional_keys if key in task))}
            receipt = {"kind": kind, "id": identity, "engine_id": task["engine_id"],
                       "input_id": frozen["id"], "family_id": task["family_id"],
                       "version": task["version"], "configuration_hash": _digest(config)}
            return receipt, config, None
        if kind == "terminal_run":
            if not _HASH.fullmatch(identity):
                raise ValueError("terminal_judgment_run_id_invalid")
            report = self.terminal.read("terminal_runs", identity)
            if report.get("schema_version") != "hakimi-terminal-run-v1" or report.get("status") != "COMPLETED":
                raise ValueError("terminal_judgment_run_not_completed")
            config = _copy(report["configuration"])
            if config["input_id"] != frozen["id"]:
                raise ValueError("terminal_judgment_binding_input_mismatch")
            receipt = {"kind": kind, "id": identity, "engine_id": report["engine_id"],
                       "input_id": frozen["id"], "task_id": report["task_id"],
                       "report_hash": report["report_hash"], "version": report["version"],
                       "configuration_hash": _digest(config)}
            summary = {"title": report["title"], "status": report["status"],
                       "run_id": report["run_id"], "report_hash": report["report_hash"],
                       "engine_id": report["engine_id"]}
            return receipt, config, summary
        if not _CORE_ID.fullmatch(identity):
            raise ValueError("terminal_judgment_core_run_id_invalid")
        replay = self.terminal._core_replay(identity)
        snapshot_id = replay["snapshot"]["snapshot_id"]
        reference = frozen.get("core_reference") or {}
        if (reference.get("snapshot_hash") != snapshot_id
                or frozen.get("meta", {}).get("core_snapshot_id") != snapshot_id
                or replay["symbol"] != frozen["symbol"]):
            raise ValueError("terminal_judgment_core_run_input_mismatch")
        config = _copy(replay["configuration"])
        receipt = {"kind": kind, "id": identity, "engine_id": replay["engine_id"],
                   "input_id": frozen["id"], "core_snapshot_id": snapshot_id,
                   "task_id": replay["task_id"], "run_id": replay["run_id"],
                   "report_hash": replay["report_hash"], "configuration_hash": _digest(config)}
        summary = {"status": "COMPLETED", "run_id": replay["run_id"],
                   "report_hash": replay["report_hash"], "engine_id": replay["engine_id"]}
        return receipt, config, summary

    def _events(self, identity, *, first_as_of):
        root = self._root(identity)
        folder = self.terminal._safe(root / "events")
        previous, prior_as_of, result = None, first_as_of, []
        for sequence, path in enumerate(sorted(folder.glob("*.json")), 1):
            event = self.terminal._read(path, schema="hakimi-terminal-judgment-event-v1")
            if (path.name != f"{sequence:06d}.json" or event.get("sequence") != sequence
                    or event.get("judgment_id") != identity or event.get("previous_hash") != previous
                    or event.get("event_type") not in _EVENT_TYPES
                    or _day(event.get("as_of"), "event_as_of") < prior_as_of
                    or event.get("order_authorized") is not False
                    or event.get("action_verification") != ("USER_REPORTED_UNVERIFIED"
                        if event["event_type"] == "USER_ACTION" else None)):
                raise ValueError("terminal_judgment_event_chain_invalid")
            previous, prior_as_of = event["id"], event["as_of"]
            result.append(event)
        return result, previous

    def _pending_event(self, identity):
        folder = self.terminal._safe(self.workspace / "terminal-judgment-requests")
        for path in folder.glob("*.json"):
            intent = self.terminal._read(path, schema="hakimi-terminal-judgment-request-v1")
            if intent.get("action") != "APPEND":
                continue
            event = intent.get("event") or {}
            if event.get("judgment_id") == identity:
                event_path = self.terminal._safe(self._root(identity) / "events" / f"{event['sequence']:06d}.json")
                if not event_path.is_file():
                    return True
        return False

    def _strict_detail(self, identity):
        record = self.terminal._read(self._root(identity) / "record.json", schema="hakimi-terminal-judgment-v1")
        if record["id"] != identity:
            raise ValueError("terminal_judgment_record_identity_conflict")
        frozen = self._input(record["input_id"])
        if (record["symbol"] != frozen["symbol"] or record["bar"] != frozen["bar"]
                or record.get("input_digest") != frozen["source_digest"]):
            raise ValueError("terminal_judgment_input_binding_changed")
        as_of = _day(record["as_of"], "as_of")
        prefix = _prefix_rows(frozen, as_of)
        if (record.get("prefix_rows_hash") != _digest(prefix)
                or record.get("prefix_row_count") != len(prefix)):
            raise ValueError("terminal_judgment_frozen_prefix_changed")
        snapshot = record.get("indicator_snapshot")
        if (type(snapshot) is not dict or snapshot.get("derived") is not True
                or snapshot.get("provenance") != "INDEPENDENT_INDICATOR_MATH"
                or snapshot.get("input_id") != frozen["id"]
                or snapshot.get("bar_date") != prefix[-1]["date"]
                or snapshot.get("prefix_rows_hash") != record["prefix_rows_hash"]
                or snapshot.get("prefix_row_count") != record["prefix_row_count"]
                or not _HASH.fullmatch(str(snapshot.get("source_sha256", "")))
                or type(snapshot.get("contract")) is not dict
                or type(snapshot.get("params")) is not dict
                or type(snapshot.get("values")) is not dict
                or record.get("research_only") is not True or record.get("order_authorized") is not False):
            raise ValueError("terminal_judgment_indicator_snapshot_invalid")
        receipt, config, summary = self._binding({key: record["binding"][key] for key in ("kind", "id")}, frozen)
        if receipt != record["binding"]:
            raise ValueError("terminal_judgment_binding_changed")
        if self._pending_event(identity):
            raise ValueError("terminal_judgment_event_commit_pending")
        events, head = self._events(identity, first_as_of=record["as_of"])
        return {**record, "judgment_id": identity, "record_hash": identity, "status": "RECORDED",
                "integrity_status": "PASS", "input_summary": self.terminal._input_view(frozen, rows=False),
                "prefix_summary": {"row_count": len(prefix), "rows_sha256": record["prefix_rows_hash"],
                                   "date_start": prefix[0]["date"], "date_end": prefix[-1]["date"]},
                "task_configuration": config, "run_summary": summary,
                "events": events, "head": head, "event_count": len(events),
                "new_economic_runs": 0}

    def _detail(self, identity):
        try:
            return self._strict_detail(identity)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            return {"id": identity, "judgment_id": identity, "record_hash": identity,
                    "status": "UNKNOWN", "integrity_status": "UNKNOWN", "reason": str(exc)[:300],
                    "automatic_retry": False, "events": [], "head": None, "event_count": 0,
                    "new_economic_runs": 0}

    @staticmethod
    def _summary(detail):
        if detail["status"] != "RECORDED":
            return detail
        return {key: _copy(detail[key]) for key in ("id", "judgment_id", "record_hash", "status",
                "integrity_status", "created_at", "recorded_at", "client_request_id", "input_id", "symbol", "bar", "binding",
                "direction", "as_of", "thesis", "trigger_condition", "invalidation_condition",
                "counter_evidence", "prefix_rows_hash", "prefix_row_count", "head", "event_count", "new_economic_runs")}

    def list(self):
        root = self.terminal._safe(self.workspace / "terminal-judgments")
        items, warnings = [], []
        for path in sorted(root.iterdir()) if root.exists() else ():
            if not path.is_dir() or not _HASH.fullmatch(path.name):
                warnings.append(path.name + ": invalid_judgment_entry")
                continue
            items.append(self._summary(self._detail(path.name)))
        intents_root = self.terminal._safe(self.workspace / "terminal-judgment-requests")
        for path in sorted(intents_root.glob("*.json")):
            try:
                intent = self.terminal._read(path, schema="hakimi-terminal-judgment-request-v1")
                if intent.get("action") == "CREATE":
                    identity = intent["record"]["id"]
                    if not (root / identity / "record.json").exists():
                        items.append({**self._summary(self._detail(identity)),
                                      "client_request_id": intent["client_request_id"]})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append(path.name + ": " + str(exc)[:120])
        items.sort(key=lambda row: (row.get("recorded_at", ""), row["id"]), reverse=True)
        return {"items": items, "warnings": warnings, "new_economic_runs": 0}

    def save(self, payload):
        _fields(payload, {"client_request_id", "input_id", "binding", "direction", "as_of", "thesis",
                          "trigger_condition", "invalidation_condition", "counter_evidence", "indicator_params"},
                {"client_request_id", "input_id", "binding", "direction", "as_of", "thesis",
                 "trigger_condition", "invalidation_condition", "counter_evidence"})
        request_id = _request_id(payload["client_request_id"])
        payload_hash = _digest(payload)
        intent_path = self._intent_path("CREATE", request_id)
        if intent_path.is_file():
            intent = self._read_intent(intent_path, "CREATE", payload_hash)
            record = intent["record"]
            self.terminal._write(self._root(record["id"]) / "record.json", record)
            return self._detail(record["id"])
        frozen = self._input(payload["input_id"])
        if payload["direction"] not in _DIRECTIONS:
            raise ValueError("terminal_judgment_direction_invalid")
        as_of = _day(payload["as_of"], "as_of")
        prefix = _prefix_rows(frozen, as_of)
        thesis = _text(payload["thesis"], "thesis", 2000)
        trigger = _text(payload["trigger_condition"], "trigger_condition", 1000)
        invalidation = _text(payload["invalidation_condition"], "invalidation_condition", 1000)
        counter = payload["counter_evidence"]
        if type(counter) is not list or len(counter) > 8:
            raise ValueError("terminal_judgment_counter_evidence_invalid")
        counter = [_text(item, "counter_evidence", 500) for item in counter]
        receipt, _, _ = self._binding(payload["binding"], frozen)
        snapshot = _indicator_snapshot(frozen, _params(payload.get("indicator_params")), prefix)
        prefix_hash = _digest(prefix)
        snapshot.update(prefix_rows_hash=prefix_hash, prefix_row_count=len(prefix))
        recorded_at = _now()
        record = _seal({"schema_version": "hakimi-terminal-judgment-v1", "recorded_at": recorded_at,
                        "created_at": recorded_at, "client_request_id": request_id,
                        "input_id": frozen["id"], "symbol": frozen["symbol"], "bar": frozen["bar"],
                        "input_digest": frozen["source_digest"], "prefix_rows_hash": prefix_hash,
                        "prefix_row_count": len(prefix), "binding": receipt,
                        "direction": payload["direction"], "as_of": as_of,
                        "as_of_is_user_declared": True,
                        "recording_relation": "RECORDED_AFTER_AS_OF" if as_of < recorded_at[:10]
                                              else "RECORDED_ON_AS_OF" if as_of == recorded_at[:10]
                                              else "AS_OF_AFTER_RECORDING_DATE",
                        "thesis": thesis,
                        "trigger_condition": trigger, "invalidation_condition": invalidation,
                        "counter_evidence": counter, "indicator_snapshot": snapshot,
                        "research_only": True, "order_authorized": False})
        intent = _seal({"schema_version": "hakimi-terminal-judgment-request-v1", "action": "CREATE",
                        "client_request_id": request_id, "payload_hash": payload_hash, "record": record})
        self.terminal._write(intent_path, intent)
        self.terminal._write(self._root(record["id"]) / "record.json", record)
        return self._detail(record["id"])

    def append(self, payload):
        _fields(payload, {"client_request_id", "judgment_id", "expected_head", "event_type", "as_of", "note"},
                {"client_request_id", "judgment_id", "expected_head", "event_type", "as_of", "note"})
        request_id = _request_id(payload["client_request_id"])
        identity = payload["judgment_id"]
        self._root(identity)
        if payload["expected_head"] is not None and (type(payload["expected_head"]) is not str
                                                     or not _HASH.fullmatch(payload["expected_head"])):
            raise ValueError("terminal_judgment_expected_head_invalid")
        if payload["event_type"] not in _EVENT_TYPES:
            raise ValueError("terminal_judgment_event_type_invalid")
        as_of = _day(payload["as_of"], "as_of")
        note = _text(payload["note"], "note", 2000)
        payload_hash = _digest(payload)
        intent_path = self._intent_path("APPEND", request_id)
        if intent_path.is_file():
            intent = self._read_intent(intent_path, "APPEND", payload_hash)
            event = intent["event"]
            event_path = self._root(identity) / "events" / f"{event['sequence']:06d}.json"
            self.terminal._write(event_path, event)
            return self._detail(identity)
        detail = self._strict_detail(identity)
        if detail["head"] != payload["expected_head"]:
            raise ValueError("terminal_judgment_head_changed_refresh_first")
        if as_of < detail["as_of"]:
            raise ValueError("terminal_judgment_event_precedes_as_of")
        if detail["events"] and as_of < detail["events"][-1]["as_of"]:
            raise ValueError("terminal_judgment_event_chronology_invalid")
        event = _seal({"schema_version": "hakimi-terminal-judgment-event-v1",
                       "judgment_id": identity, "sequence": detail["event_count"] + 1,
                       "previous_hash": detail["head"], "client_request_id": request_id,
                       "recorded_at": _now(), "as_of": as_of,
                       "as_of_is_user_declared": True, "event_type": payload["event_type"],
                       "note": note, "action_verification": "USER_REPORTED_UNVERIFIED"
                       if payload["event_type"] == "USER_ACTION" else None,
                       "order_authorized": False})
        intent = _seal({"schema_version": "hakimi-terminal-judgment-request-v1", "action": "APPEND",
                        "client_request_id": request_id, "payload_hash": payload_hash, "event": event})
        self.terminal._write(intent_path, intent)
        self.terminal._write(self._root(identity) / "events" / f"{event['sequence']:06d}.json", event)
        return self._detail(identity)

    def replay(self, identity):
        detail = self._detail(identity)
        if detail["status"] != "RECORDED":
            return {"available": False, "judgment_id": identity, "reason": detail["reason"]}
        try:
            kind = detail["binding"]["kind"]
            if kind == "terminal_run":
                run = self.terminal.read("terminal_runs", detail["binding"]["id"])
                chart = run["chart"]
                source = "JUDGMENT_FROZEN_RUN"
            elif kind == "core_run":
                chart = self.terminal._core_replay(detail["binding"]["id"])["chart"]
                source = "JUDGMENT_FROZEN_RUN"
            else:
                frozen = self._input(detail["input_id"])
                chart = {"rows": frozen["rows"], "trades": [], "meta": frozen["meta"],
                         "symbol": frozen["symbol"], "input_id": frozen["id"]}
                source = "JUDGMENT_FROZEN_INPUT"
            frozen = self._input(detail["input_id"])
            rows = _prefix_rows(frozen, detail["as_of"])
            if _digest(rows) != detail["prefix_rows_hash"] or len(rows) != detail["prefix_row_count"]:
                raise ValueError("terminal_judgment_replay_prefix_identity_changed")
            if source == "JUDGMENT_FROZEN_RUN":
                chart_prefix = [row for row in chart["rows"] if row["date"] <= detail["as_of"]]
                if len(chart_prefix) != len(rows) or any(
                    any(chart_row[key] != input_row[key] for key in ("date", "ts_ms", "open", "high", "low", "close", "volume"))
                    for chart_row, input_row in zip(chart_prefix, rows)
                ):
                    raise ValueError("terminal_judgment_replay_run_input_mismatch")
            trades = [trade for trade in chart.get("trades", [])
                      if type(trade) is dict and type(trade.get("date")) is str
                      and trade["date"] <= detail["as_of"]]
            return {"available": True, "judgment_id": identity, "record_hash": identity,
                    "as_of": detail["as_of"], "recorded_at": detail["recorded_at"],
                    "source": source, "rows": _copy(rows), "trades": _copy(trades),
                    "meta": _copy(chart["meta"]), "symbol": chart["symbol"],
                    "input_id": chart["input_id"], "terminal_input_id": detail["input_id"],
                    **({"run_id": chart["run_id"], "report_hash": chart["report_hash"],
                        "trades_are_backtest": True} if source == "JUDGMENT_FROZEN_RUN" else {}),
                    "new_economic_runs": 0}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"available": False, "judgment_id": identity, "record_hash": identity,
                    "reason": str(exc)[:300], "new_economic_runs": 0}

    def read(self, resource, identity=None):
        if resource == "terminal_judgment_replay":
            if identity is None:
                raise ValueError("terminal_judgment_id_required")
            return self.replay(identity)
        if identity is None:
            return self.list()
        self._root(identity)
        return self._detail(identity)
