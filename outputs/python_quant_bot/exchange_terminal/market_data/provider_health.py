from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Callable


class ProviderRequestCoordinator:
    """Bounded in-memory admission for public provider requests.

    This is deliberately a non-blocking gate: callers either start one request
    or receive a retry hint.  Per-symbol services remain responsible for
    singleflight and last-good cache semantics; this coordinator only prevents
    several different public endpoints from stampeding the same provider.
    """

    def __init__(
        self,
        *,
        now_ms: Callable[[], int] | None = None,
        max_requests: int = 20,
        window_ms: int = 2_000,
        failure_threshold: int = 3,
        backoff_base_ms: int = 1_000,
        backoff_cap_ms: int = 30_000,
    ) -> None:
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.max_requests = max(int(max_requests), 1)
        self.window_ms = max(int(window_ms), 1)
        self.failure_threshold = max(int(failure_threshold), 1)
        self.backoff_base_ms = max(int(backoff_base_ms), 1)
        self.backoff_cap_ms = max(int(backoff_cap_ms), self.backoff_base_ms)
        self._lock = threading.RLock()
        self._request_stamps: deque[int] = deque()
        self._consecutive_failures = 0
        self._backoff_until_ms = 0

    def _prune(self, stamp: int) -> None:
        cutoff = stamp - self.window_ms
        while self._request_stamps and self._request_stamps[0] <= cutoff:
            self._request_stamps.popleft()

    def acquire(self) -> tuple[bool, int, str]:
        """Reserve one request, or return (False, retry_after_ms, reason)."""
        stamp = max(int(self.now_ms()), 0)
        with self._lock:
            self._prune(stamp)
            backoff_retry = max(self._backoff_until_ms - stamp, 0)
            if backoff_retry:
                return False, backoff_retry, "BACKOFF"
            if len(self._request_stamps) >= self.max_requests:
                oldest = self._request_stamps[0]
                retry_after = max(self.window_ms - (stamp - oldest), 1)
                return False, retry_after, "RATE_LIMIT"
            self._request_stamps.append(stamp)
            return True, 0, "ACQUIRED"

    def complete(self, *, success: bool) -> None:
        """Close one reservation and apply bounded exponential failure backoff."""
        stamp = max(int(self.now_ms()), 0)
        with self._lock:
            if success:
                self._consecutive_failures = 0
                self._backoff_until_ms = 0
                return
            self._consecutive_failures += 1
            if self._consecutive_failures < self.failure_threshold:
                return
            exponent = self._consecutive_failures - self.failure_threshold
            delay = min(self.backoff_cap_ms, self.backoff_base_ms * (2 ** min(exponent, 10)))
            self._backoff_until_ms = stamp + delay

    def snapshot(self) -> dict[str, Any]:
        stamp = max(int(self.now_ms()), 0)
        with self._lock:
            self._prune(stamp)
            return {
                "in_window": len(self._request_stamps),
                "max_requests": self.max_requests,
                "window_ms": self.window_ms,
                "retry_after_ms": max(self._backoff_until_ms - stamp, 0),
                "consecutive_failures": self._consecutive_failures,
                "backoff_active": self._backoff_until_ms > stamp,
            }

    def reset(self) -> None:
        with self._lock:
            self._request_stamps.clear()
            self._consecutive_failures = 0
            self._backoff_until_ms = 0


class ProviderHealthRegistry:
    def __init__(
        self,
        *,
        now_ms: Callable[[], int] | None = None,
        failure_threshold: int = 2,
        cooldown_ms: int = 30_000,
        max_records: int = 600,
    ) -> None:
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_ms = max(1_000, int(cooldown_ms))
        self.max_records = max(50, int(max_records))
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _key(provider: str, operation: str, scope: str) -> str:
        return "|".join((
            str(provider or "unknown").strip().lower(),
            str(operation or "unknown").strip().lower(),
            str(scope or "global").strip().upper(),
        ))

    def allowed(self, provider: str, operation: str, scope: str = "global") -> tuple[bool, int]:
        key = self._key(provider, operation, scope)
        stamp = self.now_ms()
        with self._lock:
            record = self._records.get(key) or {}
            retry_after_ms = max(int(record.get("circuit_until_ms") or 0) - stamp, 0)
            return retry_after_ms <= 0, retry_after_ms

    def record(
        self,
        provider: str,
        operation: str,
        *,
        success: bool,
        latency_ms: float,
        error: str = "",
        scope: str = "global",
        cooldown_ms: int | None = None,
    ) -> dict[str, Any]:
        key = self._key(provider, operation, scope)
        stamp = self.now_ms()
        latency = max(float(latency_ms or 0), 0.0)
        with self._lock:
            previous = self._records.get(key) or {}
            calls = int(previous.get("calls") or 0) + 1
            success_count = int(previous.get("success_count") or 0) + (1 if success else 0)
            failure_count = int(previous.get("failure_count") or 0) + (0 if success else 1)
            total_latency_ms = float(previous.get("total_latency_ms") or 0.0) + latency
            consecutive_failures = 0 if success else int(previous.get("consecutive_failures") or 0) + 1
            circuit_until_ms = 0
            if not success and consecutive_failures >= self.failure_threshold:
                circuit_until_ms = stamp + max(1_000, int(cooldown_ms or self.cooldown_ms))
            record = {
                "provider": str(provider or "unknown").strip().lower(),
                "operation": str(operation or "unknown").strip().lower(),
                "scope": str(scope or "global").strip().upper(),
                "calls": calls,
                "success_count": success_count,
                "failure_count": failure_count,
                "consecutive_failures": consecutive_failures,
                "total_latency_ms": total_latency_ms,
                "last_latency_ms": round(latency, 2),
                "average_latency_ms": round(total_latency_ms / calls, 2),
                "max_latency_ms": round(max(float(previous.get("max_latency_ms") or 0.0), latency), 2),
                "last_attempt_at": stamp,
                "last_success_at": stamp if success else int(previous.get("last_success_at") or 0),
                "last_failure_at": stamp if not success else int(previous.get("last_failure_at") or 0),
                "last_error": "" if success else str(error or "provider call failed")[:300],
                "circuit_until_ms": circuit_until_ms,
            }
            self._records[key] = record
            if len(self._records) > self.max_records:
                oldest = sorted(self._records, key=lambda item: int(self._records[item].get("last_attempt_at") or 0))
                for stale_key in oldest[:len(self._records) - self.max_records]:
                    self._records.pop(stale_key, None)
            return self._public_record(record, stamp)

    @staticmethod
    def _public_record(record: dict[str, Any], stamp: int) -> dict[str, Any]:
        circuit_until_ms = int(record.get("circuit_until_ms") or 0)
        retry_after_ms = max(circuit_until_ms - stamp, 0)
        if retry_after_ms > 0:
            status = "CIRCUIT_OPEN"
        elif int(record.get("consecutive_failures") or 0) > 0:
            status = "DEGRADED"
        elif int(record.get("success_count") or 0) > 0:
            status = "HEALTHY"
        else:
            status = "UNKNOWN"
        return {
            **record,
            "status": status,
            "circuit_open": retry_after_ms > 0,
            "retry_after_ms": retry_after_ms,
        }

    def snapshot(self, providers: list[str] | None = None) -> dict[str, Any]:
        stamp = self.now_ms()
        provider_filter = {str(item).lower() for item in (providers or []) if item}
        with self._lock:
            records = [
                self._public_record(dict(record), stamp)
                for record in self._records.values()
                if not provider_filter or str(record.get("provider") or "").lower() in provider_filter
            ]
        grouped: dict[str, dict[str, Any]] = {}
        for record in records:
            provider = str(record.get("provider") or "unknown")
            group = grouped.setdefault(provider, {
                "provider": provider,
                "calls": 0,
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "total_latency_ms": 0.0,
                "last_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "last_attempt_at": 0,
                "last_success_at": 0,
                "last_failure_at": 0,
                "last_error": "",
                "circuit_open": False,
                "retry_after_ms": 0,
                "operations": [],
            })
            group["calls"] += int(record.get("calls") or 0)
            group["success_count"] += int(record.get("success_count") or 0)
            group["failure_count"] += int(record.get("failure_count") or 0)
            group["consecutive_failures"] = max(group["consecutive_failures"], int(record.get("consecutive_failures") or 0))
            group["total_latency_ms"] += float(record.get("total_latency_ms") or 0.0)
            if int(record.get("last_attempt_at") or 0) >= group["last_attempt_at"]:
                group["last_attempt_at"] = int(record.get("last_attempt_at") or 0)
                group["last_latency_ms"] = float(record.get("last_latency_ms") or 0.0)
                group["last_error"] = str(record.get("last_error") or "")
            group["last_success_at"] = max(group["last_success_at"], int(record.get("last_success_at") or 0))
            group["last_failure_at"] = max(group["last_failure_at"], int(record.get("last_failure_at") or 0))
            group["max_latency_ms"] = max(group["max_latency_ms"], float(record.get("max_latency_ms") or 0.0))
            group["circuit_open"] = bool(group["circuit_open"] or record.get("circuit_open"))
            group["retry_after_ms"] = max(group["retry_after_ms"], int(record.get("retry_after_ms") or 0))
            group["operations"].append(record)
        for group in grouped.values():
            calls = max(int(group["calls"]), 1)
            group["average_latency_ms"] = round(float(group.pop("total_latency_ms")) / calls, 2)
            group["last_latency_ms"] = round(float(group["last_latency_ms"]), 2)
            group["max_latency_ms"] = round(float(group["max_latency_ms"]), 2)
            if group["circuit_open"]:
                group["status"] = "CIRCUIT_OPEN"
            elif group["consecutive_failures"] > 0:
                group["status"] = "DEGRADED"
            elif group["success_count"] > 0:
                group["status"] = "HEALTHY"
            else:
                group["status"] = "UNKNOWN"
            group["operations"].sort(key=lambda item: int(item.get("last_attempt_at") or 0), reverse=True)
        return {
            "ok": True,
            "updated_at": stamp,
            "providers": grouped,
            "records": sorted(records, key=lambda item: int(item.get("last_attempt_at") or 0), reverse=True),
        }

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


PROVIDER_HEALTH = ProviderHealthRegistry()


def provider_call_allowed(provider: str, operation: str, scope: str = "global") -> tuple[bool, int]:
    return PROVIDER_HEALTH.allowed(provider, operation, scope)


def record_provider_call(
    provider: str,
    operation: str,
    *,
    success: bool,
    latency_ms: float,
    error: str = "",
    scope: str = "global",
    cooldown_ms: int | None = None,
) -> dict[str, Any]:
    return PROVIDER_HEALTH.record(
        provider,
        operation,
        success=success,
        latency_ms=latency_ms,
        error=error,
        scope=scope,
        cooldown_ms=cooldown_ms,
    )


def provider_health_snapshot(providers: list[str] | None = None) -> dict[str, Any]:
    return PROVIDER_HEALTH.snapshot(providers)


def provider_health_for_scope(
    snapshot: dict[str, Any],
    provider: str,
    operation: str,
    scope: str,
) -> dict[str, Any]:
    expected_provider = str(provider or "unknown").strip().lower()
    expected_operation = str(operation or "unknown").strip().lower()
    expected_scope = str(scope or "global").strip().upper()
    matches = [
        dict(record)
        for record in snapshot.get("records") or []
        if str(record.get("provider") or "").lower() == expected_provider
        and str(record.get("operation") or "").lower() == expected_operation
        and str(record.get("scope") or "").upper() == expected_scope
    ]
    if matches:
        matches.sort(key=lambda item: int(item.get("last_attempt_at") or 0), reverse=True)
        return matches[0]
    return {
        "provider": expected_provider,
        "operation": expected_operation,
        "scope": expected_scope,
        "calls": 0,
        "success_count": 0,
        "failure_count": 0,
        "consecutive_failures": 0,
        "last_latency_ms": 0,
        "average_latency_ms": 0,
        "last_attempt_at": 0,
        "last_success_at": 0,
        "last_failure_at": 0,
        "last_error": "",
        "circuit_open": False,
        "retry_after_ms": 0,
        "status": "UNKNOWN",
    }


def reset_provider_health() -> None:
    PROVIDER_HEALTH.reset()
