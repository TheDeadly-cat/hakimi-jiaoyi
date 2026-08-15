from __future__ import annotations

import hashlib
import json
from typing import Any

from .backtest_engine import EXECUTION_MODEL_VERSION, prepare_backtest_dataset


def _stable_hash(payload: Any, length: int = 12) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _status_from_score(score: float) -> tuple[str, str]:
    if score >= 72:
        return "PASS", "Pass"
    if score >= 50:
        return "WATCH", "Watch"
    return "BLOCK", "Block"


def _numeric_windows(params: dict[str, Any]) -> list[int]:
    windows: list[int] = []
    for key, value in params.items():
        if not any(token in str(key).lower() for token in ["window", "slow", "fast", "lookback", "period", "entry", "exit"]):
            continue
        try:
            numeric = int(float(value))
        except Exception:
            continue
        if numeric > 0:
            windows.append(numeric)
    return windows


def _safe_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def strategy_lookahead_check(
    strategy: dict[str, Any],
    *,
    candle_count: int,
    startup_candles: int,
    rows: list[dict[str, Any]] | None = None,
    prefix_invariance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = strategy.get("params") or {}
    text = json.dumps({"id": strategy.get("id"), "params": params}, ensure_ascii=True, default=str).lower()
    blocked_tokens = ["future", "lookahead", "lead", "next_candle", "tomorrow", "shift(-", "center=true", "centered"]
    issues: list[str] = []
    score = 92.0

    if any(token in text for token in blocked_tokens):
        issues.append("Parameter names or rules include future-looking tokens.")
        score -= 45

    windows = _numeric_windows(params)
    max_window = max(windows) if windows else 0
    if max_window and startup_candles < max_window + 5:
        issues.append(f"startup_candles={startup_candles} is close to max_window={max_window}.")
        score -= 14

    if candle_count < max(startup_candles * 2, 180):
        issues.append(f"Only {candle_count} candles are available for a {startup_candles}-candle startup.")
        score -= 20
    elif candle_count < max(startup_candles * 4, 360):
        issues.append("Sample is usable but still thin for robust forward validation.")
        score -= 8

    if len(params) >= 8:
        issues.append("Many parameters increase overfit risk before walk-forward testing.")
        score -= 10

    if rows:
        timestamps = [
            ts for ts in (_safe_int(row.get("ts_ms") or row.get("ts") or row.get("time")) for row in rows)
            if ts > 0
        ]
        if len(timestamps) >= 3 and timestamps != sorted(timestamps):
            issues.append("Input candles are not sorted by time.")
            score -= 18

    dynamic = prefix_invariance if isinstance(prefix_invariance, dict) else {}
    dynamic_status = str(dynamic.get("status") or "NOT_RUN").upper()
    if dynamic_status == "BLOCK":
        issues.append("Dynamic prefix-invariance audit failed.")
        score -= 55
    elif dynamic_status != "PASS":
        issues.append("Dynamic prefix-invariance audit was not run.")
        score -= 30

    score = max(0.0, min(100.0, score))
    status, label = _status_from_score(score)
    checks = [
        {"name": "future_token_scan", "status": "PASS" if not any(token in text for token in blocked_tokens) else "BLOCK"},
        {"name": "startup_window", "status": "PASS" if not max_window or startup_candles >= max_window + 5 else "WATCH"},
        {"name": "sample_size", "status": "PASS" if candle_count >= max(startup_candles * 4, 360) else "WATCH" if candle_count >= startup_candles else "BLOCK"},
        {"name": "time_order", "status": "PASS" if not rows or not issues or "Input candles are not sorted by time." not in issues else "BLOCK"},
        {"name": "causal_prefix_invariance", "status": dynamic_status, "detail": dynamic.get("issues") or []},
    ]
    return {
        "name": "Lookahead bias",
        "score": round(score, 1),
        "status": status,
        "label": label,
        "detail": "No direct future-data pattern found." if not issues else " / ".join(issues),
        "issues": issues,
        "checks": checks,
        "sample_size": candle_count,
        "startup_candles": startup_candles,
        "max_window": max_window,
        "prefix_invariance": dynamic,
    }


def market_data_fingerprint(
    rows: list[dict[str, Any]],
    *,
    symbol: str = "",
    source: str = "",
    timeframe: str = "1D",
) -> dict[str, Any]:
    manifest = prepare_backtest_dataset(
        list(rows or []),
        symbol=symbol,
        source=source,
        timeframe=timeframe,
    )["manifest"]
    return {
        "count": manifest["row_count"],
        "first": manifest["first"],
        "last": manifest["last"],
        "hash": manifest["data_hash"],
        "hash_scope": manifest["hash_scope"],
        "status": manifest["status"],
        "blockers": manifest["blockers"],
        "warnings": manifest["warnings"],
        "manifest": manifest,
    }


def backtest_reproducibility(
    *,
    symbol: str,
    strategy_id: str,
    params: dict[str, Any],
    market_payload: dict[str, Any],
    fee_rate: float = 0.0005,
    slippage_bps: float = 0.0,
    seed: int = 0,
    strategy_fingerprint: str = "",
    execution_model: str = EXECUTION_MODEL_VERSION,
) -> dict[str, Any]:
    rows = list(market_payload.get("rows") or [])
    source = str(market_payload.get("source") or "")
    timeframe = str(market_payload.get("bar") or market_payload.get("timeframe") or "1D")
    data = market_data_fingerprint(rows, symbol=symbol, source=source, timeframe=timeframe)
    param_hash = _stable_hash(params)
    run_hash = _stable_hash({
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_fingerprint": strategy_fingerprint,
        "params": params,
        "source": source,
        "timeframe": timeframe,
        "data": data,
        "fee_rate": fee_rate,
        "slippage_bps": slippage_bps,
        "seed": seed,
        "execution_model": execution_model,
    }, length=16)
    return {
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_fingerprint": strategy_fingerprint,
        "params": json.loads(json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)),
        "source": source,
        "timeframe": timeframe,
        "data_points": data["count"],
        "data_first": data["first"],
        "data_last": data["last"],
        "data_hash": data["hash"],
        "hash_scope": data["hash_scope"],
        "dataset_status": data["status"],
        "dataset_blockers": data["blockers"],
        "dataset_warnings": data["warnings"],
        "dataset_manifest": data["manifest"],
        "param_hash": param_hash,
        "run_hash": run_hash,
        "fee_rate": fee_rate,
        "slippage_bps": slippage_bps,
        "seed": seed,
        "execution_model": execution_model,
        "warning": market_payload.get("warning", ""),
    }


def backtest_acceptance_report(
    current: dict[str, Any],
    candidates: list[dict[str, Any]],
    reproducibility: dict[str, Any],
) -> dict[str, Any]:
    checks = []

    def add(name: str, passed: bool, detail: str, watch: bool = False, *, critical: bool = True) -> None:
        checks.append({
            "name": name,
            "status": "PASS" if passed else "WATCH" if watch else "BLOCK",
            "detail": detail,
            "critical": critical,
        })

    add("sample_size", int(reproducibility.get("data_points") or 0) >= 300, f"{reproducibility.get('data_points', 0)} candles", watch=int(reproducibility.get("data_points") or 0) >= 160)
    add("has_trades", int(current.get("trade_count") or 0) > 0, f"{current.get('trade_count', 0)} closed trades")
    add("drawdown", float(current.get("max_drawdown_pct") or 0.0) <= 25, f"max drawdown {current.get('max_drawdown_pct', '--')}%", watch=float(current.get("max_drawdown_pct") or 0.0) <= 35)
    add(
        "dataset_integrity",
        reproducibility.get("dataset_status") == "PASS",
        ", ".join(reproducibility.get("dataset_blockers") or []) or "full dataset validation passed",
    )
    add(
        "reproducible",
        bool(reproducibility.get("run_hash")) and reproducibility.get("hash_scope") == "FULL_OHLCV",
        f"run_hash={reproducibility.get('run_hash', '--')} / {reproducibility.get('hash_scope', '--')}",
    )
    add(
        "causal_execution",
        reproducibility.get("execution_model") == EXECUTION_MODEL_VERSION,
        reproducibility.get("execution_model") or "missing execution model",
    )
    add("optimizer", len(candidates) >= 10, f"{len(candidates)} candidate sets", watch=True, critical=False)
    add("data_warning", not reproducibility.get("warning"), reproducibility.get("warning") or "no warning", watch=True, critical=False)

    score_map = {"PASS": 100, "WATCH": 62, "BLOCK": 20}
    score = round(sum(score_map[row["status"]] for row in checks) / max(len(checks), 1), 1)
    critical_statuses = [row["status"] for row in checks if row["critical"]]
    if "BLOCK" in critical_statuses:
        status, label = "BLOCK", "Block"
    elif "WATCH" in critical_statuses:
        status, label = "WATCH", "Watch"
    else:
        status, label = "PASS", "Pass"
    return {
        "status": status,
        "label": label,
        "score": score,
        "checks": checks,
        "summary": f"Backtest acceptance {status} ({score}/100). Research and paper only.",
    }


def strategy_release_pipeline(
    *,
    doctor_score: float = 0.0,
    lookahead: dict[str, Any] | None = None,
    backtest_acceptance: dict[str, Any] | None = None,
    temporal_validation: dict[str, Any] | None = None,
    selection_evidence: dict[str, Any] | None = None,
    data_admission: dict[str, Any] | None = None,
    live_hard_block: bool = True,
) -> dict[str, Any]:
    lookahead = lookahead or {}
    backtest_acceptance = backtest_acceptance or {}
    temporal_validation = temporal_validation or {}
    selection_evidence = selection_evidence or {}
    data_admission = data_admission or {}
    prefix_invariance = lookahead.get("prefix_invariance") if isinstance(lookahead.get("prefix_invariance"), dict) else {}
    validation_ready = (
        backtest_acceptance.get("status") == "PASS"
        and lookahead.get("status") == "PASS"
        and prefix_invariance.get("status") == "PASS"
        and temporal_validation.get("status") == "PASS"
        and selection_evidence.get("status") == "PASS"
        and data_admission.get("paper_gate_status") == "PASS"
        and doctor_score >= 60
    )
    stages = [
        {"stage": "research", "status": "PASS", "detail": "Research cockpit and evidence chain are available."},
        {"stage": "backtest", "status": backtest_acceptance.get("status", "WAIT"), "detail": backtest_acceptance.get("summary", "Run a reproducible backtest before paper deployment.")},
        {"stage": "temporal_validation", "status": temporal_validation.get("status", "WAIT"), "detail": "Time split, walk-forward and cost stress must all pass."},
        {"stage": "lookahead", "status": lookahead.get("status", "WAIT"), "detail": lookahead.get("detail", "Run lookahead check.")},
        {"stage": "causal_prefix_invariance", "status": prefix_invariance.get("status", "WAIT"), "detail": ", ".join(prefix_invariance.get("issues") or []) or "Historical signals and fills are invariant to future data."},
        {"stage": "independent_matrix", "status": selection_evidence.get("status", "WAIT"), "detail": ", ".join(selection_evidence.get("blockers") or []) or "Independent matrix evidence passed."},
        {"stage": "data_admission", "status": data_admission.get("paper_gate_status", "WAIT"), "detail": ", ".join(data_admission.get("blockers") or []) or "Frozen dataset lineage and source contracts passed."},
        {"stage": "strategy_doctor", "status": "PASS" if doctor_score >= 70 else "WATCH" if doctor_score >= 50 else "BLOCK", "detail": f"doctor_score={doctor_score}"},
        {"stage": "paper_run", "status": "READY" if validation_ready else "WAIT", "detail": "Only paper/simulation can be armed after every mandatory gate passes."},
        {"stage": "audit_report", "status": "WAIT", "detail": "Collect paper order reasons, risk checks, and fills before any release."},
        {"stage": "live_trading", "status": "BLOCKED" if live_hard_block else "LOCKED", "detail": "Live trading hard wall remains enabled."},
    ]
    return {
        "paper_ready": validation_ready,
        "live_ready": False,
        "live_hard_block": live_hard_block,
        "stages": stages,
        "summary": "Research -> backtest -> doctor -> paper -> audit. Live trading stays blocked.",
    }
