from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import json
import math

import numpy as np
import pandas as pd

from hakimi_research.config import BotConfig
from hakimi_research.experiment_manifest import build_reproducible_experiment_manifest
from hakimi_research.execution import ResearchExecutionSimulator
from hakimi_research.models import Action, Fill, Order, Portfolio, Signal
from hakimi_research.risk import RiskManager
from quant_bot.strategies.base import StrategyBase


EXECUTION_MODEL_VERSION = "signal-close-next-open-ohlc-conservative-v3"


@dataclass
class BacktestReport:
    total_return: float
    annualized_return: float
    max_drawdown: float
    win_rate: float
    sharpe_ratio: float
    trades: int
    final_equity: float
    equity_curve: list[dict]
    fills: list[dict]
    total_fees: float
    ambiguous_intrabar_count: int
    execution_model: str
    reproducibility: dict
    experiment_manifest: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio,
            "trades": self.trades,
            "final_equity": self.final_equity,
            "equity_curve": self.equity_curve,
            "fills": self.fills,
            "total_fees": self.total_fees,
            "ambiguous_intrabar_count": self.ambiguous_intrabar_count,
            "execution_model": self.execution_model,
            "reproducibility": self.reproducibility,
            "experiment_manifest": self.experiment_manifest,
        }


class BacktestEngine:
    def __init__(
        self,
        config: BotConfig,
        strategy: StrategyBase,
        risk_manager: RiskManager,
        experiment_context: dict | None = None,
    ):
        if (
            type(config) is not BotConfig
            or type(config.mode) is not str
            or config.mode != "backtest"
            or type(config.execution.broker) is not str
            or config.execution.broker != "research_simulator"
            or type(config.execution.live_trading_enabled) is not bool
            or config.execution.live_trading_enabled is not False
        ):
            raise ValueError(
                "BacktestEngine requires exact backtest-only execution authority."
            )
        self.config = config
        self.strategy = strategy
        self.risk = risk_manager
        self.experiment_context = (
            dict(experiment_context) if type(experiment_context) is dict else {}
        )
        self.execution_simulator = ResearchExecutionSimulator(config.execution.fee_rate, config.execution.slippage_pct)

    def run(self, data: pd.DataFrame) -> BacktestReport:
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Backtest data must be a pandas DataFrame.")
        required = {"open", "high", "low", "close"}
        missing = sorted(required.difference(data.columns))
        if missing:
            raise ValueError(f"Backtest data is missing required OHLC columns: {', '.join(missing)}")
        if not data.index.is_monotonic_increasing or data.index.has_duplicates:
            raise ValueError("Backtest data index must be strictly increasing and unique.")
        self._validate_numeric_configuration()
        self._validate_market_data(data)
        reproducibility = self._reproducibility(data)
        portfolio = Portfolio(cash=self.config.initial_cash)
        self.risk.reset_day(self.config.initial_cash)
        equity_curve: list[dict] = []
        fills: list[Fill] = []
        fill_records: list[dict] = []
        active_stop_loss = None
        active_take_profit = None
        ambiguous_intrabar_count = 0
        active_session = ""
        previous_close_equity = float(self.config.initial_cash)
        session_labels = self._session_labels(data.index)

        def append_fill(fill: Fill, *, signal_time: str, fill_time: str, fill_basis: str) -> None:
            fills.append(fill)
            fill_records.append({
                **fill.__dict__,
                "action": fill.action.value,
                "signal_time": signal_time,
                "fill_time": fill_time,
                "fill_basis": fill_basis,
            })

        start_index = 30
        pending_signal: Signal = self.strategy.generate_signal(data.iloc[:start_index], portfolio) if len(data) >= start_index else Signal.hold("not enough data")
        pending_signal_time = str(data.index[start_index - 1]) if len(data) >= start_index else ""

        for index in range(start_index, len(data)):
            window = data.iloc[: index + 1]
            row = window.iloc[-1]
            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            fill_time = str(window.index[-1])
            session = session_labels[index]
            if session != active_session:
                self.risk.reset_day(previous_close_equity)
                active_session = session

            order = self.risk.signal_to_order(
                self.config.symbol,
                pending_signal,
                portfolio,
                open_price,
                fee_rate=self.config.execution.fee_rate,
                slippage_pct=self.config.execution.slippage_pct,
            )
            if order is not None:
                order = Order(
                    order.symbol,
                    order.action,
                    order.quantity,
                    open_price,
                    order.reason,
                    is_live=order.is_live,
                )
                fill = self.execution_simulator.submit_order(order, portfolio)
                append_fill(fill, signal_time=pending_signal_time, fill_time=fill_time, fill_basis="NEXT_BAR_OPEN")
                if order.action == Action.BUY:
                    active_stop_loss = self.risk.effective_stop_loss(pending_signal.stop_loss_pct)
                    active_take_profit = pending_signal.take_profit_pct
                elif portfolio.position_qty <= 0:
                    active_stop_loss = None
                    active_take_profit = None

            if portfolio.position_qty > 0 and portfolio.avg_entry_price > 0:
                stop_price = portfolio.avg_entry_price * (1 - abs(active_stop_loss)) if active_stop_loss is not None else 0.0
                target_price = portfolio.avg_entry_price * (1 + abs(active_take_profit)) if active_take_profit is not None else 0.0
                stop_hit = bool(stop_price and (open_price <= stop_price or low <= stop_price))
                target_hit = bool(target_price and (open_price >= target_price or high >= target_price))
                if stop_hit and target_hit:
                    ambiguous_intrabar_count += 1
                if stop_hit or target_hit:
                    if stop_hit:
                        raw_exit = open_price if open_price <= stop_price else stop_price
                        reason = "conservative intrabar stop"
                        basis = "GAP_OPEN" if open_price <= stop_price else "INTRABAR_STOP"
                    else:
                        raw_exit = target_price
                        reason = "intrabar take profit"
                        basis = "INTRABAR_TARGET"
                    forced = Order(self.config.symbol, Action.SELL, portfolio.position_qty, raw_exit, reason)
                    fill = self.execution_simulator.submit_order(forced, portfolio)
                    append_fill(fill, signal_time=fill_time, fill_time=fill_time, fill_basis=basis)
                    active_stop_loss = None
                    active_take_profit = None

            previous_close_equity = portfolio.equity(close)
            equity_curve.append({"time": fill_time, "equity": previous_close_equity})
            pending_signal = self.strategy.generate_signal(window, portfolio)
            pending_signal_time = fill_time

        curve = pd.DataFrame(equity_curve)
        if curve.empty:
            final_equity = self.config.initial_cash
            returns = pd.Series(dtype=float)
            max_drawdown = 0.0
        else:
            final_equity = float(curve["equity"].iloc[-1])
            returns = curve["equity"].pct_change().fillna(0)
            running_max = curve["equity"].cummax()
            drawdowns = curve["equity"] / running_max - 1
            max_drawdown = float(abs(drawdowns.min()))

        total_return = final_equity / self.config.initial_cash - 1
        bars_per_year = self._bars_per_year()
        if len(returns) > 1:
            elapsed_years = self._elapsed_years(data.index[start_index:], bars_per_year)
            annualized_return = float((1 + total_return) ** (1 / elapsed_years) - 1) if total_return > -1 else -1.0
            sharpe = float(np.sqrt(bars_per_year) * returns.mean() / (returns.std() or np.nan))
            if np.isnan(sharpe):
                sharpe = 0.0
        else:
            annualized_return = 0.0
            sharpe = 0.0
        closed = [fill for fill in fills if fill.action.value == "SELL"]
        wins = [fill for fill in closed if fill.pnl > 0]
        win_rate = len(wins) / len(closed) if closed else 0.0
        report = BacktestReport(
            total_return=round(total_return, 6),
            annualized_return=round(annualized_return, 6),
            max_drawdown=round(max_drawdown, 6),
            win_rate=round(win_rate, 6),
            sharpe_ratio=round(sharpe, 6),
            trades=len(fills),
            final_equity=round(final_equity, 2),
            equity_curve=[{"time": row["time"], "equity": round(float(row["equity"]), 2)} for row in equity_curve],
            fills=fill_records,
            total_fees=round(sum(fill.fee for fill in fills), 6),
            ambiguous_intrabar_count=ambiguous_intrabar_count,
            execution_model=EXECUTION_MODEL_VERSION,
            reproducibility=reproducibility,
        )
        result_payload = report.to_dict()
        result_payload.pop("experiment_manifest", None)
        report.experiment_manifest = build_reproducible_experiment_manifest(
            result_payload=result_payload,
            reproducibility=reproducibility,
            strategy_name=self.strategy.name,
            strategy_version=str(getattr(self.strategy, "version", "") or ""),
            symbol=self.config.symbol,
            timeframe=self.config.timeframe,
            fee_rate=self.config.execution.fee_rate,
            slippage_pct=self.config.execution.slippage_pct,
            context=self.experiment_context,
        )
        return report

    def _validate_numeric_configuration(self) -> None:
        risk_contract = asdict(self.config.risk)
        values = {
            "initial_cash": self.config.initial_cash,
            "fee_rate": self.config.execution.fee_rate,
            "slippage_pct": self.config.execution.slippage_pct,
            **{f"risk.{name}": value for name, value in risk_contract.items()},
        }
        invalid: list[str] = []
        parsed: dict[str, float] = {}
        for name, value in values.items():
            try:
                parsed[name] = float(value)
            except (TypeError, ValueError, OverflowError):
                invalid.append(f"{name}:not_numeric")
                continue
            if not math.isfinite(parsed[name]):
                invalid.append(f"{name}:not_finite")
        if invalid:
            raise ValueError("Backtest numeric configuration is invalid: " + ", ".join(invalid))
        if parsed["initial_cash"] <= 0:
            invalid.append("initial_cash:must_be_positive")
        for name in ("fee_rate", "slippage_pct"):
            if not 0 <= parsed[name] < 1:
                invalid.append(f"{name}:must_be_in_[0,1)")
        for name in (
            "risk.max_position_pct",
            "risk.max_single_loss_pct",
            "risk.max_daily_loss_pct",
            "risk.min_cash_pct",
        ):
            if not 0 <= parsed[name] <= 1:
                invalid.append(f"{name}:must_be_in_[0,1]")
        if parsed["risk.max_leverage"] <= 0:
            invalid.append("risk.max_leverage:must_be_positive")
        if invalid:
            raise ValueError("Backtest numeric configuration is invalid: " + ", ".join(invalid))

    def _validate_market_data(self, data: pd.DataFrame) -> None:
        if len(data) <= 30:
            raise ValueError("Backtest data requires at least 31 rows for warmup and next-bar execution.")
        columns = ["open", "high", "low", "close"]
        if "volume" in data.columns:
            columns.append("volume")
        numeric = data.loc[:, columns].apply(pd.to_numeric, errors="coerce")
        values = numeric.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Backtest data must contain finite OHLCV values.")
        if (numeric.loc[:, ["open", "high", "low", "close"]] <= 0).any().any():
            raise ValueError("Backtest OHLC prices must be positive.")
        if "volume" in numeric and (numeric["volume"] < 0).any():
            raise ValueError("Backtest volume must be non-negative.")
        if "volume" in numeric:
            with np.errstate(over="ignore", invalid="ignore"):
                dollar_volume = numeric["close"].to_numpy(dtype=float) * numeric["volume"].to_numpy(dtype=float)
            if not np.isfinite(dollar_volume).all():
                raise ValueError("Backtest close-times-volume values must be finite.")
        high_floor = numeric.loc[:, ["open", "low", "close"]].max(axis=1)
        low_ceiling = numeric.loc[:, ["open", "high", "close"]].min(axis=1)
        if (numeric["high"] < high_floor).any() or (numeric["low"] > low_ceiling).any():
            raise ValueError("Backtest OHLC relationships are invalid.")
        if self._is_daily_timeframe():
            sessions = self._session_labels(data.index, require_parseable=True)
            if pd.Index(sessions).has_duplicates:
                raise ValueError("Daily backtest data contains duplicate trading sessions.")

    def _is_daily_timeframe(self) -> bool:
        timeframe = str(self.config.timeframe or "").strip().lower().replace(" ", "")
        return timeframe in {"1d", "1dutc", "d", "day", "daily"}

    def _session_labels(self, index: pd.Index, *, require_parseable: bool = False) -> list[str]:
        if not isinstance(index, pd.DatetimeIndex) and pd.api.types.is_numeric_dtype(index.dtype):
            if require_parseable:
                raise ValueError("Daily backtest data index must contain parseable trading dates.")
            return ["UNSPECIFIED"] * len(index)
        parsed = pd.to_datetime(index, errors="coerce", utc=True)
        if parsed.isna().any():
            if require_parseable:
                raise ValueError("Daily backtest data index must contain parseable trading dates.")
            return ["UNSPECIFIED"] * len(index)
        return [timestamp.date().isoformat() for timestamp in parsed]

    def _reproducibility(self, data: pd.DataFrame) -> dict:
        canonical_rows = [
            [
                str(index),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row.get("volume", 0.0) or 0.0),
            ]
            for index, row in data.iterrows()
        ]
        data_hash = hashlib.sha256(
            json.dumps(canonical_rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        param_payload = json.dumps(self.strategy.params, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
        param_hash = hashlib.sha256(param_payload.encode("utf-8")).hexdigest()
        code_fingerprint = hashlib.sha256(inspect.getsource(type(self.strategy)).encode("utf-8")).hexdigest()
        risk_payload = json.dumps(asdict(self.config.risk), ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
        risk_hash = hashlib.sha256(risk_payload.encode("utf-8")).hexdigest()
        strategy_version = str(getattr(self.strategy, "version", "") or "")
        random_seed = self.experiment_context.get("random_seed", 0)
        if type(random_seed) is not int:
            random_seed = 0
        config_payload = {
            "mode": self.config.mode,
            "market": self.config.market,
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "initial_cash": float(self.config.initial_cash),
            "strategy": {
                "name": self.strategy.name,
                "version": strategy_version,
                "params": self.strategy.params,
            },
            "risk": asdict(self.config.risk),
            "execution": {
                "fee_rate": self.config.execution.fee_rate,
                "slippage_pct": self.config.execution.slippage_pct,
                "execution_model": EXECUTION_MODEL_VERSION,
            },
        }
        config_hash = hashlib.sha256(
            json.dumps(
                config_payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        run_payload = {
            "symbol": self.config.symbol,
            "market": self.config.market,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "strategy_version": strategy_version,
            "data_hash": data_hash,
            "param_hash": param_hash,
            "code_fingerprint": code_fingerprint,
            "initial_cash": float(self.config.initial_cash),
            "risk_hash": risk_hash,
            "config_hash": config_hash,
            "fee_rate": self.config.execution.fee_rate,
            "slippage_pct": self.config.execution.slippage_pct,
            "execution_model": EXECUTION_MODEL_VERSION,
            "random_seed": random_seed,
        }
        run_hash = hashlib.sha256(
            json.dumps(run_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return {
            "hash_scope": "FULL_OHLCV",
            "data_rows": len(canonical_rows),
            "data_hash": data_hash,
            "param_hash": param_hash,
            "risk_hash": risk_hash,
            "config_hash": config_hash,
            "strategy_code_fingerprint": code_fingerprint,
            "run_hash": run_hash,
            "execution_model": EXECUTION_MODEL_VERSION,
            "strategy_version": strategy_version,
            "random_seed": random_seed,
            "data_start": str(data.index[0]),
            "data_end": str(data.index[-1]),
        }

    def _bars_per_year(self) -> int:
        timeframe = self.config.timeframe.strip().lower()
        market_days = 252 if self.config.market.lower() == "stock" else 365
        minutes_per_day = 390 if self.config.market.lower() == "stock" else 24 * 60
        if timeframe.endswith("m"):
            minutes = max(int(timeframe[:-1] or 1), 1)
            return int(market_days * minutes_per_day / minutes)
        if timeframe.endswith("h"):
            hours = max(int(timeframe[:-1] or 1), 1)
            return int(market_days * minutes_per_day / (hours * 60))
        return market_days

    @staticmethod
    def _elapsed_years(index: pd.Index, bars_per_year: int) -> float:
        if len(index) >= 2 and isinstance(index, pd.DatetimeIndex):
            try:
                elapsed_seconds = (pd.Timestamp(index[-1]) - pd.Timestamp(index[0])).total_seconds()
                if elapsed_seconds > 0:
                    return max(elapsed_seconds / (365.2425 * 24 * 60 * 60), 1 / 365.2425)
            except Exception:
                pass
        return max(len(index) / max(bars_per_year, 1), 1 / max(bars_per_year, 1))
