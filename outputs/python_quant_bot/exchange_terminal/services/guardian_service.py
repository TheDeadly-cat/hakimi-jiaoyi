from __future__ import annotations

import threading
from typing import Any, Callable


class GuardianService:
    def __init__(
        self,
        *,
        profile: Any,
        account: Any,
        state_lock: threading.RLock,
        okx_first: Callable[[str, dict[str, str]], dict[str, Any]],
        pct: Callable[..., float],
        now_ms: Callable[[], int],
        append_ledger: Callable[[dict[str, Any]], None],
        risk_pretrade_check: Callable[..., dict[str, Any]],
        estimate_paper_notional: Callable[[float, float, float | None], float],
        paper_pretrade_context: Callable[..., dict[str, Any]],
        market_reader: Callable[[str, str], dict[str, Any]],
    ) -> None:
        self.profile = profile
        self.account = account
        self.state_lock = state_lock
        self.okx_first = okx_first
        self.pct = pct
        self.now_ms = now_ms
        self.append_ledger = append_ledger
        self.risk_pretrade_check = risk_pretrade_check
        self.estimate_paper_notional = estimate_paper_notional
        self.paper_pretrade_context = paper_pretrade_context
        self.market_reader = market_reader
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def interval_seconds(self) -> int:
        try:
            return max(5, min(int(self.profile.settings.get("refresh_seconds", 8)), 60))
        except Exception:
            return 8

    def emergency_stop(self, price: float = 0.0, reason: str = "风控急停", source: str = "manual") -> dict[str, Any]:
        with self.state_lock:
            paper = self.account.emergency_stop(price, reason)
            emergency = paper.get("emergency_stop") if isinstance(paper.get("emergency_stop"), dict) else {}
            flattened = emergency.get("safe_state_reached") is True
            status = str(emergency.get("status") or ("HALTED_FLAT" if flattened else "HALTED_WITH_POSITION"))
            self.profile.guardian.update({
                "enabled": False,
                "status": status,
                "heartbeat_ms": self.now_ms(),
                "last_symbol": self.account.symbol,
                "last_price": round(price or paper.get("mark_price", 0), 4),
                "last_action": "HALT",
                "last_equity": paper.get("equity", 0),
                "last_error": "" if flattened else str(emergency.get("flatten_error") or "position remains after emergency halt"),
                "message": reason if flattened else f"{reason}; strategy halted but paper position remains",
            })
            self.profile.notify("WARN", "风控急停", f"{source}：{reason}")
            self.append_ledger({
                "type": "guardian_emergency_stop",
                "source": source,
                "symbol": self.account.symbol,
                "reason": reason,
                "paper": paper,
            })
            self.profile.persist()
            return {
                "ok": flattened,
                "halted": True,
                "status": status,
                "flattened": flattened,
                "requires_attention": not flattened,
                "paper": paper,
                "profile": self.profile.snapshot(),
            }

    def circuit_reason(self, paper: dict[str, Any], price: float) -> str:
        drawdown = float(paper.get("drawdown_pct") or 0)
        if drawdown >= self.account.max_drawdown_pct:
            return f"最大回撤 {drawdown:.2f}% 已触发 {self.account.max_drawdown_pct:.2f}% 熔断线"
        liquidation_price = float(paper.get("liquidation_price") or 0)
        if price > 0 and liquidation_price > 0:
            distance = (price - liquidation_price) / price * 100
            if distance <= 2:
                return f"距离预估强平价仅 {distance:.2f}%，触发保护"
        if float(paper.get("available_cash") or 0) <= 0 and float(paper.get("position_value") or 0) > 0:
            return "可用保证金不足，触发保护"
        return ""

    def run_cycle(self, source: str = "daemon") -> dict[str, Any]:
        with self.state_lock:
            if self.profile.guardian.get("enabled") is not True:
                return {"ok": True, "enabled": False, "message": "guardian stopped"}
            self.profile.guardian["heartbeat_ms"] = self.now_ms()
            self.profile.guardian["cycles"] = int(self.profile.guardian.get("cycles", 0)) + 1
            self.profile.guardian["status"] = "RUNNING"

        if not self.account.armed:
            with self.state_lock:
                self.profile.guardian["last_symbol"] = self.account.symbol
                self.profile.guardian["last_action"] = "WAIT"
                self.profile.guardian["last_error"] = ""
                self.profile.guardian["message"] = "后台守护运行中，等待策略启动"
                self.profile.persist()
                return {"ok": True, "enabled": True, "armed": False, "message": self.profile.guardian["message"]}

        symbol = self.account.symbol
        try:
            market = self.market_reader(symbol, source)
            price = self.pct(market.get("price", "0"))
            if price <= 0:
                raise RuntimeError(f"{symbol} authoritative quote is unavailable")

            risk_check = self.risk_pretrade_check(
                symbol,
                "ARM",
                "PAPER",
                self.estimate_paper_notional(price, self.account.position_pct, self.account.leverage),
                price,
                self.paper_pretrade_context(
                    price,
                    {
                        "direction_mode": self.account.direction_mode,
                        "reduce_only": self.account.reduce_only,
                        "order_type": self.account.order_type,
                        "margin_mode": self.account.margin_mode,
                    },
                    leverage=self.account.leverage,
                    position_pct=self.account.position_pct,
                    source=source,
                ),
            )

            with self.state_lock:
                before_orders = len(self.account.orders)
                before_signals = len(self.account.signals)
                self.account.process_strategy_bars(
                    list(market.get("rows") or []),
                    source=str(market.get("source") or "unknown"),
                    price=price,
                    execution_ready=market.get("execution_ready") is True,
                )
                paper = self.account.evaluate(price)
                circuit_reason = self.circuit_reason(paper, price)
                if circuit_reason:
                    return self.emergency_stop(price, circuit_reason, source)
                latest_signal = self.account.signals[-1] if self.account.signals else {}
                latest_order = self.account.orders[-1] if self.account.orders else {}
                order_added = len(self.account.orders) > before_orders
                signal_added = len(self.account.signals) > before_signals
                action = latest_order.get("side") if order_added else latest_signal.get("action", "HOLD")
                risk_allowed = risk_check.get("allowed") is True
                cycle_status = "RUNNING" if risk_allowed else "RISK_BLOCK"
                cycle_error = "" if risk_allowed else str(risk_check.get("reason") or "risk blocked")
                self.profile.guardian.update({
                    "status": cycle_status,
                    "last_symbol": symbol,
                    "last_price": round(price, 4),
                    "last_action": action or "HOLD",
                    "last_equity": paper.get("equity", 0),
                    "last_error": cycle_error,
                    "message": f"后台{source}评估 {symbol}，价格 {price:.4f}，动作 {action or 'HOLD'}",
                })
                self.append_ledger({
                    "type": "guardian_cycle",
                    "source": source,
                    "symbol": symbol,
                    "price": round(price, 4),
                    "action": action,
                    "equity": paper.get("equity"),
                    "order_added": order_added,
                    "signal_added": signal_added,
                    "market_source": market.get("source"),
                    "market_snapshot_id": market.get("snapshot_id"),
                    "execution_ready": market.get("execution_ready") is True,
                    "clock_data_allowed": market.get("clock_data_allowed") is True,
                    "risk_check": {
                        "status": risk_check.get("status"),
                        "reason": risk_check.get("reason"),
                    },
                })
                if not risk_allowed:
                    self.append_ledger({
                        "type": "guardian_risk_block",
                        "source": source,
                        "symbol": symbol,
                        "price": round(price, 4),
                        "risk_check": risk_check,
                    })
                if order_added:
                    self.profile.notify(
                        "INFO",
                        "后台自动模拟成交",
                        f"{symbol} {latest_order.get('side')} @ {latest_order.get('price')}，原因：{latest_order.get('reason', '--')}",
                    )
                else:
                    self.profile.persist()
                return {
                    "ok": True,
                    "enabled": True,
                    "armed": True,
                    "paper": paper,
                    "risk_check": risk_check,
                    "market": {
                        "symbol": market.get("symbol"),
                        "source": market.get("source"),
                        "snapshot_id": market.get("snapshot_id"),
                        "execution_ready": market.get("execution_ready"),
                        "clock_data_allowed": market.get("clock_data_allowed"),
                    },
                }
        except Exception as exc:
            with self.state_lock:
                self.profile.guardian["status"] = "ERROR"
                self.profile.guardian["last_error"] = str(exc)
                self.profile.guardian["message"] = f"后台守护异常：{exc}"
                self.profile.persist()
            self.append_ledger({"type": "guardian_error", "source": source, "symbol": symbol, "error": str(exc)})
            return {"ok": False, "enabled": True, "error": str(exc)}

    def worker(self) -> None:
        while not self.stop_event.wait(self.interval_seconds()):
            if self.profile.guardian.get("enabled") is True:
                self.run_cycle("daemon")

    def start_worker(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.worker, name="quantx-guardian", daemon=True)
        self.thread.start()

    def stop_worker(self) -> None:
        self.stop_event.set()
