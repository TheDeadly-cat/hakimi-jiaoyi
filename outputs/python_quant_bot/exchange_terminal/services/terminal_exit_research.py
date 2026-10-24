"""Frozen, separately identified exit-rule research over native BUY entries.

Registration seals an original completed run, its input, BUY cohort and rules.
Execution requires a separate explicit request and is never retried after a
durable start receipt. Historical reads verify identities without recalculation.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from . import causal_structure, exit_comparison_math, indicator_math


_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REQUEST = re.compile(r"[A-Za-z0-9_-]{8,120}\Z")
_SEGMENTS = ("TRAIN", "VALIDATION", "TEST")
_RULES = ("fixed_pct", "atr_trailing", "confirmed_structure")
LOADED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


def assert_loaded_source_current():
    if sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_SOURCE_SHA256:
        raise ValueError("terminal_exit_service_source_changed_restart_required")
    return LOADED_SOURCE_SHA256


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _copy(value):
    return json.loads(_bytes(value))


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _seal(body):
    return {**body, "id": _digest(body)}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _fields(value, allowed, required=None):
    required = allowed if required is None else required
    if type(value) is not dict or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError("terminal_exit_fields_invalid")


def _identity(value, label):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ValueError("terminal_exit_" + label + "_invalid")
    return value


def _request(value):
    if type(value) is not str or not _REQUEST.fullmatch(value):
        raise ValueError("terminal_exit_client_request_id_invalid")
    return value


def _day(value):
    if type(value) is not str:
        raise ValueError("terminal_exit_split_date_invalid")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("terminal_exit_split_date_invalid") from exc
    return value


def _numeric(value, key, low, high, *, integer=False, positive=False):
    if (type(value) is not int if integer else type(value) not in (int, float)) or not math.isfinite(value):
        raise ValueError("terminal_exit_spec_number_invalid:" + key)
    if not low <= value <= high or (positive and value == 0):
        raise ValueError("terminal_exit_spec_number_invalid:" + key)
    return value


def _spec(value, rows):
    names = {"split", "fixed_stop_pct", "atr_window", "atr_mult", "structure_left_window",
             "structure_right_window", "emergency_stop_pct", "max_hold_bars", "costs"}
    _fields(value, names)
    _fields(value["split"], _SEGMENTS)
    previous_end = None
    for name in _SEGMENTS:
        period = value["split"][name]
        _fields(period, {"start_date", "end_date"})
        start, end = _day(period["start_date"]), _day(period["end_date"])
        if (start > end or (previous_end is not None and start <= previous_end)
                or start < rows[0]["date"] or end > rows[-1]["date"]):
            raise ValueError("terminal_exit_split_coverage_invalid")
        if not any(start <= row["date"] <= end for row in rows):
            raise ValueError("terminal_exit_split_segment_empty:" + name)
        previous_end = end
    _numeric(value["fixed_stop_pct"], "fixed_stop_pct", 0, 100, positive=True)
    _numeric(value["atr_window"], "atr_window", 1, 1000, integer=True)
    _numeric(value["atr_mult"], "atr_mult", 0, 100, positive=True)
    _numeric(value["structure_left_window"], "structure_left_window", 1, 1000, integer=True)
    _numeric(value["structure_right_window"], "structure_right_window", 1, 1000, integer=True)
    _numeric(value["emergency_stop_pct"], "emergency_stop_pct", 0, 100, positive=True)
    _numeric(value["max_hold_bars"], "max_hold_bars", 1, 10000, integer=True)
    _fields(value["costs"], {"fee_rate", "slippage_bps"})
    _numeric(value["costs"]["fee_rate"], "fee_rate", 0, 1)
    _numeric(value["costs"]["slippage_bps"], "slippage_bps", 0, 10000)
    return _copy(value)


def _covered(cohort, spec):
    periods = spec["split"].values()
    if any(not any(period["start_date"] <= entry["date"] <= period["end_date"]
                   for period in periods) for entry in cohort):
        raise ValueError("terminal_exit_entry_outside_preregistered_split")


def _result_binding(result, experiment, rows):
    """Check saved input/path identity only; never resimulate historical exits."""
    sources = experiment["source_hashes"]
    expected_sources = {"exit_comparison_math": sources["exit_comparison_math.py"],
                        "causal_structure": sources["causal_structure.py"],
                        "indicator_math": sources["indicator_math.py"]}
    cohort = experiment["cohort"]
    if (type(result) is not dict or result.get("source_sha256") != expected_sources
            or result.get("spec") != experiment["spec"]
            or result.get("cohort_count") != len(cohort)
            or type(result.get("samples")) is not list
            or len(result["samples"]) != len(cohort)
            or type(result.get("exit_paths")) is not list
            or len(result["exit_paths"]) != len(_RULES) * len(cohort)
            or type(result.get("structure_marks")) is not list
            or result.get("portfolio_equity_curve") is not None):
        raise ValueError("terminal_exit_result_binding_invalid")
    row_index = {row["date"]: index for index, row in enumerate(rows)}
    expected_paths = []
    for ordinal, (entry, sample) in enumerate(zip(cohort, result["samples"]), 1):
        if type(sample) is not dict or entry["date"] not in row_index:
            raise ValueError("terminal_exit_sample_entry_binding_invalid")
        index = row_index[entry["date"]]
        segment = next((name for name in _SEGMENTS
                        if experiment["spec"]["split"][name]["start_date"] <= entry["date"]
                        <= experiment["spec"]["split"][name]["end_date"]), None)
        sample_id = f"BUY-{ordinal:04d}-{index}"
        expected_entry = {"sample_id": sample_id, "index": index, "date": entry["date"],
                          "segment": segment, **entry}
        outcomes = sample.get("outcomes")
        if (segment is None or sample.get("sample_id") != sample_id or sample.get("segment") != segment
                or sample.get("entry") != expected_entry or type(outcomes) is not dict
                or set(outcomes) != set(_RULES)):
            raise ValueError("terminal_exit_sample_entry_binding_invalid")
        for rule in _RULES:
            outcome = outcomes[rule]
            required = {"status", "reason", "exit", "threshold_trace", "net_return_pct",
                        "fees", "mae_pct", "mfe_pct", "duration_bars", "censor"}
            if (type(outcome) is not dict or not required <= set(outcome)
                    or outcome["status"] not in {"EXITED", "CENSORED", "UNAVAILABLE"}
                    or type(outcome["threshold_trace"]) is not list):
                raise ValueError("terminal_exit_outcome_contract_invalid")
            expected_paths.append({"sample_id": sample_id, "entry": expected_entry,
                                   "segment": segment, "rule": rule,
                                   "status": outcome["status"], "reason": outcome["reason"],
                                   "threshold_trace": outcome["threshold_trace"],
                                   "exit": outcome["exit"], "censor": outcome["censor"]})
    if result["exit_paths"] != expected_paths:
        raise ValueError("terminal_exit_path_sample_binding_invalid")


class TerminalExitResearchService:
    def __init__(self, terminal):
        self.terminal = terminal
        self.workspace = terminal.workspace

    def _experiment_root(self, identity):
        return self.terminal._safe(self.workspace / "terminal-exit-experiments" /
                                   _identity(identity, "experiment_id"))

    def _run_root(self, identity):
        return self.terminal._safe(self.workspace / "terminal-exit-runs" /
                                   _identity(identity, "run_id"))

    def _intent_path(self, action, request_id):
        token = sha256((action + ":" + _request(request_id)).encode("utf-8")).hexdigest()
        return self.terminal._safe(self.workspace / "terminal-exit-requests" / (token + ".json"))

    def _intent(self, path, action, payload_hash):
        receipt = self.terminal._read(path, schema="hakimi-terminal-exit-request-v1")
        if receipt.get("action") != action or receipt.get("payload_hash") != payload_hash:
            raise ValueError("terminal_exit_client_request_id_conflict")
        return receipt

    def _source_hashes(self):
        return {"causal_structure.py": causal_structure.assert_loaded_source_current(),
                "exit_comparison_math.py": exit_comparison_math.assert_loaded_source_current(),
                "indicator_math.py": indicator_math.assert_loaded_source_current(),
                "terminal_exit_research.py": assert_loaded_source_current()}

    def _original(self, identity):
        _identity(identity, "original_run_id")
        report = self.terminal.read("terminal_runs", identity)
        if (report.get("id") != identity or report.get("schema_version") != "hakimi-terminal-run-v1"
                or report.get("status") != "COMPLETED" or report.get("engine_id", "").startswith("terminal.") is not True
                or report.get("configuration", {}).get("direction_mode") != "LONG_ONLY"
                or report.get("result", {}).get("ok") is not True):
            raise ValueError("terminal_exit_original_native_completed_run_required")
        configuration = report["configuration"]
        frozen = self.terminal._input(configuration["input_id"])
        if frozen["quality"].get("status") != "REVIEW" or not frozen["rows"]:
            raise ValueError("terminal_exit_original_input_blocked")
        result = report["result"]
        trades = result.get("trades")
        if (type(trades) is not list or type(result.get("order_event_count")) is not int
                or result["order_event_count"] != len(trades)):
            raise ValueError("terminal_exit_original_history_incomplete")
        sessions = {row["date"] for row in frozen["rows"]}
        cohort = []
        for trade in trades:
            if type(trade) is not dict or trade.get("side") not in {"BUY", "SELL"}:
                raise ValueError("terminal_exit_original_non_buy_add_or_unknown_trade")
            if trade["side"] != "BUY":
                continue
            if (trade.get("date") not in sessions or trade.get("fill_basis") != "NEXT_BAR_OPEN"
                    or any(type(trade.get(key)) not in (int, float) or not math.isfinite(trade[key])
                           or trade[key] <= 0 for key in ("price", "quantity"))
                    or type(trade.get("fee")) not in (int, float) or not math.isfinite(trade["fee"])
                    or trade["fee"] < 0):
                raise ValueError("terminal_exit_original_buy_invalid")
            signal_date = trade.get("signal_date", "UNKNOWN")
            if type(signal_date) is not str:
                raise ValueError("terminal_exit_original_signal_date_invalid")
            cohort.append({**{key: _copy(trade[key]) for key in
                              ("date", "side", "price", "quantity", "fee", "fill_basis")},
                           "signal_date": signal_date})
        if not cohort:
            raise ValueError("terminal_exit_original_buy_cohort_empty")
        return report, frozen, cohort

    def _strict_experiment(self, identity):
        record = self.terminal._read(self._experiment_root(identity) / "experiment.json",
                                     schema="hakimi-terminal-exit-experiment-v1")
        if record["id"] != identity or record.get("research_only") is not True or record.get("order_authorized") is not False:
            raise ValueError("terminal_exit_experiment_identity_invalid")
        report, frozen, cohort = self._original(record["original_run_id"])
        if (record.get("input_id") != frozen["id"] or record.get("input_digest") != frozen["source_digest"]
                or record.get("input_rows_hash") != _digest(frozen["rows"])
                or record.get("original_result_hash") != _digest(report["result"])
                or record.get("original_engine_id") != report["engine_id"]
                or record.get("original_strategy_id") != report["strategy_id"]
                or record.get("original_task_id") != report["task_id"]
                or record.get("original_report_hash") != report["id"]
                or record.get("cohort") != cohort or record.get("cohort_hash") != _digest(cohort)
                or record.get("cohort_count") != len(cohort)
                or not all(_HASH.fullmatch(str(v)) for v in record.get("source_hashes", {}).values())
                or set(record.get("source_hashes", {})) not in (
                    {"causal_structure.py", "exit_comparison_math.py", "indicator_math.py"},
                    {"causal_structure.py", "exit_comparison_math.py", "indicator_math.py",
                     "terminal_exit_research.py"})):
            raise ValueError("terminal_exit_experiment_binding_changed")
        _spec(record["spec"], frozen["rows"])
        _covered(cohort, record["spec"])
        return record, frozen

    def _experiment_detail(self, identity):
        try:
            record, frozen = self._strict_experiment(identity)
            return {**record, "experiment_id": identity, "record_hash": identity,
                    "status": "REGISTERED", "integrity_status": "PASS",
                    "run_compatibility": "REQUIRES_NEW_REGISTRATION" if "terminal_exit_research.py"
                                         not in record["source_hashes"] else "REGISTERED_SOURCE_VERSION",
                    "requires_revision": "terminal_exit_research.py" not in record["source_hashes"],
                    "run_blocker": "terminal_exit_service_source_not_bound_register_new_experiment"
                                   if "terminal_exit_research.py" not in record["source_hashes"] else None,
                    "input_summary": self.terminal._input_view(frozen, rows=False),
                    "new_economic_runs": 0, "automatic_retry": False}
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            return {"id": identity, "experiment_id": identity, "status": "UNKNOWN",
                    "integrity_status": "UNKNOWN", "reason": str(exc)[:300],
                    "automatic_retry": False, "new_economic_runs": 0}

    def register(self, payload):
        _fields(payload, {"client_request_id", "original_run_id", "spec"})
        request_id = _request(payload["client_request_id"])
        payload_hash = _digest(payload)
        intent_path = self._intent_path("REGISTER", request_id)
        if intent_path.is_file():
            receipt = self._intent(intent_path, "REGISTER", payload_hash)
            record = receipt["experiment"]
            self.terminal._write(self._experiment_root(record["id"]) / "experiment.json", record)
            return self._experiment_detail(record["id"])
        report, frozen, cohort = self._original(payload["original_run_id"])
        self.terminal._strategy(report["strategy_id"], new_work=True)
        spec = _spec(payload["spec"], frozen["rows"])
        _covered(cohort, spec)
        sources = self._source_hashes()
        record = _seal({"schema_version": "hakimi-terminal-exit-experiment-v1",
                        "recorded_at": _now(), "client_request_id": request_id,
                        "original_run_id": report["id"], "original_report_hash": report["id"],
                        "original_result_hash": _digest(report["result"]),
                        "original_task_id": report["task_id"], "original_engine_id": report["engine_id"],
                        "original_strategy_id": report["strategy_id"],
                        "input_id": frozen["id"], "input_digest": frozen["source_digest"],
                        "input_rows_hash": _digest(frozen["rows"]), "symbol": frozen["symbol"],
                        "bar": frozen["bar"], "cohort": cohort, "cohort_hash": _digest(cohort),
                        "cohort_count": len(cohort), "source_hashes": sources, "spec": spec,
                        "research_only": True, "order_authorized": False,
                        "interpretation": "同一原生 BUY 入场样本的独立出场规则研究；不是账户收益曲线。"})
        receipt = _seal({"schema_version": "hakimi-terminal-exit-request-v1", "action": "REGISTER",
                         "client_request_id": request_id, "payload_hash": payload_hash,
                         "experiment": record})
        if self._source_hashes() != sources:
            raise ValueError("terminal_exit_source_changed_during_registration")
        self.terminal._write(intent_path, receipt)
        self.terminal._write(self._experiment_root(record["id"]) / "experiment.json", record)
        return self._experiment_detail(record["id"])

    def _exit_run_id(self, experiment_id):
        return _digest({"kind": "terminal-exit-run-v1", "experiment_id": experiment_id})

    def _strict_run(self, identity):
        root = self._run_root(identity)
        started = self.terminal._read(root / "started.json", schema="hakimi-terminal-exit-start-v1")
        if started.get("exit_run_id") != identity or self._exit_run_id(started["experiment_id"]) != identity:
            raise ValueError("terminal_exit_start_identity_invalid")
        experiment, frozen = self._strict_experiment(started["experiment_id"])
        if (started["original_run_id"] != experiment["original_run_id"]
                or started["input_id"] != frozen["id"]
                or started["source_hashes"] != experiment["source_hashes"]):
            raise ValueError("terminal_exit_start_binding_changed")
        report = self.terminal._read(root / "report.json", schema="hakimi-terminal-exit-run-v1")
        if (report["exit_run_id"] != identity
                or report["experiment_id"] != experiment["id"]
                or report["original_run_id"] != experiment["original_run_id"]
                or report["started_hash"] != started["id"]
                or report["started_at"] != started["started_at"]
                or report["client_request_id"] != started["client_request_id"]
                or report["source_hashes"] != experiment["source_hashes"]
                or report.get("automatic_retry") is not False
                or report.get("order_authorized") is not False):
            raise ValueError("terminal_exit_report_binding_changed")
        if report["status"] == "COMPLETED":
            if type(report["result"]) is not dict or report.get("result_hash") != _digest(report["result"]):
                raise ValueError("terminal_exit_result_changed")
            _result_binding(report["result"], experiment, frozen["rows"])
        elif report["status"] != "UNKNOWN" or report.get("result") is not None:
            raise ValueError("terminal_exit_status_invalid")
        return report, experiment, frozen

    def _run_detail(self, identity):
        try:
            report, experiment, _ = self._strict_run(identity)
            aliases = ({key: _copy(report["result"][key]) for key in
                        ("summaries", "segment_stats", "structure_marks", "exit_paths")
                        if key in report["result"]} if report["status"] == "COMPLETED" else {})
            return {**report, **aliases, "id": identity, "exit_run_id": identity,
                    "record_hash": report["id"], "report_hash": report["id"],
                    "integrity_status": "PASS", "cohort_count": experiment["cohort_count"],
                    "new_economic_runs": 0}
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            pending = {}
            try:
                started = self.terminal._read(self._run_root(identity) / "started.json",
                                              schema="hakimi-terminal-exit-start-v1")
                if started.get("exit_run_id") == identity:
                    pending = {"client_request_id": started["client_request_id"],
                               "experiment_id": started["experiment_id"],
                               "original_run_id": started["original_run_id"],
                               "started_at": started["started_at"]}
            except (OSError, ValueError, KeyError, TypeError):
                pass
            return {"id": identity, "exit_run_id": identity, **pending, "status": "UNKNOWN",
                    "integrity_status": "UNKNOWN", "reason": str(exc)[:300],
                    "automatic_retry": False, "new_economic_runs": 0}

    def run(self, payload):
        _fields(payload, {"client_request_id", "experiment_id"})
        request_id = _request(payload["client_request_id"])
        experiment_id = _identity(payload["experiment_id"], "experiment_id")
        payload_hash = _digest(payload)
        intent_path = self._intent_path("RUN", request_id)
        if intent_path.is_file():
            receipt = self._intent(intent_path, "RUN", payload_hash)
            return self._run_detail(receipt["exit_run_id"])
        experiment, frozen = self._strict_experiment(experiment_id)
        identity = self._exit_run_id(experiment_id)
        root = self._run_root(identity)
        if (root / "started.json").exists() or (root / "report.json").exists():
            return {**self._run_detail(identity), "reused": True}
        self.terminal._strategy(experiment["original_strategy_id"], new_work=True)
        sources = self._source_hashes()
        if sources != experiment["source_hashes"]:
            raise ValueError("terminal_exit_source_changed_register_new_experiment")
        receipt = _seal({"schema_version": "hakimi-terminal-exit-request-v1", "action": "RUN",
                         "client_request_id": request_id, "payload_hash": payload_hash,
                         "experiment_id": experiment_id, "exit_run_id": identity})
        self.terminal._write(intent_path, receipt)
        started = _seal({"schema_version": "hakimi-terminal-exit-start-v1",
                         "exit_run_id": identity, "experiment_id": experiment_id,
                         "original_run_id": experiment["original_run_id"], "input_id": frozen["id"],
                         "client_request_id": request_id, "source_hashes": sources,
                         "started_at": _now(), "automatic_retry": False})
        self.terminal._write(root / "started.json", started)
        try:
            result = _copy(exit_comparison_math.compare_exit_rules(_copy(frozen["rows"]),
                _copy(experiment["cohort"]), _copy(experiment["spec"])))
            _result_binding(result, experiment, frozen["rows"])
            if self._source_hashes() != sources:
                raise ValueError("terminal_exit_source_changed_during_run")
            status, error = "COMPLETED", None
        except Exception as exc:
            result, status, error = None, "UNKNOWN", str(exc)[:2000]
        report = _seal({"schema_version": "hakimi-terminal-exit-run-v1",
                        "exit_run_id": identity, "experiment_id": experiment_id,
                        "original_run_id": experiment["original_run_id"],
                        "started_hash": started["id"], "started_at": started["started_at"],
                        "client_request_id": request_id, "source_hashes": sources,
                        "status": status, "error": error, "result": result,
                        "result_hash": _digest(result) if result is not None else None,
                        "automatic_retry": False, "research_only": True, "order_authorized": False,
                        "interpretation": "同一入场样本的独立出场路径，不能当账户权益或执行许可。"})
        self.terminal._write(root / "report.json", report)
        return self._run_detail(identity)

    def _list(self, kind):
        root = self.terminal._safe(self.workspace / ("terminal-exit-experiments" if kind == "experiment"
                                                   else "terminal-exit-runs"))
        items, warnings = [], []
        for path in sorted(root.iterdir()) if root.exists() else ():
            if not path.is_dir() or not _HASH.fullmatch(path.name):
                warnings.append(path.name + ": invalid_exit_entry")
                continue
            detail = self._experiment_detail(path.name) if kind == "experiment" else self._run_detail(path.name)
            if kind == "experiment" and detail["status"] == "REGISTERED":
                detail = {key: _copy(detail[key]) for key in ("id", "experiment_id", "record_hash",
                    "status", "integrity_status", "recorded_at", "client_request_id", "original_run_id",
                    "input_id", "symbol", "bar", "cohort_count", "cohort_hash", "spec", "source_hashes",
                    "run_compatibility", "requires_revision", "run_blocker")}
            if kind == "run" and detail["status"] == "COMPLETED":
                detail = {key: _copy(detail[key]) for key in ("id", "exit_run_id", "record_hash",
                    "status", "integrity_status", "started_at", "client_request_id", "experiment_id",
                    "original_run_id", "cohort_count", "result_hash")}
            items.append(detail)
        # A durable request can precede the separate record/start publication.
        # Show the receipt as UNKNOWN without completing or repeating its work.
        requests = self.terminal._safe(self.workspace / "terminal-exit-requests")
        known = {item["id"] for item in items}
        for path in sorted(requests.glob("*.json")):
            try:
                receipt = self.terminal._read(path, schema="hakimi-terminal-exit-request-v1")
                action = receipt.get("action")
                if action not in {"REGISTER", "RUN"}:
                    raise ValueError("terminal_exit_request_action_invalid")
                request_id = _request(receipt["client_request_id"])
                if path.name != self._intent_path(action, request_id).name:
                    raise ValueError("terminal_exit_request_path_invalid")
                if action == "REGISTER" and kind == "experiment":
                    record = receipt["experiment"]
                    identity = _identity(record["id"], "experiment_id")
                    if identity not in known and not (root / identity / "experiment.json").exists():
                        items.append({"id": identity, "experiment_id": identity,
                                      "client_request_id": request_id,
                                      "original_run_id": record["original_run_id"],
                                      "input_id": record["input_id"],
                                      "recorded_at": record["recorded_at"],
                                      "status": "UNKNOWN", "integrity_status": "UNKNOWN",
                                      "reason": "terminal_exit_register_commit_pending",
                                      "automatic_retry": False, "new_economic_runs": 0})
                        known.add(identity)
                elif action == "RUN" and kind == "run":
                    identity = _identity(receipt["exit_run_id"], "run_id")
                    if identity not in known and not (root / identity / "started.json").exists():
                        items.append({"id": identity, "exit_run_id": identity,
                                      "client_request_id": request_id,
                                      "experiment_id": receipt["experiment_id"],
                                      "status": "UNKNOWN", "integrity_status": "UNKNOWN",
                                      "reason": "terminal_exit_run_intent_without_start",
                                      "automatic_retry": False, "new_economic_runs": 0})
                        known.add(identity)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append(path.name + ": " + str(exc)[:120])
        items.sort(key=lambda value: (value.get("recorded_at", value.get("started_at", "")), value["id"]), reverse=True)
        return {"items": items, "warnings": warnings, "new_economic_runs": 0}

    def replay(self, identity):
        detail = self._run_detail(identity)
        if detail["status"] != "COMPLETED":
            return {"available": False, "exit_run_id": identity, "reason": detail.get("reason") or detail.get("error")
                    or "terminal_exit_run_not_completed", "new_economic_runs": 0}
        try:
            _, experiment, frozen = self._strict_run(identity)
            result = detail["result"]
            return {"available": True, "source": "EXIT_RESEARCH_FROZEN",
                    "exit_run_id": identity, "record_hash": detail["record_hash"],
                    "experiment_id": experiment["id"], "original_run_id": experiment["original_run_id"],
                    "input_id": frozen["id"], "meta": _copy(frozen["meta"]), "symbol": frozen["symbol"],
                    "rows": _copy(frozen["rows"]), "trades": [],
                    "structure_marks": _copy(result.get("structure_marks", [])),
                    "exit_paths": _copy(result.get("exit_paths", [])),
                    "result_status": "COMPLETED", "research_only": True,
                    "order_authorized": False,
                    "new_economic_runs": 0}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"available": False, "exit_run_id": identity, "reason": str(exc)[:300],
                    "new_economic_runs": 0}

    def structure_replay(self, identity):
        try:
            frozen = self.terminal._input(_identity(identity, "input_id"))
            if frozen["quality"].get("status") != "REVIEW" or not frozen["rows"]:
                raise ValueError("terminal_structure_frozen_input_blocked")
            source_sha = causal_structure.assert_loaded_source_current()
            structure = causal_structure.project_causal_structure(_copy(frozen["rows"]))
            if causal_structure.assert_loaded_source_current() != source_sha:
                raise ValueError("terminal_structure_source_changed_during_read")
            marks = ([{"type": "PIVOT", **pivot} for pivot in structure["pivots"]] +
                     [{"type": "BREAKOUT", **breakout, "confirmed_at_index": breakout["index"],
                       "confirmed_at_date": breakout["date"], "price": breakout["close"]}
                      for breakout in structure["breakouts"]])
            marks.sort(key=lambda mark: (mark["confirmed_at_index"], mark["type"],
                                         mark.get("pivot_index", -1)))
            body = {"source": "STRUCTURE_FROZEN", "input_id": frozen["id"],
                    "input_rows_hash": _digest(frozen["rows"]), "meta": _copy(frozen["meta"]),
                    "symbol": frozen["symbol"], "rows": _copy(frozen["rows"]), "trades": [],
                    "structure_marks": _copy(marks), "structure": _copy(structure), "derived": True,
                    "source_sha256": source_sha, "params": {"left_window": 3, "right_window": 3},
                    "research_only": True, "order_authorized": False}
            return {**body, "record_hash": _digest(body), "available": True,
                    "new_economic_runs": 0}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"available": False, "input_id": identity, "reason": str(exc)[:300],
                    "new_economic_runs": 0}

    def read(self, resource, identity=None):
        if resource == "terminal_structure_replay":
            if identity is None:
                raise ValueError("terminal_structure_input_id_required")
            return self.structure_replay(identity)
        if resource == "terminal_exit_replay":
            if identity is None:
                raise ValueError("terminal_exit_run_id_required")
            return self.replay(identity)
        if resource == "terminal_exit_experiments":
            return self._list("experiment") if identity is None else self._experiment_detail(_identity(identity, "experiment_id"))
        if resource == "terminal_exit_runs":
            return self._list("run") if identity is None else self._run_detail(_identity(identity, "run_id"))
        raise ValueError("terminal_exit_resource_invalid")
