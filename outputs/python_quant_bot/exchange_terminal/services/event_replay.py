from __future__ import annotations

import hashlib
import json
from typing import Any, Callable


AuditQuery = Callable[..., list[dict[str, Any]]]
OrderLoader = Callable[[str], dict[str, Any] | None]
RunOrderLoader = Callable[[str, int], list[dict[str, Any]]]


class EventReplayService:
    """Rebuilds and verifies the persisted market-to-fill evidence chain."""

    def __init__(
        self,
        *,
        now_ms: Callable[[], int],
        audit_query: AuditQuery,
        order_loader: OrderLoader,
        run_order_loader: RunOrderLoader,
    ) -> None:
        self.now_ms = now_ms
        self.audit_query = audit_query
        self.order_loader = order_loader
        self.run_order_loader = run_order_loader

    @staticmethod
    def _hash(payload: Any) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _check(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "status": "PASS" if ok else "BLOCK", "ok": bool(ok), "detail": detail})

    def replay_order(self, order_id: str) -> dict[str, Any]:
        clean_order_id = str(order_id or "").strip()
        order = self.order_loader(clean_order_id)
        if not order:
            return {"ok": False, "status": "NOT_FOUND", "order_id": clean_order_id, "checks": [], "live_order_allowed": False}

        risk_request_id = str(order.get("risk_request_id") or "")
        snapshot_id = str(order.get("market_snapshot_id") or "")
        signal_id = str(order.get("signal_id") or "")
        signal_events = self.audit_query(limit=50, signal_id=signal_id) if signal_id else []
        risk_events = self.audit_query(limit=200, request_id=risk_request_id) if risk_request_id else []
        snapshot_events = self.audit_query(limit=50, snapshot_id=snapshot_id) if snapshot_id else []
        transition_events = self.audit_query(limit=500, order_id=clean_order_id, event_type="paper_order_transition")
        risk_pass = next((event for event in risk_events if event.get("type") == "risk_pretrade_pass"), None)
        signal_event = next((event for event in signal_events if event.get("type") == "paper_signal"), None)
        market_snapshot = next((event for event in snapshot_events if event.get("type") == "market_snapshot"), None)
        transitions = list(order.get("transitions") or [])
        report = dict(order.get("execution_report") or {})
        filled_qty = float(report.get("filled_qty") or 0.0)
        fill_price = float(report.get("avg_price") or 0.0)
        filled_notional = float(report.get("filled_notional") or 0.0)
        calculated_notional = filled_qty * fill_price
        notional_tolerance = max(0.02, abs(filled_notional) * 0.0001)
        requested_qty = float(order.get("requested_qty") or report.get("requested_qty") or 0.0)
        quantity_tolerance = max(1e-10, abs(requested_qty) * 1e-8)
        quantity_constrained = bool(order.get("quantity_constrained") or report.get("quantity_constrained"))
        funding_charged = float(report.get("funding_charged") or 0.0)

        checks: list[dict[str, Any]] = []
        self._check(checks, "order_persisted", bool(clean_order_id), f"order_id={clean_order_id}")
        self._check(checks, "signal_link", bool(signal_id), f"signal_id={signal_id or '--'}")
        self._check(checks, "signal_persisted", bool(signal_event), "模拟信号事件已持久化" if signal_event else "缺少模拟信号事件")
        self._check(
            checks,
            "signal_order_link",
            bool(signal_event) and str(signal_event.get("order_id") or "") == clean_order_id,
            f"signal.order_id={(signal_event or {}).get('order_id') or '--'} / order_id={clean_order_id}",
        )
        self._check(checks, "risk_link", bool(risk_request_id), f"risk_request_id={risk_request_id or '--'}")
        self._check(checks, "risk_passed", bool(risk_pass), "统一风控通过事件已持久化" if risk_pass else "缺少统一风控通过事件")
        self._check(
            checks,
            "signal_risk_link",
            bool(risk_pass) and str(risk_pass.get("signal_id") or "") == signal_id,
            f"risk.signal_id={(risk_pass or {}).get('signal_id') or '--'} / signal_id={signal_id or '--'}",
        )
        self._check(
            checks,
            "risk_order_side",
            bool(risk_pass) and str(risk_pass.get("side") or "").upper() == str(order.get("side") or "").upper(),
            f"risk.side={(risk_pass or {}).get('side') or '--'} / order.side={order.get('side') or '--'}",
        )
        self._check(checks, "market_snapshot_link", bool(snapshot_id), f"snapshot_id={snapshot_id or '--'}")
        self._check(checks, "market_snapshot_persisted", bool(market_snapshot), "行情快照证据已持久化" if market_snapshot else "缺少行情快照证据")
        self._check(
            checks,
            "market_order_symbol",
            bool(market_snapshot) and str(market_snapshot.get("symbol") or "").upper() == str(order.get("symbol") or "").upper(),
            f"market.symbol={(market_snapshot or {}).get('symbol') or '--'} / order.symbol={order.get('symbol') or '--'}",
        )
        self._check(
            checks,
            "transition_sequence",
            bool(transitions) and str(transitions[-1].get("state") or "") == str(order.get("state") or ""),
            f"最后迁移={transitions[-1].get('state') if transitions else '--'} / 订单状态={order.get('state')}",
        )
        self._check(
            checks,
            "transition_audit",
            len(transition_events) >= len(transitions),
            f"订单内迁移 {len(transitions)} / 审计迁移 {len(transition_events)}",
        )
        if filled_qty > 0:
            self._check(
                checks,
                "fill_arithmetic",
                abs(calculated_notional - filled_notional) <= notional_tolerance,
                f"qty*price={calculated_notional:.8f} / filled_notional={filled_notional:.8f}",
            )
        else:
            self._check(checks, "fill_arithmetic", True, "订单无成交量，无需核对成交金额")
        self._check(
            checks,
            "fill_quantity_constraint",
            not quantity_constrained or requested_qty > 0 and filled_qty <= requested_qty + quantity_tolerance,
            f"filled_qty={filled_qty:.10f} / requested_qty={requested_qty:.10f} / constrained={quantity_constrained}",
        )
        self._check(
            checks,
            "fill_funding_is_estimate_only",
            abs(funding_charged) <= 1e-12,
            f"funding_charged={funding_charged:.8f}",
        )
        self._check(
            checks,
            "paper_only",
            str((risk_pass or {}).get("mode") or "PAPER").upper() != "LIVE",
            "事件链保持模拟盘模式",
        )

        evidence = {
            "signal": signal_event,
            "market_snapshot": market_snapshot,
            "risk_event": risk_pass or (risk_events[-1] if risk_events else None),
            "order": order,
            "transition_events": transition_events,
        }
        replay_hash = self._hash(evidence)
        passed = all(check.get("ok") for check in checks)
        return {
            "ok": passed,
            "status": "PASS" if passed else "BLOCK",
            "order_id": clean_order_id,
            "run_id": order.get("run_id"),
            "symbol": order.get("symbol"),
            "signal_id": signal_id,
            "risk_request_id": risk_request_id,
            "market_snapshot_id": snapshot_id,
            "checks": checks,
            "evidence": evidence,
            "replay_hash": replay_hash,
            "replayed_at": self.now_ms(),
            "deterministic": True,
            "live_order_allowed": False,
        }

    def replay_run(self, run_id: str, limit: int = 500) -> dict[str, Any]:
        clean_run_id = str(run_id or "").strip()
        orders = self.run_order_loader(clean_run_id, max(1, min(int(limit or 500), 2000)))
        traces = [self.replay_order(str(order.get("order_id") or "")) for order in orders]
        passed = sum(1 for trace in traces if trace.get("status") == "PASS")
        return {
            "ok": bool(orders) and passed == len(traces),
            "status": "PASS" if orders and passed == len(traces) else "BLOCK" if orders else "EMPTY",
            "run_id": clean_run_id,
            "order_count": len(orders),
            "passed_count": passed,
            "blocked_count": len(traces) - passed,
            "traces": traces,
            "replay_hash": self._hash([trace.get("replay_hash") for trace in traces]),
            "replayed_at": self.now_ms(),
            "live_order_allowed": False,
        }
