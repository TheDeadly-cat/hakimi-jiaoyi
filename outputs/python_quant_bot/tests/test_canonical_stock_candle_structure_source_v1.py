from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from _canonical_source import activate_canonical_source

activate_canonical_source()

import hakimi_research.stock_candles as canonical
from exchange_terminal.market_data import stock_candles as legacy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
CANONICAL_SOURCE = REPOSITORY_ROOT / "src" / "hakimi_research" / "stock_candles.py"
LEGACY_SOURCE = PROJECT_ROOT / "exchange_terminal" / "market_data" / "stock_candles.py"
ARCHIVED_SOURCE = REPOSITORY_ROOT / "archive" / "historical_research" / "adr0551_exchange_terminal_stock_candles.py"
WORKFLOW_SOURCE = REPOSITORY_ROOT / ".github" / "workflows" / "research-contracts.yml"
ORIGINAL_SHA256 = "7c1ad93b225762f283d55e9e1cdb5e2c47afcf0fd946726968ae76b7cafb6bb5"
CONSUMERS = (
    "exchange_terminal/server.py",
    "exchange_terminal/market_data/futu_quotes.py",
    "exchange_terminal/market_data/stock_candles_io.py",
)


class CanonicalStockCandleStructureSourceV1Tests(unittest.TestCase):
    def test_canonical_source_is_versioned_and_outside_outputs(self) -> None:
        self.assertTrue(CANONICAL_SOURCE.is_file())
        self.assertNotIn("outputs", CANONICAL_SOURCE.parts)
        self.assertEqual(canonical.STOCK_CANDLE_STRUCTURE_CONTRACT_VERSION, "stock-candle-structure-v1")

    def test_original_source_is_archived_byte_identically(self) -> None:
        self.assertEqual(hashlib.sha256(ARCHIVED_SOURCE.read_bytes()).hexdigest(), ORIGINAL_SHA256)

    def test_legacy_wrapper_has_no_definitions_and_reexports_identical_objects(self) -> None:
        tree = ast.parse(LEGACY_SOURCE.read_text(encoding="utf-8"))
        definitions = tuple(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
        )
        self.assertEqual(definitions, ())
        self.assertEqual(legacy.__all__, canonical.__all__)
        for name in canonical.__all__:
            self.assertIs(getattr(legacy, name), getattr(canonical, name), name)

    def test_active_consumers_import_canonical_source_directly(self) -> None:
        for relative_path in CONSUMERS:
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("from hakimi_research.stock_candles import", source, relative_path)
            self.assertNotIn("market_data.stock_candles import", source, relative_path)

    def test_non_native_rows_and_values_fail_before_controlled_methods(self) -> None:
        calls: list[str] = []

        class TrapNumber:
            def __float__(self) -> float:
                calls.append("number.__float__")
                return 100.0

            def __int__(self) -> int:
                calls.append("number.__int__")
                return 100

        class TrapDict(dict[str, object]):
            def get(self, key: str, default: object = None) -> object:
                calls.append("dict.get")
                return TrapNumber()

            def __iter__(self):
                calls.append("dict.__iter__")
                return super().__iter__()

        class TrapList(list[object]):
            def __iter__(self):
                calls.append("list.__iter__")
                return super().__iter__()

        self.assertIsNone(canonical.normalize_stock_cache_candle(TrapDict(), "AAPL"))
        self.assertEqual(canonical.aggregate_stock_rows(TrapList([{}]), 60_000), [])
        self.assertEqual(canonical.latest_stock_candle_ts(TrapList([{}])), 0)
        self.assertEqual(canonical.stock_payload_source(TrapDict()), "")
        self.assertIsNone(
            canonical.normalize_stock_cache_candle(
                {"ts": TrapNumber(), "open": 99, "high": 101, "low": 98, "close": TrapNumber(), "volume": 1},
                "AAPL",
            )
        )
        self.assertEqual(calls, [])

    def test_structural_validation_and_empty_freshness_fail_closed(self) -> None:
        valid = canonical.normalize_stock_cache_candle(
            {"ts": 1_700_000_000_000, "date": "2023-11-14", "open": 99, "high": 101, "low": 98, "close": 100, "volume": 10},
            "AAPL",
        )
        invalid_ohlc = canonical.normalize_stock_cache_candle(
            {"ts": 1_700_000_000_000, "open": 99, "high": 97, "low": 98, "close": 100, "volume": 10},
            "AAPL",
        )
        empty = canonical.with_stock_freshness(
            {"rows": [], "source": "futu", "realtime": True, "in_progress": True},
            "1m",
            "AAPL",
            at_ms=1_700_000_000_000,
        )
        self.assertIsNotNone(valid)
        self.assertIsNone(invalid_ohlc)
        self.assertFalse(empty["realtime"])
        self.assertFalse(empty["in_progress"])
        self.assertEqual(empty["latest_ts"], 0)

    def test_injected_clock_is_deterministic_and_non_authorizing(self) -> None:
        row_ts = 1_700_000_000_000
        first = canonical.with_stock_freshness(
            {"rows": [{"ts": row_ts, "close": 100, "complete": False}], "source": "futu"},
            "1m",
            "AAPL",
            at_ms=row_ts + 1_000,
        )
        second = canonical.with_stock_freshness(
            {"rows": [{"ts": row_ts, "close": 100, "complete": False}], "source": "futu"},
            "1m",
            "AAPL",
            at_ms=row_ts + 1_000,
        )
        self.assertEqual(first, second)
        self.assertTrue(first["realtime"])
        self.assertNotIn("execution_eligible", first)
        self.assertNotIn("execution_authority", first)

    def test_root_workflow_runs_this_contract(self) -> None:
        workflow = WORKFLOW_SOURCE.read_text(encoding="utf-8")
        self.assertIn("tests.test_canonical_stock_candle_structure_source_v1", workflow)


if __name__ == "__main__":
    unittest.main()
