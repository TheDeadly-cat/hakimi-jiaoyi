from __future__ import annotations

import math
from typing import Any


MOTION_META = {
    "BASELINE": {"label": "基线", "tone": "flat", "bonus": 0.0},
    "NEW": {"label": "新异动", "tone": "up", "bonus": 18.0},
    "SURGING": {"label": "快速增强", "tone": "up", "bonus": 24.0},
    "CONFIRMING": {"label": "二次确认", "tone": "up", "bonus": 12.0},
    "PERSISTING": {"label": "持续高位", "tone": "flat", "bonus": 6.0},
    "STEADY": {"label": "变化不大", "tone": "flat", "bonus": 0.0},
    "FADING": {"label": "正在衰减", "tone": "down", "bonus": -8.0},
    "REVIEW": {"label": "数据待核", "tone": "down", "bonus": -20.0},
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def _priority_rank(row: dict[str, Any]) -> int:
    level = str((row.get("watch_priority") or {}).get("level") or "C").upper()
    return {"A": 3, "B": 2, "C": 1}.get(level, 0)


def _severity_rank(row: dict[str, Any]) -> int:
    level = str(row.get("severity") or "LOW").upper()
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "REVIEW": 0}.get(level, 0)


def _requires_review(row: dict[str, Any]) -> bool:
    quality = row.get("data_quality") if isinstance(row.get("data_quality"), dict) else {}
    raw_score = _number(row.get("raw_score", row.get("score", 0.0)))
    return bool(row.get("data_quarantined") or quality.get("quarantined") or (quality.get("fallback") and raw_score >= 68))


def _motion(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    *,
    comparison_available: bool,
) -> dict[str, Any]:
    score = _number(current.get("score"))
    change = _number(current.get("change24h_pct"))
    if _requires_review(current):
        state = "REVIEW"
        score_delta = 0.0
        change_delta = 0.0
        magnitude_delta = 0.0
        new_tags: list[str] = []
    elif not comparison_available:
        state = "BASELINE"
        score_delta = 0.0
        change_delta = 0.0
        magnitude_delta = 0.0
        new_tags = []
    elif previous is None:
        state = "NEW"
        score_delta = score
        change_delta = change
        magnitude_delta = abs(change)
        new_tags = list(current.get("type_tags") or [])[:4]
    else:
        previous_score = _number(previous.get("score"))
        previous_change = _number(previous.get("change24h_pct"))
        score_delta = score - previous_score
        change_delta = change - previous_change
        magnitude_delta = abs(change) - abs(previous_change)
        previous_tags = set(str(item) for item in (previous.get("type_tags") or []))
        new_tags = [str(item) for item in (current.get("type_tags") or []) if str(item) not in previous_tags][:4]
        priority_delta = _priority_rank(current) - _priority_rank(previous)
        severity_delta = _severity_rank(current) - _severity_rank(previous)
        if priority_delta > 0 or severity_delta > 0 or score_delta >= 8 or magnitude_delta >= 1.2:
            state = "SURGING"
        elif score_delta <= -6 or magnitude_delta <= -1.0:
            state = "FADING"
        elif score_delta >= 3 or magnitude_delta >= 0.5 or new_tags:
            state = "CONFIRMING"
        elif _priority_rank(current) >= 2 and score >= 68:
            state = "PERSISTING"
        else:
            state = "STEADY"

    meta = MOTION_META[state]
    priority_bonus = _priority_rank(current) * 8.0
    attention_score = score + priority_bonus + float(meta["bonus"])
    return {
        "state": state,
        "label": meta["label"],
        "tone": meta["tone"],
        "comparison_available": comparison_available,
        "score_delta": round(score_delta, 1),
        "change_delta_pct": round(change_delta, 2),
        "magnitude_delta_pct": round(magnitude_delta, 2),
        "new_tags": new_tags,
        "attention_score": round(attention_score, 1),
    }


def annotate_anomaly_progression(
    rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    comparison_available = bool(previous_rows)
    previous_by_symbol = {
        str(row.get("symbol") or "").upper(): row
        for row in (previous_rows or [])
        if isinstance(row, dict) and row.get("symbol")
    }
    annotated: list[dict[str, Any]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        motion = _motion(row, previous_by_symbol.get(symbol), comparison_available=comparison_available)
        annotated.append({**row, "motion": motion})
    if comparison_available:
        annotated.sort(key=lambda row: (_number((row.get("motion") or {}).get("attention_score")), _number(row.get("score"))), reverse=True)
    return annotated


def anomaly_progression_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    states = [str((row.get("motion") or {}).get("state") or "BASELINE") for row in rows]
    comparison_available = any(bool((row.get("motion") or {}).get("comparison_available")) for row in rows)
    new_count = states.count("NEW")
    surging_count = states.count("SURGING")
    confirming_count = states.count("CONFIRMING")
    fading_count = states.count("FADING")
    persisting_count = states.count("PERSISTING")
    review_count = states.count("REVIEW")
    if comparison_available:
        summary = f"本轮新异动 {new_count}，增强 {surging_count + confirming_count}，持续 {persisting_count}，衰减 {fading_count}"
    else:
        summary = "已建立本轮雷达基线；下一轮开始显示新增、增强和衰减"
    return {
        "comparison_available": comparison_available,
        "new": new_count,
        "surging": surging_count,
        "confirming": confirming_count,
        "strengthening": surging_count + confirming_count,
        "persisting": persisting_count,
        "fading": fading_count,
        "review": review_count,
        "summary": summary,
    }
