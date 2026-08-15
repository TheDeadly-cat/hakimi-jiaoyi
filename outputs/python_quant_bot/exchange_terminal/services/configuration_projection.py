from __future__ import annotations

from copy import deepcopy
import math
from typing import Any


CONFIGURATION_RESEARCH_PROJECTION_SCHEMA = "configuration-research-projection-v1"

_AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "automated_paper_order_allowed",
    "binding_authorized",
    "configuration_apply_authorized",
    "execution_allowed",
    "live_order_allowed",
    "live_trading_allowed",
    "live_trading_enabled",
    "order_allowed",
    "parameter_selection_allowed",
    "paper_activation_allowed",
    "paper_armed",
    "paper_authorized",
    "paper_order_allowed",
    "runtime_mutations_allowed",
    "trade_allowed",
    "performance_claim_allowed",
    "profitability_proven",
}

_POSITIVE_STATUSES = {
    "ACTIVE",
    "AUTO",
    "CONFIGURED",
    "CONNECTED",
    "ENABLED",
    "HEALTHY",
    "ONLINE",
    "PASS",
    "PROTECTED",
    "READY",
    "RUNNING",
}
_NEGATIVE_STATUSES = {
    "BLOCK",
    "BLOCKED",
    "ERROR",
    "MISSING",
    "NEEDS_KEY",
    "OFFLINE",
    "UNSAFE",
}
_OPTIONAL_STATUSES = {"OPTIONAL", "NOT_CONFIGURED", "NOT_CONNECTED"}


def _finite_number(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return value


def _status_text(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"LOCKED", "PROTECTED"}:
        return "硬锁保持"
    if raw in _NEGATIVE_STATUSES:
        return "边界待复核"
    if raw in _OPTIONAL_STATUSES:
        return "可选配置缺口"
    if raw in {"STOPPED", "DISABLED"}:
        return "尚未运行"
    if raw in {"WATCH", "STALE", "DEGRADED", "DELAYED"}:
        return "研究观察中"
    if raw in _POSITIVE_STATUSES:
        return "研究配置已核对"
    return "研究观察"


def _root_status(value: Any) -> str:
    raw = str(value or "").strip().upper()
    return "存在边界阻断" if raw in _NEGATIVE_STATUSES or raw == "BLOCKED" else "研究配置观察"


def _safe_detail(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "研究配置状态待补充。"
    lowered = text.lower()
    if any(token in lowered for token in ("runtime", "\\", "/")):
        return "本地配置状态已核对；路径不在研究视图展示。"
    if len(text) > 280:
        return f"{text[:277]}..."
    return text


def _sanitize_authority(value: Any, *, path: str) -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        clean: dict[Any, Any] = {}
        paths: list[str] = []
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key in _AUTHORITY_FIELDS:
                clean[key] = False
                if nested is not False:
                    paths.append(nested_path)
                continue
            projected, nested_paths = _sanitize_authority(nested, path=nested_path)
            clean[key] = projected
            paths.extend(nested_paths)
        return clean, paths
    if isinstance(value, list):
        clean_items: list[Any] = []
        paths: list[str] = []
        for index, nested in enumerate(value):
            projected, nested_paths = _sanitize_authority(
                nested,
                path=f"{path}[{index}]",
            )
            clean_items.append(projected)
            paths.extend(nested_paths)
        return clean_items, paths
    if isinstance(value, tuple):
        clean_items, paths = _sanitize_authority(list(value), path=path)
        return tuple(clean_items), paths
    return deepcopy(value), []


def _project_item(item: Any, *, index: int) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    raw_status = str(source.get("status") or "UNKNOWN").strip().upper()
    return {
        "id": str(source.get("id") or f"config_{index}"),
        "name": str(source.get("name") or source.get("id") or "研究配置项"),
        "priority": str(source.get("priority") or "P1"),
        "status": _status_text(raw_status),
        "raw_status": raw_status,
        "score": _finite_number(source.get("score")),
        "configured": source.get("configured") is True,
        "locked": source.get("locked") is True,
        "detail": _safe_detail(source.get("detail") or source.get("action")),
        "action": "仅研究配置观察；不改变模拟或实盘授权。",
    }


def _project_check(item: Any, *, index: int) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    raw_status = str(source.get("status") or "UNKNOWN").strip().upper()
    return {
        "id": str(source.get("id") or f"check_{index}"),
        "label": str(source.get("label") or "研究检查项"),
        "status": _status_text(raw_status),
        "raw_status": raw_status,
        "detail": _safe_detail(source.get("detail")),
    }


def _project_provider(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    projected: dict[str, Any] = {}
    for key in (
        "provider",
        "configured",
        "model",
        "thinking",
        "role",
        "source",
        "active_env",
        "base_url",
        "opend_online",
        "ok",
    ):
        if key in source:
            projected[key] = deepcopy(source[key])
    if "status" in source:
        raw_status = str(source.get("status") or "UNKNOWN").strip().upper()
        projected["status"] = _status_text(raw_status)
        projected["raw_status"] = raw_status
    if "message" in source:
        projected["message"] = _safe_detail(source.get("message"))
    return projected


def _project_api_provider(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    result = _project_provider(source)
    saved = source.get("saved") if isinstance(source.get("saved"), dict) else {}
    result["saved"] = {
        key: deepcopy(saved[key])
        for key in (
            "exchange",
            "mode",
            "api_key_env",
            "secret_env",
            "password_env",
            "live_trading_enabled",
        )
        if key in saved
    }
    for key in ("env_status", "mapped_env_status"):
        nested = source.get(key)
        if isinstance(nested, dict):
            result[key] = {
                nested_key: (bool(nested_value) if nested_key not in {"api_key_env", "secret_env", "password_env"} else str(nested_value))
                for nested_key, nested_value in nested.items()
                if nested_key in {
                    "api_key",
                    "secret",
                    "password",
                    "OKX_API_KEY",
                    "OKX_SECRET",
                    "OKX_PASSWORD",
                    "api_key_env",
                    "secret_env",
                    "password_env",
                }
            }
    private_read = source.get("private_read")
    if isinstance(private_read, dict):
        result["private_read"] = _project_provider(private_read)
        for key in ("env_status", "env_names"):
            nested = private_read.get(key)
            if isinstance(nested, dict):
                result["private_read"][key] = {
                    nested_key: (bool(nested_value) if key == "env_status" else str(nested_value))
                    for nested_key, nested_value in nested.items()
                    if nested_key in {"api_key", "secret", "password", "api_key_env", "secret_env", "password_env"}
                }
    result["live_enabled"] = False
    result["message"] = "仅展示配置映射与研究状态；不展示密钥，也不开放真实下单。"
    return result


def build_full_configuration_projection(payload: Any) -> dict[str, Any]:
    """Project config-center output as neutral research configuration evidence."""

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "projection_schema_version": CONFIGURATION_RESEARCH_PROJECTION_SCHEMA,
            "status": "配置状态未核验",
            "raw_status": "UNKNOWN",
            "summary": "配置状态未核验；模拟未授权，实盘永久硬锁。",
            "items": [],
            "checklist": [],
            "research_only": True,
            "descriptive_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
            "live_trading_allowed": False,
            "execution_allowed": False,
            "error": "invalid_configuration_payload",
        }

    source, authority_paths = _sanitize_authority(payload, path="snapshot")
    items = [_project_item(item, index=index) for index, item in enumerate(source.get("items") or [])]
    checklist = [_project_check(item, index=index) for index, item in enumerate(source.get("checklist") or [])]
    safe_defaults_source = source.get("safe_defaults") if isinstance(source.get("safe_defaults"), dict) else {}
    providers_source = source.get("providers") if isinstance(source.get("providers"), dict) else {}
    result: dict[str, Any] = {
        "ok": source.get("ok") is not False,
        "projection_schema_version": CONFIGURATION_RESEARCH_PROJECTION_SCHEMA,
        "applied": source.get("applied") is True,
        "status": _root_status(source.get("status")),
        "raw_status": str(source.get("status") or "UNKNOWN").strip().upper(),
        "score": _finite_number(source.get("score")),
        "summary": "全局配置仅作研究配置观察；模拟未授权，实盘永久硬锁。",
        "items": items,
        "checklist": checklist,
        "quick_actions": [
            {"id": "apply_research_preset", "label": "应用研究优先配置"},
            {"id": "open_market_ai", "label": "打开 AI 行情研究"},
            {"id": "open_research", "label": "打开研究档案"},
            {"id": "refresh_data", "label": "刷新数据可靠性"},
        ],
        "safe_defaults": {
            "theme": str(safe_defaults_source.get("theme") or "dark"),
            "density": str(safe_defaults_source.get("density") or "compact"),
            "layout": str(safe_defaults_source.get("layout") or "analysis"),
            "refresh_seconds": _finite_number(safe_defaults_source.get("refresh_seconds")) or 8,
            "start_module": str(safe_defaults_source.get("start_module") or ".research-panel"),
            "live_trading_enabled": False,
            "bot_default_mode": "paper",
        },
        "providers": {
            "deepseek": _project_provider(providers_source.get("deepseek")),
            "gpt": _project_provider(providers_source.get("gpt")),
            "futu": _project_provider(providers_source.get("futu")),
            "api": _project_api_provider(providers_source.get("api")),
        },
        "research_only": True,
        "descriptive_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
        "live_trading_allowed": False,
        "execution_allowed": False,
        "automatic_paper_activation_allowed": False,
        "parameter_selection_allowed": False,
        "profitability_proven": False,
    }
    updated_at = _finite_number(source.get("updated_at"))
    if updated_at is not None:
        result["updated_at"] = updated_at
    if authority_paths:
        result["authority_sanitized_paths"] = list(dict.fromkeys(authority_paths))
    return result

