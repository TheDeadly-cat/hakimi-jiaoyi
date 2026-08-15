from __future__ import annotations

from collections import deque
import threading
from typing import Any, Callable


class EventBus:
    def __init__(self, *, now_ms: Callable[[], int], max_events: int = 1000) -> None:
        self.now_ms = now_ms
        self.events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self.subscribers: list[Callable[[dict[str, Any]], None]] = []
        self.sequence = 0
        self._lock = threading.RLock()

    def publish(self, event_type: str, payload: dict[str, Any] | None = None, *, source: str = "server") -> dict[str, Any]:
        with self._lock:
            self.sequence += 1
            event = {
                "seq": self.sequence,
                "time": self.now_ms(),
                "type": event_type,
                "source": source,
                "payload": payload or {},
            }
            self.events.append(event)
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception:
                continue
        return event

    def subscribe(self, handler: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self.subscribers.append(handler)

    def recent(self, limit: int = 120, event_type: str = "") -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 120), 1000))
        with self._lock:
            rows = list(self.events)
        if event_type:
            rows = [event for event in rows if event.get("type") == event_type]
        return rows[-limit:]
