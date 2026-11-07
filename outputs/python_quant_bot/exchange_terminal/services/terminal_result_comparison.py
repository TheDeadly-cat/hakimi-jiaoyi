"""Strict, read-only comparison of already verified saved report envelopes.

The route resolves opaque IDs and runs the existing record verifier before
calling this module. An integrity marker is not source authentication. No report
is repaired, re-signed, defaulted, recalculated or ranked here.
"""
from copy import deepcopy
from decimal import Decimal
import math


SCHEMA = "hakimi-strict-saved-result-comparison-v1"
_MISSING = object()
_PERMISSIONS = {"research_only": True, "paper_allowed": False, "live_allowed": False, "order_allowed": False}


def _get(value, path, default=None):
    for key in path.split("."):
        if type(value) is not dict or key not in value:
            return default
        value = value[key]
    return value


def _present(value):
    if value is None or value is _MISSING:
        return False
    if type(value) is str:
        return bool(value.strip()) and value.strip().upper() not in {"UNKNOWN", "UNRECORDED", "NOT_RECORDED", "未记录"}
    if type(value) in (dict, list, tuple):
        return bool(value)
    return type(value) is bool or type(value) in (int, float) and math.isfinite(value)


def _first(*values):
    return next((value for value in values if _present(value)), None)


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def project_saved_result(envelope):
    """Preserve report identities; absent essential facts remain missing.

    Canonical reports need their verified retained snapshot for timeframe/as-of
    fields omitted from the report projection. Native reports use input_summary.
    Both require verification_status=VERIFIED_RECORD set by the trusted reader.
    """
    if type(envelope) is not dict:
        raise ValueError("comparison_verified_envelope_required")
    report = envelope.get("report", {})
    if type(report) is not dict:
        raise ValueError("comparison_report_object_required")
    native = report.get("schema_version") == "hakimi-terminal-run-v1"
    canonical = report.get("schema_version") in {"us-equity-research-report-v1", "us-equity-research-report-v2", "us-equity-content-task-report-v1"}
    kind = "ORIGINAL_NATIVE" if native else "CANONICAL_EQUITY" if canonical else "UNRECOGNIZED"
    config, result = report.get("configuration", {}), report.get("result", {})
    manifest, snapshot = envelope.get("manifest", {}), envelope.get("snapshot", {})
    config = config if type(config) is dict else {}
    result = result if type(result) is dict else {}
    manifest = manifest if type(manifest) is dict else {}
    snapshot = snapshot if type(snapshot) is dict else {}
    conditions, missing, conflicts = {}, [], []

    def fact(key, value, *, numeric=False):
        if numeric:
            value = _number(value)
        conditions[key] = deepcopy(value) if _present(value) else None
        if not _present(value):
            missing.append(key)

    def agree(label, *values):
        known = [value for value in values if _present(value)]
        if known and any(value != known[0] for value in known[1:]):
            conflicts.append(label)

    fact("record_integrity", envelope.get("verification_status") if envelope.get("verification_status") == "VERIFIED_RECORD" else None)
    fact("engine_family", kind if native or canonical else None)
    is_benchmark = (canonical and _get(manifest, "task.strategy") == "price.buy_and_hold@1"
                    and _get(report, "spec.strategy.name") == "buy_and_hold"
                    and _get(report, "spec.execution_policy") == "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET")
    if native:
        inputs = report.get("input_summary", {})
        meta = _get(inputs, "meta") or {}
        risk = config.get("risk") or {}
        strategy_id = report.get("strategy_id")
        params = config.get("strategy_params")
        identities = {"run_id": _first(envelope.get("run_id"), report.get("run_id"), report.get("id")),
                      "report_hash": _first(report.get("report_hash"), report.get("id")),
                      "task_id": report.get("task_id"), "task_version": report.get("version")}
        fact("completed_result", report.get("status") if report.get("status") == "COMPLETED" else None)
        fact("engine_identity", _first(report.get("engine_id"), config.get("engine_id")))
        fact("code_source", config.get("engine_source_identity"))
        fact("input_identity", config.get("input_id"))
        fact("retained_input_identity", _first(_get(inputs, "id"), _get(inputs, "input_id")))
        agree("native_input_binding", config.get("input_id"), _get(inputs, "id"), _get(inputs, "input_id"))
        fact("security_identity", _first(meta.get("security_id"), _get(meta, "security.security_id")))
        fact("timeframe", _first(_get(inputs, "bar"), meta.get("interval")))
        fact("session", meta.get("session"))
        fact("timezone", meta.get("timezone"))
        fact("as_of", meta.get("as_of"))
        fact("price_basis", meta.get("price_basis") if meta.get("price_basis") != "UNKNOWN" else None)
        fact("data_start", _get(inputs, "date_start"))
        fact("data_end", _get(inputs, "date_end"))
        for target, key in (("score_start", "start"), ("score_end", "end"), ("scored_rows", "evaluated_rows"), ("context_rows", "context_rows")):
            fact(target, _get(result, "evaluation_window." + key), numeric=target.endswith("rows"))
        fact("initial_cash", config.get("initial_cash"), numeric=True)
        fact("currency", _first(meta.get("currency"), _get(meta, "security.currency")))
        fact("position_risk", risk)
        for key in ("position_pct", "take_profit_pct", "stop_loss_pct", "leverage"):
            fact("risk." + key, risk.get(key), numeric=True)
        fee, slippage = _get(config, "costs.fee_rate"), _get(config, "costs.slippage_bps")
        slippage_unit = "basis_points"
        fact("fee_rate", fee, numeric=True)
        fact("slippage_rate", slippage, numeric=True)
        fact("slippage_unit", slippage_unit)
        fact("execution_model", config.get("execution_model"))
        agree("native_execution_binding", config.get("execution_model"), result.get("execution_model"))
        fact("execution_assumptions", result.get("execution_assumptions"))
        fact("quantity_policy", _first(config.get("quantity_policy"), result.get("quantity_policy"), _get(result, "execution_assumptions.quantity_policy")))
        fact("direction_policy", config.get("direction_mode"))
        fact("end_policy", config.get("end_policy"))
        fact("corporate_action_policy", _first(config.get("corporate_action_policy"), _get(meta, "core_research_admission.scope")))
        net_return = _number(result.get("total_return_pct"))
        net_return_ratio = float(Decimal(str(net_return)) / 100) if net_return is not None else None
        benchmark_policy = None
    else:
        spec, dataset = report.get("spec", {}), report.get("dataset", {})
        spec = spec if type(spec) is dict else {}
        dataset = dataset if type(dataset) is dict else {}
        params = _get(spec, "strategy.params")
        risk = spec.get("risk") or {}
        strategy_id = _get(manifest, "task.strategy")
        identities = {"run_id": manifest.get("run_id"), "report_hash": report.get("report_hash"),
                      "task_id": manifest.get("task_id"), "task_version": _get(manifest, "task.management.revision")}
        # A verified canonical complete report has no native status field. Its
        # recorded schema/result and retained manifest are the completion proof.
        fact("completed_result", report.get("schema_version") if canonical and result and manifest else None)
        fact("engine_identity", {"report_schema": report.get("schema_version"), "execution_model": result.get("execution_model")} if canonical and result.get("execution_model") else None)
        fact("code_source", _get(manifest, "runtime.source_identity.content_sha256"))
        fact("runtime_dependencies", _get(manifest, "runtime.environment_verified"))
        fact("input_identity", dataset.get("snapshot_id"))
        fact("retained_input_identity", snapshot.get("snapshot_id"))
        agree("canonical_input_binding", dataset.get("snapshot_id"), spec.get("snapshot_id"), snapshot.get("snapshot_id"))
        agree("canonical_report_task_binding", spec, _get(manifest, "task.experiment"))
        if report.get("schema_version") in {"us-equity-research-report-v2", "us-equity-content-task-report-v1"}:
            fact("event_input_identity", spec.get("event_context_hash"))
            fact("event_rule", spec.get("event_rule"))
            agree("canonical_event_binding", spec.get("event_context_hash"), _get(report, "event_context.context_hash"))
        fact("security_identity", dataset.get("security"))
        fact("timeframe", snapshot.get("timeframe"))
        fact("session_clock", _get(report, "scoring_protocol.session_clock_hash"))
        fact("timezone", snapshot.get("timezone"))
        fact("as_of", snapshot.get("as_of"))
        fact("price_basis", dataset.get("price_basis"))
        sessions = dataset.get("sessions")
        fact("data_start", sessions[0].get("date") if type(sessions) is list and sessions and type(sessions[0]) is dict else None)
        fact("data_end", sessions[-1].get("date") if type(sessions) is list and sessions and type(sessions[-1]) is dict else None)
        for target, key in (("score_start", "score_start"), ("score_end", "score_end"), ("scored_rows", "scored_sessions"), ("context_rows", "available_context_sessions")):
            fact(target, _get(report, "scoring_protocol." + key), numeric=target.endswith("rows"))
        fact("initial_cash", spec.get("initial_cash"), numeric=True)
        fact("currency", _get(dataset, "security.currency"))
        fact("position_risk", risk)
        for key in ("max_position_pct", "max_single_loss_pct", "max_daily_loss_pct", "max_leverage", "min_cash_pct"):
            fact("risk." + key, risk.get(key), numeric=True)
        fact("allocation", _get(params, "target_position_pct" if is_benchmark else "position_pct"), numeric=True)
        protections = _get(result, "risk_semantics.protective_exits_enabled")
        fact("protective_exits_enabled", protections if type(protections) is bool else None)
        if protections is True:
            fact("requested_stop_loss", _get(params, "stop_loss_pct"), numeric=True)
            fact("requested_take_profit", _get(params, "take_profit_pct"), numeric=True)
        fact("risk_semantics", result.get("risk_semantics"))
        fee, slippage = spec.get("fee_rate"), spec.get("slippage_pct")
        slippage_unit = "ratio"
        fact("fee_rate", fee, numeric=True)
        fact("slippage_rate", slippage, numeric=True)
        fact("slippage_unit", slippage_unit)
        fact("execution_model", result.get("execution_model"))
        fact("execution_policy", spec.get("execution_policy"))
        fact("quantity_policy", spec.get("quantity_policy"))
        fact("end_policy", spec.get("end_policy"))
        fact("corporate_action_policy", _get(report, "scoring_protocol.company_actions"))
        fact("research_admission_scope", _get(dataset, "research_admission.scope"))
        net_return_ratio = _number(result.get("total_return"))
        benchmark_policy = {"execution_policy": spec.get("execution_policy"),
                            "recorded_benchmark_policy": _get(result, "risk_semantics.benchmark_policy"),
                            "protective_exits_enabled": protections} if is_benchmark else None
    for key in ("run_id", "report_hash", "task_id"):
        if not _present(identities[key]):
            missing.append("identity." + key)
    if not _present(strategy_id):
        missing.append("strategy_identity")
    if net_return_ratio is None:
        missing.append("net_return")
    if envelope.get("status") is not None and envelope.get("status") != "COMPLETED":
        missing.append("envelope_completed_result")
    return {"record_id": envelope.get("id"), "kind": kind, "identities": deepcopy(identities),
            "strategy_id": strategy_id, "strategy_params": deepcopy(params),
            "role": "BENCHMARK_REFERENCE" if is_benchmark else "STRATEGY_RESULT",
            "benchmark_policy": benchmark_policy, "conditions": conditions,
            "missing_fields": sorted(set(missing)), "binding_conflicts": conflicts,
            "costs": {"fee_rate": _number(fee), "fee_rate_unit": "ratio", "total_fees": _number(result.get("total_fees")),
                      "slippage_rate": _number(slippage), "slippage_unit": slippage_unit,
                      "slippage_model_recorded": _first(_get(config, "costs.slippage_model"), config.get("slippage_model"), result.get("slippage_model")),
                      "execution_model": conditions.get("execution_model"), "currency": conditions.get("currency"),
                      "slippage_amount_recorded": _number(result.get("total_slippage"))},
            "net_return_ratio": net_return_ratio, "evidence_status": _first(report.get("evidence_status"), _get(report, "dataset.evidence_kind")),
            "max_drawdown_ratio": (float(Decimal(str(result["max_drawdown_pct"])) / 100)
                if native and _number(result.get("max_drawdown_pct")) is not None
                else _number(result.get("max_drawdown")) if canonical else None),
            "statistical_status": deepcopy(result.get("statistical_status")), "original_report_unchanged": True}


def compare_saved_results(records):
    if type(records) is not list or not 2 <= len(records) <= 10:
        raise ValueError("strict_comparison_requires_two_to_ten_saved_results")
    rows = [project_saved_result(record) for record in records]
    identities = [(row["kind"], row["identities"]["run_id"], row["identities"]["report_hash"]) for row in rows
                  if _present(row["identities"]["run_id"]) and _present(row["identities"]["report_hash"])]
    if len(set(identities)) != len(identities):
        raise ValueError("strict_comparison_requires_distinct_saved_results")
    missing = [{"row": index, "fields": row["missing_fields"]} for index, row in enumerate(rows, 1) if row["missing_fields"]]
    conflicts = [{"row": index, "fields": row["binding_conflicts"]} for index, row in enumerate(rows, 1) if row["binding_conflicts"]]
    mismatches = []
    baseline = rows[0]["conditions"]
    for index, row in enumerate(rows[1:], 2):
        fields = [key for key in sorted(set(baseline) | set(row["conditions"]))
                  if _present(baseline.get(key)) and _present(row["conditions"].get(key)) and baseline[key] != row["conditions"][key]]
        if row["kind"] != rows[0]["kind"] and "engine_family" not in fields:
            fields.append("engine_family")
        if fields:
            mismatches.append({"row": index, "fields": fields})
    benchmark_rows = [index for index, row in enumerate(rows, 1) if row["role"] == "BENCHMARK_REFERENCE"]
    status = "UNKNOWN_CONDITIONS" if missing or conflicts else "SIDE_BY_SIDE_ONLY" if mismatches or benchmark_rows else "COMPARABLE_CONDITIONS"
    differences = []
    if status == "COMPARABLE_CONDITIONS":
        initial = Decimal(str(rows[0]["net_return_ratio"]))
        differences = [{"row": index, "net_return_percentage_points": float((Decimal(str(row["net_return_ratio"])) - initial) * 100)}
                       for index, row in enumerate(rows[1:], 2)]
    return {"schema_version": SCHEMA, "status": status, "rows": rows, "missing": missing,
            "mismatches": mismatches, "binding_conflicts": conflicts, "benchmark_rows": benchmark_rows,
            "differences_from_first": differences, "ranking": None, "new_economic_runs": 0,
            "shared_portfolio": False, "permissions": dict(_PERMISSIONS),
            "interpretation": ["只读取已经校验的保存结果，不补算、不重签；未记录的关键条件保持未记录。",
                "条件齐全且相同时，仅展示相对首行的描述性净收益百分点差，不表示策略有效性或排名。",
                "基准独立展示其入场与保护政策，不自动计算跨引擎超额收益。",
                "手续费金额与滑点参数按原记录展示；未记录滑点金额或模型时不补造。"]}
