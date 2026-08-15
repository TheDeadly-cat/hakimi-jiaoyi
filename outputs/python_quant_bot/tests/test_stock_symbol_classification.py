from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.market_data.stocks import is_stock_symbol, stock_meta


class StockSymbolClassificationTests(unittest.TestCase):
    def test_unlisted_plain_us_tickers_remain_stock_research_symbols(self) -> None:
        for symbol in ("ON", "MCHP", "MPWR", "NXPI"):
            with self.subTest(symbol=symbol):
                self.assertTrue(is_stock_symbol(symbol))
                self.assertEqual(stock_meta(symbol)["market"], "US")
                self.assertEqual(stock_meta(symbol)["yahoo"], symbol)

    def test_normalized_crypto_symbols_and_plain_crypto_bases_are_not_stocks(self) -> None:
        for symbol in ("BTC", "ETH", "BTC-USDT", "ETH-USDT-SWAP"):
            with self.subTest(symbol=symbol):
                self.assertFalse(is_stock_symbol(symbol))

    def test_invalid_or_hyphenated_unknown_symbols_do_not_become_stocks(self) -> None:
        for symbol in ("", "BAD-SYMBOL", "../AAPL", "AAPL/USD"):
            with self.subTest(symbol=symbol):
                self.assertFalse(is_stock_symbol(symbol))


if __name__ == "__main__":
    unittest.main()
