from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.instrument_rules import (
    PublicInstrumentRuleService,
    build_okx_public_spot_rules,
    verify_public_instrument_rules,
)


def okx_payload(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "instType": "SPOT",
        "instId": "BTC-USDT",
        "baseCcy": "BTC",
        "quoteCcy": "USDT",
        "state": "live",
        "tickSz": "0.1",
        "lotSz": "0.00000001",
        "minSz": "0.00001",
        "maxLmtSz": "9999999999",
        "maxMktSz": "1000000",
        "listTime": "1611907686000",
        "contTdSwTime": "",
        "expTime": "",
        "ctVal": "",
        "ctMult": "",
        "ctValCcy": "",
        "groupId": "12",
        "upcChg": [],
    }
    row.update(overrides)
    return {"code": "0", "msg": "", "data": [row]}


class PublicInstrumentRuleTests(unittest.TestCase):
    def test_verified_spot_rules_bind_exact_decimal_strings_and_hashes(self) -> None:
        first = build_okx_public_spot_rules(
            okx_payload(),
            symbol="BTC-USDT",
            captured_at_ms=1_000_000,
        )
        second = build_okx_public_spot_rules(
            okx_payload(),
            symbol="BTC-USDT",
            captured_at_ms=1_001_000,
        )

        self.assertEqual(first["status"], "VERIFIED")
        self.assertEqual(first["tick_size"], "0.1")
        self.assertEqual(first["lot_size"], "0.00000001")
        self.assertEqual(first["minimum_order_size"], "0.00001")
        self.assertIsNone(first["minimum_cost"])
        self.assertFalse(first["verification"]["account_fee_verified"])
        self.assertFalse(first["verification"]["minimum_cost_verified"])
        self.assertEqual(first["rules_hash"], second["rules_hash"])
        self.assertNotEqual(first["snapshot_hash"], second["snapshot_hash"])
        verification = verify_public_instrument_rules(
            first,
            expected_symbol="BTC-USDT",
            now_ms=1_000_100,
        )
        self.assertEqual(verification["status"], "PASS")
        self.assertFalse(verification["rules"]["credentials_used"])
        self.assertFalse(verification["rules"]["live_order_allowed"])

    def test_bad_identity_state_precision_and_derivative_fields_fail_closed(self) -> None:
        cases = (
            {"instType": "SWAP"},
            {"instId": "ETH-USDT"},
            {"state": "preopen"},
            {"tickSz": "0"},
            {"lotSz": "not-a-decimal"},
            {"ctVal": "0.01"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                snapshot = build_okx_public_spot_rules(
                    okx_payload(**overrides),
                    symbol="BTC-USDT",
                    captured_at_ms=1_000_000,
                )
                self.assertNotEqual(snapshot["status"], "VERIFIED")
                self.assertFalse(snapshot["verification"]["venue_rules_verified"])
                self.assertFalse(snapshot["live_order_allowed"])

    def test_same_symbol_concurrent_requests_share_one_public_fetch(self) -> None:
        call_count = 0
        count_lock = threading.Lock()

        def fetch(_path: str, _query: dict[str, str]) -> dict[str, object]:
            nonlocal call_count
            with count_lock:
                call_count += 1
            time.sleep(0.02)
            return okx_payload()

        service = PublicInstrumentRuleService(fetch_payload=fetch, now_ms=lambda: 1_000_000)
        results: list[dict[str, object]] = []
        threads = [threading.Thread(target=lambda: results.append(service.snapshot("BTC-USDT"))) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(call_count, 1)
        self.assertEqual(len(results), 8)
        self.assertTrue(all(item["status"] == "VERIFIED" for item in results))
        self.assertEqual(len({str(item["rules_hash"]) for item in results}), 1)

    def test_same_symbol_concurrent_force_requests_share_one_refresh(self) -> None:
        call_count = 0
        count_lock = threading.Lock()

        def fetch(_path: str, _query: dict[str, str]) -> dict[str, object]:
            nonlocal call_count
            with count_lock:
                call_count += 1
            time.sleep(0.02)
            return okx_payload()

        service = PublicInstrumentRuleService(fetch_payload=fetch, now_ms=lambda: 1_000_000)
        results: list[dict[str, object]] = []
        threads = [
            threading.Thread(target=lambda: results.append(service.snapshot("BTC-USDT", force=True)))
            for _ in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(call_count, 1)
        self.assertEqual(len(results), 8)
        self.assertTrue(all(item["status"] == "VERIFIED" for item in results))
        self.assertEqual(service._inflight, {})

    def test_failed_symbols_leave_no_per_key_inflight_state(self) -> None:
        service = PublicInstrumentRuleService(
            fetch_payload=lambda _path, _query: {"code": "0", "data": []},
            now_ms=lambda: 1_000_000,
        )

        for index in range(20):
            result = service.snapshot(f"BAD{index}-USDT")
            self.assertEqual(result["status"], "NOT_FOUND")

        self.assertEqual(service._inflight, {})
        self.assertEqual(service._cache, {})

    def test_refresh_failure_preserves_last_good_as_stale_not_verified(self) -> None:
        clock = [1_000_000]
        fail = [False]

        def fetch(_path: str, _query: dict[str, str]) -> dict[str, object]:
            if fail[0]:
                raise RuntimeError("public endpoint unavailable")
            return okx_payload()

        service = PublicInstrumentRuleService(
            fetch_payload=fetch,
            now_ms=lambda: clock[0],
            max_age_ms=100,
        )
        good = service.snapshot("BTC-USDT")
        fail[0] = True
        clock[0] += 101
        stale = service.snapshot("BTC-USDT")

        self.assertEqual(good["status"], "VERIFIED")
        self.assertEqual(stale["status"], "STALE")
        self.assertFalse(stale["current"])
        self.assertEqual(stale["rules_hash"], good["rules_hash"])
        self.assertIn("public_rules_refresh_failed", stale["blockers"])
        verification = verify_public_instrument_rules(
            stale,
            expected_symbol="BTC-USDT",
            now_ms=clock[0],
        )
        self.assertNotEqual(verification["status"], "PASS")
        self.assertFalse(stale["live_order_allowed"])


if __name__ == "__main__":
    unittest.main()
