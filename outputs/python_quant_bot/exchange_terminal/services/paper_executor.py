from __future__ import annotations

from copy import deepcopy
import math
import secrets
import threading
from typing import Any, Callable

try:
    from market_data.okx import okx_first, okx_rows
    from services.event_lineage import build_signal_context
    from services.paper_order_contract import MAX_IDEMPOTENCY_KEY_LENGTH, ORDER_TYPES, PAPER_TERMINAL_STATES, validate_paper_lifecycle_order
    from utils import pct
except ModuleNotFoundError:
    try:
        from ..market_data.okx import okx_first, okx_rows
        from .event_lineage import build_signal_context
        from .paper_order_contract import MAX_IDEMPOTENCY_KEY_LENGTH, ORDER_TYPES, PAPER_TERMINAL_STATES, validate_paper_lifecycle_order
        from ..utils import pct
    except ImportError:
        from exchange_terminal.market_data.okx import okx_first, okx_rows
        from exchange_terminal.services.event_lineage import build_signal_context
        from exchange_terminal.services.paper_order_contract import MAX_IDEMPOTENCY_KEY_LENGTH, ORDER_TYPES, PAPER_TERMINAL_STATES, validate_paper_lifecycle_order
        from exchange_terminal.utils import pct


PERSISTENT_ORDER_TYPES = {"LIMIT", "POST_ONLY"}
MAX_RISK_AUTHORIZATION_AGE_MS = 15_000
MAX_RISK_AUTHORIZATION_FUTURE_SKEW_MS = 1_000
MAX_RISK_REQUEST_ID_LENGTH = 160

BookReader = Callable[[str, str], list[Any]]
FundingRateReader = Callable[[str], float]
AuditWriter = Callable[[dict[str, Any]], Any]
HistoryLoader = Callable[[], list[dict[str, Any]]]
OrderWriter = Callable[[dict[str, Any]], Any]
IdempotencyLoader = Callable[[str], dict[str, Any] | None]
RiskRequestLoader = Callable[[str], dict[str, Any] | None]


def finite_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def finite_nonnegative(value: Any) -> float:
    return max(finite_float(value), 0.0)


def strict_finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def numbers_match(left: float, right: float, *, absolute: float, relative: float) -> bool:
    return abs(left - right) <= max(absolute, abs(right) * relative)


def normalize_order_type(order_type: str | None) -> str:
    text = (order_type or "MARKET").upper()
    return text if text in ORDER_TYPES else "MARKET"


def simulated_execution_price(side: str, order_type: str, mark_price: float, limit_price: float = 0.0) -> float:
    clean_side = (side or "").upper()
    clean_order_type = normalize_order_type(order_type)
    if mark_price <= 0:
        return 0.0
    if clean_order_type in {"MARKET", "CURRENT"}:
        return mark_price
    if clean_order_type in {"LIMIT", "POST_ONLY", "IOC", "FOK"}:
        if limit_price <= 0:
            return 0.0
        if clean_side == "BUY" and mark_price <= limit_price:
            return min(mark_price, limit_price)
        if clean_side == "SELL" and mark_price >= limit_price:
            return max(mark_price, limit_price)
    return 0.0


def order_fee_rate(order_type: str) -> float:
    text = normalize_order_type(order_type)
    if text == "POST_ONLY":
        return 0.0002
    if text in {"LIMIT", "OCO"}:
        return 0.00035
    return 0.0005


def funding_rate_for_symbol(symbol: str) -> float:
    swap = str(symbol or "").upper()
    if not swap.endswith("-SWAP"):
        return 0.0
    try:
        row = okx_first("/api/v5/public/funding-rate", {"instId": swap})
        return pct(row.get("fundingRate", "0"))
    except Exception:
        return 0.0


def read_okx_book_side(symbol: str, side: str) -> list[Any]:
    payload = okx_rows("/api/v5/market/books", {"instId": symbol, "sz": "50"})
    book = payload[0] if payload else {}
    return book.get("asks" if side == "BUY" else "bids", []) or []


def rejected_report(
    side: str,
    order_type: str,
    mark_price: float,
    notional: float,
    note: str,
    *,
    requested_qty: float = 0.0,
) -> dict[str, Any]:
    clean_mark_price = finite_nonnegative(mark_price)
    clean_notional = finite_nonnegative(notional)
    clean_requested_qty = finite_nonnegative(requested_qty)
    clean_requested_notional = (
        clean_requested_qty * clean_mark_price
        if clean_requested_qty > 0 and clean_mark_price > 0
        else clean_notional
    )
    return {
        "status": "REJECTED",
        "avg_price": round(clean_mark_price, 6),
        "filled_notional": 0.0,
        "filled_qty": 0.0,
        "slippage_pct": 0.0,
        "fee": 0.0,
        "funding_estimate": 0.0,
        "funding_charged": 0.0,
        "funding_rate": 0.0,
        "levels_used": 0,
        "note": note,
        "side": (side or "").upper(),
        "order_type": str(order_type or "MARKET").upper(),
        "requested_notional": round(clean_requested_notional, 2),
        "requested_qty": round(clean_requested_qty, 8),
        "quantity_constrained": clean_requested_qty > 0,
    }


def simulated_execution_report(
    symbol: str,
    side: str,
    order_type: str,
    mark_price: float,
    notional: float,
    limit_price: float = 0.0,
    book_reader: BookReader | None = None,
    funding_rate_reader: FundingRateReader | None = None,
    requested_qty: float = 0.0,
) -> dict[str, Any]:
    mark_price = finite_nonnegative(mark_price)
    notional = finite_nonnegative(notional)
    limit_price = finite_nonnegative(limit_price)
    clean_side = (side or "").upper()
    clean_order_type = normalize_order_type(order_type)
    requested_qty_invalid = isinstance(requested_qty, bool)
    if not requested_qty_invalid:
        try:
            raw_requested_qty = float(requested_qty or 0.0)
        except (TypeError, ValueError, OverflowError):
            requested_qty_invalid = True
        else:
            requested_qty_invalid = not math.isfinite(raw_requested_qty) or raw_requested_qty < 0
    clean_requested_qty = finite_nonnegative(requested_qty)
    quantity_constrained = clean_requested_qty > 0
    requested_notional = notional
    warnings: list[str] = []
    if requested_qty_invalid:
        return {
            **rejected_report(clean_side, clean_order_type, mark_price, notional, "委托数量必须是有限非负数"),
            "quantity_contract_invalid": True,
        }
    if clean_side not in {"BUY", "SELL"}:
        return rejected_report(clean_side, clean_order_type, mark_price, notional, "订单方向无效", requested_qty=clean_requested_qty)
    if not isinstance(order_type, str) or (order_type or "MARKET").upper() not in ORDER_TYPES:
        return rejected_report(clean_side, order_type, mark_price, notional, "未知订单类型，已拒绝模拟", requested_qty=clean_requested_qty)
    if mark_price <= 0:
        return rejected_report(clean_side, clean_order_type, mark_price, notional, "标记价格无效", requested_qty=clean_requested_qty)
    if requested_notional <= 0:
        return rejected_report(clean_side, clean_order_type, mark_price, notional, "名义金额必须大于0", requested_qty=clean_requested_qty)
    if clean_order_type in {"LIMIT", "IOC", "FOK"} and limit_price <= 0:
        return rejected_report(clean_side, clean_order_type, mark_price, notional, "限价类订单缺少有效 limit_price", requested_qty=clean_requested_qty)
    if clean_order_type == "POST_ONLY":
        if limit_price <= 0:
            return rejected_report(clean_side, clean_order_type, mark_price, notional, "Post Only缺少有效 limit_price", requested_qty=clean_requested_qty)
        crosses_book = (clean_side == "BUY" and limit_price >= mark_price) or (clean_side == "SELL" and limit_price <= mark_price)
        if crosses_book:
            return rejected_report(clean_side, clean_order_type, mark_price, notional, "Post Only价格会立即成交，模拟拒单", requested_qty=clean_requested_qty)
        return {
            **rejected_report(clean_side, clean_order_type, mark_price, notional, "Post Only仅挂单，不主动吃单", requested_qty=clean_requested_qty),
            "status": "MAKER_WAIT",
        }

    report = {
        "status": "FILLED",
        "avg_price": round(mark_price, 6),
        "filled_notional": round(max(requested_notional, 0.0), 2),
        "filled_qty": round(clean_requested_qty if quantity_constrained else max(requested_notional, 0.0) / mark_price, 8),
        "slippage_pct": 0.0,
        "fee": round(max(requested_notional, 0.0) * order_fee_rate(clean_order_type), 4),
        "funding_estimate": 0.0,
        "funding_charged": 0.0,
        "funding_rate": 0.0,
        "levels_used": 0,
        "note": "最新价估算",
        "side": clean_side,
        "order_type": clean_order_type,
        "requested_notional": round(max(requested_notional, 0.0), 2),
        "requested_qty": round(clean_requested_qty, 8),
        "quantity_constrained": quantity_constrained,
        "limit_price": round(limit_price, 6) if limit_price else 0.0,
        "warnings": warnings,
    }

    rows: list[Any] = []
    try:
        reader = book_reader or read_okx_book_side
        rows = reader(symbol, clean_side)
    except Exception as exc:
        warnings.append(f"盘口读取失败，使用最新价估算：{exc}")
        rows = []

    if not rows and clean_order_type in {"LIMIT", "IOC", "FOK"}:
        status = "WAITING_LIMIT" if clean_order_type == "LIMIT" else "IOC_CANCELLED" if clean_order_type == "IOC" else "REJECTED"
        return {
            **rejected_report(clean_side, clean_order_type, mark_price, notional, "盘口不可用，限价类订单不模拟成交", requested_qty=clean_requested_qty),
            "status": status,
            "warnings": warnings,
        }

    if rows:
        remaining = clean_requested_qty if quantity_constrained else requested_notional
        remaining_notional = requested_notional
        filled_notional = 0.0
        filled_qty = 0.0
        levels_used = 0
        for level in rows:
            raw_price = level[0] if isinstance(level, (list, tuple)) and len(level) > 0 else 0
            raw_size = level[1] if isinstance(level, (list, tuple)) and len(level) > 1 else 0
            if isinstance(raw_price, bool) or isinstance(raw_size, bool):
                continue
            price = pct(raw_price)
            size = pct(raw_size)
            if not math.isfinite(price) or not math.isfinite(size) or price <= 0 or size <= 0:
                continue
            if clean_order_type in {"LIMIT", "IOC", "FOK"} and limit_price > 0:
                if clean_side == "BUY" and price > limit_price:
                    break
                if clean_side == "SELL" and price < limit_price:
                    break
            if quantity_constrained:
                affordable_qty = remaining_notional / price
                take_qty = min(remaining, size, affordable_qty)
                if take_qty <= 1e-12:
                    break
                filled_qty += take_qty
                level_fill_notional = take_qty * price
                filled_notional += level_fill_notional
                remaining -= take_qty
                remaining_notional = max(remaining_notional - level_fill_notional, 0.0)
            else:
                level_notional = price * size
                take = min(remaining, level_notional)
                filled_notional += take
                filled_qty += take / price
                remaining -= take
            levels_used += 1
            if remaining <= (1e-10 if quantity_constrained else 1e-6):
                break
        remainder_tolerance = 1e-10 if quantity_constrained else 1e-6
        if clean_order_type == "FOK" and remaining > remainder_tolerance:
            return rejected_report(clean_side, clean_order_type, mark_price, notional, "FOK未能全额成交", requested_qty=clean_requested_qty)
        if filled_notional <= 0:
            status = "WAITING_LIMIT" if clean_order_type in {"LIMIT", "IOC", "FOK"} else "REJECTED"
            return {
                **rejected_report(clean_side, clean_order_type, mark_price, notional, "盘口未触达委托价", requested_qty=clean_requested_qty),
                "status": status,
            }
        status = "PARTIAL" if remaining > remainder_tolerance else "FILLED"
        if clean_order_type == "IOC" and remaining > remainder_tolerance:
            status = "IOC_PARTIAL_CANCEL"
        avg_price = filled_notional / max(filled_qty, 1e-9)
        slippage = (avg_price / mark_price - 1) * 100 if clean_side == "BUY" else (mark_price / avg_price - 1) * 100
        report.update({
            "status": status,
            "avg_price": round(avg_price, 6),
            "filled_notional": round(filled_notional, 2),
            "filled_qty": round(filled_qty, 8),
            "slippage_pct": round(slippage, 4),
            "fee": round(filled_notional * order_fee_rate(clean_order_type), 4),
            "levels_used": levels_used,
            "note": "按OKX盘口深度模拟撮合",
        })

    try:
        funding_reader = funding_rate_reader or funding_rate_for_symbol
        funding_rate = funding_reader(symbol) if str(symbol or "").upper().endswith("-SWAP") else 0.0
    except Exception as exc:
        warnings.append(f"资金费率读取失败：{exc}")
        funding_rate = 0.0
    clean_funding_rate = finite_float(funding_rate)
    report["funding_rate"] = round(clean_funding_rate, 8)
    report["funding_estimate"] = round(report["filled_notional"] * clean_funding_rate, 4)
    report["funding_charged"] = 0.0
    report["warnings"] = warnings
    return report


class PaperExecutor:
    """Owns the simulated order lifecycle while account balances stay in PaperAccount."""

    TERMINAL_STATES = PAPER_TERMINAL_STATES

    def __init__(
        self,
        *,
        now_ms: Callable[[], int],
        audit_writer: AuditWriter | None = None,
        book_reader: BookReader | None = None,
        funding_rate_reader: FundingRateReader | None = None,
        history_loader: HistoryLoader | None = None,
        order_writer: OrderWriter | None = None,
        idempotency_loader: IdempotencyLoader | None = None,
        risk_request_loader: RiskRequestLoader | None = None,
        max_orders: int = 2000,
        instance_nonce: str | None = None,
        account_id: str = "default",
    ) -> None:
        self.now_ms = now_ms
        self.audit_writer = audit_writer
        self.book_reader = book_reader
        self.funding_rate_reader = funding_rate_reader
        self.history_loader = history_loader
        self.order_writer = order_writer
        self.idempotency_loader = idempotency_loader
        self.risk_request_loader = risk_request_loader
        self.max_orders = max(100, int(max_orders))
        self.account_id = str(account_id or "").strip() or "default"
        clean_instance_nonce = str(instance_nonce or "").strip().lower()
        self._instance_nonce = (
            clean_instance_nonce
            if 8 <= len(clean_instance_nonce) <= 64 and clean_instance_nonce.isalnum()
            else secrets.token_hex(8)
        )
        self._lock = threading.RLock()
        self._sequence = 0
        self._orders: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}
        self._risk_requests: dict[str, str] = {}
        self._restore_status = "NOT_CONFIGURED" if history_loader is None else "PENDING"
        self._restore_blockers: list[str] = []
        self._restore_error = ""
        self._restore()

    def _restore(self) -> None:
        if not self.history_loader:
            return
        try:
            rows = self.history_loader() or []
        except Exception as exc:
            self._restore_status = "BLOCK"
            self._restore_blockers = [f"paper_order_history_load_failed:{type(exc).__name__}"]
            self._restore_error = type(exc).__name__
            return
        if not isinstance(rows, (list, tuple)):
            self._restore_status = "BLOCK"
            self._restore_blockers = ["paper_order_history_invalid_type"]
            self._restore_error = type(rows).__name__
            return
        try:
            for row in rows[-self.max_orders:]:
                if not isinstance(row, dict):
                    raise ValueError("paper_order_history_row_invalid")
                nested_order = row.get("order")
                order = deepcopy(nested_order if isinstance(nested_order, dict) else row)
                validate_paper_lifecycle_order(order)
                order_id = str(order.get("order_id") or "")
                idempotency_key = str(order.get("idempotency_key") or "")
                existing_id = self._idempotency.get(idempotency_key) if idempotency_key else ""
                if existing_id and existing_id != order_id:
                    raise ValueError("paper_order_history_idempotency_conflict")
                risk_request_id = str(order.get("risk_request_id") or "")
                existing_risk_order_id = self._risk_requests.get(risk_request_id) if risk_request_id else ""
                if existing_risk_order_id and existing_risk_order_id != order_id:
                    raise ValueError("paper_order_history_risk_request_conflict")
                order.setdefault("persistence_status", "PERSISTED")
                self._orders[order_id] = order
                if idempotency_key:
                    self._idempotency[idempotency_key] = order_id
                if risk_request_id:
                    self._risk_requests[risk_request_id] = order_id
                state = str(order.get("state") or "").upper()
                if state == "WORKING":
                    self._transition(
                        order,
                        "EXPIRED",
                        "Persistent paper matching is not enabled; restored working order expired.",
                    )
                    self._persist_snapshot(order)
        except Exception as exc:
            self._orders.clear()
            self._idempotency.clear()
            self._risk_requests.clear()
            self._sequence = 0
            self._restore_status = "BLOCK"
            if isinstance(exc, ValueError) and str(exc).startswith("paper_order_history_"):
                blocker = str(exc)
            elif isinstance(exc, ValueError) and str(exc).startswith("paper_order_contract_"):
                blocker = f"paper_order_history_{exc}"
            else:
                blocker = f"paper_order_history_restore_failed:{type(exc).__name__}"
            self._restore_blockers = [blocker]
            self._restore_error = type(exc).__name__
            return
        restored_sequences = []
        for order_id in self._orders:
            try:
                restored_sequences.append(int(order_id.rsplit("-", 1)[-1]))
            except (TypeError, ValueError, OverflowError):
                continue
        self._sequence = max([len(self._orders), *restored_sequences])
        self._restore_status = "PASS"

    def _next_order_id(self) -> str:
        while True:
            self._sequence += 1
            order_id = f"paper-{self.now_ms()}-{self._instance_nonce}-{self._sequence:06d}"
            if order_id not in self._orders:
                return order_id

    @staticmethod
    def _request_signature(
        symbol: str,
        side: str,
        order_type: str,
        mark_price: float,
        notional: float,
        limit_price: float,
        requested_qty: float,
    ) -> str:
        parts = [
            str(symbol or "").upper(),
            str(side or "").upper(),
            normalize_order_type(order_type),
            f"{finite_nonnegative(mark_price):.8f}",
            f"{finite_nonnegative(notional):.8f}",
            f"{finite_nonnegative(limit_price):.8f}",
        ]
        clean_requested_qty = finite_nonnegative(requested_qty)
        if clean_requested_qty > 0:
            parts.append(f"{clean_requested_qty:.8f}")
        return "|".join(parts)

    @staticmethod
    def _report_from_order(order: dict[str, Any], *, idempotent_replay: bool = False) -> dict[str, Any]:
        raw_report = order.get("execution_report")
        if not isinstance(raw_report, dict):
            raise ValueError("paper_order_contract_execution_report_invalid")
        report = deepcopy(raw_report)
        return {
            **report,
            "order_id": order.get("order_id"),
            "account_id": order.get("account_id"),
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "order_type": order.get("order_type"),
            "mark_price": order.get("mark_price"),
            "limit_price": order.get("limit_price"),
            "requested_notional": order.get("requested_notional"),
            "requested_qty": order.get("requested_qty"),
            "quantity_constrained": order.get("quantity_constrained"),
            "reduce_only": order.get("reduce_only"),
            "lifecycle_state": order.get("state"),
            "transitions": deepcopy(list(order.get("transitions") or [])),
            "risk_request_id": order.get("risk_request_id"),
            "market_snapshot_id": order.get("market_snapshot_id"),
            "signal_id": order.get("signal_id"),
            "idempotency_key": order.get("idempotency_key"),
            "idempotent_replay": bool(idempotent_replay),
            "persistence_status": order.get("persistence_status", "UNKNOWN"),
            "audit_warnings": deepcopy(list(order.get("audit_warnings") or [])),
        }

    def _emit_audit(self, order: dict[str, Any], event: dict[str, Any]) -> None:
        if not self.audit_writer:
            return
        try:
            self.audit_writer(deepcopy(event))
        except Exception as exc:
            warning = f"{type(exc).__name__}: {exc}"
            warnings = order.setdefault("audit_warnings", [])
            if warning not in warnings:
                warnings.append(warning)

    def _transition(self, order: dict[str, Any], state: str, reason: str = "") -> None:
        row = {"state": state, "time": self.now_ms(), "reason": reason}
        order["state"] = state
        order["updated_at"] = row["time"]
        order.setdefault("transitions", []).append(row)
        self._emit_audit(order, {
                "type": "paper_order_transition",
                "order_id": order["order_id"],
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "source": order.get("source"),
                "strategy_id": order.get("strategy_id"),
                "run_id": order.get("run_id"),
                "risk_request_id": order.get("risk_request_id"),
                "market_snapshot_id": order.get("market_snapshot_id"),
                "signal_id": order.get("signal_id"),
                "state": state,
                "reason": reason,
            })

    def _persist_snapshot(self, order: dict[str, Any]) -> None:
        if self.order_writer:
            order["persistence_status"] = "PERSISTED"
            try:
                self.order_writer(deepcopy(order))
            except Exception:
                order["persistence_status"] = "FAILED"
                raise
        else:
            order["persistence_status"] = "MEMORY_ONLY"
        self._emit_audit(order, {
                "type": "paper_order_snapshot",
                "order_id": order.get("order_id"),
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "source": order.get("source"),
                "strategy_id": order.get("strategy_id"),
                "run_id": order.get("run_id"),
                "signal_id": order.get("signal_id"),
                "risk_request_id": order.get("risk_request_id"),
                "market_snapshot_id": order.get("market_snapshot_id"),
                "state": order.get("state"),
                "order": order,
            })

    def _resolve_persistence_race(self, order: dict[str, Any], error: Exception) -> dict[str, Any] | None:
        if str(error) not in {
            "paper_idempotency_key_conflict",
            "paper_lifecycle_identity_conflict",
        }:
            return None
        idempotency_key = str(order.get("idempotency_key") or "")
        if not idempotency_key or not self.idempotency_loader:
            return None
        try:
            winner = self.idempotency_loader(idempotency_key)
            validate_paper_lifecycle_order(winner)
        except Exception:
            return None
        if str(winner.get("request_signature") or "") != str(order.get("request_signature") or ""):
            return None
        winner = deepcopy(winner)
        losing_order_id = str(order.get("order_id") or "")
        winner_order_id = str(winner.get("order_id") or "")
        if losing_order_id != winner_order_id:
            self._orders.pop(losing_order_id, None)
            losing_risk_request_id = str(order.get("risk_request_id") or "")
            if self._risk_requests.get(losing_risk_request_id) == losing_order_id:
                self._risk_requests.pop(losing_risk_request_id, None)
        self._orders[winner_order_id] = winner
        self._idempotency[idempotency_key] = winner_order_id
        winner_risk_request_id = str(winner.get("risk_request_id") or "")
        if winner_risk_request_id:
            self._risk_requests[winner_risk_request_id] = winner_order_id
        self._emit_audit(order, {
            "type": "paper_order_persistence_race_resolved",
            "discarded_order_id": losing_order_id,
            "winner_order_id": winner_order_id,
            "idempotency_key": idempotency_key,
            "request_signature": order.get("request_signature"),
        })
        return winner

    def _persist_or_resolve(self, order: dict[str, Any]) -> dict[str, Any]:
        try:
            self._persist_snapshot(order)
            return order
        except Exception as exc:
            winner = self._resolve_persistence_race(order, exc)
            if winner is not None:
                return winner
            self._restore_status = "BLOCK"
            self._restore_blockers = [f"paper_order_persistence_failed:{type(exc).__name__}"]
            self._restore_error = type(exc).__name__
            self._emit_audit(order, {
                "type": "paper_order_persistence_failed",
                "order_id": order.get("order_id"),
                "risk_request_id": order.get("risk_request_id"),
                "state": order.get("state"),
                "error_type": type(exc).__name__,
            })
            raise

    def _risk_authorization_blockers(
        self,
        *,
        risk_result: Any,
        symbol: str,
        side: str,
        order_type: str,
        mark_price: float,
        notional: float,
        limit_price: float,
        requested_qty: float,
        idempotency_key: str,
        allow_expired: bool = False,
    ) -> list[str]:
        if not isinstance(risk_result, dict):
            return ["risk_result_object_required"]
        blockers: list[str] = []
        risk_context = risk_result.get("context")
        if not isinstance(risk_context, dict):
            risk_context = {}
            blockers.append("risk_context_object_required")

        request_id = risk_result.get("request_id")
        if (
            not isinstance(request_id, str)
            or not request_id.strip()
            or len(request_id.strip()) > MAX_RISK_REQUEST_ID_LENGTH
        ):
            blockers.append("risk_request_id_invalid")
        if risk_result.get("allowed") is not True:
            blockers.append("risk_not_allowed")
        if risk_result.get("paper_order_allowed") is not True:
            blockers.append("paper_order_not_authorized")
        if risk_result.get("live_order_allowed") is not False:
            blockers.append("live_order_boundary_invalid")
        if str(risk_result.get("mode") or "").upper() not in {"PAPER", "SHADOW", "SIMULATION"}:
            blockers.append("risk_mode_invalid")
        if str(risk_result.get("symbol") or "").upper() != str(symbol or "").upper():
            blockers.append("risk_symbol_mismatch")
        if str(risk_result.get("side") or "").upper() != str(side or "").upper():
            blockers.append("risk_side_mismatch")

        checked_at = risk_result.get("checked_at")
        if isinstance(checked_at, bool) or not isinstance(checked_at, int) or checked_at <= 0:
            blockers.append("risk_checked_at_invalid")
        elif not allow_expired:
            age_ms = self.now_ms() - checked_at
            if age_ms < -MAX_RISK_AUTHORIZATION_FUTURE_SKEW_MS:
                blockers.append("risk_checked_at_future")
            elif age_ms > MAX_RISK_AUTHORIZATION_AGE_MS:
                blockers.append("risk_authorization_expired")

        clean_mark_price = strict_finite(mark_price)
        clean_notional = strict_finite(notional)
        clean_limit_price = strict_finite(limit_price)
        approved_price = strict_finite(risk_result.get("requested_price"))
        approved_notional = strict_finite(risk_result.get("notional"))
        if clean_mark_price is None or clean_mark_price <= 0:
            blockers.append("order_mark_price_invalid")
        elif approved_price is None or not numbers_match(
            approved_price,
            clean_mark_price,
            absolute=1e-8,
            relative=1e-10,
        ):
            blockers.append("risk_price_mismatch")
        if clean_notional is None or clean_notional <= 0:
            blockers.append("order_notional_invalid")
        elif approved_notional is None or not numbers_match(
            approved_notional,
            clean_notional,
            absolute=0.011,
            relative=1e-8,
        ):
            blockers.append("risk_notional_mismatch")
        approved_limit_price = strict_finite(risk_context.get("limit_price"))
        if clean_limit_price is None or clean_limit_price < 0:
            blockers.append("order_limit_price_invalid")
        elif approved_limit_price is None or not numbers_match(
            approved_limit_price,
            clean_limit_price,
            absolute=1e-8,
            relative=1e-10,
        ):
            blockers.append("risk_limit_price_mismatch")

        raw_requested_qty = strict_finite(requested_qty)
        if raw_requested_qty is None or raw_requested_qty < 0:
            blockers.append("requested_quantity_invalid")
        elif raw_requested_qty > 0 and clean_mark_price is not None and clean_notional is not None:
            quantity_notional = raw_requested_qty * clean_mark_price
            if not numbers_match(quantity_notional, clean_notional, absolute=0.011, relative=1e-8):
                blockers.append("requested_quantity_notional_mismatch")

        raw_context_order_type = risk_context.get("order_type")
        if not isinstance(raw_context_order_type, str) or raw_context_order_type.upper() != order_type.upper():
            blockers.append("risk_order_type_mismatch")
        if type(risk_context.get("reduce_only")) is not bool:
            blockers.append("risk_reduce_only_contract_invalid")
        raw_context_idempotency = risk_context.get("idempotency_key", "")
        if not isinstance(raw_context_idempotency, str) or raw_context_idempotency.strip() != idempotency_key:
            blockers.append("risk_idempotency_key_mismatch")

        audit_status = risk_context.get("risk_audit_status")
        risk_reducing_contract = risk_context.get("risk_reducing_authoritative")
        if audit_status == "FAILED" and type(risk_reducing_contract) is not bool:
            blockers.append("risk_reduction_authority_contract_invalid")
        risk_reducing = risk_reducing_contract is True
        if audit_status != "PASS" and not (audit_status == "FAILED" and risk_reducing):
            blockers.append("risk_audit_not_durable")
        return blockers

    @staticmethod
    def _authorization_rejected(
        *,
        side: str,
        order_type: str,
        mark_price: float,
        notional: float,
        requested_qty: float,
        blockers: list[str],
    ) -> dict[str, Any]:
        report = rejected_report(
            side,
            order_type,
            mark_price,
            notional,
            "Risk authorization rejected: " + ", ".join(blockers),
            requested_qty=requested_qty,
        )
        return {
            **report,
            "lifecycle_state": "REJECTED",
            "risk_authorization_invalid": True,
            "risk_authorization_blockers": list(blockers),
            "persistence_status": "NOT_ATTEMPTED",
        }

    def submit(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        mark_price: float,
        notional: float,
        limit_price: float = 0.0,
        risk_result: dict[str, Any] | None,
        requested_qty: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if context is not None and not isinstance(context, dict):
            return self._authorization_rejected(
                side=side,
                order_type=order_type,
                mark_price=mark_price,
                notional=notional,
                requested_qty=requested_qty,
                blockers=["execution_context_object_required"],
            )
        clean_context = dict(context) if isinstance(context, dict) else {}
        clean_risk_result = risk_result if isinstance(risk_result, dict) else None
        with self._lock:
            if self._restore_status == "BLOCK":
                report = rejected_report(
                    side,
                    order_type,
                    mark_price,
                    notional,
                    "模拟订单历史恢复失败，已拒绝执行以防重复成交",
                    requested_qty=requested_qty,
                )
                return {
                    **report,
                    "lifecycle_state": "REJECTED",
                    "restore_status": self._restore_status,
                    "restore_blockers": list(self._restore_blockers),
                    "persistence_status": "RESTORE_BLOCKED",
                }
            raw_idempotency_key = clean_context.get("idempotency_key", "")
            idempotency_key = raw_idempotency_key.strip() if isinstance(raw_idempotency_key, str) else ""
            if (
                raw_idempotency_key is not None
                and raw_idempotency_key != ""
                and (
                    not isinstance(raw_idempotency_key, str)
                    or len(idempotency_key) > MAX_IDEMPOTENCY_KEY_LENGTH
                )
            ):
                invalid = rejected_report(
                    side,
                    order_type,
                    mark_price,
                    notional,
                    "Idempotency key must be a string of at most 160 characters.",
                    requested_qty=requested_qty,
                )
                return {
                    **invalid,
                    "lifecycle_state": "REJECTED",
                    "idempotency_contract_invalid": True,
                    "persistence_status": "NOT_ATTEMPTED",
                }
            if not isinstance(order_type, str) or str(order_type or "MARKET").upper() not in ORDER_TYPES:
                return self._authorization_rejected(
                    side=side,
                    order_type=order_type,
                    mark_price=mark_price,
                    notional=notional,
                    requested_qty=requested_qty,
                    blockers=["order_type_invalid"],
                )
            clean_order_type = str(order_type or "MARKET").upper()
            request_signature = self._request_signature(
                symbol,
                side,
                order_type,
                mark_price,
                notional,
                limit_price,
                requested_qty,
            )
            existing: dict[str, Any] | None = None
            if idempotency_key:
                existing_id = self._idempotency.get(idempotency_key)
                existing = self._orders.get(existing_id or "")
                if existing is None and self.idempotency_loader:
                    try:
                        loaded = self.idempotency_loader(idempotency_key)
                        if loaded is not None:
                            validate_paper_lifecycle_order(loaded)
                            existing = deepcopy(loaded)
                    except Exception as exc:
                        self._restore_status = "BLOCK"
                        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                        self._restore_blockers = [f"paper_idempotency_history_invalid:{detail}"]
                        self._restore_error = type(exc).__name__
                        blocked = rejected_report(
                            side,
                            order_type,
                            mark_price,
                            notional,
                            "Durable idempotency history is invalid; execution is blocked.",
                            requested_qty=requested_qty,
                        )
                        return {
                            **blocked,
                            "lifecycle_state": "REJECTED",
                            "restore_status": self._restore_status,
                            "restore_blockers": list(self._restore_blockers),
                            "persistence_status": "RESTORE_BLOCKED",
                        }
                    if existing and existing.get("order_id"):
                        self._orders[str(existing["order_id"])] = existing
                        self._idempotency[idempotency_key] = str(existing["order_id"])
                        restored_risk_request_id = str(existing.get("risk_request_id") or "")
                        if restored_risk_request_id:
                            self._risk_requests[restored_risk_request_id] = str(existing["order_id"])
                if existing is None and existing_id:
                    unavailable = rejected_report(
                        side,
                        order_type,
                        mark_price,
                        notional,
                        "幂等订单历史已移出内存且无持久记录，拒绝重复执行",
                        requested_qty=requested_qty,
                    )
                    return {
                        **unavailable,
                        "order_id": existing_id,
                        "lifecycle_state": "REJECTED",
                        "idempotency_key": idempotency_key,
                        "idempotency_history_unavailable": True,
                    }
                if existing:
                    existing_signature = str(existing.get("request_signature") or "")
                    compatible_signatures = {request_signature}
                    if finite_nonnegative(requested_qty) > 0 and "quantity_constrained" not in existing:
                        compatible_signatures.add(
                            self._request_signature(symbol, side, order_type, mark_price, notional, limit_price, 0.0)
                        )
                    if existing_signature not in compatible_signatures:
                        conflict = rejected_report(
                            side,
                            order_type,
                            mark_price,
                            notional,
                            "幂等键已用于不同的模拟订单请求",
                            requested_qty=requested_qty,
                        )
                        return {
                            **conflict,
                            "order_id": existing.get("order_id"),
                            "lifecycle_state": "REJECTED",
                            "idempotency_key": idempotency_key,
                            "idempotency_conflict": True,
                        }
                    replay_blockers = self._risk_authorization_blockers(
                        risk_result=clean_risk_result,
                        symbol=symbol,
                        side=side,
                        order_type=clean_order_type,
                        mark_price=mark_price,
                        notional=notional,
                        limit_price=limit_price,
                        requested_qty=requested_qty,
                        idempotency_key=idempotency_key,
                        allow_expired=True,
                    )
                    if replay_blockers:
                        return self._authorization_rejected(
                            side=side,
                            order_type=clean_order_type,
                            mark_price=mark_price,
                            notional=notional,
                            requested_qty=requested_qty,
                            blockers=replay_blockers,
                        )
                    if self.order_writer and str(existing.get("persistence_status") or "PERSISTED") in {"FAILED", "PENDING"}:
                        if not isinstance(existing.get("execution_report"), dict):
                            incomplete = rejected_report(
                                side,
                                order_type,
                                mark_price,
                                notional,
                                "Previous idempotent attempt stopped before execution; submit a new request key.",
                                requested_qty=requested_qty,
                            )
                            existing["execution_report"] = incomplete
                            self._transition(existing, "REJECTED", incomplete["note"])
                        existing = self._persist_or_resolve(existing)
                    return self._report_from_order(existing, idempotent_replay=True)

            authorization_blockers = self._risk_authorization_blockers(
                risk_result=clean_risk_result,
                symbol=symbol,
                side=side,
                order_type=clean_order_type,
                mark_price=mark_price,
                notional=notional,
                limit_price=limit_price,
                requested_qty=requested_qty,
                idempotency_key=idempotency_key,
            )
            if authorization_blockers:
                return self._authorization_rejected(
                    side=side,
                    order_type=clean_order_type,
                    mark_price=mark_price,
                    notional=notional,
                    requested_qty=requested_qty,
                    blockers=authorization_blockers,
                )

            risk_request_id = str(clean_risk_result.get("request_id") or "")
            existing_risk_order_id = self._risk_requests.get(risk_request_id)
            if not existing_risk_order_id and self.risk_request_loader:
                try:
                    durable_risk_order = self.risk_request_loader(risk_request_id)
                except Exception as exc:
                    return self._authorization_rejected(
                        side=side,
                        order_type=clean_order_type,
                        mark_price=mark_price,
                        notional=notional,
                        requested_qty=requested_qty,
                        blockers=[f"risk_request_history_unavailable:{type(exc).__name__}"],
                    )
                if durable_risk_order is not None:
                    try:
                        validate_paper_lifecycle_order(durable_risk_order)
                    except Exception:
                        return self._authorization_rejected(
                            side=side,
                            order_type=clean_order_type,
                            mark_price=mark_price,
                            notional=notional,
                            requested_qty=requested_qty,
                            blockers=["risk_request_history_invalid"],
                        )
                    existing_risk_order_id = str(durable_risk_order.get("order_id") or "")
                    if existing_risk_order_id:
                        self._risk_requests[risk_request_id] = existing_risk_order_id
            if existing_risk_order_id:
                return self._authorization_rejected(
                    side=side,
                    order_type=clean_order_type,
                    mark_price=mark_price,
                    notional=notional,
                    requested_qty=requested_qty,
                    blockers=["risk_authorization_already_consumed"],
                )

            order_id = self._next_order_id()
            risk_context = clean_risk_result.get("context") if isinstance((clean_risk_result or {}).get("context"), dict) else {}
            reduce_only_contract_valid = "reduce_only" not in risk_context or type(risk_context.get("reduce_only")) is bool
            signal_context = build_signal_context(
                {**clean_context, **risk_context},
                now_ms=self.now_ms,
                symbol=symbol,
                side=side,
            )
            order = {
                "order_id": order_id,
                "account_id": self.account_id,
                "symbol": str(symbol or "").upper(),
                "side": str(side or "").upper(),
                "order_type": clean_order_type,
                "mark_price": finite_nonnegative(mark_price),
                "limit_price": finite_nonnegative(limit_price),
                "requested_notional": finite_nonnegative(notional),
                "requested_qty": finite_nonnegative(requested_qty),
                "quantity_constrained": finite_nonnegative(requested_qty) > 0,
                "source": clean_context.get("source", "paper_account"),
                "strategy_id": clean_context.get("strategy_id"),
                "run_id": clean_context.get("run_id"),
                "market_snapshot_id": risk_context.get("market_snapshot_id") or clean_context.get("market_snapshot_id"),
                "risk_request_id": risk_request_id,
                "signal_id": signal_context.get("signal_id"),
                "signal_created_at": signal_context.get("signal_created_at"),
                "signal_action": signal_context.get("signal_action"),
                "signal_reason": signal_context.get("signal_reason"),
                "position_side_before": risk_context.get("position_side"),
                "reduce_only": risk_context.get("reduce_only") is True,
                "data_quality": risk_context.get("data_quality") if isinstance(risk_context.get("data_quality"), dict) else {},
                "idempotency_key": idempotency_key,
                "request_signature": request_signature,
                "created_at": self.now_ms(),
                "transitions": [],
                "persistence_status": "PENDING" if self.order_writer else "MEMORY_ONLY",
            }
            self._orders[order_id] = order
            if idempotency_key:
                self._idempotency[idempotency_key] = order_id
            self._risk_requests[risk_request_id] = order_id
            self._emit_audit(order, {
                    "type": "paper_signal",
                    "time": order.get("signal_created_at"),
                    "signal_id": order.get("signal_id"),
                    "order_id": order_id,
                    "request_id": order.get("risk_request_id"),
                    "market_snapshot_id": order.get("market_snapshot_id"),
                    "symbol": order.get("symbol"),
                    "action": order.get("signal_action"),
                    "reason": order.get("signal_reason"),
                    "source": order.get("source"),
                    "strategy_id": order.get("strategy_id"),
                    "run_id": order.get("run_id"),
                    "status": "OBSERVED",
                    "safe_action": "观察 / 仅研究 / 仅模拟盘验证",
                })
            self._transition(order, "CREATED", "Paper order accepted by lifecycle service.")

            if not reduce_only_contract_valid:
                report = rejected_report(
                    side,
                    order_type,
                    mark_price,
                    notional,
                    "Risk result reduce-only contract is invalid.",
                    requested_qty=requested_qty,
                )
                self._transition(order, "REJECTED", report["note"])
            elif clean_order_type in PERSISTENT_ORDER_TYPES:
                report = rejected_report(
                    side,
                    order_type,
                    mark_price,
                    notional,
                    "Persistent LIMIT and POST_ONLY paper orders are disabled until the matcher and settlement callback are available.",
                    requested_qty=requested_qty,
                )
                report["unsupported_capability"] = "persistent_order_matching"
                self._transition(order, "REJECTED", report["note"])
            else:
                self._transition(order, "RISK_CHECKED", "Unified risk service passed.")
                self._transition(order, "ACCEPTED", "Simulation engine accepted the order.")
                report = simulated_execution_report(
                    symbol,
                    side,
                    order_type,
                    mark_price,
                    notional,
                    limit_price,
                    self.book_reader,
                    self.funding_rate_reader,
                    requested_qty,
                )
                report_status = str(report.get("status") or "REJECTED")
                if report_status == "FILLED":
                    self._transition(order, "FILLED", report.get("note", ""))
                elif report_status == "PARTIAL":
                    self._transition(order, "PARTIALLY_FILLED", report.get("note", ""))
                    self._transition(order, "CANCELLED", "Unfilled immediate-order remainder cancelled.")
                elif report_status == "IOC_PARTIAL_CANCEL":
                    self._transition(order, "PARTIALLY_FILLED", report.get("note", ""))
                    self._transition(order, "CANCELLED", "IOC remainder cancelled.")
                elif report_status in {"WAITING_LIMIT", "MAKER_WAIT"}:
                    self._transition(order, "REJECTED", "Persistent matcher is unavailable; order cannot remain working.")
                elif report_status == "IOC_CANCELLED":
                    self._transition(order, "CANCELLED", report.get("note", ""))
                else:
                    self._transition(order, "REJECTED", report.get("note", ""))

            order["execution_report"] = report
            try:
                persisted_order = self._persist_or_resolve(order)
            except ValueError as exc:
                if str(exc) != "paper_risk_request_id_conflict":
                    raise
                self._orders.pop(order_id, None)
                if idempotency_key and self._idempotency.get(idempotency_key) == order_id:
                    self._idempotency.pop(idempotency_key, None)
                if self._risk_requests.get(risk_request_id) == order_id:
                    self._risk_requests.pop(risk_request_id, None)
                return self._authorization_rejected(
                    side=side,
                    order_type=clean_order_type,
                    mark_price=mark_price,
                    notional=notional,
                    requested_qty=requested_qty,
                    blockers=["risk_authorization_already_consumed"],
                )
            if persisted_order is not order:
                return self._report_from_order(persisted_order, idempotent_replay=True)
            report = self._report_from_order(order)
            if len(self._orders) > self.max_orders:
                oldest = next(iter(self._orders))
                self._orders.pop(oldest, None)
            return report

    def cancel(self, order_id: str, reason: str = "Cancelled by user.") -> dict[str, Any] | None:
        with self._lock:
            order = self._orders.get(order_id)
            if not order:
                return None
            if order.get("state") not in self.TERMINAL_STATES:
                self._transition(order, "CANCELLED", reason)
                self._persist_snapshot(order)
            return deepcopy(order)

    def get(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            order = self._orders.get(order_id)
            return deepcopy(order) if order else None

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            safe_limit = max(1, min(int(limit or 100), 1000))
            return [deepcopy(order) for order in list(self._orders.values())[-safe_limit:]][::-1]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            orders = list(self._orders.values())
            counts: dict[str, int] = {}
            for order in orders:
                state = str(order.get("state") or "UNKNOWN")
                counts[state] = counts.get(state, 0) + 1
            persistence_failed_count = sum(
                1 for order in orders if str(order.get("persistence_status") or "") == "FAILED"
            )
            return {
                "ok": True,
                "order_count": len(orders),
                "working_count": counts.get("WORKING", 0),
                "counts": counts,
                "persistence_failed_count": persistence_failed_count,
                "durability_mode": "DURABLE" if self.order_writer else "MEMORY_ONLY",
                "restart_ready": bool(self.order_writer and self.history_loader and self._restore_status == "PASS"),
                "restore_status": self._restore_status,
                "restore_blockers": list(self._restore_blockers),
                "restore_error": self._restore_error,
                "live_order_allowed": False,
            }
