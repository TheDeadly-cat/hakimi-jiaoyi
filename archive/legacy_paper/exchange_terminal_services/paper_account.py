from __future__ import annotations

import copy
import functools
import inspect
import math
import threading
from pathlib import Path
from typing import Any, Callable

try:
    from services.paper_executor import ORDER_TYPES, PERSISTENT_ORDER_TYPES
    from services.event_lineage import build_signal_context
    from services.paper_strategy_clock import PAPER_STRATEGY_CLOCK_VERSION, paper_clock_transition
    from utils import choice, clamp, now_ms
except ModuleNotFoundError:
    try:
        from .paper_executor import ORDER_TYPES, PERSISTENT_ORDER_TYPES
        from .event_lineage import build_signal_context
        from .paper_strategy_clock import PAPER_STRATEGY_CLOCK_VERSION, paper_clock_transition
        from ..utils import choice, clamp, now_ms
    except ImportError:
        from exchange_terminal.services.paper_executor import ORDER_TYPES, PERSISTENT_ORDER_TYPES
        from exchange_terminal.services.event_lineage import build_signal_context
        from exchange_terminal.services.paper_strategy_clock import PAPER_STRATEGY_CLOCK_VERSION, paper_clock_transition
        from exchange_terminal.utils import choice, clamp, now_ms

_RUNTIME: dict[str, Any] = {}
STATE_FILE: Path | str | None = None


def _strict_finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _strict_quantity_pct(value: Any) -> float | None:
    parsed = _strict_finite_number(value)
    return parsed if parsed is not None and 0 < parsed <= 100 else None


def _strict_boolean_option(options: dict[str, Any], key: str, default: bool) -> bool:
    if key not in options:
        return default
    value = options.get(key)
    if type(value) is not bool:
        raise ValueError(f"paper_boolean_option_invalid:{key}")
    return value


def configure_paper_account_runtime(
    *,
    state_file: Path | str,
    write_json: Callable[[Path | str, dict[str, Any]], None],
    append_ledger: Callable[[dict[str, Any]], None],
    choose_strategy: Callable[[str], dict[str, Any]],
    trade_direction_from_mode: Callable[[str], str],
    analyze_strategy_context: Callable[..., dict[str, Any]],
    evaluate_directional_strategy_signal: Callable[..., dict[str, Any]],
    risk_pretrade_check: Callable[..., dict[str, Any]],
    execute_paper_order: Callable[..., dict[str, Any]],
    persist_state: Callable[..., Any] | None = None,
    order_applied: Callable[[str], bool] | None = None,
) -> None:
    global STATE_FILE
    STATE_FILE = state_file
    persist_state_accepts_applied_ids = True
    if callable(persist_state):
        try:
            inspect.signature(persist_state).bind({}, "state_update", [])
        except TypeError:
            persist_state_accepts_applied_ids = False
        except (ValueError, AttributeError):
            persist_state_accepts_applied_ids = True
    _RUNTIME.update({
        "write_json": write_json,
        "append_ledger": append_ledger,
        "choose_strategy": choose_strategy,
        "trade_direction_from_mode": trade_direction_from_mode,
        "analyze_strategy_context": analyze_strategy_context,
        "evaluate_directional_strategy_signal": evaluate_directional_strategy_signal,
        "risk_pretrade_check": risk_pretrade_check,
        "execute_paper_order": execute_paper_order,
        "persist_state": persist_state,
        "persist_state_accepts_applied_ids": persist_state_accepts_applied_ids,
        "order_applied": order_applied,
    })


def _runtime_call(name: str, *args: Any, **kwargs: Any) -> Any:
    func = _RUNTIME.get(name)
    if not callable(func):
        raise RuntimeError(f"PaperAccount runtime callback is not configured: {name}")
    return func(*args, **kwargs)


def write_json(path: Path | str | None, payload: dict[str, Any]) -> None:
    if path is None:
        raise RuntimeError("PaperAccount state file is not configured")
    _runtime_call("write_json", path, payload)


def append_ledger(event: dict[str, Any]) -> None:
    _runtime_call("append_ledger", event)


def choose_strategy(strategy_id: str) -> dict[str, Any]:
    return _runtime_call("choose_strategy", strategy_id)


def trade_direction_from_mode(value: str) -> str:
    return _runtime_call("trade_direction_from_mode", value)


def analyze_strategy_context(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_call("analyze_strategy_context", *args, **kwargs)


def evaluate_directional_strategy_signal(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_call("evaluate_directional_strategy_signal", *args, **kwargs)


def risk_pretrade_check(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_call("risk_pretrade_check", *args, **kwargs)


def execute_paper_order(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _runtime_call("execute_paper_order", *args, **kwargs)


def execution_lineage(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": str(report.get("order_id") or ""),
        "signal_id": str(report.get("signal_id") or ""),
        "risk_request_id": str(report.get("risk_request_id") or ""),
        "market_snapshot_id": str(report.get("market_snapshot_id") or ""),
        "idempotency_key": str(report.get("idempotency_key") or ""),
    }


NO_FILL_EXECUTION_STATES = {
    "REJECTED",
    "MAKER_WAIT",
    "WAITING_LIMIT",
    "IOC_CANCELLED",
    "CANCELLED",
    "EXPIRED",
}
MAX_PRETRADE_RESULT_AGE_MS = 15_000


def execution_report_has_fill(report: dict[str, Any]) -> bool:
    status = str(report.get("status") or "").upper()
    avg_price = _strict_finite_number(report.get("avg_price"))
    filled_qty = _strict_finite_number(report.get("filled_qty"))
    filled_notional = _strict_finite_number(report.get("filled_notional"))
    return (
        status not in NO_FILL_EXECUTION_STATES
        and avg_price is not None
        and filled_qty is not None
        and filled_notional is not None
        and avg_price > 0
        and filled_qty > 0
        and filled_notional > 0
    )


def execution_report_contract_errors(
    report: Any,
    *,
    symbol: str,
    side: str,
    order_type: str,
    mark_price: float,
    notional: float,
    limit_price: float,
    requested_qty: float,
    reduce_only: bool,
    idempotency_key: str,
    risk_check: dict[str, Any],
) -> list[str]:
    if not isinstance(report, dict):
        return ["execution_report_object_required"]
    errors: list[str] = []

    def numeric(field: str, *, nonnegative: bool = True) -> float | None:
        value = _strict_finite_number(report.get(field))
        if value is None or (nonnegative and value < 0):
            errors.append(f"execution_{field}_invalid")
            return None
        return value

    order_id = report.get("order_id")
    if not isinstance(order_id, str) or not order_id.strip():
        errors.append("execution_order_id_invalid")
    if str(report.get("symbol") or "").upper() != str(symbol or "").upper():
        errors.append("execution_symbol_mismatch")
    if str(report.get("side") or "").upper() != str(side or "").upper():
        errors.append("execution_side_mismatch")
    if str(report.get("order_type") or "").upper() != str(order_type or "").upper():
        errors.append("execution_order_type_mismatch")
    if type(report.get("reduce_only")) is not bool or report.get("reduce_only") is not reduce_only:
        errors.append("execution_reduce_only_mismatch")
    expected_quantity_constrained = requested_qty > 0
    if (
        type(report.get("quantity_constrained")) is not bool
        or report.get("quantity_constrained") is not expected_quantity_constrained
    ):
        errors.append("execution_quantity_semantics_mismatch")
    if type(report.get("idempotent_replay")) is not bool:
        errors.append("execution_replay_contract_invalid")
    if str(report.get("persistence_status") or "").upper() != "PERSISTED":
        errors.append("execution_not_durable")

    risk_request_id = str(risk_check.get("request_id") or "")
    if not risk_request_id or str(report.get("risk_request_id") or "") != risk_request_id:
        errors.append("execution_risk_request_mismatch")
    if str(report.get("idempotency_key") or "") != str(idempotency_key or ""):
        errors.append("execution_idempotency_key_mismatch")

    report_mark_price = numeric("mark_price")
    report_limit_price = numeric("limit_price")
    report_requested_notional = numeric("requested_notional")
    report_requested_qty = numeric("requested_qty")
    avg_price = numeric("avg_price")
    filled_qty = numeric("filled_qty")
    filled_notional = numeric("filled_notional")
    fee = numeric("fee")
    funding_charged = numeric("funding_charged", nonnegative=False)
    del fee, funding_charged

    comparisons = (
        (report_mark_price, mark_price, 1e-8, "execution_mark_price_mismatch"),
        (report_limit_price, limit_price, 1e-8, "execution_limit_price_mismatch"),
        (report_requested_notional, notional, 0.01, "execution_requested_notional_mismatch"),
        (report_requested_qty, requested_qty, 1e-8, "execution_requested_qty_mismatch"),
    )
    for actual, expected, tolerance, error in comparisons:
        if actual is not None and abs(actual - float(expected)) > tolerance:
            errors.append(error)

    if avg_price is not None and filled_qty is not None and filled_notional is not None:
        calculated_notional = avg_price * filled_qty
        arithmetic_tolerance = max(0.05, calculated_notional * 1e-5)
        if filled_qty > 0 and (
            avg_price <= 0
            or filled_notional <= 0
            or abs(filled_notional - calculated_notional) > arithmetic_tolerance
        ):
            errors.append("execution_fill_arithmetic_mismatch")
        if filled_notional > float(notional) + 0.01:
            errors.append("execution_notional_budget_exceeded")
        if requested_qty > 0 and filled_qty > requested_qty + 1e-8:
            errors.append("execution_quantity_budget_exceeded")

    status = str(report.get("status") or "").upper()
    lifecycle_state = str(report.get("lifecycle_state") or "").upper()
    if filled_qty is not None and filled_qty > 0:
        if status not in {"FILLED", "PARTIAL", "IOC_PARTIAL_CANCEL"}:
            errors.append("execution_fill_status_mismatch")
        if lifecycle_state not in {"FILLED", "CANCELLED"}:
            errors.append("execution_lifecycle_fill_mismatch")
    elif status in {"FILLED", "PARTIAL", "IOC_PARTIAL_CANCEL"}:
        errors.append("execution_fill_missing")
    return list(dict.fromkeys(errors))


def execution_funding_charged(report: dict[str, Any]) -> float:
    value = _strict_finite_number(report.get("funding_charged", 0.0))
    return value if value is not None else 0.0


def synchronized(method: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(method)
    def wrapped(self: "PaperAccount", *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapped


class PaperAccount:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._applied_execution_ids: set[str] = set()
        self._initialize_state()

    def _initialize_state(self) -> None:
        if not hasattr(self, "_applied_execution_ids"):
            self._applied_execution_ids = set()
        self._last_persisted_state: dict[str, Any] = {}
        self.initial_cash = 10000.0
        self.cash = self.initial_cash
        self.position_qty = 0.0
        self.entry_price = 0.0
        self.realized_pnl = 0.0
        self.armed = False
        self.symbol = "BTC-USDT"
        self.strategy_id = "dual_ma"
        self.pipeline_run_id = ""
        self.leverage = 1.0
        self.position_pct = 25.0
        self.max_drawdown_pct = 5.0
        self.margin_mode = "CROSS"
        self.direction_mode = "LONG_ONLY"
        self.order_type = "MARKET"
        self.reduce_only = False
        self.take_profit_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_pct = 0.0
        self.stop_loss_pct = 0.0
        self.risk_source = "AI"
        self.risk_value_mode = "PRICE"
        self.trailing_take_enabled = False
        self.trailing_take_pct = 1.5
        self.trailing_stop_enabled = False
        self.trailing_stop_pct = 1.0
        self.trailing_peak_price = 0.0
        self.trailing_take_price = 0.0
        self.trailing_stop_price = 0.0
        self.last_scale_price = 0.0
        self.short_margin = 0.0
        self.strategy_timeframe = "1D"
        self.strategy_clock_status = "IDLE"
        self.strategy_clock_source = ""
        self.strategy_clock_last_poll_ms = 0
        self.strategy_clock_last_seen_bar_ts = 0
        self.last_strategy_signal_bar_ts = 0
        self.last_strategy_attempt_bar_ts = 0
        self.last_strategy_fill_bar_ts = 0
        self.pending_strategy_signal: dict[str, Any] = {}
        self.ai_analysis: dict[str, Any] = {}
        self.orders: list[dict[str, Any]] = []
        self.signals: list[dict[str, Any]] = []
        self.conditional_orders: list[dict[str, Any]] = []
        self.equity_curve: list[dict[str, Any]] = [{"time": now_ms(), "equity": self.initial_cash}]
        self._last_persisted_state = copy.deepcopy(self.to_dict())

    @synchronized
    def symbol_change_check(self, symbol: str) -> dict[str, Any]:
        requested = str(symbol or "").strip().upper()
        blockers: list[str] = []
        if not requested:
            blockers.append("标的代码不能为空")
        if requested and requested != self.symbol:
            if self.armed:
                blockers.append("策略已启动，请先停止策略")
            if abs(float(self.position_qty)) > 1e-9:
                blockers.append("账户仍有持仓，请先平仓")
            active_conditions = [
                order for order in self.conditional_orders
                if order.get("status") in {"WAITING", "WAITING_LIMIT", "WAITING_OCO"}
            ]
            if active_conditions:
                blockers.append("仍有活动条件单，请先撤销")
        return {
            "ok": not blockers,
            "current_symbol": self.symbol,
            "requested_symbol": requested,
            "blockers": blockers,
        }

    @synchronized
    def bind_symbol(self, symbol: str, reason: str = "paper_request") -> dict[str, Any]:
        check = self.symbol_change_check(symbol)
        if not check["ok"]:
            append_ledger({"type": "paper_symbol_change_block", "reason": reason, **check})
            return check
        requested = str(check["requested_symbol"])
        if requested == self.symbol:
            return {**check, "changed": False}
        previous = self.symbol
        self.symbol = requested
        self.ai_analysis = {}
        self.take_profit_price = 0.0
        self.stop_loss_price = 0.0
        self.trailing_peak_price = 0.0
        self.trailing_take_price = 0.0
        self.trailing_stop_price = 0.0
        self.last_scale_price = 0.0
        self._reset_strategy_clock("SYMBOL_CHANGED")
        append_ledger({
            "type": "paper_symbol_change",
            "from_symbol": previous,
            "to_symbol": requested,
            "reason": reason,
        })
        self.persist("symbol_change")
        return {**check, "changed": True, "previous_symbol": previous}

    @synchronized
    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "position_qty": self.position_qty,
            "entry_price": self.entry_price,
            "realized_pnl": self.realized_pnl,
            "armed": self.armed,
            "symbol": self.symbol,
            "strategy_id": self.strategy_id,
            "pipeline_run_id": self.pipeline_run_id,
            "leverage": self.leverage,
            "position_pct": self.position_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "margin_mode": self.margin_mode,
            "direction_mode": self.direction_mode,
            "order_type": self.order_type,
            "reduce_only": self.reduce_only,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "take_profit_pct": self.take_profit_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "risk_source": self.risk_source,
            "risk_value_mode": self.risk_value_mode,
            "trailing_take_enabled": self.trailing_take_enabled,
            "trailing_take_pct": self.trailing_take_pct,
            "trailing_stop_enabled": self.trailing_stop_enabled,
            "trailing_stop_pct": self.trailing_stop_pct,
            "trailing_peak_price": self.trailing_peak_price,
            "trailing_take_price": self.trailing_take_price,
            "trailing_stop_price": self.trailing_stop_price,
            "last_scale_price": self.last_scale_price,
            "short_margin": self.short_margin,
            "strategy_timeframe": self.strategy_timeframe,
            "strategy_clock_status": self.strategy_clock_status,
            "strategy_clock_source": self.strategy_clock_source,
            "strategy_clock_last_poll_ms": self.strategy_clock_last_poll_ms,
            "strategy_clock_last_seen_bar_ts": self.strategy_clock_last_seen_bar_ts,
            "last_strategy_signal_bar_ts": self.last_strategy_signal_bar_ts,
            "last_strategy_attempt_bar_ts": self.last_strategy_attempt_bar_ts,
            "last_strategy_fill_bar_ts": self.last_strategy_fill_bar_ts,
            "pending_strategy_signal": self.pending_strategy_signal,
            "ai_analysis": self.ai_analysis,
            "orders": self.orders,
            "signals": self.signals,
            "conditional_orders": self.conditional_orders,
            "equity_curve": self.equity_curve,
        }

    @synchronized
    def load(self, payload: dict[str, Any]) -> None:
        for key, value in payload.items():
            if not key.startswith("_") and hasattr(self, key):
                setattr(self, key, value)
        self._last_persisted_state = copy.deepcopy(self.to_dict())
        self._applied_execution_ids.update(
            str(item.get("order_id") or "")
            for item in self.orders
            if isinstance(item, dict) and str(item.get("order_id") or "")
        )

    @synchronized
    def persist(self, reason: str = "state_update") -> None:
        payload = self.to_dict()
        previous = copy.deepcopy(self._last_persisted_state)
        previous_order_ids = {
            str(item.get("order_id") or "")
            for item in list(previous.get("orders") or [])
            if isinstance(item, dict) and str(item.get("order_id") or "")
        }
        current_order_ids = {
            str(item.get("order_id") or "")
            for item in list(payload.get("orders") or [])
            if isinstance(item, dict) and str(item.get("order_id") or "")
        }
        newly_applied_ids = sorted(current_order_ids - previous_order_ids)
        try:
            persist_state = _RUNTIME.get("persist_state")
            if callable(persist_state):
                if _RUNTIME.get("persist_state_accepts_applied_ids") is False:
                    persist_state(payload, reason)
                else:
                    persist_state(payload, reason, newly_applied_ids)
            else:
                write_json(STATE_FILE, payload)
        except Exception:
            for key, value in previous.items():
                if not key.startswith("_") and hasattr(self, key):
                    setattr(self, key, copy.deepcopy(value))
            raise
        self._last_persisted_state = copy.deepcopy(payload)
        self._applied_execution_ids.update(newly_applied_ids)

    @synchronized
    def equity(self, price: float) -> float:
        if self.position_qty < 0 and price > 0:
            return self.cash + self.short_margin + (self.entry_price - price) * abs(self.position_qty)
        return self.cash + self.position_qty * price

    @synchronized
    def drawdown_pct(self, price: float) -> float:
        peak = max((point["equity"] for point in self.equity_curve), default=self.initial_cash)
        if peak <= 0:
            return 0.0
        return max(0.0, (peak - self.equity(price)) / peak * 100)

    @synchronized
    def snapshot(self, price: float = 0.0) -> dict[str, Any]:
        mark_price = price or self.entry_price
        equity = self.equity(mark_price) if mark_price else self.cash
        unrealized = (mark_price - self.entry_price) * self.position_qty if self.position_qty and mark_price else 0.0
        position_value = abs(self.position_qty) * mark_price if mark_price else 0.0
        margin_used = self.short_margin if self.position_qty < 0 else position_value / max(self.leverage, 1.0) if position_value else 0.0
        maintenance_margin = position_value * 0.005 if position_value else 0.0
        liquidation_price = 0.0
        if self.position_qty > 0 and self.leverage > 1 and self.entry_price > 0:
            if self.margin_mode == "CROSS" and position_value > 0:
                cross_buffer = clamp((self.cash + margin_used) / position_value, 0.02, 0.95)
                liquidation_price = self.entry_price * (1 - cross_buffer + 0.005)
            else:
                liquidation_price = self.entry_price * (1 - 1 / self.leverage + 0.005)
        elif self.position_qty < 0 and self.leverage > 1 and self.entry_price > 0:
            if self.margin_mode == "CROSS" and position_value > 0:
                cross_buffer = clamp((self.cash + margin_used) / position_value, 0.02, 0.95)
                liquidation_price = self.entry_price * (1 + cross_buffer - 0.005)
            else:
                liquidation_price = self.entry_price * (1 + 1 / self.leverage - 0.005)
        risk_status = "正常"
        drawdown = self.drawdown_pct(mark_price) if mark_price else 0.0
        if drawdown >= self.max_drawdown_pct:
            risk_status = "熔断观察"
        elif self.position_qty > 0:
            risk_status = "持仓监控"
        return {
            "armed": self.armed,
            "symbol": self.symbol,
            "strategy": copy.deepcopy(choose_strategy(self.strategy_id)),
            "leverage": self.leverage,
            "position_pct": self.position_pct,
            "margin_mode": self.margin_mode,
            "direction_mode": self.direction_mode,
            "order_type": self.order_type,
            "reduce_only": self.reduce_only,
            "cash": round(self.cash, 2),
            "position_qty": round(self.position_qty, 8),
            "position_side": "LONG" if self.position_qty > 0 else "SHORT" if self.position_qty < 0 else "FLAT",
            "entry_price": round(self.entry_price, 4),
            "mark_price": round(mark_price, 4),
            "equity": round(equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
            "position_value": round(position_value, 2),
            "margin_used": round(margin_used, 2),
            "short_margin": round(self.short_margin, 2),
            "maintenance_margin": round(maintenance_margin, 2),
            "liquidation_price": round(liquidation_price, 4),
            "available_cash": round(max(self.cash - maintenance_margin, 0), 2),
            "drawdown_pct": round(drawdown, 2),
            "risk_status": risk_status,
            "take_profit_price": round(self.take_profit_price, 4),
            "stop_loss_price": round(self.stop_loss_price, 4),
            "take_profit_pct": round(self.take_profit_pct, 4),
            "stop_loss_pct": round(self.stop_loss_pct, 4),
            "risk_source": self.risk_source,
            "risk_value_mode": self.risk_value_mode,
            "trailing_take_enabled": self.trailing_take_enabled,
            "trailing_take_pct": round(self.trailing_take_pct, 4),
            "trailing_stop_enabled": self.trailing_stop_enabled,
            "trailing_stop_pct": round(self.trailing_stop_pct, 4),
            "trailing_peak_price": round(self.trailing_peak_price, 4),
            "trailing_take_price": round(self.trailing_take_price, 4),
            "trailing_stop_price": round(self.trailing_stop_price, 4),
            "last_scale_price": round(self.last_scale_price, 4),
            "strategy_clock": {
                "version": PAPER_STRATEGY_CLOCK_VERSION,
                "timeframe": self.strategy_timeframe,
                "status": self.strategy_clock_status,
                "source": self.strategy_clock_source,
                "last_poll_ms": self.strategy_clock_last_poll_ms,
                "last_seen_bar_ts": self.strategy_clock_last_seen_bar_ts,
                "last_signal_bar_ts": self.last_strategy_signal_bar_ts,
                "last_attempt_bar_ts": self.last_strategy_attempt_bar_ts,
                "last_fill_bar_ts": self.last_strategy_fill_bar_ts,
                "pending_signal": copy.deepcopy(self.pending_strategy_signal),
            },
            "ai_analysis": copy.deepcopy(self.ai_analysis),
            "orders": copy.deepcopy(self.orders[-80:]),
            "signals": copy.deepcopy(self.signals[-80:]),
            "conditional_orders": copy.deepcopy(self.conditional_orders[-80:]),
            "equity_curve": copy.deepcopy(self.equity_curve[-240:]),
        }

    @synchronized
    def apply_risk_config(self, risk_config: dict[str, Any]) -> None:
        self.risk_source = str(risk_config.get("risk_source", self.risk_source) or self.risk_source).upper()
        self.risk_value_mode = str(risk_config.get("value_mode", self.risk_value_mode) or self.risk_value_mode).upper()
        self.order_type = risk_config.get("order_type", self.order_type)
        self.margin_mode = risk_config.get("margin_mode", self.margin_mode)
        self.direction_mode = risk_config.get("direction_mode", self.direction_mode)
        self.reduce_only = _strict_boolean_option(risk_config, "reduce_only", self.reduce_only)
        self.take_profit_pct = float(risk_config.get("take_profit_pct", self.take_profit_pct) or 0)
        self.stop_loss_pct = float(risk_config.get("stop_loss_pct", self.stop_loss_pct) or 0)
        self.trailing_take_enabled = _strict_boolean_option(
            risk_config,
            "trailing_take_enabled",
            self.trailing_take_enabled,
        )
        self.trailing_take_pct = float(risk_config.get("trailing_take_pct", self.trailing_take_pct) or 1.5)
        self.trailing_stop_enabled = _strict_boolean_option(
            risk_config,
            "trailing_stop_enabled",
            self.trailing_stop_enabled,
        )
        self.trailing_stop_pct = float(risk_config.get("trailing_stop_pct", self.trailing_stop_pct) or 1.0)
        if self.risk_source == "MANUAL" and self.risk_value_mode == "PRICE":
            self.take_profit_price = float(risk_config.get("manual_take_profit") or 0.0)
            self.stop_loss_price = float(risk_config.get("manual_stop_loss") or 0.0)

    @synchronized
    def refresh_entry_risk_plan(self, reference_price: float, direction: str) -> None:
        clean_direction = "SHORT" if str(direction or "").upper() == "SHORT" else "LONG"
        self.ai_analysis = analyze_strategy_context(
            self.strategy_id,
            self.symbol,
            reference_price,
            self.take_profit_price if self.risk_source == "MANUAL" and self.risk_value_mode == "PRICE" else 0.0,
            self.stop_loss_price if self.risk_source == "MANUAL" and self.risk_value_mode == "PRICE" else 0.0,
            clean_direction,
        )
        if self.risk_source == "AI":
            self.take_profit_price = float(self.ai_analysis.get("take_profit") or 0.0)
            self.stop_loss_price = float(self.ai_analysis.get("stop_loss") or 0.0)
            return
        if self.risk_value_mode != "PCT" or reference_price <= 0:
            return
        if clean_direction == "SHORT":
            self.take_profit_price = round(reference_price * (1 - self.take_profit_pct / 100), 8) if self.take_profit_pct > 0 else 0.0
            self.stop_loss_price = round(reference_price * (1 + self.stop_loss_pct / 100), 8) if self.stop_loss_pct > 0 else 0.0
        else:
            self.take_profit_price = round(reference_price * (1 + self.take_profit_pct / 100), 8) if self.take_profit_pct > 0 else 0.0
            self.stop_loss_price = round(reference_price * (1 - self.stop_loss_pct / 100), 8) if self.stop_loss_pct > 0 else 0.0

    def _reset_strategy_clock(self, status: str) -> None:
        self.strategy_timeframe = "1D"
        self.strategy_clock_status = status
        self.strategy_clock_source = ""
        self.strategy_clock_last_poll_ms = 0
        self.strategy_clock_last_seen_bar_ts = 0
        self.last_strategy_signal_bar_ts = 0
        self.last_strategy_attempt_bar_ts = 0
        self.last_strategy_fill_bar_ts = 0
        self.pending_strategy_signal = {}

    def _record_equity(self, price: float, *, force: bool = False) -> None:
        stamp = now_ms()
        point = {"time": stamp, "equity": round(self.equity(price), 2)}
        if self.equity_curve and not force and stamp - int(self.equity_curve[-1].get("time") or 0) < 60_000:
            self.equity_curve[-1] = point
        else:
            self.equity_curve.append(point)
        self.equity_curve = self.equity_curve[-2000:]

    @synchronized
    def refresh_trailing_prices(self, price: float) -> None:
        if self.position_qty == 0 or price <= 0:
            self.trailing_peak_price = 0.0
            self.trailing_take_price = 0.0
            self.trailing_stop_price = 0.0
            return
        if self.position_qty < 0:
            self.trailing_peak_price = min(self.trailing_peak_price or price, price)
            if self.trailing_stop_enabled:
                next_stop = self.trailing_peak_price * (1 + self.trailing_stop_pct / 100)
                self.trailing_stop_price = min(self.trailing_stop_price or next_stop, next_stop)
            if self.trailing_take_enabled and self.entry_price > 0 and self.trailing_peak_price <= self.entry_price * (1 - self.trailing_take_pct / 100):
                next_take = self.trailing_peak_price * (1 + self.trailing_take_pct / 100)
                self.trailing_take_price = min(self.trailing_take_price or next_take, next_take)
            return
        self.trailing_peak_price = max(self.trailing_peak_price or price, price)
        if self.trailing_stop_enabled:
            next_stop = self.trailing_peak_price * (1 - self.trailing_stop_pct / 100)
            self.trailing_stop_price = max(self.trailing_stop_price or 0.0, next_stop)
        if self.trailing_take_enabled and self.entry_price > 0 and self.trailing_peak_price >= self.entry_price * (1 + self.trailing_take_pct / 100):
            next_take = self.trailing_peak_price * (1 - self.trailing_take_pct / 100)
            self.trailing_take_price = max(self.trailing_take_price or 0.0, next_take)

    @synchronized
    def arm(
        self,
        symbol: str,
        strategy_id: str,
        leverage: float,
        position_pct: float,
        price: float = 0.0,
        risk_config: dict[str, Any] | None = None,
        *,
        pipeline_run_id: str = "",
    ) -> None:
        risk_config = dict(risk_config or {})
        value_mode = str(risk_config.get("value_mode") or risk_config.get("risk_value_mode") or self.risk_value_mode).upper()
        profile = {
            "direction_mode": str(risk_config.get("direction_mode") or self.direction_mode).upper(),
            "risk_source": str(risk_config.get("risk_source") or self.risk_source).upper(),
            "risk_value_mode": value_mode,
            "trailing_take_enabled": _strict_boolean_option(
                risk_config,
                "trailing_take_enabled",
                self.trailing_take_enabled,
            ),
            "trailing_stop_enabled": _strict_boolean_option(
                risk_config,
                "trailing_stop_enabled",
                self.trailing_stop_enabled,
            ),
            "reduce_only": _strict_boolean_option(risk_config, "reduce_only", self.reduce_only),
            "order_type": str(risk_config.get("order_type") or self.order_type).upper(),
            "margin_mode": str(risk_config.get("margin_mode") or self.margin_mode).upper(),
        }
        blockers: list[str] = []
        expected = {
            "direction_mode": "LONG_ONLY",
            "risk_source": "MANUAL",
            "risk_value_mode": "PCT",
            "trailing_take_enabled": False,
            "trailing_stop_enabled": False,
            "reduce_only": False,
            "order_type": "CURRENT",
            "margin_mode": "CROSS",
        }
        for key, expected_value in expected.items():
            if profile[key] != expected_value:
                blockers.append(f"{key}={profile[key]} expected {expected_value}")
        if abs(float(leverage) - 1.0) > 1e-9:
            blockers.append(f"leverage={leverage} expected 1.0")
        if self.armed:
            blockers.append("automated paper strategy is already armed")
        if abs(float(self.position_qty)) > 1e-9:
            blockers.append("automated paper strategy requires a flat account")
        if self.pending_strategy_signal:
            blockers.append("stale pending strategy signal must be cleared before arming")
        if any(
            str(order.get("status") or "").upper() in {"WAITING", "WAITING_LIMIT", "WAITING_OCO", "MAKER_WAIT"}
            for order in self.conditional_orders
            if isinstance(order, dict)
        ):
            blockers.append("active conditional orders must be cancelled before arming")
        if blockers:
            raise ValueError("Automated paper profile rejected: " + ", ".join(blockers))
        binding = self.bind_symbol(symbol, "strategy_arm")
        if not binding.get("ok"):
            raise ValueError("；".join(binding.get("blockers") or ["模拟账户标的切换被阻止"]))
        self.armed = True
        self.strategy_id = strategy_id
        self.pipeline_run_id = str(pipeline_run_id or self.pipeline_run_id)
        self.leverage = 1.0
        self.position_pct = max(1.0, min(position_pct, 100.0))
        self.apply_risk_config(risk_config)
        self.trailing_peak_price = 0.0
        self.trailing_take_price = 0.0
        self.trailing_stop_price = 0.0
        self._reset_strategy_clock("COLD_START")
        if price > 0:
            self.refresh_entry_risk_plan(
                price,
                risk_config.get("analysis_direction") or trade_direction_from_mode(self.direction_mode),
            )
        self.signals.append({
            "time": now_ms(),
            "symbol": self.symbol,
            "action": "ARM",
            "reason": f"启动 {choose_strategy(strategy_id)['name']}，AI风控概率 {self.ai_analysis.get('profit_probability', 0) * 100:.0f}%",
            "confidence": float(self.ai_analysis.get("profit_probability") or 1.0),
            "analysis": self.ai_analysis,
        })
        append_ledger({
            "type": "strategy_arm",
            "symbol": symbol,
            "strategy": strategy_id,
            "pipeline_run_id": self.pipeline_run_id,
            "leverage": self.leverage,
            "position_pct": self.position_pct,
            "take_profit": self.take_profit_price,
            "stop_loss": self.stop_loss_price,
            "trailing_take": self.trailing_take_enabled,
            "trailing_stop": self.trailing_stop_enabled,
            "reduce_only": self.reduce_only,
            "margin_mode": self.margin_mode,
            "direction_mode": self.direction_mode,
            "order_type": self.order_type,
            "probability": self.ai_analysis.get("profit_probability"),
        })
        self.persist()

    @synchronized
    def stop(self) -> str:
        stopped_run_id = str(self.pipeline_run_id or "")
        self.armed = False
        self.pipeline_run_id = ""
        self.pending_strategy_signal = {}
        self.strategy_clock_status = "STOPPED"
        self.signals.append({
            "time": now_ms(),
            "symbol": self.symbol,
            "action": "STOP",
            "reason": "模拟策略停止",
            "confidence": 1.0,
        })
        append_ledger({
            "type": "strategy_stop",
            "symbol": self.symbol,
            "strategy": self.strategy_id,
            "pipeline_run_id": stopped_run_id,
        })
        self.persist()
        return stopped_run_id

    @synchronized
    def emergency_stop(self, price: float = 0.0, reason: str = "风控急停") -> dict[str, Any]:
        mark_price = price or self.entry_price
        stopped_run_id = str(self.pipeline_run_id or "")
        pending_signal_id = str(self.pending_strategy_signal.get("signal_id") or "")
        position_before = float(self.position_qty)
        active_states = {"WAITING", "WAITING_LIMIT", "WAITING_OCO"}
        cancelled_condition_ids: list[str] = []
        stamp = now_ms()

        self.armed = False
        self.pending_strategy_signal = {}
        self.strategy_clock_status = "EMERGENCY_HALTED"
        for order in self.conditional_orders:
            if str(order.get("status") or "").upper() not in active_states:
                continue
            order["status"] = "CANCELLED"
            order["updated_at"] = stamp
            order["cancel_reason"] = "emergency_stop"
            cancelled_condition_ids.append(str(order.get("id") or ""))
        self.persist("emergency_halt_requested")

        flatten_attempted = abs(position_before) > 1e-9 and mark_price > 0
        flatten_error = ""
        signal_count_before_flatten = len(self.signals)
        try:
            if self.position_qty > 0 and mark_price > 0:
                self.close_long_manual(
                    mark_price,
                    100.0,
                    "MARKET",
                    0.0,
                    reason,
                    manual=False,
                    idempotency_key=f"emergency:{self.symbol}:{stamp}",
                )
            elif self.position_qty < 0 and mark_price > 0:
                self.close_short_manual(
                    mark_price,
                    100.0,
                    "MARKET",
                    0.0,
                    reason,
                    manual=False,
                    idempotency_key=f"emergency:{self.symbol}:{stamp}",
                )
        except Exception as exc:
            flatten_error = f"{type(exc).__name__}: {exc}"

        flattened = abs(self.position_qty) <= 1e-9
        if not flattened and not flatten_error and len(self.signals) > signal_count_before_flatten:
            flatten_error = str(self.signals[-1].get("reason") or "paper flatten did not fill")
        if not flatten_attempted and not flattened and not flatten_error:
            flatten_error = "authoritative emergency flatten price is unavailable"
        self.pipeline_run_id = ""
        self.signals.append({
            "time": now_ms(),
            "symbol": self.symbol,
            "action": "HALT",
            "reason": reason,
            "confidence": 1.0,
            "flattened": flattened,
        })
        emergency = {
            "status": "HALTED_FLAT" if flattened else "HALTED_WITH_POSITION",
            "safe_state_reached": flattened,
            "flatten_attempted": flatten_attempted,
            "flattened": flattened,
            "flatten_error": flatten_error,
            "position_before": position_before,
            "remaining_position_qty": float(self.position_qty),
            "pipeline_run_id": stopped_run_id,
            "pending_signal_id": pending_signal_id,
            "cancelled_condition_ids": cancelled_condition_ids,
        }
        append_ledger({
            "type": "emergency_stop",
            "symbol": self.symbol,
            "price": mark_price,
            "reason": reason,
            **emergency,
        })
        self.persist("emergency_halt_finalized")
        snapshot = self.snapshot(mark_price)
        snapshot["emergency_stop"] = emergency
        return snapshot

    @synchronized
    def reset(self) -> dict[str, Any]:
        blockers: list[str] = []
        if self.armed:
            blockers.append("策略仍在运行")
        if abs(float(self.position_qty)) > 1e-9:
            blockers.append("账户仍有持仓")
        if any(
            order.get("status") in {"WAITING", "WAITING_LIMIT", "WAITING_OCO"}
            for order in self.conditional_orders
        ):
            blockers.append("仍有活动条件单")
        if blockers:
            result = {"ok": False, "blockers": blockers}
            append_ledger({"type": "paper_reset_block", **result})
            return result
        rollback_state = copy.deepcopy(self.to_dict())
        self._initialize_state()
        self._last_persisted_state = rollback_state
        append_ledger({"type": "paper_reset"})
        self.persist("paper_reset")
        return {"ok": True, "blockers": []}

    @synchronized
    def manual_signal(self, action: str, reason: str, price: float, confidence: float = 1.0, manual: bool = True) -> None:
        self.signals.append({
            "time": now_ms(),
            "symbol": self.symbol,
            "action": action,
            "reason": reason,
            "confidence": confidence,
            "price": round(price, 4) if price else 0.0,
            "manual": manual,
        })

    @synchronized
    def blocked_manual_order(self, action: str, reason: str, price: float) -> dict[str, Any]:
        self.manual_signal(action, reason, price)
        self.equity_curve.append({"time": now_ms(), "equity": round(self.equity(price), 2)})
        append_ledger({"type": "paper_manual_block", "symbol": self.symbol, "action": action, "reason": reason})
        self.persist()
        return self.snapshot(price)

    @synchronized
    def execution_risk_check(
        self,
        side: str,
        notional: float,
        price: float,
        order_type: str,
        reduce_only: bool = False,
        idempotency_key: str = "",
        limit_price: float = 0.0,
        signal_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        position_side = "LONG" if self.position_qty > 0 else "SHORT" if self.position_qty < 0 else "FLAT"
        context = {
            "position_side": position_side,
            "direction_mode": self.direction_mode,
            "reduce_only": reduce_only or self.reduce_only,
            "order_type": order_type,
            "limit_price": limit_price,
            "margin_mode": self.margin_mode,
            "leverage": self.leverage,
            "position_pct": self.position_pct,
            "idempotency_key": str(idempotency_key or ""),
        }
        for key in ("signal_id", "signal_created_at", "signal_action", "signal_reason"):
            if signal_context and signal_context.get(key) not in {None, ""}:
                context[key] = signal_context[key]
        return risk_pretrade_check(
            self.symbol,
            side,
            "PAPER",
            notional,
            price,
            context,
        )

    @synchronized
    def authoritative_execution_risk_check(
        self,
        pretrade_result: dict[str, Any] | None,
        side: str,
        notional: float,
        price: float,
        order_type: str,
        reduce_only: bool,
        idempotency_key: str,
        signal_context: dict[str, Any] | None = None,
        limit_price: float = 0.0,
    ) -> dict[str, Any]:
        candidate = pretrade_result if isinstance(pretrade_result, dict) else None
        candidate_context = candidate.get("context") if isinstance((candidate or {}).get("context"), dict) else {}
        effective_signal_context = {**candidate_context, **dict(signal_context or {})}
        position_side = "LONG" if self.position_qty > 0 else "SHORT" if self.position_qty < 0 else "FLAT"
        if type(reduce_only) is not bool:
            raise ValueError("paper_boolean_option_invalid:reduce_only")
        expected_reduce_only = reduce_only or self.reduce_only
        expected_notional = round(float(notional), 2)
        try:
            candidate_notional = round(float((candidate or {}).get("notional") or 0.0), 2)
        except (TypeError, ValueError, OverflowError):
            candidate_notional = -1.0
        candidate_price = _strict_finite_number((candidate or {}).get("requested_price"))
        candidate_limit_price = _strict_finite_number(candidate_context.get("limit_price"))
        expected_limit_price = _strict_finite_number(limit_price)
        raw_checked_at = (candidate or {}).get("checked_at")
        candidate_checked_at = (
            int(raw_checked_at)
            if isinstance(raw_checked_at, int) and not isinstance(raw_checked_at, bool)
            else 0
        )
        candidate_age_ms = now_ms() - candidate_checked_at if candidate_checked_at else MAX_PRETRADE_RESULT_AGE_MS + 1
        contract_matches = bool(
            candidate
            and str(candidate.get("request_id") or "")
            and str(candidate.get("symbol") or "").upper() == self.symbol.upper()
            and str(candidate.get("side") or "").upper() == str(side or "").upper()
            and str(candidate.get("mode") or "").upper() == "PAPER"
            and abs(candidate_notional - expected_notional) <= 0.01
            and candidate_price is not None
            and abs(candidate_price - float(price)) <= 1e-8
            and candidate_limit_price is not None
            and expected_limit_price is not None
            and abs(candidate_limit_price - expected_limit_price) <= 1e-8
            and -1_000 <= candidate_age_ms <= MAX_PRETRADE_RESULT_AGE_MS
            and str(candidate_context.get("position_side") or "").upper() == position_side
            and type(candidate.get("allowed")) is bool
            and type(candidate_context.get("reduce_only")) is bool
            and candidate_context.get("reduce_only") is expected_reduce_only
            and str(candidate_context.get("order_type") or "").upper() == str(order_type or "").upper()
            and str(candidate_context.get("idempotency_key") or "") == str(idempotency_key or "")
            and candidate_context.get("risk_audit_status") in {"PASS", "FAILED"}
            and (
                not signal_context
                or str(candidate_context.get("signal_id") or "") == str(signal_context.get("signal_id") or "")
            )
        )
        if contract_matches:
            return candidate

        previous_request_id = str((candidate or {}).get("request_id") or "")
        fresh = self.execution_risk_check(
            side,
            notional,
            price,
            order_type,
            reduce_only,
            idempotency_key,
            limit_price=limit_price,
            signal_context=effective_signal_context,
        )
        if previous_request_id:
            fresh["revalidated_from_request_id"] = previous_request_id
        if candidate is not None:
            candidate.clear()
            candidate.update(fresh)
            return candidate
        return fresh

    @synchronized
    def execution_already_applied(self, report: dict[str, Any], price: float) -> dict[str, Any] | None:
        order_id = str(report.get("order_id") or "")
        if not order_id:
            return None
        locally_applied = order_id in self._applied_execution_ids or any(
            str(order.get("order_id") or "") == order_id for order in self.orders
        )
        durable_applied = False
        order_applied = _RUNTIME.get("order_applied")
        if callable(order_applied):
            durable_applied = order_applied(order_id) is True
        if not locally_applied and not durable_applied:
            return None
        self._applied_execution_ids.add(order_id)
        append_ledger({
            "type": "paper_order_idempotent_replay" if report.get("idempotent_replay") is True else "paper_order_duplicate_report",
            "order_id": order_id,
            "symbol": self.symbol,
            "status": "NOOP",
        })
        return self.snapshot(price)

    @synchronized
    def execution_contract_block(
        self,
        report: Any,
        *,
        side: str,
        order_type: str,
        price: float,
        notional: float,
        limit_price: float,
        requested_qty: float,
        reduce_only: bool,
        idempotency_key: str,
        risk_check: dict[str, Any],
    ) -> dict[str, Any] | None:
        errors = execution_report_contract_errors(
            report,
            symbol=self.symbol,
            side=side,
            order_type=order_type,
            mark_price=price,
            notional=notional,
            limit_price=limit_price,
            requested_qty=requested_qty,
            reduce_only=reduce_only,
            idempotency_key=idempotency_key,
            risk_check=risk_check,
        )
        if not errors:
            return None
        append_ledger({
            "type": "paper_execution_contract_block",
            "symbol": self.symbol,
            "side": side,
            "order_id": str(report.get("order_id") or "") if isinstance(report, dict) else "",
            "errors": errors,
        })
        return self.blocked_manual_order(
            "EXECUTION_BLOCK",
            "Execution report contract rejected: " + ", ".join(errors),
            price,
        )

    @synchronized
    def open_long_manual(self, price: float, quantity_pct: float, order_type: str, limit_price: float, reason: str, manual: bool = True, idempotency_key: str = "", pretrade_result: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.position_qty < -1e-9:
            return self.blocked_manual_order("BLOCK", "Existing short position must be covered before opening long.", price)
        if self.reduce_only:
            return self.blocked_manual_order("BLOCK", "只减仓已开启，不能手动开多", price)
        spend = min(self.cash * 0.98, self.equity(price) * quantity_pct / 100 * self.leverage)
        risk_check = self.authoritative_execution_risk_check(
            pretrade_result, "BUY", spend, price, order_type, False, idempotency_key,
            limit_price=limit_price,
        )
        if risk_check.get("allowed") is not True:
            return self.blocked_manual_order("RISK_BLOCK", risk_check.get("reason", "影子风控阻止开多"), price)
        report = execute_paper_order(self.symbol, "BUY", order_type, price, spend, limit_price, risk_check)
        replay_snapshot = self.execution_already_applied(report, price)
        if replay_snapshot is not None:
            return replay_snapshot
        contract_block = self.execution_contract_block(
            report,
            side="BUY",
            order_type=order_type,
            price=price,
            notional=spend,
            limit_price=limit_price,
            requested_qty=0.0,
            reduce_only=False,
            idempotency_key=idempotency_key,
            risk_check=risk_check,
        )
        if contract_block is not None:
            return contract_block
        if not execution_report_has_fill(report):
            return self.blocked_manual_order("WAIT", f"手动买入未成交：{report['note']}", price)
        execution_price = float(report["avg_price"])
        quantity = float(report["filled_qty"])
        spend = float(report["filled_notional"])
        old_qty = max(self.position_qty, 0.0)
        old_cost = self.entry_price * old_qty
        self.cash -= spend + float(report["fee"])
        self.position_qty = old_qty + quantity
        self.entry_price = (old_cost + spend + float(report["fee"])) / max(self.position_qty, 1e-9)
        self.last_scale_price = execution_price
        self.trailing_peak_price = max(self.trailing_peak_price, execution_price)
        self.refresh_entry_risk_plan(self.entry_price, "LONG")
        self.orders.append({
            **execution_lineage(report),
            "time": now_ms(),
            "symbol": self.symbol,
            "side": "BUY" if old_qty <= 0 else "ADD",
            "order_type": order_type,
            "price": round(execution_price, 4),
            "quantity": round(quantity, 8),
            "notional": round(spend, 2),
            "fee": report["fee"],
            "funding_estimate": report["funding_estimate"],
            "funding_charged": execution_funding_charged(report),
            "slippage_pct": report["slippage_pct"],
            "match_status": report["status"],
            "reason": reason,
            "manual": manual,
            "reduce_only": False,
        })
        self.manual_signal("BUY", reason, execution_price, manual=manual)
        append_ledger({"type": "paper_order", "order": self.orders[-1]})
        self.equity_curve.append({"time": now_ms(), "equity": round(self.equity(execution_price), 2)})
        self.persist()
        return self.snapshot(execution_price)

    @synchronized
    def close_long_manual(self, price: float, quantity_pct: float, order_type: str, limit_price: float, reason: str, manual: bool = True, idempotency_key: str = "", pretrade_result: dict[str, Any] | None = None, signal_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.position_qty <= 1e-9:
            return self.blocked_manual_order("WAIT", "No long position is available to close.", price)
        close_qty = min(self.position_qty * quantity_pct / 100, self.position_qty)
        risk_check = self.authoritative_execution_risk_check(
            pretrade_result, "SELL", close_qty * price, price, order_type, True,
            idempotency_key, signal_context, limit_price,
        )
        if risk_check.get("allowed") is not True:
            return self.blocked_manual_order("RISK_BLOCK", risk_check.get("reason", "影子风控阻止平多"), price)
        report = execute_paper_order(
            self.symbol,
            "SELL",
            order_type,
            price,
            close_qty * price,
            limit_price,
            risk_check,
            requested_qty=close_qty,
        )
        replay_snapshot = self.execution_already_applied(report, price)
        if replay_snapshot is not None:
            return replay_snapshot
        contract_block = self.execution_contract_block(
            report,
            side="SELL",
            order_type=order_type,
            price=price,
            notional=close_qty * price,
            limit_price=limit_price,
            requested_qty=close_qty,
            reduce_only=True,
            idempotency_key=idempotency_key,
            risk_check=risk_check,
        )
        if contract_block is not None:
            return contract_block
        if not execution_report_has_fill(report):
            return self.blocked_manual_order("WAIT", f"手动卖出未成交：{report['note']}", price)
        execution_price = float(report["avg_price"])
        close_qty = min(float(report["filled_qty"]), self.position_qty)
        notional = close_qty * execution_price
        funding_charged = execution_funding_charged(report)
        pnl = (execution_price - self.entry_price) * close_qty - float(report["fee"]) - funding_charged
        self.cash += notional - float(report["fee"]) - funding_charged
        self.realized_pnl += pnl
        self.position_qty -= close_qty
        if self.position_qty <= 1e-9:
            self.position_qty = 0.0
            self.entry_price = 0.0
            self.last_scale_price = 0.0
            self.refresh_trailing_prices(0.0)
        self.orders.append({
            **execution_lineage(report),
            "time": now_ms(),
            "symbol": self.symbol,
            "side": "SELL",
            "order_type": order_type,
            "price": round(execution_price, 4),
            "quantity": round(close_qty, 8),
            "notional": round(notional, 2),
            "pnl": round(pnl, 2),
            "fee": report["fee"],
            "funding_estimate": report["funding_estimate"],
            "funding_charged": execution_funding_charged(report),
            "slippage_pct": report["slippage_pct"],
            "match_status": report["status"],
            "reason": reason,
            "manual": manual,
            "reduce_only": True,
        })
        self.manual_signal("SELL", reason, execution_price, manual=manual)
        append_ledger({"type": "paper_order", "order": self.orders[-1]})
        self.equity_curve.append({"time": now_ms(), "equity": round(self.equity(execution_price), 2)})
        self.persist()
        return self.snapshot(execution_price)

    @synchronized
    def open_short_manual(self, price: float, quantity_pct: float, order_type: str, limit_price: float, reason: str, manual: bool = True, idempotency_key: str = "", pretrade_result: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.position_qty > 1e-9:
            return self.blocked_manual_order("BLOCK", "Existing long position must be closed before opening short.", price)
        if self.reduce_only:
            return self.blocked_manual_order("BLOCK", "只减仓已开启，不能手动开空", price)
        notional = min(self.cash * 0.98 * self.leverage, self.equity(price) * quantity_pct / 100 * self.leverage)
        risk_check = self.authoritative_execution_risk_check(
            pretrade_result, "SELL", notional, price, order_type, False, idempotency_key,
            limit_price=limit_price,
        )
        if risk_check.get("allowed") is not True:
            return self.blocked_manual_order("RISK_BLOCK", risk_check.get("reason", "影子风控阻止开空"), price)
        report = execute_paper_order(self.symbol, "SELL", order_type, price, notional, limit_price, risk_check)
        replay_snapshot = self.execution_already_applied(report, price)
        if replay_snapshot is not None:
            return replay_snapshot
        contract_block = self.execution_contract_block(
            report,
            side="SELL",
            order_type=order_type,
            price=price,
            notional=notional,
            limit_price=limit_price,
            requested_qty=0.0,
            reduce_only=False,
            idempotency_key=idempotency_key,
            risk_check=risk_check,
        )
        if contract_block is not None:
            return contract_block
        if not execution_report_has_fill(report):
            return self.blocked_manual_order("WAIT", f"手动开空未成交：{report['note']}", price)
        execution_price = float(report["avg_price"])
        quantity = float(report["filled_qty"])
        notional = float(report["filled_notional"])
        margin_required = notional / max(self.leverage, 1.0)
        old_abs_qty = abs(min(self.position_qty, 0.0))
        old_cost = self.entry_price * old_abs_qty
        self.cash -= margin_required + float(report["fee"])
        self.short_margin += margin_required
        self.position_qty = -(old_abs_qty + quantity)
        self.entry_price = (old_cost + notional) / max(abs(self.position_qty), 1e-9)
        self.last_scale_price = execution_price
        self.trailing_peak_price = execution_price if old_abs_qty <= 0 else min(self.trailing_peak_price or execution_price, execution_price)
        self.refresh_entry_risk_plan(self.entry_price, "SHORT")
        self.orders.append({
            **execution_lineage(report),
            "time": now_ms(),
            "symbol": self.symbol,
            "side": "SHORT" if old_abs_qty <= 0 else "ADD_SHORT",
            "order_type": order_type,
            "price": round(execution_price, 4),
            "quantity": round(quantity, 8),
            "notional": round(notional, 2),
            "fee": report["fee"],
            "funding_estimate": report["funding_estimate"],
            "funding_charged": execution_funding_charged(report),
            "slippage_pct": report["slippage_pct"],
            "match_status": report["status"],
            "reason": reason,
            "manual": manual,
            "reduce_only": False,
        })
        self.manual_signal("SHORT", reason, execution_price, manual=manual)
        append_ledger({"type": "paper_order", "order": self.orders[-1]})
        self.equity_curve.append({"time": now_ms(), "equity": round(self.equity(execution_price), 2)})
        self.persist()
        return self.snapshot(execution_price)

    @synchronized
    def close_short_manual(self, price: float, quantity_pct: float, order_type: str, limit_price: float, reason: str, manual: bool = True, idempotency_key: str = "", pretrade_result: dict[str, Any] | None = None, signal_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.position_qty >= -1e-9:
            return self.blocked_manual_order("WAIT", "No short position is available to close.", price)
        abs_qty = abs(self.position_qty)
        close_qty = min(abs_qty * quantity_pct / 100, abs_qty)
        risk_check = self.authoritative_execution_risk_check(
            pretrade_result, "BUY", close_qty * price, price, order_type, True,
            idempotency_key, signal_context, limit_price,
        )
        if risk_check.get("allowed") is not True:
            return self.blocked_manual_order("RISK_BLOCK", risk_check.get("reason", "影子风控阻止平空"), price)
        report = execute_paper_order(
            self.symbol,
            "BUY",
            order_type,
            price,
            close_qty * price,
            limit_price,
            risk_check,
            requested_qty=close_qty,
        )
        replay_snapshot = self.execution_already_applied(report, price)
        if replay_snapshot is not None:
            return replay_snapshot
        contract_block = self.execution_contract_block(
            report,
            side="BUY",
            order_type=order_type,
            price=price,
            notional=close_qty * price,
            limit_price=limit_price,
            requested_qty=close_qty,
            reduce_only=True,
            idempotency_key=idempotency_key,
            risk_check=risk_check,
        )
        if contract_block is not None:
            return contract_block
        if not execution_report_has_fill(report):
            return self.blocked_manual_order("WAIT", f"手动平空未成交：{report['note']}", price)
        execution_price = float(report["avg_price"])
        close_qty = min(float(report["filled_qty"]), abs_qty)
        notional = close_qty * execution_price
        release_ratio = close_qty / max(abs_qty, 1e-9)
        released_margin = self.short_margin * release_ratio
        funding_charged = execution_funding_charged(report)
        pnl = (self.entry_price - execution_price) * close_qty - float(report["fee"]) - funding_charged
        self.cash += released_margin + pnl
        self.short_margin = max(0.0, self.short_margin - released_margin)
        self.realized_pnl += pnl
        self.position_qty += close_qty
        if abs(self.position_qty) <= 1e-9:
            self.position_qty = 0.0
            self.entry_price = 0.0
            self.short_margin = 0.0
            self.last_scale_price = 0.0
            self.refresh_trailing_prices(0.0)
        self.orders.append({
            **execution_lineage(report),
            "time": now_ms(),
            "symbol": self.symbol,
            "side": "COVER",
            "order_type": order_type,
            "price": round(execution_price, 4),
            "quantity": round(close_qty, 8),
            "notional": round(notional, 2),
            "pnl": round(pnl, 2),
            "fee": report["fee"],
            "funding_estimate": report["funding_estimate"],
            "funding_charged": execution_funding_charged(report),
            "slippage_pct": report["slippage_pct"],
            "match_status": report["status"],
            "reason": reason,
            "manual": manual,
            "reduce_only": True,
        })
        self.manual_signal("COVER", reason, execution_price, manual=manual)
        append_ledger({"type": "paper_order", "order": self.orders[-1]})
        self.equity_curve.append({"time": now_ms(), "equity": round(self.equity(execution_price), 2)})
        self.persist()
        return self.snapshot(execution_price)

    @synchronized
    def manual_order(
        self,
        side: str,
        price: float,
        quantity_pct: float,
        order_type: str = "MARKET",
        limit_price: float = 0.0,
        idempotency_key: str = "",
        pretrade_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_side = str(side or "").strip().upper()
        if normalized_side not in {"BUY", "SELL", "CLOSE"}:
            return self.blocked_manual_order("REJECT", "Manual order side must be BUY, SELL, or CLOSE.", 0.0)
        normalized_order_type = str(order_type or "").strip().upper()
        if normalized_order_type not in ORDER_TYPES:
            return self.blocked_manual_order("REJECT", "Manual order type is unsupported.", 0.0)
        clean_quantity_pct = 100.0 if normalized_side == "CLOSE" else _strict_quantity_pct(quantity_pct)
        if clean_quantity_pct is None:
            return self.blocked_manual_order(
                "REJECT",
                "Manual order quantity_pct must be greater than 0 and at most 100.",
                0.0,
            )
        clean_price = _strict_finite_number(price)
        if clean_price is None or clean_price <= 0:
            clean_price = _strict_finite_number(self.entry_price)
        if clean_price is None or clean_price <= 0:
            return self.blocked_manual_order("REJECT", "No valid price is available for simulated execution.", 0.0)
        clean_limit_price = _strict_finite_number(limit_price)
        if clean_limit_price is None or clean_limit_price < 0:
            return self.blocked_manual_order(
                "REJECT",
                "Manual order limit price must be finite and non-negative.",
                clean_price,
            )
        side = normalized_side
        order_type = normalized_order_type
        quantity_pct = clean_quantity_pct
        price = clean_price
        limit_price = clean_limit_price
        if side == "CLOSE":
            if self.position_qty > 0:
                return self.close_long_manual(price, 100.0, order_type, limit_price, "手动模拟平多", idempotency_key=idempotency_key, pretrade_result=pretrade_result)
            if self.position_qty < 0:
                return self.close_short_manual(price, 100.0, order_type, limit_price, "手动模拟平空", idempotency_key=idempotency_key, pretrade_result=pretrade_result)
            return self.blocked_manual_order("WAIT", "当前没有持仓可平", price)
        if side == "BUY":
            if self.position_qty < 0:
                return self.close_short_manual(price, quantity_pct, order_type, limit_price, "手动买入平空", idempotency_key=idempotency_key, pretrade_result=pretrade_result)
            if self.direction_mode == "SHORT_ONLY":
                return self.blocked_manual_order("BLOCK", "当前是只做空模式，买入只允许用于平空", price)
            return self.open_long_manual(price, quantity_pct, order_type, limit_price, "手动模拟买入/开多", idempotency_key=idempotency_key, pretrade_result=pretrade_result)
        if self.position_qty > 0:
            return self.close_long_manual(price, quantity_pct, order_type, limit_price, "手动卖出减仓/平多", idempotency_key=idempotency_key, pretrade_result=pretrade_result)
        if self.direction_mode == "LONG_ONLY":
            return self.blocked_manual_order("BLOCK", "当前是只做多模式，卖出只会用于已有多仓减仓", price)
        return self.open_short_manual(price, quantity_pct, order_type, limit_price, "手动模拟卖出/开空", idempotency_key=idempotency_key, pretrade_result=pretrade_result)

    @synchronized
    def add_condition(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        quantity_pct: float,
        note: str,
        order_type: str = "MARKET",
        limit_price: float = 0.0,
        reduce_only: bool = False,
        take_profit_price: float = 0.0,
        stop_loss_price: float = 0.0,
        time_in_force: str = "GTC",
        batch_plan: str = "",
        take_profit_plan: str = "",
    ) -> dict[str, Any]:
        normalized_order_type = str(order_type or "").strip().upper()
        if normalized_order_type not in ORDER_TYPES:
            raise ValueError("Conditional order type is unsupported")
        if normalized_order_type in PERSISTENT_ORDER_TYPES:
            raise ValueError("持久 LIMIT/POST_ONLY 条件单尚未启用撮合与结算回调")
        normalized_side = str(side or "").strip().upper()
        if normalized_side not in {"BUY", "SELL"}:
            raise ValueError("条件单方向必须是 BUY 或 SELL")
        normalized_symbol = str(symbol or "").strip().upper()
        if not normalized_symbol:
            raise ValueError("条件单标的不能为空")
        clean_quantity_pct = _strict_quantity_pct(quantity_pct)
        if clean_quantity_pct is None:
            raise ValueError("Conditional order quantity_pct must be greater than 0 and at most 100")
        numeric_prices = {
            "trigger_price": _strict_finite_number(trigger_price),
            "limit_price": _strict_finite_number(limit_price),
            "take_profit_price": _strict_finite_number(take_profit_price),
            "stop_loss_price": _strict_finite_number(stop_loss_price),
        }
        if any(value is None or value < 0 for value in numeric_prices.values()):
            raise ValueError("Conditional order prices must be finite and non-negative")
        normalized_time_in_force = str(time_in_force or "").strip().upper()
        if normalized_time_in_force not in {"GTC", "IOC", "FOK", "POST_ONLY"}:
            raise ValueError("Conditional order time_in_force is unsupported")
        created_at = now_ms()
        order = {
            "id": f"C{created_at}-{len(self.conditional_orders) + 1:04d}",
            "time": created_at,
            "symbol": normalized_symbol,
            "side": normalized_side,
            "order_type": normalized_order_type,
            "trigger_price": round(float(numeric_prices["trigger_price"]), 4),
            "limit_price": round(float(numeric_prices["limit_price"]), 4),
            "take_profit_price": round(float(numeric_prices["take_profit_price"]), 4),
            "stop_loss_price": round(float(numeric_prices["stop_loss_price"]), 4),
            "time_in_force": normalized_time_in_force,
            "batch_plan": batch_plan,
            "take_profit_plan": take_profit_plan,
            "quantity_pct": round(clean_quantity_pct, 2),
            "reduce_only": reduce_only,
            "status": "WAITING_OCO" if normalized_order_type == "OCO" else "WAITING",
            "note": note or "条件触发后由模拟盘执行",
        }
        self.conditional_orders.append(order)
        append_ledger({"type": "condition_add", "order": order})
        self.persist()
        return order

    @synchronized
    def cancel_condition(self, order_id: str) -> None:
        for order in self.conditional_orders:
            if order["id"] == order_id and order["status"] in {"WAITING", "WAITING_LIMIT", "WAITING_OCO"}:
                order["status"] = "CANCELLED"
                order["updated_at"] = now_ms()
                append_ledger({"type": "condition_cancel", "id": order_id})
        self.persist()

    @synchronized
    def evaluate_conditionals(self, price: float) -> None:
        clean_market_price = _strict_finite_number(price)
        if clean_market_price is None or clean_market_price <= 0:
            append_ledger({"type": "condition_evaluation_block", "reason": "invalid_market_price"})
            return
        price = clean_market_price
        active_states = {"WAITING", "WAITING_LIMIT", "WAITING_OCO"}
        for order in self.conditional_orders:
            if order.get("status") not in active_states or order.get("symbol") != self.symbol:
                continue
            side = str(order.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                order["status"] = "REJECTED"
                order["updated_at"] = now_ms()
                order["reject_reason"] = "条件单方向无效"
                append_ledger({"type": "condition_reject", "order": order})
                self.persist("condition_invalid_side")
                continue

            quantity_pct = _strict_quantity_pct(order.get("quantity_pct"))
            order_type = str(order.get("order_type") or "MARKET").upper()
            numeric_prices = {
                "trigger_price": _strict_finite_number(order.get("trigger_price")),
                "limit_price": _strict_finite_number(order.get("limit_price")),
                "take_profit_price": _strict_finite_number(order.get("take_profit_price", 0.0)),
                "stop_loss_price": _strict_finite_number(order.get("stop_loss_price", 0.0)),
            }
            if (
                quantity_pct is None
                or order_type not in ORDER_TYPES
                or type(order.get("reduce_only")) is not bool
                or any(value is None or value < 0 for value in numeric_prices.values())
            ):
                order["status"] = "REJECTED"
                order["updated_at"] = now_ms()
                order["reject_reason"] = "Conditional order numeric or type contract is invalid."
                append_ledger({"type": "condition_reject", "order": order})
                self.persist("condition_numeric_contract_block")
                continue
            trigger = float(numeric_prices["trigger_price"])
            limit_price = float(numeric_prices["limit_price"])
            if order_type in PERSISTENT_ORDER_TYPES:
                order["status"] = "REJECTED"
                order["updated_at"] = now_ms()
                order["reject_reason"] = "持久 LIMIT/POST_ONLY 条件单尚未启用撮合与结算回调"
                append_ledger({"type": "condition_reject", "order": order})
                self.persist("condition_persistent_order_block")
                continue
            trigger_label = f"{trigger:.2f}"
            if order_type == "OCO":
                take_profit = float(numeric_prices["take_profit_price"])
                stop_loss = float(numeric_prices["stop_loss_price"])
                if side == "SELL":
                    triggered = (take_profit > 0 and price >= take_profit) or (stop_loss > 0 and price <= stop_loss)
                else:
                    triggered = (take_profit > 0 and price <= take_profit) or (stop_loss > 0 and price >= stop_loss)
                trigger_label = f"TP {take_profit:.2f} / SL {stop_loss:.2f}"
            else:
                triggered = (
                    order.get("status") == "WAITING_LIMIT"
                    or trigger <= 0
                    or (side == "BUY" and price <= trigger)
                    or (side == "SELL" and price >= trigger)
                )
            if not triggered:
                continue

            reduces_position = (
                (side == "BUY" and self.position_qty < 0)
                or (side == "SELL" and self.position_qty > 0)
            )
            if order.get("reduce_only") is True and not reduces_position:
                order["status"] = "REJECTED"
                order["updated_at"] = now_ms()
                order["reject_reason"] = "只减仓条件单不能增加或反向建立仓位"
                append_ledger({"type": "condition_reject", "order": order})
                self.persist("condition_reduce_only_block")
                continue

            idempotency_key = f"condition:{order.get('id')}"
            existing_order = next(
                (
                    item for item in reversed(self.orders)
                    if str(item.get("idempotency_key") or "") == idempotency_key
                ),
                None,
            )
            if existing_order is not None:
                order["status"] = "TRIGGERED"
                order["updated_at"] = now_ms()
                order["execution_order_id"] = existing_order.get("order_id")
                order["recovered_from_idempotency"] = True
                append_ledger({"type": "condition_recovered", "order": order})
                self.persist("condition_recovered")
                continue

            before_orders = len(self.orders)
            before_signals = len(self.signals)
            execution_order_type = "MARKET" if order_type == "OCO" else order_type
            self.manual_order(
                side,
                price,
                quantity_pct,
                execution_order_type,
                limit_price,
                idempotency_key=idempotency_key,
            )
            order["updated_at"] = now_ms()
            if len(self.orders) > before_orders:
                filled_order = self.orders[-1]
                condition_reason = str(order.get("note") or f"{order_type} 条件单触发 {trigger_label}")
                filled_order["reason"] = condition_reason
                filled_order["manual"] = False
                filled_order["condition_order_id"] = order.get("id")
                if len(self.signals) > before_signals:
                    self.signals[-1].update({"reason": condition_reason, "manual": False})
                order["status"] = "TRIGGERED"
                order["execution_order_id"] = filled_order.get("order_id")
                append_ledger({
                    "type": "condition_triggered",
                    "order": order,
                    "execution_order_id": filled_order.get("order_id"),
                })
            else:
                last_signal = self.signals[-1] if len(self.signals) > before_signals else {}
                signal_action = str(last_signal.get("action") or "REJECT").upper()
                if signal_action == "WAIT" and execution_order_type in {"LIMIT", "POST_ONLY"}:
                    order["status"] = "WAITING_LIMIT"
                else:
                    order["status"] = "REJECTED"
                order["reject_reason"] = str(last_signal.get("reason") or "条件单未成交")
                append_ledger({"type": "condition_no_fill", "order": order})
            self.persist("condition_evaluated")

    @synchronized
    def process_strategy_bars(
        self,
        rows: list[dict[str, Any]],
        *,
        source: str,
        price: float,
        execution_ready: bool,
    ) -> dict[str, Any]:
        if not self.armed:
            return self.snapshot(price)

        stamp = now_ms()
        previous_poll_ms = int(self.strategy_clock_last_poll_ms or 0)
        previous_seen_bar_ts = int(self.strategy_clock_last_seen_bar_ts or 0)
        transition = paper_clock_transition(
            rows=rows,
            now_ms=stamp,
            last_poll_ms=previous_poll_ms,
            last_seen_bar_ts=previous_seen_bar_ts,
            last_signal_bar_ts=int(self.last_strategy_signal_bar_ts or 0),
            pending_signal=self.pending_strategy_signal,
            execution_ready=execution_ready is True,
        )
        self.strategy_clock_source = str(source or "unknown")
        self.strategy_clock_last_poll_ms = stamp
        latest_bar_ts = int(transition.get("latest_bar_ts") or 0)

        latest_complete = transition.get("latest_complete_bar") or {}
        latest_complete_ts = int(latest_complete.get("ts_ms") or 0)
        if transition.get("status") == "DATA_BLOCK" or latest_complete_ts <= 0:
            self.strategy_clock_status = "DATA_BLOCK"
            self.persist("strategy_clock_data_block")
            return self.snapshot(price)

        if self.last_strategy_signal_bar_ts <= 0:
            self.last_strategy_signal_bar_ts = latest_complete_ts
            self.strategy_clock_last_seen_bar_ts = latest_bar_ts
            self.strategy_clock_status = "SYNCED_NO_BACKFILL"
            append_ledger({
                "type": "paper_strategy_clock_sync",
                "symbol": self.symbol,
                "strategy": self.strategy_id,
                "bar_ts": latest_complete_ts,
                "source": self.strategy_clock_source,
                "backfill": False,
            })
            self.persist("strategy_clock_sync")
            return self.snapshot(price)

        if transition.get("pending_expired") and self.pending_strategy_signal:
            expired = dict(self.pending_strategy_signal)
            self.pending_strategy_signal = {}
            self.strategy_clock_status = "PENDING_EXPIRED"
            self.signals.append({
                "time": stamp,
                "symbol": self.symbol,
                "action": "EXPIRE",
                "reason": "strategy_signal_expired_after_clock_downtime",
                "confidence": 1.0,
                "signal_bar_ts": int(expired.get("signal_bar_ts") or 0),
                "stage": "CLOCK_GAP",
            })
            append_ledger({
                "type": "paper_strategy_signal_expired",
                "symbol": self.symbol,
                "strategy": self.strategy_id,
                "signal": expired,
                "downtime_ms": int(transition.get("downtime_ms") or 0),
            })

        execution_bar = transition.get("execution_bar")
        if execution_bar and self.pending_strategy_signal:
            pending = dict(self.pending_strategy_signal)
            action = str(pending.get("action") or "HOLD").upper()
            execution_bar_ts = int(execution_bar.get("ts_ms") or 0)
            signal_bar_ts = int(pending.get("signal_bar_ts") or 0)
            idempotency_key = (
                f"strategy:{self.pipeline_run_id or 'unbound'}:{self.symbol}:"
                f"{self.strategy_id}:{signal_bar_ts}:{action}"
            )
            before_orders = len(self.orders)
            result_state = "SKIPPED_STATE_MISMATCH"
            if action == "BUY" and self.position_qty <= 0:
                self.open_long_manual(
                    price,
                    self.position_pct,
                    self.order_type,
                    0.0,
                    str(pending.get("reason") or "completed_bar_entry"),
                    manual=False,
                    idempotency_key=idempotency_key,
                    pretrade_result=self.execution_risk_check(
                        "BUY",
                        min(self.cash * 0.98, self.equity(price) * self.position_pct / 100 * self.leverage),
                        price,
                        self.order_type,
                        False,
                        idempotency_key,
                        signal_context=pending,
                    ),
                )
                result_state = "ORDER_ATTEMPTED"
            elif action in {"SELL", "EXIT"} and self.position_qty > 0:
                self.close_long_manual(
                    price,
                    100.0,
                    self.order_type,
                    0.0,
                    str(pending.get("reason") or "completed_bar_exit"),
                    manual=False,
                    idempotency_key=idempotency_key,
                    pretrade_result=self.execution_risk_check(
                        "SELL",
                        self.position_qty * price,
                        price,
                        self.order_type,
                        True,
                        idempotency_key,
                        signal_context=pending,
                    ),
                )
                result_state = "ORDER_ATTEMPTED"

            order_added = len(self.orders) > before_orders
            if order_added:
                self.orders[-1].update({
                    "signal_bar_ts": signal_bar_ts,
                    "execution_bar_ts": execution_bar_ts,
                    "fill_basis": "FIRST_OBSERVED_QUOTE_AFTER_NEW_BAR",
                    "strategy_clock_version": PAPER_STRATEGY_CLOCK_VERSION,
                })
                self.last_strategy_fill_bar_ts = execution_bar_ts
                result_state = "FILLED"
            self.last_strategy_attempt_bar_ts = execution_bar_ts
            self.pending_strategy_signal = {}
            self.strategy_clock_status = result_state
            append_ledger({
                "type": "paper_strategy_execution_attempt",
                "symbol": self.symbol,
                "strategy": self.strategy_id,
                "signal_bar_ts": signal_bar_ts,
                "execution_bar_ts": execution_bar_ts,
                "price": round(float(price), 8),
                "execution_ready": execution_ready is True,
                "status": result_state,
                "idempotency_key": idempotency_key,
                "signal_id": pending.get("signal_id"),
            })

        missed_bar = transition.get("missed_signal_bar")
        if missed_bar:
            missed_ts = int(missed_bar.get("ts_ms") or 0)
            self.last_strategy_signal_bar_ts = missed_ts
            self.strategy_clock_status = "MISSED_BAR_NO_BACKFILL"
            self.signals.append({
                "time": stamp,
                "symbol": self.symbol,
                "action": "SKIP",
                "reason": "completed_bar_transition_was_not_observed_live",
                "confidence": 1.0,
                "signal_bar_ts": missed_ts,
                "stage": "NO_BACKFILL",
            })
            append_ledger({
                "type": "paper_strategy_bar_missed",
                "symbol": self.symbol,
                "strategy": self.strategy_id,
                "bar_ts": missed_ts,
                "backfill": False,
            })

        signal_bar = transition.get("signal_bar")
        if signal_bar:
            signal_bar_ts = int(signal_bar.get("ts_ms") or 0)
            completed_bars = [
                dict(row)
                for row in transition.get("bars") or []
                if row.get("complete") is True and int(row.get("ts_ms") or 0) <= signal_bar_ts
            ]
            completed_closes = [
                float(row["close"])
                for row in completed_bars
            ]
            signal = evaluate_directional_strategy_signal(
                self.strategy_id,
                float(signal_bar.get("close") or 0.0),
                self.direction_mode,
                self.position_qty,
                self.entry_price,
                self.last_scale_price,
                closes=completed_closes,
                bars=completed_bars,
                symbol=self.symbol,
            )
            signal = {
                **signal,
                "time": stamp,
                "symbol": self.symbol,
                "signal_bar_ts": signal_bar_ts,
                "signal_price": round(float(signal_bar.get("close") or 0.0), 8),
                "stage": "COMPLETED_BAR_CLOSE",
                "strategy_clock_version": PAPER_STRATEGY_CLOCK_VERSION,
            }
            self.last_strategy_signal_bar_ts = signal_bar_ts
            self.signals.append(signal)
            action = str(signal.get("action") or "HOLD").upper()
            if action in {"BUY", "SELL", "EXIT"}:
                signal_idempotency_key = (
                    f"strategy:{self.pipeline_run_id or 'unbound'}:{self.symbol}:"
                    f"{self.strategy_id}:{signal_bar_ts}:{action}"
                )
                signal_lineage = build_signal_context(
                    {
                        "source": "strategy",
                        "strategy_id": self.strategy_id,
                        "run_id": self.pipeline_run_id,
                        "idempotency_key": signal_idempotency_key,
                        "signal_created_at": stamp,
                        "signal_action": action,
                        "signal_reason": str(signal.get("reason") or "completed_bar_signal"),
                    },
                    now_ms=now_ms,
                    symbol=self.symbol,
                    side=action,
                )
                signal.update({
                    "signal_id": signal_lineage["signal_id"],
                    "signal_created_at": signal_lineage["signal_created_at"],
                })
                self.pending_strategy_signal = {
                    "action": action,
                    "reason": str(signal.get("reason") or "completed_bar_signal"),
                    "confidence": float(signal.get("confidence") or 0.0),
                    "signal_id": signal_lineage["signal_id"],
                    "signal_created_at": signal_lineage["signal_created_at"],
                    "signal_action": signal_lineage["signal_action"],
                    "signal_reason": signal_lineage["signal_reason"],
                    "signal_bar_ts": signal_bar_ts,
                    "signal_price": float(signal_bar.get("close") or 0.0),
                    "created_at": stamp,
                    "strategy_id": self.strategy_id,
                    "symbol": self.symbol,
                }
                self.strategy_clock_status = "SIGNAL_PENDING_NEXT_BAR"
            else:
                self.strategy_clock_status = "BAR_PROCESSED_NO_ACTION"
            append_ledger({
                "type": "paper_strategy_completed_bar_signal",
                "symbol": self.symbol,
                "strategy": self.strategy_id,
                "signal": signal,
                "pending": bool(self.pending_strategy_signal),
            })

        self.strategy_clock_last_seen_bar_ts = latest_bar_ts
        self.signals = self.signals[-2000:]
        self.persist("strategy_clock_advance")
        return self.snapshot(price)

    @synchronized
    def evaluate(self, price: float) -> dict[str, Any]:
        if price <= 0:
            return self.snapshot(price)
        active_conditions = any(
            str(order.get("status") or "").upper() in {"WAITING", "WAITING_LIMIT", "WAITING_OCO", "MAKER_WAIT"}
            for order in self.conditional_orders
            if isinstance(order, dict)
        )
        if not self.armed and not active_conditions:
            return self.snapshot(price)
        self.evaluate_conditionals(price)
        self.refresh_trailing_prices(price)
        signal: dict[str, Any] | None = None
        if self.position_qty > 0 and self.trailing_stop_enabled and self.trailing_stop_price and price <= self.trailing_stop_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"移动止损触发 {self.trailing_stop_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty > 0 and self.trailing_take_enabled and self.trailing_take_price and price <= self.trailing_take_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"移动止盈回落触发 {self.trailing_take_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty > 0 and self.stop_loss_price and price <= self.stop_loss_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"止损触发 {self.stop_loss_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty > 0 and self.take_profit_price and price >= self.take_profit_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"止盈触发 {self.take_profit_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty < 0 and self.trailing_stop_enabled and self.trailing_stop_price and price >= self.trailing_stop_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"空头移动止损触发 {self.trailing_stop_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty < 0 and self.trailing_take_enabled and self.trailing_take_price and price >= self.trailing_take_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"空头移动止盈触发 {self.trailing_take_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty < 0 and self.stop_loss_price and price >= self.stop_loss_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"空头止损触发 {self.stop_loss_price:.2f}",
                "analysis": self.ai_analysis,
            }
        elif self.position_qty < 0 and self.take_profit_price and price <= self.take_profit_price:
            signal = {
                "action": "EXIT",
                "confidence": 1.0,
                "reason": f"空头止盈触发 {self.take_profit_price:.2f}",
                "analysis": self.ai_analysis,
            }
        else:
            signal = {
                "action": "HOLD",
                "confidence": 1.0,
                "reason": "quote_tick_risk_check_only",
            }
        signal_stamp = now_ms()
        signal.update({"time": signal_stamp, "symbol": self.symbol})
        if self.armed and signal["action"] != "HOLD":
            execution_side = "BUY" if self.position_qty < 0 else "SELL"
            idempotency_key = (
                f"risk-exit:{self.pipeline_run_id or 'unbound'}:{self.symbol}:"
                f"{signal_stamp}:{execution_side}"
            )
            signal_context = build_signal_context(
                {
                    "source": "quote_risk_exit",
                    "strategy_id": self.strategy_id,
                    "run_id": self.pipeline_run_id,
                    "idempotency_key": idempotency_key,
                    "signal_created_at": signal_stamp,
                    "signal_action": "EXIT",
                    "signal_reason": str(signal.get("reason") or "quote_risk_exit"),
                },
                now_ms=now_ms,
                symbol=self.symbol,
                side=execution_side,
            )
            signal.update({
                "signal_id": signal_context["signal_id"],
                "signal_created_at": signal_context["signal_created_at"],
            })
            self.signals.append(signal)
            action = signal["action"]
            if action in {"BUY", "EXIT"} and self.position_qty < 0:
                return self.close_short_manual(
                    price,
                    100.0,
                    self.order_type,
                    0.0,
                    signal["reason"],
                    manual=False,
                    idempotency_key=idempotency_key,
                    signal_context=signal_context,
                )
            if action in {"SELL", "EXIT"} and self.position_qty > 0:
                return self.close_long_manual(
                    price,
                    100.0,
                    self.order_type,
                    0.0,
                    signal["reason"],
                    manual=False,
                    idempotency_key=idempotency_key,
                    signal_context=signal_context,
                )
            return self.snapshot(price)
        self._record_equity(price)
        if self.armed:
            self.persist()
        return self.snapshot(price)
