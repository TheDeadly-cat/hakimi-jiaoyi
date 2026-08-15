from __future__ import annotations

import hashlib
import uuid
from typing import Any, Callable


def build_signal_context(
    context: dict[str, Any] | None,
    *,
    now_ms: Callable[[], int],
    symbol: str,
    side: str,
) -> dict[str, Any]:
    """Attach a stable paper-signal identity before risk and execution."""

    clean = dict(context or {})
    signal_id = str(clean.get("signal_id") or "").strip()
    if not signal_id:
        idempotency_key = str(clean.get("idempotency_key") or "").strip()
        if idempotency_key:
            digest = hashlib.sha256(f"paper-signal:{idempotency_key}".encode("utf-8")).hexdigest()[:24]
            signal_id = f"signal-{digest}"
        else:
            signal_id = f"signal-{now_ms()}-{uuid.uuid4().hex[:10]}"
    source = str(clean.get("source") or "paper_account")
    clean["signal_id"] = signal_id[:160]
    clean.setdefault("signal_created_at", now_ms())
    clean.setdefault("signal_action", str(side or "OBSERVE").upper())
    clean.setdefault("signal_reason", f"{source} submitted a paper execution intent")
    clean.setdefault("signal_symbol", str(symbol or "").upper())
    return clean
