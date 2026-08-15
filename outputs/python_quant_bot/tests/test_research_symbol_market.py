from __future__ import annotations

import ast
from pathlib import Path
import unittest

from exchange_terminal.services.research_symbol_market import (
    RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION,
    research_market_for_symbol,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ResearchSymbolMarketTests(unittest.TestCase):
    def test_classifier_covers_supported_equity_and_non_usdt_crypto_symbols(self) -> None:
        self.assertEqual(RESEARCH_SYMBOL_MARKET_CLASSIFIER_VERSION, "research-symbol-market-v1")
        self.assertEqual(research_market_for_symbol("AAPL"), "stock")
        self.assertEqual(research_market_for_symbol("US.AAPL"), "stock")
        self.assertEqual(research_market_for_symbol("HK.00700"), "stock")
        self.assertEqual(research_market_for_symbol("BTC-USDC"), "crypto")
        self.assertEqual(research_market_for_symbol("BTC-USD-SWAP"), "crypto")
        self.assertEqual(research_market_for_symbol("BTC"), "crypto")
        with self.assertRaisesRegex(ValueError, "research_symbol_market_unsupported"):
            research_market_for_symbol("UNSUPPORTED_LONG_SYMBOL")

    def test_selection_replay_imports_no_configful_market_or_server_module(self) -> None:
        forbidden = {
            "exchange_terminal.config",
            "exchange_terminal.server",
            "exchange_terminal.market_data.stocks",
        }
        for relative in (
            "exchange_terminal/services/research_symbol_market.py",
            "exchange_terminal/services/strategy_selection_replay.py",
        ):
            tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
            imported: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    module = str(node.module or "")
                    if node.level == 0:
                        imported.add(module)
                    elif module == "market_data.stocks":
                        imported.add("exchange_terminal.market_data.stocks")
            self.assertTrue(forbidden.isdisjoint(imported), (relative, imported & forbidden))


if __name__ == "__main__":
    unittest.main()
