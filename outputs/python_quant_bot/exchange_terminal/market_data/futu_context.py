"""Bounded quote connections; no account, login or trading operations."""
from __future__ import annotations

import math
from typing import Any


FUTU_CONNECT_TIMEOUT_SECONDS = 5.0


def valid_futu_snapshot_row(row: Any, requested_codes: Any) -> bool:
    if not isinstance(row, dict) or not isinstance(row.get("code"), str) or row["code"] not in requested_codes:
        return False
    value = row.get("last_price")
    if isinstance(value, bool):
        return False
    try:
        price = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(price) and price > 0


def open_futu_quote_context(sdk: Any, *, host: str, port: int) -> Any:
    """Avoid the SDK's indefinitely retrying synchronous constructor.

    The installed SDK exposes is_async_connect and set_sync_query_connect_timeout.
    Its separate response timeout remains owned by the SDK. Callers must close
    the returned context in finally; setup failures are closed here.
    """
    context = sdk.OpenQuoteContext(host=host, port=port, is_async_connect=True)
    try:
        context.set_sync_query_connect_timeout(FUTU_CONNECT_TIMEOUT_SECONDS)
    except BaseException:
        try:
            context.close()
        except Exception:
            pass
        raise
    return context


def classify_futu_error(error: Any) -> tuple[str, str]:
    """Expose bounded categories, never provider text containing identities."""
    message = str(error or "").lower()
    if any(part in message for part in ("permission", "entitlement", "no right", "no access", "无权限", "权限不足", "没有权限")):
        return "PERMISSION_DENIED", "当前行情请求没有所需权限；本机连接状态需单独判断。"
    if any(part in message for part in ("not login", "not logged", "login required", "login first", "未登录", "请先登录")):
        return "LOGIN_REQUIRED", "请在本机 OpenD 界面完成登录，再检查行情。"
    if any(part in message for part in ("timeout", "timed out", "超时")):
        return "TIMEOUT", "行情连接或响应超时；尚不能据此判断登录和权限。"
    if any(part in message for part in ("connect", "disconnect", "refused", "reset by peer", "连接")):
        return "CONNECTION_ERROR", "行情协议连接未就绪；请核对 OpenD 状态。"
    if any(part in message for part in ("rsa", "encrypt", "sdk", "加密")):
        return "SDK_ERROR", "行情 SDK 或协议配置未就绪。"
    return "QUOTE_ERROR", "行情请求未返回可用数据；未将其判为 OpenD 离线。"
