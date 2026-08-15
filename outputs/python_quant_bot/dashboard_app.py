from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from quant_bot.backtest import BacktestEngine
from quant_bot.config import BotConfig
from quant_bot.data import build_data_provider
from quant_bot.engine import TradingEngine
from quant_bot.execution import build_broker
from quant_bot.logging_setup import setup_logging
from quant_bot.models import Portfolio
from quant_bot.optimizer import ParameterOptimizer
from quant_bot.reporting import save_json_report
from quant_bot.risk import RiskManager
from quant_bot.strategies.templates import STRATEGY_REGISTRY, build_strategy

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - optional UI dependency
    go = None


APP_DIR = Path(__file__).resolve().parent
CONFIG_TEMPLATE_PATH = APP_DIR / "config.example.json"
CONFIG_PATH = APP_DIR / "config.local.json"
RUNTIME_DIR = APP_DIR / "runtime"
REPORT_DIR = RUNTIME_DIR / "reports"
LOG_PATH = RUNTIME_DIR / "logs" / "bot.log"


STRATEGY_DEFAULTS: dict[str, dict[str, Any]] = {
    "dual_ma": {
        "fast_window": 20,
        "slow_window": 60,
        "position_pct": 0.25,
        "take_profit_pct": 0.08,
        "stop_loss_pct": 0.03,
    },
    "grid": {
        "lookback": 80,
        "grids": 8,
        "position_pct": 0.12,
        "stop_loss_pct": 0.05,
    },
    "bollinger": {
        "window": 20,
        "std_mult": 2.0,
        "position_pct": 0.2,
        "stop_loss_pct": 0.04,
    },
    "macd": {
        "fast": 12,
        "slow": 26,
        "signal": 9,
        "position_pct": 0.25,
        "stop_loss_pct": 0.035,
    },
    "rsi": {
        "window": 14,
        "oversold": 30,
        "overbought": 70,
        "position_pct": 0.15,
        "stop_loss_pct": 0.04,
    },
    "momentum": {
        "window": 20,
        "threshold": 0.015,
        "position_pct": 0.22,
        "stop_loss_pct": 0.035,
    },
}


METRIC_LABELS = {
    "total_return": "总收益率",
    "annualized_return": "年化收益",
    "max_drawdown": "最大回撤",
    "win_rate": "胜率",
    "sharpe_ratio": "夏普比率",
    "trades": "交易次数",
    "final_equity": "最终权益",
}


def read_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if CONFIG_TEMPLATE_PATH.exists():
        return json.loads(CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return {
        "name": "okx_auto_quant_bot",
        "mode": "paper",
        "market": "crypto",
        "symbol": "BTC-USDT",
        "timeframe": "1h",
        "initial_cash": 10000,
    }


def write_config(raw: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")


def build_config_from_ui(raw: dict[str, Any]) -> dict[str, Any]:
    st.sidebar.header("运行配置")
    raw["mode"] = "paper"
    st.sidebar.info("运行模式：模拟盘。实盘真实下单永久锁定。")
    raw["market"] = st.sidebar.selectbox("市场", ["crypto", "stock", "futures"], index=["crypto", "stock", "futures"].index(raw.get("market", "crypto")))
    raw["symbol"] = st.sidebar.text_input("交易标的", raw.get("symbol", "BTC-USDT"))
    raw["timeframe"] = st.sidebar.selectbox("周期", ["1m", "5m", "15m", "1h", "4h", "1d"], index=["1m", "5m", "15m", "1h", "4h", "1d"].index(raw.get("timeframe", "1h")))
    raw["initial_cash"] = float(st.sidebar.number_input("初始资金", min_value=100.0, value=float(raw.get("initial_cash", 10000)), step=500.0))

    data = raw.setdefault("data", {})
    data["provider"] = st.sidebar.selectbox("行情源", ["okx", "csv", "synthetic"], index=["okx", "csv", "synthetic"].index(data.get("provider", "okx")))
    data["history_limit"] = int(st.sidebar.slider("历史K线数量", 100, 3000, int(data.get("history_limit", 500)), 100))
    data["csv_path"] = st.sidebar.text_input("CSV路径", data.get("csv_path", ""))
    data["cache_dir"] = st.sidebar.text_input("缓存目录", data.get("cache_dir", "runtime/cache"))
    data["use_cache"] = st.sidebar.toggle("启用行情缓存", value=bool(data.get("use_cache", True)))

    strategy = raw.setdefault("strategy", {})
    current_strategy = strategy.get("name", "dual_ma")
    names = sorted(STRATEGY_REGISTRY)
    strategy["name"] = st.sidebar.selectbox("策略模板", names, index=names.index(current_strategy) if current_strategy in names else 0)
    strategy["params"] = strategy_params_form(strategy["name"], strategy.get("params", {}))

    risk = raw.setdefault("risk", {})
    st.sidebar.header("风控")
    risk["max_position_pct"] = st.sidebar.slider("最大持仓比例", 0.05, 1.0, float(risk.get("max_position_pct", 0.35)), 0.05)
    risk["max_single_loss_pct"] = st.sidebar.slider("单笔最大亏损", 0.005, 0.2, float(risk.get("max_single_loss_pct", 0.03)), 0.005)
    risk["max_daily_loss_pct"] = st.sidebar.slider("单日最大亏损", 0.01, 0.5, float(risk.get("max_daily_loss_pct", 0.05)), 0.01)
    risk["max_leverage"] = st.sidebar.slider("最大杠杆", 1.0, 10.0, float(risk.get("max_leverage", 2.0)), 0.5)
    risk["min_cash_pct"] = st.sidebar.slider("最低现金保留", 0.0, 0.5, float(risk.get("min_cash_pct", 0.05)), 0.01)

    execution = raw.setdefault("execution", {})
    st.sidebar.header("执行")
    execution["broker"] = "paper"
    st.sidebar.caption("执行器：paper（本地模拟）")
    execution["exchange"] = st.sidebar.text_input("交易所", execution.get("exchange", "okx"))
    execution["fee_rate"] = st.sidebar.number_input("手续费率", min_value=0.0, max_value=0.02, value=float(execution.get("fee_rate", 0.0008)), step=0.0001, format="%.4f")
    execution["slippage_pct"] = st.sidebar.number_input("滑点", min_value=0.0, max_value=0.02, value=float(execution.get("slippage_pct", 0.0005)), step=0.0001, format="%.4f")
    execution["poll_seconds"] = int(st.sidebar.number_input("轮询秒数", min_value=1, max_value=3600, value=int(execution.get("poll_seconds", 5))))
    execution["live_trading_enabled"] = False

    logging = raw.setdefault("logging", {})
    logging["level"] = st.sidebar.selectbox("日志等级", ["INFO", "WARNING", "ERROR", "DEBUG"], index=["INFO", "WARNING", "ERROR", "DEBUG"].index(logging.get("level", "INFO")))
    logging["log_dir"] = st.sidebar.text_input("日志目录", logging.get("log_dir", "runtime/logs"))
    return raw


def strategy_params_form(name: str, existing: dict[str, Any]) -> dict[str, Any]:
    st.sidebar.header("策略参数")
    params = dict(STRATEGY_DEFAULTS.get(name, {}))
    params.update(existing or {})

    if name == "dual_ma":
        params["fast_window"] = int(st.sidebar.number_input("快均线", 2, 200, int(params["fast_window"])))
        params["slow_window"] = int(st.sidebar.number_input("慢均线", 3, 400, int(params["slow_window"])))
    elif name == "grid":
        params["lookback"] = int(st.sidebar.number_input("网格观察周期", 20, 1000, int(params["lookback"])))
        params["grids"] = int(st.sidebar.number_input("网格数量", 2, 50, int(params["grids"])))
    elif name == "bollinger":
        params["window"] = int(st.sidebar.number_input("布林周期", 5, 200, int(params["window"])))
        params["std_mult"] = float(st.sidebar.number_input("标准差倍数", 0.5, 5.0, float(params["std_mult"]), 0.1))
    elif name == "macd":
        params["fast"] = int(st.sidebar.number_input("MACD快线", 2, 80, int(params["fast"])))
        params["slow"] = int(st.sidebar.number_input("MACD慢线", 3, 160, int(params["slow"])))
        params["signal"] = int(st.sidebar.number_input("MACD信号线", 2, 80, int(params["signal"])))
    elif name == "rsi":
        params["window"] = int(st.sidebar.number_input("RSI周期", 2, 100, int(params["window"])))
        params["oversold"] = float(st.sidebar.number_input("超卖线", 1.0, 50.0, float(params["oversold"])))
        params["overbought"] = float(st.sidebar.number_input("超买线", 50.0, 99.0, float(params["overbought"])))
    elif name == "momentum":
        params["window"] = int(st.sidebar.number_input("动量周期", 2, 200, int(params["window"])))
        params["threshold"] = float(st.sidebar.number_input("动量阈值", 0.001, 0.2, float(params["threshold"]), 0.001, format="%.3f"))

    params["position_pct"] = st.sidebar.slider("单次开仓比例", 0.01, 1.0, float(params.get("position_pct", 0.2)), 0.01)
    params["stop_loss_pct"] = st.sidebar.slider("策略止损", 0.005, 0.3, float(params.get("stop_loss_pct", 0.03)), 0.005)
    if name in {"dual_ma"}:
        params["take_profit_pct"] = st.sidebar.slider("策略止盈", 0.01, 0.5, float(params.get("take_profit_pct", 0.08)), 0.01)
    return params


def load_stack(config: BotConfig, with_broker: bool = False):
    setup_logging(config.logging.log_dir, config.logging.level)
    provider = build_data_provider(config)
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    risk = RiskManager(config.risk)
    broker = build_broker(config) if with_broker else None
    return provider, strategy, risk, broker


def show_price_chart(data: pd.DataFrame) -> None:
    if data.empty:
        st.warning("暂无行情数据")
        return
    chart_data = data.tail(220).copy()
    if go is None:
        st.line_chart(chart_data["close"])
        return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=chart_data.index,
        open=chart_data["open"],
        high=chart_data["high"],
        low=chart_data["low"],
        close=chart_data["close"],
        name="K线",
    ))
    fig.update_layout(
        height=440,
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)


def run_backtest(config: BotConfig) -> dict[str, Any]:
    provider, strategy, risk, _broker = load_stack(config, with_broker=False)
    data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
    report = BacktestEngine(config=config, strategy=strategy, risk_manager=risk).run(data)
    report_data = report.to_dict()
    output = save_json_report(report_data, str(REPORT_DIR), f"backtest_{config.strategy.name}_{config.symbol}")
    report_data["report_path"] = str(output)
    return report_data


def run_optimizer(config: BotConfig) -> dict[str, Any]:
    provider, _strategy, risk, _broker = load_stack(config, with_broker=False)
    data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
    result = ParameterOptimizer(config=config, risk_manager=risk).run(data)
    output = save_json_report(result, str(REPORT_DIR), f"optimize_{config.strategy.name}_{config.symbol}")
    result["report_path"] = str(output)
    return result


def run_paper_cycles(config: BotConfig, cycles: int) -> dict[str, Any]:
    config.mode = "paper"
    config.execution.broker = "paper"
    config.execution.live_trading_enabled = False
    provider, strategy, risk, broker = load_stack(config, with_broker=True)
    if broker is None:
        raise RuntimeError("broker is required for paper trading")
    engine = TradingEngine(config=config, data_provider=provider, strategy=strategy, risk_manager=risk, broker=broker)
    engine.run(cycles=cycles)
    price = engine.last_price or 0.0
    return {
        "last_price": round(price, 4),
        "cash": round(engine.portfolio.cash, 2),
        "position_qty": round(engine.portfolio.position_qty, 8),
        "equity": round(engine.portfolio.equity(price), 2) if price else round(engine.portfolio.cash, 2),
    }


def metric_row(report: dict[str, Any]) -> None:
    cols = st.columns(7)
    for col, key in zip(cols, METRIC_LABELS):
        value = report.get(key, 0)
        if key in {"total_return", "annualized_return", "max_drawdown", "win_rate"}:
            display = f"{float(value) * 100:.2f}%"
        elif key == "final_equity":
            display = f"{float(value):,.2f}"
        else:
            display = str(value)
        col.metric(METRIC_LABELS[key], display)


def show_report(report: dict[str, Any]) -> None:
    metric_row(report)
    equity_curve = pd.DataFrame(report.get("equity_curve", []))
    if not equity_curve.empty:
        equity_curve["time"] = pd.to_datetime(equity_curve["time"])
        st.line_chart(equity_curve.set_index("time")["equity"])
    fills = pd.DataFrame(report.get("fills", []))
    if not fills.empty:
        st.dataframe(fills.tail(50), use_container_width=True, hide_index=True)


def latest_report_files() -> list[Path]:
    if not REPORT_DIR.exists():
        return []
    return sorted(REPORT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)


def show_logs() -> None:
    if not LOG_PATH.exists():
        st.info("暂无日志")
        return
    lines = LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    st.code("\n".join(lines[-160:]), language="text")


def main() -> None:
    st.set_page_config(page_title="Python Quant Bot", layout="wide")
    st.title("Python Quant Bot")

    raw = build_config_from_ui(read_config())
    if st.sidebar.button("保存配置", use_container_width=True):
        write_config(raw)
        st.sidebar.success("配置已保存")
        st.rerun()

    write_config(raw)
    config = BotConfig.from_file(CONFIG_PATH)

    st.info("当前仅支持回测与模拟盘，实盘下单入口已从配置、界面和执行器三层移除。")

    overview_tab, backtest_tab, optimize_tab, paper_tab, reports_tab, logs_tab = st.tabs([
        "总览",
        "回测",
        "参数寻优",
        "模拟盘",
        "报告",
        "日志",
    ])

    with overview_tab:
        left, right = st.columns([2, 1])
        with left:
            provider = build_data_provider(config)
            try:
                data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
            except Exception as exc:
                st.error(f"行情读取失败：{exc}")
                data = pd.DataFrame()
            show_price_chart(data)
        with right:
            latest_price = float(data["close"].iloc[-1]) if not data.empty else 0.0
            st.metric("最新价格", f"{latest_price:,.4f}")
            st.metric("策略", config.strategy.name)
            st.metric("运行模式", config.mode)
            st.metric("行情源", config.data.provider)
            if not data.empty:
                strategy = build_strategy(config.strategy.name, config.strategy.params)
                signal = strategy.generate_signal(data, portfolio=Portfolio(cash=config.initial_cash))
                st.metric("策略信号", signal.action.value)
                st.caption(signal.reason)

    with backtest_tab:
        if st.button("运行回测", use_container_width=True):
            with st.spinner("回测运行中"):
                try:
                    st.session_state["last_backtest"] = run_backtest(config)
                except Exception as exc:
                    st.error(f"回测失败：{exc}")
        if "last_backtest" in st.session_state:
            show_report(st.session_state["last_backtest"])
            st.caption(st.session_state["last_backtest"].get("report_path", ""))

    with optimize_tab:
        if st.button("运行参数寻优", use_container_width=True):
            with st.spinner("参数寻优运行中"):
                try:
                    st.session_state["last_optimize"] = run_optimizer(config)
                except Exception as exc:
                    st.error(f"参数寻优失败：{exc}")
        if "last_optimize" in st.session_state:
            result = st.session_state["last_optimize"]
            st.json(result.get("best", {}), expanded=True)
            rows = pd.DataFrame(result.get("results", []))
            if not rows.empty:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption(result.get("report_path", ""))

    with paper_tab:
        cycles = st.slider("运行轮数", 1, 50, 5)
        if st.button("启动模拟盘循环", use_container_width=True):
            with st.spinner("模拟盘运行中"):
                try:
                    st.session_state["last_paper"] = run_paper_cycles(config, cycles)
                except Exception as exc:
                    st.error(f"模拟盘运行失败：{exc}")
        if "last_paper" in st.session_state:
            cols = st.columns(4)
            for col, (key, value) in zip(cols, st.session_state["last_paper"].items()):
                col.metric(key, value)

    with reports_tab:
        files = latest_report_files()
        if not files:
            st.info("暂无报告")
        else:
            selected = st.selectbox("报告文件", files, format_func=lambda path: path.name)
            st.json(json.loads(selected.read_text(encoding="utf-8")), expanded=False)

    with logs_tab:
        show_logs()


if __name__ == "__main__":
    main()
