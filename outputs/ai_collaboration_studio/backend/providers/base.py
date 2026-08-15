from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class ProviderResponse:
    ok: bool
    content: str = ""
    provider: str = ""
    model: str = ""
    error: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


class ChatProvider(Protocol):
    provider_id: str

    def status(self) -> dict[str, Any]: ...

    def generate(self, *, instructions: str, input_text: str, model: str = "") -> ProviderResponse: ...

