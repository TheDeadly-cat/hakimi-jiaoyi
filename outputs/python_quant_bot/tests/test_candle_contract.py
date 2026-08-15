from __future__ import annotations

import unittest

from exchange_terminal.market_data.candle_contract import candle_is_complete, explicit_boolean


class CandleContractTests(unittest.TestCase):
    def test_explicit_boolean_accepts_only_recognized_values(self) -> None:
        self.assertIs(explicit_boolean(True), True)
        self.assertIs(explicit_boolean(1), True)
        self.assertIs(explicit_boolean("completed"), True)
        self.assertIs(explicit_boolean(False), False)
        self.assertIs(explicit_boolean(0), False)
        self.assertIs(explicit_boolean("false"), False)
        self.assertIsNone(explicit_boolean("definitely"))
        self.assertIsNone(explicit_boolean(2))

    def test_candle_completion_fails_closed_on_malformed_flags(self) -> None:
        self.assertTrue(candle_is_complete({"complete": "true"}))
        self.assertFalse(candle_is_complete({"complete": "false"}))
        self.assertFalse(candle_is_complete({"complete": "invalid"}))
        self.assertTrue(candle_is_complete({"provisional": "false"}))
        self.assertFalse(candle_is_complete({"provisional": "true"}))
        self.assertFalse(candle_is_complete({}))
        self.assertTrue(candle_is_complete({}, default_if_missing=True))


if __name__ == "__main__":
    unittest.main()
