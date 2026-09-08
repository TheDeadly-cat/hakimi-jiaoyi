from __future__ import annotations

from typing import Any, Callable


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _module_by_id(modules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id") or ""): item for item in modules}


def _module_score(module_map: dict[str, dict[str, Any]], module_id: str, default: float = 0.0) -> float:
    return _safe_float(module_map.get(module_id, {}).get("maturity"), default)


def _average(values: list[float]) -> float:
    values = [value for value in values if value > 0]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _status(score: float) -> str:
    if score >= 76:
        return "PASS"
    if score >= 64:
        return "IN_PROGRESS"
    if score >= 50:
        return "WATCH"
    return "BLOCK"


def _lane(
    lane_id: str,
    name: str,
    score: float,
    objective: str,
    landed: list[str],
    next_steps: list[str],
    gaps: list[str] | None = None,
) -> dict[str, Any]:
    score = _clamp_score(score)
    return {
        "id": lane_id,
        "name": name,
        "status": _status(score),
        "score": score,
        "objective": objective,
        "landed": landed,
        "next": next_steps,
        "gaps": gaps or [],
    }


def build_six_lane_roadmap(
    modules: list[dict[str, Any]],
    data_reliability: dict[str, Any],
    adapters: dict[str, Any],
    risk_engine: dict[str, Any],
    *,
    now_ms: Callable[[], int] | None = None,
) -> dict[str, Any]:
    module_map = _module_by_id(modules)
    live_hard_block = bool(risk_engine.get("live_trading_hard_block", True))
    data_score = _safe_float(data_reliability.get("score"), 0.0)
    adapter_score = _safe_float(adapters.get("score"), 0.0)
    adapter_online = int((adapters.get("counts") or {}).get("online") or 0)

    lanes = [
        _lane(
            "tradingview_market_workflow",
            "TradingView market workflow",
            _average([
                _module_score(module_map, "market_radar", 70),
                _module_score(module_map, "market_data", 70),
                74,
            ]),
            "Make chart, radar, evidence, replay and commands the first workflow.",
            [
                "Market radar, trend cockpit and evidence chain are visible in Research.",
                "Chart supports indicators, drawing tools, auto marks and replay mode.",
                "Command palette can jump to modules and execute research actions.",
            ],
            [
                "Add multi-chart synchronization.",
                "Persist chart drawings per symbol.",
                "Turn anomaly rules into user-configurable alerts.",
            ],
            ["Multi-chart sync is still not a first-class screen."],
        ),
        _lane(
            "nautilus_event_core",
            "NautilusTrader service core",
            _average([
                _module_score(module_map, "market_data", 70),
                _module_score(module_map, "risk_center", 70),
                _module_score(module_map, "paper_execution", 60),
                72 if live_hard_block else 35,
            ]),
            "Move toward event-driven data, risk, execution, audit and bus services.",
            [
                "market_data_service, risk_service, research_execution_rehearsal, audit_log and event_bus exist.",
                "Risk checks are kept ahead of paper execution paths.",
                "Live order routing remains hard-blocked.",
            ],
            [
                "Keep archived order lifecycle logic out of server.py; extend only the pure in-memory research rehearsal contract.",
                "Publish more market, risk and strategy events through event_bus.",
                "Promote JSONL audit records into a SQLite audit store.",
            ],
            ["server.py still owns too much orchestration logic."],
        ),
        _lane(
            "freqtrade_dry_run_doctor",
            "Freqtrade dry-run and strategy doctor",
            _average([
                _module_score(module_map, "strategy_lab", 66),
                78,
                90 if live_hard_block else 35,
            ]),
            "Require backtest, lookahead review and paper validation before any release.",
            [
                "Strategy doctor includes lookahead-bias checks.",
                "Backtest output includes acceptance gates and reproducibility hashes.",
                "Fixed-parameter chronological slices are labeled as historical robustness, not walk-forward optimization.",
                "Configured, stress and severe fee/slippage evidence remains descriptive and requires stressed break-even preservation.",
                "Release pipeline explicitly ends at paper/audit, with live blocked.",
            ],
            [
                "Preregister a rolling-refit walk-forward contract before making any WFO claim.",
                "Bind modeled fee/slippage stress to observed venue schedules and liquidity-depth evidence.",
                "Record every paper signal reason into the audit report.",
            ],
            [
                "Current robustness is fixed-parameter historical replay, not rolling-refit WFO; modeled costs do not prove realized execution costs."
            ],
        ),
        _lane(
            "openbb_data_platform",
            "OpenBB unified data layer",
            data_score * 0.62 + adapter_score * 0.38,
            "Fetch once, normalize once, then let chart, AI, radar and backtest share snapshots.",
            [
                "Market snapshots carry source, freshness and adapter information.",
                "Data reliability center reports latency, freshness and fallback reasons.",
                "Local history cache is exposed as a reusable fallback source.",
            ],
            [
                "Attach the same snapshot id to chart, AI prompt and backtest.",
                "Expose stale-cache banners more aggressively in stock views.",
                "Add per-symbol data lineage drilldown.",
            ],
            ["Some stock news/fundamental feeds are still shallow."],
        ),
        _lane(
            "hummingbot_adapters",
            "Hummingbot-style adapters",
            adapter_score + min(adapter_online, 4) * 1.5,
            "Keep OKX, Futu, cache and CSV connectors as adapter-like market data modules.",
            [
                "OKX, Futu, stock cache and CSV/local history adapters are cataloged.",
                "Adapter status is visible in the system panel.",
                "Adapter safety text states data-only mode and live-order hard wall.",
            ],
            [
                "Move adapter fetch implementations behind common interfaces.",
                "Add adapter-level retry, cooldown and telemetry.",
                "Prepare Binance/Yahoo/Stooq as optional read-only adapters.",
            ],
            ["Current adapters are cataloged and routed, but not fully plugin-loaded."],
        ),
        _lane(
            "lean_research_pipeline",
            "QuantConnect LEAN research pipeline",
            _average([
                _module_score(module_map, "strategy_lab", 66),
                _module_score(module_map, "operations", 57),
                74,
            ]),
            "Create a traceable path from research to backtest, doctor, paper run and audit.",
            [
                "Backtest reproducibility reports include data hash, param hash and run hash.",
                "Strategy release pipeline is rendered in Strategy Lab.",
                "System overview links platform maturity, risk and data state.",
            ],
            [
                "Create a dedicated Research Run record.",
                "Tie backtest, paper trades and audit logs to one run id.",
                "Add exportable research-to-paper report.",
            ],
            ["Research runs are not yet persisted as first-class records."],
        ),
    ]

    score = _clamp_score(_average([_safe_float(row.get("score")) for row in lanes]))
    status_counts = {
        "pass": len([row for row in lanes if row.get("status") == "PASS"]),
        "in_progress": len([row for row in lanes if row.get("status") == "IN_PROGRESS"]),
        "watch": len([row for row in lanes if row.get("status") == "WATCH"]),
        "block": len([row for row in lanes if row.get("status") == "BLOCK"]),
    }
    return {
        "ok": True,
        "score": score,
        "status": _status(score),
        "summary": f"Six-lane roadmap {score}/100. PASS {status_counts['pass']} / IN_PROGRESS {status_counts['in_progress']} / WATCH {status_counts['watch']} / BLOCK {status_counts['block']}.",
        "lanes": lanes,
        "counts": status_counts,
        "safety": "Live trading remains hard-blocked; this roadmap is for research, paper validation and audit readiness.",
        "updated_at": now_ms() if now_ms else 0,
    }
