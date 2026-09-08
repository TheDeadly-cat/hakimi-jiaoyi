from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any

try:
    from config import OKX_BASE_URL, OKX_TIMEOUT
except ModuleNotFoundError:
    try:
        from ..config import OKX_BASE_URL, OKX_TIMEOUT
    except ImportError:
        from hakimi_research.terminal_config import OKX_BASE_URL, OKX_TIMEOUT

try:
    from market_data.provider_health import (
        ProviderRequestCoordinator,
        provider_call_allowed,
        record_provider_call,
    )
except ModuleNotFoundError:
    from exchange_terminal.market_data.provider_health import (
        ProviderRequestCoordinator,
        provider_call_allowed,
        record_provider_call,
    )


OKX_USER_AGENT = "Python-Quant-Exchange-Terminal/0.1"
OKX_PUBLIC_REQUEST_COORDINATOR = ProviderRequestCoordinator(
    max_requests=20,
    window_ms=2_000,
    failure_threshold=3,
    backoff_base_ms=1_000,
    backoff_cap_ms=30_000,
)


def read_bodyless_okx(path: str, query: dict[str, str]) -> dict[str, Any]:
    health_allowed, health_retry_after_ms = provider_call_allowed("okx", "public", "GLOBAL")
    if not health_allowed:
        raise RuntimeError(f"okx public provider circuit open; retry_after_ms={health_retry_after_ms}")
    allowed, retry_after_ms, reason = OKX_PUBLIC_REQUEST_COORDINATOR.acquire()
    if not allowed:
        raise RuntimeError(f"okx public provider {reason.lower()}; retry_after_ms={retry_after_ms}")
    started = time.perf_counter()
    url = f"{OKX_BASE_URL}{path}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"User-Agent": OKX_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=OKX_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        OKX_PUBLIC_REQUEST_COORDINATOR.complete(success=False)
        record_provider_call(
            "okx",
            "public",
            success=False,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=type(exc).__name__,
            scope="GLOBAL",
        )
        raise
    code = str(payload.get("code", "0")) if isinstance(payload, dict) else ""
    success = code == "0"
    OKX_PUBLIC_REQUEST_COORDINATOR.complete(success=success)
    record_provider_call(
        "okx",
        "public",
        success=success,
        latency_ms=(time.perf_counter() - started) * 1000,
        error="provider_response_error" if not success else "",
        scope="GLOBAL",
    )
    return payload


def okx_rows_with_error(path: str, query: dict[str, str]) -> tuple[list[Any], str]:
    try:
        payload = read_bodyless_okx(path, query)
        return payload.get("data") or [], ""
    except Exception as exc:
        return [], str(exc)


def okx_first(path: str, query: dict[str, str]) -> dict[str, Any]:
    try:
        payload = read_bodyless_okx(path, query)
        return (payload.get("data") or [{}])[0] or {}
    except Exception:
        return {}


def okx_rows(path: str, query: dict[str, str]) -> list[Any]:
    try:
        payload = read_bodyless_okx(path, query)
        return payload.get("data") or []
    except Exception:
        return []
