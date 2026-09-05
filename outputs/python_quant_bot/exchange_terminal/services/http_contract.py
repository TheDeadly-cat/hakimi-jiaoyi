from __future__ import annotations

import json
from urllib.parse import urlparse
from typing import Any


LOCAL_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

LOCAL_CLIENT_HOSTS = frozenset({"127.0.0.1", "::1"})

# Outside the research MVP. Retired handlers remain for history, but are not
# registered and the dispatcher rejects them before reading request bodies.
RETIRED_MANAGEMENT_PATHS = frozenset({
    "/api/ai/deepseek/code-worker/run",
    "/api/ai/deepseek/code-worker/archive",
    "/api/ai/deepseek/code-worker/drafts",
    "/api/ai/runtime-keys",
    "/api/ai/runtime-keys/clear",
    "/api/futu/configure",
    "/api/futu/verify-code",
    "/api/futu/enable-telnet",
})

MUTATION_PATHS = frozenset({
    "/api/strategy/backtest",
    "/api/strategy/doctor",
    "/api/strategy/install",
    "/api/strategy/uninstall",
    "/api/strategy/pipeline",
    "/api/bot/assign",
    "/api/bot/release",
    "/api/export/orders",
    "/api/export/ledger",
    "/api/config/full/apply",
    "/api/config/api/save",
    "/api/data/cache/backfill",
    "/api/profile/transfer",
    "/api/profile/notifications/read",
    "/api/profile/guardian",
    "/api/profile/guardian/heartbeat",
    "/api/profile/guardian/emergency-stop",
    "/api/profile/indicators",
    "/api/profile/settings",
    "/api/profile/layout",
    "/api/daemon/prepare",
    "/api/paper/arm",
    "/api/paper/manual-order",
    "/api/paper/stop",
    "/api/paper/reset",
    "/api/paper/condition/add",
    "/api/paper/condition/cancel",
    "/api/paper/evaluate",
})

# The pipeline path exposes a read-only GET snapshot and protected POST actions.
READABLE_MUTATION_PATHS = frozenset({"/api/strategy/pipeline"})

POST_API_PATHS = frozenset({
    "/api/stocks/data-audit",
    "/api/ai/market/dual-analysis",
    "/api/ai/trading-agents/discuss",
    "/api/integration/trading-analysis/research-summaries",
})


def allowed_web_origin(origin: str | None) -> str:
    clean = str(origin or "").strip()
    if not clean:
        return ""
    parsed = urlparse(clean)
    if (
        parsed.scheme != "http"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return ""
    host = (parsed.hostname or "").lower()
    if host not in LOCAL_LOOPBACK_HOSTS:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    if not (1 <= int(port or 0) <= 65535):
        return ""
    return clean


def _query_flag_enabled(query: dict[str, str], key: str) -> bool:
    return str(query.get(key) or "").strip().lower() in {"1", "true", "yes", "on"}


def trusted_refresh_get_allowed(
    path: str,
    query: dict[str, str],
    *,
    client_host: str,
    origin: str | None,
    sec_fetch_site: str | None = None,
) -> bool:
    protected = str(path or "").startswith("/api/") and (
        _query_flag_enabled(query, "force") or _query_flag_enabled(query, "emit")
    )
    if not protected:
        return True
    clean_origin = str(origin or "").strip()
    browser_site = str(sec_fetch_site or "").strip().lower()
    return bool(
        str(client_host or "").strip() in LOCAL_CLIENT_HOSTS
        and (
            allowed_web_origin(clean_origin)
            if clean_origin
            else browser_site != "cross-site"
        )
    )


def read_only_get_mutation_requested(path: str, query: dict[str, str]) -> bool:
    return (
        path == "/api/stocks/history-prewarm"
        and (_query_flag_enabled(query, "start") or _query_flag_enabled(query, "force"))
    ) or (
        path == "/api/market/anomaly-radar"
        and (_query_flag_enabled(query, "notify") or _query_flag_enabled(query, "force"))
    ) or (
        path in {"/api/market/insights", "/api/market/scanner"}
        and _query_flag_enabled(query, "notify")
    )


def payload_to_query(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): (
            "true" if value is True else
            "false" if value is False else
            json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else
            str(value)
        )
        for key, value in payload.items()
        if value is not None
    }
