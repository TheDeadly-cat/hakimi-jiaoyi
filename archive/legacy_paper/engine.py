from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
import time

from exchange_terminal.domain.contracts import build_candle_decision_id

from quant_bot.config import BotConfig
from quant_bot.data import MarketDataProvider
from quant_bot.execution import BrokerBase
from quant_bot.models import Action, Portfolio
from quant_bot.risk import RiskManager
from quant_bot.strategies.base import StrategyBase

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(self, config: BotConfig, data_provider: MarketDataProvider, strategy: StrategyBase, risk_manager: RiskManager, broker: BrokerBase):
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.risk = risk_manager
        self.broker = broker
        self.portfolio = Portfolio(cash=config.initial_cash)
        self.active_stop_loss: float | None = None
        self.active_take_profit: float | None = None
        self.last_price: float | None = None
        self._risk_session = ""
        self._last_equity = float(config.initial_cash)
        self._decision_scope = f"{self.config.name}|{self.config.symbol}|{self.config.timeframe}|{self.strategy.name}"
        self._decision_state_path = Path(self.config.logging.log_dir).parent / "legacy_engine_decision_state.json"
        self._decision_state: dict[str, str] = {}
        self._load_decision_state()

    def _load_decision_state(self) -> None:
        path = self._decision_state_path
        try:
            if not path.exists():
                return
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            state = raw.get("decisions")
            if not isinstance(state, dict):
                return
            for key, value in state.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                self._decision_state[key] = value
        except Exception:
            logger.warning("failed to load legacy engine decision state from %s", path, exc_info=True)

    def _persist_decision_state(self) -> None:
        path = self._decision_state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "decisions": self._decision_state}
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        if path.exists():
            try:
                shutil.copy2(path, backup_path)
            except Exception:
                pass
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as handle:
                handle.write(serialized)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
                temp_path = Path(handle.name)
            os.replace(temp_path, path)
            try:
                _ = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError("decision state is corrupt") from exc
        except Exception:
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, path)
                except Exception:
                    pass
            raise

    def _latest_bar_id(self, data) -> str:
        try:
            if not len(data.index):
                return "UNSPECIFIED"
            return str(data.index[-1])
        except Exception:
            return "UNSPECIFIED"

    def _is_duplicate_decision(self, bar_id: str, decision_id: str) -> bool:
        return self._decision_state.get(self._decision_scope) == f"{bar_id}:{decision_id}"

    def _reserve_decision(self, bar_id: str, decision_id: str) -> None:
        reservation = f"{bar_id}:{decision_id}"
        previous = self._decision_state.get(self._decision_scope)
        self._decision_state[self._decision_scope] = reservation
        try:
            self._persist_decision_state()
        except Exception as exc:
            if previous is None:
                self._decision_state.pop(self._decision_scope, None)
            else:
                self._decision_state[self._decision_scope] = previous
            raise RuntimeError(
                "failed to reserve candle decision before broker submission"
            ) from exc

    def run_once(self) -> None:
        data = self.data_provider.get_latest(self.config.symbol, self.config.timeframe, self.config.data.history_limit)
        price = float(data["close"].iloc[-1])
        self.last_price = price
        session = str(data.index[-1])[:10] if len(data.index) else "UNSPECIFIED"
        if session != self._risk_session:
            self.risk.reset_day(self._last_equity)
            self._risk_session = session
        forced_order = self.risk.enforce_stop_rules(self.config.symbol, self.portfolio, price, self.active_stop_loss, self.active_take_profit)
        if forced_order is not None:
            fill = self.broker.submit_order(forced_order, self.portfolio)
            logger.info("risk fill=%s equity=%.2f", fill, self.portfolio.equity(price))
            if self.portfolio.position_qty <= 0:
                self.active_stop_loss = None
                self.active_take_profit = None
            self._last_equity = self.portfolio.equity(price)
            return

        signal = self.strategy.generate_signal(data, self.portfolio)
        bar_id = self._latest_bar_id(data)
        decision_id = build_candle_decision_id(
            strategy=self.strategy.name,
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            candle_close_time=bar_id,
            action=getattr(signal.action, "value", "NONE"),
            strategy_version=getattr(self.strategy, "version", None),
        )

        if signal.action != Action.HOLD and self._is_duplicate_decision(bar_id, decision_id):
            logger.info("skip duplicate candle decision id=%s", decision_id)
            self._last_equity = self.portfolio.equity(price)
            return

        order = self.risk.signal_to_order(
            self.config.symbol,
            signal,
            self.portfolio,
            price,
            fee_rate=self.config.execution.fee_rate,
            slippage_pct=self.config.execution.slippage_pct,
        )
        logger.info("signal=%s reason=%s price=%.4f equity=%.2f", signal.action, signal.reason, price, self.portfolio.equity(price))
        if order:
            self._reserve_decision(bar_id, decision_id)
            try:
                fill = self.broker.submit_order(order, self.portfolio)
            except Exception:
                logger.error(
                    "broker submission outcome is unknown; retaining candle "
                    "decision reservation id=%s",
                    decision_id,
                    exc_info=True,
                )
                raise
            logger.info("fill=%s equity=%.2f", fill, self.portfolio.equity(price))
            if order.action == Action.BUY:
                self.active_stop_loss = self.risk.effective_stop_loss(signal.stop_loss_pct)
                self.active_take_profit = signal.take_profit_pct
            elif self.portfolio.position_qty <= 0:
                self.active_stop_loss = None
                self.active_take_profit = None
        self._last_equity = self.portfolio.equity(price)

    def run(self, cycles: int | None = None) -> None:
        count = 0
        logger.info("Trading engine started: mode=%s strategy=%s symbol=%s", self.config.mode, self.strategy.name, self.config.symbol)
        while cycles is None or count < cycles:
            try:
                self.run_once()
            except Exception:
                logger.exception("engine cycle failed")
            count += 1
            if cycles is not None and count >= cycles:
                break
            time.sleep(max(1, self.config.execution.poll_seconds))
