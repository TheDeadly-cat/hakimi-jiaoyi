"""Pure descriptions of verified saved research and a verified synthetic snapshot.

The caller owns verification and one consistent ledger read transaction. This
module performs no reads, writes, matching, research runs, or return attribution.
Evidence pointers address the supplied projection/binding/snapshot, not invented
paths into an engine's original report. Record integrity is not authenticity.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
import math

from .offline_execution import SCHEMA as LEDGER_SCHEMA, PERMISSIONS, _binding, _hash


SCHEMA = "hakimi-execution-explanation-v1"
GROUPS = (("DATA", "数据"), ("RULES", "规则"), ("TIMING", "时点"),
          ("MATCHING", "撮合"), ("COSTS", "费用"), ("UNKNOWN", "未知"))


def _known(value):
    if value is None or value == "UNKNOWN" or value == "UNRECORDED":
        return False
    if type(value) is float:
        return math.isfinite(value)
    return value != ""


def _same(left, right):
    # In particular, a boolean must not silently equal a numeric parameter.
    return _hash(left) == _hash(right)


def explain_execution(saved_projection, bound_plan, validated_snapshot, reference_binding):
    """Explain recorded conditions; MATCH never establishes event alignment.

    `saved_projection` must come from project_saved_result after verification;
    `validated_snapshot` is the full store.snapshot() return, not service display
    metadata or a history tail. A different reference yields context only and no
    associated order facts. Missing descriptive fields remain null.
    """
    p, plan, snap = saved_projection, bound_plan, validated_snapshot
    if any(type(value) is not dict for value in (p, plan, snap)):
        raise ValueError("execution_explanation_objects_required")
    c, identities = p.get("conditions", {}), p.get("identities", {})
    if (c.get("record_integrity") != "VERIFIED_RECORD" or not c.get("completed_result")
            or p.get("binding_conflicts") != []):
        raise ValueError("execution_explanation_verified_projection_required")
    reference = _binding(reference_binding)
    for actual, expected in ((identities.get("report_hash"), reference["report_hash"]),
                             (identities.get("run_id"), reference["report_id"]),
                             (identities.get("task_id"), reference["task_id"]),
                             (c.get("input_identity"), reference["input_id"]),
                             (p.get("strategy_id"), reference["strategy_id"]),
                             (p.get("strategy_params"), reference["strategy_params"])):
        if not _same(actual, expected):
            raise ValueError("execution_explanation_projection_binding_mismatch")
    if (snap.get("schema_version") != LEDGER_SCHEMA or snap.get("evidence_kind") != "SYNTHETIC_TEST"
            or type(snap.get("revision")) is not int or snap["revision"] < 0
            or any(snap.get("permissions", {}).get(key) is not False for key in PERMISSIONS if key != "local_simulation_allowed")):
        raise ValueError("execution_explanation_synthetic_snapshot_required")
    plan_id, account_id = plan.get("plan_id"), snap.get("account_id")
    plans = snap.get("plans", [])
    matches = [(i, value) for i, value in enumerate(plans) if value.get("plan_id") == plan_id]
    if not plan_id or len(matches) != 1 or not _same(matches[0][1], plan) or plan.get("account_id") != account_id:
        raise ValueError("execution_explanation_snapshot_plan_mismatch")
    bound = _binding(plan["research_binding"])
    if plan.get("binding_hash") != _hash(bound):
        raise ValueError("execution_explanation_plan_binding_mismatch")
    document = {key: value for key, value in plan.items() if key != "plan_id"}
    if _hash(document) != plan_id:
        raise ValueError("execution_explanation_plan_identity_mismatch")
    associated = _same(reference, bound)
    if reference["report_hash"] == bound["report_hash"] and not associated:
        raise ValueError("execution_explanation_same_report_binding_conflict")
    plan_index, revision = matches[0][0], snap["revision"]
    groups = {key: {"id": key, "label": label, "items": []} for key, label in GROUPS}

    def evidence(source, pointer, **extra):
        identity = ({"report_hash": reference["report_hash"], "record_id": p.get("record_id")}
                    if source in {"SAVED_PROJECTION", "REFERENCE_BINDING"}
                    else {"account_id": account_id, "ledger_revision": revision})
        return {"source": source, "pointer": pointer, **identity, **extra}

    def fact(value, refs, unit=None):
        return {"value": deepcopy(value) if _known(value) else None, "unit": unit,
                "evidence_ref": deepcopy(refs if type(refs) is list else [refs])}

    def research(key, *, container="conditions", unit=None):
        refs = [evidence("SAVED_PROJECTION", "/"+container+"/"+key)]
        unit_key = {"fee_rate": "fee_rate_unit", "slippage_rate": "slippage_unit", "total_fees": "currency"}.get(key)
        if container == "costs" and unit_key:
            refs.append(evidence("SAVED_PROJECTION", "/costs/"+unit_key))
        return fact(p.get(container, {}).get(key), refs, unit)

    def contract(key, value, unit=None):
        return fact(value, {"source": "SCHEMA_CONTRACT", "schema_version": LEDGER_SCHEMA, "contract_key": key}, unit)

    def unavailable(reason):
        return fact(None, {"source": "UNRECORDED", "reason": reason})

    def add(group, key, label, left, right, explanation, *, comparable=True, action="查看只读依据"):
        status = ("UNKNOWN" if not comparable or not _known(left["value"]) or not _known(right["value"])
                  else "MATCH" if _same(left["value"], right["value"]) and left["unit"] == right["unit"] else "DIFFERENT")
        groups[group]["items"].append({"id": key, "label": label, "status": status,
            "research": left, "simulation": right, "explanation_code": key.upper(),
            "explanation": explanation, "next_action": action})

    def binding(group, key, label, explanation):
        add(group, key, label, fact(reference.get(key), evidence("REFERENCE_BINDING", "/"+key)),
            fact(bound.get(key), evidence("VALIDATED_SNAPSHOT", f"/plans/{plan_index}/research_binding/{key}", plan_id=plan_id)), explanation)

    # One cumulative row per exact order identity. Identical duplicates are
    # counted once; conflicting duplicates cannot represent a verified view.
    selected, seen = [], {}
    for index, row in enumerate(snap.get("orders", [])):
        terms = row.get("terms", {})
        if terms.get("plan_id") != plan_id:
            continue
        order_id = row.get("order_id")
        if not order_id or terms.get("account_id") != account_id or terms.get("owner_id") != plan.get("owner_id") or terms.get("binding_hash") != plan["binding_hash"]:
            raise ValueError("execution_explanation_order_binding_mismatch")
        if order_id in seen:
            if not _same(seen[order_id], row):
                raise ValueError("execution_explanation_conflicting_order_rows")
            continue
        seen[order_id] = row
        selected.append((index, row))
    linked = selected if associated else []

    def order_facts(keys, *, terms=False):
        if not associated:
            return unavailable("SELECTED_REPORT_IS_NOT_PLAN_REPORT")
        values, refs = [], []
        for index, row in linked:
            source = row["terms"] if terms else row
            values.append({"order_id": row["order_id"], **{key: deepcopy(source.get(key)) for key in keys}})
            refs.extend(evidence("VALIDATED_SNAPSHOT", f"/orders/{index}/"+("terms/" if terms else "")+key,
                                 order_id=row["order_id"]) for key in keys)
        return fact(values if values else None, refs or evidence("VALIDATED_SNAPSHOT", "/orders", plan_id=plan_id))

    def cumulative_fee():
        if not associated or not linked:
            return unavailable("NO_ASSOCIATED_PLAN_ORDER_FEES")
        currency = snap.get("config", {}).get("currency")
        refs, values = [evidence("VALIDATED_SNAPSHOT", "/config/currency")], []
        for index, row in linked:
            value = row.get("fee")
            refs.append(evidence("VALIDATED_SNAPSHOT", f"/orders/{index}/fee", order_id=row["order_id"]))
            try:
                amount = Decimal(value) if type(value) is str else None
            except InvalidOperation:
                amount = None
            if amount is None or not amount.is_finite() or amount < 0:
                return fact(None, refs, currency)
            values.append(amount)
        with localcontext() as precision:
            precision.prec = 60
            return fact(format(sum(values, Decimal(0)), "f"), refs, currency)

    binding("DATA", "security_id", "证券身份", "一致仅表示计划绑定了这份研究证券，不证明合成报价来自该研究行情。")
    binding("DATA", "input_id", "封存数据", "此处核对计划绑定的输入编号；合成订单没有新的行情序列可与原输入逐行核对。")
    coverage = {key: c.get(key) for key in ("data_start", "data_end", "score_start", "score_end", "context_rows", "scored_rows", "price_basis", "as_of")}
    add("DATA", "data_window", "数据与评估范围", fact(coverage,
        [evidence("SAVED_PROJECTION", "/conditions/"+key) for key in coverage]), unavailable("NO_SIMULATION_BAR_SERIES"),
        "预热行与评估行按原记录展示；演练没有对应日线序列，不能推定为同一行情窗口。")
    for key, label in (("engine_id", "研究引擎"), ("strategy_id", "规则身份"), ("strategy_params", "规则参数"), ("risk", "研究风险设置"), ("source_hash", "代码身份")):
        binding("RULES", key, label, "核对保存报告与计划的绑定记录。即使一致，也不能证明手工订单由这条规则的某次信号产生。")
    add("TIMING", "timing_policy", "信号与执行时点约定", research("execution_assumptions"),
        contract("timing_policy", "EXPLICIT_SIGNAL_AND_EXECUTION_TIMESTAMPS"),
        "回测时点约定按报告记录展示；演练订单时间由用户明确填写，未建立逐笔信号对应。", comparable=False)
    add("TIMING", "order_times", "订单记录时间", unavailable("NO_EXPLICIT_RESEARCH_EVENT_LINK"),
        order_facts(("signal_at", "execution_at"), terms=True), "这些是合成订单声明的时间，不是成交观察发生时间。", comparable=False)
    add("TIMING", "fill_time", "成交发生时间", unavailable("NO_EXPLICIT_RESEARCH_EVENT_LINK"),
        unavailable("OBSERVATION_SCHEMA_HAS_NO_FILL_TIME"), "当前观察没有记录成交发生时刻，不能由事件顺序推算成交延迟。")
    add("MATCHING", "fill_model", "成交方式", research("execution_model"),
        contract("fill_model", "EXPLICIT_SYNTHETIC_CUMULATIVE_OBSERVATIONS_NO_PRICE_MATCHING"),
        "回测使用报告中的撮合模型；演练仅接受明确记录的合成累计观察，不自动用价格撮合，也不是券商成交。")
    add("MATCHING", "quantity_policy", "股数规则", research("quantity_policy"),
        fact(snap.get("config", {}).get("quantity_policy"), evidence("VALIDATED_SNAPSHOT", "/config/quantity_policy")),
        "演练使用整数股、只做多；回测是否允许碎股只看原记录，缺项不会补推。")
    add("MATCHING", "order_observations", "本计划订单累计记录", unavailable("NO_EXPLICIT_RESEARCH_EVENT_LINK"),
        order_facts(("state", "filled", "notional", "fee", "reserved_cash", "reserved_shares", "cancel_state")),
        "只展示此计划每笔订单最新累计值，不累加历史累计观察。部分成交、撤销与待核对均保持原状态。", comparable=False)
    binding("COSTS", "costs", "绑定费用设置", "计划保留原研究费用设置；一致不表示两边实际成交股数或费用相同。")
    add("COSTS", "fee_rate", "回测手续费率", research("fee_rate", container="costs", unit=p.get("costs", {}).get("fee_rate_unit")),
        unavailable("OBSERVATIONS_RECORD_AMOUNTS_NOT_FEE_RATE"), "演练记录的是合成费用金额，不能倒推出与回测同口径的费率。")
    add("COSTS", "slippage", "回测滑点", research("slippage_rate", container="costs", unit=p.get("costs", {}).get("slippage_unit")),
        unavailable("NO_MATCHED_REFERENCE_PRICE"), "保留原滑点单位；没有逐笔基准价与事件对应，演练滑点金额保持未知。")
    add("COSTS", "recorded_fees", "各自记录的累计费用", research("total_fees", container="costs", unit=p.get("costs", {}).get("currency")),
        cumulative_fee(), "合成费用仅对本计划不同订单的累计费用求和。两边事件未对应，不计算费用对收益差的贡献。", comparable=False)
    add("UNKNOWN", "event_alignment", "逐笔对应关系", unavailable("NO_EXPLICIT_CAUSAL_MAPPING"),
        unavailable("NO_EXPLICIT_CAUSAL_MAPPING"), "计划绑定一致不等于逐笔对应；不能按列表位置、相似时间或相同股票猜测。")
    add("UNKNOWN", "authenticity", "记录性质", fact(p.get("evidence_status"), evidence("SAVED_PROJECTION", "/evidence_status")),
        fact(snap["evidence_kind"], evidence("VALIDATED_SNAPSHOT", "/evidence_kind")),
        "文件与账本校验只确认记录完整性。手工合成观察不提供外部成交真实性证明。", comparable=False)
    add("UNKNOWN", "ledger_gate", "账户待核对事项", unavailable("RESEARCH_IS_NOT_SHARED_ACCOUNT_STATE"),
        fact({key: snap.get(key) for key in ("stop_reason", "reconciliation_required", "account_deficits")},
             [evidence("VALIDATED_SNAPSHOT", "/"+key) for key in ("stop_reason", "reconciliation_required", "account_deficits")]),
        "暂停、待核对与账户缺口按当前账本显示；查看差异不会恢复账户或重提未知订单。", comparable=False)

    for group in groups.values():
        group["counts"] = {status: sum(item["status"] == status for item in group["items"]) for status in ("MATCH", "DIFFERENT", "UNKNOWN")}
        group["default_open"] = bool(group["counts"]["DIFFERENT"] or group["counts"]["UNKNOWN"])
    return {"schema_version": SCHEMA,
        "status": "BOUND_REPORT_CONTEXT_ONLY" if associated else "ONLY_CONTEXT_NO_ATTRIBUTION",
        "summary": ("计划绑定这份报告；以下说明记录条件，尚不能逐笔解释收益差。" if associated else
                    "当前报告不是此计划绑定的原报告；仅展示合同差异，不把该计划订单关联到当前报告。"),
        "scope": {"account_id": account_id, "plan_id": plan_id, "ledger_revision": revision,
                  "reference_report_hash": reference["report_hash"], "bound_report_hash": bound["report_hash"],
                  "orders_associated_with_reference": associated, "order_count": len(linked) if associated else None},
        "groups": list(groups.values()),
        "account_scope": {"label": "整个合成账户，跨策略共享；不是本计划收益", "account_id": account_id,
            "ledger_revision": revision, "currency": snap.get("config", {}).get("currency"),
            "cash": snap.get("cash"), "reserved_cash": snap.get("reserved_cash"), "available_cash": snap.get("available_cash"),
            "owner_positions_scope": "OWNER_ACROSS_PLANS_NOT_SINGLE_PLAN", "owner_id": plan.get("owner_id"),
            "owner_positions": deepcopy([row for row in snap.get("positions", []) if row.get("owner_id") == plan.get("owner_id")]),
            "evidence_ref": [evidence("VALIDATED_SNAPSHOT", "/"+key) for key in ("cash", "reserved_cash", "available_cash", "positions", "config/currency")]},
        "attribution": {"event_alignment": "UNKNOWN", "numeric_performance_comparison_allowed": False,
                        "total_difference": None, "contributions": None},
        "permissions": dict(PERMISSIONS), "new_economic_runs": 0, "external_calls": 0}
