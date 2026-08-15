from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

# Keep this isolated test from probing any local AI environment file during
# module import; the production process sets the same flag before imports.
os.environ.setdefault("HAKIMI_SKIP_LOCAL_AI_ENV", "1")

from exchange_terminal.market_data.provider_health import ProviderRequestCoordinator
from exchange_terminal.market_data import okx


class ProviderRequestCoordinatorTests(unittest.TestCase):
    def test_window_is_bounded_and_reopens_after_time_moves(self) -> None:
        clock = [1_000]
        coordinator = ProviderRequestCoordinator(
            now_ms=lambda: clock[0],
            max_requests=2,
            window_ms=100,
        )
        self.assertEqual(coordinator.acquire(), (True, 0, "ACQUIRED"))
        self.assertEqual(coordinator.acquire(), (True, 0, "ACQUIRED"))
        allowed, retry_after, reason = coordinator.acquire()
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
        self.assertEqual(reason, "RATE_LIMIT")
        clock[0] += 100
        self.assertEqual(coordinator.acquire(), (True, 0, "ACQUIRED"))
        self.assertEqual(coordinator.snapshot()["in_window"], 1)

    def test_failures_use_bounded_exponential_backoff(self) -> None:
        clock = [2_000]
        coordinator = ProviderRequestCoordinator(
            now_ms=lambda: clock[0],
            max_requests=5,
            window_ms=100,
            failure_threshold=2,
            backoff_base_ms=10,
            backoff_cap_ms=25,
        )
        for _ in range(2):
            self.assertTrue(coordinator.acquire()[0])
            coordinator.complete(success=False)
        allowed, retry_after, reason = coordinator.acquire()
        self.assertFalse(allowed)
        self.assertEqual(reason, "BACKOFF")
        self.assertEqual(retry_after, 10)
        clock[0] += 10
        self.assertTrue(coordinator.acquire()[0])
        coordinator.complete(success=True)
        self.assertFalse(coordinator.snapshot()["backoff_active"])

    def test_okx_get_is_admitted_once_and_records_only_safe_health(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"code": "0", "data": []}).encode("utf-8")

        coordinator = ProviderRequestCoordinator(max_requests=1, window_ms=10_000)
        with (
            patch.object(okx, "OKX_PUBLIC_REQUEST_COORDINATOR", coordinator),
            patch.object(okx, "provider_call_allowed", return_value=(True, 0)),
            patch.object(okx, "record_provider_call") as record,
            patch.object(okx.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen,
        ):
            first = okx.read_bodyless_okx("/api/v5/public/instruments", {"instType": "SPOT"})
            self.assertEqual(first["code"], "0")
            with self.assertRaisesRegex(RuntimeError, "rate_limit"):
                okx.read_bodyless_okx("/api/v5/market/books", {"instId": "BTC-USDT"})
        urlopen.assert_called_once()
        self.assertEqual(record.call_count, 1)
        kwargs = record.call_args.kwargs
        self.assertEqual(kwargs["scope"], "GLOBAL")
        self.assertEqual(kwargs["error"], "")


if __name__ == "__main__":
    unittest.main()
