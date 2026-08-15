from __future__ import annotations

import math
import threading
from typing import Any, Callable


VALID_SIDES = {"BUY", "SELL", "CLOSE", "SHORT", "COVER", "ARM", "CONDITION"}
VALID_MODES = {"PAPER", "SHADOW", "SIMULATION", "LIVE"}
VALID_POSITION_SIDES = {"FLAT", "LONG", "SHORT"}
VALID_DIRECTION_MODES = {"LONG_ONLY", "SHORT_ONLY"}
IMMEDIATE_PAPER_ORDER_TYPES = {"MARKET", "CURRENT", "IOC", "FOK"}
CONDITIONAL_PAPER_ORDER_TYPES = {"OCO"}
PERSISTENT_PAPER_ORDER_TYPES = {"LIMIT", "POST_ONLY"}
HISTORICAL_SIMULATION_STATUSES = {"BACKTEST_READY", "HISTORICAL_READY"}
MAX_RISK_SNAPSHOT_AGE_MS = 5_000
MAX_RISK_SNAPSHOT_FUTURE_SKEW_MS = 1_000
AUTHORITATIVE_MARKET_CONTEXT_KEYS = (
    "data_status",
    "data_quarantined",
    "data_realtime",
    "data_fallback",
    "data_quality",
    "market_snapshot_id",
    "authoritative_price",
    "price_deviation_pct",
)

AuditWriter = Callable[[dict[str, Any]], Any]
DataContextProvider = Callable[[str, float, dict[str, Any]], dict[str, Any]]
PortfolioContextProvider = Callable[[dict[str, Any], str, str, float, float, dict[str, Any]], dict[str, Any]]


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    ok: bool,
    level: str,
    message: str,
    *,
    blocking: bool | None = None,
) -> None:
    clean_ok = ok if type(ok) is bool else False
    if blocking is None:
        clean_blocking = level == "P0"
    else:
        clean_blocking = blocking if type(blocking) is bool else True
    checks.append({
        "name": name,
        "ok": clean_ok,
        "level": level,
        "blocking": clean_blocking,
        "message": message,
    })


def blocking_messages(checks: list[dict[str, Any]]) -> list[str]:
    return [
        str(item.get("message") or item.get("name"))
        for item in checks
        if item.get("blocking") is True and item.get("ok") is not True
    ]


def risk_status_from_checks(checks: list[dict[str, Any]]) -> str:
    if blocking_messages(checks):
        return "BLOCK"
    if any(item.get("ok") is not True for item in checks):
        return "WATCH"
    return "PASS"


def resolve_boolean_sources(
    *sources: tuple[str, dict[str, Any], str],
    default: bool = False,
) -> tuple[bool, list[str]]:
    values: list[tuple[str, bool]] = []
    errors: list[str] = []
    for label, mapping, key in sources:
        if key not in mapping:
            continue
        value = mapping.get(key)
        if type(value) is not bool:
            errors.append(f"{label}:expected_boolean")
            continue
        values.append((label, value))
    if values and any(value != values[0][1] for _, value in values[1:]):
        errors.append("conflicting_boolean_sources:" + ",".join(label for label, _ in values))
    return (values[0][1] if values else default), errors


def finite_positive(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(number) or number <= 0:
        return 0.0
    return number


def finite_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except Exception:
        return default
    return number if math.isfinite(number) else default


def normalized_string_list(value: Any) -> tuple[list[str], bool]:
    if not isinstance(value, (list, tuple)):
        return [], False
    return [str(item) for item in value if str(item)], True


def fallback_market_context(reason: str) -> dict[str, Any]:
    return {
        "data_status": "OFFLINE",
        "data_quarantined": True,
        "data_realtime": False,
        "data_fallback": True,
        "market_snapshot_id": "",
        "authoritative_price": 0.0,
        "price_deviation_pct": 0.0,
        "data_quality": {
            "status": "OFFLINE",
            "realtime": False,
            "fallback": True,
            "quarantined": True,
            "can_increase_risk": False,
            "can_simulate": False,
            "historical": False,
            "attested": False,
            "blocking_reasons": [reason],
        },
    }


def validate_market_context_contract(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["market_context_object_required"]
    errors: list[str] = []
    if not isinstance(value.get("data_status"), str) or not str(value.get("data_status") or "").strip():
        errors.append("data_status_invalid")
    for field in ("data_quarantined", "data_realtime", "data_fallback"):
        if type(value.get(field)) is not bool:
            errors.append(f"{field}_invalid")
    for field in ("market_snapshot_id",):
        if not isinstance(value.get(field), str):
            errors.append(f"{field}_invalid")
    for field in ("authoritative_price", "price_deviation_pct"):
        raw = value.get(field)
        parsed = finite_number(raw, math.nan)
        if isinstance(raw, bool) or not math.isfinite(parsed) or parsed < 0:
            errors.append(f"{field}_invalid")
    quality = value.get("data_quality")
    if not isinstance(quality, dict):
        errors.append("data_quality_object_required")
        return errors
    if not isinstance(quality.get("status"), str) or not str(quality.get("status") or "").strip():
        errors.append("data_quality_status_invalid")
    for field in ("realtime", "fallback", "quarantined", "can_increase_risk"):
        if type(quality.get(field)) is not bool:
            errors.append(f"data_quality_{field}_invalid")
    _, reasons_valid = normalized_string_list(quality.get("blocking_reasons"))
    if not reasons_valid:
        errors.append("data_quality_blocking_reasons_invalid")
    return errors


def canonicalize_account_context(risk: dict[str, Any], context: dict[str, Any]) -> tuple[str, bool]:
    """Replace caller-supplied account facts with the authoritative risk snapshot."""
    paper = risk.get("paper") if isinstance(risk.get("paper"), dict) else {}
    raw_mismatches = context.get("account_context_mismatches", [])
    mismatches_contract_valid = isinstance(raw_mismatches, (list, tuple))
    safe_mismatches = raw_mismatches if mismatches_contract_valid else []
    mismatches = [
        dict(item)
        for item in safe_mismatches
        if isinstance(item, dict)
    ]

    def add_mismatch(field: str, caller: Any, authoritative: Any) -> None:
        mismatch = {"field": field, "caller": caller, "authoritative": authoritative}
        if mismatch not in mismatches:
            mismatches.append(mismatch)

    authoritative = str(paper.get("position_side") or "").upper()
    caller_supplied = "requested_position_side" in context or (
        "position_side" in context and str(context.get("position_side") or "").strip() != ""
    )
    if "requested_position_side" not in context and caller_supplied:
        context["requested_position_side"] = context.get("position_side")
    caller = str(context.get("requested_position_side") or "").upper()

    if authoritative in VALID_POSITION_SIDES:
        if caller_supplied and caller != authoritative:
            add_mismatch("position_side", caller, authoritative)
        position_side = authoritative
        authoritative_available = True
    else:
        if caller_supplied:
            add_mismatch("position_side", caller, "UNAVAILABLE")
        position_side = "FLAT"
        authoritative_available = False

    authoritative_direction = str(paper.get("direction_mode") or "").upper()
    direction_supplied = "requested_direction_mode" in context or (
        "direction_mode" in context and str(context.get("direction_mode") or "").strip() != ""
    )
    if "requested_direction_mode" not in context and direction_supplied:
        context["requested_direction_mode"] = context.get("direction_mode")
    requested_direction = str(context.get("requested_direction_mode") or "").upper()
    direction_available = authoritative_direction in VALID_DIRECTION_MODES
    if direction_available:
        if direction_supplied and requested_direction != authoritative_direction:
            add_mismatch("direction_mode", requested_direction, authoritative_direction)
        direction_mode = authoritative_direction
    else:
        if direction_supplied:
            add_mismatch("direction_mode", requested_direction, "UNAVAILABLE")
        direction_mode = ""

    authoritative_leverage = finite_positive(paper.get("leverage"))
    raw_context_leverage = context.get("leverage")
    leverage_supplied = "requested_leverage" in context or (
        "leverage" in context and raw_context_leverage is not None and raw_context_leverage != ""
    )
    if "requested_leverage" not in context and leverage_supplied:
        context["requested_leverage"] = context.get("leverage")
    requested_leverage = finite_positive(context.get("requested_leverage"))
    leverage_available = authoritative_leverage > 0
    if leverage_available:
        if leverage_supplied and (
            requested_leverage <= 0
            or abs(requested_leverage - authoritative_leverage) > 1e-9
        ):
            caller_value: Any = requested_leverage if requested_leverage > 0 else "INVALID"
            add_mismatch("leverage", caller_value, authoritative_leverage)
        leverage = authoritative_leverage
    else:
        if leverage_supplied:
            caller_value = requested_leverage if requested_leverage > 0 else "INVALID"
            add_mismatch("leverage", caller_value, "UNAVAILABLE")
        leverage = 1.0

    raw_authoritative_reduce_only = paper.get("reduce_only")
    reduce_only_available = type(raw_authoritative_reduce_only) is bool
    reduce_only_supplied = "requested_reduce_only" in context or "reduce_only" in context
    if "requested_reduce_only" not in context and "reduce_only" in context:
        context["requested_reduce_only"] = context.get("reduce_only")
    requested_reduce_only = context.get("requested_reduce_only")
    if reduce_only_available:
        if reduce_only_supplied and (
            type(requested_reduce_only) is not bool
            or requested_reduce_only is not raw_authoritative_reduce_only
        ):
            add_mismatch(
                "reduce_only",
                requested_reduce_only if type(requested_reduce_only) is bool else "INVALID",
                raw_authoritative_reduce_only,
            )
        reduce_only = raw_authoritative_reduce_only
    else:
        if reduce_only_supplied:
            add_mismatch("reduce_only", requested_reduce_only, "UNAVAILABLE")
        reduce_only = False

    context["position_side"] = position_side
    context["position_side_authoritative"] = authoritative_available
    context["direction_mode"] = direction_mode
    context["direction_mode_authoritative"] = direction_available
    context["leverage"] = leverage
    context["leverage_authoritative"] = leverage_available
    context["reduce_only"] = reduce_only
    context["reduce_only_authoritative"] = reduce_only_available
    context["account_context_mismatches"] = mismatches
    context["account_context_mismatches_contract_valid"] = mismatches_contract_valid

    account_symbol = str(paper.get("symbol") or "").strip().upper()
    raw_position_value = paper.get("position_value")
    position_value = finite_number(raw_position_value, math.nan)
    position_value_available = (
        not isinstance(raw_position_value, bool)
        and math.isfinite(position_value)
        and position_value >= 0
    )
    context["account_symbol"] = account_symbol
    context["account_symbol_authoritative"] = bool(account_symbol)
    context["position_value"] = position_value if position_value_available else 0.0
    context["position_value_authoritative"] = position_value_available
    return position_side, authoritative_available


def build_risk_snapshot(
    paper: dict[str, Any],
    guardian: dict[str, Any],
    live_trading_hard_block: bool,
    updated_at: int,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    live_wall_contract_valid = type(live_trading_hard_block) is bool
    live_wall_enabled = live_trading_hard_block is True
    add_check(
        checks,
        "live_trading_wall_contract",
        live_wall_contract_valid,
        "P0",
        "Live-trading wall state must be a native boolean.",
    )
    add_check(checks, "live_trading_wall", live_wall_enabled, "P0", "实盘硬墙已开启，任何真实下单都会被拒绝")

    drawdown = max(finite_number(paper.get("drawdown_pct"), math.inf), 0.0)
    max_drawdown = finite_positive(paper.get("max_drawdown_pct")) or 5.0
    add_check(checks, "drawdown_limit", drawdown < max_drawdown, "P0", f"当前回撤 {drawdown:.2f}% / 熔断 {max_drawdown:.2f}%")

    cash = finite_number(paper.get("available_cash"), -math.inf)
    add_check(checks, "cash_available", cash >= 0, "P1", f"可用现金 {cash:.2f} USDT", blocking=False)

    add_check(checks, "cash_integrity", cash >= 0, "P0", "Available cash must be finite and non-negative.")

    guardian_status = str(guardian.get("status", "STOPPED") or "STOPPED").upper()
    add_check(checks, "guardian_state", guardian_status != "ERROR", "P1", f"守护状态 {guardian_status}")

    position_value = finite_number(paper.get("position_value"), math.inf)
    gross_position_value = finite_number(
        paper.get("gross_position_value", paper.get("position_value")),
        math.inf,
    )
    equity = finite_positive(paper.get("equity"))
    leverage = max(finite_positive(paper.get("leverage")) or 1.0, 1.0)
    reduce_only = paper.get("reduce_only", False)
    add_check(
        checks,
        "reduce_only_contract",
        type(reduce_only) is bool,
        "P0",
        "Paper-account reduce-only state must be a native boolean.",
    )
    add_check(checks, "account_equity_positive", equity > 0, "P0", f"Account equity {equity:.2f} must be positive.")
    add_check(checks, "position_value_valid", 0 <= position_value < math.inf, "P0", f"Position value {position_value:.2f} must be finite and non-negative.")
    add_check(
        checks,
        "gross_position_value_valid",
        0 <= gross_position_value < math.inf,
        "P0",
        f"Gross position value {gross_position_value:.2f} must be finite and non-negative.",
    )
    max_gross_notional = max(equity * leverage, equity, 1.0)
    add_check(
        checks,
        "gross_notional_limit",
        gross_position_value <= max_gross_notional * 1.05,
        "P0",
        f"持仓名义价值 {gross_position_value:.2f} / 账户上限 {max_gross_notional:.2f}",
    )

    add_check(checks, "deepseek_boundary", True, "P1", "AI 只提供研究建议，不拥有下单权限", blocking=False)

    allowed_shadow = not blocking_messages(checks)
    status = "BLOCK_LIVE_READY_PAPER" if allowed_shadow else "RISK_BLOCK"
    return {
        "ok": True,
        "mode": "shadow",
        "live_trading_hard_block": live_wall_enabled,
        "live_order_allowed": False,
        "paper_order_allowed": allowed_shadow,
        "status": status,
        "checks": checks,
        "reject_reasons": blocking_messages(checks),
        "pretrade": {
            "status": "PASS" if allowed_shadow else "BLOCK",
            "paper_allowed": allowed_shadow,
            "live_allowed": False,
            "reason": "影子风控通过，仍只允许模拟执行" if allowed_shadow else " / ".join(blocking_messages(checks)),
        },
        "paper": {
            "symbol": paper.get("symbol"),
            "equity": paper.get("equity"),
            "cash": paper.get("cash"),
            "available_cash": paper.get("available_cash"),
            "drawdown_pct": paper.get("drawdown_pct"),
            "risk_status": paper.get("risk_status"),
            "position_side": paper.get("position_side"),
            "position_value": paper.get("position_value"),
            "gross_position_value": paper.get("gross_position_value", paper.get("position_value")),
            "leverage": paper.get("leverage"),
            "direction_mode": paper.get("direction_mode"),
            "reduce_only": reduce_only,
        },
        "updated_at": updated_at,
    }


def build_runtime_risk_view(
    policy_snapshot: Any,
    *,
    runtime_read_only: Any,
    paper: Any,
    pipeline_run: Any = None,
) -> dict[str, Any]:
    """Combine risk-policy state with the runtime's effective paper authority."""
    policy_contract_valid = isinstance(policy_snapshot, dict)
    policy = dict(policy_snapshot) if policy_contract_valid else {
        "ok": False,
        "status": "RISK_SNAPSHOT_ERROR",
        "live_trading_hard_block": True,
        "live_order_allowed": False,
        "paper_order_allowed": False,
        "checks": [],
        "pretrade": {"status": "BLOCK", "paper_allowed": False, "live_allowed": False},
    }
    paper_contract_valid = isinstance(paper, dict)
    clean_paper = dict(paper) if paper_contract_valid else {}
    pipeline_contract_valid = pipeline_run is None or isinstance(pipeline_run, dict)
    clean_pipeline = dict(pipeline_run) if isinstance(pipeline_run, dict) else {}
    runtime_contract_valid = type(runtime_read_only) is bool
    read_only = runtime_read_only is not False
    runtime_mutations_allowed = runtime_contract_valid and not read_only

    live_wall_enabled = policy.get("live_trading_hard_block") is True
    live_boundary_valid = policy.get("live_order_allowed") is False
    risk_policy_allows_paper = (
        policy_contract_valid
        and live_wall_enabled
        and live_boundary_valid
        and policy.get("paper_order_allowed") is True
    )
    paper_order_allowed = risk_policy_allows_paper and runtime_mutations_allowed

    paper_armed = clean_paper.get("armed") is True
    bound_pipeline_run_id = str(clean_paper.get("pipeline_run_id") or "").strip()
    authorized_pipeline_run_id = str(clean_pipeline.get("run_id") or "").strip()
    strategy_binding_valid = bool(
        paper_armed
        and bound_pipeline_run_id
        and bound_pipeline_run_id == authorized_pipeline_run_id
    )
    binding_authorized = bool(
        strategy_binding_valid
        and pipeline_contract_valid
        and clean_pipeline.get("paper_authorized") is True
    )
    paper_authorized = bool(binding_authorized and runtime_mutations_allowed)
    automated_paper_order_allowed = bool(
        paper_order_allowed and paper_armed and paper_authorized
    )

    paper_blockers: list[str] = []
    if not policy_contract_valid:
        paper_blockers.append("risk_snapshot_contract_invalid")
    if not runtime_contract_valid:
        paper_blockers.append("runtime_read_only_contract_invalid")
    if not live_wall_enabled:
        paper_blockers.append("live_trading_hard_wall_missing")
    if not live_boundary_valid:
        paper_blockers.append("live_order_boundary_invalid")
    if not risk_policy_allows_paper:
        paper_blockers.append("risk_policy_blocked")
    if read_only:
        paper_blockers.append("runtime_read_only")

    strategy_blockers = list(paper_blockers)
    if not paper_armed:
        strategy_blockers.append("paper_strategy_not_armed")
    if paper_armed and not bound_pipeline_run_id:
        strategy_blockers.append("paper_pipeline_run_missing")
    if paper_armed and bound_pipeline_run_id and bound_pipeline_run_id != authorized_pipeline_run_id:
        strategy_blockers.append("paper_pipeline_run_mismatch")
    if paper_armed and not pipeline_contract_valid:
        strategy_blockers.append("paper_pipeline_contract_invalid")
    if paper_armed and clean_pipeline.get("paper_authorized") is not True:
        strategy_blockers.append("paper_pipeline_not_authorized")

    if not live_wall_enabled or not live_boundary_valid:
        status = "LIVE_TRADING_HARD_WALL_MISSING"
        reason = "Live-trading hard-wall verification failed; all execution is blocked."
    elif read_only or not runtime_contract_valid:
        status = "RUNTIME_READ_ONLY"
        reason = "Runtime is read-only; risk policy may be inspected but paper execution is blocked."
    elif not risk_policy_allows_paper:
        status = "RISK_BLOCK"
        reason = "Risk policy blocks paper execution."
    elif paper_armed and not paper_authorized:
        status = "STRATEGY_AUTHORIZATION_BLOCK"
        reason = "The armed paper strategy is not bound to an authorized pipeline run."
    elif automated_paper_order_allowed:
        status = "PAPER_STRATEGY_READY"
        reason = "Paper runtime, risk policy, account arm state, and pipeline authorization all pass."
    else:
        status = "PAPER_MANUAL_READY"
        reason = "Paper runtime and risk policy pass; automated strategy execution is not armed."

    policy_pretrade = dict(policy.get("pretrade") or {}) if isinstance(policy.get("pretrade"), dict) else {}
    view = dict(policy)
    view.update({
        "status": status,
        "risk_policy_status": str(policy.get("status") or "RISK_SNAPSHOT_ERROR"),
        "risk_policy_allows_paper": risk_policy_allows_paper,
        "risk_policy_reject_reasons": list(policy.get("reject_reasons") or []),
        "runtime_read_only": read_only,
        "runtime_mutations_allowed": runtime_mutations_allowed,
        "paper_armed": paper_armed,
        "paper_authorized": paper_authorized,
        "binding_authorized": binding_authorized,
        "paper_pipeline_run_id": bound_pipeline_run_id,
        "authorized_pipeline_run_id": authorized_pipeline_run_id,
        "strategy_binding_valid": strategy_binding_valid,
        "paper_order_allowed": paper_order_allowed,
        "automated_paper_order_allowed": automated_paper_order_allowed,
        "paper_order_requires_pretrade": True,
        "live_order_allowed": False,
        "reject_reasons": paper_blockers,
        "policy_pretrade": policy_pretrade,
        "pretrade": {
            "status": "PASS" if paper_order_allowed else "BLOCK",
            "paper_allowed": paper_order_allowed,
            "automated_paper_allowed": automated_paper_order_allowed,
            "live_allowed": False,
            "reason": reason,
        },
        "authorization": {
            "status": "PASS" if paper_order_allowed else "BLOCK",
            "risk_policy_allows_paper": risk_policy_allows_paper,
            "runtime_mutations_allowed": runtime_mutations_allowed,
            "paper_order_allowed": paper_order_allowed,
            "paper_order_blockers": list(dict.fromkeys(paper_blockers)),
            "paper_armed": paper_armed,
            "paper_authorized": paper_authorized,
            "binding_authorized": binding_authorized,
            "strategy_binding_valid": strategy_binding_valid,
            "automated_paper_order_allowed": automated_paper_order_allowed,
            "automated_execution_blockers": list(dict.fromkeys(strategy_blockers)),
            "live_order_allowed": False,
        },
    })
    return view


def apply_runtime_pretrade_authorization(
    pretrade_result: Any,
    *,
    runtime_read_only: Any,
) -> dict[str, Any]:
    """Fail closed when a policy-approved request reaches a non-writable runtime."""
    result_contract_valid = isinstance(pretrade_result, dict)
    result = dict(pretrade_result) if result_contract_valid else {
        "allowed": False,
        "paper_order_allowed": False,
        "live_order_allowed": False,
        "status": "BLOCK",
        "reason": "Pretrade result contract is invalid.",
        "reject_reason": "Pretrade result contract is invalid.",
        "checks": [],
    }
    runtime_contract_valid = type(runtime_read_only) is bool
    read_only = runtime_read_only is not False
    runtime_mutations_allowed = runtime_contract_valid and not read_only
    risk_policy_allowed = result_contract_valid and result.get("allowed") is True
    policy_status = str(result.get("status") or "BLOCK")
    checks = [dict(item) for item in result.get("checks") or [] if isinstance(item, dict)]
    add_check(
        checks,
        "runtime_write_authority",
        runtime_mutations_allowed,
        "P0",
        "Runtime mutations must be enabled before a paper order can execute.",
    )

    result.update({
        "risk_policy_allowed": risk_policy_allowed,
        "risk_policy_status": policy_status,
        "runtime_read_only": read_only,
        "runtime_mutations_allowed": runtime_mutations_allowed,
        "checks": checks,
        "live_order_allowed": False,
    })
    if not runtime_mutations_allowed:
        reason = (
            "Runtime read-only contract is invalid; paper execution is blocked."
            if not runtime_contract_valid
            else "Runtime is read-only; paper execution is blocked."
        )
        result.update({
            "allowed": False,
            "paper_order_allowed": False,
            "status": "BLOCK",
            "reason": reason,
            "reject_reason": reason,
        })
    else:
        result["paper_order_allowed"] = (
            risk_policy_allowed
            and str(result.get("mode") or "PAPER").upper() != "LIVE"
        )
    return result


def build_pretrade_check(
    risk: Any,
    symbol: str,
    side: str,
    mode: str,
    notional: float,
    context: Any = None,
) -> dict[str, Any]:
    risk_contract_valid = isinstance(risk, dict)
    risk = risk if isinstance(risk, dict) else {
        "live_trading_hard_block": True,
        "paper_order_allowed": False,
        "status": "RISK_SNAPSHOT_ERROR",
        "checks": [],
        "paper": {},
    }
    context_contract_valid = context is None or isinstance(context, dict)
    context = context if isinstance(context, dict) else {}
    if context.get("_risk_input_context_valid") is False:
        context_contract_valid = False
    clean_symbol = str(symbol or "").upper()
    clean_side = str(side or "").upper()
    clean_mode = str(mode or "PAPER").upper()
    amount = finite_positive(notional)
    order_type = str(context.get("order_type") or "MARKET").upper()
    conditional_order = context.get("conditional_order") is True
    checks: list[dict[str, Any]] = []

    add_check(checks, "risk_snapshot_object", risk_contract_valid, "P0", "Risk snapshot must be an object.")
    add_check(checks, "execution_context_object", context_contract_valid, "P0", "Execution context must be an object.")
    add_check(checks, "symbol_present", bool(clean_symbol), "P0", f"交易标的 {clean_symbol or '--'}")
    add_check(checks, "side_valid", clean_side in VALID_SIDES, "P0", f"订单方向 {clean_side or '--'}")
    add_check(checks, "mode_valid", clean_mode in VALID_MODES, "P0", f"执行模式 {clean_mode or '--'}")

    paper = risk.get("paper") if isinstance(risk.get("paper"), dict) else {}
    position_side, position_side_authoritative = canonicalize_account_context(risk, context)
    direction_mode = str(context.get("direction_mode") or "").upper()
    reduce_only = context.get("reduce_only") is True
    account_symbol = str(context.get("account_symbol") or "").upper()
    account_symbol_authoritative = context.get("account_symbol_authoritative") is True
    position_value = finite_number(context.get("position_value"), math.nan)
    position_value_authoritative = context.get("position_value_authoritative") is True
    account_symbol_matches = account_symbol_authoritative and clean_symbol == account_symbol

    opens_long = False
    opens_short = False
    reduces_long = False
    reduces_short = False
    side_semantics_valid = clean_side in VALID_SIDES
    side_semantics_reason = ""
    if clean_side in {"ARM", "CONDITION"}:
        order_semantics = "CONTROL"
    elif position_side == "FLAT":
        if clean_side == "BUY":
            opens_long = True
            order_semantics = "OPEN_LONG"
        elif clean_side in {"SELL", "SHORT"}:
            opens_short = True
            order_semantics = "OPEN_SHORT"
        else:
            order_semantics = "INVALID"
            side_semantics_valid = False
            side_semantics_reason = f"{clean_side or '--'} cannot reduce a flat account."
    elif position_side == "LONG":
        if clean_side == "BUY":
            opens_long = True
            order_semantics = "ADD_LONG"
        elif clean_side in {"SELL", "CLOSE"}:
            reduces_long = True
            order_semantics = "REDUCE_LONG"
        else:
            order_semantics = "INVALID"
            side_semantics_valid = False
            side_semantics_reason = f"{clean_side or '--'} is invalid while a long position is open."
    elif position_side == "SHORT":
        if clean_side in {"SELL", "SHORT"}:
            opens_short = True
            order_semantics = "ADD_SHORT"
        elif clean_side in {"BUY", "COVER", "CLOSE"}:
            reduces_short = True
            order_semantics = "REDUCE_SHORT"
        else:
            order_semantics = "INVALID"
            side_semantics_valid = False
            side_semantics_reason = f"{clean_side or '--'} is invalid while a short position is open."
    else:
        order_semantics = "INVALID"
        side_semantics_valid = False
        side_semantics_reason = "Authoritative position side is invalid."

    reduction_candidate = reduces_long or reduces_short
    reduction_cap = (
        position_value + max(0.05, position_value * 0.001)
        if position_value_authoritative and position_value >= 0
        else 0.0
    )
    if reduction_candidate and not account_symbol_matches:
        side_semantics_valid = False
        side_semantics_reason = "Reduction symbol does not match the authoritative account position."
    elif reduction_candidate and (not position_value_authoritative or position_value <= 0):
        side_semantics_valid = False
        side_semantics_reason = "Authoritative reducible position value is unavailable."
    elif reduction_candidate and amount > reduction_cap:
        side_semantics_valid = False
        side_semantics_reason = (
            f"Reduction notional {amount:.2f} exceeds authoritative position value {position_value:.2f}."
        )

    is_reduce_side = reduction_candidate and side_semantics_valid
    is_entry_side = (opens_long or opens_short) and side_semantics_valid
    risk_increasing = (
        is_entry_side or clean_side in {"ARM", "CONDITION"}
    ) and not is_reduce_side and not reduce_only
    context["account_symbol_matches"] = account_symbol_matches
    context["order_semantics"] = order_semantics
    context["side_semantics_valid"] = side_semantics_valid
    context["risk_reducing_authoritative"] = is_reduce_side
    context["reducible_notional"] = round(max(position_value, 0.0), 2) if position_value_authoritative else 0.0
    account_context_mismatches = list(context.get("account_context_mismatches") or [])
    execution_boolean_errors = [
        f"{field}:expected_boolean"
        for field in ("reduce_only", "conditional_order")
        if field in context and type(context.get(field)) is not bool
    ]
    add_check(
        checks,
        "execution_boolean_contract",
        not execution_boolean_errors,
        "P0",
        (
            "Execution boolean fields are valid."
            if not execution_boolean_errors
            else "Malformed execution boolean fields: " + ", ".join(execution_boolean_errors)
        ),
        blocking=bool(execution_boolean_errors),
    )
    add_check(
        checks,
        "account_context_collection_contract",
        context.get("account_context_mismatches_contract_valid") is True,
        "P0",
        "Account-context mismatch evidence must be a list.",
    )
    add_check(
        checks,
        "account_symbol_binding",
        account_symbol_authoritative and (position_side == "FLAT" or account_symbol_matches),
        "P0",
        (
            f"Authoritative account symbol {account_symbol or '--'} matches {clean_symbol or '--'}."
            if account_symbol_authoritative and (position_side == "FLAT" or account_symbol_matches)
            else f"Requested symbol {clean_symbol or '--'} does not match authoritative account symbol {account_symbol or '--'}."
        ),
    )
    add_check(
        checks,
        "position_value_authority",
        position_value_authoritative and (
            (position_side == "FLAT" and position_value <= 0.05)
            or (position_side in {"LONG", "SHORT"} and position_value > 0)
        ),
        "P0",
        "Authoritative position value is finite and consistent with the position side.",
    )
    add_check(
        checks,
        "side_interpretation",
        side_semantics_valid,
        "P0" if not side_semantics_valid else "P1",
        side_semantics_reason or f"Order semantics: {order_semantics}.",
        blocking=not side_semantics_valid,
    )

    direction_mode_authoritative = context.get("direction_mode_authoritative") is True
    leverage_authoritative = context.get("leverage_authoritative") is True
    reduce_only_authoritative = context.get("reduce_only_authoritative") is True
    unavailable_account_fields = [
        field
        for field, available in (
            ("position_side", position_side_authoritative),
            ("direction_mode", direction_mode_authoritative),
            ("leverage", leverage_authoritative),
            ("reduce_only", reduce_only_authoritative),
        )
        if not available
    ]
    if not position_side_authoritative:
        add_check(
            checks,
            "account_context_consistency",
            False,
            "P0",
            "Authoritative account position side is unavailable.",
        )
    elif unavailable_account_fields:
        add_check(
            checks,
            "account_context_consistency",
            False,
            "P0" if not is_reduce_side else "P1",
            "Authoritative account fields are unavailable: " + ", ".join(unavailable_account_fields) + ".",
            blocking=not is_reduce_side,
        )
    elif account_context_mismatches:
        add_check(
            checks,
            "account_context_consistency",
            False,
            "P0" if not is_reduce_side else "P1",
            "Caller account context differed from the authoritative account snapshot.",
            blocking=not is_reduce_side,
        )
    else:
        add_check(
            checks,
            "account_context_consistency",
            True,
            "P1",
            f"Authoritative account profile: {position_side} / {direction_mode} / {context.get('leverage')}x.",
            blocking=False,
        )

    snapshot_boolean_errors = [
        f"{field}:expected_boolean"
        for field in ("live_trading_hard_block", "paper_order_allowed", "live_order_allowed")
        if field not in risk or type(risk.get(field)) is not bool
    ]
    add_check(
        checks,
        "risk_snapshot_boolean_contract",
        not snapshot_boolean_errors,
        "P0",
        (
            "Risk snapshot boolean fields are valid."
            if not snapshot_boolean_errors
            else "Malformed risk snapshot boolean fields: " + ", ".join(snapshot_boolean_errors)
        ),
        blocking=bool(snapshot_boolean_errors),
    )
    raw_snapshot_checks = risk.get("checks")
    snapshot_checks_contract_valid = isinstance(raw_snapshot_checks, list) and all(
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and type(item.get("ok")) is bool
        and type(item.get("blocking")) is bool
        for item in (raw_snapshot_checks if isinstance(raw_snapshot_checks, list) else [])
    )
    snapshot_checks = raw_snapshot_checks if snapshot_checks_contract_valid else []
    snapshot_blockers = blocking_messages(snapshot_checks)
    risk_allows_paper = risk.get("paper_order_allowed") is True
    snapshot_status = str(risk.get("status") or "").upper()
    snapshot_consistent = snapshot_checks_contract_valid and not (
        risk_allows_paper and (
            snapshot_blockers
            or snapshot_status != "BLOCK_LIVE_READY_PAPER"
            or risk.get("live_order_allowed") is not False
        )
    )
    add_check(
        checks,
        "risk_snapshot_checks_contract",
        snapshot_checks_contract_valid,
        "P0",
        "Risk snapshot checks must be a structured list with native boolean semantics.",
    )
    add_check(
        checks,
        "risk_snapshot_consistency",
        snapshot_consistent,
        "P0",
        "Risk snapshot authorization is consistent with its status and blocking checks.",
    )
    raw_snapshot_updated_at = risk.get("updated_at")
    snapshot_timestamp_valid = (
        isinstance(raw_snapshot_updated_at, int)
        and not isinstance(raw_snapshot_updated_at, bool)
        and raw_snapshot_updated_at > 0
    )
    add_check(
        checks,
        "risk_snapshot_timestamp_contract",
        snapshot_timestamp_valid,
        "P0",
        "Risk snapshot updated_at must be a positive native integer timestamp.",
    )
    snapshot_fresh = context.get("risk_snapshot_fresh", True)
    snapshot_fresh_contract_valid = type(snapshot_fresh) is bool
    add_check(
        checks,
        "risk_snapshot_freshness",
        snapshot_fresh_contract_valid and snapshot_fresh is True,
        "P0",
        (
            f"Risk snapshot age {context.get('risk_snapshot_age_ms')}ms is within the execution window."
            if snapshot_fresh_contract_valid and snapshot_fresh is True
            else "Risk snapshot is stale, from the future, or has an invalid freshness contract."
        ),
    )
    live_block = risk.get("live_trading_hard_block") is True
    if clean_mode == "LIVE":
        add_check(checks, "live_mode_blocked", False, "P0", "实盘硬墙已开启，当前系统不允许真实下单")
    else:
        add_check(checks, "live_mode_blocked", live_block, "P0", "非实盘路径，真实下单保持阻断")

    snapshot_allows_paper = risk_allows_paper or is_reduce_side
    if risk_allows_paper:
        snapshot_message = "影子风控允许模拟执行"
    elif is_reduce_side:
        snapshot_message = "风控阻断中，但减仓/平仓仍允许"
    else:
        snapshot_message = "影子风控当前阻断新增风险"
    add_check(checks, "risk_snapshot_allows_paper", snapshot_allows_paper, "P0", snapshot_message)
    add_check(checks, "notional_positive", amount > 0, "P0", f"订单名义金额 {amount:.2f}")
    if order_type in PERSISTENT_PAPER_ORDER_TYPES:
        add_check(
            checks,
            "paper_order_contract",
            False,
            "P0",
            f"{order_type} requires a persistent matcher and settlement callback, which are not enabled.",
        )
    elif order_type in CONDITIONAL_PAPER_ORDER_TYPES and not (conditional_order or clean_side == "CONDITION"):
        add_check(checks, "paper_order_contract", False, "P0", "OCO is only valid for a conditional paper order.")
    elif order_type not in IMMEDIATE_PAPER_ORDER_TYPES | CONDITIONAL_PAPER_ORDER_TYPES:
        add_check(checks, "paper_order_contract", False, "P0", f"Unsupported paper order type: {order_type or '--'}.")
    else:
        add_check(checks, "paper_order_contract", True, "P1", f"Paper execution contract: {order_type}.", blocking=False)

    equity = finite_positive(paper.get("equity"))
    leverage = max(finite_positive(context.get("leverage")) or 1.0, 1.0)
    if clean_side == "ARM":
        requested_arm_leverage = (
            finite_positive(context.get("requested_leverage"))
            if "requested_leverage" in context
            else leverage
        )
        requested_arm_direction = str(
            context.get("requested_direction_mode")
            if "requested_direction_mode" in context
            else direction_mode
        ).upper()
        add_check(checks, "paper_arm_order_type", order_type == "CURRENT", "P0", "Automated paper strategy requires CURRENT execution.")
        add_check(checks, "paper_arm_leverage", abs(requested_arm_leverage - 1.0) <= 1e-9, "P0", "Automated paper strategy requires 1x cash exposure.")
        add_check(checks, "paper_arm_direction", requested_arm_direction == "LONG_ONLY", "P0", "Automated paper strategy currently supports LONG_ONLY only.")
    max_single_order = equity * leverage if equity > 0 else 0.0
    if is_reduce_side:
        add_check(checks, "single_order_notional", True, "P1", "减仓/平仓不受开仓名义上限阻断", blocking=False)
    elif max_single_order > 0 and amount > 0:
        add_check(checks, "single_order_notional", amount <= max_single_order * 1.02, "P0", f"单笔名义 {amount:.2f} / 上限 {max_single_order:.2f}")
    else:
        add_check(checks, "single_order_notional", True, "P1", "账户权益不足时只做基础名义金额校验", blocking=False)

    if reduce_only and not is_reduce_side and clean_side not in {"ARM", "CONDITION"}:
        add_check(checks, "reduce_only_position", False, "P0", "只减仓模式下没有可减持仓")
    elif direction_mode == "LONG_ONLY" and opens_short:
        add_check(checks, "direction_mode", False, "P0", "只做多模式禁止开空")
    elif direction_mode == "SHORT_ONLY" and opens_long:
        add_check(checks, "direction_mode", False, "P0", "只做空模式下 BUY 只能用于平空")
    else:
        add_check(checks, "direction_mode", True, "P1", f"方向模式 {direction_mode or '--'} / 当前持仓 {position_side or '--'}", blocking=False)
    data_quality = context.get("data_quality") if isinstance(context.get("data_quality"), dict) else {}
    data_status = str(context.get("data_status") or data_quality.get("status") or "UNKNOWN").upper()
    data_quarantined, quarantined_errors = resolve_boolean_sources(
        ("context.data_quarantined", context, "data_quarantined"),
        ("data_quality.quarantined", data_quality, "quarantined"),
    )
    data_fallback, fallback_errors = resolve_boolean_sources(
        ("context.data_fallback", context, "data_fallback"),
        ("data_quality.fallback", data_quality, "fallback"),
    )
    data_realtime, realtime_errors = resolve_boolean_sources(
        ("context.data_realtime", context, "data_realtime"),
        ("data_quality.realtime", data_quality, "realtime"),
    )
    data_historical, historical_errors = resolve_boolean_sources(
        ("context.data_historical", context, "data_historical"),
        ("data_quality.historical", data_quality, "historical"),
    )
    data_attested, attested_errors = resolve_boolean_sources(
        ("context.data_attested", context, "data_attested"),
        ("data_quality.attested", data_quality, "attested"),
    )
    quality_allows_entry, entry_errors = resolve_boolean_sources(
        ("data_quality.can_increase_risk", data_quality, "can_increase_risk"),
    )
    quality_allows_simulation, simulation_errors = resolve_boolean_sources(
        ("data_quality.can_simulate", data_quality, "can_simulate"),
    )
    data_boolean_errors = [
        *quarantined_errors,
        *fallback_errors,
        *realtime_errors,
        *historical_errors,
        *attested_errors,
        *entry_errors,
        *simulation_errors,
    ]
    quality_reasons, quality_reasons_valid = normalized_string_list(data_quality.get("blocking_reasons", []))
    reconciliation_required = context.get("ledger_reconciliation_required") is True
    raw_pending_settlements = context.get("ledger_pending_settlements", 0)
    pending_settlements = (
        raw_pending_settlements
        if isinstance(raw_pending_settlements, int)
        and not isinstance(raw_pending_settlements, bool)
        and raw_pending_settlements >= 0
        else 0
    )

    add_check(
        checks,
        "market_data_boolean_contract",
        not data_boolean_errors,
        "P0" if data_boolean_errors and risk_increasing else "P1",
        (
            "Market-data boolean fields are valid."
            if not data_boolean_errors
            else "Malformed or conflicting market-data boolean fields: " + ", ".join(data_boolean_errors)
        ),
        blocking=bool(data_boolean_errors and risk_increasing),
    )
    add_check(
        checks,
        "market_data_collection_contract",
        quality_reasons_valid,
        "P0" if not quality_reasons_valid and risk_increasing else "P1",
        "Market-data blocking reasons must be a list.",
        blocking=bool(not quality_reasons_valid and risk_increasing),
    )
    ledger_boolean_valid = (
        "ledger_reconciliation_required" not in context
        or type(context.get("ledger_reconciliation_required")) is bool
    )
    ledger_pending_valid = "ledger_pending_settlements" not in context or (
        isinstance(context.get("ledger_pending_settlements"), int)
        and not isinstance(context.get("ledger_pending_settlements"), bool)
        and context.get("ledger_pending_settlements") >= 0
    )
    add_check(
        checks,
        "paper_ledger_context_contract",
        ledger_boolean_valid and ledger_pending_valid,
        "P0",
        "Paper-ledger reconciliation fields must have native boolean and finite numeric types.",
    )

    if reconciliation_required:
        add_check(
            checks,
            "paper_ledger_reconciled",
            False,
            "P0",
            f"模拟账本存在 {pending_settlements} 笔未结算成交，完成对账前禁止任何新模拟成交",
        )
    else:
        add_check(
            checks,
            "paper_ledger_reconciled",
            True,
            "P1",
            "模拟账本已对账",
            blocking=False,
        )

    if is_reduce_side or reduce_only:
        add_check(
            checks,
            "market_data_quality",
            True,
            "P1",
            f"行情状态 {data_status}；减仓、平仓和撤单保持可用",
            blocking=False,
        )
    elif risk_increasing and data_quarantined:
        add_check(
            checks,
            "market_data_quality",
            False,
            "P0",
            "行情数据已隔离，禁止增加模拟风险" + (f"：{' / '.join(quality_reasons)}" if quality_reasons else ""),
        )
    elif clean_mode == "SIMULATION" and risk_increasing:
        simulation_ready = bool(
            quality_allows_simulation
            and data_historical
            and data_attested
            and data_status in HISTORICAL_SIMULATION_STATUSES
            and not data_fallback
        )
        add_check(
            checks,
            "market_data_quality",
            simulation_ready,
            "P0" if not simulation_ready else "P1",
            (
                f"历史回放行情状态 {data_status}，冻结数据合同与来源证明通过"
                if simulation_ready
                else f"历史回放行情状态 {data_status} 不满足冻结、来源证明和可模拟合同，禁止增加模拟风险"
                + (f"：{' / '.join(quality_reasons)}" if quality_reasons else "")
            ),
            blocking=not simulation_ready,
        )
    elif risk_increasing and (
        not quality_allows_entry
        or data_status not in {"READY", "FRESH", "LIVE", "OK"}
        or data_fallback
        or not data_realtime
    ):
        add_check(
            checks,
            "market_data_quality",
            False,
            "P0",
            f"行情状态 {data_status} 不满足开仓要求，禁止增加模拟风险"
            + (f"：{' / '.join(quality_reasons)}" if quality_reasons else ""),
        )
    else:
        add_check(
            checks,
            "market_data_quality",
            True,
            "P1",
            f"行情状态 {data_status}，实时质量门禁通过",
            blocking=False,
        )

    daily_loss_fields_valid = True
    for field in ("daily_loss_pct", "max_daily_loss_pct"):
        if field not in context:
            continue
        value = context.get(field)
        parsed = finite_number(value, math.nan)
        if isinstance(value, bool) or not math.isfinite(parsed) or parsed < 0:
            daily_loss_fields_valid = False
    add_check(
        checks,
        "daily_loss_context_contract",
        daily_loss_fields_valid,
        "P0" if not daily_loss_fields_valid and risk_increasing else "P1",
        "Daily-loss fields must be finite non-negative numbers.",
        blocking=bool(not daily_loss_fields_valid and risk_increasing),
    )
    daily_loss_pct = max(finite_number(context.get("daily_loss_pct")), 0.0)
    max_daily_loss_pct = max(finite_number(context.get("max_daily_loss_pct")), 0.0)
    if max_daily_loss_pct > 0:
        add_check(
            checks,
            "daily_loss_limit",
            daily_loss_pct < max_daily_loss_pct or is_reduce_side,
            "P0",
            f"Daily loss {daily_loss_pct:.2f}% / limit {max_daily_loss_pct:.2f}%.",
        )

    portfolio_risk = context.get("portfolio_risk") if isinstance(context.get("portfolio_risk"), dict) else {}
    portfolio_required = context.get("portfolio_risk_required") is True
    portfolio_required_valid = (
        "portfolio_risk_required" not in context
        or type(context.get("portfolio_risk_required")) is bool
    )
    portfolio_gate_valid = (
        not portfolio_risk
        or type(portfolio_risk.get("portfolio_gate_passed")) is bool
    )
    portfolio_reasons, portfolio_reasons_valid = normalized_string_list(
        portfolio_risk.get("reject_reasons", [])
    )
    portfolio_boolean_valid = portfolio_required_valid and portfolio_gate_valid
    add_check(
        checks,
        "portfolio_risk_boolean_contract",
        portfolio_boolean_valid,
        "P0" if not portfolio_boolean_valid and risk_increasing else "P1",
        (
            "Portfolio-risk boolean fields are valid."
            if portfolio_boolean_valid
            else "Portfolio-risk authorization fields must be native booleans."
        ),
        blocking=bool(not portfolio_boolean_valid and risk_increasing),
    )
    add_check(
        checks,
        "portfolio_risk_collection_contract",
        portfolio_reasons_valid,
        "P0" if not portfolio_reasons_valid and risk_increasing else "P1",
        "Portfolio-risk reject reasons must be a list.",
        blocking=bool(not portfolio_reasons_valid and risk_increasing),
    )
    if is_reduce_side or reduce_only:
        add_check(
            checks,
            "portfolio_risk_budget",
            True,
            "P1",
            "组合风险超限时仍保留减仓和平仓路径",
            blocking=False,
        )
    elif risk_increasing and portfolio_risk:
        portfolio_passed = (
            portfolio_risk.get("status") == "PASS"
            and portfolio_risk.get("portfolio_gate_passed") is True
        )
        add_check(
            checks,
            "portfolio_risk_budget",
            portfolio_passed,
            "P0",
            "组合敞口、集中度和相关性门禁通过"
            if portfolio_passed
            else "组合风险预算阻断" + (f"：{' / '.join(portfolio_reasons)}" if portfolio_reasons else ""),
        )
    elif risk_increasing and portfolio_required:
        add_check(checks, "portfolio_risk_budget", False, "P0", "组合风险预算不可用，禁止增加模拟风险")
    else:
        add_check(
            checks,
            "portfolio_risk_budget",
            True,
            "P1",
            "当前调用未要求组合风险预算",
            blocking=False,
        )

    reject_reasons = blocking_messages(checks)
    allowed = not reject_reasons
    reason = "风控通过：仅允许模拟盘验证" if allowed else " / ".join(reject_reasons)
    return {
        "allowed": allowed,
        "status": "PASS" if allowed else "BLOCK",
        "reason": reason,
        "reject_reason": reason if not allowed else "",
        "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
        "checks": checks,
        "risk": risk,
        "symbol": clean_symbol,
        "side": clean_side,
        "mode": clean_mode,
        "notional": round(amount, 2),
        "live_order_allowed": False,
        "paper_order_allowed": allowed and clean_mode != "LIVE",
        "context": context,
    }


class RiskService:
    """Single pre-trade gateway for manual, strategy, and conditional requests."""

    def __init__(
        self,
        *,
        snapshot_provider: Callable[[float], dict[str, Any]],
        now_ms: Callable[[], int],
        audit_writer: AuditWriter | None = None,
        data_context_provider: DataContextProvider | None = None,
        portfolio_context_provider: PortfolioContextProvider | None = None,
    ) -> None:
        self.snapshot_provider = snapshot_provider
        self.now_ms = now_ms
        self.audit_writer = audit_writer
        self.data_context_provider = data_context_provider
        self.portfolio_context_provider = portfolio_context_provider
        self._lock = threading.RLock()
        self._sequence = 0

    def _request_id(self) -> str:
        with self._lock:
            self._sequence += 1
            return f"risk-{self.now_ms()}-{self._sequence:06d}"

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        mode: str,
        notional: float,
        price: float = 0.0,
        context: Any = None,
    ) -> dict[str, Any]:
        request_id = self._request_id()
        context_contract_valid = context is None or isinstance(context, dict)
        clean_context = dict(context) if isinstance(context, dict) else {}
        clean_context["_risk_input_context_valid"] = context_contract_valid
        clean_context.setdefault("source", "unknown")
        clean_context.setdefault("request_id", request_id)
        safe_price = finite_positive(price)
        safe_notional = finite_positive(notional)
        if self.data_context_provider:
            requested_market_context = {
                key: clean_context.get(key)
                for key in AUTHORITATIVE_MARKET_CONTEXT_KEYS
                if key in clean_context
            }
            if requested_market_context:
                clean_context["requested_market_context"] = requested_market_context
            for key in AUTHORITATIVE_MARKET_CONTEXT_KEYS:
                clean_context.pop(key, None)
            try:
                market_context = self.data_context_provider(str(symbol or "").upper(), safe_price, clean_context)
                market_contract_errors = validate_market_context_contract(market_context)
                if market_contract_errors:
                    raise ValueError("market_context_contract:" + ",".join(market_contract_errors))
            except Exception as exc:
                clean_context["market_context_error"] = f"{type(exc).__name__}: {exc}"
                market_context = fallback_market_context(f"行情质量门禁读取失败：{exc}")
            for key in AUTHORITATIVE_MARKET_CONTEXT_KEYS:
                clean_context[key] = market_context[key]
        try:
            risk = self.snapshot_provider(safe_price)
            if not isinstance(risk, dict):
                raise TypeError("risk snapshot provider returned a non-object value")
        except Exception as exc:
            clean_context["risk_snapshot_error"] = f"{type(exc).__name__}: {exc}"
            risk = {
                "live_trading_hard_block": True,
                "paper_order_allowed": False,
                "status": "RISK_SNAPSHOT_ERROR",
                "checks": [],
                "paper": {},
            }
        snapshot_observed_at = self.now_ms()
        snapshot_updated_at = risk.get("updated_at")
        snapshot_timestamp_valid = (
            isinstance(snapshot_updated_at, int)
            and not isinstance(snapshot_updated_at, bool)
            and snapshot_updated_at > 0
        )
        snapshot_age_ms = snapshot_observed_at - snapshot_updated_at if snapshot_timestamp_valid else None
        clean_context["risk_snapshot_age_ms"] = snapshot_age_ms
        clean_context["risk_snapshot_fresh"] = bool(
            snapshot_timestamp_valid
            and snapshot_age_ms is not None
            and -MAX_RISK_SNAPSHOT_FUTURE_SKEW_MS <= snapshot_age_ms <= MAX_RISK_SNAPSHOT_AGE_MS
        )
        canonicalize_account_context(risk, clean_context)
        if self.portfolio_context_provider:
            clean_context["portfolio_risk_required"] = True
            try:
                portfolio_context = self.portfolio_context_provider(
                    risk,
                    str(symbol or "").upper(),
                    str(side or "").upper(),
                    safe_notional,
                    safe_price,
                    clean_context,
                )
                if not isinstance(portfolio_context, dict):
                    raise TypeError("portfolio context provider returned a non-object value")
                clean_context["portfolio_risk"] = portfolio_context
            except Exception as exc:
                clean_context["portfolio_risk"] = {
                    "status": "BLOCK",
                    "portfolio_gate_passed": False,
                    "reject_reasons": [f"组合风险预算读取失败：{exc}"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
        result = build_pretrade_check(risk, symbol, side, mode, safe_notional, clean_context)
        result.update({
            "request_id": request_id,
            "checked_at": self.now_ms(),
            "requested_price": round(safe_price, 8),
            "source": clean_context.get("source"),
            "strategy_id": clean_context.get("strategy_id"),
            "run_id": clean_context.get("run_id"),
        })
        if self.audit_writer and clean_context.get("audit_event", True) is not False:
            audit_event = {
                "type": "risk_pretrade_pass" if result.get("allowed") else "risk_pretrade_block",
                "request_id": request_id,
                "symbol": result.get("symbol"),
                "side": result.get("side"),
                "mode": result.get("mode"),
                "notional": result.get("notional"),
                "source": clean_context.get("source"),
                "strategy_id": clean_context.get("strategy_id"),
                "run_id": clean_context.get("run_id"),
                "market_snapshot_id": clean_context.get("market_snapshot_id"),
                "signal_id": clean_context.get("signal_id"),
                "signal_action": clean_context.get("signal_action"),
                "signal_reason": clean_context.get("signal_reason"),
                "authoritative_price": clean_context.get("authoritative_price"),
                "price_deviation_pct": clean_context.get("price_deviation_pct"),
                "idempotency_key": clean_context.get("idempotency_key"),
                "data_quality": clean_context.get("data_quality", {}),
                "account_context_mismatches": clean_context.get("account_context_mismatches", []),
                "portfolio_risk": clean_context.get("portfolio_risk", {}),
                "status": result.get("status"),
                "reason": result.get("reason"),
                "checks": result.get("checks", []),
            }
            try:
                self.audit_writer(audit_event)
                clean_context["risk_audit_status"] = "PASS"
            except Exception as exc:
                clean_context["risk_audit_status"] = "FAILED"
                clean_context["risk_audit_error"] = f"{type(exc).__name__}: {exc}"
                risk_reducing = clean_context.get("risk_reducing_authoritative") is True
                add_check(
                    result["checks"],
                    "risk_audit_persistence",
                    False,
                    "P0",
                    "Risk audit persistence failed.",
                    blocking=not risk_reducing,
                )
                reject_reasons = blocking_messages(result["checks"])
                result["allowed"] = not reject_reasons
                result["status"] = "BLOCK" if reject_reasons else "WATCH"
                result["reason"] = (
                    " / ".join(reject_reasons)
                    if reject_reasons
                    else "Risk audit is unavailable; only risk reduction remains permitted."
                )
                result["reject_reason"] = result["reason"] if reject_reasons else ""
                result["paper_order_allowed"] = result["allowed"] is True and str(mode or "PAPER").upper() != "LIVE"
        return result
