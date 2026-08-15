from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable


class StockHistoryPrewarmService:
    def __init__(
        self,
        *,
        read_candles: Callable[..., dict[str, Any]],
        cache_coverage: Callable[[str, str, str], dict[str, Any]],
        futu_status: Callable[..., dict[str, Any]],
        now_ms: Callable[[], int] | None = None,
        max_workers: int = 2,
        success_cooldown_ms: int = 30 * 60 * 1000,
    ) -> None:
        self.read_candles = read_candles
        self.cache_coverage = cache_coverage
        self.futu_status = futu_status
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self.success_cooldown_ms = max(60_000, int(success_cooldown_ms))
        self.max_workers = max(1, min(int(max_workers), 4))
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="stock-history")
        self._lock = threading.RLock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._last_started_at = 0

    @staticmethod
    def _key(symbol: str, interval: str, session: str) -> str:
        return f"{str(symbol or '').upper()}|{str(interval or '1d').lower()}|{str(session or 'regular').lower()}"

    @staticmethod
    def _coverage_ready(coverage: dict[str, Any], interval: str, limit: int) -> bool:
        if not coverage.get("available"):
            return False
        normalized_interval = str(interval or "1d").lower()
        daily = normalized_interval in {"1d", "1dutc"}
        required_rows = min(max(int(limit), 1), 260 if daily else 120)
        max_data_age_ms = (14 if daily else 5) * 24 * 60 * 60 * 1000
        data_age_ms = coverage.get("data_age_ms")
        return (
            int(coverage.get("row_count") or 0) >= required_rows
            and isinstance(data_age_ms, (int, float))
            and 0 <= float(data_age_ms) <= max_data_age_ms
        )

    @staticmethod
    def _coverage_source(coverage: dict[str, Any]) -> str:
        source_counts = coverage.get("source_counts") or {}
        if not isinstance(source_counts, dict) or not source_counts:
            return "stock_sqlite_cache"
        return str(max(source_counts.items(), key=lambda item: int(item[1] or 0))[0])

    def start(
        self,
        symbols: list[str],
        *,
        interval: str = "1d",
        session: str = "regular",
        limit: int = 520,
        force: bool = False,
    ) -> dict[str, Any]:
        stamp = self.now_ms()
        queued = 0
        skipped = 0
        seen: set[str] = set()
        for raw_symbol in symbols:
            symbol = str(raw_symbol or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            key = self._key(symbol, interval, session)
            coverage = self._coverage({"symbol": symbol, "interval": interval, "session": session}) if not force else {}
            with self._lock:
                current = self._jobs.get(key) or {}
                if current.get("status") in {"QUEUED", "RUNNING"}:
                    skipped += 1
                    continue
                if (
                    not force
                    and current.get("status") == "READY"
                    and stamp - int(current.get("finished_at") or 0) < self.success_cooldown_ms
                ):
                    skipped += 1
                    continue
                if not force and self._coverage_ready(coverage, interval, limit):
                    self._jobs[key] = {
                        "key": key,
                        "symbol": symbol,
                        "interval": interval,
                        "session": session,
                        "limit": int(limit),
                        "status": "READY",
                        "queued_at": stamp,
                        "started_at": stamp,
                        "finished_at": stamp,
                        "latency_ms": 0,
                        "source": self._coverage_source(coverage),
                        "row_count": int(coverage.get("row_count") or 0),
                        "latest_date": str(coverage.get("latest_date") or ""),
                        "error": "",
                        "force": False,
                        "cache_hit": True,
                    }
                    skipped += 1
                    continue
                self._jobs[key] = {
                    "key": key,
                    "symbol": symbol,
                    "interval": interval,
                    "session": session,
                    "limit": int(limit),
                    "status": "QUEUED",
                    "queued_at": stamp,
                    "started_at": 0,
                    "finished_at": 0,
                    "latency_ms": 0,
                    "source": "",
                    "row_count": 0,
                    "latest_date": "",
                    "error": "",
                    "force": bool(force),
                }
                self._futures[key] = self._executor.submit(self._run_job, key)
                queued += 1
        with self._lock:
            if queued:
                self._last_started_at = stamp
        return {**self.status(), "queued_now": queued, "skipped_now": skipped}

    def _run_job(self, key: str) -> None:
        with self._lock:
            job = dict(self._jobs.get(key) or {})
            if not job:
                return
            job["status"] = "RUNNING"
            job["started_at"] = self.now_ms()
            self._jobs[key] = job
        started = time.perf_counter()
        status: dict[str, Any] = {}
        try:
            try:
                status = self.futu_status(False)
            except Exception:
                status = {"opend_online": False}
            payload = self.read_candles(
                job["symbol"],
                job["limit"],
                job["interval"],
                job["session"],
                fast=False,
                force=True,
            )
            rows = list(payload.get("rows") or [])
            if not payload.get("ok") or not rows:
                raise RuntimeError(payload.get("error") or payload.get("warning") or "history returned no rows")
            source = str(payload.get("source") or "stock").lower()
            warning = str(payload.get("warning") or "").strip()
            if source in {"offline-seed", "quote_preview_seed", "quick_preview_seed"} or payload.get("fallback") or warning:
                raise RuntimeError(warning or f"history provider returned non-authoritative source: {source}")
            coverage = self._coverage(job)
            update = {
                "status": "READY",
                "source": str(payload.get("source") or "stock"),
                "row_count": int(coverage.get("row_count") or len(rows)),
                "latest_date": str(coverage.get("latest_date") or rows[-1].get("date") or ""),
                "error": "",
                "futu_online": bool(status.get("opend_online")),
            }
        except Exception as exc:
            coverage = self._coverage(job)
            error_text = str(exc)
            update = {
                "status": "SKIPPED" if "opend offline" in error_text.lower() else "ERROR",
                "source": "",
                "row_count": int(coverage.get("row_count") or 0),
                "latest_date": str(coverage.get("latest_date") or ""),
                "error": error_text[:300],
                "futu_online": bool(status.get("opend_online")),
            }
        with self._lock:
            current = dict(self._jobs.get(key) or job)
            current.update(update)
            current["finished_at"] = self.now_ms()
            current["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            self._jobs[key] = current
            self._futures.pop(key, None)

    def _coverage(self, job: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.cache_coverage(job["symbol"], job["interval"], job["session"])
        except Exception:
            return {}

    def status(self, symbol: str = "") -> dict[str, Any]:
        clean_symbol = str(symbol or "").strip().upper()
        with self._lock:
            jobs = [dict(job) for job in self._jobs.values() if not clean_symbol or job.get("symbol") == clean_symbol]
            active = len(self._futures)
            last_started_at = self._last_started_at
        jobs.sort(key=lambda item: (int(item.get("queued_at") or 0), str(item.get("symbol") or "")))
        counts = {name: sum(1 for job in jobs if job.get("status") == name) for name in ["QUEUED", "RUNNING", "READY", "SKIPPED", "ERROR"]}
        return {
            "ok": True,
            "symbol": clean_symbol,
            "active_jobs": active,
            "counts": counts,
            "jobs": jobs,
            "last_started_at": last_started_at,
            "updated_at": self.now_ms(),
            "max_concurrency": self.max_workers,
            "mode": "read_only_history_prewarm",
            "live_trading_allowed": False,
        }

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)
