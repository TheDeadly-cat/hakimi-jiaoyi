from __future__ import annotations

from copy import deepcopy
from typing import Any


_AUTHORITY_FIELDS = {
    "armed",
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "can_execute",
    "can_trade",
    "execution_allowed",
    "live_order_allowed",
    "live_ready",
    "live_trading_allowed",
    "live_trading_enabled",
    "mission_authorized",
    "order_allowed",
    "owner",
    "paper_activation_allowed",
    "paper_authorized",
    "paper_armed",
    "paper_order_allowed",
    "paper_ready",
    "parameter_selection_allowed",
    "performance_claim_allowed",
    "profitability_proven",
    "recommended",
    "role_assignment_allowed",
    "runtime_mutations_allowed",
    "selection_allowed",
    "locked",
    "trade_allowed",
}

_STATUS_FIELDS = {"status", "level", "mission_status", "risk_status"}
_VERIFIED_STATUSES = {
    "PASS",
    "READY",
    "DONE",
    "ONLINE",
    "RUNNING",
    "SUCCESS",
    "SUCCEEDED",
}
_BLOCKED_STATUSES = {
    "BLOCK",
    "BLOCKED",
    "ERROR",
    "FAILED",
    "PROTECTED",
    "REJECTED",
    "UNSAFE",
}
_ACTIVE_STATUSES = {"ACTIVE", "IN_PROGRESS", "PARTIAL"}


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
    return "RESEARCH_OBSERVE"


def _research_role(value: Any) -> str:
    raw = _normalise(value, "OBSERVER")
    return "RESEARCH_PRIMARY" if raw in {"OWNER", "PRIMARY"} else "RESEARCH_OBSERVER"


def _research_action(value: Any) -> str:
    raw = _normalise(value, "HOLD")
    if raw in {"BUY", "ADD", "LONG", "OPEN", "OPEN_SMALL"}:
        return "研究假设：偏多 · 非订单"
    if raw in {"SELL", "SHORT", "EXIT", "COVER"}:
        return "研究假设：偏空 · 非订单"
    if raw in {"HALT", "BLOCK"}:
        return "研究结论：阻断"
    if raw in {"WAIT", "WATCH", "HOLD"}:
        return "研究结论：继续观察"
    return "研究结论：待核验"


def _sanitize(value: Any, *, path: str = "bot_research") -> tuple[Any, list[str]]:
    """Copy a response while sealing known authority and execution vocabulary."""

    if isinstance(value, dict):
        clean: dict[Any, Any] = {}
        paths: list[str] = []
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS:
                clean[key] = False
                if nested is not False:
                    clean[f"raw_{key}"] = deepcopy(nested)
                    paths.append(nested_path)
                continue
            if key in _STATUS_FIELDS:
                raw_status = _normalise(nested)
                clean[f"raw_{key}"] = raw_status
                clean[key] = _research_status(raw_status)
                continue
            if key in {"execution_role", "role"}:
                raw_role = _normalise(nested, "OBSERVER")
                clean[f"raw_{key}"] = raw_role
                clean[key] = _research_role(raw_role)
                paths.append(nested_path)
                continue
            projected, projected_paths = _sanitize(nested, path=nested_path)
            clean[key] = projected
            paths.extend(projected_paths)
        return clean, paths
    if isinstance(value, list):
        clean_items: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, projected_paths = _sanitize(
                nested,
                path=f"{path}[{index}]",
            )
            clean_items.append(projected)
            paths.extend(projected_paths)
        return clean_items, paths
    if isinstance(value, tuple):
        projected, paths = _sanitize(list(value), path=path)
        return tuple(projected), paths
    return deepcopy(value), []


def _flags(payload: dict[str, Any], *, schema: str, sanitized_paths: list[str]) -> dict[str, Any]:
    payload["research_schema"] = schema
    payload["read_only"] = True
    payload["research_only"] = True
    payload["descriptive_only"] = True
    payload["observation_only"] = True
    payload["development_heuristic_only"] = True
    payload["profitability_proven"] = False
    payload["performance_claim_allowed"] = False
    payload["parameter_selection_allowed"] = False
    payload["selection_allowed"] = False
    payload["execution_allowed"] = False
    payload["paper_authorized"] = False
    payload["paper_ready"] = False
    payload["live_order_allowed"] = False
    payload["live_ready"] = False
    payload["live_trading_hard_block"] = True
    payload["role_assignment_allowed"] = False
    payload["interpretation"] = (
        "DESCRIPTIVE_BOT_RESEARCH_ONLY; roles, readiness, scores and allocation text "
        "are development evidence, not paper/live authorization or order intent"
    )
    if sanitized_paths:
        payload["authority_sanitized_paths"] = list(dict.fromkeys(sanitized_paths))
    else:
        payload.pop("authority_sanitized_paths", None)
    return payload


def _project_blueprint(row: Any, index: int, projected_row: Any = None) -> Any:
    if not isinstance(row, dict):
        return deepcopy(projected_row if projected_row is not None else row)
    result = deepcopy(projected_row if isinstance(projected_row, dict) else row)
    raw_recommended = bool(row.get("recommended"))
    result["raw_recommended"] = raw_recommended
    result["recommended"] = False
    result["research_priority"] = raw_recommended
    raw_role = _normalise(row.get("execution_role"), "OBSERVER")
    result["raw_execution_role"] = raw_role
    result["execution_role"] = _research_role(raw_role)
    result["research_role"] = result["execution_role"]
    result["readiness_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_AUTHORIZATION"
    result["status_semantics"] = "DESCRIPTIVE_RESEARCH_STATE"
    result["next"] = "研究缺口待补；不构成启停或执行条件"
    result["detail"] = (
        f"研究观察：{row.get('detail') or row.get('next') or '证据待核验'} · 非执行"
    )
    return result


def _project_layer(row: Any) -> Any:
    if not isinstance(row, dict):
        return deepcopy(row)
    result = deepcopy(row)
    result["score_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_AUTHORIZATION"
    result["detail"] = f"研究观察：{row.get('detail') or '证据待核验'} · 非执行"
    return result


def _project_scheduler(source: Any, *, sanitized_paths: list[str] | None = None) -> dict[str, Any]:
    raw = source if isinstance(source, dict) else {}
    projected, paths = _sanitize(raw, path="bot_research.scheduler")
    result = dict(projected) if isinstance(projected, dict) else {}
    active_bot = raw.get("active_bot")
    result["raw_active_bot"] = deepcopy(active_bot)
    result["active_bot"] = None
    result["raw_active_name"] = deepcopy(raw.get("active_name"))
    result["active_name"] = "研究角色未授权"
    raw_mode = _normalise(raw.get("mode"), "UNKNOWN")
    result["raw_mode"] = raw_mode
    result["mode"] = "research_observe"
    result["raw_locked"] = bool(raw.get("locked"))
    result["locked"] = False
    result["summary"] = "研究角色观察台 · 不授予模拟或实盘执行权"
    result["raw_summary"] = deepcopy(raw.get("summary"))
    result["candidates"] = [
        _project_candidate(row, projected_row)
        for row, projected_row in zip(
            raw.get("candidates") or [],
            projected.get("candidates") if isinstance(projected.get("candidates"), list) else [],
        )
    ]
    result["conflicts"] = [
        _project_conflict(row, projected_row)
        for row, projected_row in zip(
            raw.get("conflicts") or [],
            projected.get("conflicts") if isinstance(projected.get("conflicts"), list) else [],
        )
    ]
    result["rules"] = [
        "同一标的的角色切换仅记录研究观察标签，不生成订单。",
        "研究角色可用于比较、解释和缺口登记，不代表 OWNER 或可执行。",
        "任何模拟/实盘授权仍需独立证据合同；当前模拟未授权、实盘永久硬锁。",
    ]
    result["raw_rules"] = deepcopy(raw.get("rules") or [])
    result["role_assignment_allowed"] = False
    result["raw_role_assignment_allowed"] = True
    if sanitized_paths:
        paths.extend(sanitized_paths)
    _flags(result, schema="bot-scheduler-research-projection-v1", sanitized_paths=paths)
    return result


def build_bot_scheduler_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    return _project_scheduler(report)


def _project_candidate(row: Any, projected_row: Any = None) -> Any:
    if not isinstance(row, dict):
        return deepcopy(projected_row if projected_row is not None else row)
    result = deepcopy(projected_row if isinstance(projected_row, dict) else row)
    raw_role = _normalise(row.get("role"), "OBSERVER")
    result["raw_role"] = raw_role
    result["role"] = _research_role(raw_role)
    result["research_role"] = result["role"]
    raw_recommended = bool(row.get("recommended"))
    result["raw_recommended"] = raw_recommended
    result["recommended"] = False
    result["research_priority"] = raw_recommended
    result["raw_can_execute"] = bool(row.get("can_execute"))
    result["can_execute"] = False
    raw_reason = str(row.get("reason") or "").strip()
    result["raw_reason"] = raw_reason
    result["reason"] = f"研究说明：{raw_reason or '证据待核验'} · 非执行"
    result["score_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_SELECTION"
    result["readiness_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_AUTHORIZATION"
    result["selection_allowed"] = False
    return result


def _project_conflict(row: Any, projected_row: Any = None) -> Any:
    if not isinstance(row, dict):
        return deepcopy(projected_row if projected_row is not None else row)
    result = deepcopy(projected_row if isinstance(projected_row, dict) else row)
    result["raw_level"] = _normalise(row.get("level"), "UNKNOWN")
    result["level"] = "RESEARCH_NOTE"
    result["message"] = f"研究冲突待核验：{row.get('message') or '条件未闭合'} · 不触发执行"
    return result


def build_bot_center_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source, path="bot_research.center")
    payload = dict(projected) if isinstance(projected, dict) else {}
    payload["raw_summary"] = deepcopy(source.get("summary"))
    payload["summary"] = (
        f"{source.get('symbol') or '--'} · 研究机器人观察台 · "
        "模拟未授权 · 实盘永久硬锁"
    )
    payload["raw_recommended"] = deepcopy(source.get("recommended") or [])
    payload["recommended"] = []
    payload["research_priority"] = deepcopy(source.get("recommended") or [])
    source_paper = source.get("paper") if isinstance(source.get("paper"), dict) else {}
    projected_paper = payload.get("paper") if isinstance(payload.get("paper"), dict) else {}
    projected_paper["raw_armed"] = bool(source_paper.get("armed"))
    projected_paper["armed"] = False
    projected_paper["simulation_semantics"] = "RESEARCH_OBSERVATION_ONLY"
    projected_paper["risk_status"] = _research_status(source_paper.get("risk_status"))
    payload["paper"] = projected_paper
    projected_blueprints = projected.get("blueprints") if isinstance(projected.get("blueprints"), list) else []
    payload["blueprints"] = [
        _project_blueprint(row, index, projected_blueprints[index] if index < len(projected_blueprints) else None)
        for index, row in enumerate(source.get("blueprints") or [])
    ]
    projected_layers = projected.get("layers") if isinstance(projected.get("layers"), list) else []
    payload["layers"] = [
        _project_layer(projected_layers[index] if index < len(projected_layers) else row)
        for index, row in enumerate(source.get("layers") or [])
    ]
    payload["scheduler"] = _project_scheduler(source.get("scheduler"), sanitized_paths=paths)
    payload["allocations"] = []
    payload["allocation_semantics"] = "DESIGN_ONLY_NOT_ACCOUNT_ALLOCATION"
    payload["raw_allocations"] = deepcopy(source.get("allocations") or [])
    for row in source.get("allocations") or []:
        if not isinstance(row, dict):
            continue
        payload["allocations"].append({
            "bucket": row.get("bucket", "研究桶"),
            "pct": None,
            "raw_pct": row.get("pct"),
            "reason": f"研究草案：{row.get('reason') or '证据待核验'} · 不构成账户配置",
            "allocation_semantics": "DESIGN_ONLY_NOT_ACCOUNT_ALLOCATION",
        })
    payload["gaps"] = []
    projected_gaps = projected.get("gaps") if isinstance(projected.get("gaps"), list) else []
    for index, row in enumerate(source.get("gaps") or []):
        if not isinstance(row, dict):
            continue
        projected_row = projected_gaps[index] if index < len(projected_gaps) and isinstance(projected_gaps[index], dict) else row
        payload["gaps"].append({
            **deepcopy(projected_row),
            "priority": f"研究缺口 {row.get('priority') or '--'}",
            "raw_priority": row.get("priority"),
            "detail": f"研究缺口：{row.get('detail') or '待核验'} · 不构成执行条件",
            "gap_semantics": "DESCRIPTIVE_RESEARCH_GAP",
        })
    payload["raw_rules"] = deepcopy(source.get("rules") or [])
    payload["rules"] = [
        "机器人中枢只展示架构、证据和研究角色，不授予模拟或实盘权限。",
        "同一标的的角色关系仅作观察标签；任何订单路径仍被独立风控合同阻断。",
        "分配比例、成熟度和推荐顺序均为开发期草案，不能当作资金配置或选参结论。",
    ]
    _flags(payload, schema="bot-center-research-projection-v1", sanitized_paths=paths)
    return payload


def build_strategy_robot_profiles_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source, path="bot_research.robot_profiles")
    payload = dict(projected) if isinstance(projected, dict) else {}
    payload["raw_summary"] = deepcopy(source.get("summary"))
    payload["summary"] = (
        f"{source.get('symbol') or '--'} 机器人研究档案 · "
        "开发期观察，不授予模拟或实盘权限"
    )
    rows: list[Any] = []
    projected_rows = projected.get("rows") if isinstance(projected.get("rows"), list) else []
    for index, row in enumerate(source.get("rows") or []):
        if not isinstance(row, dict):
            rows.append(deepcopy(projected_rows[index] if index < len(projected_rows) else row))
            continue
        item = deepcopy(projected_rows[index] if index < len(projected_rows) and isinstance(projected_rows[index], dict) else row)
        raw_owner = bool(row.get("owner"))
        item["raw_owner"] = raw_owner
        item["owner"] = False
        item["research_role"] = "RESEARCH_PRIMARY" if raw_owner else "RESEARCH_OBSERVER"
        raw_action = _normalise(row.get("market_action"), "HOLD")
        item["raw_market_action"] = raw_action
        item["market_action"] = _research_action(raw_action)
        item["status_semantics"] = "DESCRIPTIVE_RESEARCH_STATE"
        item["status_label"] = {
            "PASS": "研究观察条件较完整",
            "WATCH": "研究观察待补证",
            "BLOCK": "研究阻断 / 证据缺口",
        }.get(_normalise(row.get("status")), "研究状态待核验")
        item["readiness_semantics"] = "DEVELOPMENT_HEURISTIC_NOT_AUTHORIZATION"
        item["probability_semantics"] = "UNCALIBRATED_MODEL_ESTIMATE"
        item["raw_start_condition"] = str(row.get("start_condition") or "")
        item["start_condition"] = "仅作研究观察；需冻结证据、成本与自然前向复核"
        item["raw_stop_condition"] = str(row.get("stop_condition") or "")
        item["stop_condition"] = "研究失效条件待核验；不构成启停或交易规则"
        item["next"] = "研究缺口待补；不进入模拟或实盘"
        item["reason"] = f"研究说明：{row.get('reason') or '证据待核验'} · 非订单"
        item["selection_allowed"] = False
        item["order_allowed"] = False
        rows.append(item)
    payload["rows"] = rows
    payload["raw_rules"] = deepcopy(source.get("rules") or [])
    payload["rules"] = [
        "机器人档案只描述开发期证据和缺口，不决定模拟或实盘优先级。",
        "角色字段仅作研究标签；当前模拟未授权，实盘永久硬锁。",
        "状态、评分和概率均未校准，不能单独支持选参或收益结论。",
    ]
    _flags(payload, schema="strategy-robot-profiles-research-projection-v1", sanitized_paths=paths)
    return payload


def build_bot_scheduler_result_projection(report: dict[str, Any] | None) -> dict[str, Any]:
    source = report if isinstance(report, dict) else {}
    projected, paths = _sanitize(source, path="bot_research.scheduler_result")
    payload = dict(projected) if isinstance(projected, dict) else {}
    if isinstance(source.get("scheduler"), dict):
        payload["scheduler"] = _project_scheduler(source["scheduler"], sanitized_paths=paths)
    payload["summary"] = "研究角色变更结果 · 仅记录观察标签，不生成订单"
    payload["raw_summary"] = deepcopy(source.get("summary"))
    payload["planning_only"] = True
    payload["mutation_semantics"] = "RESEARCH_ROLE_LABEL_ONLY"
    _flags(payload, schema="bot-scheduler-result-research-projection-v1", sanitized_paths=paths)
    return payload


__all__ = [
    "build_bot_center_projection",
    "build_bot_scheduler_projection",
    "build_bot_scheduler_result_projection",
    "build_strategy_robot_profiles_projection",
]
