from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.public_order_book import (
    PublicOrderBookService,
    build_okx_public_order_book,
    build_public_order_book_microstructure,
    legacy_okx_order_book_payload,
    public_order_book_placeholder,
    verify_public_order_book,
)
from exchange_terminal.services import public_order_book as order_book_module


NOW_MS = 1_000_100


def payload(
    *,
    asks: list[list[str]] | None = None,
    bids: list[list[str]] | None = None,
    timestamp: str = "1000000",
    sequence_id: int = 42,
) -> dict[str, object]:
    return {
        "code": "0",
        "msg": "",
        "data": [{
            "asks": [
                ["100.0000000000000000001", "0.05", "0", "2"],
                ["100.1", "0.10", "0", "3"],
            ] if asks is None else asks,
            "bids": [
                ["99.9", "0.20", "0", "4"],
                ["99.8", "0.30", "0", "5"],
            ] if bids is None else bids,
            "ts": timestamp,
            "seqId": sequence_id,
        }],
    }


class PublicOrderBookTests(unittest.TestCase):
    def test_verified_snapshot_preserves_decimal_evidence_and_permissions(self) -> None:
        book = build_okx_public_order_book(
            payload(),
            symbol="BTC-USDT",
            observed_at_ms=NOW_MS,
        )
        verified = verify_public_order_book(
            book,
            expected_symbol="BTC-USDT",
            now_ms=NOW_MS,
        )

        self.assertEqual(verified["status"], "PASS")
        self.assertEqual(book["asks"][0]["price"], "100.0000000000000000001")
        self.assertEqual(book["asks"][0]["size"], "0.05")
        self.assertEqual(book["liquidity_scope"], "STANDARD_BOOK_NON_RPI")
        self.assertEqual(book["book_half_used"], "ASKS")
        self.assertNotIn("side", book)
        self.assertEqual(book["checksum_policy"], "NOT_APPLICABLE")
        self.assertTrue(book["hash_verified"])
        self.assertTrue(book["contract_hash_verified"])
        self.assertFalse(book["complete_book_verified"])
        self.assertFalse(book["is_executable_quote"])
        self.assertFalse(book["execution_allowed"])
        self.assertFalse(book["paper_authorized"])
        self.assertFalse(book["live_order_allowed"])

    def test_empty_crossed_and_unsorted_books_fail_closed(self) -> None:
        cases = {
            "empty": (payload(asks=[], bids=[]), "NOT_CHECKED"),
            "asks_only": (payload(bids=[]), "NOT_CHECKED"),
            "crossed": (payload(
                asks=[["99", "1", "0", "1"], ["100", "1", "0", "1"]],
                bids=[["101", "1", "0", "1"], ["98", "1", "0", "1"]],
            ), "BLOCK"),
            "unsorted": (payload(
                asks=[["101", "1", "0", "1"], ["100", "1", "0", "1"]],
            ), "BLOCK"),
        }
        for name, (raw, expected) in cases.items():
            with self.subTest(name=name):
                book = build_okx_public_order_book(raw, symbol="BTC-USDT", observed_at_ms=NOW_MS)
                self.assertEqual(book["status"], expected)
                self.assertFalse(book["planning_usable"])
                self.assertNotEqual(legacy_okx_order_book_payload(book)["code"], "0")

    def test_singleflight_and_timestamp_regression_preserve_last_good(self) -> None:
        calls = {"count": 0}
        current = {"now": NOW_MS, "timestamp": "1000000", "sequence": 42}

        def fetch(_path: str, _query: dict[str, str]) -> dict[str, object]:
            calls["count"] += 1
            time.sleep(0.02)
            return payload(timestamp=current["timestamp"], sequence_id=current["sequence"])

        service = PublicOrderBookService(
            fetch_payload=fetch,
            now_ms=lambda: current["now"],
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            first = list(pool.map(lambda _index: service.snapshot("BTC-USDT", force=True), range(8)))

        self.assertEqual(calls["count"], 1)
        self.assertTrue(all(item["status"] == "VERIFIED" for item in first))
        accepted_hash = first[0]["book_hash"]

        current.update({"now": 1_002_000, "timestamp": "999000", "sequence": 40})
        regressed = service.snapshot("BTC-USDT", force=True)

        self.assertEqual(calls["count"], 2)
        self.assertEqual(regressed["status"], "BLOCK")
        self.assertEqual(regressed["book_hash"], accepted_hash)
        self.assertTrue(regressed["validation"]["cache_regression"])
        self.assertFalse(regressed["planning_usable"])

        forged = copy.deepcopy(regressed)
        forged["status"] = "VERIFIED"
        forged["current"] = True
        forged["planning_usable"] = True
        forged["validation"]["cache_regression"] = False
        forged["blockers"] = []
        forged_result = verify_public_order_book(
            forged,
            expected_symbol="BTC-USDT",
            now_ms=current["now"],
        )
        self.assertEqual(forged_result["status"], "BLOCK")
        self.assertIn("public_order_book_contract_hash_invalid", forged_result["blockers"])

    def test_microstructure_derives_two_sided_facts_without_signal_authority(self) -> None:
        book = build_okx_public_order_book(payload(), symbol="BTC-USDT", observed_at_ms=NOW_MS)
        truth = build_public_order_book_microstructure(
            book,
            expected_symbol="BTC-USDT",
            now_ms=NOW_MS,
        )

        self.assertEqual(truth["status"], "OBSERVATION_ONLY")
        self.assertEqual(truth["schema_version"], "public-order-book-microstructure-v2")
        self.assertEqual(truth["book_sides_observed"], "BIDS_AND_ASKS")
        self.assertEqual(truth["evidence"]["comparison_level_count"], 2)
        self.assertEqual(truth["top_of_book"]["spread_quote"], "0.1000000000000000001")
        self.assertEqual(truth["visible_depth"]["bid_base_total"], "0.5")
        self.assertEqual(truth["visible_depth"]["ask_base_total"], "0.15")
        self.assertEqual(truth["visible_depth"]["bid_quote_notional"], "49.92")
        self.assertEqual(truth["visible_depth"]["ask_quote_notional"], "15.010000000000000000005")
        self.assertEqual(truth["top_of_book"]["spread_bps"], "10.0050025")
        self.assertEqual(truth["top_of_book"]["spread_bps_basis"], "MID_PRICE")
        self.assertEqual(truth["visible_depth"]["bid_to_ask_quote_ratio"], "3.325782811459")
        self.assertEqual(
            truth["price_band_depth"],
            {
                "basis": "SYMMETRIC_MID_PRICE_BPS",
                "bands_bps": [5, 10, 25],
                "boundary_inclusive": True,
                "reference_mid_price": "99.95000000000000000005",
                "coverage_rule": "VISIBLE_PREFIX_REACHES_BAND_BOUNDARY",
                "quote_notional_semantics": "VISIBLE_LOWER_BOUND_WHEN_BOUNDARY_NOT_COVERED",
                "rows": [
                    {
                        "band_bps": 5,
                        "bid_floor_price": "99.900025000000000000049975",
                        "ask_ceiling_price": "99.999975000000000000050025",
                        "visible_bid_levels": 0,
                        "visible_ask_levels": 0,
                        "visible_bid_base_total": "0",
                        "visible_ask_base_total": "0",
                        "visible_bid_quote_notional": "0",
                        "visible_ask_quote_notional": "0",
                        "bid_band_boundary_covered": True,
                        "ask_band_boundary_covered": True,
                        "two_sided_band_boundary_covered": True,
                    },
                    {
                        "band_bps": 10,
                        "bid_floor_price": "99.85005000000000000004995",
                        "ask_ceiling_price": "100.04995000000000000005005",
                        "visible_bid_levels": 1,
                        "visible_ask_levels": 1,
                        "visible_bid_base_total": "0.2",
                        "visible_ask_base_total": "0.05",
                        "visible_bid_quote_notional": "19.98",
                        "visible_ask_quote_notional": "5.000000000000000000005",
                        "bid_band_boundary_covered": True,
                        "ask_band_boundary_covered": True,
                        "two_sided_band_boundary_covered": True,
                    },
                    {
                        "band_bps": 25,
                        "bid_floor_price": "99.700125000000000000049875",
                        "ask_ceiling_price": "100.199875000000000000050125",
                        "visible_bid_levels": 2,
                        "visible_ask_levels": 2,
                        "visible_bid_base_total": "0.5",
                        "visible_ask_base_total": "0.15",
                        "visible_bid_quote_notional": "49.92",
                        "visible_ask_quote_notional": "15.010000000000000000005",
                        "bid_band_boundary_covered": False,
                        "ask_band_boundary_covered": False,
                        "two_sided_band_boundary_covered": False,
                    },
                ],
                "complete_book_verified": False,
            },
        )
        self.assertEqual(
            Decimal(truth["visible_depth"]["bid_share"])
            + Decimal(truth["visible_depth"]["ask_share"]),
            Decimal("1"),
        )
        self.assertEqual(truth["evidence"]["book_hash"], book["book_hash"])
        self.assertEqual(truth["evidence"]["book_contract_hash"], book["contract_hash"])
        self.assertTrue(truth["interpretation"]["descriptive_only"])
        self.assertFalse(truth["interpretation"]["signal_allowed"])
        self.assertFalse(truth["execution_allowed"])
        self.assertFalse(truth["paper_authorized"])
        self.assertFalse(truth["live_order_allowed"])
        self.assertEqual(
            truth["permissions"],
            {
                "planning_only": True,
                "order_submission_allowed": False,
                "execution_allowed": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        )
        hash_content = {
            key: value
            for key, value in truth.items()
            if key not in {"microstructure_hash", "hash_verified"}
        }
        expected_hash = hashlib.sha256(json.dumps(
            hash_content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        self.assertEqual(truth["microstructure_hash"], expected_hash)
        self.assertNotIn("direction", truth)
        self.assertNotIn("action", truth)

    def test_microstructure_and_not_applicable_contracts_fail_closed(self) -> None:
        stale_book = build_okx_public_order_book(
            payload(),
            symbol="BTC-USDT",
            observed_at_ms=NOW_MS + 10_000,
        )
        stale_truth = build_public_order_book_microstructure(
            stale_book,
            expected_symbol="BTC-USDT",
            now_ms=NOW_MS + 10_000,
        )
        self.assertEqual(stale_truth["status"], "NOT_CHECKED")
        self.assertEqual(stale_truth["top_of_book"]["best_bid"], "")

        stock_book = public_order_book_placeholder("AAPL", observed_at_ms=NOW_MS)
        stock_book["permissions"]["live_order_allowed"] = True
        stock_book = order_book_module._seal_contract(stock_book)
        result = verify_public_order_book(stock_book, expected_symbol="AAPL", now_ms=NOW_MS)
        self.assertEqual(result["status"], "BLOCK")
        microstructure = build_public_order_book_microstructure(
            stock_book,
            expected_symbol="AAPL",
            now_ms=NOW_MS,
        )
        self.assertEqual(microstructure["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
