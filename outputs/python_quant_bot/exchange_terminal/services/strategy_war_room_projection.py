from __future__ import annotations

from copy import deepcopy
from typing import Any

from .execution_authority import authority_violations, sanitize_authority_claims


_VERIFIED_STATUSES = {
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
_ACTIVE_STATUSES = {"RUNNING", "ACTIVE", "IN_PROGRESS"}
_BLOCKED_STATUSES = {"BLOCK", "BLOCKED", "ERROR", "FAILED", "REJECTED", "UNSAFE"}


def _normalise(value: Any, fallback: str = "UNKNOWN") -> str:
    text = str(value or "").strip().upper()
    return text or fallback


def _research_status(value: Any) -> str:
    raw = _normalise(value)
    if raw in _BLOCKED_STATUSES:
        return "RESEARCH_BLOCKED"
    if raw in _ACTIVE_STATUSES:
        return "RESEARCH_REVIEW"
    if raw in _VERIFIED_STATUSES:
        return "RESEARCH_VERIFIED"
    if raw in {"WATCH", "WAIT", "WAITING", "NOT_STARTED", "UNKNOWN", "INFO"}:
        return "RESEARCH_OBSERVE"
    return "RESEARCH_OBSERVE"


def _research_status_label(value: Any) -> str:
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
    )
    for source, replacement in replacements:
        text = text.replace(source, replacement)
    return text


def _project_status_row(row: Any) -> Any:
    if not isinstance(row, dict):
        return deepcopy(row)
    result = deepcopy(row)
    raw_status = _normalise(row.get("status"))
    result["raw_status"] = raw_status
    result["status"] = _research_status(raw_status)
    if "detail" in result:
        result["detail"] = _neutral_text(result.get("detail"))
    if "title" in result:
        result["title"] = _neutral_text(result.get("title"))
    return result


def _project_action_row(row: Any, *, action_key: str = "action") -> Any:
    result = _project_status_row(row)
    if not isinstance(result, dict):
        return result
    raw_action = str(row.get(action_key) or "WAIT").strip().upper()
    result["raw_action"] = raw_action
    result[action_key] = _research_action(raw_action)
    return result


def _project_planning_ladder(rows: Any) -> Any:
    if not isinstance(rows, list):
        return []
    projected: list[Any] = []
    for row in rows:
        if not isinstance(row, dict):
            projected.append(deepcopy(row))
            continue
        item = deepcopy(row)
        item["raw_name"] = str(row.get("name") or "")
        item["raw_rule"] = str(row.get("rule") or "")
        item["name"] = f"观察区间 · {item['raw_name']}" if item["raw_name"] else "观察区间"
        rule = _neutral_text(item["raw_rule"]) or "等待条件核验"
        item["rule"] = f"仅观察 · {rule}"
        item["planning_only"] = True
        item["order_allowed"] = False
        projected.append(item)
    return projected


def _project_card(card: Any) -> Any:
    if not isinstance(card, dict):
        return deepcopy(card)
    result = _project_status_row(card)
    raw_value = str(card.get("value") or "")
    result["raw_value"] = raw_value
    raw_upper = raw_value.strip().upper()
    if raw_upper in {"BUY", "ADD", "LONG", "SELL", "SHORT", "EXIT", "COVER", "HOLD", "WAIT", "WATCH"}:
        result["value"] = _research_action(raw_upper)
    elif raw_value == "可模拟执行":
        result["value"] = "研究条件齐全 · 仍需人工复核"
    elif raw_value == "可开仓":
        result["value"] = "仅规划参数 · 不授权开仓"
    else:
        result["value"] = _neutral_text(raw_value) or "--"
    return result


def _project_rows(value: Any, projector: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [projector(row) for row in value]


def _invalid_projection(error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "mission_status": "RESEARCH_BLOCKED",
        "mission_label": "Research evidence blocked",
        "summary": "War-room research projection failed authority validation.",
        "cards": [],
        "matrix": [],
        "timeline": [],
        "execution_log": [],
        "anchor_plan": [],
        "top_strategies": [],
        "entry_ladder": [],
        "exit_ladder": [],
        "no_trade": ["Authority boundary validation failed"],
        "read_only": True,
        "research_only": True,
        "observation_only": True,
        "simulation_only": True,
        "descriptive_only": True,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "automatic_paper_activation_allowed": False,
        "execution_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_hard_block": True,
        "paper_ready": False,
        "live_ready": False,
        "error": error,
    }


def build_strategy_war_room_projection(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Project the war-room response as descriptive research evidence only."""

    source = report if isinstance(report, dict) else {}
    raw_mission_status = _normalise(source.get("mission_status"))
    raw_mission_label = str(source.get("mission_label") or "")
    projected, sanitized_paths = sanitize_authority_claims(
        source,
        path="war_room",
    )
    payload = dict(projected)

    payload["raw_mission_status"] = raw_mission_status
    payload["raw_mission_label"] = raw_mission_label
    payload["mission_status"] = _research_status(raw_mission_status)
    payload["mission_label"] = (
        "研究条件齐全 · 仍需人工复核"
        if raw_mission_status in _VERIFIED_STATUSES or raw_mission_label == "可模拟执行"
        else "研究证据存在阻断"
        if raw_mission_status in _BLOCKED_STATUSES
        else "研究观察 · 待核验"
    )
    payload["summary"] = _neutral_text(payload.get("summary"))
    payload["read_only"] = True
    payload["research_only"] = True
    payload["observation_only"] = True
    payload["simulation_only"] = True
    payload["descriptive_only"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["automatic_paper_activation_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["live_order_allowed"] = False
    payload["live_trading_hard_block"] = True
    payload["paper_ready"] = False
    payload["live_ready"] = False

    if isinstance(payload.get("bot"), dict):
        bot = dict(payload["bot"])
        bot["raw_role"] = str(bot.get("role") or "")
        bot["raw_active_bot"] = str(bot.get("active_bot") or "")
        bot["role"] = "RESEARCH_ONLY"
        bot["active_bot"] = None
        bot["execution_allowed"] = False
        payload["bot"] = bot

    payload["cards"] = _project_rows(payload.get("cards"), _project_card)
    payload["matrix"] = _project_rows(payload.get("matrix"), _project_status_row)
    payload["timeline"] = _project_rows(payload.get("timeline"), _project_status_row)
    payload["execution_log"] = _project_rows(payload.get("execution_log"), _project_status_row)
    payload["anchor_plan"] = _project_rows(payload.get("anchor_plan"), _project_action_row)
    payload["top_strategies"] = _project_rows(payload.get("top_strategies"), _project_action_row)
    payload["entry_ladder"] = _project_planning_ladder(payload.get("entry_ladder", []))
    payload["exit_ladder"] = _project_planning_ladder(payload.get("exit_ladder", []))
    payload["no_trade"] = [
        _neutral_text(item) for item in payload.get("no_trade", [])
    ] if isinstance(payload.get("no_trade"), list) else payload.get("no_trade")

    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    if authority_violations(payload):
        return _invalid_projection("authority_projection_postcondition_failed")
    return payload


__all__ = ["build_strategy_war_room_projection"]
