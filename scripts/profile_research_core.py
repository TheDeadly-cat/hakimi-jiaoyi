"""Synthetic core profile with ordinary copies/validation; no provider or account I/O.

Run each size in a fresh process. Windows peak working set includes interpreter,
imports, fixture creation, and run; run_wall_seconds measures only engine.run.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import logging
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd

from hakimi_research.backtest import BACKTEST_SCHEMA_VERSION, METRIC_SEMANTICS_VERSION, BacktestEngine
from hakimi_research.config import BotConfig, ExecutionConfig, RiskConfig
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import build_strategy


def peak_working_set() -> int:
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return counters.PeakWorkingSetSize


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, choices=(5000, 20000), required=True)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    steps = np.arange(args.rows, dtype=float)
    close = 100 + 3 * np.sin(steps / 30) + 0.002 * steps
    opening = np.roll(close, 1)
    opening[0] = close[0]
    frame = pd.DataFrame({"open": opening, "high": np.maximum(opening, close) + 0.25,
                          "low": np.minimum(opening, close) - 0.25, "close": close,
                          "volume": np.full(args.rows, 1000.0)},
                         index=pd.date_range("2024-01-01", periods=args.rows, freq="h", tz="UTC"))
    params = {"fast_window": 20, "slow_window": 60, "position_pct": 0.25,
              "stop_loss_pct": 0.03, "take_profit_pct": 0.08}
    config = BotConfig(symbol="SYNTH-PERF", risk=RiskConfig(max_leverage=1.0),
                       execution=ExecutionConfig(fee_rate=0.0008, slippage_pct=0.0005))
    candidate = BacktestEngine(config, build_strategy("dual_ma", params), RiskManager(config.risk))
    memory_before = peak_working_set()
    started = time.perf_counter()
    report = candidate.run(frame, score_start=62).to_dict()
    elapsed = time.perf_counter() - started
    core_root = Path(__file__).resolve().parents[1] / "src" / "hakimi_research"
    source_hashes = {name: hashlib.sha256((core_root / name).read_bytes()).hexdigest()
                     for name in ("backtest.py", "execution.py", "risk.py", "strategies/base.py", "strategies/templates.py")}
    record = {
        "schema_version": "research-synthetic-performance-profile-v1",
        "evidence_kind": "SYNTHETIC_REGRESSION_DIAGNOSTIC", "rows": args.rows,
        "scored_rows": args.rows - 62, "run_wall_seconds": elapsed,
        "peak_process_working_set_bytes": peak_working_set(), "pre_run_peak_working_set_bytes": memory_before,
        "memory_measurement": "WINDOWS_GETPROCESSMEMORYINFO_PEAK_WORKING_SET_FRESH_PROCESS_INCLUDING_IMPORTS",
        "timing_measurement": "ENGINE_RUN_AND_DETACHED_REPORT_EXPORT_EXCLUDES_FIXTURE_AND_IMPORTS",
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "platform": platform.platform(), "backtest_schema": BACKTEST_SCHEMA_VERSION,
        "metric_semantics": METRIC_SEMANTICS_VERSION, "execution_model": report["execution_model"],
        "strategy": "dual_ma", "params": params, "normal_input_and_report_guards": True,
        "normal_strategy_history_copy": True, "optimizations_enabled": False,
        "fill_count": report["fill_count"], "source_sha256": source_hashes,
        "market_effectiveness_assessed": False, "network_calls": 0, "research_only": True,
    }
    print(json.dumps(record, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
