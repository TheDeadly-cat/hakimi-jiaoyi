from __future__ import annotations

from typing import Any

from .base import ChatProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ChatProvider] = {
            "openai": OpenAIProvider(),
        }

    def get(self, provider_id: str) -> ChatProvider | None:
        return self._providers.get(str(provider_id or "").lower())

    def status(self) -> list[dict[str, Any]]:
        return [provider.status() for provider in self._providers.values()]


PROVIDERS = ProviderRegistry()

