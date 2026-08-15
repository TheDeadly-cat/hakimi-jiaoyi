from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .base import ProviderResponse


def _response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def _http_error_text(raw: str, status_code: int) -> str:
    try:
        payload = json.loads(raw)
        error = payload.get("error") if isinstance(payload, dict) else {}
        code = str((error or {}).get("code") or "")
        message = str((error or {}).get("message") or "")
        if code == "insufficient_quota":
            return "OpenAI 配额不足，请检查该项目的余额或账单设置。"
        if code == "invalid_api_key":
            return "OpenAI 密钥无效或已失效。"
        if code == "rate_limit_exceeded":
            return "OpenAI 请求频率受限，请稍后重试。"
        if message:
            return f"OpenAI 请求失败：{message[:260]}"
    except Exception:
        pass
    return f"OpenAI HTTP {status_code}"


class OpenAIProvider:
    provider_id = "openai"

    def __init__(self, *, api_key: str = OPENAI_API_KEY, base_url: str = OPENAI_BASE_URL, default_model: str = OPENAI_MODEL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model

    def status(self) -> dict[str, Any]:
        return {
            "id": self.provider_id,
            "name": "OpenAI",
            "configured": bool(self._api_key),
            "model": self._default_model,
            "api": "Responses API",
        }

    def generate(self, *, instructions: str, input_text: str, model: str = "") -> ProviderResponse:
        selected_model = model or self._default_model
        if not self._api_key:
            return ProviderResponse(
                ok=False,
                provider=self.provider_id,
                model=selected_model,
                error="OPENAI_API_KEY 未配置",
            )
        body = {
            "model": selected_model,
            "instructions": instructions,
            "input": input_text,
            "max_output_tokens": 900,
            "store": False,
        }
        request = urllib.request.Request(
            f"{self._base_url}/responses",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AICollaborationStudio/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:500]
            return ProviderResponse(
                ok=False,
                provider=self.provider_id,
                model=selected_model,
                error=_http_error_text(detail, exc.code),
            )
        except Exception as exc:
            return ProviderResponse(
                ok=False,
                provider=self.provider_id,
                model=selected_model,
                error=str(exc),
            )
        content = _response_text(payload)
        return ProviderResponse(
            ok=bool(content),
            content=content,
            provider=self.provider_id,
            model=str(payload.get("model") or selected_model),
            error="" if content else "模型没有返回可显示文本",
            usage=payload.get("usage") or {},
        )
