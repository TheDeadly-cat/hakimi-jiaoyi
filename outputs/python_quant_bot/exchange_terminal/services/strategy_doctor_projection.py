from __future__ import annotations

from copy import deepcopy
from typing import Any


_AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_trade",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "live_trading_allowed",
    "live_trading_enabled",
    "order_allowed",
    "paper_activation_allowed",
    "paper_authorized",
    "paper_armed",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "runtime_mutations_allowed",
    "trade_allowed",
}

_VERIFIED = {
    "PASS",
    "READY",
    "DONE",
    "COMPLETE",
    "COMPLETED",
    "SUCCESS",
    "SUCCEEDED",
    "PAPER_READY",
    "PAPER_RUNNING",
    "PAPER_MANUAL_READY",
    "PAPER_STRATEGY_READY",
    "RESTART_READY",
}
_ACTIVE = {"RUNNING", "ACTIVE", "IN_PROGRESS"}
_BLOCKED = {"BLOCK", "BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text or fallback


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in _BLOCKED:
        return "RESEARCH_BLOCKED"
    if raw in _ACTIVE:
        return "RESEARCH_REVIEW"
    if raw in _VERIFIED:
        return "RESEARCH_VERIFIED"
    return "RESEARCH_OBSERVE"


def _research_label(value: Any) -> str:
    status = _research_status(value)
    return {
        "RESEARCH_VERIFIED": "研究证据已核对 · 非授权",
        "RESEARCH_REVIEW": "研究证据待复核 · 非授权",
        "RESEARCH_BLOCKED": "研究证据存在阻断",
        "RESEARCH_OBSERVE": "研究观察 · 待核验",
    }[status]


def _research_action(value: Any) -> str:
    raw = _normalise(value, "WAIT")
    if raw in {"BUY", "ADD", "LONG", "OPEN", "OPEN_SMALL"}:
        return "研究假设：偏多 · 非订单"
    if raw in {"SELL", "SHORT", "EXIT", "COVER"}:
        return "研究假设：偏空 · 非订单"
    if raw in {"HALT", "BLOCK"}:
        return "研究结论：阻断"
    if raw in {"WAIT", "WATCH", "HOLD"}:
        return "研究结论：继续观察"
    return "研究结论：待核验"


def _neutral_text(value: Any) -> str:
    text = str(value or "")
    replacements = (
        ("可模拟执行", "研究条件齐全 · 仍需人工复核"),
        ("模拟执行层", "研究观察层"),
        ("模拟执行", "研究观察"),
        ("执行机器人", "研究角色"),
        ("执行权", "研究角色"),
        ("可开仓", "仅规划参数 · 不授权开仓"),
        ("OWNER", "研究角色"),
        ("上线前", "后续研究阶段"),
    )
    for source, replacement in replacements:
        text = text.replace(source, replacement)
    return text


def _project(value: Any, *, path: str = "doctor") -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        paths: list[str] = []
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS:
                result[key] = False
                if nested is not False:
                    paths.append(nested_path)
                continue
            if key in {"status", "level", "mission_status"}:
                raw_status = _normalise(nested)
                result[f"raw_{key}"] = raw_status
                result[key] = _research_status(raw_status)
                continue
            if key == "action":
                raw_action = _normalise(nested, "WAIT")
                result["raw_action"] = raw_action
                result[key] = _research_action(raw_action)
                continue
            if key == "label":
                raw_status = value.get("status") if isinstance(value, dict) else result.get("raw_status")
                result[key] = (
                    _research_label(raw_status)
                    if raw_status
                    else _neutral_text(nested)
                )
                continue
            projected, projected_paths = _project(nested, path=nested_path)
            if key in {"summary", "detail", "title", "reason", "mapped"} and isinstance(projected, str):
                projected = _neutral_text(projected)
            result[key] = projected
            paths.extend(projected_paths)
        return result, paths
    if isinstance(value, list):
        result: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, projected_paths = _project(nested, path=f"{path}[{index}]")
            result.append(projected)
            paths.extend(projected_paths)
        return result, paths
    if isinstance(value, tuple):
        projected, paths = _project(list(value), path=path)
        return tuple(projected), paths
    return deepcopy(value), []


def build_strategy_doctor_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Keep doctor output descriptive and fail-closed for every consumer."""

    source = report if isinstance(report, dict) else {}
    projected, sanitized_paths = _project(source)
    payload = dict(projected)
    release = payload.get("release_pipeline")
    raw_release_paper_ready = None
    if isinstance(source.get("release_pipeline"), dict):
        raw_release_paper_ready = source["release_pipeline"].get("paper_ready")
    if isinstance(release, dict):
        release["raw_paper_ready"] = raw_release_paper_ready
        release["paper_ready"] = False
        release["live_ready"] = False
        release["live_hard_block"] = True
        release["summary"] = _neutral_text(release.get("summary"))
        stages = release.get("stages")
        if isinstance(stages, list):
            release["stages"] = stages
    payload["raw_paper_ready"] = raw_release_paper_ready
    payload["preview"] = bool(source.get("preview"))
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["automatic_paper_activation_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["live_order_allowed"] = False
    payload["paper_ready"] = False
    payload["live_ready"] = False
    payload["live_trading_hard_block"] = True
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    return payload


__all__ = ["build_strategy_doctor_projection"]
