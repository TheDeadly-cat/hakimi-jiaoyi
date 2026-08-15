from __future__ import annotations

from typing import Any, Callable


ADAPTER_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "okx_adapter",
        "name": "OKX public market adapter",
        "asset_types": ["crypto"],
        "sources": ["okx_realtime", "okx_history"],
        "capabilities": ["quote", "candles", "history", "funding", "open_interest"],
        "mode": "public_readonly",
        "safety": "no_private_key_no_live_order",
    },
    {
        "id": "futu_adapter",
        "name": "Futu OpenD stock adapter",
        "asset_types": ["stock"],
        "sources": ["futu_opend", "stock_quotes"],
        "capabilities": ["quote", "candles", "depth", "timeshare"],
        "mode": "local_opend_readonly",
        "safety": "research_only",
    },
    {
        "id": "stock_cache_adapter",
        "name": "Stock cache and fallback adapter",
        "asset_types": ["stock"],
        "sources": ["stock_quotes", "market_history_cache"],
        "capabilities": ["cached_quote", "cached_candles", "fallback"],
        "mode": "local_cache",
        "safety": "stale_data_must_be_labeled",
    },
    {
        "id": "csv_adapter",
        "name": "CSV and local history adapter",
        "asset_types": ["crypto", "stock"],
        "sources": ["btc_local_daily", "market_history_cache"],
        "capabilities": ["history", "backtest_seed", "offline_replay"],
        "mode": "local_file",
        "safety": "not_realtime",
    },
]


def _status_rank(status: str) -> int:
    text = str(status or "").upper()
    if text == "ONLINE":
        return 3
    if text in {"READY", "PASS"}:
        return 2
    if text in {"WATCH", "PARTIAL"}:
        return 1
    return 0


def _adapter_status(source_rows: list[dict[str, Any]], source_ids: list[str]) -> tuple[str, float, list[str]]:
    matched = [row for row in source_rows if str(row.get("id") or "") in source_ids]
    if not matched:
        return "OFFLINE", 0.0, ["No source status was reported."]
    best_rank = max(_status_rank(str(row.get("status") or "")) for row in matched)
    if best_rank >= 3:
        status = "ONLINE"
    elif best_rank >= 1:
        status = "WATCH"
    else:
        status = "OFFLINE"
    score = sum(float(row.get("score") or 0.0) for row in matched) / max(len(matched), 1)
    warnings = [
        str(row.get("warning") or row.get("next") or "")
        for row in matched
        if str(row.get("status") or "").upper() not in {"ONLINE", "READY", "PASS"} and (row.get("warning") or row.get("next"))
    ]
    return status, round(score, 1), list(dict.fromkeys(warnings))


def build_market_adapter_catalog(
    reliability: dict[str, Any],
    *,
    now_ms: Callable[[], int] | None = None,
) -> dict[str, Any]:
    source_rows = list(reliability.get("rows") or [])
    rows: list[dict[str, Any]] = []
    for definition in ADAPTER_DEFINITIONS:
        status, score, warnings = _adapter_status(source_rows, list(definition.get("sources") or []))
        rows.append({
            **definition,
            "status": status,
            "score": score,
            "warnings": warnings[:3],
            "source_status": [
                {
                    "id": row.get("id"),
                    "status": row.get("status"),
                    "score": row.get("score"),
                    "detail": row.get("detail"),
                }
                for row in source_rows
                if str(row.get("id") or "") in definition.get("sources", [])
            ],
        })
    counts = {
        "online": len([row for row in rows if row.get("status") == "ONLINE"]),
        "watch": len([row for row in rows if row.get("status") == "WATCH"]),
        "offline": len([row for row in rows if row.get("status") == "OFFLINE"]),
    }
    score = round(sum(float(row.get("score") or 0.0) for row in rows) / max(len(rows), 1), 1)
    return {
        "ok": True,
        "score": score,
        "status": "ONLINE" if counts["offline"] == 0 and counts["online"] >= 2 else "WATCH" if counts["online"] else "OFFLINE",
        "summary": f"Adapters {counts['online']} online / {counts['watch']} watch / {counts['offline']} offline",
        "rows": rows,
        "counts": counts,
        "safety": "Adapters expose market data only. Live order routing remains hard-blocked.",
        "updated_at": now_ms() if now_ms else 0,
    }
