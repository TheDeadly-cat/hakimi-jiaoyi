"""Read-only explanation of one verified accepted-core saved strategy.

This never converts an accepted report to the native engine or reruns a study.
The original guarded DualMA and SMA implement the rule; a separate explanation
is checked against their unrounded action. These checks cover that loaded rule
and its immediate bindings, not arbitrary hostile code in the same process.
"""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
import marshal
import math
from pathlib import Path
import re
import sys
from types import CodeType, FunctionType

from .terminal_saved_results import verified_saved_result


CONTEXT_SCHEMA = "hakimi-accepted-rule-context-v1"
FACTORS_SCHEMA = "hakimi-accepted-factors-v1"
ROW_SCHEMA = "hakimi-accepted-strategy-diagnostic-v1"
ENGINE_ID, STRATEGY_ID = "research.accepted-equity", "price.dual_ma@1"
PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}
SOURCE_SCOPE = "PINNED_PACKAGE_DISK_AND_LOADED_RULE_SMA_BINDINGS"
PARAMETER_UNITS = {"fast_window": "sessions", "slow_window": "sessions", "position_pct": "ratio",
                   "stop_loss_pct": "ratio", "take_profit_pct": "ratio", "fixed_take_profit_policy": "enum"}
HASH = re.compile(r"[a-f0-9]{64}\Z")
REFERENCE = re.compile(r"[a-f0-9]{24}\Z")
_ADAPTER_LOADED_SHA = sha256(Path(__file__).read_bytes()).hexdigest()


def _require(value, reason):
    if not value:
        raise ValueError("accepted_factor_" + reason)


def _bytes(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("ascii")


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _hash(value):
    return type(value) is str and HASH.fullmatch(value) is not None


def _reference(value):
    _require(type(value) is dict and set(value) == {"kind", "id"} and value["kind"] == "core_run"
             and type(value["id"]) is str and REFERENCE.fullmatch(value["id"]), "core_saved_reference_required")
    return deepcopy(value)


def _normal_code(value, filename):
    return value.replace(co_filename=filename, co_consts=tuple(
        _normal_code(item, filename) if type(item) is CodeType else item for item in value.co_consts))


def _code_by_name(value, name):
    if value.co_qualname == name:
        return value
    for item in value.co_consts:
        if type(item) is CodeType:
            found = _code_by_name(item, name)
            if found is not None:
                return found
    return None


def _rule_runtime(recorded_source):
    """Pin disk package plus the actual rule/SMA/wrapper and immediate helpers."""
    from .quant_workspace import ACCEPTED_SOURCE_SHA256, _load_kernel
    _require(recorded_source == ACCEPTED_SOURCE_SHA256, "recorded_source_changed")
    package = sys.modules.get("hakimi_terminal_research")
    location = getattr(package, "__file__", None)
    _require(type(location) is str, "accepted_kernel_not_loaded")
    # The loaded installed package is the anchor, not a development checkout
    # and never a client-selected path. The original loader rechecks its pin
    # and every already-loaded module's ownership of this exact directory.
    kernel = _load_kernel(Path(location).resolve().parent.parent)
    modules = {name: importlib.import_module("hakimi_terminal_research." + name) for name in
               ("strategies.templates", "strategies.base", "indicators", "models", "equity_dataset")}
    template, base, indicators, models = (modules[name] for name in
                                        ("strategies.templates", "strategies.base", "indicators", "models"))
    strategy = template.DualMovingAverageStrategy
    guarded = strategy.generate_signal
    original = getattr(guarded, "__wrapped__", None)
    _require(type(guarded) is FunctionType and type(original) is FunctionType
             and getattr(guarded, "_research_strategy_guarded", False) is True, "loaded_rule_guard_changed")
    closure = dict(zip(guarded.__code__.co_freevars, guarded.__closure__ or ()))
    _require("original" in closure and closure["original"].cell_contents is original,
             "loaded_rule_closure_changed")
    _require(strategy.__bases__ == (base.StrategyBase,) and template.sma is indicators.sma
             and template.pd is indicators.pd and base.pd is indicators.pd
             and template.Signal is base.Signal is models.Signal
             and template.Portfolio is base.Portfolio is models.Portfolio, "loaded_rule_binding_changed")
    checks = [
        ("strategies.templates", "DualMovingAverageStrategy.generate_signal", original),
        ("strategies.base", "StrategyBase.__init_subclass__.<locals>.guarded", guarded),
        ("strategies.base", "StrategyBase.__init__", base.StrategyBase.__init__),
        ("strategies.base", "StrategyBase.get", base.StrategyBase.get),
        ("strategies.base", "StrategyBase.params", base.StrategyBase.params.fget),
        ("indicators", "sma", indicators.sma),
        ("models", "Portfolio.__post_init__", models.Portfolio.__post_init__),
        ("models", "Signal.__post_init__", models.Signal.__post_init__),
        ("models", "Signal.buy", models.Signal.buy.__func__),
        ("models", "Signal.exit", models.Signal.exit.__func__),
        ("models", "Signal.hold", models.Signal.hold.__func__),
        ("equity_dataset", "EquitySnapshot.frame", modules["equity_dataset"].EquitySnapshot.frame),
    ]
    compiled, codes = {}, {}
    for module_name, qualified_name, function in checks:
        relative = module_name.replace(".", "/") + ".py"
        path = kernel.root / relative
        _require(Path(modules[module_name].__file__).resolve() == path.resolve()
                 and type(function) is FunctionType and function.__globals__ is modules[module_name].__dict__,
                 "loaded_rule_location_changed")
        if relative not in compiled:
            compiled[relative] = compile(path.read_bytes(), str(path), "exec", dont_inherit=True,
                                         optimize=sys.flags.optimize)
        expected = _code_by_name(compiled[relative], qualified_name)
        _require(expected is not None and marshal.dumps(_normal_code(function.__code__, relative)) ==
                 marshal.dumps(_normal_code(expected, relative)), "loaded_rule_code_changed")
        codes[relative + ":" + qualified_name] = sha256(marshal.dumps(_normal_code(expected, relative))).hexdigest()
    identity = dict(recorded_sha256=recorded_source, accepted_sha256=ACCEPTED_SOURCE_SHA256,
        disk_sha256=ACCEPTED_SOURCE_SHA256, loaded_rule_verified=True,
        loaded_rule_code_sha256=_digest(codes), verification_scope=SOURCE_SCOPE)
    return identity, strategy, indicators, models, modules["equity_dataset"].EquitySnapshot


def _saved_context(service, reference):
    reference = _reference(reference)
    envelope = verified_saved_result(service, reference)
    manifest, report, snapshot = envelope["manifest"], envelope["report"], envelope["snapshot"]
    _require(envelope["verification_status"] == "VERIFIED_RECORD" and envelope["id"] == reference["id"],
             "verified_original_required")
    task, spec = manifest["task"], report["spec"]
    _require(task["strategy"] == STRATEGY_ID and spec["strategy"]["name"] == "dual_ma", "strategy_unsupported")
    recorded_source = manifest["runtime"]["source_identity"]["content_sha256"]
    source, _, _, _, _ = _rule_runtime(recorded_source)
    params = deepcopy(spec["strategy"]["params"])
    _require(type(params) is dict and not set(params) - set(PARAMETER_UNITS), "parameters_unsupported")
    _require(report["spec"] == task["experiment"] and report["dataset"]["snapshot_id"] == snapshot["snapshot_id"],
             "saved_spec_or_snapshot_changed")
    dates = [session["date"] for session in snapshot["sessions"]]
    cutoff, start = spec["score_end_session"], spec["score_start_session"]
    _require(cutoff in dates and start in dates and dates.index(start) <= dates.index(cutoff), "score_window_invalid")
    security = snapshot["security"]
    body = dict(schema_version=CONTEXT_SCHEMA, reference=reference, read_only=True, new_economic_runs=0,
        permissions=dict(PERMISSIONS), engine_id=ENGINE_ID, strategy_id=STRATEGY_ID,
        strategy_params=params, parameter_units={key: PARAMETER_UNITS[key] for key in params},
        execution_risk=deepcopy(spec["risk"]), risk_units="FRACTION_RATIOS",
        costs={key: spec[key] for key in ("fee_rate", "slippage_pct") if key in spec}, cost_units="FRACTION_RATIOS",
        initial_cash=spec["initial_cash"], task_id=manifest["task_id"],
        task_version=task.get("management", {}).get("revision") or manifest["task_id"],
        input_id=snapshot["snapshot_id"], report_id=manifest["run_id"], report_hash=report["report_hash"],
        spec_hash=report["spec_hash"], source_hash=recorded_source,
        source_digest=manifest["input_sha256"]["snapshot.json"], input_data_hash=snapshot["data_hash"],
        symbol=security["symbol"], security_id=security["security_id"], currency=security["currency"],
        data_start=dates[0], snapshot_end=dates[-1], score_start_session=start, cutoff_session=cutoff,
        quantity_policy=spec["quantity_policy"], execution_model=report["result"]["execution_model"],
        accepted_source_identity=source, adapter_source_sha256=_ADAPTER_LOADED_SHA,
        explanation_scope="NEW_READ_ONLY_SCORE_END_CLOSE_EXPLANATION_NOT_RETAINED_REPORT_FACTORS")
    _require(all(_hash(body[key]) for key in ("task_id", "input_id", "report_id", "report_hash", "spec_hash",
        "source_hash", "source_digest", "input_data_hash")), "saved_identity_invalid")
    body["fingerprint"] = _digest(dict(adapter="accepted-dual-ma-factors-v1", adapter_source_sha256=_ADAPTER_LOADED_SHA, source=source,
        strategy_id=STRATEGY_ID, strategy_identity=task["strategy_identity"], strategy_params=params))
    body["context_id"] = _digest(body)
    return body, snapshot


def accepted_rule_context(service, reference):
    """Verify original saved context, without the HTTP derived-computation guard."""
    context, _ = _saved_context(service, reference)
    return context


def _factor(key, label, value, operator, threshold, role, position, cutoff, *, unit="price"):
    applies = role == "WARMUP" or (role == "EXIT") == position
    passed = None
    if value is not None and threshold is not None:
        _require(type(value) in (int, float) and type(threshold) in (int, float)
                 and math.isfinite(value) and math.isfinite(threshold), "nonfinite_factor")
        passed = {">=": value >= threshold, "<=": value <= threshold,
                  ">": value > threshold, "<": value < threshold}[operator]
    return dict(key=key, label=label, value=value, operator=operator, threshold=threshold,
        passed=passed, unit=unit, role=role, applies_to_position=applies, cutoff_session=cutoff)


def _explain_prefix(frame, params, has_position, cutoff, *, strategy_class, indicators, models):
    """Pure explanation/parity seam; no report identity is invented here."""
    count = len(frame)
    strategy = strategy_class(deepcopy(params))
    # These are deliberately only the caller's diagnostic holding scenarios.
    # No account balance or actual position is read or inferred.
    portfolio = models.Portfolio(cash=0.0, position_qty=1.0 if has_position else 0.0)
    actual = strategy.generate_signal(frame, portfolio)
    fast, slow = int(strategy.get("fast_window", 20)), int(strategy.get("slow_window", 60))
    ready = count >= slow + 2
    previous_fast = previous_slow = current_fast = current_slow = None
    if ready:
        fast_line, slow_line = indicators.sma(frame["close"], fast), indicators.sma(frame["close"], slow)
        previous_fast, current_fast = float(fast_line.iloc[-2]), float(fast_line.iloc[-1])
        previous_slow, current_slow = float(slow_line.iloc[-2]), float(slow_line.iloc[-1])
    factors = [
        _factor("warmup_sessions", "已有完整历史日数", count, ">=", slow + 2, "WARMUP", has_position, cutoff, unit="sessions"),
        _factor("entry_previous_not_above", "上日快均线不高于慢均线", previous_fast, "<=", previous_slow, "ENTRY", has_position, cutoff),
        _factor("entry_current_above", "当日快均线高于慢均线", current_fast, ">", current_slow, "ENTRY", has_position, cutoff),
        _factor("exit_previous_not_below", "上日快均线不低于慢均线", previous_fast, ">=", previous_slow, "EXIT", has_position, cutoff),
        _factor("exit_current_below", "当日快均线低于慢均线", current_fast, "<", current_slow, "EXIT", has_position, cutoff),
    ]
    expected = ("EXIT" if has_position else "BUY") if all(
        factor["passed"] is True for factor in factors if factor["applies_to_position"]) else "HOLD"
    _require(actual.action.value == expected and actual.reason in {
        "fast MA crossed above slow MA", "fast MA crossed below slow MA", "no MA crossover", "not enough data"},
        "original_signal_factor_mismatch")
    return {"position_context": {"has_position": has_position},
        "status": "READY" if ready else "INSUFFICIENT_HISTORY", "signal": {"action": actual.action.value, "reason": actual.reason},
        "decision_matches_factors": True, "factors": factors,
        "effective_windows": {"fast_window": fast, "slow_window": slow, "warmup_sessions": slow + 2},
        "freshness": {"context": "SAVED_HISTORICAL_INPUT", "cutoff_session": cutoff, "live_quote_verified": False}}


def _diagnose(context, snapshot, has_position):
    """Evaluate exactly one original rule over the saved prefix, no backtest."""
    source, strategy_class, indicators, models, snapshot_class = _rule_runtime(context["source_hash"])
    _require(source == context["accepted_source_identity"], "source_changed_during_read")
    dates = [row["date"] for row in snapshot["sessions"]]
    count = dates.index(context["cutoff_session"]) + 1
    frame = snapshot_class(deepcopy(snapshot)).frame().iloc[:count].copy(deep=True)
    row = {**deepcopy(context), "schema_version": ROW_SCHEMA,
        **_explain_prefix(frame, context["strategy_params"], has_position, context["cutoff_session"],
                         strategy_class=strategy_class, indicators=indicators, models=models)}
    row["diagnostic_id"] = _digest(row)
    _require(_rule_runtime(context["source_hash"])[0] == source, "source_changed_during_read")
    return row


def accepted_factors(service, payload):
    _require(type(payload) is dict and set(payload) == {"reference", "context_id", "position_context"}, "request_fields_invalid")
    position = payload["position_context"]
    _require(type(position) is dict and set(position) == {"has_position"}
             and type(position["has_position"]) is bool, "explicit_position_context_required")
    _require(_hash(payload["context_id"]), "context_id_required")
    _require(sha256(Path(__file__).read_bytes()).hexdigest() == _ADAPTER_LOADED_SHA, "adapter_source_changed_restart_required")
    context, snapshot = _saved_context(service, payload["reference"])
    _require(context["context_id"] == payload["context_id"], "context_changed_reread_required")
    row = _diagnose(context, snapshot, position["has_position"])
    # Recheck the original files after calculation as well; never attach a
    # response to a context changed while it was being explained.
    _require(_saved_context(service, payload["reference"])[0] == context, "saved_context_changed_during_read")
    _require(sha256(Path(__file__).read_bytes()).hexdigest() == _ADAPTER_LOADED_SHA, "adapter_source_changed_restart_required")
    return dict(schema_version=FACTORS_SCHEMA, reference=deepcopy(context["reference"]),
        context_id=context["context_id"], read_only=True, new_economic_runs=0, permissions=dict(PERMISSIONS), row=row)
