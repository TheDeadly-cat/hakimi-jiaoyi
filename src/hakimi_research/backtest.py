from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import json
import math

import numpy as np
import pandas as pd

from hakimi_research.config import BotConfig
from hakimi_research.benchmarks import (
    BUY_AND_HOLD_POLICY, STANDARD_RISK_POLICY, BuyAndHoldBenchmarkStrategy,
)
from hakimi_research.experiment_manifest import build_reproducible_experiment_manifest
from hakimi_research.execution import ResearchExecutionSimulator
from hakimi_research.models import Action, Fill, Order, Portfolio, Signal
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.base import StrategyBase


EXECUTION_MODEL_VERSION = "signal-close-next-open-ohlc-v5"
EX_POST_CAPACITY_MODEL_VERSION = "signal-close-next-open-price-ex-post-shared-volume-v5"
METRIC_SEMANTICS_VERSION = "research-accounting-score-start-v2"
MIN_STATISTICAL_RETURN_OBSERVATIONS = 30
RESEARCH_BACKTEST_WARMUP_ROWS = 30


def build_backtest_reproducibility(
    data: pd.DataFrame,
    config: BotConfig,
    strategy: StrategyBase,
    *,
    experiment_context: dict | None = None,
    max_volume_participation_rate: float | None = None,
    score_start: int | None = None,
    score_end: int | None = None,
    benchmark_policy: str = STANDARD_RISK_POLICY,
) -> dict:
    """Build the deterministic run identity without executing a backtest."""

    context = dict(experiment_context) if type(experiment_context) is dict else {}
    execution_model = (
        EX_POST_CAPACITY_MODEL_VERSION
        if max_volume_participation_rate is not None else EXECUTION_MODEL_VERSION
    )
    score_range = {
        "start_inclusive": RESEARCH_BACKTEST_WARMUP_ROWS if score_start is None else score_start,
        "end_exclusive": len(data) if score_end is None else score_end,
        "end_position_policy": "MARK_TO_MARKET_NO_FORCED_LIQUIDATION",
        "metric_semantics_version": METRIC_SEMANTICS_VERSION,
    }
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
    param_payload = json.dumps(
        strategy.params,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    param_hash = hashlib.sha256(param_payload.encode("utf-8")).hexdigest()
    code_fingerprint = hashlib.sha256(
        inspect.getsource(type(strategy)).encode("utf-8")
    ).hexdigest()
    risk_payload = json.dumps(
        asdict(config.risk),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    risk_hash = hashlib.sha256(risk_payload.encode("utf-8")).hexdigest()
    strategy_version = str(getattr(strategy, "version", "") or "")
    random_seed = context.get("random_seed", 0)
    if type(random_seed) is not int:
        random_seed = 0
    config_payload = {
        "mode": config.mode,
        "market": config.market,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "initial_cash": float(config.initial_cash),
        "strategy": {
            "name": strategy.name,
            "version": strategy_version,
            "params": strategy.params,
        },
        "risk": asdict(config.risk),
        "execution": {
            "fee_rate": config.execution.fee_rate,
            "slippage_pct": config.execution.slippage_pct,
            "execution_model": execution_model,
            "max_volume_participation_rate": max_volume_participation_rate,
            "benchmark_policy": benchmark_policy,
        },
        "scoring": score_range,
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
        "symbol": config.symbol,
        "market": config.market,
        "timeframe": config.timeframe,
        "strategy": strategy.name,
        "strategy_version": strategy_version,
        "data_hash": data_hash,
        "param_hash": param_hash,
        "code_fingerprint": code_fingerprint,
        "initial_cash": float(config.initial_cash),
        "risk_hash": risk_hash,
        "config_hash": config_hash,
        "fee_rate": config.execution.fee_rate,
        "slippage_pct": config.execution.slippage_pct,
        "max_volume_participation_rate": max_volume_participation_rate,
        "benchmark_policy": benchmark_policy,
        "execution_model": execution_model,
        "scoring": score_range,
        "random_seed": random_seed,
    }
    run_hash = hashlib.sha256(
        json.dumps(
            run_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
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
        "execution_model": execution_model,
        "scoring": score_range,
        "max_volume_participation_rate": max_volume_participation_rate,
        "benchmark_policy": benchmark_policy,
        "strategy_version": strategy_version,
        "random_seed": random_seed,
        "data_start": str(data.index[0]),
        "data_end": str(data.index[-1]),
    }


@dataclass
class _BacktestReportCore:
    total_return: float
    annualized_return: float | None
    max_drawdown: float
    win_rate: float | None
    sharpe_ratio: float | None
    trades: int
    final_equity: float
    equity_curve: list[dict]
    fills: list[dict]
    total_fees: float
    ambiguous_intrabar_count: int
    execution_model: str
    reproducibility: dict
    experiment_manifest: dict = field(default_factory=dict)
    accounting: dict = field(default_factory=dict)
    orders: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    round_trips: list[dict] = field(default_factory=list)
    return_series: list[dict] = field(default_factory=list)
    statistical_status: dict = field(default_factory=dict)
    risk_semantics: dict = field(default_factory=dict)
    scoring: dict = field(default_factory=dict)

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
            "metric_semantics_version": METRIC_SEMANTICS_VERSION,
            "accounting": self.accounting,
            **{key: value for key, value in self.accounting.items() if key in _ACCOUNTING_FIELDS},
            "orders": self.orders,
            "signals": self.signals,
            "round_trips": self.round_trips,
            "return_series": self.return_series,
            "statistical_status": self.statistical_status,
            "risk_semantics": self.risk_semantics,
            "scoring": self.scoring,
        }


class _BacktestEngineCore:
    def __init__(
        self,
        config: BotConfig,
        strategy: StrategyBase,
        risk_manager: RiskManager,
        experiment_context: dict | None = None,
        max_volume_participation_rate: float | None = None,
        benchmark_policy: str = STANDARD_RISK_POLICY,
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
        self._config = config
        self._strategy = strategy
        self._risk = risk_manager
        self._benchmark_policy = benchmark_policy
        self._experiment_context = (
            dict(experiment_context) if type(experiment_context) is dict else {}
        )
        self._execution_simulator = ResearchExecutionSimulator(
            config.execution.fee_rate,
            config.execution.slippage_pct,
            max_volume_participation_rate,
        )

    def run(
        self, data: pd.DataFrame, *, score_start: int | None = None,
        score_end: int | None = None,
    ) -> BacktestReport:
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Backtest data must be a pandas DataFrame.")
        required = {"open", "high", "low", "close"}
        missing = sorted(required.difference(data.columns))
        if missing:
            raise ValueError(f"Backtest data is missing required OHLC columns: {', '.join(missing)}")
        if not data.index.is_monotonic_increasing or data.index.has_duplicates:
            raise ValueError("Backtest data index must be strictly increasing and unique.")
        start_index = RESEARCH_BACKTEST_WARMUP_ROWS if score_start is None else score_start
        end_index = len(data) if score_end is None else score_end
        if (
            type(start_index) is not int or type(end_index) is not int
            or not 1 <= start_index < end_index <= len(data)
        ):
            raise ValueError("Score range requires 1 <= start_inclusive < end_exclusive <= data rows.")
        self._validate_numeric_configuration()
        self._validate_market_data(data)
        reproducibility = self._reproducibility(data, score_start=start_index, score_end=end_index)
        strategy = _copy.deepcopy(self._strategy)
        portfolio = Portfolio(cash=self._config.initial_cash)
        self._risk.reset_day(self._config.initial_cash)
        # OHLC timestamps denote interval opens. This explicit initial observation
        # precedes any scored fee, fill, or mark and belongs to the score boundary.
        equity_curve = [{
            "time": str(data.index[start_index]), "point": "INITIAL",
            "equity": float(self._config.initial_cash), "cash": float(self._config.initial_cash),
            "position_qty": 0.0, "position_value": 0.0,
        }]
        fills: list[Fill] = []
        fill_records: list[dict] = []
        order_records: list[dict] = []
        signal_records: list[dict] = []
        round_trips: list[dict] = []
        active_round_trip: dict | None = None
        active_stop_loss = None
        active_take_profit = None
        ambiguous_intrabar_count = 0
        active_session = ""
        previous_close_equity = float(self._config.initial_cash)
        session_labels = self._session_labels(data.index)
        participation = self._execution_simulator.max_volume_participation_rate
        remaining_volume: float | None = None
        original_volume: float | None = None

        def execute(order: Order, *, signal_time: str, fill_time: str, basis: str) -> Fill | None:
            nonlocal remaining_volume, active_round_trip
            quantity_before = portfolio.position_qty
            realized_before = portfolio.realized_pnl
            available = remaining_volume
            admission = self._execution_simulator.assess_order(
                order, portfolio, available_volume=available,
            )
            record = {
                "order_id": len(order_records) + 1, "action": order.action.value,
                "signal_time": signal_time, "bar_time": fill_time,
                "requested_quantity": order.quantity, "reference_price": order.price,
                "reason": order.reason, "time_in_force": "ONE_ATTEMPT_CANCEL_REMAINDER",
                "capacity_timing": "EX_POST_FINAL_BAR_VOLUME" if participation is not None else "UNLIMITED_APPROXIMATION",
                "capacity_before_quantity": admission.volume_capacity_quantity,
                "status": admission.status, "admission_reason": admission.reason,
                "filled_quantity": 0.0, "cancelled_quantity": order.quantity,
            }
            order_records.append(record)
            if admission.status == "REJECTED":
                return None
            fill = self._execution_simulator.submit_order(order, portfolio, available_volume=available)
            if participation is not None:
                remaining_volume = max(0.0, available - fill.quantity / participation)
            record.update({
                "filled_quantity": fill.quantity,
                "cancelled_quantity": max(0.0, order.quantity - fill.quantity),
                "status": "PARTIAL_CANCELLED" if fill.quantity < order.quantity else "FILLED",
            })
            fills.append(fill)
            fill_records.append({
                **fill.__dict__, "action": fill.action.value, "order_id": record["order_id"],
                "requested_quantity": order.quantity, "filled_quantity": fill.quantity,
                "fill_ratio": fill.quantity / order.quantity,
                "partial_fill": fill.quantity < order.quantity,
                "available_volume": available, "bar_final_volume": original_volume,
                "max_volume_participation_rate": participation,
                "volume_capacity_quantity": admission.volume_capacity_quantity,
                "capacity_remaining_quantity": remaining_volume * participation if participation is not None else None,
                "signal_time": signal_time, "fill_time": fill_time,
                "fill_basis": basis + "_EX_POST_VOLUME_CAPACITY" if participation is not None else basis,
                "position_before": quantity_before, "position_after": portfolio.position_qty,
                "cash_after": portfolio.cash, "realized_pnl_after": portfolio.realized_pnl,
            })
            if fill.action is Action.BUY and quantity_before == 0:
                active_round_trip = {
                    "round_trip_id": len(round_trips) + 1, "entry_time": fill_time,
                    "exit_time": None, "fill_count": 0, "bought_quantity": 0.0,
                    "sold_quantity": 0.0, "fees": 0.0, "realized_pnl": 0.0,
                }
            if active_round_trip is not None:
                active_round_trip["fill_count"] += 1
                active_round_trip["fees"] += fill.fee
                quantity_key = "bought_quantity" if fill.action is Action.BUY else "sold_quantity"
                active_round_trip[quantity_key] += fill.quantity
                active_round_trip["realized_pnl"] += portfolio.realized_pnl - realized_before
                if portfolio.position_qty == 0:
                    active_round_trip["exit_time"] = fill_time
                    round_trips.append(active_round_trip)
                    active_round_trip = None
            return fill

        def record_signal(signal: Signal, at_time: str, *, seeds_score: bool = False) -> None:
            signal_records.append({
                "time": at_time, "action": signal.action.value, "reason": signal.reason,
                "size_pct": signal.size_pct, "seeds_score": seeds_score,
                "requested_stop_loss_pct": signal.stop_loss_pct,
                "effective_stop_loss_pct": self._risk.effective_stop_loss(signal.stop_loss_pct) if signal.action is Action.BUY and self._benchmark_policy == STANDARD_RISK_POLICY else None,
                "requested_take_profit_pct": signal.take_profit_pct,
            })

        pending_signal = strategy.generate_signal(data.iloc[:start_index], portfolio)
        pending_signal_time = str(data.index[start_index - 1])
        record_signal(pending_signal, pending_signal_time, seeds_score=True)
        for index in range(start_index, end_index):
            window = data.iloc[:index + 1]
            row = window.iloc[-1]
            open_price, high, low, close = (float(row[key]) for key in ("open", "high", "low", "close"))
            fill_time = str(window.index[-1])
            original_volume = float(row["volume"]) if "volume" in row.index else None
            remaining_volume = original_volume
            if participation is not None and original_volume is None:
                raise ValueError("Volume-capacity model requires base-asset volume for every bar.")
            session = session_labels[index]
            if session != active_session:
                self._risk.reset_day(previous_close_equity)
                active_session = session
            order = self._risk.signal_to_order(
                self._config.symbol, pending_signal, portfolio, open_price,
                fee_rate=self._config.execution.fee_rate,
                slippage_pct=self._config.execution.slippage_pct,
            )
            if order is not None:
                fill = execute(order, signal_time=pending_signal_time, fill_time=fill_time, basis="NEXT_BAR_OPEN")
                if fill is not None and order.action is Action.BUY and self._benchmark_policy == STANDARD_RISK_POLICY:
                    active_stop_loss = self._risk.effective_stop_loss(pending_signal.stop_loss_pct)
                    active_take_profit = pending_signal.take_profit_pct
                elif portfolio.position_qty <= 0:
                    active_stop_loss = active_take_profit = None
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
                        raw_exit, reason, basis = target_price, "intrabar take profit", "INTRABAR_TARGET"
                    execute(
                        Order(self._config.symbol, Action.SELL, portfolio.position_qty, raw_exit, reason),
                        signal_time=fill_time, fill_time=fill_time, basis=basis,
                    )
                    if portfolio.position_qty <= 0:
                        active_stop_loss = active_take_profit = None
            previous_close_equity = portfolio.equity(close)
            equity_curve.append({
                "time": self._close_time(data.index[index]), "bar_time": fill_time, "point": "BAR_CLOSE",
                "equity": previous_close_equity, "cash": portfolio.cash,
                "position_qty": portfolio.position_qty, "position_value": portfolio.position_value(close),
            })
            if index + 1 < end_index:
                pending_signal = strategy.generate_signal(window, portfolio)
                pending_signal_time = fill_time
                record_signal(pending_signal, pending_signal_time)
        equity_values = pd.Series([point["equity"] for point in equity_curve], dtype=float)
        # Do not fill the initial undefined return with zero: the n scored bars
        # have exactly n period returns, including the very first loss or fee.
        returns = equity_values.pct_change(fill_method=None).iloc[1:]
        final_equity = float(equity_values.iloc[-1])
        drawdowns = equity_values / equity_values.cummax() - 1
        max_drawdown = float(abs(drawdowns.min()))
        total_return = final_equity / self._config.initial_cash - 1
        bars_per_year = self._bars_per_year()
        elapsed_years = self._elapsed_years(data.index[start_index:end_index], bars_per_year)
        stats = {
            "observation_count": len(returns), "minimum_observations": MIN_STATISTICAL_RETURN_OBSERVATIONS,
            "annualization_basis": "SCORED_INTERVAL_COUNT_OVER_CONFIGURED_PERIODS_PER_YEAR",
            "periods_per_year": bars_per_year, "elapsed_years": elapsed_years,
            "inference_status": "DESCRIPTIVE_ONLY_NO_STRATEGY_VALIDATION",
        }
        annualized_return = sharpe = None
        valid_returns = bool(np.isfinite(returns.to_numpy()).all())
        if not valid_returns:
            stats.update(annualized_return="UNDEFINED_RETURN_AFTER_ZERO_EQUITY", sharpe_ratio="UNDEFINED_RETURN_AFTER_ZERO_EQUITY")
        elif len(returns) < MIN_STATISTICAL_RETURN_OBSERVATIONS:
            stats.update(annualized_return="SHORT_SAMPLE", sharpe_ratio="SHORT_SAMPLE")
        else:
            try:
                candidate = float(math.expm1(math.log1p(total_return) / elapsed_years)) if total_return > -1 else -1.0
            except (OverflowError, ValueError):
                candidate = math.inf
            if math.isfinite(candidate):
                annualized_return = candidate
                stats["annualized_return"] = "DESCRIPTIVE_ESTIMATE"
            else:
                stats["annualized_return"] = "NUMERIC_RANGE_EXCEEDED"
            deviation = float(returns.std(ddof=1))
            if deviation <= 1e-15:
                stats["sharpe_ratio"] = "ZERO_VARIANCE"
            else:
                sharpe = float(np.sqrt(bars_per_year) * returns.mean() / deviation)
                stats["sharpe_ratio"] = "DESCRIPTIVE_ESTIMATE"
        win_rate = sum(trip["realized_pnl"] > 0 for trip in round_trips) / len(round_trips) if round_trips else None
        stats["win_rate"] = "DESCRIPTIVE_COMPLETED_ROUND_TRIPS" if round_trips else "NO_COMPLETED_ROUND_TRIPS"
        stats["status"] = (
            "INSUFFICIENT_EVIDENCE"
            if annualized_return is None or sharpe is None or win_rate is None
            else "DESCRIPTIVE_ONLY"
        )
        total_fees = sum(fill.fee for fill in fills)
        last_close = float(data.iloc[end_index - 1]["close"])
        unrealized = (last_close - portfolio.avg_entry_price) * portfolio.position_qty - portfolio.entry_fees
        exposures = [point["position_value"] / point["equity"] if point["equity"] > 0 else 0.0 for point in equity_curve[1:]]
        accounting = {
            "buy_fees": sum(fill.fee for fill in fills if fill.action is Action.BUY),
            "sell_fees": sum(fill.fee for fill in fills if fill.action is Action.SELL),
            "signal_count": sum(signal["action"] != Action.HOLD.value for signal in signal_records),
            "decision_count": len(signal_records), "order_count": len(order_records),
            "fill_count": len(fills), "round_trip_count": len(round_trips),
            "realized_pnl": portfolio.realized_pnl, "unrealized_pnl": unrealized,
            "open_position_qty": portfolio.position_qty, "unallocated_entry_fees": portfolio.entry_fees,
            "final_cash": portfolio.cash, "end_mark_price": last_close,
            "exposure_ratio": sum(exposures) / len(exposures),
            "exposure_definition": "MEAN_SCORED_CLOSE_POSITION_MARKET_VALUE_OVER_EQUITY",
            "end_position_policy": "MARK_TO_MARKET_NO_FORCED_LIQUIDATION",
            "trades_alias": "DEPRECATED_ALIAS_OF_FILL_COUNT",
            "pnl_reconciliation_error": final_equity - self._config.initial_cash - portfolio.realized_pnl - unrealized,
        }
        scoring = {
            "start_inclusive": start_index, "end_exclusive": end_index,
            "warmup_rows": start_index, "scored_bar_count": end_index - start_index,
            "start_time": str(data.index[start_index]), "end_time": equity_curve[-1]["time"],
            "seed_signal_time": str(data.index[start_index - 1]),
            "warmup_policy": "CONTEXT_ONLY_NO_TRADES_FEES_OR_SCORED_RETURNS",
        }
        report = BacktestReport(
            total_return=total_return, annualized_return=annualized_return, max_drawdown=max_drawdown,
            win_rate=win_rate, sharpe_ratio=sharpe, trades=len(fills), final_equity=final_equity,
            equity_curve=equity_curve, fills=fill_records, total_fees=total_fees,
            ambiguous_intrabar_count=ambiguous_intrabar_count, execution_model=reproducibility["execution_model"],
            reproducibility=reproducibility, accounting=accounting, orders=order_records,
            signals=signal_records, round_trips=round_trips,
            return_series=[{
                "time": equity_curve[position + 1]["time"],
                "return": float(value) if math.isfinite(value) else None,
            } for position, value in enumerate(returns)],
            statistical_status=stats, risk_semantics={
                **self._risk.describe_semantics(),
                "execution_policy": self._benchmark_policy,
                "protective_exits_enabled": self._benchmark_policy == STANDARD_RISK_POLICY,
                "benchmark_policy": "EXPLICIT_NO_STOPS_NO_TARGETS_SINGLE_INITIAL_ATTEMPT" if self._benchmark_policy == BUY_AND_HOLD_POLICY else "NOT_APPLICABLE",
            }, scoring=scoring,
        )
        result_payload = report.to_dict()
        result_payload.pop("experiment_manifest", None)
        report.experiment_manifest = build_reproducible_experiment_manifest(
            result_payload=result_payload, reproducibility=reproducibility,
            strategy_name=self._strategy.name, strategy_version=str(getattr(self._strategy, "version", "") or ""),
            symbol=self._config.symbol, timeframe=self._config.timeframe,
            fee_rate=self._config.execution.fee_rate, slippage_pct=self._config.execution.slippage_pct,
            context=self._experiment_context,
        )
        return report

    def _close_time(self, value: object) -> str:
        if isinstance(value, pd.Timestamp):
            try:
                interval = self._config.timeframe.lower().replace("utc", "")
                if interval.endswith("d"):
                    interval = interval[:-1] + "D"
                duration = pd.Timedelta(interval)
                return str(value + duration)
            except ValueError:
                pass
        return f"{value}:CLOSE"

    def _validate_numeric_configuration(self) -> None:
        risk_contract = asdict(self._config.risk)
        values = {
            "initial_cash": self._config.initial_cash,
            "fee_rate": self._config.execution.fee_rate,
            "slippage_pct": self._config.execution.slippage_pct,
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
        if len(data) < 2:
            raise ValueError("Backtest data requires prior context and at least one scored bar.")
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
        timeframe = str(self._config.timeframe or "").strip().lower().replace(" ", "")
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

    def _reproducibility(
        self, data: pd.DataFrame, *, score_start: int | None = None,
        score_end: int | None = None,
    ) -> dict:
        return build_backtest_reproducibility(
            data,
            self._config,
            self._strategy,
            experiment_context=self._experiment_context,
            max_volume_participation_rate=(
                self._execution_simulator.max_volume_participation_rate
            ),
            score_start=score_start,
            score_end=score_end,
            benchmark_policy=self._benchmark_policy,
        )

    def _bars_per_year(self) -> int:
        timeframe = self._config.timeframe.strip().lower()
        market_days = 252 if self._config.market.lower() == "stock" else 365
        minutes_per_day = 390 if self._config.market.lower() == "stock" else 24 * 60
        if timeframe.endswith("m"):
            minutes = max(int(timeframe[:-1] or 1), 1)
            return int(market_days * minutes_per_day / minutes)
        if timeframe.endswith("h"):
            hours = max(int(timeframe[:-1] or 1), 1)
            return int(market_days * minutes_per_day / (hours * 60))
        return market_days

    @staticmethod
    def _elapsed_years(index: pd.Index, bars_per_year: int) -> float:
        # Input labels are interval opens; n opens represent n full scored
        # intervals. Subtracting last-first would drop the first interval.
        return len(index) / bars_per_year
BACKTEST_SCHEMA_VERSION = "research-backtest-core-v2"

import copy as _copy
from contextvars import ContextVar as _ContextVar
from dataclasses import FrozenInstanceError as _FrozenInstanceError

from hakimi_research.config import validate_research_config as _validate_research_config


_MAX_JSON_DEPTH = 64
_REPORT_CORE_BUILD = _ContextVar("research_backtest_report_core_build", default=False)
_ACCOUNTING_FIELDS = frozenset({
    "buy_fees", "sell_fees",
    "signal_count", "decision_count", "order_count", "fill_count", "round_trip_count",
    "realized_pnl", "unrealized_pnl", "open_position_qty", "unallocated_entry_fees",
    "final_cash", "end_mark_price", "exposure_ratio", "exposure_definition",
    "end_position_policy", "trades_alias", "pnl_reconciliation_error",
})
_REPORT_MUTABLE_FIELDS = frozenset(
    {
        "equity_curve",
        "fills",
        "reproducibility",
        "experiment_manifest",
        "accounting", "orders", "signals", "round_trips", "return_series",
        "statistical_status", "risk_semantics", "scoring",
    }
)
_REPORT_FIELDS = frozenset(
    {
        "total_return",
        "annualized_return",
        "max_drawdown",
        "win_rate",
        "sharpe_ratio",
        "trades",
        "final_equity",
        "equity_curve",
        "fills",
        "total_fees",
        "ambiguous_intrabar_count",
        "execution_model",
        "reproducibility",
        "experiment_manifest",
        "accounting", "orders", "signals", "round_trips", "return_series",
        "statistical_status", "risk_semantics", "scoring",
    }
)
_ENGINE_PROTECTED_FIELDS = frozenset(
    {
        "_benchmark_policy",
        "_config",
        "_strategy",
        "_risk",
        "_experiment_context",
        "_execution_simulator",
    }
)


def _boundary_fail(code: str) -> None:
    raise ValueError(code)


def _native_number(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if type(value) not in (int, float):
        _boundary_fail(f"research_backtest_{label}_exact_native_number_required")
    parsed = float(value)
    if not math.isfinite(parsed):
        _boundary_fail(f"research_backtest_{label}_finite_required")
    if minimum is not None and parsed < minimum:
        _boundary_fail(f"research_backtest_{label}_below_minimum")
    if maximum is not None and parsed > maximum:
        _boundary_fail(f"research_backtest_{label}_above_maximum")
    return parsed


def _native_count(value: object, *, label: str) -> int:
    if type(value) is not int:
        _boundary_fail(f"research_backtest_{label}_exact_int_required")
    if value < 0:
        _boundary_fail(f"research_backtest_{label}_nonnegative_required")
    return value


def _exact_text(value: object, *, label: str, nonempty: bool = False) -> str:
    if type(value) is not str:
        _boundary_fail(f"research_backtest_{label}_exact_str_required")
    if nonempty and not value:
        _boundary_fail(f"research_backtest_{label}_nonempty_required")
    return value


def _clone_json(
    value: object,
    *,
    path: str,
    active_container_ids: set[int] | None = None,
    depth: int = 0,
) -> object:
    if depth > _MAX_JSON_DEPTH:
        _boundary_fail("research_backtest_json_depth_exceeded")
    if active_container_ids is None:
        active_container_ids = set()
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            _boundary_fail(f"research_backtest_{path}_finite_required")
        return value
    if type(value) is list:
        identity = id(value)
        if identity in active_container_ids:
            _boundary_fail("research_backtest_json_cycle_rejected")
        active_container_ids.add(identity)
        try:
            return [
                _clone_json(
                    item,
                    path=f"{path}_{index}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            ]
        finally:
            active_container_ids.remove(identity)
    if type(value) is dict:
        identity = id(value)
        if identity in active_container_ids:
            _boundary_fail("research_backtest_json_cycle_rejected")
        active_container_ids.add(identity)
        try:
            cloned: dict[str, object] = {}
            for key, item in value.items():
                exact_key = _exact_text(key, label=f"{path}_key", nonempty=True)
                cloned[exact_key] = _clone_json(
                    item,
                    path=f"{path}_{exact_key}",
                    active_container_ids=active_container_ids,
                    depth=depth + 1,
                )
            return cloned
        finally:
            active_container_ids.remove(identity)
    _boundary_fail(f"research_backtest_{path}_exact_json_value_required")


def _risk_limits_match(config: BotConfig, manager: RiskManager) -> bool:
    names = (
        "max_position_pct",
        "max_single_loss_pct",
        "max_daily_loss_pct",
        "max_leverage",
        "min_cash_pct",
    )
    return all(
        getattr(config.risk, name) == getattr(manager.config, name)
        for name in names
    )


class BacktestReport(_BacktestReportCore):
    def __init__(
        self,
        total_return: float,
        annualized_return: float | None,
        max_drawdown: float,
        win_rate: float | None,
        sharpe_ratio: float | None,
        trades: int,
        final_equity: float,
        equity_curve: list[dict],
        fills: list[dict],
        total_fees: float,
        ambiguous_intrabar_count: int,
        execution_model: str,
        reproducibility: dict,
        experiment_manifest: dict | None = None,
        accounting: dict | None = None,
        orders: list[dict] | None = None,
        signals: list[dict] | None = None,
        round_trips: list[dict] | None = None,
        return_series: list[dict] | None = None,
        statistical_status: dict | None = None,
        risk_semantics: dict | None = None,
        scoring: dict | None = None,
    ) -> None:
        if type(equity_curve) is not list:
            _boundary_fail("research_backtest_equity_curve_exact_list_required")
        if type(fills) is not list:
            _boundary_fail("research_backtest_fills_exact_list_required")
        if type(reproducibility) is not dict:
            _boundary_fail("research_backtest_reproducibility_exact_dict_required")
        if experiment_manifest is None:
            experiment_manifest = {}
        if type(experiment_manifest) is not dict:
            _boundary_fail("research_backtest_experiment_manifest_exact_dict_required")
        extras = {}
        for name, value, kind in (
            ("accounting", accounting, dict), ("orders", orders, list),
            ("signals", signals, list), ("round_trips", round_trips, list),
            ("return_series", return_series, list), ("statistical_status", statistical_status, dict),
            ("risk_semantics", risk_semantics, dict), ("scoring", scoring, dict),
        ):
            if value is None:
                value = kind()
            if type(value) is not kind:
                _boundary_fail(f"research_backtest_{name}_exact_{kind.__name__}_required")
            extras[name] = _clone_json(value, path=name)
        super().__init__(
            total_return=_native_number(total_return, label="total_return"),
            annualized_return=None if annualized_return is None else _native_number(
                annualized_return,
                label="annualized_return",
            ),
            max_drawdown=_native_number(max_drawdown, label="max_drawdown"),
            win_rate=None if win_rate is None else _native_number(
                win_rate,
                label="win_rate",
                minimum=0.0,
                maximum=1.0,
            ),
            sharpe_ratio=None if sharpe_ratio is None else _native_number(sharpe_ratio, label="sharpe_ratio"),
            trades=_native_count(trades, label="trades"),
            final_equity=_native_number(
                final_equity,
                label="final_equity",
                minimum=0.0,
            ),
            equity_curve=_clone_json(
                equity_curve,
                path="equity_curve",
            ),
            fills=_clone_json(fills, path="fills"),
            total_fees=_native_number(
                total_fees,
                label="total_fees",
                minimum=0.0,
            ),
            ambiguous_intrabar_count=_native_count(
                ambiguous_intrabar_count,
                label="ambiguous_intrabar_count",
            ),
            execution_model=_exact_text(
                execution_model,
                label="execution_model",
                nonempty=True,
            ),
            reproducibility=_clone_json(
                reproducibility,
                path="reproducibility",
            ),
            experiment_manifest=_clone_json(
                experiment_manifest,
                path="experiment_manifest",
            ),
            **extras,
        )
        object.__setattr__(self, "_sealed_report", not _REPORT_CORE_BUILD.get())

    def _seal_after_core(self) -> None:
        for name in _REPORT_MUTABLE_FIELDS:
            raw_value = object.__getattribute__(self, name)
            object.__setattr__(
                self,
                name,
                _clone_json(raw_value, path=f"sealed_{name}"),
            )
        object.__setattr__(self, "_sealed_report", True)

    def __setattr__(self, name: str, value: object) -> None:
        if self.__dict__.get("_sealed_report", False) and name in _REPORT_FIELDS:
            raise _FrozenInstanceError(f"cannot assign to field '{name}'")
        super().__setattr__(name, value)

    def __getattribute__(self, name: str):
        value = super().__getattribute__(name)
        if name in _REPORT_MUTABLE_FIELDS:
            return _copy.deepcopy(value)
        return value

    def to_dict(self) -> dict:
        payload = super().to_dict()
        return _clone_json(payload, path="report_payload")


class BacktestEngine(_BacktestEngineCore):
    def __init__(
        self,
        config: BotConfig,
        strategy: StrategyBase,
        risk_manager: RiskManager,
        experiment_context: dict | None = None,
        *,
        max_volume_participation_rate: float | None = None,
        benchmark_policy: str = STANDARD_RISK_POLICY,
    ) -> None:
        if type(config) is not BotConfig:
            _boundary_fail("research_backtest_exact_canonical_config_required")
        try:
            exact_authority = (
                type(config.mode) is str
                and config.mode == "backtest"
                and type(config.execution.broker) is str
                and config.execution.broker == "research_simulator"
                and type(config.execution.exchange) is str
                and config.execution.exchange == "disabled"
                and type(config.execution.live_trading_enabled) is bool
                and config.execution.live_trading_enabled is False
            )
        except AttributeError:
            exact_authority = False
        if not exact_authority:
            raise ValueError(
                "BacktestEngine requires exact backtest-only execution authority."
            )
        try:
            _validate_research_config(config)
        except ValueError as exc:
            raise ValueError("BacktestEngine numeric configuration is invalid.") from exc
        config_snapshot = _copy.deepcopy(config)
        try:
            _validate_research_config(config_snapshot)
        except ValueError as exc:
            raise ValueError("BacktestEngine numeric configuration is invalid.") from exc

        if not isinstance(strategy, StrategyBase):
            _boundary_fail("research_backtest_strategy_base_instance_required")
        if type(benchmark_policy) is not str or benchmark_policy not in {STANDARD_RISK_POLICY, BUY_AND_HOLD_POLICY}:
            _boundary_fail("research_backtest_execution_policy_invalid")
        is_buy_hold = type(strategy) is BuyAndHoldBenchmarkStrategy
        if (benchmark_policy == BUY_AND_HOLD_POLICY) != is_buy_hold:
            _boundary_fail("research_backtest_buy_hold_requires_exact_strategy_and_explicit_policy")
        if is_buy_hold and (
            config_snapshot.risk.max_position_pct != 1.0
            or config_snapshot.risk.min_cash_pct != 0.0
            or config_snapshot.risk.max_leverage != 1.0
        ):
            _boundary_fail("research_backtest_buy_hold_requires_explicit_full_spot_capacity_risk")
        if type(strategy.name) is not str or not strategy.name:
            _boundary_fail("research_backtest_strategy_name_exact_nonempty_str_required")
        if type(strategy.version) is not str or not strategy.version:
            _boundary_fail("research_backtest_strategy_version_exact_nonempty_str_required")
        if type(strategy.params) is not dict:
            _boundary_fail("research_backtest_strategy_params_exact_dict_required")
        _clone_json(strategy.params, path="strategy_params")
        strategy_snapshot = _copy.deepcopy(strategy)
        if strategy_snapshot is strategy:
            _boundary_fail("research_backtest_strategy_snapshot_alias_rejected")

        if type(risk_manager) is not RiskManager:
            _boundary_fail("research_backtest_exact_canonical_risk_manager_required")
        if not _risk_limits_match(config_snapshot, risk_manager):
            _boundary_fail("research_backtest_risk_limits_must_match_config")

        if experiment_context is None:
            context_snapshot: dict[str, object] = {}
        else:
            if type(experiment_context) is not dict:
                _boundary_fail("research_backtest_experiment_context_exact_dict_required")
            context_snapshot = _clone_json(
                experiment_context,
                path="experiment_context",
            )

        if max_volume_participation_rate is not None:
            if (
                type(max_volume_participation_rate) not in {int, float}
                or type(max_volume_participation_rate) is bool
                or not math.isfinite(float(max_volume_participation_rate))
                or not 0 < float(max_volume_participation_rate) <= 1
            ):
                _boundary_fail(
                    "research_backtest_volume_participation_rate_invalid"
                )
            max_volume_participation_rate = float(
                max_volume_participation_rate
            )

        object.__setattr__(self, "_sealed_engine", False)
        super().__init__(
            config_snapshot,
            strategy_snapshot,
            RiskManager(config_snapshot.risk),
            context_snapshot,
            max_volume_participation_rate,
            benchmark_policy,
        )
        object.__setattr__(self, "_sealed_engine", True)

    def __setattr__(self, name: str, value: object) -> None:
        if (
            self.__dict__.get("_sealed_engine", False)
            and name in _ENGINE_PROTECTED_FIELDS
        ):
            raise AttributeError(f"research_backtest_dependency_is_immutable:{name}")
        super().__setattr__(name, value)

    @property
    def config(self) -> BotConfig:
        return _copy.deepcopy(self._config)

    @property
    def strategy(self) -> StrategyBase:
        return _copy.deepcopy(self._strategy)

    @property
    def risk(self) -> RiskManager:
        return _copy.deepcopy(self._risk)

    @property
    def experiment_context(self) -> dict:
        return _copy.deepcopy(self._experiment_context)

    @property
    def execution_simulator(self) -> ResearchExecutionSimulator:
        return self._execution_simulator

    def run(
        self, data: pd.DataFrame, *, score_start: int | None = None,
        score_end: int | None = None,
    ) -> BacktestReport:
        if type(data) is not pd.DataFrame:
            _boundary_fail("research_backtest_exact_dataframe_required")
        token = _REPORT_CORE_BUILD.set(True)
        try:
            report = super().run(data.copy(deep=True), score_start=score_start, score_end=score_end)
        finally:
            _REPORT_CORE_BUILD.reset(token)
        if type(report) is not BacktestReport:
            _boundary_fail("research_backtest_exact_canonical_report_required")
        report._seal_after_core()
        return report


__all__ = [
    "BACKTEST_SCHEMA_VERSION",
    "METRIC_SEMANTICS_VERSION",
    "EXECUTION_MODEL_VERSION",
    "EX_POST_CAPACITY_MODEL_VERSION",
    "BacktestEngine",
    "BacktestReport",
    "build_backtest_reproducibility",
]
