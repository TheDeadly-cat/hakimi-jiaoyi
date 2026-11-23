"""Offline examples for the two frozen calculation modules."""
from decimal import Decimal
import unittest

from terminal_depth_replay import preview_depth
from terminal_sim_order_fees import paper_order_fees


class FeeTests(unittest.TestCase):
    # Expected cases retained from test_terminal_workflow_records.py.
    def test_stock_caps(self):
        total, parts = paper_order_fees("STOCK", "buy", 1, Decimal(".50"))
        self.assertEqual((total, parts["commission"], parts["platform"]),
                         (Decimal(".01"), Decimal(".0025"), Decimal(".0025")))
        total, parts = paper_order_fees("STOCK", "sell", 100000, Decimal("100"))
        self.assertEqual((total, parts["trading_activity"]), (Decimal("1378.30"), Decimal("8.30")))

    def test_option_fee_threshold(self):
        total, parts = paper_order_fees("OPTION", "buy", 20, Decimal(".10"))
        self.assertEqual((total, parts["commission"]), (Decimal("9.58"), Decimal("3")))
        higher, _ = paper_order_fees("OPTION", "buy", 20, Decimal(".1001"))
        sell, parts = paper_order_fees("OPTION", "sell", 20, Decimal(".10"))
        self.assertEqual((higher, sell, parts["regulatory"]),
                         (Decimal("19.58"), Decimal("9.65"), Decimal(".01")))


class DepthTests(unittest.TestCase):
    def setUp(self):
        # Fictional prices, quantities and times for a synthetic US symbol.
        stamp = "2000-01-03T15:00:00Z"
        self.request = {
            "order": {"symbol": "DEMO", "side": "BUY", "quantity": 4,
                      "type": "LIMIT", "limit_price": 10},
            "as_of": stamp,
            "quote": {"symbol": "DEMO", "code": "US.DEMO", "currency": "USD", "ok": True,
                      "source": "Futu OpenD / get_market_snapshot", "receivedAt": stamp,
                      "book": {"status": "AVAILABLE", "source": "Futu OpenD / get_order_book",
                               "bookType": "NORMAL", "invalidLevels": 0, "crossed": False,
                               "receivedAt": stamp, "bids": [{"level": 1, "price": 9, "size": 4}],
                               "asks": [{"level": 1, "price": 10, "size": 3},
                                        {"level": 2, "price": 11, "size": 1}]}}
        }

    def test_limit_leaves_unpriced_quantity(self):
        result = preview_depth(self.request)
        self.assertEqual(result["status"], "PARTIAL_DEPTH")
        self.assertEqual(result["estimated_notional_usd"], "30")
        self.assertEqual(result["unpriced_quantity"], "1")
        self.assertIsNone(result["broker_fill_quantity"])
        self.assertFalse(result["execution_authorized"])

    def test_future_book_cannot_price_order(self):
        self.request["quote"]["book"]["receivedAt"] = "2000-01-03T15:00:01Z"
        with self.assertRaises(ValueError):
            preview_depth(self.request)
